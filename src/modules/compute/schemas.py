from typing import Any, Literal, Annotated

from pydantic import BaseModel, Discriminator, TypeAdapter

TaskTypes = Literal["search", "process-pdf"]


class TaskBase(BaseModel):
    id: int


class PdfTask(TaskBase):
    type: Literal["process-pdf"] = "process-pdf"
    pdf_url: str


class SearchTask(TaskBase):
    type: Literal["search"] = "search"
    query: str


Task = Annotated[PdfTask | SearchTask, Discriminator("type")]
TaskAdapter = TypeAdapter(Task)


class Result(BaseModel):
    task_id: int
    task_type: TaskTypes
    status: str
    result: Any
