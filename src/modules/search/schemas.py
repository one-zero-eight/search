import re
from typing import Literal, Annotated, TypeAlias

from beanie import PydanticObjectId
from pydantic import ConfigDict, Discriminator, model_validator

from src.custom_pydantic import CustomModel


class PdfLocation(CustomModel):
    page_index: int
    "Page index in the PDF file. Starts from 1."


class MoodleSource(CustomModel):
    type: Literal["moodle"] = "moodle"
    display_name: str = "-"
    "Display name of the resource."
    breadcrumbs: list[str] = ["Moodle"]
    "Breadcrumbs to the resource."
    course_id: int
    "Course ID in the Moodle system."
    course_name: str
    "Course name in the Moodle system."
    module_id: int
    "Module ID in the Moodle system (resources)."
    module_name: str
    "Module name in the Moodle system."
    resource_type: str
    "Type of the resource."
    filename: str | None = None
    "Filename of the resource."
    link: str
    "Anchor URL to the resource on Moodle."
    resource_preview_url: str
    "URL to get the preview of the resource."
    resource_download_url: str
    "URL to download the resource."
    preview_location: PdfLocation | None = None

    @model_validator(mode="before")
    def set_breadcrumbs_and_display_name(cls, data):
        if "course_name" not in data or "module_name" not in data:
            return data
        course_name = data["course_name"]
        # remove "/ Глубокое обучение для задач поиска" from "[Sum24] Deep Learning for Search / Глубокое обучение
        # для задач поиска"
        course_name = course_name.split(" / ")[0]
        data["breadcrumbs"] = ["Moodle", course_name, data["module_name"]]
        data["display_name"] = data["module_name"]
        return data


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


Sources: TypeAlias = Annotated[MoodleSource | TelegramSource, Discriminator("type")]


class SearchResponse(CustomModel):
    source: Sources
    "Relevant source for the search."
    score: float | None = None
    "Score of the search response. Optional."


def _example() -> dict:
    return dict(
        searched_for="computer architecture",
        responses=[
            dict(
                source=dict(
                    type="moodle",
                    course_id=1114,
                    course_name="[F22] Fundamentals of Computer Architecture",
                    module_id=82752,
                    module_name="Week 01 - 01 August 2022",
                    display_name="Lecture 2 Slides",
                    resource_type="pdf",
                    resource_download_url="https://ontheline.trincoll.edu/images/bookdown/sample-local-pdf.pdf",
                    resource_preview_url="https://ontheline.trincoll.edu/images/bookdown/sample-local-pdf.pdf",
                    link="https://moodle.innopolis.university/course/view.php?id=1114#module-82752",
                    preview_location=dict(page_index=1),
                ),
                score=0.5,
            ),
            dict(
                source=dict(
                    type="telegram",
                    chat_username="one_zero_eight",
                    chat_title="one-zero-eight – 108",
                    message_id=63,
                    link="https://t.me/one_zero_eight/63",
                ),
                score=0.3,
            ),
        ],
    )


class SearchResponses(CustomModel):
    searched_for: str
    "Text that was searched for."
    responses: list[SearchResponse]
    "Responses to the search query."
    search_query_id: PydanticObjectId | None = None
    "Assigned search query index"

    model_config = ConfigDict(json_schema_extra={"examples": [_example()]})
