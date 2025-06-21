import re
from typing import Annotated, Generic, Literal, TypeVar

from beanie import PydanticObjectId
from pydantic import BaseModel, Discriminator, model_validator

from src.custom_pydantic import CustomModel
from src.storages.mongo import CampusLifeEntry, EduWikiEntry, HotelEntry


class PdfLocation(CustomModel):
    page_index: int
    "Page index in the PDF file. Starts from 1."


class MoodleSourceBase(CustomModel):
    display_name: str = "-"
    "Display name of the resource."
    breadcrumbs: list[str] = ["Moodle"]
    "Breadcrumbs to the resource."
    link: str
    "Anchor URL to the resource on Moodle."

    def set_breadcrumbs_and_display_name(
        self, course_name: str, module_name: str, filename: str, within_folder: bool = False
    ):
        # remove "/ Глубокое обучение для задач поиска" from "[Sum24] Deep Learning for Search / Глубокое обучение
        # для задач поиска"
        course_name = course_name.split(" / ")[0]
        self.breadcrumbs = ["Moodle", course_name, module_name]
        if within_folder:
            self.display_name = f"{module_name} / {filename}"
        else:
            self.display_name = module_name


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


class TelegramSource(CustomModel):
    type: Literal["telegram"] = "telegram"
    display_name: str = "-"
    "Display name of the resource."
    breadcrumbs: list[str] = ["Telegram"]
    "Breadcrumbs to the resource."
    chat_username: str
    "Username of the chat, channel, group"
    chat_title: str
    "Title of the chat, channel, group"
    message_id: int
    "Message ID in the chat"
    link: str
    "Link to the message"

    @model_validator(mode="before")
    def set_breadcrumbs(cls, data):
        if "chat_title" not in data:
            return data
        data["breadcrumbs"] = ["Telegram", data["chat_title"]]
        display_name = ""
        text = data.get("text") or data.get("caption")

        if text:
            # get first line of the message
            display_name = text.split("\n")[0]
            # only normal characters
            display_name = re.sub(r"[^a-zA-Z0-9 ]", "", display_name)
        data["display_name"] = display_name or "-"
        return data


class EduWikiSource(BaseModel):
    type: Literal["eduwiki"] = "eduwiki"
    inner: EduWikiEntry


class HotelSource(BaseModel):
    type: Literal["hotel"] = "hotel"
    inner: HotelEntry


class CampusLifeSource(BaseModel):
    type: Literal["campus-life"] = "campus-life"
    inner: CampusLifeEntry


Sources = Annotated[
    EduWikiSource
    | HotelSource
    | CampusLifeSource
    | MoodleFileSource
    | MoodleUrlSource
    | MoodleUnknownSource
    | TelegramSource,
    Discriminator("type"),
]

T = TypeVar("T")


class WithScore(BaseModel, Generic[T]):
    score: float | list[float] | None = None
    "Score of the search response. Multiple scores if was an aggregation of multiple chunks."
    inner: T


class SearchResponse(CustomModel):
    score: float | list[float] | None = None
    "Score of the search response. Multiple scores if was an aggregation of multiple chunks. Optional."
    source: Sources
    "Relevant source for the search."


class SearchResponses(CustomModel):
    searched_for: str
    "Text that was searched for."
    responses: list[SearchResponse]
    "Responses to the search query."
    search_query_id: PydanticObjectId | None = None
    "Assigned search query index"
