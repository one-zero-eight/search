"""Source `eduwiki`: a snapshot of the eduwiki (MediaWiki) into raw/eduwiki. compile.py makes the bundle's pages of it.

    catix-wiki fetch [NAMESPACE ...]   # default: namespace 0 (articles); only pages whose revision changed are downloaded
    catix-wiki status                  # pages in the snapshot, redirects, pages missing on the wiki now

One file per page (raw/eduwiki/pages/<pageid>.json) with the wikitext and the revision it came from;
raw/eduwiki/manifest.json maps page id -> title and revision id. Files are never edited by hand.
"""

import json
from datetime import datetime, timezone

import httpx

from catix.wiki.paths import RAW
API = "https://eduwiki.innopolis.university/api.php"
ROOT = RAW / "eduwiki"
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


def fetch(namespaces: list[int]) -> int:
    """New and changed pages of the wiki into the snapshot; the number of pages new, changed or deleted."""
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
        gone = 0
        for pid, entry in manifest.items():
            if entry["ns"] in namespaces:
                gone += (int(pid) not in remote) != entry.get("deleted", False)
                entry["deleted"] = int(pid) not in remote
        save_manifest(manifest)
    return len(todo) + gone


def status() -> None:
    manifest = load_manifest()
    redirects = sum(e["redirect"] for e in manifest.values())
    deleted = sum(e.get("deleted", False) for e in manifest.values())
    print(f"{len(manifest)} pages in the snapshot, {redirects} redirects, {deleted} deleted on the wiki")
