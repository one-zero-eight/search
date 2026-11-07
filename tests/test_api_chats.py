"""The site's chats in the database (api/chats.py), and the agent's memory of a chat in Postgres (api/ask.py `memory`): the
user comes back to a chat after the API restarts and the agent still knows what was said. Skipped without DATABASE_URL;
the rows and threads of the test's own user are removed afterwards."""

import asyncio
import uuid

import pytest
from langchain_core.messages import AIMessage
from pydantic import SecretStr

from catix.agent.core import build_agent
from catix.api import ask, chats
from catix.api.auth import UserTokenData
from catix.api.schemas import AskDecision, AskResponses
from catix.db import pg
from catix.settings import settings
from tests.test_account import DAY, _call, music_room  # noqa: F401 - music_room is a fixture
from tests.test_account import native_mcp  # noqa: F401 - synthetic MCP identity and transport
from tests.test_roles import ScriptedModel, _ask

pytestmark = pytest.mark.skipif(not settings.database_url, reason="needs the database (DATABASE_URL)")


@pytest.fixture
def owner():
    """A user of its own; their chats, answers and the agent's threads go afterwards."""
    innohassle_id = f"test:{uuid.uuid4().hex}"
    yield innohassle_id
    with pg.connection() as conn:
        threads = [chats.thread_of(c) for c in pg.column(conn, "SELECT chat_id FROM api_chats WHERE innohassle_id = %s", (innohassle_id,))]
        conn.execute("DELETE FROM api_chats WHERE innohassle_id = %s", (innohassle_id,))  # the answers go with them
        if pg.scalar(conn, "SELECT to_regclass('checkpoints') IS NOT NULL"):
            for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
                conn.execute(f"DELETE FROM {table} WHERE thread_id = ANY(%s)", (threads,))  # noqa: S608 - fixed names


def answer(chat_id: str, text: str, ask_query_id: str | None = None) -> AskResponses:
    return AskResponses(query=f"q:{text}", answer=text, chat_id=chat_id, ask_query_id=ask_query_id, search_responses=[], messages=[{"a": 1}])


def test_a_chat_is_named_by_the_model_until_the_user_renames_it(owner):
    chat_id = chats.start(owner, "когда пересдача")
    assert chats.needs_title(chat_id) and not chats.needs_title("nope")
    chats.save_answer(answer(chat_id, "first"), None, "cp-1", title="Пересдачи")
    assert chats.history(chat_id, owner).title == "Пересдачи" and not chats.needs_title(chat_id)  # type: ignore[union-attr]
    chats.save_answer(answer(chat_id, "second"), None, "cp-2", title="Другое")  # named already: kept
    assert chats.history(chat_id, owner).title == "Пересдачи"  # type: ignore[union-attr]

    assert chats.rename(chat_id, "somebody else", "чужое") is None
    renamed = chats.rename(chat_id, owner, "  Мои пересдачи ")
    assert renamed is not None and renamed.title == "Мои пересдачи"
    chats.save_answer(answer(chat_id, "third"), None, "cp-3", title="Модель")
    assert chats.of_user(owner)[0].title == "Мои пересдачи"


def test_a_chat_keeps_its_answers_and_votes(owner):
    chat_id = chats.start(owner, "  Когда пересдача?  ")
    empty = chats.start(owner, "no answer yet")
    assert chats.owner(chat_id) == owner and chats.owner("nope") is None
    assert chats.checkpoint(chat_id) is None

    chats.save_answer(answer(chat_id, "first", ask_query_id=f"{chat_id}-1"), "span-1", "cp-1")
    chats.save_answer(answer(chat_id, "second"), None, "cp-2")  # tracing was off: nothing to vote on
    assert chats.checkpoint(chat_id) == "cp-2"
    assert [c.chat_id for c in chats.of_user(owner)] == [chat_id]  # a chat without an answer is not listed
    assert chats.of_user(owner)[0].title == "Когда пересдача?"

    assert chats.asked(f"{chat_id}-1") == (owner, "span-1") and chats.asked("nope") is None
    chats.vote(f"{chat_id}-1", "dislike", "wrong date")
    history = chats.history(chat_id, owner)
    assert history is not None and history.title == "Когда пересдача?"
    assert [(a.answer, a.feedback, a.feedback_comment, a.messages) for a in history.answers] == [
        ("first", "dislike", "wrong date", []),
        ("second", None, None, []),
    ]
    assert chats.history(chat_id, "somebody else") is None
    assert chats.history(empty, owner).answers == []  # type: ignore[union-attr]

    chats.save_answer(answer(empty, "now"), None, "cp-3")
    assert [c.chat_id for c in chats.of_user(owner)] == [empty, chat_id]  # the last answered first


