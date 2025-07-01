import asyncio

import uvicorn
from fastapi import FastAPI
from httpx import AsyncClient

from src.api.docs import generate_unique_operation_id
from src.api.logging_ import logger
from src.ml_service import docs
from src.ml_service.lifespan import lifespan
from src.ml_service.llm import generate_answer
from src.ml_service.prepare import prepare_resource
from src.ml_service.search import search_pipeline
from src.modules.ml.schemas import MLAskRequest, MLAskResponse, MLSearchResult, MLSearchTask
from src.modules.sources_enum import InfoSources

# App definition
app = FastAPI(
    title=docs.TITLE,
    version=docs.VERSION,
    contact=docs.CONTACT_INFO,
    license_info=docs.LICENSE_INFO,
    servers=[],
    swagger_ui_parameters={
        "tryItOutEnabled": True,
        "persistAuthorization": True,
        "filter": True,
    },
    root_path_in_servers=False,
    generate_unique_id_function=generate_unique_operation_id,
    lifespan=lifespan,
)

# Highly likely will be removed in the future. All responses will be manually rewritten.
BASIC_RESPONSES = {
    200: {"description": "Success"},
    403: {"description": "Invalid API key"},  # allow only backend to communicate with it
    404: {"description": "Not Found"},
}


@app.post("/search", responses=BASIC_RESPONSES)
async def search_info(task: MLSearchTask) -> MLSearchResult:
    results = await search_pipeline(task.query, task.sources, limit=task.limit)
    return MLSearchResult(result_items=results)


@app.post("/lancedb/update/{resource}")
async def update_resource(resource: InfoSources, docs: list[dict]):
    resources = await prepare_resource(resource, docs=docs)
    return {"status": "success", "resources": resources}


# Update info in vector db
# @app.put("/search", responses=BASIC_RESPONSES)
# async def update_search_db(task: UpdateTask) -> UpdateResult:...

# Add info in vector db
# @app.post("/search", responses=BASIC_RESPONSES)
# async def update_search_db(task: AddTask) -> AddResult:...


@app.post("/ask", responses=BASIC_RESPONSES)
async def ask_llm(request: MLAskRequest) -> MLAskResponse:
    target_sources = request.sources or [
        InfoSources.moodle,
        InfoSources.hotel,
        InfoSources.eduwiki,
        InfoSources.campuslife,
    ]
    logger.info(f"Target sources: {target_sources}")
    results = await search_pipeline(request.query, target_sources, limit=10)
    if not results:
        results = []

    snippets = [h["content"] for h in results]
    answer = await generate_answer(request.query, snippets)

    return MLAskResponse(answer=answer, search_result=MLSearchResult(result_items=results))


# TODO: add swagger docs

# # Redirect root to docs
# @app.get("/", tags=["Root"], include_in_schema=False)
# async def redirect_to_docs(request: Request):
#     return RedirectResponse(url=request.url_for("swagger_ui_html"))
#
#
# @app.get("/docs", tags=["System"], include_in_schema=False)
# async def swagger_ui_html(request: Request):
#     from fastapi.openapi.docs import get_swagger_ui_html
#
#     root_path = request.scope.get("root_path", "").rstrip("/")
#     openapi_url = root_path + app.openapi_url
#
#     return get_swagger_ui_html(
#         openapi_url=openapi_url,
#         title=app.title + " - Swagger UI",
#         swagger_js_url="https://api.innohassle.ru/swagger/swagger-ui-bundle.js",
#         swagger_css_url="https://api.innohassle.ru/swagger/swagger-ui.css",
#         swagger_favicon_url="https://api.innohassle.ru/swagger/favicon.png",
#         swagger_ui_parameters={"tryItOutEnabled": True, "persistAuthorization": True, "filter": True},
#     )

if __name__ == "__main__":

    async def test_ask():
        async with AsyncClient(app=app, base_url="http://test") as client:
            payload = {
                "query": "Who is the leader of basketball club?",
            }
            resp = await client.post("/ask", json=payload)
            print("Status:", resp.status_code)
            print("Body:", resp.json())

    asyncio.run(test_ask())

    uvicorn.run(app, host="127.0.0.1", port=8000)
