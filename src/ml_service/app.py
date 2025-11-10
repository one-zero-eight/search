import asyncio

import uvicorn
from fastapi import FastAPI
from httpx import AsyncClient
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

from src.api.docs import generate_unique_operation_id
from src.api.logging_ import logger
from src.config import settings
from src.ml_service import docs
from src.ml_service.lifespan import lifespan
from src.ml_service.llm import act, client
from src.ml_service.prepare import prepare_resource
from src.ml_service.prompt import build_prompt
from src.ml_service.search import search_pipeline
from src.modules.ml.schemas import (
    MLActRequest,
    MLActResponse,
    MLAskRequest,
    MLAskResponse,
    MLSearchResult,
    MLSearchTask,
)
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
    root_path=settings.ml_service.app_root_path,
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
        InfoSources.clubs,
    ]
    logger.info(f"Target sources: {target_sources}")

    rewrite_system = ChatCompletionSystemMessageParam(
        role="system",
        content=(
            "Given the following conversation and a follow up question, "
            "rephrase the follow up question to be a standalone question, in its original language.\n\n"
            "Keep as much details as possible from previous messages. Keep entity names and all.\n\n"
            + (
                "Chat History:\n" + "\n".join(f"{m['role']}: {m['content']}" for m in request.history) + "\n"
                if request.history
                else ""
            )
            + f"Follow Up Input: {request.query}\n"
            "Standalone question:"
        ),
    )

    rewrite_resp = await client.chat.completions.create(
        model=settings.ml_service.llm_model,
        messages=[rewrite_system],
        max_tokens=2048,
        temperature=0.0,
        top_p=1.0,
    )
    standalone_query = rewrite_resp.choices[0].message.content.strip()
    logger.info(f"Rewritten query: {standalone_query}")

    search_output = await search_pipeline(standalone_query, target_sources, limit=10)

    results = search_output["results"]
    original_query = search_output["original_query"]
    query_lang = search_output["query_lang"]
    logger.info(f"🗣️  Original query: '{original_query}' | Detected language: {query_lang}")

    snippets = [
        {
            "resource": r["resource"],
            "content": r["content"],
        }
        for r in results
    ]

    if snippets:
        search_knowledge_content = build_prompt(
            original_query,
            snippets,
            query_lang,
        )
    else:
        search_knowledge_content = (
            f"{original_query}\n\n"
            "No information was found in the provided contexts. "
            "Please apologize and state this strictly in the same language as the question above."
        )
    system_message = ChatCompletionSystemMessageParam(role="system", content=settings.ml_service.system_prompt)

    search_knowledge_content_message = ChatCompletionSystemMessageParam(role="system", content=search_knowledge_content)

    user_message = ChatCompletionUserMessageParam(role="user", content=original_query)

    if standalone_query != request.query:
        history_msgs = [
            ChatCompletionSystemMessageParam(role=m["role"], content=m["content"]) for m in (request.history or [])
        ]
        messages = [system_message] + history_msgs + [user_message, search_knowledge_content_message]
    else:
        messages = [system_message, user_message, search_knowledge_content_message]

    r = await client.chat.completions.create(
        model=settings.ml_service.llm_model,
        messages=messages,
        max_tokens=2048,
        temperature=0.0,
        top_p=1.0,
    )
    answer = r.choices[0].message.content

    logger.info(f"Answer:\n{answer}")
    if answer is None:
        raise RuntimeError("No answer from openai")

    updated_history = (request.history or []) + [
        {"role": "user", "content": request.query},
        {"role": "assistant", "content": answer},
    ]
    logger.info(f"Updated history: {updated_history}")

    return MLAskResponse(
        answer=answer, search_result=MLSearchResult(result_items=results), updated_history=updated_history
    )


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
