"""The request and response models of the API: the same JSON as the search service had before cAtIx replaced it."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Discriminator

from catix.attachments import AttachmentInfo


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


class ArchiveDocument(BaseModel):
    page: str
    "Exact wiki page of the cited archive member."
    revision: str
    "Indexed page fingerprint; a different revision must not be substituted."
    member: str
    "Original filename including its path inside the archive."


class EduwikiSource(SiteBaseSource):
    type: Literal[InfoSources.eduwiki] = InfoSources.eduwiki
    breadcrumbs: list[str] = ["EduWiki"]
    archive_document: ArchiveDocument | None = None


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
    end_suggested: bool = False
    "The end is an explicit 90-minute proposal, not a source-provided duration."
    all_day: bool = False
    "The answer names the day only, not the time."
    room: str | None = None
    source_url: str | None = None
    "Where the event comes from (a message of a chat)."


class AddedCalendarEvent(BaseModel):
    proposal_id: str
    title: str
    "The title of the event as it is in the calendar."


class AskAction(BaseModel):
    name: str
    "The action: book_music_room, book_room, enroll_in_event or cancel_booking."
    description: str
    "What is to be done for the user, in the language of the question, to show them."


class AskApproval(BaseModel):
    id: str
    "Which wait this is: pass it as `approval_id` of the decision, so that it is not taken for a later one."
    actions: list[AskAction]
    "What the assistant is about to do for the user in InNoHassle. Nothing is done before the user decides: POST /ask/{chat_id}/decision."


class AskResponses(BaseModel):
    query: str
    answer: str
    attachments: list[AttachmentInfo] = []
    "Private files attached to this question, also retained through approval and in chat history."
    chat_id: str | None = None
    "Assigned chat index"
    ask_query_id: str | None = None
    "Assigned ask query index"
    search_responses: list[SearchResponse]
    "Responses to the search query."
    calendar_events: list[CalendarEventOffer] = []
    "Upcoming events the answer names (an exam, a deadline), offered for the user's calendar: a button each."
    messages: list
    "Chat history for llm (do not show on frontend). Empty in a chat's history (GET /ask/chats/{chat_id})."
    feedback: Literal["like", "dislike"] | None = None
    "The user's 👍 (`like`) or 👎 (`dislike`) on the answer, in a chat's history."
    feedback_comment: str | None = None
    "What the user said of the answer with their vote, in a chat's history."
    approval: AskApproval | None = None
    "The answer is not there yet: the assistant waits for the user's decision on these actions (`answer` says so). The decision "
    "(POST /ask/{chat_id}/decision) gives the answer; a new question in the chat instead drops them undone."


class AskChat(BaseModel):
    chat_id: str
    title: str
    "The first question of the chat."
    created_at: datetime
    updated_at: datetime
    "When the last answer was given."


class AskChatHistory(AskChat):
    answers: list[AskResponses]
    "The questions with their answers, the oldest first, as POST /ask/ gave them, with the user's votes."
    waiting: AskResponses | None = None
    "The last question, when the assistant waits for the user's decision on its `approval` (POST /ask/{chat_id}/decision)."


class AskDecision(BaseModel):
    decision: Literal["approve", "reject"]
    "Do the actions of the chat's `approval` (approve) or not (reject)."
    approval_id: str | None = None
    "The `id` of the approval decided on; when it is not the one waiting, nothing is done (409)."


class ActResponses(BaseModel):
    query: str
    answer: str
    act_query_id: str | None = None
    "Assigned act query index"
    tool_calls: list
    "Which tools were used."
    messages: list
    "Chat history for llm (do not show on frontend)."
