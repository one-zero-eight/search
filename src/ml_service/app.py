import asyncio

import uvicorn
from fastapi import FastAPI
from httpx import AsyncClient

from src.api.docs import generate_unique_operation_id
from src.api.logging_ import logger
from src.ml_service import docs
from src.ml_service.lifespan import lifespan
from src.ml_service.llm import generate_answer, act
from src.ml_service.prepare import prepare_resource
from src.ml_service.search import search_pipeline
from src.modules.ml.schemas import MLAskRequest, MLAskResponse, MLSearchResult, MLSearchTask, MLActRequest, MLActResponse
from src.modules.sources_enum import InfoSources


# App definition
app = FastAPI(
    title=docs.TITLE,
    version=docs.VERSION,
    contact=docs.CONTACT_INFO,
    license_info=docs.LICENSE_INFO,
    description=docs.DESCRIPTION,
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
    stats = await search_pipeline(task.query, task.sources, limit=task.limit)
    items = stats["results"] if isinstance(stats, dict) else stats
    return MLSearchResult(result_items=items)


@app.post("/lancedb/update/{resource}")
async def update_resource(resource: InfoSources, docs: list[dict]):
    resources = await prepare_resource(resource, docs=docs)
    return {"status": "success", "resources": resources}


@app.post("/ask", responses=BASIC_RESPONSES)
async def ask_llm(request: MLAskRequest) -> MLAskResponse:
    target_sources = request.sources or [
        InfoSources.moodle,
        InfoSources.hotel,
        InfoSources.eduwiki,
        InfoSources.campuslife,
    ]
    logger.info(f"Target sources: {target_sources}")

    search_output = await search_pipeline(request.query, target_sources, limit=10)

    results = search_output["results"]
    original_query = search_output["original_query"]
    query_lang = search_output["query_lang"]
    lang_name = search_output["query_lang_name"]

    if not results:
        results = []

    snippets = [h["content"] for h in results]
    answer = await generate_answer(original_query, snippets, lang_name)

    logger.info(f"🗣️  Original query: '{original_query}' | Detected language: {query_lang} ({lang_name})")

    return MLAskResponse(answer=answer, search_result=MLSearchResult(result_items=results))

@app.post("/act", responses=BASIC_RESPONSES)
async def llm_act(request: MLActRequest) -> MLActResponse:
    result = await act(request.query, request.user_token)
    return result

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
