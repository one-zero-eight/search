"""Web search of the docs helper (DeepSeek Search & Fetch), for what the knowledge base lacks: official sites first
(OFFICIAL_SITES, the hosts the wiki's pages come from), the rest of the web only when asked.

The knowledge base stays the first place to look: a web search before a search_wiki of the same question is refused, and a
question gets at most MAX_SEARCHES searches and MAX_READS page reads. Official sites are batched into site: queries to fit
DeepSeek's 128-character limit (at most one request per site). Only the helper's own query goes there, never who asks.
What a page says is data, as a chat message is: the results are cited like the
wiki's pieces (sources.Collector.add_web) and a page off the official sites is said to be from the web.

Without a key (settings.deepseek_api_key) the helper has no such tools (core.helper_tools) and its prompt does not
mention them (roles.prompt). An optional HTTP proxy is set with settings.deepseek_proxy.
A proxy that does not work (or a DeepSeek that cannot be reached,
refuses the key or is out of its limit) fails within TIMEOUT and the helper reports without the web; for DOWN_SECONDS
after that the web is not asked again in this process (what is cached is still given), so that every question does not
wait for it.
"""

import functools
import hashlib
import json
import logging
import time
from urllib.parse import urlsplit

import httpx
from langchain.tools import ToolRuntime
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.types import Command
from pydantic import BaseModel, Field

from catix.agent.sources import Collector
from catix.common import cache
from catix.settings import settings

log = logging.getLogger("catix.web")

DEEPSEEK = "https://api.deepseek.com"
# The hosts the wiki's pages come from (with their subdomains): the university, its schools and services, the city.
OFFICIAL_SITES = ["innopolis.university", "innopolis.ru", "innopolis.com", "sezinnopolis.ru", "innopolis.college", "innohassle.ru"]
QUERY_CHARS = 128
OFFICIAL_QUERY_CHARS = QUERY_CHARS - len(" site:") - max(map(len, OFFICIAL_SITES))
NAMES = {"search_web", "read_web_page"}
MAX_RESULTS = 5
TEXT_CHARS = 700  # of a search result
PAGE_CHARS = 4000  # of a page read
MAX_SEARCHES = 2
MAX_READS = 1
CACHE_SECONDS = 6 * 3600
DOWN_SECONDS = 120.0
TIMEOUT = httpx.Timeout(20, connect=5)  # (a proxy that cannot be reached is given up on in 5 s, a silent one in 20 s)
WIKI_FIRST = "Search the knowledge base first (search_wiki); search the web only for what it does not have."
NO_MORE = "No more web {what} in this question: report with what you have, and say what is missing."

# Until when (time.monotonic) the web is not asked, and what the helper is told meanwhile.
_down: tuple[float, str] = (0.0, "")


class _Down(Exception):
    """The web search failed a moment ago (_down): not asked again yet."""


def enabled() -> bool:
    return settings.deepseek_api_key is not None


@functools.cache
def _client() -> httpx.Client:
    """Through DEEPSEEK_PROXY when it is set, else the environment's usual HTTP route."""
    proxy = settings.deepseek_proxy.get_secret_value() if settings.deepseek_proxy else None
    return httpx.Client(base_url=DEEPSEEK, proxy=proxy, timeout=TIMEOUT)


def official(url: str) -> bool:
    host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    return any(host == site or host.endswith("." + site) for site in OFFICIAL_SITES)


def _deepseek(path: str, body: dict) -> dict:
    """POST to DeepSeek (through the proxy, if any), cached for CACHE_SECONDS: the same query costs nothing again, in
    any process. Raises httpx.HTTPError, or _Down while the web is not asked."""

    def load() -> dict:
        if time.monotonic() < _down[0]:
            raise _Down
        resp = _client().post(path, json=body, headers={"Authorization": f"Bearer {settings.deepseek_api_key.get_secret_value()}"})  # type: ignore[union-attr]
        resp.raise_for_status()
        return resp.json()

    asked = hashlib.sha256(f"{path} {json.dumps(body, sort_keys=True, ensure_ascii=False)}".encode()).hexdigest()
    return cache.cached(f"deepseek:{asked}", CACHE_SECONDS, load)


def _run_calls(runtime: ToolRuntime) -> list[str]:
    """The names of the tools whose results came back since the helper got the question."""
    messages = runtime.state.get("messages", []) if runtime.state else []
    start = max((i for i, m in enumerate(messages) if isinstance(m, HumanMessage)), default=-1)
    return [m.name or "" for m in messages[start + 1 :] if isinstance(m, ToolMessage)]


