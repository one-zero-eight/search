from inspect import cleandoc
from typing import Literal, Annotated, TypeAlias

from beanie import Document
from pydantic import ConfigDict, Discriminator

from src.custom_pydantic import CustomModel


class PdfLocation(CustomModel):
    page_index: int


class MoodleSource(CustomModel):
    type: Literal["moodle"] = "moodle"
    course_id: int
    course_name: str
    module_id: int
    module_name: str
    data_id: int
    display_name: str
    resource_type: Literal["pdf"]
    resource_download_url: str
    resource_preview_url: str
    preview_location: PdfLocation | None = None


class TelegramSource(CustomModel):
    type: Literal["telegram"] = "telegram"
    chat_username: str
    chat_title: str
    message_id: int
    link: str


Sources: TypeAlias = Annotated[MoodleSource | TelegramSource, Discriminator("type")]


class SearchResponse(CustomModel):
    markdown_text: str
    sources: list[Sources]


def _example() -> dict:
    md_text = cleandoc(
        """
    # Computer Architecture. Week 2

    ### Content of the Class:

    - The role of performance characteristics and their relation to computer speed
    - The measurement of performance characteristics
    - Decision-making based on various performance metrics
    - Programs to determine comprehensive performance indexes
    """
    )

    return dict(
        responses=[
            dict(
                markdown_text=md_text,
                sources=[
                    dict(
                        type="moodle",
                        course_id=1114,
                        course_name="[F22] Fundamentals of Computer Architecture",
                        module_id=82752,
                        module_name="Week 01 - 01 August 2022",
                        data_id=82752,
                        display_name="Lecture 2 Slides Файл",
                        resource_type="pdf",
                        resource_download_url="https://ontheline.trincoll.edu/images/bookdown/sample-local-pdf.pdf",
                        resource_preview_url="https://ontheline.trincoll.edu/images/bookdown/sample-local-pdf.pdf",
                        preview_location=dict(page_index=1),
                    ),
                    dict(
                        type="telegram",
                        chat_username="one_zero_eight",
                        chat_title="one-zero-eight – 108",
                        message_id=63,
                        link="https://t.me/one_zero_eight/63",
                    ),
                ],
            )
        ]
    )


class SearchResponses(CustomModel):
    responses: list[SearchResponse]

    model_config = ConfigDict(json_schema_extra={"examples": [_example()]})


# TODO: Move from schemas to separate file
class SearchResponseDocument(Document):
    """
    Don't mind it is in schemas for now. Subject to change
    """

    responses: list[SearchResponse]

    class Config:
        json_schema_extra = {"examples": [_example()]}

    class Settings:
        collection = "search_responses"


async def create_search_response():
    example_data = _example()
    search_response_document = SearchResponseDocument(**example_data)
    await search_response_document.insert()


async def read_search_responses():
    responses: list[SearchResponseDocument] = await SearchResponseDocument.find_all().to_list()
    return responses


async def delete_search_response(response_id):
    response = await SearchResponseDocument.get(response_id)
    if response:
        await response.delete()
