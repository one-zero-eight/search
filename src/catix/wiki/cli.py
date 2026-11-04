"""`catix-wiki`: the commands of the wiki.

    catix-wiki fetch [NAMESPACE ...]   # default: namespace 0 (articles); only pages whose revision changed are downloaded
    catix-wiki status                  # pages in the snapshot, redirects, pages missing on the wiki now
    catix-wiki sveden discover|triage|status|override   # all documents of innopolis.university/sveden (see sources/sveden.py)
    catix-wiki regs fetch|compile      # official regulations (PDF) as a second source, see sources/regulations.py
    catix-wiki rpd fetch|compile|status   # course programmes (РПД) from the archives of sveden/education, see sources/rpd.py
    catix-wiki sites fetch [SITE ...]|compile|status   # the sites of the university, its services and the city, see sources/sites.py
    catix-wiki papers fetch|compile|status  # past exam papers from the students' Notion database, see sources/pastpapers.py
    catix-wiki autopilot [--loop] [--source NAME ...] [--no-push] [--no-answers]   # the wiki maintains itself and commits to its branch (see autopilot.py)
    catix-wiki build [--offline]       # the whole chain, re-running only what changed (see build.py)
    catix-wiki agent [queue|all [FOLDER]|check [--two-sources]|links|candidates|notes|PATH ...]   # the cards (agent.py), the links (links.py), the notes of the pages (notes.py)
    catix-wiki graph                   # relations between concepts (prerequisites, teachers), see graph.py
    catix-wiki lint                    # check wiki/ against OKF v0.2
    catix-wiki index [status|--no-embed]   # the bundle in the database for the agent's search (see search_index.py)
    catix-wiki compile ...             # snapshot -> OKF bundle in wiki/ (see compile.py)
    catix-wiki layout [--dry-run]      # the documents into wiki/raw/, every path that led to them with them (see layout.py)

The bundle (paths.py): wiki/raw/ holds the documents, written by code and never by the model; wiki/notes/ the model's notes
on single documents; every other folder is the model's: knowledge/ (cards of subjects) and the folders it makes for the
entities the documents name (people/, positions/, units/, ...), declared in wiki/folders.json.

The code is laid out by what each part does:
    sources/       what the wiki is made from: each module asks one source what is new and brings it into raw/
                   (eduwiki, sveden: the site's documents, regulations: their PDFs and pages, rpd: course programmes, sites: the services' sites, pastpapers: past exams,
                   mock: a stand-in site); sources/__init__.py says how often each is asked
    compile.py     eduwiki snapshot -> pages (the model turns wikitext into markdown); also what every part shares
                   (the bundle's folder, the model client, front matter)
    graph.py       relations between pages (code; the model only resolves a prerequisite line to a course)
    agent.py       the wiki's agent (deepagents): reads the documents and keeps the cards of subjects and of entities;
                   code checks every card;  layout.py: the move of the documents into wiki/raw/
    lint.py        OKF checks;  search_index.py, chunks.py: the bundle in the database for the agent's search
    build.py       the whole chain;  autopilot.py: the wiki's own run that commits to the `wiki` branch
"""

import argparse
import sys
from pathlib import Path


