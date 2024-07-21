from fastapi import FastAPI

from src.compute_service.search import search_pipeline
from src.modules.compute.schemas import SearchResult


# App definition
app = FastAPI(
    title="Compute Service for InNoHassle Search",
    version="0.1.0",
    contact={
        "name": "one-zero-eight (Telegram)",
        "url": "https://t.me/one_zero_eight",
    },
    license_info={
        "name": "MIT License",
        "identifier": "MIT",
    },
    swagger_ui_parameters={
        "tryItOutEnabled": True,
        "persistAuthorization": True,
        "filter": True,
    },
    root_path_in_servers=False,
    redoc_url=None,
    redirect_slashes=False,
)


@app.get(
    "/search",
    responses={
        200: {"description": "Success"},
        403: {"description": "Invalid API key"},
    },
)
def _search(query: str) -> SearchResult:
    moodle_file_results = search_pipeline(query)
    search_result = SearchResult(status="completed", result=moodle_file_results)
    return search_result
