"""Snapshot of the eduwiki (MediaWiki) into raw/eduwiki: the source the OKF bundle in wiki/ is compiled from.

    catix-wiki fetch [NAMESPACE ...]   # default: namespace 0 (articles); only pages whose revision changed are downloaded
    catix-wiki status                  # pages in the snapshot, redirects, pages missing on the wiki now
    catix-wiki sveden discover|triage|status|override   # all documents of innopolis.university/sveden (see sveden.py)
    catix-wiki topics [list|accept|reject]   # the model proposes guides, a person accepts them (see topics.py)
    catix-wiki regs fetch|compile      # official regulations (PDF) as a second source, see regulations.py
    catix-wiki build [--offline] [--force] [--auto]   # the whole chain, re-running only what changed (see build.py)
    catix-wiki synth [TOPIC ...]       # guides that combine many concepts (wiki/guides/), see synth.py
    catix-wiki graph                   # relations between concepts (prerequisites, teachers), see graph.py
    catix-wiki lint                    # check wiki/ against OKF v0.2
    catix-wiki compile ...             # snapshot -> OKF bundle in wiki/ (see compile.py)

One file per page (raw/eduwiki/pages/<pageid>.json) with the wikitext and the revision it came from;
raw/eduwiki/manifest.json maps page id -> title and revision id. Files are never edited by hand.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

API = "https://eduwiki.innopolis.university/api.php"
ROOT = Path(__file__).resolve().parents[3] / "raw" / "eduwiki"
PAGES = ROOT / "pages"
MANIFEST = ROOT / "manifest.json"
BATCH = 50  # MediaWiki returns page content for at most 50 titles per request


def _get(client: httpx.Client, **params) -> dict:
    resp = client.get(API, params={"format": "json", "formatversion": "2", **params})
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"{params.get('action')}: {data['error']}")
    return data


def list_pages(client: httpx.Client, namespace: int) -> dict[int, dict]:
    """page id -> {title, revid, redirect} for every page of the namespace."""
    pages: dict[int, dict] = {}
    cont: dict = {}
    while True:
        data = _get(client, action="query", generator="allpages", gapnamespace=namespace, gaplimit=500, prop="info", **cont)
        for p in data["query"]["pages"]:
            pages[p["pageid"]] = {"title": p["title"], "revid": p["lastrevid"], "redirect": p.get("redirect", False), "ns": namespace}
        if "continue" not in data:
            return pages
        cont = data["continue"]


def fetch_content(client: httpx.Client, ids: list[int]) -> list[dict]:
    data = _get(client, action="query", pageids="|".join(map(str, ids)), prop="revisions", rvprop="ids|timestamp|content", rvslots="main")
    out = []
    for p in data["query"]["pages"]:
        if "missing" in p:
            continue
        rev = p["revisions"][0]
        out.append({"pageid": p["pageid"], "title": p["title"], "ns": p["ns"], "revid": rev["revid"], "timestamp": rev["timestamp"], "wikitext": rev["slots"]["main"]["content"]})
    return out


def load_manifest() -> dict[str, dict]:
    return json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}


def save_manifest(manifest: dict[str, dict]) -> None:
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def fetch(namespaces: list[int]) -> None:
    PAGES.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    with httpx.Client(timeout=60, headers={"User-Agent": "catix-wiki/0.1 (Innopolis University assistant)"}) as client:
        remote: dict[int, dict] = {}
        for ns in namespaces:
            remote |= list_pages(client, ns)
        todo = [pid for pid, p in remote.items() if manifest.get(str(pid), {}).get("revid") != p["revid"]]
        print(f"{len(remote)} pages on the wiki, {len(todo)} new or changed")
        for i in range(0, len(todo), BATCH):
            for page in fetch_content(client, todo[i : i + BATCH]):
                page["fetched_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                (PAGES / f"{page['pageid']}.json").write_text(json.dumps(page, ensure_ascii=False, indent=1), encoding="utf-8")
                manifest[str(page["pageid"])] = {"title": page["title"], "revid": page["revid"], "redirect": remote[page["pageid"]]["redirect"], "ns": page["ns"]}
            print(f"  {min(i + BATCH, len(todo))}/{len(todo)}")
            save_manifest(manifest)
        # pages deleted on the wiki stay in the snapshot but are marked, so the compiler can retire their concepts
        for pid, entry in manifest.items():
            if entry["ns"] in namespaces:
                entry["deleted"] = int(pid) not in remote
        save_manifest(manifest)


def status() -> None:
    manifest = load_manifest()
    redirects = sum(e["redirect"] for e in manifest.values())
    deleted = sum(e.get("deleted", False) for e in manifest.values())
    print(f"{len(manifest)} pages in the snapshot, {redirects} redirects, {deleted} deleted on the wiki")


def main() -> None:
    cmd, *args = sys.argv[1:] or ["status"]
    if cmd == "fetch":
        fetch([int(a) for a in args] or [0])
    elif cmd == "status":
        status()
    elif cmd == "sveden":
        from catix.wiki import sveden

        sveden.main()
    elif cmd == "topics":
        from catix.wiki import topics

        topics.main()
    elif cmd == "regs":
        from catix.wiki import regulations

        regulations.main()
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
    elif cmd in {"compile", "link"}:
        from catix.wiki import compile as compiler

        compiler.main([cmd] + args if cmd == "link" else args)
    else:
        raise SystemExit(__doc__)
