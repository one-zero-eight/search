"""Database setup.

    catix-db init      # create the read-only role, apply db/schema.sql (safe to repeat)
    catix-db migrate   # copy chats and messages from the old SQLite file; drop its extracted events
    catix-db status    # per chat: messages, vectors, messages waiting for a vector
    catix-db migrate-chat OLD NEW   # a basic group became a supergroup: move its messages and vectors to the new id
    catix-db prune-noise [yes]      # list the stored messages ingest/noise.py would not store now (yes = delete them)
"""

import argparse
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from psycopg import sql

from catix.db import pg
from catix.db import store
from catix.db.rows import ChatStatus
from catix.ingest import noise
from catix.settings import settings

SCHEMA = Path(__file__).resolve().parents[3] / "db" / "schema.sql"
READER = "ctx_reader"
BATCH = 500


def init() -> None:
    if not settings.reader_password:
        raise SystemExit("Set READER_PASSWORD in .env: the password of the read-only role that runs the model's SQL.")
    password = sql.Literal(settings.reader_password.get_secret_value())
    with pg.connect() as conn:
        conn.autocommit = True
        exists = pg.scalar(conn, "SELECT 1 FROM pg_roles WHERE rolname = %s", (READER,))
        verb = "ALTER ROLE" if exists else "CREATE ROLE"
        conn.execute(sql.SQL("{} {} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD {}").format(
            sql.SQL(verb), sql.Identifier(READER), password))
        database = pg.scalar(conn, "SELECT current_database()")
        conn.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(database), sql.Identifier(READER)))
        # Defaults for every session of the role; the app also enforces them per query.
        for setting, value in [("search_path", "visible, pg_catalog"), ("statement_timeout", "'5s'"), ("default_transaction_read_only", "on")]:
            conn.execute(sql.SQL("ALTER ROLE {} SET {} = {}").format(sql.Identifier(READER), sql.Identifier(setting), sql.SQL(value)))
        conn.execute(sql.SQL(SCHEMA.read_text(encoding="utf-8").replace("__TZ__", settings.timezone)))  # type: ignore[arg-type]  # a file, not user input
        queued = pg.scalar(conn, "SELECT count(*) FROM embedding_queue")
    print(f"schema applied; {queued} messages waiting for a vector")


def prune_noise(args: list[str]) -> None:
    """Find stored messages that ingest/noise.py rejects now; with `yes` delete them (their vectors go with them)."""
    with pg.connection() as conn:
        rows = conn.execute("SELECT id, text FROM messages").fetchall()
    found = [r for r in rows if noise.is_noise(r["text"])]
    print(f"{len(found)} of {len(rows)} messages are noise")
    shown: dict[str, int] = {}
    for r in found:  # Distinct texts with counts, most frequent first.
        shown[r["text"].strip()] = shown.get(r["text"].strip(), 0) + 1
    for text, count in sorted(shown.items(), key=lambda x: -x[1])[:40]:
        print(f"  {count:>4} x {text[:80]!r}")
    if args[:1] != ["yes"]:
        print("nothing deleted; run `catix-db prune-noise yes` to delete them")
        return
    with pg.connection() as conn:
        deleted = conn.execute("DELETE FROM messages WHERE id = ANY(%s::bigint[])", ([r["id"] for r in found],)).rowcount
    print(f"deleted {deleted} messages with their vectors")


