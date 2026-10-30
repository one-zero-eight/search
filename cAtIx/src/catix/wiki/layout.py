"""The bundle's folders as paths.py lays them out: the documents under wiki/raw/, the model's own folders beside them.

    catix-wiki layout [--dry-run]

Before 2026-10-30 the documents stood in wiki/<folder>/ beside the cards. This moves every folder of documents
(compile.TYPES, compile.FOLDERS) into wiki/raw/ and rewrites what led to their pages: the links and front matter of every
page (the cards' citations, the notes' `source`, eduwiki's links between its pages, graph.py's relations), the agent's queue,
graph.py's cache of answers, and the paths of the search index in the database — moved, not cut again, so no piece is
embedded again for a move (a piece whose text held a link is, at the next `catix-wiki index`). A second run finds nothing to
move.
"""

import re
import shutil
import sys
from pathlib import Path

from catix.settings import settings
from catix.wiki.compile import FOLDERS, TYPES
from catix.wiki.paths import BUNDLE, DOCS, DOCS_FOLDER, RAW, card_folders


def document_folders() -> list[str]:
    """The folders of documents the code writes (they go under wiki/raw/)."""
    return sorted(set(FOLDERS) | set(TYPES.values()))


def old_path(folders: list[str]) -> re.Pattern:
    """A bundle path of a document as it was ('/regulations/x' after '(', '"', a space or a line's start): not a part of a URL."""
    return re.compile(r"(?<=[(\"'\s])/(" + "|".join(map(re.escape, folders)) + r")/")


def to_move(bundle: Path = BUNDLE) -> list[str]:
    """The folders of documents still beside the model's (a folder the model declared is its own, whatever its name)."""
    mine = set(card_folders(bundle))
    return [f for f in document_folders() if (bundle / f).is_dir() and f not in mine]


def move_files(folders: list[str], bundle: Path = BUNDLE, dry_run: bool = False) -> int:
    """wiki/<folder>/ -> wiki/raw/<folder>/; the files moved."""
    moved = 0
    for folder in folders:
        source, target = bundle / folder, bundle / DOCS_FOLDER / folder
        files = [p for p in source.rglob("*") if p.is_file()]
        clash = [p for p in files if (target / p.relative_to(source)).exists() and p.name != "index.md"]
        if clash:
            raise SystemExit(f"{target} already holds {clash[0].relative_to(source)}: move by hand")
        moved += len(files)
        if dry_run:
            continue
        for p in files:
            (target / p.relative_to(source)).parent.mkdir(parents=True, exist_ok=True)
            p.replace(target / p.relative_to(source))
        shutil.rmtree(source)
    return moved


def rewrite(text: str, pattern: re.Pattern) -> str:
    return pattern.sub(lambda m: f"/{DOCS_FOLDER}/{m.group(1)}/", text)


def rewrite_files(folders: list[str], bundle: Path = BUNDLE, dry_run: bool = False) -> int:
    """Every link and front matter path to a moved page, in every page of the bundle; the files rewritten."""
    pattern, changed = old_path(folders), 0
    for path in bundle.rglob("*.md"):
        if any(part.startswith(".") for part in path.relative_to(bundle).parts):
            continue
        text = path.read_text(encoding="utf-8")
        if (new := rewrite(text, pattern)) != text:
            changed += 1
            if not dry_run:
                path.write_text(new, encoding="utf-8")
    return changed


def rewrite_state(folders: list[str], dry_run: bool = False) -> list[str]:
    """The files beside the bundle that hold its paths: the agent's queue, graph.py's cache."""
    pattern, changed = old_path(folders), []
    for path in [RAW / "knowledge-queue.json", RAW / "eduwiki" / "graph-cache.json"]:
        if path.exists() and (new := rewrite(path.read_text(encoding="utf-8"), pattern)) != path.read_text(encoding="utf-8"):
            changed.append(path.name)
            if not dry_run:
                path.write_text(new, encoding="utf-8")
    return changed


def move_index(folders: list[str], dry_run: bool = False) -> int:
    """The search index's pages and pieces under their new paths, their vectors kept; the pages moved."""
    from catix.db import pg

    regex = r'"/(' + "|".join(map(re.escape, folders)) + r')/'
    with pg.connection() as conn:
        n = pg.scalar(conn, "SELECT count(*) FROM wiki_pages WHERE split_part(path, '/', 2) = ANY(%s)", (folders,))
        if dry_run or not n:
            return n
        conn.execute(
            """INSERT INTO wiki_pages (path, sha, title, type, trust, audience, resource, status, review, source_warning, stale_after, issued, indexed_at)
               SELECT %(raw)s || path, sha, title, type, trust, audience, resource, status, review, source_warning, stale_after, issued, indexed_at
               FROM wiki_pages WHERE split_part(path, '/', 2) = ANY(%(f)s) ON CONFLICT (path) DO NOTHING""",
            {"raw": f"/{DOCS_FOLDER}", "f": folders})
        conn.execute("UPDATE wiki_chunks SET path = %s || path WHERE split_part(path, '/', 2) = ANY(%s)", (f"/{DOCS_FOLDER}", folders))
        conn.execute("UPDATE wiki_chunks SET cites = regexp_replace(cites::text, %s, %s, 'g')::jsonb WHERE cites::text ~ %s",
                     (regex, f'"/{DOCS_FOLDER}/\\1/', regex))
        conn.execute("DELETE FROM wiki_pages WHERE split_part(path, '/', 2) = ANY(%s)", (folders,))
    return n


def migrate(dry_run: bool = False) -> list[str]:
    """Every folder of documents still beside the model's, moved into wiki/raw/ with every path to it; the folders moved."""
    folders = to_move()
    if not folders:
        return []
    print(f"{'would move' if dry_run else 'moving'} {', '.join(folders)} -> wiki/{DOCS_FOLDER}/", flush=True)
    print(f"  {move_files(folders, dry_run=dry_run)} files")
    print(f"  {rewrite_files(folders, dry_run=dry_run)} pages with links rewritten")
    print(f"  state: {', '.join(rewrite_state(folders, dry_run)) or 'nothing'}")
    if settings.database_url:
        print(f"  search index: {move_index(folders, dry_run)} pages moved")
    if not dry_run:
        from catix.wiki.compile import link

        link()  # the indexes of every folder, the root's with the documents first
    return folders


def main() -> None:
    if not migrate("--dry-run" in sys.argv[2:]):
        print(f"nothing to move: the documents are in {DOCS}")
