"""POST /ask/: a question to the cAtIx agent (the one the Telegram and Max bots use), with a conversation by `chat_id`.

POST /act/ is a mock: the search service had an agent that did things in InNoHassle services for the user (booking a
music room, sport classes); cAtIx has none.
"""

import asyncio
import functools
import logging
import time

from fastapi import APIRouter, Body, HTTPException
from langchain_core.messages import AIMessage, HumanMessage

from catix import groups
from catix.agent import tracing
from catix.agent.core import build_agent, final_answer
from catix.agent.questions import QuestionQueue
from catix.agent.tools import AgentContext
from catix.api import state
from catix.api.auth import UserTokenData, VerifiedDep
from catix.api.schemas import ActResponses, AskResponses, SearchResponse
from catix.api.search import make_source
from catix.settings import settings

log = logging.getLogger("catix.api")
router = APIRouter(prefix="", tags=["Ask"])

ACT_UNAVAILABLE = "Действия в сервисах InNoHassle пока недоступны. Я могу ответить на вопрос об университете: задайте его через /ask/."


@functools.cache
def agent():
    return build_agent()


questions = QuestionQueue(settings.agent_parallel_questions)


def _cards(registry: dict, before: set[str]) -> list[SearchResponse]:
    """The pages of the knowledge base this answer found, as cards (one per document)."""
    cards: dict[tuple, SearchResponse] = {}
    for ref, source in registry.items():
        if ref in before or not source.get("wiki"):
            continue
        preview = f"{source['title']}" + (f", п. {source['clause']}" if source.get("clause") else "")
        card = make_source(
            source["title"], source.get("link") or "", preview, site=bool(source.get("site")), trust=source.get("trust") or "wiki"
        )
        cards.setdefault((card.display_name, card.url), SearchResponse(source=card))
    return list(cards.values())


def _history(messages: list) -> list[dict]:
    """The conversation as plain messages: the questions and the answers, without the helpers' work."""
    return [
        {"role": "user" if isinstance(m, HumanMessage) else "assistant", "content": m.text}
        for m in messages
        if isinstance(m, HumanMessage) or (isinstance(m, AIMessage) and not m.tool_calls and m.text)
    ]


async def run(query: str, chat_id: str, user: UserTokenData) -> tuple[str, list[SearchResponse], list]:
    key = f"tg:{user.telegram_id or 0}"
    allowed = await asyncio.to_thread(groups.scoped_chat_ids, key, user.telegram_id)
    group = await asyncio.to_thread(groups.effective_group, key, user.telegram_id)
    thread_id = state.thread_of(chat_id)
    config = tracing.run_config(thread_id, str(user.telegram_id) if user.telegram_id else user.innohassle_id)
    context = AgentContext(
        allowed_chat_ids=frozenset(allowed),
        user_telegram_id=user.telegram_id,
        study_group=None if group == groups.ALL else group,
    )
    before = set((await agent().aget_state(config)).values.get("sources") or {})
    async with questions.turn(f"api:{user.innohassle_id}"):
        with tracing.question(thread_id, user.innohassle_id, query) as traced:
            result = await agent().ainvoke({"messages": [{"role": "user", "content": query}]}, config, context=context)
            answer = final_answer(result["messages"], result.get("sources") or {}) or "Не получилось сформулировать ответ."
            traced.answer(answer)
    cited = answer.rstrip().split("\n\n")[-1].startswith(("Источники:", "Sources:"))
    cards = _cards(result.get("sources") or {}, before) if cited else []
    return answer, cards, _history(result["messages"])


@router.post(
    "/ask/",
    response_model=AskResponses,
    responses={
        200: {"description": "Success"},
        408: {"description": "Chat timed out"},
        502: {"description": "ML service error"},
    },
)
async def ask_by_query(user: VerifiedDep, query: str = Body(...), chat_id: str | None = Body(None)):
    if chat_id and chat_id in state.chats and state.chats[chat_id] != user.innohassle_id:
        raise HTTPException(status_code=404, detail="Chat not found or user has no access to it")
    if not chat_id or chat_id not in state.chats:
        chat_id = state.remember_chat(user.innohassle_id)  # An id that is not known (any more) starts a new chat.
    started = time.monotonic()
    try:
        answer, cards, messages = await run(query, chat_id, user)
    except Exception as e:
        log.exception("the agent failed")
        raise HTTPException(status_code=502, detail=f"ML service error: {e}") from e
    log.info("ask for `%s` (%d ms): %s", query, round((time.monotonic() - started) * 1000), answer)
    return AskResponses(
        query=query, answer=answer, chat_id=chat_id, ask_query_id=state.new_id(), search_responses=cards, messages=messages
    )


@router.post(
    "/act/",
    responses={
        200: {"description": "Success"},
        408: {"description": "Chat timed out"},
        502: {"description": "ML service error"},
    },
)
async def act_by_query(_auth: VerifiedDep, query: str = Body(..., embed=True)) -> ActResponses:
    return ActResponses(
        query=query,
        answer=ACT_UNAVAILABLE,
        act_query_id=state.new_id(),
        tool_calls=[],
        messages=[{"role": "user", "content": query}, {"role": "assistant", "content": ACT_UNAVAILABLE}],
    )