def _failed(e: httpx.HTTPError | _Down) -> str:
    """What the helper is told; a failure that will not pass in a moment stops the web for DOWN_SECONDS."""
    global _down
    if isinstance(e, _Down):
        return _down[1]
    status = e.response.status_code if isinstance(e, httpx.HTTPStatusError) else None
    if status is None:  # (the proxy refused, closed or did not answer, or DeepSeek could not be reached)
        via = "through DEEPSEEK_PROXY" if settings.deepseek_proxy else "(no DEEPSEEK_PROXY)"
        log.warning("DeepSeek cannot be reached %s: %s", via, type(e).__name__)
        say = "The web search is not available now (it cannot be reached): report without it."
    elif status in (401, 403):
        log.warning("DeepSeek refused (%s)", status)
        say = "The web search is not available now (it was refused): report without it."
    elif status in (402, 429):
        log.warning("DeepSeek is out of its balance or request limit (%s)", status)
        say = "The web search is out of its limit for now: report without it."
    else:
        log.warning("DeepSeek failed: %s", status)
        say = "The web search did not answer: report without it."
        if status < 500 and status != 408:
            return say
    _down = (time.monotonic() + DOWN_SECONDS, say)
    return say


def _text(value: str | None, limit: int) -> str:
    text = " ".join((value or "").split())
    return text if len(text) <= limit else text[:limit].rstrip() + " [...cut]"


class SearchWebArgs(BaseModel):
    query: str = Field(min_length=1, max_length=QUERY_CHARS, description="What to find, as a search engine query, in the language "
                       f"of the pages wanted. At most {OFFICIAL_QUERY_CHARS} characters for official sites, {QUERY_CHARS} with anywhere=true.")
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
    limit = QUERY_CHARS if anywhere else OFFICIAL_QUERY_CHARS
    if not query.strip() or len(query) > limit:
        return collector.result({"error": f"Use a nonblank search query of at most {limit} characters."}, "search_web")
    queries = [query] if anywhere else _official_queries(query)
    try:
        found = []
        for q in queries:
            body = {"query": q, "count": MAX_RESULTS, "need_content": False}
            found.extend(_deepseek("/v1/tools/search", body).get("results") or [])
    except (httpx.HTTPError, _Down) as e:
        return collector.result({"error": _failed(e)}, "search_web")
    results = []
    seen: set[str] = set()
    for hit in sorted(found, key=lambda r: r.get("rerank_score") or 0, reverse=True):
        url, is_official = hit.get("url") or "", official(hit.get("url") or "")
        if url in seen or not url.startswith(("https://", "http://")) or (not anywhere and not is_official):
            continue
        seen.add(url)
        item = {"ref": collector.add_web(_text(hit.get("title"), 150) or url, url, is_official), "title": _text(hit.get("title"), 150),
                "url": url, "official_site": is_official, "date": (hit.get("date") or "")[:10] or None,
                "text": _text(hit.get("summary") or hit.get("snippet") or hit.get("content"), TEXT_CHARS)}  # fmt: skip
        results.append({k: v for k, v in item.items() if v is not None})
        if len(results) >= MAX_RESULTS:
            break
    payload: dict = {"total": len(results), "results": results}
    if not results:
        payload["note"] = "Nothing found on the web." if anywhere else "Nothing found on the sites of the university and the city."
    elif any(not r["official_site"] for r in results):
        payload["note"] = "Pages off the official sites (official_site false) may be wrong or old: say where a fact comes from."
    return collector.result(payload, "search_web", {"relevant": [r["ref"] for r in results]})


def _official_queries(query: str) -> list[str]:
    """Keep the query intact; pack site: clauses into as few requests as the API's character limit permits."""
    queries, sites = [], ""
    for site in OFFICIAL_SITES:
        candidate = f"{sites} OR site:{site}" if sites else f"site:{site}"
        if len(f"{query} {candidate}") > QUERY_CHARS:
            queries.append(f"{query} {sites}")
            sites = f"site:{site}"
        else:
            sites = candidate
    return [*queries, f"{query} {sites}"]


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
    try:
        data = _deepseek("/v1/tools/fetch", {"url": url})
    except (httpx.HTTPError, _Down) as e:
        if isinstance(e, httpx.HTTPStatusError) and e.response.status_code in (403, 404):
            return collector.result({"error": "The page could not be read: report with the search result."}, "read_web_page")
        return collector.result({"error": _failed(e)}, "read_web_page")
    if not data.get("content"):
        return collector.result({"error": "The page could not be read: report with the search result."}, "read_web_page")
    ref = collector.add_web(url, url, official(url))  # (the ref of the search result: the same page keeps its ref)
    return collector.result({"ref": ref, "url": url, "text": _text(data["content"], PAGE_CHARS)}, "read_web_page")


WEB_TOOLS = [search_web, read_web_page]
