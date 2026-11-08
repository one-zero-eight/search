"""The conversations of the site's assistant (POST /ask/) in Postgres, tables api_chats and api_answers (db/schema.sql): whose
each chat is and its name, its answers as the client got them with the user's 👍/👎, and the checkpoint the agent's thread
of the chat goes on from. A chat is named by its first question until the model names it (agent/titles.py) or the user
renames it; the model never replaces the user's name. The agent's thread itself is in LangGraph's tables (AsyncPostgresSaver, api/ask.py `memory`).
A question whose answer waits for the user's decision on actions (api/ask.py) is kept in the chat as `waiting` until the decision
gives the answer or a new question drops it.

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


def needs_title(chat_id: str) -> bool:
    """Whether the chat is still named by its first question: neither the model nor the user has named it."""
    with pg.connection() as conn:
        return bool(pg.scalar(conn, "SELECT title_by = 'question' FROM api_chats WHERE chat_id = %s", (chat_id,)))


def save_answer(response: AskResponses, span_id: str | None, checkpoint: str | None, title: str | None = None) -> None:
    """Keep an answer in its chat (`response.chat_id`), with the root span of its trace (what a vote annotates) and the
    checkpoint of the agent's thread after it, which the next question goes on from. `title` is the model's name of the
    chat: it is taken only while the chat is named by its question."""
    kept = response.model_dump(mode="json", exclude={"messages", "feedback", "feedback_comment"})
    with pg.connection() as conn:
        conn.execute(
            "INSERT INTO api_answers (chat_id, ask_query_id, span_id, response) VALUES (%s, %s, %s, %s)",
            (response.chat_id, response.ask_query_id, span_id, Jsonb(kept)),
        )
        conn.execute(
            "UPDATE api_chats SET checkpoint = %s, waiting_checkpoint = NULL, waiting = NULL, updated_at = now() WHERE chat_id = %s",
            (checkpoint, response.chat_id),
        )
        if title:
            conn.execute(
                "UPDATE api_chats SET title = %s, title_by = 'model' WHERE chat_id = %s AND title_by = 'question'",
                (title[:TITLE_MAX], response.chat_id),
            )


def save_waiting(response: AskResponses, checkpoint: str, interrupts: list[dict]) -> None:
    """Keep a question whose answer waits for the user's decision on `response.approval`: the checkpoint the agent paused at
    and its interrupts ({id, actions}: how many decisions each wants). The chat's own checkpoint stays that of its last
    answer: a new question goes on from it, as if this one had not been asked."""
    kept = response.model_dump(mode="json", exclude={"messages", "feedback", "feedback_comment"})
    with pg.connection() as conn:
        conn.execute(
            "UPDATE api_chats SET waiting_checkpoint = %s, waiting = %s, updated_at = now() WHERE chat_id = %s",
            (checkpoint, Jsonb({"response": kept, "interrupts": interrupts}), response.chat_id),
        )


def waiting(chat_id: str) -> tuple[str, list[dict], AskResponses] | None:
    """(the checkpoint to resume, the interrupts, what the client got) of the chat's question waiting for a decision; None."""
    with pg.connection() as conn:
        row = conn.execute("SELECT waiting_checkpoint, waiting FROM api_chats WHERE chat_id = %s", (chat_id,)).fetchone()
    if row is None or not row["waiting_checkpoint"] or not row["waiting"]:
        return None
    return row["waiting_checkpoint"], row["waiting"]["interrupts"], AskResponses(**row["waiting"]["response"], messages=[])


def take_waiting(chat_id: str, checkpoint: str) -> bool:
    """Take the question waiting at `checkpoint` for the decision now made: it waits no more, whether the agent then answers
    or fails, so that an action is never done twice (a second decision, or the same one again after the client went away).
    False when it is not waiting there any more (decided by another request meanwhile)."""
    with pg.connection() as conn:
        return conn.execute(
            "UPDATE api_chats SET waiting_checkpoint = NULL, waiting = NULL WHERE chat_id = %s AND waiting_checkpoint = %s",
            (chat_id, checkpoint),
        ).rowcount > 0


def rename(chat_id: str, innohassle_id: str, title: str) -> AskChat | None:
    """The user's name of their chat, which the model does not replace; None when the chat is not theirs."""
    with pg.connection() as conn:
        row = conn.execute(
            """UPDATE api_chats SET title = %s, title_by = 'user' WHERE chat_id = %s AND innohassle_id = %s
               RETURNING chat_id, title, created_at, updated_at""",
            (title.strip()[:TITLE_MAX], chat_id, innohassle_id),
        ).fetchone()
    return None if row is None else AskChat(**row)


def delete(chat_id: str, innohassle_id: str) -> bool:
    """The user's chat goes with its answers and their votes (ON DELETE CASCADE); False when the chat is not theirs. The
    agent's thread of it is the caller's to delete (api/ask.py `delete_chat`)."""
    with pg.connection() as conn:
        return conn.execute("DELETE FROM api_chats WHERE chat_id = %s AND innohassle_id = %s", (chat_id, innohassle_id)).rowcount > 0


def of_user(innohassle_id: str) -> list[AskChat]:
    """The user's chats with an answer, waiting decision or bound upload, most recently updated first."""
    with pg.connection() as conn:
        rows = conn.execute(
            """SELECT chat_id, title, created_at, updated_at FROM api_chats c
               WHERE innohassle_id = %s AND (c.waiting IS NOT NULL
                   OR EXISTS (SELECT 1 FROM api_answers a WHERE a.chat_id = c.chat_id)
                   OR EXISTS (SELECT 1 FROM api_attachments f WHERE f.chat_id = c.chat_id AND f.owner = c.innohassle_id))
               ORDER BY updated_at DESC LIMIT %s""",
            (innohassle_id, LISTED),
        ).fetchall()
    return [AskChat(**row) for row in rows]


def history(chat_id: str, innohassle_id: str) -> AskChatHistory | None:
    """The chat with its answers, the oldest first; None when it is not the user's."""
    with pg.connection() as conn:
        chat = conn.execute(
            "SELECT chat_id, title, created_at, updated_at, waiting FROM api_chats WHERE chat_id = %s AND innohassle_id = %s",
            (chat_id, innohassle_id),
        ).fetchone()
        if chat is None:
            return None
        rows = conn.execute("SELECT response, feedback, comment FROM api_answers WHERE chat_id = %s ORDER BY id", (chat_id,)).fetchall()
    answers = [AskResponses(**row["response"], messages=[], feedback=row["feedback"], feedback_comment=row["comment"]) for row in rows]
    pending = chat.pop("waiting")
    waiting_for = AskResponses(**pending["response"], messages=[]) if pending else None
    return AskChatHistory(**chat, answers=answers, waiting=waiting_for)


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
