"""The whole chain, re-running only what changed.

    catix-wiki build [--offline] [--force] [--auto]

  fetch    new and changed pages of the wiki; the documents of innopolis.university/sveden, kept or skipped by the model (--offline: use what is downloaded)
  regs     regulations -> wiki/regulations (the text as it is; the model writes only the description)
  rpd      course programmes of the latest cohorts -> wiki/course-programmes (by code only)
  compile  pages whose revision is not in the bundle yet (the model)
  link     links between concepts, index.md
  graph    prerequisites, teachers, duplicates (the model only for lines it has not seen; answers are cached)
  topics   (--auto) guides for new documents, proposed by the model and accepted when every code check passes
  synth    guides whose evidence changed (--force: all)
  claims   which sentences of the guides rest on evidence that changed (wiki/.claims/)
  lint     the bundle against OKF v0.2; the exit code is 1 on errors
  index    (when DATABASE_URL is set and lint passed) the agent's search: pages and pieces that changed, their vectors
"""

import sys

from catix.wiki import compile as compiler
from catix.settings import settings
from catix.wiki import fetch, graph, lint, regulations, rpd, search_index, sveden, synth, topics


def main() -> None:
    args = sys.argv[2:]
    before = set(fetch.load_manifest().items() and {(k, v["revid"]) for k, v in fetch.load_manifest().items()})
    if "--offline" not in args:
        print("== fetch")
        fetch.fetch([0])
    changed = {(k, v["revid"]) for k, v in fetch.load_manifest().items()} - before
    print(f"== {len(changed)} pages new or changed in the snapshot")
    print("== regulations")
    if "--offline" not in args:
        sveden.discover()  # new documents on innopolis.university/sveden
        sveden.triage()  # the model decides about the documents it has not seen
        regulations.fetch()
        rpd.fetch()  # archives of course programmes not read yet
    regulations.compile_all()
    rpd.compile_all()
    print("== compile")
    compiler.compile_pages(None)
    print("== link")
    compiler.link()
    print("== graph")
    graph.main()
    if "--auto" in args:
        print("== topics")
        topics.propose(limit=8, auto=True)  # the model proposes guides for new documents; those that pass every check are accepted
    print("== synth")
    written = synth.run(force="--force" in args)
    print(f"== {written} guides written")
    print("== claims")
    stale = synth.check_claims(synth.Index())
    print(f"== {sum(1 for _, n in stale.values() if n != 0)} guides have sentences on changed evidence")
    print("== lint")
    errors = lint.lint()
    if errors or not settings.database_url:
        sys.exit(errors)  # a broken bundle does not reach the agent
    print("== index")
    counts = search_index.sync()
    print(", ".join(f"{v} {k}" for k, v in counts.items()))
    print(f"== {search_index.embed_all()} pieces embedded")
