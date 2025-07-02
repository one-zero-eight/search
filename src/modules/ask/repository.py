import httpx
from fastapi import HTTPException, Query, Request

from src.modules.ask.schemas import AskResponses
from src.modules.ml.ml_client import get_ml_service_client
from src.modules.ml.schemas import MLAskRequest, MLAskResponse
from src.modules.search.repository import search_repository
from src.modules.sources_enum import ALL_SOURCES, InfoSources


class AskRepository:
    async def ask(
        self,
        query: str,
        request: Request,
        sources: list[InfoSources] = Query(default=[]),
    ) -> AskResponses:
        if not sources:
            sources = ALL_SOURCES
        body = MLAskRequest(
            query=query,
            sources=sources,
        ).model_dump()

        async with get_ml_service_client() as client:
            try:
                resp = await client.post("/ask", json=body)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                raise HTTPException(status_code=502, detail=f"ML service error: {e}")
        ml_ask_response = MLAskResponse.model_validate(resp.json())
        search_responses = await search_repository._process_ml_results(ml_ask_response.search_result, request=request)
        return AskResponses(
            query=query,
            answer=ml_ask_response.answer,
            ask_query_id=None,
            search_responses=search_responses,
        )


ask_repository = AskRepository()
