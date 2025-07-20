from typing import cast

import httpx
from beanie import PydanticObjectId
from fastapi import HTTPException, Request
from openai.types.chat import ChatCompletionMessageParam

from src.api.logging_ import logger
from src.modules.ask.schemas import ActResponses, AskResponses
from src.modules.ml.ml_client import get_ml_service_client
from src.modules.ml.schemas import MLActRequest, MLActResponse, MLAskRequest, MLAskResponse
from src.modules.search.repository import search_repository
from src.modules.sources_enum import ALL_SOURCES, InfoSources
from src.storages.mongo.chat import ChatSession


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
        innohassle_id: str,
        chat_id: PydanticObjectId | None = None,
        sources: list[InfoSources] | None = None,
    ) -> AskResponses:
        if not sources:
            sources = ALL_SOURCES
        chat = await ChatSession.get(chat_id) if chat_id else None

        if not chat:
            chat = ChatSession(innohassle_id=innohassle_id, history=[])
            await chat.insert()
        elif chat.innohassle_id != innohassle_id:
            raise HTTPException(status_code=404, detail="Chat not found or user has no access to it")

        history = chat.history or []

        token = get_token(request)

        body = MLAskRequest(
            query=query, sources=sources, user_token=token, history=cast(list[ChatCompletionMessageParam], history)
        ).model_dump()

        async with get_ml_service_client() as client:
            try:
                resp = await client.post("/ask", json=body)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                logger.exception(f"Got http error from ML service: {repr(e)}", exc_info=True)
                raise HTTPException(status_code=502, detail=f"ML service error: {e}")

        ml_ask_response = MLAskResponse.model_validate(resp.json())

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
            if ml_ask_response.search_result:
                logger.info("!!! Answer is no info, but search result is not empty")
            else:
                logger.info(f"Answer is no info: {answer_lc}")
            search_responses = []
        else:
            search_responses = await search_repository._process_ml_results(
                ml_ask_response.search_result,
                request=request,
            )

        chat.history = ml_ask_response.updated_history
        await chat.save()

        return AskResponses(
            query=query,
            answer=ml_ask_response.answer,
            ask_query_id=None,
            search_responses=search_responses,
            messages=chat.history,
            chat_id=chat.id,
        )

    async def act(
        self,
        query: str,
        request: Request,
    ) -> ActResponses:
        user_token = get_token(request)
        body = MLActRequest(query=query, user_token=user_token).model_dump()

        async with get_ml_service_client() as client:
            try:
                resp = await client.post("/act", json=body)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                logger.exception(f"Got http error from ML service: {repr(e)}", exc_info=True)
                raise HTTPException(status_code=502, detail=f"ML service error: {e}")

        ml_act_response = MLActResponse.model_validate(resp.json())

        return ActResponses(
            query=query,
            answer=ml_act_response.answer,
            act_query_id=None,
            tool_calls=ml_act_response.tool_calls,
            messages=ml_act_response.messages,
        )


ask_repository = AskRepository()
