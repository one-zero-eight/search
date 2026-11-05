"""The conversations of the site's assistant (POST /ask/) in Postgres, tables api_chats and api_answers (db/schema.sql): whose
each chat is, its answers as the client got them with the user's 👍/👎, and the checkpoint the agent's thread of the chat
goes on from. The agent's thread itself is in LangGraph's tables (AsyncPostgresSaver, api/ask.py `memory`).

The functions block: the API calls them with asyncio.to_thread.
"""

from psycopg.types.json import Jsonb

from catix.api import state
from catix.api.schemas import AskChat, AskChatHistory, AskResponses
from catix.db import pg

TITLE_MAX = 200  # characters of the first question kept as the chat's title
LISTED = 100  # chats in GET /ask/chats


def thread_of(chat_id: str) -> str:
    """The agent's thread of the chat."""
    return f"api:{chat_id}"


def start(innohassle_id: str, question: str) -> str:
    """A new chat of the user, titled by its first question."""
    chat_id = state.new_id()
    with pg.connection() as conn:
        conn.execute(
            "INSERT INTO api_chats (chat_id, innohassle_id, title) VALUES (%s, %s, %s)",
            (chat_id, innohassle_id, question.strip()[:TITLE_MAX]),
        )
    return chat_id


def owner(chat_id: str) -> str | None:
    """The InNoHassle id of the chat's owner; None when there is no such chat."""
    with pg.connection() as conn:
        return pg.scalar(conn, "SELECT innohassle_id FROM api_chats WHERE chat_id = %s", (chat_id,))


def checkpoint(chat_id: str) -> str | None:
    """The checkpoint of the agent's thread after the chat's last answer; None before the first one."""
    with pg.connection() as conn:
        return pg.scalar(conn, "SELECT checkpoint FROM api_chats WHERE chat_id = %s", (chat_id,))


def save_answer(response: AskResponses, span_id: str | None, checkpoint: str | None) -> None:
    """Keep an answer in its chat (`response.chat_id`), with the root span of its trace (what a vote annotates) and the
    checkpoint of the agent's thread after it, which the next question goes on from."""
    kept = response.model_dump(mode="json", exclude={"messages", "feedback", "feedback_comment"})
    with pg.connection() as conn:
        conn.execute(
            "INSERT INTO api_answers (chat_id, ask_query_id, span_id, response) VALUES (%s, %s, %s, %s)",
            (response.chat_id, response.ask_query_id, span_id, Jsonb(kept)),
        )
        conn.execute("UPDATE api_chats SET checkpoint = %s, updated_at = now() WHERE chat_id = %s", (checkpoint, response.chat_id))


def of_user(innohassle_id: str) -> list[AskChat]:
    """The user's chats that have an answer, the last answered first."""
    with pg.connection() as conn:
        rows = conn.execute(
            """SELECT chat_id, title, created_at, updated_at FROM api_chats c
               WHERE innohassle_id = %s AND EXISTS (SELECT 1 FROM api_answers a WHERE a.chat_id = c.chat_id)
               ORDER BY updated_at DESC LIMIT %s""",
            (innohassle_id, LISTED),
        ).fetchall()
    return [AskChat(**row) for row in rows]


def history(chat_id: str, innohassle_id: str) -> AskChatHistory | None:
    """The chat with its answers, the oldest first; None when it is not the user's."""
    with pg.connection() as conn:
        chat = conn.execute(
            "SELECT chat_id, title, created_at, updated_at FROM api_chats WHERE chat_id = %s AND innohassle_id = %s",
            (chat_id, innohassle_id),
        ).fetchone()
        if chat is None:
            return None
        rows = conn.execute("SELECT response, feedback, comment FROM api_answers WHERE chat_id = %s ORDER BY id", (chat_id,)).fetchall()
    answers = [AskResponses(**row["response"], messages=[], feedback=row["feedback"], feedback_comment=row["comment"]) for row in rows]
    return AskChatHistory(**chat, answers=answers)


def asked(ask_query_id: str) -> tuple[str, str] | None:
    """(the InNoHassle id of the chat's owner, the root span of the answer's trace) of an answer; None when there is none."""
    with pg.connection() as conn:
        row = conn.execute(
            "SELECT c.innohassle_id, a.span_id FROM api_answers a JOIN api_chats c USING (chat_id) WHERE a.ask_query_id = %s",
            (ask_query_id,),
        ).fetchone()
    return None if row is None else (row["innohassle_id"], row["span_id"])


def vote(ask_query_id: str, feedback: str, comment: str | None) -> None:
    """The user's 👍/👎 on an answer with what they said of it; it replaces the one before."""
    with pg.connection() as conn:
        conn.execute("UPDATE api_answers SET feedback = %s, comment = %s WHERE ask_query_id = %s", (feedback, comment, ask_query_id))
