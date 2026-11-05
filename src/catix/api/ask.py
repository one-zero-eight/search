"""POST /ask/: a question to the cAtIx agent (the one the Telegram and Max bots use), with a conversation by `chat_id`.
An answer that names upcoming events offers them for the user's calendar (`calendar_events`), as the "➕ В мой календарь"
buttons under the bot's answers; POST /users/my-calendar/events/{id} adds one (api/users.py).
POST /ask/{ask_query_id}/feedback: a 👍/👎 on an answer with an optional comment, an annotation on its trace in Phoenix as under
the bot's answers.

POST /act/ is a mock: the search service had an agent that did things in InNoHassle services for the user (booking a
music room, sport classes); cAtIx has none.
"""

import asyncio
import contextlib
import functools
import json
import logging
import time
from typing import Literal

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage

from catix import groups, personal_calendar
from catix.agent import events as calendar_events
from catix.agent import tracing
from catix.agent.core import SUPERVISOR_NAME, build_agent, final_answer
from catix.agent.questions import QuestionQueue
from catix.agent.tools import AgentContext
from catix.api import state
from catix.api.auth import UserTokenData, VerifiedDep
from catix.api.schemas import ActResponses, AskResponses, CalendarEventOffer, SearchResponse
from catix.api.search import make_source
from catix.common.llm_down import UNAVAILABLE, unreachable
from catix.common.status import CHECKING, HELPER_TOOLS, QUEUED, STATUS, WRITING
from catix.settings import settings
from catix.tgbot.stream import partial_text

log = logging.getLogger("catix.api")
router = APIRouter(prefix="", tags=["Ask"])

NOT_BLANK = r"\S"  # a question has at least one non-space character
COMMENT_MAX = 2000  # characters in a comment on an answer, as in the site's text box
ACT_UNAVAILABLE = "Действия в сервисах InNoHassle пока недоступны. Я могу ответить на вопрос об университете: задайте его через /ask/."


@functools.cache
def agent():
    return build_agent()


questions = QuestionQueue(settings.agent_parallel_questions)

# The answer, the cards of its sources, the conversation, and the root span of the answer's trace (None when tracing is off)
Answered = tuple[str, list[SearchResponse], list, str | None]


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


async def stream_agent(inputs: dict, config: dict, context: AgentContext, events: asyncio.Queue) -> dict:
    """Run the agent and return its final state; the tools it runs (`status`) and the answer as it is written (`answer`,
    the whole text so far) are put to `events` as (name, data). As in the Telegram bot, only the supervisor's last model
    call is the answer, and the refs of sources that are not numbered yet are hidden."""
    state: dict = {"messages": []}
    call_id, call_text, shown, status = None, "", "", CHECKING

    async def show_status(text: str | None) -> None:
        nonlocal status
        if text and text != status:
            status = text
            await events.put(("status", {"text": text}))

    await events.put(("status", {"text": CHECKING}))
    async for mode, data in agent().astream(inputs, config, context=context, stream_mode=["messages", "values", "custom"]):
        if mode == "values":
            state = data
        elif mode == "custom":
            if isinstance(data, dict):
                await show_status(STATUS.get(data.get("tool") or ""))
        else:
            chunk, metadata = data
            if isinstance(chunk, ToolMessage):  # A helper came back: the supervisor now writes the answer.
                if chunk.name in HELPER_TOOLS:
                    await show_status(WRITING)
                continue
            if not isinstance(chunk, AIMessageChunk):
                continue
            if metadata.get("langgraph_node") != "model" or metadata.get("lc_agent_name") != SUPERVISOR_NAME:
                continue
            if chunk.tool_call_chunks:
                await show_status(STATUS.get(chunk.tool_call_chunks[0].get("name") or ""))
                continue
            if chunk.id != call_id:  # A new model call begins: its text starts from zero.
                call_id, call_text = chunk.id, ""
            call_text += chunk.text
            text = partial_text(call_text)
            if text and "<tool_call>" not in call_text and text != shown:
                shown = text
                await events.put(("answer", {"text": text}))
    return state


class AskCancelled(Exception):
    """The question was cancelled by POST /ask/{chat_id}/cancel (the caller itself was not cancelled)."""


# chat_id -> the questions of the chat that are running or waiting for their turn
pending: dict[str, set[asyncio.Task]] = {}
# InNoHassle id -> [lock, how many questions use it]: one client's questions are answered one at a time, in the order they
# came (an asyncio.Lock wakes its waiters first come first served), whatever chat they are in. Without it two questions of
# a chat would run at once on one thread of the agent. The lock is taken before the queue for the model (agent/questions.py),
# so a client's waiting questions do not hold places in it.
_gates: dict[str, list] = {}


@contextlib.asynccontextmanager
async def one_at_a_time(client: str):
    gate = _gates.setdefault(client, [asyncio.Lock(), 0])
    gate[1] += 1
    try:
        async with gate[0]:
            yield
    finally:
        gate[1] -= 1
        if not gate[1]:
            _gates.pop(client, None)


