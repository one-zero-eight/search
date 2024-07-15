from fastapi import APIRouter

from src.api.dependencies import ComputerServiceDep
from src.api.logging_ import logger
from src.exceptions import IncorrectCredentialsException
from src.modules.compute.schemas import SearchResult, SearchTask
from src.modules.minio.repository import minio_repository
from src.modules.moodle.repository import moodle_repository
from src.modules.search.repository import search_repository

router = APIRouter(prefix="/compute", tags=["Compute"])


@router.get(
    "/corpora",
    responses={200: {"description": "Success"}, **IncorrectCredentialsException.responses},
)
async def get_corpora(_: ComputerServiceDep):
    moodle_files = minio_repository.get_moodle_objects()
    moodle_entries = await moodle_repository.read_all_in(
        [(file.course_id, file.module_id, file.filename) for file in moodle_files]
    )
    as_dict = {
        (entry.course_id, entry.module_id, content.filename): entry
        for entry in moodle_entries
        for content in entry.contents
    }
    for file in moodle_files:
        entry = as_dict.get((file.course_id, file.module_id, file.filename), None)
        if entry is not None:
            file.course_fullname = entry.course_fullname
            file.section_summary = entry.section_summary
            file.module_name = entry.module_name
            file.module_modname = entry.module_modname

    return {"moodle_files": moodle_files}


@router.get(
    "/pending-searchs",
    responses={200: {"description": "Success"}, **IncorrectCredentialsException.responses},
)
async def get_pending_search_queries(_: ComputerServiceDep) -> list[SearchTask]:
    return list(search_repository.pending_searches.values())


@router.post(
    "/completed-searchs",
    responses={200: {"description": "Success"}, **IncorrectCredentialsException.responses},
)
async def post_completed_search_queries(_: ComputerServiceDep, results: list[SearchResult]):
    logger.info(f"Received {len(results)} search results")
    search_repository.submit_search_results(results)
