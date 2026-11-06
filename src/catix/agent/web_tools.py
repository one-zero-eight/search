"""Web search of the docs helper (Tavily), for what the knowledge base lacks: the university's and the city's own sites first
(OFFICIAL_SITES, the hosts the wiki's pages come from), the rest of the web only when asked.

The knowledge base stays the first place to look: a web search before a search_wiki of the same question is refused, and a
question gets at most MAX_SEARCHES searches and MAX_READS page reads (each costs Tavily credits). Only the helper's own
query goes to Tavily, never who asks. What a page says is data, as a chat message is: the results are cited like the
wiki's pieces (sources.Collector.add_web) and a page off the official sites is said to be from the web. Without a key
(settings.tavily_api_key) the helper has no such tools (core._helper_tool) and its prompt does not mention them
(roles.prompt).
"""

import json
import logging
import threading
import time
from urllib.parse import urlsplit

import httpx
from langchain.tools import ToolRuntime
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.types import Command
from pydantic import BaseModel, Field

from catix.agent.sources import Collector
from catix.settings import settings

log = logging.getLogger("catix.web")

TAVILY = "https://api.tavily.com"
# The hosts the wiki's pages come from (with their subdomains): the university, its schools and services, the city.
OFFICIAL_SITES = ["innopolis.university", "innopolis.ru", "innopolis.com", "sezinnopolis.ru", "innopolis.college", "innohassle.ru"]
NAMES = {"search_web", "read_web_page"}
MAX_RESULTS = 5
TEXT_CHARS = 700  # of a search result
PAGE_CHARS = 4000  # of a page read
MAX_SEARCHES = 2
MAX_READS = 1
CACHE_SECONDS = 6 * 3600
CACHE_SIZE = 500
WIKI_FIRST = "Search the knowledge base first (search_wiki); search the web only for what it does not have."
NO_MORE = "No more web {what} in this question: report with what you have, and say what is missing."

_client = httpx.Client(base_url=TAVILY, timeout=20)
_cache: dict[str, tuple[float, dict]] = {}
_lock = threading.Lock()


def enabled() -> bool:
    return settings.tavily_api_key is not None


def official(url: str) -> bool:
    host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    return any(host == site or host.endswith("." + site) for site in OFFICIAL_SITES)


