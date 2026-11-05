"""POST /ask/: a question to the cAtIx agent (the one the Telegram and Max bots use), with a conversation by `chat_id`. The chats
are kept in Postgres: the agent's memory of each (LangGraph's AsyncPostgresSaver) and the answers as the client got them
(api/chats.py), so that the user comes back to a chat (GET /ask/chats, GET /ask/chats/{chat_id}) and goes on with it, after a
restart as well. The model names a chat by its first question while the agent answers it (agent/titles.py); the user
renames it with PATCH /ask/chats/{chat_id} and deletes it with DELETE /ask/chats/{chat_id}.
An answer that names upcoming events offers them for the user's calendar (`calendar_events`), as the "➕ В мой календарь"
buttons under the bot's answers; POST /users/my-calendar/events/{id} adds one (api/users.py).
POST /ask/{ask_query_id}/feedback: a 👍/👎 on an answer with an optional comment, an annotation on its trace in Phoenix as under
the bot's answers.

POST /act/ is a mock: the search service had an agent that did things in InNoHassle services for the user (booking a
music room, sport classes); cAtIx has none.
"""

import asyncio
import contextlib
import json
import logging
import time
from typing import Literal

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from catix import groups, personal_calendar
from catix.agent import events as calendar_events
from catix.agent import titles, tracing
from catix.agent.core import SUPERVISOR_NAME, build_agent, final_answer
from catix.agent.questions import QuestionQueue
from catix.agent.tools import AgentContext
from catix.api import chats, state
from catix.api.auth import UserTokenData, VerifiedDep
from catix.api.schemas import ActResponses, AskChat, AskChatHistory, AskResponses, CalendarEventOffer, SearchResponse
from catix.api.search import make_source
from catix.common.llm_down import UNAVAILABLE, unreachable
from catix.common.status import CHECKING, HELPER_TOOLS, QUEUED, STATUS, WRITING
from catix.settings import settings
from catix.tgbot.stream import partial_text

log = logging.getLogger("catix.api")
router = APIRouter(prefix="", tags=["Ask"])

TITLE_WAIT = 5  # seconds the answer waits for the model's name of the chat once it is ready itself
NOT_BLANK = r"\S"  # a question has at least one non-space character
COMMENT_MAX = 2000  # characters in a comment on an answer, as in the site's text box
ACT_UNAVAILABLE = "Действия в сервисах InNoHassle пока недоступны. Я могу ответить на вопрос об университете: задайте его через /ask/."


_agent = None


def agent():
    """The agent of the API, built when the app starts (`memory`)."""
    if _agent is None:
        raise RuntimeError("the agent is built when the app starts (api/ask.py `memory`)")
    return _agent


@contextlib.asynccontextmanager
async def memory():
    """For the life of the app: the agent that keeps its memory of the chats in Postgres (AsyncPostgresSaver, thread
    `api:<chat_id>`; `setup` makes its tables or brings them up to date)."""
    global _agent
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set (see docker-compose.yml)")
    # The connections as AsyncPostgresSaver.from_conn_string makes its own. The saver uses one at a time.
    pool = AsyncConnectionPool(
        settings.database_url,
        min_size=1,
        max_size=2,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        open=False,
    )
    async with pool:
        saver = AsyncPostgresSaver(pool)  # type: ignore[arg-type]  # (a pool of dict-row connections, as it wants)
        await saver.setup()
        _agent = build_agent(checkpointer=saver)
        try:
            yield
        finally:
            _agent = None


questions = QuestionQueue(settings.agent_parallel_questions)

# The answer, the cards of its sources, the conversation, the root span of the answer's trace (None when tracing is off) and the
# checkpoint of the chat's thread after the answer
Answered = tuple[str, list[SearchResponse], list, str | None, str | None]


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


async def run(query: str, chat_id: str, user: UserTokenData, events: asyncio.Queue | None = None) -> AskResponses:
    """Answer a question and keep the answer in its chat. It runs as a task of its own that POST /ask/{chat_id}/cancel can cancel: then `AskCancelled` is
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


async def chat_title(question: str) -> str | None:
    """The model's name of a chat that starts with the question. A bonus: when it fails, the chat keeps the question."""
    try:
        return await asyncio.to_thread(titles.name, question)
    except Exception:  # noqa: BLE001 - the answer does not need it
        log.exception("could not name the chat")
        return None


