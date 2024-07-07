from fastapi import APIRouter

from src.api.dependencies import ComputerServiceDep
from src.exceptions import IncorrectCredentialsException
from src.modules.compute.schemas import Result, SearchTask, PdfTask, Task

router = APIRouter(prefix="/compute", tags=["Compute"])


@router.get(
    "/tasks/pending",
    responses={200: {"description": "Success"}, **IncorrectCredentialsException.responses},
)
async def get_tasks(_: ComputerServiceDep) -> list[Task]:
    return [SearchTask(id=i, query=f"query_{i}") for i in range(3)] + [
        PdfTask(id=i, pdf_url="https://pdfobject.com/pdf/sample.pdf") for i in range(3)
    ]


@router.post("/tasks/completed", responses={200: {"description": "Success"}})
async def mark_task_as_completed(results: list[Result], _: ComputerServiceDep) -> None:
    print(f"Marking tasks as completed: {results}")
