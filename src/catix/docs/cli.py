"""`catix-docs`: the commands of the documents.

    catix-docs status                                   # the documents and the vector queue in the database
    catix-docs run [--loop] [--source NAME ...] [--site NAME ...] [--build]   # the documents maintain themselves, see runner.py
    catix-docs build [--embed]                          # rebuild the documents from the sources' data; --embed: then compute the vectors
    catix-docs eduwiki fetch [NAMESPACE ...]|status     # the eduwiki snapshot; default namespace 0 (articles)
    catix-docs regs fetch|queue                         # official regulations (PDF), see sources/regulations.py; queue: the OCR queue (sources/ocr_queue.py)
    catix-docs rpd fetch|refresh|status                 # course programmes (РПД) from the archives of sveden/education, see sources/rpd.py
    catix-docs sites request URL|status|unvisited|catalog   # the sites of the university, its services and the city, see sources/sites.py

Everything lives in Postgres (DATABASE_URL), in a table of its own for each kind of data: the catalog of sites (site_catalog), the
crawl (crawl_urls, crawl_links: frontier.py), the documents read (document_files: notes.py; archives; course_programmes), the
eduwiki (eduwiki_pages) and the documents made of them (documents).

The code is laid out by what each part does:
    frontier.py    the crawl: the addresses, their links, when each is read next;  notes.py: the notes and texts of the documents read
    sources/       what the documents are made from: each module reads one source, keeps its data in its tables and makes documents
                   of it (eduwiki, regulations: the documents the sites link, rpd: course programmes, sites: the services' sites);
                   sources/__init__.py lists the jobs and how often each is asked
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
    run = command(commands, "run", "Read the addresses that are due, rebuild the documents, serve the API's requests")
    run.add_argument("--source", nargs="+", action="extend", metavar="NAME", help="Jobs to run now: eduwiki, rpd, rpd-refresh; may be repeated")
    run.add_argument("--site", nargs="+", action="extend", metavar="NAME", help="Read these sites' addresses first, and end when they are read; may be repeated")
    run.add_argument("--loop", action="store_true", help="Keep running: read what falls due")
    run.add_argument("--build", action="store_true", help="Rebuild the documents without reading anything")
    command(commands, "build", "Rebuild the documents from the sources' data").add_argument("--embed", action="store_true", help="Then compute the vectors")

    for name, about, default, actions in (
        ("eduwiki", "Eduwiki pages", "status", ("fetch", "status")),
        ("regs", "Official regulations", None, ("fetch", "queue")),
        ("rpd", "Course programmes", "status", ("fetch", "refresh", "status")),
        ("sites", "University and city sites", "status", ("request", "status", "unvisited", "catalog")),
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
                leaf.add_argument("--key", help="Queue this one document for docs-loop to read again, whatever its note says, with no limit of size, pages or OCR budget (a key of the documents)")
                leaf.add_argument("--now", action="store_true", help="With --key: read it in this process at once, not in docs-loop")
            elif name == "rpd" and action == "fetch":
                leaf.add_argument("--all-years", action="store_const", const=True, default=None, help="Include every cohort")
                leaf.add_argument("--limit", type=positive)
            elif name == "sites":
                if action == "request":
                    leaf.add_argument("url")
                    leaf.add_argument("--name", help="Its name in the catalog; the host with dashes when omitted")
                elif action == "unvisited":
                    leaf.add_argument("names", nargs="*", metavar="SITE")
                    leaf.add_argument("--summary", action="store_true", help="Only the number of addresses per site and host")
                    which = leaf.add_mutually_exclusive_group()
                    which.add_argument("--known", dest="only", action="store_const", const="known", help="Only the sites of the catalog")
                    which.add_argument("--unknown", dest="only", action="store_const", const="unknown", help="Only the hosts the catalog does not have")
                elif action == "catalog":
                    catalog = leaf.add_subparsers(dest="catalog_action", required=True)
                    command(catalog, "import", "Replace the catalog with a file (sites.yaml)").add_argument("file", type=Path)
                    command(catalog, "export", "Print the catalog as YAML")
                    add = command(catalog, "add", "Add or replace a site")
                    add.add_argument("name")
                    add.add_argument("fields", nargs="+", metavar="KEY=VALUE", help="base=https://x/ language=ru about=... skip=''; lists as YAML")
                    command(catalog, "remove", "Remove a site").add_argument("name")
                    command(catalog, "block", "Never read a host").add_argument("host")
                    command(catalog, "unblock", "Read a blocked host again").add_argument("host")
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
    if cmd in ("run", "build", "regs", "rpd", "eduwiki", "sites"):
        from catix.docs import frontier

        frontier.ensure_imported()  # (the old store, once: legacy.py)
    if cmd == "status":
        from catix.docs import frontier, store

        store.status()
        frontier.status()
    elif cmd == "run":
        from catix.docs import runner

        runner.main(args)
    elif cmd == "build":
        from catix.docs import build, store

        print(build.rebuild())
        if args.embed:
            store.embed_all()
    elif cmd == "eduwiki":
        from catix.docs.sources import eduwiki

        eduwiki.fetch(args.namespaces or [0]) if args.action == "fetch" else eduwiki.status()
    elif cmd == "regs":
        from catix.docs.sources import regulations

        regulations.main(args)
    elif cmd == "sites":
        from catix.docs.sources import sites

        sites.main(args)
    elif cmd == "rpd":
        from catix.docs.sources import rpd

        rpd.main(args)


if __name__ == "__main__":
    main()
