import httpx
from fastapi import HTTPException, Query, Request

from src.api.logging_ import logger
from src.modules.ask.schemas import AskResponses
from src.modules.ml.ml_client import get_ml_service_client
from src.modules.ml.schemas import MLAskRequest, MLAskResponse
from src.modules.search.repository import search_repository
from src.modules.sources_enum import ALL_SOURCES, InfoSources


def get_token(request: Request) -> str | None:
    headers = request.headers
    authorization = headers.get("Authorization")
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


class AskRepository:
    async def ask(
        self,
        query: str,
        request: Request,
        sources: list[InfoSources] = Query(default=[]),
    ) -> AskResponses:
        if not sources:
            sources = ALL_SOURCES
        token = get_token(request)
        body = MLAskRequest(query=query, sources=sources, user_token=token).model_dump()

        async with get_ml_service_client() as client:
            try:
                resp = await client.post("/ask", json=body)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                logger.exception(f"Got http error from ML service: {repr(e)}", exc_info=True)
                raise HTTPException(status_code=502, detail=f"ML service error: {e}")

        ml_ask_response = MLAskResponse.model_validate(resp.json())

        # search_responses = await search_repository._process_ml_results(
        #    ml_ask_response.search_result,
        #    request=request,
        # )

        no_info_patterns = [
            # English
            "there is no",
            "no information",
            "does not contain information",
            "i do not know",
            "sorry",
            "the letter",
            "does not have a specific meaning",
            "please provide",
            # Russian
            "нет информации",
            "не содержат информации",
            "я не знаю",
            "извините",
            "уточните вопрос",
            "сведения отсутствуют",
        ]
        answer_lc = ml_ask_response.answer.strip().lower()
        if any(phrase in answer_lc for phrase in no_info_patterns):
            search_responses = []
        else:
            search_responses = await search_repository._process_ml_results(
                ml_ask_response.search_result,
                request=request,
            )

        return AskResponses(
            query=query,
            answer=ml_ask_response.answer,
            ask_query_id=None,
            search_responses=search_responses,
        )


ask_repository = AskRepository()