async def run(query: str, chat_id: str, user: UserTokenData, events: asyncio.Queue | None = None) -> Answered:
    """Answer a question. It runs as a task of its own that POST /ask/{chat_id}/cancel can cancel: then `AskCancelled` is
    raised here, while the cancelling of the caller itself (the client went away) goes on as it is."""
    task = asyncio.ensure_future(_in_line(query, chat_id, user, events))
    pending.setdefault(chat_id, set()).add(task)

    def forget(done: asyncio.Task) -> None:
        if chat_id in pending:
            pending[chat_id].discard(done)
            if not pending[chat_id]:
                del pending[chat_id]

    task.add_done_callback(forget)
    try:
        return await task
    except asyncio.CancelledError:
        if task.cancelled() and not asyncio.current_task().cancelling():
            raise AskCancelled(chat_id) from None
        raise


async def _in_line(query: str, chat_id: str, user: UserTokenData, events: asyncio.Queue | None = None) -> Answered:
    async with one_at_a_time(user.innohassle_id):
        return await _run(query, chat_id, user, events)


async def _run(query: str, chat_id: str, user: UserTokenData, events: asyncio.Queue | None = None) -> Answered:
    key = f"tg:{user.telegram_id or 0}"
    allowed = await asyncio.to_thread(groups.scoped_chat_ids, key, user.telegram_id)
    group = await asyncio.to_thread(groups.effective_group, key, user.telegram_id)
    thread_id = state.thread_of(chat_id)
    config = tracing.run_config(thread_id, str(user.telegram_id) if user.telegram_id else user.innohassle_id)
    if resume := state.resume_from.pop(chat_id, None):
        config["configurable"]["checkpoint_id"] = resume  # fork from before the question that did not finish
    context = AgentContext(
        allowed_chat_ids=frozenset(allowed),
        user_telegram_id=user.telegram_id,
        study_group=None if group == groups.ALL else group,
    )
    snapshot = await agent().aget_state(config)
    before = set(snapshot.values.get("sources") or {})
    checkpoint = snapshot.config["configurable"].get("checkpoint_id")  # None: the chat has no history yet
    async def report_wait(ahead: int) -> None:
        await events.put(("status", {"text": QUEUED.format(ahead=ahead)}))  # type: ignore[union-attr]

    try:
        async with questions.turn(f"api:{user.innohassle_id}", on_wait=None if events is None else report_wait):
            with tracing.question(thread_id, user.innohassle_id, query) as traced:
                inputs = {"messages": [{"role": "user", "content": query}]}
                if events is None:
                    result = await agent().ainvoke(inputs, config, context=context)
                else:
                    result = await stream_agent(inputs, config, context, events)
                answer = final_answer(result["messages"], result.get("sources") or {}) or "Не получилось сформулировать ответ."
                traced.answer(answer)
    except BaseException:  # cancelled or failed halfway: the thread goes back to where the question found it
        if checkpoint is None:
            agent().checkpointer.delete_thread(thread_id)
        else:
            state.resume_from[chat_id] = checkpoint
        raise
    cited = answer.rstrip().split("\n\n")[-1].startswith(("Источники:", "Sources:"))
    cards = _cards(result.get("sources") or {}, before) if cited else []
    return answer, cards, _history(result["messages"]), traced.id


async def calendar_offers(answer: str) -> list[CalendarEventOffer]:
    """The upcoming events the answer names, offered for the user's calendar as under the bot's answers (one more short
    call of the model, only when the answer has a date). A bonus: when it fails, the answer goes without them."""
    try:
        events = await asyncio.to_thread(calendar_events.extract, answer)
        offered = await asyncio.to_thread(personal_calendar.propose, events) if events else []
    except Exception:  # noqa: BLE001 - the answer is there already
        log.exception("could not offer calendar events")
        return []
    return [CalendarEventOffer(id=proposal_id, **event) for proposal_id, event in offered]


def chat_of(user: UserTokenData, chat_id: str | None) -> str:
    """The chat a question goes to: its owner's chat, or a new one."""
    if chat_id and chat_id in state.chats and state.chats[chat_id] != user.innohassle_id:
        raise HTTPException(status_code=404, detail="Chat not found or user has no access to it")
    if not chat_id or chat_id not in state.chats:
        return state.remember_chat(user.innohassle_id)  # An id that is not known (any more) starts a new chat.
    return chat_id


