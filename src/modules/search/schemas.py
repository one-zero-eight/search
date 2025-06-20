import re
from typing import Annotated, Literal

from beanie import PydanticObjectId
from pydantic import Discriminator, model_validator

from src.custom_pydantic import CustomModel
from src.storages.mongo import MoodleEntry


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


Sources: type = Annotated[
    MoodleFileSource | MoodleUrlSource | MoodleUnknownSource | TelegramSource, Discriminator("type")
]


class MoodleEntryWithScore(MoodleEntry):
    score: float | list[float] | None = None
    "Score of the search response. Multiple scores if was an aggregation of multiple chunks."


class SearchResponse(CustomModel):
    source: Sources
    "Relevant source for the search."
    score: float | list[float] | None = None
    "Score of the search response. Multiple scores if was an aggregation of multiple chunks. Optional."


class SearchResponses(CustomModel):
    searched_for: str
    "Text that was searched for."
    responses: list[SearchResponse]
    "Responses to the search query."
    search_query_id: PydanticObjectId | None = None
    "Assigned search query index"
