"""What the agent did with the last questions, from their traces in Phoenix: no question is asked again.

    uv run python experiments/trace_stats.py [N] [--trace ID] [--project NAME]

For each question (a `question` span): its time, the model calls of the agent, the tools it ran (search rounds, the empty ones,
reads that gave text), the tool results that were an error or a refusal ("No more reading", a repeated call), the calls the
guard made the report (its order to answer in the model's input), the calls asked again after a tool call written as text
(`again`), and how long the last model call took (it writes the answer). Then the totals: where the time goes, how often the
agent searched round after round, which questions the screen stopped.

`--trace ID` prints one question's tool calls in order, with what each found.
"""

import argparse
import json
import statistics
import sys
from collections import Counter

import httpx

PHOENIX = "http://localhost:6006"
FORCED = ("You have used your tool budget",)  # core.FINAL_HINT: the guard's order to answer
AGAIN = ("That tool call was not made",)  # core.NOT_MADE_HINT / UNKNOWN_TOOL_HINT: asked again after a call written as text
SCREEN = ("С этим я помогать не буду", "I won't help with that", "Я помогаю только с вопросами", "I only help with questions",
          "Такие задачи я не выполняю", "I don't do tasks like that")  # guardrail.REFUSALS


def gql(query: str, **variables) -> dict:
    r = httpx.post(f"{PHOENIX}/graphql", json={"query": query, "variables": variables}, timeout=120).json()
    if "errors" in r:
        sys.exit(r["errors"])
    return r["data"]


def project_id(name: str) -> str:
    return next(p["id"] for p in httpx.get(f"{PHOENIX}/v1/projects", timeout=10).json()["data"] if p["name"] == name)


def questions(project: str, n: int) -> list[str]:
    data = gql("""query($id: ID!, $n: Int!, $f: String) { node(id: $id) { ... on Project {
        spans(first: $n, filterCondition: $f, sort: {col: startTime, dir: desc}) { edges { node { context { traceId } } } } } } }""",
               id=project, n=n, f="name == 'question'")
    return [e["node"]["context"]["traceId"] for e in data["node"]["spans"]["edges"]]


def spans_of(project: str, trace: str) -> list[dict]:
    data = gql("""query($id: ID!, $t: ID!) { node(id: $id) { ... on Project { trace(traceId: $t) { spans(first: 1000) { edges { node {
        spanId parentId name spanKind startTime latencyMs attributes input { value } output { value } } } } } } } }""", id=project, t=trace)
    spans = [e["node"] for e in data["node"]["trace"]["spans"]["edges"]]
    for s in spans:
        if isinstance(s["attributes"], str):
            s["attributes"] = json.loads(s["attributes"] or "{}")
    return sorted(spans, key=lambda s: s["startTime"])


def tool_result(span: dict) -> dict | None:
    """The JSON a tool gave the model, or None (text); its artifact, unseen by the model, as `artifact`."""
    try:
        out = json.loads((span.get("output") or {}).get("value") or "{}")
        data = out["update"]["messages"][0]["data"] if "update" in out else {"content": out}
        content = json.loads(data["content"]) if isinstance(data["content"], str) else data["content"]
        return {**content, "artifact": data["artifact"]} if isinstance(content, dict) and data.get("artifact") else content
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def _parents(span: dict, by_id: dict) -> list[dict]:
    out = []
    while span.get("parentId") in by_id:
        span = by_id[span["parentId"]]
        out.append(span)
    return out


