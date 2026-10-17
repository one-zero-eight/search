"""Read-only SQL for the agent, limited to the chats the asker may see.

How it is kept safe (see the bottom of db/schema.sql):
- the query runs on its own connection as the role ctx_reader, which has no rights on any table, only SELECT on the
  views visible.chats and visible.messages;
- the views show the chats stored for that connection's backend pid in query_context, a table the role cannot read
  or change, so the filter cannot be switched off from inside the query;
- the view filter runs before anything the query adds (security_barrier);
- the transaction is read-only, has a statement timeout, and the query runs inside a server-side cursor, which
  accepts a single SELECT only and sends back just the first rows.
"""

import re
from collections.abc import Collection
from datetime import date, datetime
from decimal import Decimal

import psycopg
from psycopg import errors
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.rows import tuple_row

from catix.db import pg
from catix.settings import settings

MAX_ROWS = 50
MAX_CELL = 300
TIMEOUT = "5s"
READER = "ctx_reader"

DESCRIPTION = """\
Run one read-only PostgreSQL SELECT over the chat messages, for questions the other tools cannot answer:
counts, rankings, lists with several filters ("сколько сообщений за неделю", "что писал староста",
"какие чаты есть"). Do NOT use it to find the answer to a question about content (use search_chats: it ranks by
relevance and meaning). Always add LIMIT; at most 50 rows are returned.

Tables (only the chats the user may see; nothing else exists):
  visible.chats(chat_id, title, username)
  visible.messages(ref, chat_id, chat, topic_id, day, sent_at, sender_name, reply_to, text, link)
      day = local date, sent_at = timestamptz, chat = chat title, ref identifies the message for citations.
Rules:
  - PostgreSQL syntax. Case-insensitive text match, Cyrillic included: text ILIKE '%мидтерм%'.
  - Dates: day >= current_date - 7; date_trunc('day', sent_at); count(*) FILTER (WHERE ...).
  - Select the `ref` column of messages you mention and cite it like the results of other tools."""


def _reader_conninfo() -> str:
    if not settings.database_url or not settings.reader_password:
        raise RuntimeError("DATABASE_URL and READER_PASSWORD must be set; run `catix-db init`")
    info = conninfo_to_dict(settings.database_url)
    info.update(user=READER, password=settings.reader_password.get_secret_value())
    return make_conninfo(**info)


def _cell(value: object) -> object:
    if isinstance(value, str):
        return value[:MAX_CELL] + "…" if len(value) > MAX_CELL else value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (bytes, memoryview)):
        return f"<{len(value)} bytes>"
    return value


def _unique(columns: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    names = []
    for name in columns:
        seen[name] = seen.get(name, 0) + 1
        names.append(name if seen[name] == 1 else f"{name}_{seen[name]}")
    return names


def run(query: str, allowed_chat_ids: Collection[int] | None) -> dict:
    """Execute a SELECT; problems are returned as {"error": ...} so the model can fix its query."""
    query = query.strip().rstrip(";").strip()
    if not re.match(r"(?is)(select|with|table|values)\b", query):
        return {"error": "Only a single SELECT (or WITH ... SELECT) statement is allowed."}
    try:
        reader = psycopg.connect(_reader_conninfo(), row_factory=tuple_row, connect_timeout=5)
    except (psycopg.Error, RuntimeError) as e:
        return {"error": f"The message database is not available: {e}"}

    pid = reader.info.backend_pid
    ids = None if allowed_chat_ids is None else [int(i) for i in allowed_chat_ids]
    try:
        # The context row is written by the app (a different connection, with rights the reader lacks).
        with pg.connection() as admin:
            admin.execute(
                """INSERT INTO query_context (backend_pid, chat_ids) VALUES (%s, %s::bigint[])
                   ON CONFLICT (backend_pid) DO UPDATE SET chat_ids = excluded.chat_ids, created_at = now()""",
                (pid, ids),
            )
        reader.read_only = True
        reader.execute(f"SET LOCAL statement_timeout = '{TIMEOUT}'")  # Starts the (read-only) transaction.
        with reader.cursor(name="q") as cursor:
            cursor.execute(query)
            columns = _unique([c.name for c in cursor.description])
            rows = cursor.fetchmany(MAX_ROWS + 1)
    except errors.QueryCanceled:
        return {"error": f"Query took longer than {TIMEOUT}; simplify it or add filters."}
    except errors.InsufficientPrivilege:
        return {"error": "Not authorized: only visible.messages and visible.chats are available."}
    except psycopg.Error as e:
        # Errors can quote a row ("invalid input syntax ...: <text>"): keep them short.
        return {"error": (e.diag.message_primary or str(e)).strip()[:300]}
    finally:
        try:
            reader.rollback()
        except psycopg.Error:
            pass
        reader.close()
        with pg.connection() as admin:
            admin.execute("DELETE FROM query_context WHERE backend_pid = %s", (pid,))

    result = {
        "columns": columns,
        # Dicts, not bare lists: refs are found by their key when sources are listed.
        "rows": [{name: _cell(value) for name, value in zip(columns, row)} for row in rows[:MAX_ROWS]],
    }
    if len(rows) > MAX_ROWS:
        result["note"] = f"Only the first {MAX_ROWS} rows are shown; add filters or aggregate."
    return result


def reset_context() -> None:
    """Drop context rows left behind by a crashed run."""
    with pg.connection() as conn:
        conn.execute("DELETE FROM query_context")
