"""`catix-docs`: the commands of the documents.

    catix-docs status                                   # the documents and the vector queue in the database
    catix-docs run [--loop] [--source NAME ...] [--site NAME ...] [--build]   # the documents maintain themselves, see runner.py
    catix-docs build [--embed]                          # rebuild the documents from the sources' data; --embed: then compute the vectors
    catix-docs import-wiki ROOT                         # once: the data of the old WIKI_ROOT/raw into the database
    catix-docs eduwiki fetch [NAMESPACE ...]|status     # the eduwiki snapshot; default namespace 0 (articles)
    catix-docs regs fetch|refresh|queue                 # official regulations (PDF), see sources/regulations.py; queue: the OCR queue (sources/ocr_queue.py)
    catix-docs rpd fetch|refresh|status                 # course programmes (РПД) from the archives of sveden/education, see sources/rpd.py
    catix-docs sites fetch [SITE ...]|new|status|docs   # the sites of the university, its services and the city, see sources/sites.py
    catix-docs papers fetch|status                      # past exam papers from the students' Notion database, see sources/pastpapers.py

Everything lives in Postgres (DATABASE_URL): the sources' state and extracted text in source_files, the documents in documents.

The code is laid out by what each part does:
    sources/       what the documents are made from: each module asks one source what is new, keeps its state in source_files
                   and makes documents of it (eduwiki, regulations: the documents the sites link, rpd: course programmes,
                   sites: the services' sites, pastpapers: past exams); sources/__init__.py says how often each is asked
    store.py       documents in the database for the agent's search;  chunks.py: how a document is cut into pieces
    build.py       all sources' documents;  runner.py: the run that keeps them current and serves the API's requests
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
    root = argparse.ArgumentParser(prog="catix-docs", description="Read sources and maintain the documents.", allow_abbrev=False,
                                   epilog="Data: Postgres (DATABASE_URL).")
    commands = root.add_subparsers(dest="command")
    root.set_defaults(command="status")

    def command(parent, name, help):
        child = parent.add_parser(name, help=help, description=help, allow_abbrev=False)
        child.set_defaults(_parser=child)
        return child

    command(commands, "status", "Show the documents and the vector queue")
    run = command(commands, "run", "Ask the due sources, rebuild the documents, serve the API's requests")
    run.add_argument("--source", nargs="+", action="extend", metavar="NAME", help="Sources to ask now; may be repeated")
    run.add_argument("--site", nargs="+", action="extend", metavar="NAME", help="Read only these sites (the source sites, limited); may be repeated")
    run.add_argument("--loop", action="store_true", help="Keep running on the source schedule")
    run.add_argument("--build", action="store_true", help="Rebuild the documents without asking sources")
    command(commands, "build", "Rebuild the documents from the sources' data").add_argument("--embed", action="store_true", help="Then compute the vectors")
    command(commands, "import-wiki", "Import the data of an old WIKI_ROOT/raw into the database").add_argument("root", type=Path, metavar="ROOT")

    for name, about, default, actions in (
        ("eduwiki", "Eduwiki pages", "status", ("fetch", "status")),
        ("regs", "Official regulations", None, ("fetch", "refresh", "queue")),
        ("rpd", "Course programmes", "status", ("fetch", "refresh", "status")),
        ("papers", "Past exam papers", "status", ("fetch", "status")),
        ("sites", "University and city sites", "status", ("fetch", "new", "status", "docs")),
    ):
        group = command(commands, name, about)
        actions_parser = group.add_subparsers(dest="action", required=default is None)
        group.set_defaults(action=default)
        for action in actions:
            about_action = "Show the OCR queue and the scans too long for OCR" if (name, action) == ("regs", "queue") else f"{action.capitalize()} {about.lower()}"
            leaf = command(actions_parser, action, about_action)
            if name == "eduwiki" and action == "fetch":
                leaf.add_argument("namespaces", nargs="*", type=int, metavar="NAMESPACE")
            elif name == "regs" and action == "fetch":
                leaf.add_argument("limit", nargs="?", type=positive, metavar="N", help="At most N new documents")
                leaf.add_argument("--no-ocr", action="store_true", help="Read text layers only; queue scans for a run with OCR")
            elif name == "rpd" and action == "fetch":
                leaf.add_argument("--all-years", action="store_const", const=True, default=None, help="Include every cohort")
                leaf.add_argument("--limit", type=positive)
            elif name == "sites":
                if action == "fetch":
                    leaf.add_argument("names", nargs="*", metavar="SITE")
                    leaf.add_argument("--only-new", action="store_true", help="Fetch only trusted-provider page links no run has read or tried lately")
                elif action == "new":
                    leaf.add_argument("names", nargs="*", metavar="SITE")
    return root


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return parser().parse_args(list(sys.argv[1:] if argv is None else argv))


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    from catix.settings import settings

    if not settings.database_url:
        sys.exit("catix-docs needs DATABASE_URL: the documents and their sources live in Postgres")
    from catix.db import pg

    try:
        dispatch(args)
    finally:
        pg.close()


def dispatch(args) -> None:
    cmd = args.command
    if cmd == "status":
        from catix.docs import store

        store.status()
    elif cmd == "run":
        from catix.docs import runner

        runner.main(args)
    elif cmd == "build":
        from catix.docs import build, store

        print(build.rebuild())
        if args.embed:
            store.embed_all()
    elif cmd == "import-wiki":
        from catix.docs import import_wiki

        import_wiki.main(args.root)
    elif cmd == "eduwiki":
        from catix.docs.sources import eduwiki

        eduwiki.fetch(args.namespaces or [0]) if args.action == "fetch" else eduwiki.status()
    elif cmd == "regs":
        from catix.docs.sources import regulations

        regulations.main(args)
    elif cmd == "sites":
        from catix.docs.sources import sites

        sites.main(args)
    elif cmd == "papers":
        from catix.docs.sources import pastpapers

        pastpapers.main(args)
    elif cmd == "rpd":
        from catix.docs.sources import rpd

        rpd.main(args)


if __name__ == "__main__":
    main()