def _tavily(path: str, body: dict) -> dict:
    """POST to Tavily, cached: the same query of the same day costs nothing again. Raises httpx.HTTPError."""
    key = f"{path} {json.dumps(body, sort_keys=True, ensure_ascii=False)}"
    with _lock:
        if (hit := _cache.get(key)) and hit[0] > time.monotonic():
            return hit[1]
    resp = _client.post(path, json=body, headers={"Authorization": f"Bearer {settings.tavily_api_key.get_secret_value()}"})  # type: ignore[union-attr]
    resp.raise_for_status()
    data = resp.json()
    with _lock:
        if len(_cache) >= CACHE_SIZE:
            for old in sorted(_cache, key=lambda k: _cache[k][0])[: CACHE_SIZE // 2]:
                del _cache[old]
        _cache[key] = (time.monotonic() + CACHE_SECONDS, data)
    return data


def _run_calls(runtime: ToolRuntime) -> list[str]:
    """The names of the tools whose results came back since the helper got the question."""
    messages = runtime.state.get("messages", []) if runtime.state else []
    start = max((i for i, m in enumerate(messages) if isinstance(m, HumanMessage)), default=-1)
    return [m.name or "" for m in messages[start + 1 :] if isinstance(m, ToolMessage)]


def _failed(e: httpx.HTTPError) -> str:
    status = e.response.status_code if isinstance(e, httpx.HTTPStatusError) else None
    log.warning("Tavily failed: %s", status or e)
    if status in (401, 403):
        return "The web search is not available now (its key was refused): report without it."
    if status in (429, 432, 433):
        return "The web search is out of its limit for now: report without it."
    return "The web search did not answer: report without it."


def _text(value: str | None, limit: int) -> str:
    text = " ".join((value or "").split())
    return text if len(text) <= limit else text[:limit].rstrip() + " [...cut]"


class SearchWebArgs(BaseModel):
    query: str = Field(max_length=200, description="What to find, as a search engine query, in the language of the pages wanted.")
    anywhere: bool = Field(
        False,
        description="false (default): only the sites of the university and of the city of Innopolis. true: the whole web, only "
        "for what those sites cannot have (another city, a company, transport between cities).",
    )


@tool(args_schema=SearchWebArgs)
def search_web(query: str, runtime: ToolRuntime, anywhere: bool = False) -> Command:
    """Search the web for what the knowledge base does not have: pages newer than it, or not in it. By default only the sites
    of the university and of the city of Innopolis. Returns pieces of pages with a ref to cite."""
    collector = Collector(runtime)
    calls = _run_calls(runtime)
    if "search_wiki" not in calls:
        return collector.result({"error": WIKI_FIRST}, "search_web")
    if calls.count("search_web") >= MAX_SEARCHES:
        return collector.result({"error": NO_MORE.format(what="searches")}, "search_web")
    body = {"query": query, "search_depth": "basic", "max_results": MAX_RESULTS, "include_published_date": True}
    if not anywhere:
        body["include_domains"] = OFFICIAL_SITES
    try:
        found = _tavily("/search", body).get("results") or []
    except httpx.HTTPError as e:
        return collector.result({"error": _failed(e)}, "search_web")
    results = []
    for hit in found[:MAX_RESULTS]:
        url, is_official = hit.get("url") or "", official(hit.get("url") or "")
        if not url.startswith(("https://", "http://")) or (not anywhere and not is_official):
            continue
        item = {"ref": collector.add_web(_text(hit.get("title"), 150) or url, url, is_official), "title": _text(hit.get("title"), 150),
                "url": url, "official_site": is_official, "date": (hit.get("published_date") or "")[:10] or None,
                "text": _text(hit.get("content"), TEXT_CHARS)}  # fmt: skip
        results.append({k: v for k, v in item.items() if v is not None})
    payload: dict = {"total": len(results), "results": results}
    if not results:
        payload["note"] = "Nothing found on the web." if anywhere else "Nothing found on the sites of the university and the city."
    elif any(not r["official_site"] for r in results):
        payload["note"] = "Pages off the official sites (official_site false) may be wrong or old: say where a fact comes from."
    return collector.result(payload, "search_web", {"relevant": [r["ref"] for r in results]})


class ReadWebPageArgs(BaseModel):
    url: str = Field(max_length=500, description="The `url` of a search_web result.")


@tool(args_schema=ReadWebPageArgs)
def read_web_page(url: str, runtime: ToolRuntime) -> Command:
    """Read more of a page that search_web found, when its piece is cut or the answer is further on the page."""
    collector = Collector(runtime)
    if _run_calls(runtime).count("read_web_page") >= MAX_READS:
        return collector.result({"error": NO_MORE.format(what="reads")}, "read_web_page")
    found = any(s.get("web") and s.get("link") == url for s in collector.known.values())
    if not found:  # (a page named in a chat message or another page is not read: it may be anything)
        return collector.result({"error": "Only a page that search_web found can be read: give its `url`."}, "read_web_page")
    question = next((str(m.content) for m in (runtime.state or {}).get("messages", []) if isinstance(m, HumanMessage)), "")
    body = {"urls": [url], "extract_depth": "basic", "format": "markdown", "query": question[:300], "chunks_per_source": 3}
    try:
        data = _tavily("/extract", body)
    except httpx.HTTPError as e:
        return collector.result({"error": _failed(e)}, "read_web_page")
    page = next((r for r in data.get("results") or [] if r.get("raw_content")), None)
    if page is None:
        return collector.result({"error": "The page could not be read: report with the search result."}, "read_web_page")
    ref = collector.add_web(url, url, official(url))  # (the ref of the search result: the same page keeps its ref)
    return collector.result({"ref": ref, "url": url, "text": _text(page["raw_content"], PAGE_CHARS)}, "read_web_page")


WEB_TOOLS = [search_web, read_web_page]