def test_a_deleted_chat_goes_with_its_answers(owner):
    chat_id = chats.start(owner, "удалить")
    kept = chats.start(owner, "оставить")
    chats.save_answer(answer(chat_id, "first", ask_query_id=f"{chat_id}-1"), "span-1", "cp-1")
    chats.save_answer(answer(kept, "kept"), None, "cp-2")
    chats.vote(f"{chat_id}-1", "like", None)

    assert not chats.delete(chat_id, "somebody else") and chats.owner(chat_id) == owner
    assert chats.delete(chat_id, owner)
    assert chats.owner(chat_id) is None and chats.history(chat_id, owner) is None and chats.asked(f"{chat_id}-1") is None
    with pg.connection() as conn:
        assert pg.scalar(conn, "SELECT count(*) FROM api_answers WHERE chat_id = %s", (chat_id,)) == 0
    assert [c.chat_id for c in chats.of_user(owner)] == [kept]
    assert not chats.delete(chat_id, owner)  # gone already


def test_the_agent_remembers_a_chat_after_a_restart(owner, monkeypatch):
    script = [_ask("ask_chats", "вопрос"), AIMessage("Отчёт помощника."), AIMessage("Ответ.")]  # each question: helper, report, answer
    monkeypatch.setattr(ask, "build_agent", lambda checkpointer: build_agent(ScriptedModel(responses=script), guardrail=False,
                                                                            checkpointer=checkpointer))
    monkeypatch.setattr(ask.groups, "scoped_chat_ids", lambda key, telegram_id: set())
    monkeypatch.setattr(ask.groups, "effective_group", lambda key, telegram_id: ask.groups.ALL)
    monkeypatch.setattr(ask.titles, "name", lambda question: "Вопросы")
    user = UserTokenData(innohassle_id=owner, email="a@innopolis.university", telegram_id=None)
    chat_id = chats.start(owner, "первый вопрос")

    async def ask_once(question: str) -> list:
        async with ask.memory():  # the API starts, answers and stops
            await ask.run(question, chat_id, user)
            state = await ask.agent().aget_state({"configurable": {"thread_id": chats.thread_of(chat_id)}})
            return [m.text for m in state.values["messages"] if m.type == "human"]

    assert asyncio.run(ask_once("первый вопрос")) == ["первый вопрос"]
    assert asyncio.run(ask_once("второй вопрос")) == ["первый вопрос", "второй вопрос"]
    history = chats.history(chat_id, owner)
    assert history is not None and [a.query for a in history.answers] == ["первый вопрос", "второй вопрос"]
    assert history.title == "Вопросы"


def test_a_question_waits_in_the_chat_for_the_decision_that_is_made_once(owner, monkeypatch, music_room, native_mcp):  # noqa: F811
    asked = "забронируй музкомнату послезавтра с 18 до 19"
    script = [
        _call("call_api_tool", {"name": "music_book_music_room", "arguments": {
            "day": DAY.isoformat(), "time_from": "18:00", "time_to": "19:00"}}, "h1"),
        AIMessage("Готово: музкомната ваша."),
    ]
    monkeypatch.setattr(ask, "build_agent", lambda checkpointer: build_agent(ScriptedModel(responses=script), guardrail=False,
                                                                            checkpointer=checkpointer))
    monkeypatch.setattr(ask.groups, "scoped_chat_ids", lambda key, telegram_id: set())
    monkeypatch.setattr(ask.groups, "effective_group", lambda key, telegram_id: ask.groups.ALL)
    monkeypatch.setattr(ask.titles, "name", lambda question: "Музкомната")
    user = UserTokenData(innohassle_id=owner, email="a@innopolis.university", telegram_id=None, token=SecretStr("user-token"))
    chat_id = chats.start(owner, asked)

    async def ask_and_decide():
        async with ask.memory():
            waits = await ask.run(asked, chat_id, user)
            assert waits.approval is not None and not music_room, "nothing is booked before the user decides"
            assert [c.chat_id for c in chats.of_user(owner)] == [chat_id], "a chat that waits is listed"
            history = chats.history(chat_id, owner)
            assert history is not None and history.answers == [] and history.waiting.approval == waits.approval  # type: ignore[union-attr]
            with pytest.raises(ask.NothingToDecide):  # not the approval that waits
                await ask.run(asked, chat_id, user, decision=AskDecision(decision="approve", approval_id="another"))
            done = await ask.run(asked, chat_id, user, decision=AskDecision(decision="approve", approval_id=waits.approval.id))
            with pytest.raises(ask.NothingToDecide):  # decided already: the music room is not booked twice
                await ask.run(asked, chat_id, user, decision=AskDecision(decision="approve", approval_id=waits.approval.id))
            return done

    done = asyncio.run(ask_and_decide())
    assert done.answer == "Готово: музкомната ваша." and done.approval is None
    assert [(token, f"{start:%H:%M}") for token, start, _ in music_room] == [("user-token", "18:00")]
    history = chats.history(chat_id, owner)
    assert history is not None and history.waiting is None and [a.answer for a in history.answers] == [done.answer]
    assert history.title == "Музкомната"
