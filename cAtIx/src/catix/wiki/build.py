"""The whole chain, re-running only what changed.

    catix-wiki build [--offline]

  sources  (not with --offline) every source asks what is new or changed (sources/): the wiki, the documents of
           innopolis.university/sveden (kept or skipped by the model), the regulations, the course programmes
  regs     regulations -> wiki/regulations (the text as it is; the model writes only the description)
  rpd      course programmes of every cohort -> wiki/course-programmes (by code only)
  sites    pages of the services' sites -> wiki/sites (the text as it is; the model writes only the description)
  papers   past exam papers -> wiki/past-papers, one page per subject (by code only)
  compile  pages whose revision is not in the bundle yet (the model)
  link     links between concepts, index.md
  graph    prerequisites, teachers, duplicates (the model only for lines it has not seen; answers are cached)
  lint     the bundle against OKF v0.2; the exit code is 1 on errors
  index    (when DATABASE_URL is set and lint passed) the agent's search: pages and pieces that changed, their vectors

The wiki's own run (autopilot.py) calls `rebuild` after its sources found something, then the wiki's agent keeps the
knowledge cards (agent.py), and commits what they made.
"""

import sys
from dataclasses import dataclass, field

from catix.settings import settings
from catix.wiki import compile as compiler
from catix.wiki import graph, lint, search_index, sources
from catix.wiki.sources import pastpapers, regulations, rpd, sites


@dataclass
class Report:
    """What one rebuild did and found: what the checks before a commit look at."""

    lint_errors: int = 0
    index: dict[str, int] = field(default_factory=dict)
    agent: dict[str, int] = field(default_factory=dict)  # what the wiki's agent did with the cards (agent.py)


def rebuild() -> Report:
    """Everything after the sources: pages, links, graph, checks and (when lint passed) the search index."""
    report = Report()
    print("== regulations")
    regulations.compile_all()
    print("== course programmes")
    rpd.compile_all()
    print("== sites")
    sites.compile_all()
    print("== past papers")
    pastpapers.compile_all()
    print("== compile")
    compiler.compile_pages(None)
    print("== link")
    compiler.link()
    print("== graph")
    graph.main()
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
    report = rebuild()
    sys.exit(1 if report.lint_errors else 0)
