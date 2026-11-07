"""POST /{section}/parse: a request for the wiki's own run, not an update made here. The API never writes the wiki (its
checkout is read-only in docker-compose.prod.yml): it queues the request in Redis (catix.wiki.parse_requests), and
`catix-wiki autopilot` asks the source with its checks, commits to `wiki` and pushes, or sends the changes for review. The
server's index follows the branch (scripts/wiki-pull.sh). GET /parse/{id} tells where the request is."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from catix.api.auth import VerifiedDep
from catix.api.schemas import InfoSources
from catix.wiki import parse_requests
from catix.wiki.sources import sites as site_source

router = APIRouter()
Section = InfoSources | Literal["wiki", "sites"]
SOURCE_OF = {"wiki": "eduwiki", "eduwiki": "eduwiki", "sites": "sites", "resources": "sites", "hotel": "sites", "campuslife": "sites"}


class ParseRequest(BaseModel):
    id: str
    section: str
    source: Literal["eduwiki", "sites"]
    sites: list[str] = Field(default_factory=list, description="The sites the run reads (names of GET /sites)")
    parsing: bool = Field(True, description="False: no source is asked, the run builds and checks the data it holds")
    status: Literal["queued", "running", "done", "failed"]
    outcome: Literal["", "committed", "review", "unchanged", "error"] = Field(
        "", description="done: committed to the `wiki` branch (the search has it after the server pulls it), review (the "
                        "changes failed a check and wait for a person in a branch wiki-review/...) or unchanged; failed: error")
    result: str = Field("", description="What the wiki's run did, in its own words")
    created_at: str
    started_at: str = ""
    finished_at: str = ""

    @classmethod
    def of(cls, request: parse_requests.Request) -> "ParseRequest":
        return cls.model_validate({k: v for k, v in vars(request).items() if k in cls.model_fields})


class SiteChoice(BaseModel):
    name: str
    url: str
    about: str


@router.get("/sites", tags=["Parsers"])
def list_sites(_auth: VerifiedDep) -> list[SiteChoice]:
    """Names accepted by the parser: trusted configured sites from sites.SITES."""
    site_source.reload_catalog()
    return [SiteChoice(name=name, url=site.base, about=site.about) for name, site in sorted(site_source.SITES.items())]


def selected_sites(section: str, names: list[str] | None) -> list[str]:
    if section in {"moodle", "clubs", "maps", "residents"}:
        raise HTTPException(410, f"No parser for {section}; use sites to select a configured website")
    if SOURCE_OF[section] != "sites":
        if names is not None:
            raise HTTPException(400, "sites is only supported for website resources")
        return []
    site_source.reload_catalog()
    catalog = site_source.SITES
    if section in {"hotel", "campuslife"}:
        if names is not None and set(names) != {section}:
            raise HTTPException(400, f"Use /sites/parse to select sites other than {section}")
        names = [section]
    selected = list(dict.fromkeys(names)) if names is not None else sorted(catalog)
    if unknown := [name for name in selected if name not in catalog]:
        raise HTTPException(400, detail={"unknown_sites": unknown, "available_sites": sorted(catalog)})
    if not selected:
        raise HTTPException(400, "No trusted sites to read")
    return selected


@router.post("/{section}/parse", status_code=202, responses={
    400: {"description": "Invalid site selection or flags"},
    401: {"description": "Unauthorized"},
    410: {"description": "Source has no parser"},
    503: {"description": "The queue of the wiki's run (Redis) is not configured or does not answer"},
})
def run_parse_route(
    _auth: VerifiedDep,
    section: Section,
    indexing_is_needed: bool = Query(True, deprecated=True, description="Ignored: the wiki's run always checks and indexes "
                                     "what it commits, and the server's index follows the `wiki` branch"),
    parsing_is_needed: bool = True,
    sites: list[str] | None = Query(default=None, description="Names from GET /sites; repeat to select several. Omit for all sites."),
) -> ParseRequest:
    """Queue an update of the source for the wiki's own run and answer at once (202) with the request; GET /parse/{id} follows it.

    wiki/eduwiki: the pages of the eduwiki whose revision changed; sites/resources: the trusted sites named (all of them when
    none is), their pages and the documents they link; hotel/campuslife: that site. The run (`catix-wiki autopilot`) asks the
    source, builds the pages, runs its checks (lint, cards, search, answers) and commits to the `wiki` branch, or sends the
    changes to a review branch when a check fails. parsing_is_needed=false asks no source: the run builds and checks the data
    it already holds. The same request still waiting is queued once: asking again answers with it.
    """
    names = selected_sites(section, sites)
    if not parsing_is_needed and not indexing_is_needed:
        raise HTTPException(400, "Enable parsing or indexing")
    try:
        request = parse_requests.submit(section, SOURCE_OF[section], names, parsing_is_needed)
    except parse_requests.Unavailable as e:
        raise HTTPException(503, str(e)) from None
    return ParseRequest.of(request)


@router.get("/parse/{request_id}", tags=["Parsers"], responses={404: {"description": "No such request (or finished long ago)"},
                                                              503: {"description": "The queue (Redis) does not answer"}})
def parse_status(_auth: VerifiedDep, request_id: str) -> ParseRequest:
    """Where a request of POST /{section}/parse is: queued, running, done (with what the run did) or failed."""
    try:
        request = parse_requests.get(request_id)
    except parse_requests.Unavailable as e:
        raise HTTPException(503, str(e)) from None
    if request is None:
        raise HTTPException(404, "No such request")
    return ParseRequest.of(request)
