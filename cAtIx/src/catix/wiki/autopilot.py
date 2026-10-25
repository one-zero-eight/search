"""The wiki maintains itself: its sources are asked on their schedule, what changed becomes pages and knowledge cards, checks decide,
and the result is committed to the `wiki` branch and pushed.

    catix-wiki autopilot [--loop] [--source NAME ...] [--no-push] [--no-answers]
    catix-wiki autopilot accept    # a person read the review branch and agrees: the changes are committed to `wiki` and pushed
    catix-wiki autopilot discard   # a person disagrees: the changes are thrown away, the search index follows the branch again

One run:
  1. the sources that are due (sources/, each with its own interval; `--source` asks the named ones now, e.g. when
     something tells the wiki that a source changed);
  2. if one brought something, or the data still has changes an earlier run could not commit: build.rebuild(), then the
     wiki's agent on the pages that changed (agent.py);
  3. the checks: lint without errors, every card holds against the pages, the search finds the answers of
     quality.py (hit@5 >= settings.wiki_min_hit5), the agent answers tests/test_docs_answers.py (a failed test once more);
  4. a commit in the checkout of the `wiki` branch (settings.wiki_root), where only wiki/ and raw/ may change. All checks
     passed: pushed to `wiki`. One failed: the same changes go to a branch `wiki-review/<time>` for a person, and `wiki`
     stays as it was; the working tree keeps them, and the next run checks them again together with what is new.
Runs one at a time (a lock file). Its state (when each source was asked, the changes last sent for review) is in
.autopilot.json next to the data, not committed.
"""

import fcntl
import json
import os
import subprocess
import sys
import time
import traceback
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from catix.settings import settings
from catix.wiki import build, quality, sources
from catix.wiki.paths import DATA, REPO

ALLOWED = ("wiki/", "raw/")  # the only paths a commit of the wiki's own run may touch
STATE = DATA / ".autopilot.json"
LOCK = DATA / ".autopilot.lock"
AUTHOR = {"GIT_AUTHOR_NAME": "cAtIx wiki", "GIT_AUTHOR_EMAIL": "wiki@catix.invalid", "GIT_COMMITTER_NAME": "cAtIx wiki", "GIT_COMMITTER_EMAIL": "wiki@catix.invalid"}
IDLE = timedelta(minutes=15)  # the longest sleep of --loop between two looks at the schedule


def git(*args: str, check: bool = True) -> str:
    out = subprocess.run(["git", "-C", str(DATA), *args], capture_output=True, text=True, env={**os.environ, **AUTHOR})
    if check and out.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {out.stderr.strip()}")
    return out.stdout.strip()


def load_state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}


def save_state(state: dict) -> None:
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def due(state: dict, now: datetime) -> list[sources.Source]:
    asked = state.get("asked", {})
    return [s for s in sources.SOURCES if s.name not in asked or now - datetime.fromisoformat(asked[s.name]) >= s.every]


def outside(paths: list[str]) -> list[str]:
    """Paths a commit of the wiki's run must not touch (code, configuration: everything but the data)."""
    return [p for p in paths if not p.startswith(ALLOWED)]


def summary(name_status: str) -> str:
    """'wiki/regulations: 3 new, 2 changed' from `git diff --name-status`."""
    words = {"A": "new", "M": "changed", "D": "removed", "R": "renamed"}
    by = Counter()
    for line in name_status.splitlines():
        status, *paths = line.split("\t")
        folder = "/".join(paths[-1].split("/")[:2]) if paths[-1].count("/") > 1 else paths[-1]
        by[folder, words.get(status[:1], status)] += 1
    folders = dict.fromkeys(f for f, _ in sorted(by))
    return "\n".join(f"{f}: " + ", ".join(f"{n} {w}" for (g, w), n in sorted(by.items()) if g == f) for f in folders)


@dataclass
class Checks:
    failed: list[str] = field(default_factory=list)
    passed: list[str] = field(default_factory=list)

    def add(self, ok: bool, text: str) -> None:
        (self.passed if ok else self.failed).append(text)


