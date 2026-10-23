"""The whole chain, re-running only what changed.

    catix-wiki build [--offline] [--force] [--auto]

  sources  (not with --offline) every source asks what is new or changed (sources/): the wiki, the documents of
           innopolis.university/sveden (kept or skipped by the model), the regulations, the course programmes
  regs     regulations -> wiki/regulations (the text as it is; the model writes only the description)
  rpd      course programmes of every cohort -> wiki/course-programmes (by code only)
  compile  pages whose revision is not in the bundle yet (the model)
  link     links between concepts, index.md
  graph    prerequisites, teachers, duplicates (the model only for lines it has not seen; answers are cached)
  topics   (--auto) guides for new documents, proposed by the model and accepted when every code check passes
  synth    guides whose evidence changed (--force: all)
  claims   which sentences of the guides rest on evidence that changed (wiki/.claims/)
  lint     the bundle against OKF v0.2; the exit code is 1 on errors
  index    (when DATABASE_URL is set and lint passed) the agent's search: pages and pieces that changed, their vectors

The wiki's own run (autopilot.py) calls `rebuild` after its sources found something and commits what it made.
"""

import sys
from dataclasses import dataclass, field

from catix.settings import settings
from catix.wiki import compile as compiler
from catix.wiki import graph, lint, search_index, sources, synth, topics
from catix.wiki.sources import regulations, rpd


@dataclass
class Report:
    """What one rebuild did and found: what the checks before a commit look at."""

    guides_written: int = 0
    stale_guides: list[str] = field(default_factory=list)  # guides with sentences on evidence that changed (or to be written again)
    review: list[str] = field(default_factory=list)  # guides written with `review:` (the model's draft failed the code check twice)
    lint_errors: int = 0
    index: dict[str, int] = field(default_factory=dict)
    agent: dict[str, int] = field(default_factory=dict)  # what the wiki's agent did with the cards (agent.py)


def rebuild(auto: bool = False, force: bool = False, topics_limit: int = 8) -> Report:
    """Everything after the sources: pages, links, graph, guides, checks and (when lint passed) the search index."""
    report = Report()
    print("== regulations")
    regulations.compile_all()
    print("== course programmes")
    rpd.compile_all()
    print("== compile")
    compiler.compile_pages(None)
    print("== link")
    compiler.link()
    print("== graph")
    graph.main()
    if auto:
        print("== topics")
        topics.propose(limit=topics_limit, auto=True)  # the model proposes guides for new documents; those that pass every check are accepted
        synth.load_accepted_topics()  # (synth read the accepted topics when it was imported: the new ones get their guide in this run)
    print("== synth")
    report.guides_written = synth.run(force=force)
    print(f"== {report.guides_written} guides written")
    print("== claims")
    stale = synth.check_claims(synth.Index())
    report.stale_guides = sorted(slug for slug, (_, n) in stale.items() if n != 0)
    report.review = synth.under_review()
    print(f"== {len(report.stale_guides)} guides have sentences on changed evidence, {len(report.review)} wait for review")
    print("== lint")
    report.lint_errors = lint.lint()
    if report.lint_errors or not settings.database_url:
        return report  # a broken bundle does not reach the agent
    print("== index")
    report.index = search_index.sync()
    print(", ".join(f"{v} {k}" for k, v in report.index.items()))
    print(f"== {search_index.embed_all()} pieces embedded")
    return report


def main() -> None:
    args = sys.argv[2:]
    if "--offline" not in args:
        for source in sources.SOURCES:
            print(f"== source {source.name}")
            source.update()
    report = rebuild(auto="--auto" in args, force="--force" in args)
    sys.exit(1 if report.lint_errors else 0)
