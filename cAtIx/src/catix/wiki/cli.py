"""`catix-wiki`: the commands of the wiki.

    catix-wiki fetch [NAMESPACE ...]   # default: namespace 0 (articles); only pages whose revision changed are downloaded
    catix-wiki status                  # pages in the snapshot, redirects, pages missing on the wiki now
    catix-wiki sveden discover|triage|status|override   # all documents of innopolis.university/sveden (see sources/sveden.py)
    catix-wiki regs fetch|compile      # official regulations (PDF) as a second source, see sources/regulations.py
    catix-wiki rpd fetch|compile|status   # course programmes (РПД) from the archives of sveden/education, see sources/rpd.py
    catix-wiki sites fetch|compile|status   # campuslife.innopolis.ru, hotel.innopolis.university, see sources/sites.py
    catix-wiki papers fetch|compile|status  # past exam papers from the students' Notion database, see sources/pastpapers.py
    catix-wiki autopilot [--loop] [--source NAME ...] [--no-push] [--no-answers]   # the wiki maintains itself and commits to its branch (see autopilot.py)
    catix-wiki build [--offline]       # the whole chain, re-running only what changed (see build.py)
    catix-wiki agent [queue|all [FOLDER]|check [--two-sources]|links [--dry-run]|PATH ...]   # the wiki's agent keeps the knowledge cards (wiki/knowledge/), see agent.py and links.py
    catix-wiki graph                   # relations between concepts (prerequisites, teachers), see graph.py
    catix-wiki lint                    # check wiki/ against OKF v0.2
    catix-wiki index [status|--no-embed]   # the bundle in the database for the agent's search (see search_index.py)
    catix-wiki compile ...             # snapshot -> OKF bundle in wiki/ (see compile.py)

The code is laid out by what each part does:
    sources/       what the wiki is made from: each module asks one source what is new and brings it into raw/
                   (eduwiki, sveden: the site's documents, regulations: their PDFs and pages, rpd: course programmes, sites: the services' sites, pastpapers: past exams,
                   mock: a stand-in site); sources/__init__.py says how often each is asked
    compile.py     eduwiki snapshot -> pages (the model turns wikitext into markdown); also what every part shares
                   (the bundle's folder, the model client, front matter)
    graph.py       relations between pages (code; the model only resolves a prerequisite line to a course)
    agent.py       the wiki's agent (deepagents): reads the pages and keeps knowledge cards; code checks every card
    lint.py        OKF checks;  search_index.py, chunks.py: the bundle in the database for the agent's search
    build.py       the whole chain;  autopilot.py: the wiki's own run that commits to the `wiki` branch
"""

import sys

from catix.wiki.sources import eduwiki


def main() -> None:
    from catix.settings import settings

    settings.phoenix_project = settings.wiki_phoenix_project  # before tracing is set up: the wiki's traces go to a project of their own
    cmd, *args = sys.argv[1:] or ["status"]
    if cmd == "fetch":
        eduwiki.fetch([int(a) for a in args] or [0])
    elif cmd == "status":
        eduwiki.status()
    elif cmd == "sveden":
        from catix.wiki.sources import sveden

        sveden.main()
    elif cmd == "regs":
        from catix.wiki.sources import regulations

        regulations.main()
    elif cmd == "sites":
        from catix.wiki.sources import sites

        sites.main()
    elif cmd == "papers":
        from catix.wiki.sources import pastpapers

        pastpapers.main()
    elif cmd == "rpd":
        from catix.wiki.sources import rpd

        rpd.main()
    elif cmd == "autopilot":
        from catix.wiki import autopilot

        autopilot.main()
    elif cmd == "build":
        from catix.wiki import build

        build.main()
    elif cmd == "agent":
        from catix.wiki import agent

        agent.main()
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