def _ts(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _required_ts(value: str) -> datetime:
    parsed = _ts(value)
    assert parsed is not None
    return parsed


def migrate() -> None:
    src = sqlite3.connect(settings.messages_db)
    src.row_factory = sqlite3.Row
    chats = {
        r["chat_id"]: store.ChatInfo(r["chat_id"], r["title"], r["username"], bool(r["bot_member"]))
        for r in src.execute("SELECT chat_id, title, username, bot_member FROM chats")
    }
    rows = src.execute(
        """SELECT chat_id, msg_id, topic_id, date, edit_date, sender_id, sender_name, reply_to, text, link
           FROM messages ORDER BY date"""
    ).fetchall()
    known = [r for r in rows if r["chat_id"] in chats]
    print(f"{len(chats)} chats, {len(known)} messages ({len(rows) - len(known)} without a chat skipped)")
    store.write_batch(chats.values(), [])
    for i in range(0, len(known), BATCH):
        store.write_batch([], [
            store.Message(r["chat_id"], r["msg_id"], r["topic_id"], _required_ts(r["date"]), _ts(r["edit_date"]),
                          r["sender_id"], r["sender_name"], r["reply_to"], r["text"], r["link"])
            for r in known[i : i + BATCH]
        ])
    with pg.connection() as conn:
        counts = {t: pg.scalar(conn, f"SELECT count(*) FROM {t}") for t in ("chats", "messages", "embedding_queue")}  # noqa: S608
    print("postgres now:", counts)
    events = src.execute("SELECT count(*) FROM events").fetchone()[0] if src.execute("SELECT 1 FROM sqlite_master WHERE name = 'events'").fetchone() else 0
    src.execute("DROP TABLE IF EXISTS events")
    src.commit()
    src.execute("VACUUM")
    print(f"dropped the extracted events from the SQLite file ({events} rows); they are not used any more")


def status() -> None:
    """Per chat: stored messages, how many have a vector, how many wait for one."""
    with pg.connection() as conn:
        rows = pg.rows(
            conn,
            ChatStatus,
            """SELECT c.title, c.chat_id,
                      count(m.id) AS messages,
                      count(e.message_id) AS with_vector,
                      count(q.message_id) AS queued,
                      count(m.id) - count(e.message_id) - count(q.message_id) AS neither,
                      to_char(max(m.date) AT TIME ZONE %s, 'DD.MM HH24:MI') AS newest
               FROM chats c
               LEFT JOIN messages m ON m.chat_id = c.chat_id
               LEFT JOIN message_embeddings e ON e.message_id = m.id
               LEFT JOIN embedding_queue q ON q.message_id = m.id
               GROUP BY c.chat_id, c.title ORDER BY max(m.date) DESC NULLS LAST""",
            (settings.timezone,),
        )
        oldest = pg.scalar(conn, "SELECT now() - min(queued_at) FROM embedding_queue")
    print(f"{'chat':<44} {'messages':>8} {'vectors':>8} {'queued':>7} {'neither':>8}  newest message")
    for r in rows:
        flag = "  <-- messages without a vector" if r.neither else ""
        print(f"{r.title[:43]:<44} {r.messages:>8} {r.with_vector:>8} {r.queued:>7} {r.neither:>8}  {r.newest or '-'}{flag}")
    print(
        f"{'TOTAL':<44} {sum(r.messages for r in rows):>8} {sum(r.with_vector for r in rows):>8} "
        f"{sum(r.queued for r in rows):>7} {sum(r.neither for r in rows):>8}"
    )
    print(f"oldest message waiting in the queue: {oldest if oldest else 'none, the queue is empty'}")


def migrate_chat(args: list[str]) -> None:
    if len(args) != 2:
        raise SystemExit("Usage: catix-db migrate-chat OLD_ID NEW_ID  (a basic group that became a supergroup)")
    old, new = int(args[0]), int(args[1])
    print(f"moved {old} -> {new}:", store.migrate_chat(old, new))


def main() -> None:
    parser = argparse.ArgumentParser(prog="catix-db", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["init", "migrate", "status", "migrate-chat", "prune-noise"])
    parser.add_argument("args", nargs="*", help="OLD_ID NEW_ID, for migrate-chat; `yes` for prune-noise")
    parsed = parser.parse_args()
    try:
        if parsed.command == "migrate-chat":
            migrate_chat(parsed.args)
        elif parsed.command == "prune-noise":
            prune_noise(parsed.args)
        else:
            {"init": init, "migrate": migrate, "status": status}[parsed.command]()
    finally:
        pg.close()
