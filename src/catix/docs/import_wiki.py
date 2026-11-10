"""One-off import of the old wiki's data: WIKI_ROOT/raw (the sources' JSON state, extracted text, cached pages) into
source_files, then the documents are built from it (build.rebuild). The md pages of the old wiki/ are not read: the documents
are made again from the sources' state, and an unchanged piece is found by its sha and keeps its vector. Repeatable.

    catix-docs import-wiki ROOT
"""

import json
import sys
from collections import Counter
from pathlib import Path

from catix.docs import build, files, store

FOLDERS = {"eduwiki", "regulations", "sites", "rpd", "past-papers"}  # the first segment of what is imported
SKIP = {"eduwiki/graph-cache.json", "regulations/proposals.json", "regulations/selection-cache.json"}
BATCH = 500  # files between two lines of progress


def wanted(rel: Path) -> bool:
    parts = rel.parts
    return (parts[0] in FOLDERS and rel.suffix in (".json", ".txt", ".md") and rel.as_posix() not in SKIP
            and not any(p.endswith((".chandra", ".ocr")) for p in parts))


def main(root: Path) -> None:
    raw = root / "raw"
    if not raw.is_dir():
        sys.exit(f"{root}/raw is not a folder of the wiki's data")
    found = sorted(p for p in raw.rglob("*") if p.is_file() and wanted(p.relative_to(raw)))
    for i in range(0, len(found), BATCH):
        for p in found[i : i + BATCH]:
            rel = p.relative_to(raw).as_posix()
            if p.suffix == ".json":
                files.write_json(rel, json.loads(p.read_text(encoding="utf-8")))
            else:
                files.write_text(rel, p.read_text(encoding="utf-8"))
        print(f"  {min(i + BATCH, len(found))}/{len(found)}", flush=True)
    for folder, n in sorted(Counter(p.relative_to(raw).parts[0] for p in found).items()):
        print(f"{folder}: {n} files")
    print(build.rebuild())
    print(f"pieces wait for a vector: the worker computes them ({store.queued()})")