def server_event(name: str, data: dict) -> str:
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post(
    "/ask/",
    response_model=AskResponses,
    responses={
        200: {"description": "Success"},
        408: {"description": "Chat timed out"},
        502: {"description": "ML service error"},
        503: {"description": "The language model cannot be reached; the detail says the assistant is not working now"},
    },
)
async def ask_by_query(user: VerifiedDep, query: str = Body(..., pattern=NOT_BLANK), chat_id: str | None = Body(None)):
    chat_id = chat_of(user, chat_id)
    started = time.monotonic()
    try:
        answer, cards, messages, span_id = await run(query, chat_id, user)
    except AskCancelled:
        raise HTTPException(status_code=409, detail="The question was cancelled") from None
    except Exception as e:
        log.exception("the agent failed")
        if unreachable(e):
            raise HTTPException(status_code=503, detail=UNAVAILABLE) from e
        raise HTTPException(status_code=502, detail=f"ML service error: {e}") from e
    log.info("ask for `%s` (%d ms): %s", query, round((time.monotonic() - started) * 1000), answer)
    return AskResponses(
        query=query,
        answer=answer,
        chat_id=chat_id,
        ask_query_id=state.remember_ask(user.innohassle_id, span_id),
        search_responses=cards,
        calendar_events=await calendar_offers(answer),
        messages=messages,
    )


@router.post(
    "/ask/stream",
    response_class=StreamingResponse,
    responses={200: {"description": "Server-sent events: `status`, `answer`, then `done` (AskResponses) or `error`"}},
)
async def ask_by_query_stream(user: VerifiedDep, query: str = Body(..., pattern=NOT_BLANK), chat_id: str | None = Body(None)):
    """The same as POST /ask/, but the work is shown while it goes on. Events: `status` ({text}: what the agent is doing: waiting in the queue, checking, asking a helper, writing, as in the Telegram bot),
    `answer` ({text}: the whole answer so far), `done` (AskResponses: the final answer with its sources and the events it
    offers for the calendar), `cancelled`
    ({detail}: POST /ask/{chat_id}/cancel) or `error` ({detail}). A client's questions are answered one at a time, in the
    order they came: while an earlier one is not done, this one waits and sends no events."""
    chat_id = chat_of(user, chat_id)
    events: asyncio.Queue = asyncio.Queue()

    async def work() -> None:
        started = time.monotonic()
        try:
            answer, cards, messages, span_id = await run(query, chat_id, user, events)
            log.info("ask (stream) for `%s` (%d ms): %s", query, round((time.monotonic() - started) * 1000), answer)
            done = AskResponses(
                query=query,
                answer=answer,
                chat_id=chat_id,
                ask_query_id=state.remember_ask(user.innohassle_id, span_id),
                search_responses=cards,
                calendar_events=await calendar_offers(answer),
                messages=messages,
            )
            await events.put(("done", done.model_dump(mode="json")))
        except AskCancelled:
            await events.put(("cancelled", {"detail": "The question was cancelled"}))
        except Exception as e:
            log.exception("the agent failed")
            await events.put(("error", {"detail": UNAVAILABLE if unreachable(e) else f"ML service error: {e}"}))
        await events.put(None)

    async def generate():
        task = asyncio.create_task(work())
        try:
            while (event := await events.get()) is not None:
                yield server_event(*event)
        finally:
            task.cancel()  # The client went away: the answer is not needed any more.

    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post(
    "/ask/{chat_id}/cancel",
    responses={200: {"description": "Success"}, 404: {"description": "Chat not found or user has no access to it"}},
)
async def cancel_ask(user: VerifiedDep, chat_id: str):
    """Cancel the work of the agent in the chat: the question being answered and the ones of this chat still waiting for
    their turn. Their requests end with 409 (`/ask/stream`: a `cancelled` event). The conversation goes on as it was before
    the cancelled questions; the answers already given stay in it."""
    if state.chats.get(chat_id) != user.innohassle_id:
        raise HTTPException(status_code=404, detail="Chat not found or user has no access to it")
    tasks = [task for task in pending.get(chat_id, ()) if not task.done()]
    for task in tasks:
        task.cancel()
    return {"status": "success", "chat_id": chat_id, "cancelled": len(tasks)}


@router.post(
    "/ask/{ask_query_id}/feedback",
    responses={
        200: {"description": "Success"},
        404: {"description": "Ask query not found or user has no access to it"},
        502: {"description": "The feedback could not be saved"},
    },
)
async def add_user_feedback(
    user: VerifiedDep,
    ask_query_id: str,
    feedback: Literal["like", "dislike"],
    comment: str | None = Body(None, embed=True, max_length=COMMENT_MAX),
):
    """A 👍 (`like`) or 👎 (`dislike`) on an answer, as under the answers of the Telegram bot: the annotation `user-feedback` on
    the answer's trace in Phoenix, and the user's `comment` on what they liked or not is its explanation. A second vote of the
    user (the same one with a comment, or another) replaces the first. An answer has an `ask_query_id` only when tracing is on."""
    asked = state.asks.get(ask_query_id)
    if asked is None or asked[0] != user.innohassle_id:
        raise HTTPException(status_code=404, detail="Ask query not found or user has no access to it")
    comment = (comment or "").strip() or None
    try:
        await asyncio.to_thread(tracing.score_feedback, asked[1], f"api:{user.innohassle_id}", feedback == "like", comment)
    except Exception as e:
        log.exception("could not save the feedback")
        raise HTTPException(status_code=502, detail="The feedback could not be saved") from e
    return {"status": "success", "ask_query_id": ask_query_id}


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
