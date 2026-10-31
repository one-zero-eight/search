"""What the agent did with the last questions, from their traces in Phoenix: no question is asked again.

    uv run python experiments/trace_stats.py [N] [--trace ID] [--project NAME]

For each question (a `question` span): its time, the model calls of the supervisor and of each helper it asked, the tools
the helpers ran (search rounds, the empty ones, reads that gave text), the tool results that were an error or a refusal
("No more reading", a repeated call), the calls the guard made the report (its order to answer in the model's input), the
calls asked again after a tool call written as text (`again`), and how long the supervisor's last call took (it writes the answer again from the helper's report; `pass` when the one report was the answer, core.PassReportMiddleware). Then the totals: where the
time goes, how often a helper searched round after round, which questions the screen stopped.

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
SCREEN = ("С этим я помогать не буду", "I won't help with that", "Я помогаю только с вопросами", "I only help with questions")  # guardrail.REFUSALS


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
    """The JSON a tool gave the model, or None (a helper's report is text); its artifact, unseen by the model, as `artifact`."""
    try:
        out = json.loads((span.get("output") or {}).get("value") or "{}")
        data = out["update"]["messages"][0]["data"] if "update" in out else {"content": out}
        content = json.loads(data["content"]) if isinstance(data["content"], str) else data["content"]
        return {**content, "artifact": data["artifact"]} if isinstance(content, dict) and data.get("artifact") else content
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def summary(spans: list[dict]) -> dict:
    by_id = {s["spanId"]: s for s in spans}

    def helper(span: dict) -> str:
        """The helper a span ran in (the ask_* tool above it), or 'supervisor'."""
        while span.get("parentId") in by_id:
            span = by_id[span["parentId"]]
            if span["spanKind"] == "tool" and span["name"].startswith("ask_"):
                return span["name"][4:]
        return "supervisor"

    root = next((s for s in spans if s["name"] == "question"), spans[0])
    answer = ((root.get("output") or {}).get("value") or "")
    out = {"when": root["startTime"][:16].replace("T", " "), "question": (root.get("input") or {}).get("value") or "",
           "seconds": (root["latencyMs"] or 0) / 1000, "screened": answer.startswith(SCREEN), "helpers": Counter(),
           "calls": Counter(), "rounds": Counter(), "empty": Counter(), "reads": Counter(), "errors": [], "forced": Counter(),
           "again": Counter(), "final": 0.0, "tools": []}
    llm = [s for s in spans if s["spanKind"] == "llm" and s["name"] != "guardrail"]
    for s in llm:
        if helper(s) == "supervisor" and any(p["name"] == "guardrail" for p in _parents(s, by_id)):
            continue  # (the screen's own call)
        who = helper(s)
        out["calls"][who] += 1
        given = json.dumps(s["attributes"].get("llm", {}).get("input_messages", ""), ensure_ascii=False)
        if any(hint in given for hint in AGAIN):
            out["again"][who] += 1
        elif any(hint in given for hint in FORCED):
            out["forced"][who] += 1
    sup = [s for s in llm if helper(s) == "supervisor" and not any(p["name"] == "guardrail" for p in _parents(s, by_id))]
    asks = [s for s in spans if s["spanKind"] == "tool" and s["name"].startswith("ask_") and helper(s) == "supervisor"]
    out["passed"] = bool(sup and asks and sup[-1]["startTime"] < asks[-1]["startTime"])  # no model call after the report
    if sup and not out["passed"]:
        out["final"] = (sup[-1]["latencyMs"] or 0) / 1000
    rounds: dict[str, set] = {}
    for s in spans:
        if s["spanKind"] != "tool":
            continue
        who, name = helper(s), s["name"]
        if name.startswith("ask_"):
            out["helpers"][name[4:]] += 1
            continue
        res = tool_result(s)
        total = res.get("total") if isinstance(res, dict) else None
        out["tools"].append((s["startTime"][11:19], who, name, (s.get("input") or {}).get("value", ""), res))
        if name.startswith("search_"):
            rounds.setdefault(who, set()).add(s["parentId"])  # (the calls of one model turn share the tools node)
            out["empty"][who] += total == 0 or (res.get("artifact") or {}).get("relevant") == []  # (none about the question)
        if name == "read_wiki" and isinstance(res, dict) and res.get("pieces"):
            out["reads"][who] += 1
        if isinstance(res, dict) and res.get("error"):
            out["errors"].append(f"{who}/{name}: {str(res['error'])[:60]}")
    out["rounds"] = Counter({who: len(parents) for who, parents in rounds.items()})
    return out


def _parents(span: dict, by_id: dict) -> list[dict]:
    out = []
    while span.get("parentId") in by_id:
        span = by_id[span["parentId"]]
        out.append(span)
    return out


def show_trace(project: str, trace: str) -> None:
    s = summary(spans_of(project, trace))
    print(f"{s['when']}  {s['seconds']:.1f} s  «{s['question'][:100]}»  model calls {dict(s['calls'])}")
    for when, who, name, args, res in s["tools"]:
        if isinstance(res, dict):
            items = res.get("pieces") or res.get("messages") or res.get("rows") or []
            found = f"total {res.get('total', len(items))}" + (f", relevant {res['artifact']['relevant']}" if "relevant" in (res.get("artifact") or {}) else "") + (f", error: {res['error'][:70]}" if res.get("error") else "") + (f", {res['note'][:70]}" if res.get("note") else "")
        else:
            found = "(text)"
        print(f"  {when} {who:>10} {name}({args[:110]})\n{'':22}-> {found}")


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
    print(f"{'when':16} {'s':>5} {'calls':>5} {'final':>5}  helpers (model calls / search rounds, empty / reads)  forced  again  errors  question")
    for trace, s in rows:
        helpers = " ".join(f"{h}{'×' + str(k) if k > 1 else ''}:{s['calls'][h]}/{s['rounds'][h]},{s['empty'][h]}/{s['reads'][h]}"
                           for h, k in s["helpers"].items()) or ("SCREENED" if s["screened"] else "-")
        forced, again = sum(s["forced"].values()), sum(s["again"].values())
        final = " pass" if s["passed"] else f"{s['final']:5.1f}"
        print(f"{s['when']:16} {s['seconds']:5.1f} {sum(s['calls'].values()):5} {final}  {helpers:44} {forced or '':>6} {again or '':>5} {len(s['errors']) or '':>6}  {s['question'][:60]!r}  {trace}")
    asked = [s for _, s in rows if not s["screened"]]
    if not asked:
        return
    secs = [s["seconds"] for s in asked]
    one = [s for s in asked if sum(s["helpers"].values()) == 1]
    print(f"\n{len(rows)} questions, {len(rows) - len(asked)} stopped by the screen")
    print(f"time: median {statistics.median(secs):.1f} s, mean {statistics.mean(secs):.1f} s, max {max(secs):.1f} s; "
          f"model calls: median {statistics.median(sum(s['calls'].values()) for s in asked)}")
    passed = sum(s["passed"] for s in asked)
    rewritten = [s for s in one if not s["passed"]]
    print(f"the supervisor's last call: {sum(s['final'] for s in asked) / sum(secs):.0%} of all the time; {len(one)} questions asked "
          f"one helper only, {passed} answered with its report" + (f", {len(rewritten)} rewritten ({statistics.mean(s['final'] for s in rewritten):.1f} s each)" if rewritten else ""))
    again = [s for s in asked if any(k > 1 for k in s["helpers"].values())]
    print(f"the supervisor asked one helper again: {len(again)} questions ({statistics.mean(s['seconds'] for s in again):.1f} s each)" if again else "")
    loops = [(t, s) for t, s in rows if any(n >= 3 for n in s["rounds"].values())]
    print(f"a helper searched 3 rounds or more: {len(loops)}; a tool gave an error or a refusal: {sum(bool(s['errors']) for _, s in rows)}; "
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