async def _in_line(query: str, chat_id: str, user: UserTokenData, events: asyncio.Queue | None = None) -> AskResponses:
    async with one_at_a_time(user.innohassle_id):
        # A chat not named yet is named while the agent answers: the answer does not wait for it.
        naming = asyncio.ensure_future(chat_title(query)) if await asyncio.to_thread(chats.needs_title, chat_id) else None
        try:
            answer, cards, messages, span_id, checkpoint = await _run(query, chat_id, user, events)
        except BaseException:
            if naming is not None:
                naming.cancel()  # The question is not kept: the next one names the chat.
            raise
        response = AskResponses(
            query=query,
            answer=answer,
            chat_id=chat_id,
            # The id of the answer for its 👍/👎. None when tracing is off: a vote is an annotation on the answer's trace, and
            # without a trace there is nothing to vote on (the bot shows no buttons then either).
            ask_query_id=state.new_id() if span_id else None,
            search_responses=cards,
            calendar_events=await calendar_offers(answer),
            messages=messages,
        )
        title = None
        if naming is not None:  # Ready by now as a rule: the agent takes longer. The answer waits for it only so long.
            done, _ = await asyncio.wait({naming}, timeout=TITLE_WAIT)
            title = naming.result() if done else None
            naming.cancel()
        # Kept before the client's next question starts: it goes on from the checkpoint kept with this answer.
        await asyncio.to_thread(chats.save_answer, response, span_id, checkpoint, title)
        return response


async def _run(query: str, chat_id: str, user: UserTokenData, events: asyncio.Queue | None = None) -> Answered:
    key = f"tg:{user.telegram_id or 0}"
    allowed = await asyncio.to_thread(groups.scoped_chat_ids, key, user.telegram_id)
    group = await asyncio.to_thread(groups.effective_group, key, user.telegram_id)
    thread_id = chats.thread_of(chat_id)
    config = tracing.run_config(thread_id, str(user.telegram_id) if user.telegram_id else user.innohassle_id)
    # A question goes on from the chat's last answer: one that was cancelled (or failed, or the API stopped) halfway left its
    # messages in the thread, and a tool call without its result would break the next question. Before the first answer
    # there is nothing to go on from: what such a question left goes.
    if last := await asyncio.to_thread(chats.checkpoint, chat_id):
        config["configurable"]["checkpoint_id"] = last
    else:
        await agent().checkpointer.adelete_thread(thread_id)
    context = AgentContext(
        allowed_chat_ids=frozenset(allowed),
        user_telegram_id=user.telegram_id,
        study_group=None if group == groups.ALL else group,
    )
    snapshot = await agent().aget_state(config)
    before = set(snapshot.values.get("sources") or {})

    async def report_wait(ahead: int) -> None:
        await events.put(("status", {"text": QUEUED.format(ahead=ahead)}))  # type: ignore[union-attr]

    async with questions.turn(f"api:{user.innohassle_id}", on_wait=None if events is None else report_wait):
        with tracing.question(thread_id, user.innohassle_id, query) as traced:
            inputs = {"messages": [{"role": "user", "content": query}]}
            if events is None:
                result = await agent().ainvoke(inputs, config, context=context)
            else:
                result = await stream_agent(inputs, config, context, events)
            answer = final_answer(result["messages"], result.get("sources") or {}) or "Не получилось сформулировать ответ."
            traced.answer(answer)
    cited = answer.rstrip().split("\n\n")[-1].startswith(("Источники:", "Sources:"))
    cards = _cards(result.get("sources") or {}, before) if cited else []
    after = await agent().aget_state({"configurable": {"thread_id": thread_id}})  # the thread's latest checkpoint
    return answer, cards, _history(result["messages"]), traced.id, after.config["configurable"]["checkpoint_id"]


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


async def chat_of(user: UserTokenData, chat_id: str | None, query: str) -> str:
    """The chat a question goes to: its owner's chat, or a new one titled by the question."""
    owner = await asyncio.to_thread(chats.owner, chat_id) if chat_id else None
    if owner is not None and owner != user.innohassle_id:
        raise HTTPException(status_code=404, detail="Chat not found or user has no access to it")
    if owner is None:
        return await asyncio.to_thread(chats.start, user.innohassle_id, query)  # An id that is not known starts a new chat.
    return chat_id  # type: ignore[return-value]  # (it has an owner)


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
    chat_id = await chat_of(user, chat_id, query)
    started = time.monotonic()
    try:
        response = await run(query, chat_id, user)
    except AskCancelled:
        raise HTTPException(status_code=409, detail="The question was cancelled") from None
    except Exception as e:
        log.exception("the agent failed")
        if unreachable(e):
            raise HTTPException(status_code=503, detail=UNAVAILABLE) from e
        raise HTTPException(status_code=502, detail=f"ML service error: {e}") from e
    log.info("ask for `%s` (%d ms): %s", query, round((time.monotonic() - started) * 1000), response.answer)
    return response


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
    chat_id = await chat_of(user, chat_id, query)
    events: asyncio.Queue = asyncio.Queue()

    async def work() -> None:
        started = time.monotonic()
        try:
            done = await run(query, chat_id, user, events)
            log.info("ask (stream) for `%s` (%d ms): %s", query, round((time.monotonic() - started) * 1000), done.answer)
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
    if await asyncio.to_thread(chats.owner, chat_id) != user.innohassle_id:
        raise HTTPException(status_code=404, detail="Chat not found or user has no access to it")
    return {"status": "success", "chat_id": chat_id, "cancelled": len(cancel_pending(chat_id))}