def answers_pass() -> bool:
    """tests/test_docs_answers.py against the real agent; a failed test gets one more try (the model is not deterministic)."""
    test = ["uv", "run", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_docs_answers.py"]
    env = {**os.environ, "WIKI_ROOT": str(DATA)}
    first = subprocess.run(test, cwd=REPO, capture_output=True, text=True, env=env)
    if first.returncode == 0:
        return True
    failed = [line.split(" ")[1] for line in first.stdout.splitlines() if line.startswith("FAILED ")]
    return bool(failed) and subprocess.run([*test[:-1], *failed], cwd=REPO, capture_output=True, text=True, env=env).returncode == 0


def check(report: build.Report, answers: bool) -> Checks:
    checks = Checks()
    checks.add(report.lint_errors == 0, f"lint: {report.lint_errors} errors")
    if not settings.database_url:
        checks.add(False, "search: not checked (no DATABASE_URL)")
        return checks
    if report.lint_errors:
        return checks  # (the index was not updated: the search and the answers would check the old bundle)
    score = quality.score()
    checks.add(score.hit5 >= settings.wiki_min_hit5, f"search: hit@5 {score.hit5:.0%} (at least {settings.wiki_min_hit5:.0%}), hit@10 {score.hit10:.0%}"
               + (f"; not found: {'; '.join(score.missed[:5])}" if score.missed else ""))
    if answers:
        checks.add(answers_pass(), "answers: tests/test_docs_answers.py")
    if report.agent:
        broken = report.agent.get("cards broken", 0)
        checks.add(broken == 0, f"cards: {report.agent.get('cards written', 0)} written, {broken} do not hold against the pages (catix-wiki agent check)")
    return checks


def changed_pages() -> list[str]:
    """Source pages the run added or changed ('/regulations/x.md'), from git: what the wiki's agent reads next."""
    out = []
    for line in git("status", "--porcelain", "-uall", "--", "wiki").splitlines():  # (-uall: a new folder is its files, not one line)
        status, path = line[:2], line[3:].split(" -> ")[-1].strip('"')
        if "D" in status or not path.endswith(".md") or path.startswith("wiki/knowledge/") or path.rsplit("/", 1)[-1] in {"index.md", "log.md"}:
            continue
        out.append("/" + path.removeprefix("wiki/"))
    return out


def keep_cards(report: build.Report) -> None:
    """The wiki's agent on the pages that changed (and on those still queued from earlier runs), then the cards into the index."""
    from catix.wiki import agent, lint, search_index

    print(f"== agent: {agent.enqueue(changed_pages())} changed pages queued, {len(agent.load_queue())} in the queue", flush=True)
    if not agent.load_queue() and not agent.check_all():
        return
    report.agent = agent.run()
    print(f"== agent: {report.agent}", flush=True)
    report.lint_errors = lint.lint()
    if not report.lint_errors and settings.database_url:
        search_index.sync()
        search_index.embed_all()


def run_once(names: list[str] | None = None, push: bool = True, answers: bool = True) -> str:
    """One run; what it did, in a line."""
    state, now = load_state(), datetime.now(timezone.utc)
    asked = [s for s in sources.SOURCES if s.name in names] if names else due(state, now)
    changed: dict[str, int] = {}
    for source in asked:
        print(f"== source {source.name}: {source.about}", flush=True)
        try:
            changed[source.name] = source.update()
        except Exception:  # noqa: BLE001 - one source failing must not stop the others; it is asked again next time
            traceback.print_exc()
            continue
        state.setdefault("asked", {})[source.name] = now.isoformat(timespec="seconds")
        save_state(state)
    from catix.wiki import agent

    waiting = settings.wiki_agent and bool(agent.load_queue())
    if not any(changed.values()) and not git("status", "--porcelain") and not waiting:
        return f"nothing new ({', '.join(s.name for s in asked) or 'no source due'})"
    if not any(changed.values()) and state.get("review_tree") and working_tree() == state["review_tree"]:
        return "nothing new; changes wait for review (catix-wiki autopilot accept | discard)"
    report = build.rebuild()
    if settings.wiki_agent and not report.lint_errors:
        keep_cards(report)
    git("add", "-A")
    staged = git("diff", "--cached", "--name-only").splitlines()
    if not staged:
        return "sources changed, the wiki did not"
    if bad := outside(staged):
        git("reset", "-q")
        raise RuntimeError(f"the run changed paths outside the data, nothing committed: {bad[:5]}")
    checks = check(report, answers)
    found = ", ".join(f"{k} {v}" for k, v in changed.items() if v) or "changes left by an earlier run"
    message = (f"wiki: {found}\n\n{summary(git('diff', '--cached', '--name-status'))}\n\nChecks:\n"
               + "\n".join([*(f"- FAILED {c}" for c in checks.failed), *(f"- {c}" for c in checks.passed)]))
    if not checks.failed:
        git("commit", "-q", "-m", message)
        if push and settings.wiki_push:
            git("push", "-q", settings.wiki_remote, f"HEAD:{settings.wiki_branch}")
        state.pop("review_tree", None)
        save_state(state)
        return f"committed {git('rev-parse', '--short', 'HEAD')}: {len(staged)} files" + (" and pushed" if push and settings.wiki_push else "")
    tree = git("write-tree")
    git("reset", "-q")  # (the working tree keeps the changes; `wiki` does not get them)
    if state.get("review_tree") == tree:
        return "the same changes as last time failed the checks again: " + "; ".join(checks.failed)
    commit = git("commit-tree", tree, "-p", "HEAD", "-m", message)
    branch = f"wiki-review/{now:%Y%m%d-%H%M}"
    git("update-ref", f"refs/heads/{branch}", commit)
    if push and settings.wiki_push:
        git("push", "-q", settings.wiki_remote, f"{commit}:refs/heads/{branch}")
    state["review_tree"] = tree
    save_state(state)
    return f"checks failed, changes sent to {branch} for review: " + "; ".join(checks.failed)


def working_tree() -> str:
    """The tree the working state would commit, without committing it."""
    git("add", "-A")
    try:
        return git("write-tree")
    finally:
        git("reset", "-q")


def accept(push: bool = True) -> str:
    """The changes waiting for review, committed to `wiki` as a person accepted them."""
    git("add", "-A")
    if bad := outside(git("diff", "--cached", "--name-only").splitlines()):
        git("reset", "-q")
        return f"paths outside the data changed, nothing committed: {bad[:5]}"
    if not git("diff", "--cached", "--name-only"):
        return "nothing waits for review"
    git("commit", "-q", "-m", f"wiki: accepted after review\n\n{summary(git('diff', '--cached', '--name-status'))}")
    if push and settings.wiki_push:
        git("push", "-q", settings.wiki_remote, f"HEAD:{settings.wiki_branch}")
    state = load_state()
    state.pop("review_tree", None)
    save_state(state)
    return f"committed {git('rev-parse', '--short', 'HEAD')}"


def discard() -> str:
    """The changes waiting for review, thrown away: the files of the branch come back (downloads, which git ignores, stay) and
    the search index follows them."""
    git("checkout", "--", ".")
    git("clean", "-fdq", "--", *ALLOWED)  # (new pages of the run; ignored files are not touched without -x)
    state = load_state()
    state.pop("review_tree", None)
    save_state(state)
    if settings.database_url:
        from catix.wiki import search_index

        search_index.sync()
    return "changes thrown away"


def ready() -> str | None:
    """Why the run cannot work here, or None: the data must be a checkout of the `wiki` branch, not the code."""
    if settings.wiki_root is None:
        return "WIKI_ROOT is not set: the wiki's run writes to a checkout of the `wiki` branch (DEPLOY.md, section 2a)"
    try:
        branch = git("rev-parse", "--abbrev-ref", "HEAD")
    except RuntimeError as e:
        return f"{DATA} is not a git checkout: {e}"
    if branch != settings.wiki_branch:
        return f"{DATA} is on branch {branch}, not {settings.wiki_branch}"
    return None


def main() -> None:
    args = sys.argv[2:]
    if problem := ready():
        sys.exit(problem)
    if args[:1] in (["accept"], ["discard"]):
        print(accept("--no-push" not in args) if args[0] == "accept" else discard())
        return
    names = [a for a in args[args.index("--source") + 1:] if not a.startswith("--")] if "--source" in args else None
    with LOCK.open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            sys.exit("another run of the wiki is going on")
        while True:
            started = datetime.now(timezone.utc)
            try:
                print(f"[{started:%Y-%m-%d %H:%M}] {run_once(names, push='--no-push' not in args, answers='--no-answers' not in args)}", flush=True)
            except Exception:  # noqa: BLE001 - the loop keeps going; the next run tries again
                traceback.print_exc()
            if "--loop" not in args:
                return
            names = None  # (--source asks now; the loop then follows the schedule)
            state = load_state()
            waits = [datetime.fromisoformat(state["asked"][s.name]) + s.every - datetime.now(timezone.utc) for s in sources.SOURCES if s.name in state.get("asked", {})]
            time.sleep(max(60.0, min([IDLE, *waits]).total_seconds()))
