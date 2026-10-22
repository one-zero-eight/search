"""The whole chain, re-running only what changed.

    catix-wiki build [--offline] [--force]

  fetch    new and changed pages of the wiki, and the regulation PDFs (--offline: use what is downloaded)
  regs     regulations -> wiki/regulations (the text as it is; the model writes only the description)
  compile  pages whose revision is not in the bundle yet (the model)
  link     links between concepts, index.md
  graph    prerequisites, teachers, duplicates (the model only for lines it has not seen; answers are cached)
  synth    guides whose evidence changed (--force: all)
  lint     the bundle against OKF v0.2; the exit code is 1 on errors
"""

import sys

from catix.wiki import compile as compiler
from catix.wiki import fetch, graph, lint, regulations, synth


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
        regulations.fetch()
    regulations.compile_all()
    print("== compile")
    compiler.compile_pages(None)
    print("== link")
    compiler.link()
    print("== graph")
    graph.main()
    print("== synth")
    written = synth.run(force="--force" in args)
    print(f"== {written} guides written")
    print("== lint")
    sys.exit(lint.lint())
