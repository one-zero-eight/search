"""Read-only catalogue of the current user's Telegram sources and configured modes."""
from typing import Literal

from fastapi import APIRouter, Response
from pydantic import BaseModel

from catix import groups, sources
from catix.api.auth import VerifiedDep

router = APIRouter(prefix="/sources", tags=["Sources"])


class SourceTopicView(BaseModel):
    topic_id: str
    title: str
    mode: Literal["store", "search", "off"]


class SourceView(BaseModel):
    chat_id: str
    title: str
    group_code: str
    forum: bool
    default_mode: Literal["store", "search", "off"]
    topics: list[SourceTopicView]
    has_stored_messages: bool


class SourcesView(BaseModel):
    verified_groups: list[str]
    sources: list[SourceView]


@router.get("", response_model=SourcesView)
def list_sources(user: VerifiedDep, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    verified = groups.website_groups(user.token.get_secret_value() if user.token else None)
    return {"verified_groups": verified, "sources": sources.website_sources(verified)}
