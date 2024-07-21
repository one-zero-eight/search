from fastapi import APIRouter

from src.api.dependencies import ComputerServiceDep
from src.exceptions import IncorrectCredentialsException
from src.modules.moodle.repository import moodle_repository

router = APIRouter(prefix="/compute", tags=["Compute"])


@router.get(
    "/corpora",
    responses={200: {"description": "Success"}, **IncorrectCredentialsException.responses},
)
async def get_corpora(_: ComputerServiceDep):
    moodle_entries = await moodle_repository.read_all()

    return {"moodle_entries": moodle_entries}
