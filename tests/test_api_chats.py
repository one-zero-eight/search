"""The site's chats in the database (api/chats.py), and the agent's memory of a chat in Postgres (api/ask.py `memory`): the
user comes back to a chat after the API restarts and the agent still knows what was said. Skipped without DATABASE_URL;
the rows and threads of the test's own user are removed afterwards."""

import asyncio
import uuid

import pytest
from langchain_core.messages import AIMessage

from catix.agent.core import build_agent
from catix.api import ask, chats
from catix.api.auth import UserTokenData
from catix.api.schemas import AskResponses
from catix.db import pg
from catix.settings import settings
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


def test_the_agent_remembers_a_chat_after_a_restart(owner, monkeypatch):
    script = [_ask("ask_chats", "вопрос"), AIMessage("Отчёт помощника."), AIMessage("Ответ.")]  # each question: helper, report, answer
    monkeypatch.setattr(ask, "build_agent", lambda checkpointer: build_agent(ScriptedModel(responses=script), guardrail=False,
                                                                            checkpointer=checkpointer))
    monkeypatch.setattr(ask.groups, "scoped_chat_ids", lambda key, telegram_id: set())
    monkeypatch.setattr(ask.groups, "effective_group", lambda key, telegram_id: ask.groups.ALL)
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