def positive(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="catix-wiki", description="Read sources, build and maintain the wiki.", allow_abbrev=False,
                                   epilog="Data: WIKI_ROOT/raw and WIKI_ROOT/wiki. WIKI_ROOT is required: a checkout of the `wiki` branch, not the code.")
    commands = root.add_subparsers(dest="command")
    root.set_defaults(command="status")

    def command(parent, name, help):
        child = parent.add_parser(name, help=help, description=help, allow_abbrev=False)
        child.set_defaults(_parser=child)
        return child

    command(commands, "fetch", "Download changed eduwiki pages").add_argument("namespaces", nargs="*", type=int, metavar="NAMESPACE")
    command(commands, "status", "Show the eduwiki snapshot")

    for name, about, default, actions in (
        ("sveden", "University disclosure documents", "status", ("discover", "triage", "status", "override")),
        ("regs", "Official regulations", None, ("fetch", "compile", "reextract", "refresh")),
        ("rpd", "Course programmes", "status", ("fetch", "compile", "refresh", "status")),
        ("papers", "Past exam papers", "status", ("fetch", "compile", "status")),
        ("sites", "University and city sites", "status", ("fetch", "new", "compile", "status", "docs", "discover", "explore", "add", "review", "accept", "approve", "reject", "migrate")),
    ):
        group = command(commands, name, about)
        actions_parser = group.add_subparsers(dest="action", required=default is None)
        group.set_defaults(action=default)
        for action in actions:
            leaf = command(actions_parser, action, f"{action.capitalize()} {about.lower()}")
            if name == "sveden" and action == "triage":
                leaf.add_argument("--redo", action="store_true", help="Triage documents again")
            elif name == "sveden" and action == "override":
                leaf.add_argument("decision", choices=("keep", "skip"))
                leaf.add_argument("ids", nargs="+", metavar="ID")
            elif name == "regs" and action == "fetch":
                leaf.add_argument("limit", nargs="?", type=positive, metavar="N", help="At most N new documents")
                leaf.add_argument("--no-ocr", action="store_true", help="Read text layers only; queue scans for a run with OCR")
            elif name == "rpd" and action in ("fetch", "compile"):
                leaf.add_argument("--all-years", action="store_const", const=True, default=None, help="Include every cohort")
                if action == "fetch":
                    leaf.add_argument("--limit", type=positive)
            elif name == "sites":
                if action == "fetch":
                    leaf.add_argument("names", nargs="*", metavar="SITE")
                    leaf.add_argument("--only-new", action="store_true", help="Fetch only uncached trusted-provider page links")
                elif action == "new":
                    leaf.add_argument("names", nargs="*", metavar="SITE")
                elif action == "discover":
                    leaf.add_argument("--dry-run", action="store_true", help="Probe, but write nothing")
                    leaf.add_argument("--all", action="store_true", help="Probe every candidate, retry failed and closed hosts now")
                elif action == "explore":
                    leaf.add_argument("--rounds", type=positive, default=10, help="Maximum rounds (default: 10)")
                    leaf.add_argument("--max-sites", type=positive, default=60, help="Stop after a round reaches this many new sites (default: 60)")
                elif action == "add":
                    leaf.add_argument("addresses", nargs="+", metavar="HOST_OR_URL")
                elif action == "migrate":
                    leaf.add_argument("--from", dest="source", type=Path, help="Old sites.yaml; used only when the data catalog is absent")
                elif action in ("accept", "approve", "reject"):
                    selection = leaf.add_mutually_exclusive_group(required=True)
                    selection.add_argument("names", nargs="*", metavar="HOST_OR_NAME")
                    selection.add_argument("--all", action="store_true", help="All pending sites" + (" and closed sites" if action == "reject" else ""))

    pilot = command(commands, "autopilot", "Run, accept or discard wiki updates")
    pilot.add_argument("action", nargs="?", choices=("run", "accept", "discard"), default="run")
    pilot.add_argument("--source", nargs="+", action="extend", metavar="NAME", help="Sources to ask now; may be repeated")
    for flag, help in (("loop", "Keep running on the source schedule"), ("only-new", "Read only pending sites"),
                       ("build", "Build existing data without fetching sources"), ("no-push", "Do not push commits"),
                       ("no-answers", "Skip answer checks")):
        pilot.add_argument("--" + flag, action="store_true", help=help)

    command(commands, "build", "Rebuild the entire wiki").add_argument("--offline", action="store_true", help="Do not fetch sources")
    agent = command(commands, "agent", "Maintain cards, links and notes (agent /PATH ... also works)")
    actions = agent.add_subparsers(dest="action")
    agent.set_defaults(action="queue")
    command(actions, "queue", "Process the card queue")
    command(actions, "all", "Enqueue source pages").add_argument("folders", nargs="*", metavar="FOLDER")
    command(actions, "run", "Process selected source pages").add_argument("pages", nargs="+", metavar="PATH")
    command(actions, "check", "Check every card").add_argument("--two-sources", action="store_true", help="Require two source pages")
    command(actions, "links", "Regenerate links between cards").add_argument("--dry-run", action="store_true", help="Write nothing")
    candidates = command(actions, "candidates", "Report subjects named in multiple documents")
    candidates.add_argument("--output", type=Path, help="JSON report path")
    candidates.add_argument("--folders", help="Comma-separated document folders to skip")
    notes = command(actions, "notes", "Write or check notes of source pages")
    notes.add_argument("pages", nargs="*", metavar="PATH")
    mode = notes.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Check existing notes")
    mode.add_argument("--link", action="store_true", help="Regenerate page-to-note links")
    notes.add_argument("--measure", action="store_true", help="Measure retrieval before and after writing notes")

    command(commands, "graph", "Derive relations between concepts").add_argument("--no-model", action="store_true", help="Do not ask the model")
    command(commands, "lint", "Validate the OKF bundle")
    command(commands, "layout", "Move source documents into wiki/raw").add_argument("--dry-run", action="store_true", help="Write nothing")
    index = command(commands, "index", "Sync, inspect or transfer the search index")
    index.add_argument("action", nargs="?", choices=("sync", "status", "export", "import"), default="sync")
    index.add_argument("file", nargs="?", type=Path, help="Export/import file")
    index.add_argument("--no-embed", action="store_true", help="Sync without embedding")

    compile_ = command(commands, "compile", "Compile eduwiki pages or rebuild links (compile link)")
    mode = compile_.add_mutually_exclusive_group()
    mode.add_argument("--sample", action="store_true", help="Compile the sample pages")
    mode.add_argument("--random", type=positive, metavar="N", help="Compile N random pages")
    mode.add_argument("--all", action="store_true", help="Compile all changed pages")
    compile_.add_argument("pages", nargs="*", metavar="PAGE")
    command(commands, "link", "Rebuild bundle indexes (alias for compile link)")
    return root


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    words = list(sys.argv[1:] if argv is None else argv)
    if len(words) > 1 and words[0] == "agent" and words[1].startswith("/"):
        words.insert(1, "run")  # preserve `agent /raw/regulations/x.md ...`
    args = parser().parse_args(words)

    if args.command == "compile":
        if not (args.pages or args.sample or args.random or args.all):
            args._parser.error("provide PAGE ... or --sample, --random N, --all, or link")
        if args.pages and (args.sample or args.random or args.all):
            args._parser.error("PAGE arguments cannot be combined with --sample, --random or --all")
        if args.pages[:1] == ["link"] and len(args.pages) != 1:
            args._parser.error("compile link takes no page arguments")
    elif args.command == "index":
        if (args.action in ("export", "import")) != (args.file is not None):
            args._parser.error("export/import require a file; sync/status take no file")
        if args.action != "sync" and args.no_embed:
            args._parser.error("--no-embed is only valid for sync")
    elif args.command == "autopilot" and args.action != "run":
        if args.source or args.loop or args.only_new or args.build or args.no_answers or (args.action == "discard" and args.no_push):
            args._parser.error("run options cannot be used with accept/discard")
    return args


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    from catix.settings import settings

    settings.phoenix_project = settings.wiki_phoenix_project  # before tracing is set up: the wiki's traces go to a project of their own
    cmd = args.command
    if cmd == "fetch":
        from catix.wiki.sources import eduwiki

        eduwiki.fetch(args.namespaces or [0])
    elif cmd == "status":
        from catix.wiki.sources import eduwiki

        eduwiki.status()
    elif cmd == "sveden":
        from catix.wiki.sources import sveden

        sveden.main(args)
    elif cmd == "regs":
        from catix.wiki.sources import regulations

        regulations.main(args)
    elif cmd == "sites":
        from catix.wiki.sources import sites

        sites.main(args)
    elif cmd == "papers":
        from catix.wiki.sources import pastpapers

        pastpapers.main(args)
    elif cmd == "rpd":
        from catix.wiki.sources import rpd

        rpd.main(args)
    elif cmd == "autopilot":
        from catix.wiki import autopilot

        autopilot.main(args)
    elif cmd == "build":
        from catix.wiki import build

        build.main(args)
    elif cmd == "agent":
        from catix.wiki import agent

        agent.main(args)
    elif cmd == "graph":
        from catix.wiki import graph

        graph.main(use_model=not args.no_model)
    elif cmd == "lint":
        from catix.wiki import lint

        lint.main()
    elif cmd == "layout":
        from catix.wiki import layout

        layout.main(dry_run=args.dry_run)
    elif cmd == "index":
        from catix.wiki import search_index

        search_index.main(args)
    elif cmd in {"compile", "link"}:
        from catix.wiki import compile as compiler

        compiler.main(args)


if __name__ == "__main__":
    main()