def summary(spans: list[dict]) -> dict:
    by_id = {s["spanId"]: s for s in spans}
    root = next((s for s in spans if s["name"] == "question"), spans[0])
    answer = ((root.get("output") or {}).get("value") or "")
    out = {"when": root["startTime"][:16].replace("T", " "), "question": (root.get("input") or {}).get("value") or "",
           "seconds": (root["latencyMs"] or 0) / 1000, "screened": answer.startswith(SCREEN), "calls": 0, "rounds": 0, "empty": 0,
           "reads": 0, "errors": [], "forced": 0, "again": 0, "final": 0.0, "tools": []}
    llm = [s for s in spans if s["spanKind"] == "llm" and s["name"] != "guardrail"
           and not any(p["name"] == "guardrail" for p in _parents(s, by_id))]  # (not the screen's own call)
    for s in llm:
        out["calls"] += 1
        given = json.dumps(s["attributes"].get("llm", {}).get("input_messages", ""), ensure_ascii=False)
        if any(hint in given for hint in AGAIN):
            out["again"] += 1
        elif any(hint in given for hint in FORCED):
            out["forced"] += 1
    if llm:
        out["final"] = (llm[-1]["latencyMs"] or 0) / 1000

    def turn(span: dict) -> str | None:
        """The model call that made a tool call: the last one that started before it. (Parallel calls of one turn do not share
        a parent span: each runs in a node of its own.)"""
        before = [c for c in llm if c["startTime"] < span["startTime"]]
        return before[-1]["spanId"] if before else None

    rounds: set = set()
    for s in spans:
        if s["spanKind"] != "tool":
            continue
        name = s["name"]
        res = tool_result(s)
        total = res.get("total") if isinstance(res, dict) else None
        out["tools"].append((s["startTime"][11:19], name, (s.get("input") or {}).get("value", ""), res))
        if name == "search":
            rounds.add(turn(s))
            out["empty"] += total == 0 or (res.get("artifact") or {}).get("relevant") == []  # (none about the question)
        if name == "read_wiki" and isinstance(res, dict) and res.get("pieces"):
            out["reads"] += 1
        if isinstance(res, dict) and res.get("error"):
            out["errors"].append(f"{name}: {str(res['error'])[:60]}")
    out["rounds"] = len(rounds)
    return out


def show_trace(project: str, trace: str) -> None:
    s = summary(spans_of(project, trace))
    print(f"{s['when']}  {s['seconds']:.1f} s  «{s['question'][:100]}»  model calls {s['calls']}")
    for when, name, args, res in s["tools"]:
        if isinstance(res, dict):
            items = res.get("pieces") or res.get("messages") or res.get("rows") or []
            found = f"total {res.get('total', len(items))}" + (f", relevant {res['artifact']['relevant']}" if "relevant" in (res.get("artifact") or {}) else "") + (f", error: {res['error'][:70]}" if res.get("error") else "") + (f", {res['note'][:70]}" if res.get("note") else "")
        else:
            found = "(text)"
        print(f"  {when} {name}({args[:110]})\n{'':12}-> {found}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("n", nargs="?", type=int, default=50)
    ap.add_argument("--trace")
    ap.add_argument("--project", default="catix")
    args = ap.parse_args()
    project = project_id(args.project)
    if args.trace:
        return show_trace(project, args.trace)
    rows = []
    for trace in questions(project, args.n):
        try:
            rows.append((trace, summary(spans_of(project, trace))))
        except (KeyError, StopIteration, IndexError) as e:
            print(f"{trace}: not read ({type(e).__name__})", file=sys.stderr)
    print(f"{'when':16} {'s':>5} {'calls':>5} {'final':>5}  search rounds / empty / reads  forced  again  errors  question")
    for trace, s in rows:
        searched = "SCREENED" if s["screened"] else f"{s['rounds']}/{s['empty']}/{s['reads']}"
        print(f"{s['when']:16} {s['seconds']:5.1f} {s['calls']:5} {s['final']:5.1f}  {searched:29} {s['forced'] or '':>6} {s['again'] or '':>5} {len(s['errors']) or '':>6}  {s['question'][:60]!r}  {trace}")
    asked = [s for _, s in rows if not s["screened"]]
    if not asked:
        return
    secs = [s["seconds"] for s in asked]
    print(f"\n{len(rows)} questions, {len(rows) - len(asked)} stopped by the screen")
    print(f"time: median {statistics.median(secs):.1f} s, mean {statistics.mean(secs):.1f} s, max {max(secs):.1f} s; "
          f"model calls: median {statistics.median(s['calls'] for s in asked)}")
    print(f"the last model call: {sum(s['final'] for s in asked) / sum(secs):.0%} of all the time")
    loops = [s for s in asked if s["rounds"] >= 3]
    print(f"searched 3 rounds or more: {len(loops)}; a tool gave an error or a refusal: {sum(bool(s['errors']) for _, s in rows)}; "
          f"the guard made the report: {sum(bool(s['forced']) for _, s in rows)}; "
          f"asked again after a call written as text: {sum(bool(s['again']) for _, s in rows)}")
    errors = Counter(e.split(": ", 1)[1] for _, s in rows for e in s["errors"])
    for text, n in errors.most_common(6):
        print(f"  {n:3} × {text}")
    for _, s in rows:
        if s["screened"]:
            print(f"  screened: {s['when']} {s['question'][:90]!r}")


if __name__ == "__main__":
    main()