def cancel_pending(chat_id: str) -> list[asyncio.Task]:
    """Cancel the questions of the chat that are running or waiting for their turn; the tasks cancelled."""
    tasks = [task for task in pending.get(chat_id, ()) if not task.done()]
    for task in tasks:
        task.cancel()
    return tasks


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
    user (the same one with a comment, or another) replaces the first. An answer has an `ask_query_id` only when tracing is on.
    The chat's history (GET /ask/chats/{chat_id}) shows the vote with its comment."""
    asked = await asyncio.to_thread(chats.asked, ask_query_id)
    if asked is None or asked[0] != user.innohassle_id:
        raise HTTPException(status_code=404, detail="Ask query not found or user has no access to it")
    comment = (comment or "").strip() or None
    try:
        await asyncio.to_thread(tracing.score_feedback, asked[1], f"api:{user.innohassle_id}", feedback == "like", comment)
        await asyncio.to_thread(chats.vote, ask_query_id, feedback, comment)
    except Exception as e:
        log.exception("could not save the feedback")
        raise HTTPException(status_code=502, detail="The feedback could not be saved") from e
    return {"status": "success", "ask_query_id": ask_query_id}


@router.get("/ask/chats", responses={200: {"description": "Success"}})
async def list_chats(user: VerifiedDep) -> list[AskChat]:
    """The user's chats with the assistant, the last answered first (at most 100). GET /ask/chats/{chat_id} gives the
    questions and answers of one, and a question with its `chat_id` goes on with it."""
    return await asyncio.to_thread(chats.of_user, user.innohassle_id)


@router.get(
    "/ask/chats/{chat_id}",
    responses={200: {"description": "Success"}, 404: {"description": "Chat not found or user has no access to it"}},
)
async def chat_history(user: VerifiedDep, chat_id: str) -> AskChatHistory:
    """A chat of the user: its questions and answers, the oldest first, as POST /ask/ gave them, with the user's votes. A
    question that was cancelled or failed is not in it: the agent does not remember it either."""
    found = await asyncio.to_thread(chats.history, chat_id, user.innohassle_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Chat not found or user has no access to it")
    return found


@router.patch(
    "/ask/chats/{chat_id}",
    responses={200: {"description": "Success"}, 404: {"description": "Chat not found or user has no access to it"}},
)
async def rename_chat(
    user: VerifiedDep,
    chat_id: str,
    title: str = Body(..., embed=True, pattern=NOT_BLANK, max_length=chats.TITLE_MAX),
) -> AskChat:
    """The user's name of their chat, in place of the one the model gave it (or its first question). The model does not
    name the chat again after that."""
    renamed = await asyncio.to_thread(chats.rename, chat_id, user.innohassle_id, title)
    if renamed is None:
        raise HTTPException(status_code=404, detail="Chat not found or user has no access to it")
    return renamed


@router.delete(
    "/ask/chats/{chat_id}",
    responses={200: {"description": "Success"}, 404: {"description": "Chat not found or user has no access to it"}},
)
async def delete_chat(user: VerifiedDep, chat_id: str):
    """Delete a chat of the user: its questions and answers with the user's votes, and the agent's memory of it. A question
    of the chat being answered or waiting for its turn is cancelled first (its request ends as by POST /ask/{chat_id}/cancel).
    A question sent with this `chat_id` afterwards starts a new chat. The answers' traces stay in Phoenix, and the events
    the user added to their calendar stay there."""
    if await asyncio.to_thread(chats.owner, chat_id) != user.innohassle_id:
        raise HTTPException(status_code=404, detail="Chat not found or user has no access to it")
    if tasks := cancel_pending(chat_id):
        await asyncio.wait(tasks)  # They stop before the chat goes: none of them writes to the agent's thread after it.
    if not await asyncio.to_thread(chats.delete, chat_id, user.innohassle_id):
        raise HTTPException(status_code=404, detail="Chat not found or user has no access to it")  # (deleted meanwhile)
    await agent().checkpointer.adelete_thread(chats.thread_of(chat_id))
    return {"status": "success", "chat_id": chat_id}


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
