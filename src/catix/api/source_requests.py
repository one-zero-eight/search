"""Owner-only source submission/status; invitations and moderation identities stay server-side."""
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from catix import groups, source_requests
from catix.api.auth import VerifiedDep

router = APIRouter(prefix="/sources", tags=["Sources"])


class SourceRequestCreate(BaseModel):
    invite_link: str = Field(max_length=160, repr=False)
    group_code: str = Field(max_length=40)
    comment: str = Field(default="", max_length=2000)
    consent: Literal[True]

    @field_validator("consent", mode="before")
    @classmethod
    def explicit_consent(cls, value):
        if value is not True:
            raise ValueError("Explicit consent is required")
        return value


class SourceRequestView(BaseModel):
    id: str = Field(pattern=r"^[0-9a-f]{32}$")
    group_code: str
    comment: str
    status: Literal["pending", "approved", "joining", "waiting_join", "connected", "failed", "rejected"]
    message: str | None
    title: str | None
    created_at: datetime


class SourceRequestsView(BaseModel):
    requests: list[SourceRequestView]
    verified_groups: list[str]


@router.get("/requests", response_model=SourceRequestsView)
def list_requests(user: VerifiedDep):
    verified = groups.website_groups(user.token.get_secret_value() if user.token else None)
    return {"requests": source_requests.list_owned(user.innohassle_id), "verified_groups": verified}


@router.post("/requests", response_model=SourceRequestView, status_code=201)
def create_request(body: SourceRequestCreate, user: VerifiedDep):
    code = groups.normalize(body.group_code)
    if not code:
        raise HTTPException(422, "A valid study group or all is required")
    if code != groups.ALL and code not in groups.website_groups(user.token.get_secret_value() if user.token else None):
        raise HTTPException(403, "Select one of your verified study groups or all cAtIx users. Reload the form to refresh your groups.")
    try:
        return source_requests.submit(user.innohassle_id, user.email, body.invite_link, body.group_code, body.comment, consent=body.consent)
    except source_requests.RateLimited as e:
        raise HTTPException(429, str(e), headers={"Retry-After": "86400"}) from None
    except source_requests.ExistingRequest as e:
        raise HTTPException(409, str(e)) from None
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
