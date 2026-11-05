"""The request and response models of the API: the same JSON as the search service had before cAtIx replaced it."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Discriminator


class InfoSources(StrEnum):
    moodle = "moodle"
    eduwiki = "eduwiki"
    clubs = "clubs"
    campuslife = "campuslife"
    hotel = "hotel"
    maps = "maps"
    residents = "residents"
    resources = "resources"


ALL_SOURCES = list(InfoSources)


class Resources(StrEnum):
    innohassle = "innohassle"
    myuni = "myuni"
    ithelp = "ithelp"
    academic_calendar = "academic_calendar"
    psychologist = "psychologist"
    university_events = "university_events"
    university_store = "university_store"


class PdfLocation(BaseModel):
    page_index: int
    "Page index in the PDF file. Starts from 1."


class MoodleSourceBase(BaseModel):
    display_name: str = "-"
    "Display name of the resource."
    breadcrumbs: list[str] = ["Moodle"]
    "Breadcrumbs to the resource."
    link: str
    "Anchor URL to the resource on Moodle."


class MoodleFileSource(MoodleSourceBase):
    type: Literal["moodle-file"] = "moodle-file"
    resource_preview_url: str | None = None
    "URL to get the preview of the resource."
    resource_download_url: str | None = None
    "URL to download the resource."
    preview_location: PdfLocation | None = None


class MoodleUrlSource(MoodleSourceBase):
    type: Literal["moodle-url"] = "moodle-url"
    url: str
    "URL of the resource"


class MoodleUnknownSource(MoodleSourceBase):
    type: Literal["moodle-unknown"] = "moodle-unknown"


class SiteBaseSource(BaseModel):
    display_name: str = "-"
    url: str
    preview_text: str


class EduwikiSource(SiteBaseSource):
    type: Literal[InfoSources.eduwiki] = InfoSources.eduwiki
    breadcrumbs: list[str] = ["EduWiki"]


class CampusLifeSource(SiteBaseSource):
    type: Literal[InfoSources.campuslife] = InfoSources.campuslife
    breadcrumbs: list[str] = ["Campus life"]


class HotelSource(SiteBaseSource):
    type: Literal[InfoSources.hotel] = InfoSources.hotel
    breadcrumbs: list[str] = ["Hotel"]


class ResidentsSource(SiteBaseSource):
    type: Literal[InfoSources.residents] = InfoSources.residents
    breadcrumbs: list[str] = ["Residents"]


class ClubsSource(SiteBaseSource):
    type: Literal[InfoSources.clubs] = InfoSources.clubs
    breadcrumbs: list[str] = ["Clubs"]


class MapsSource(SiteBaseSource):
    type: Literal[InfoSources.maps] = InfoSources.maps
    breadcrumbs: list[str] = ["Maps"]


class ResourcesSource(SiteBaseSource):
    type: Literal[InfoSources.resources] = InfoSources.resources
    resource_type: Resources
    breadcrumbs: list[str] = ["Resources"]


Sources = Annotated[
    EduwikiSource
    | CampusLifeSource
    | HotelSource
    | ClubsSource
    | MapsSource
    | MoodleFileSource
    | MoodleUrlSource
    | MoodleUnknownSource
    | ResidentsSource
    | ResourcesSource,
    Discriminator("type"),
]


class SearchResponse(BaseModel):
    score: float | list[float] | None = None
    "Score of the search response. Multiple scores if was an aggregation of multiple chunks. Optional."
    source: Sources
    "Relevant source for the search."


class SearchResponses(BaseModel):
    searched_for: str
    "Text that was searched for."
    responses: list[SearchResponse]
    "Responses to the search query."
    search_query_id: str | None = None
    "Assigned search query index"


class PageText(BaseModel):
    title: str
    url: str
    "Address of the original page."
    text: str
    "The page as markdown."


class CalendarEventOffer(BaseModel):
    id: str
    "Pass it to POST /users/my-calendar/events/{proposal_id} to add the event to the user's calendar (for 48 hours)."
    title: str
    starts_at: datetime
    "Start; for an all-day event the day (its time means nothing)."
    ends_at: datetime | None = None
    all_day: bool = False
    "The answer names the day only, not the time."
    room: str | None = None
    source_url: str | None = None
    "Where the event comes from (a message of a chat)."


class AddedCalendarEvent(BaseModel):
    proposal_id: str
    title: str
    "The title of the event as it is in the calendar."


class AskResponses(BaseModel):
    query: str
    answer: str
    chat_id: str | None = None
    "Assigned chat index"
    ask_query_id: str | None = None
    "Assigned ask query index"
    search_responses: list[SearchResponse]
    "Responses to the search query."
    calendar_events: list[CalendarEventOffer] = []
    "Upcoming events the answer names (an exam, a deadline), offered for the user's calendar: a button each."
    messages: list
    "Chat history for llm (do not show on frontend)."


class ActResponses(BaseModel):
    query: str
    answer: str
    act_query_id: str | None = None
    "Assigned act query index"
    tool_calls: list
    "Which tools were used."
    messages: list
    "Chat history for llm (do not show on frontend)."
