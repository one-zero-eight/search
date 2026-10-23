"""`catix-wiki`: the commands of the wiki.

    catix-wiki fetch [NAMESPACE ...]   # default: namespace 0 (articles); only pages whose revision changed are downloaded
    catix-wiki status                  # pages in the snapshot, redirects, pages missing on the wiki now
    catix-wiki sveden discover|triage|status|override   # all documents of innopolis.university/sveden (see sources/sveden.py)
    catix-wiki topics [list|accept|reject]   # the model proposes guides, a person accepts them (see topics.py)
    catix-wiki regs fetch|compile      # official regulations (PDF) as a second source, see sources/regulations.py
    catix-wiki rpd fetch|compile|status   # course programmes (РПД) from the archives of sveden/education, see sources/rpd.py
    catix-wiki autopilot [--loop] [--source NAME ...] [--no-push] [--no-answers]   # the wiki maintains itself and commits to its branch (see autopilot.py)
    catix-wiki build [--offline] [--force] [--auto]   # the whole chain, re-running only what changed (see build.py)
    catix-wiki synth [TOPIC ...]       # guides that combine many concepts (wiki/guides/), see synth.py
    catix-wiki graph                   # relations between concepts (prerequisites, teachers), see graph.py
    catix-wiki lint                    # check wiki/ against OKF v0.2
    catix-wiki index [status|--no-embed]   # the bundle in the database for the agent's search (see search_index.py)
    catix-wiki compile ...             # snapshot -> OKF bundle in wiki/ (see compile.py)

The code is laid out by what each part does:
    sources/       what the wiki is made from: each module asks one source what is new and brings it into raw/
                   (eduwiki, sveden: the site's documents, regulations: their PDFs and pages, rpd: course programmes,
                   mock: a stand-in site); sources/__init__.py says how often each is asked
    compile.py     eduwiki snapshot -> pages (the model turns wikitext into markdown); also what every part shares
                   (the bundle's folder, the model client, front matter)
    graph.py       relations between pages (code; the model only resolves a prerequisite line to a course)
    topics.py      which guides the wiki needs (the model proposes, code checks, a person or the run accepts)
    synth.py       guides from numbered evidence (the model writes, code checks every citation and number)
    lint.py        OKF checks;  search_index.py, chunks.py: the bundle in the database for the agent's search
    build.py       the whole chain;  autopilot.py: the wiki's own run that commits to the `wiki` branch
"""

import sys

from catix.wiki.sources import eduwiki


def main() -> None:
    cmd, *args = sys.argv[1:] or ["status"]
    if cmd == "fetch":
        eduwiki.fetch([int(a) for a in args] or [0])
    elif cmd == "status":
        eduwiki.status()
    elif cmd == "sveden":
        from catix.wiki.sources import sveden

        sveden.main()
    elif cmd == "topics":
        from catix.wiki import topics

        topics.main()
    elif cmd == "regs":
        from catix.wiki.sources import regulations

        regulations.main()
    elif cmd == "rpd":
        from catix.wiki.sources import rpd

        rpd.main()
    elif cmd == "autopilot":
        from catix.wiki import autopilot

        autopilot.main()
    elif cmd == "build":
        from catix.wiki import build

        build.main()
    elif cmd == "synth":
        from catix.wiki import synth

        synth.main()
    elif cmd == "graph":
        from catix.wiki import graph

        graph.main()
    elif cmd == "lint":
        from catix.wiki import lint

        lint.main()
    elif cmd == "index":
        from catix.wiki import search_index

        search_index.main()
    elif cmd in {"compile", "link"}:
        from catix.wiki import compile as compiler

        compiler.main([cmd] + args if cmd == "link" else args)
    else:
        raise SystemExit(__doc__)
