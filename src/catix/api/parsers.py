"""Manual incremental source updates. No autopilot, agent, git commits or pushes."""

import fcntl
import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from catix.api.auth import VerifiedDep
from catix.api.schemas import InfoSources
from catix.settings import settings
from catix.wiki import compile as compiler
from catix.wiki import lint, search_index
from catix.wiki.paths import DATA
from catix.wiki.sources import eduwiki
from catix.wiki.sources import sites as site_source

router = APIRouter()
log = logging.getLogger(__name__)
LOCK = DATA / ".autopilot.lock"  # shared with autopilot.main, including other API worker processes
Section = InfoSources | Literal["wiki", "sites"]


class ParseResult(BaseModel):
    section: str
    sites: list[str] = Field(default_factory=list)
    changed: int = 0
    processed: bool = False
    indexed: bool = False
    index: dict[str, int] = Field(default_factory=dict)
    embedded: int = 0


class SiteChoice(BaseModel):
    name: str
    url: str
    about: str


@router.get("/sites", tags=["Parsers"])
def list_sites(_auth: VerifiedDep) -> list[SiteChoice]:
    """Names accepted by the parser, from the same catalog as sites.fetch (including pending sites)."""
    return [SiteChoice(name=name, url=site.base, about=site.about) for name, site in sorted(site_source.every_site().items())]


def selected_sites(section: str, names: list[str] | None) -> list[str]:
    if section in {"moodle", "clubs", "maps", "residents"}:
        raise HTTPException(410, f"No parser for {section}; use sites to select a configured website")
    if section not in {"sites", "resources", "hotel", "campuslife"}:
        if names is not None:
            raise HTTPException(400, "sites is only supported for website resources")
        return []
    catalog = site_source.every_site()
    if section in {"hotel", "campuslife"}:
        if names is not None and set(names) != {section}:
            raise HTTPException(400, f"Use /sites/parse to select sites other than {section}")
        names = [section]
    selected = list(dict.fromkeys(names)) if names is not None else sorted(catalog)
    if unknown := [name for name in selected if name not in catalog]:
        raise HTTPException(400, detail={"unknown_sites": unknown, "available_sites": sorted(catalog)})
    return selected


@router.post("/{section}/parse", responses={
    400: {"description": "Invalid site selection or flags"},
    401: {"description": "Unauthorized"},
    409: {"description": "Wiki update already running or bundle failed lint"},
    410: {"description": "Source has no parser"},
    502: {"description": "Source update or processing failed"},
    503: {"description": "Indexing is not configured"},
})
def run_parse_route(
    _auth: VerifiedDep,
    section: Section,
    indexing_is_needed: bool = True,
    parsing_is_needed: bool = True,
    sites: list[str] | None = Query(default=None, description="Names from GET /sites; repeat to select several. Omit for all sites."),
) -> ParseResult:
    """Fetch new/changed pages and process only when fetch reports changes.

    wiki/eduwiki reads MediaWiki; sites/resources reads configured websites; hotel/campuslife selects that site.
    The response waits for completion; blocking work runs in FastAPI's thread pool. No autopilot or agent is started.
    parsing_is_needed=false rebuilds and indexes the cached source without fetching (also retries a failed processing step).
    indexing_is_needed=false only updates the snapshot and bundle. Website links retain sites.fetch's trusted-site traversal.
    """
    result = ParseResult(section=section, sites=selected_sites(section, sites))
    if not parsing_is_needed and not indexing_is_needed:
        raise HTTPException(400, "Enable parsing or indexing")
    if indexing_is_needed and not settings.database_url:
        raise HTTPException(503, "Indexing requires DATABASE_URL; use indexing_is_needed=false to only update pages")
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise HTTPException(409, "A wiki update is already running") from None
        try:
            return update(result, parsing_is_needed, indexing_is_needed)
        except HTTPException:
            raise
        except Exception:
            log.exception("Parser failed for %s", section)
            raise HTTPException(502, "Source update failed; see server logs. Cached data is kept for retry.") from None


def update(result: ParseResult, parsing: bool, indexing: bool) -> ParseResult:
    """The caller holds the shared wiki lock for the entire fetch/compile/index chain."""
    wiki = result.section in {"wiki", "eduwiki"}
    if parsing:
        if wiki:
            result.changed = eduwiki.fetch([0])
        elif result.sites:
            result.changed = site_source.fetch(result.sites)
    if result.changed or not parsing:
        if wiki:
            compiler.compile_pages(None)
        else:
            site_source.compile_all()
        compiler.link()
        result.processed = True
        if indexing:
            if errors := lint.lint():
                raise HTTPException(409, f"Bundle has {errors} lint errors; index not updated")
            result.index = search_index.sync()
            result.embedded = search_index.embed_all()
            result.indexed = True
    return result
