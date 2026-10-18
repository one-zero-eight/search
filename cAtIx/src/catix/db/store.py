"""Postgres storage of chat messages: hybrid search (BM25 + vectors) and the access bookkeeping.

Everything here is synchronous and uses the connection pool, so it is safe to call from worker threads.
Async code runs it with asyncio.to_thread.
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Collection, Iterable
from dataclasses import dataclass
from datetime import datetime

from catix import userbot_config
from catix.common import courses
from catix.db import pg
from catix.ingest import usefulness
from catix.db.rows import ChatRow, MemberRow, MessageHit, SourceRow
from catix.settings import settings

log = logging.getLogger("catix.store")

MAX_QUERIES = 8  # Angles per search call.
# How much a message gains from also being found by the other queries. Small on purpose: queries about different
# courses all contain "мидтерм", and summing their ranks would let the generic midterm messages crowd out the
# one message that only the query for its own course finds (it fell to 26th of 40 that way).
CROSS_QUERY_BONUS = 0.1
YEAR_RE = re.compile(r"^(19|20)\d\d$")

GENERAL_TOPIC_ID = 1  # The default topic of every forum; its messages carry no topic id.
RRF_K = 60  # Reciprocal rank fusion constant; 60 is the value from the original paper.
CANDIDATES = 30  # Per method, before fusion.


# Question and filler words. With BM25 ranking a natural question ("когда меняют постельное бельё") is dominated by
# the common words; dropping them lifted lexical hit@5 from 55% to 64% in the evaluation. Vectors get the full text.
STOPWORDS = frozenset(
    """когда где как что какой какая какие какое каким кто почему зачем куда это этот эта для про при по на в во с со и а
    но или у к о об от до из за ли же бы можно нужно надо делать будет был была было были есть мне нам вам их он она
    они там тут здесь the a an is are was were be to of in on for and or how what when where which who why do does can
    i we""".split()
)


@dataclass
class Message:
    chat_id: int
    msg_id: int
    topic_id: int | None
    date: datetime
    edit_date: datetime | None
    sender_id: int | None
    sender_name: str | None
    reply_to: int | None
    text: str
    link: str | None
    sender_link: str | None = None  # Profile of the author, built from the @username where the messenger has one.


@dataclass(frozen=True)
class ChatInfo:
    chat_id: int
    title: str
    username: str | None
    via_bot: bool = False  # Seen by the Bot API bot, so getChatMember works for it.
    link: str | None = None  # Link to the chat, shown in sources when a message has no link of its own.


# ---- writing ----------------------------------------------------------------------------------------------


def write_batch(chats: Iterable[ChatInfo], messages: list[Message]) -> None:
    """Store chats and messages in one transaction. New or edited text is queued for embedding by a trigger."""
    latest = {c.chat_id: c for c in chats}
    scores = usefulness.score_all([m.text for m in messages])  # Before the transaction: it must not wait for the model.
    with pg.connection() as conn, conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO chats (chat_id, title, username, bot_member, link) VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (chat_id) DO UPDATE SET
                   title = excluded.title, username = excluded.username, link = coalesce(excluded.link, chats.link),
                   bot_member = chats.bot_member OR excluded.bot_member""",
            [(c.chat_id, c.title, c.username, c.via_bot, c.link) for c in latest.values()],
        )
        cur.executemany(
            """INSERT INTO messages (chat_id, msg_id, topic_id, date, edit_date, sender_id, sender_name, reply_to, text, link, sender_link,
                                     usefulness, filtered)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (chat_id, msg_id) DO UPDATE SET
                   text = excluded.text, edit_date = excluded.edit_date, sender_name = excluded.sender_name,
                   usefulness = excluded.usefulness, filtered = excluded.filtered
               -- Re-reading an unchanged message must not rewrite the row (and its search index entries).
               WHERE messages.text IS DISTINCT FROM excluded.text
                  OR messages.edit_date IS DISTINCT FROM excluded.edit_date""",
            [
                (m.chat_id, m.msg_id, m.topic_id, m.date, m.edit_date, m.sender_id, m.sender_name, m.reply_to, m.text, m.link, m.sender_link,
                 value, usefulness.is_useless(value))
                for m, value in zip(messages, scores)
            ],
        )
        # Whoever writes in a chat is a member of it.
        _set_members(cur, {(m.chat_id, m.sender_id) for m in messages if m.sender_id and m.sender_id > 0}, True)


def migrate_chat(old_id: int, new_id: int) -> dict[str, int]:
    """Move a chat to its new id after Telegram upgraded a basic group to a supergroup (the id changes).

    Messages, their vectors, member records and the chat row move to `new_id`. Safe to repeat. A message whose id is
    already taken in the new chat (old and new ids are separate numberings) stays under the old id rather than
    overwriting anything; the old chat row is kept while any message is left there.
    """
    counts = {"messages": 0, "left_behind": 0, "members": 0}
    if old_id == new_id:
        return counts
    with pg.connection() as conn:
        old = pg.row(conn, ChatRow, "SELECT chat_id, title, username, bot_member FROM chats WHERE chat_id = %s", (old_id,))
        if old is None:
            return counts  # Nothing stored under the old id: already moved, or never seen.
        conn.execute(
            """INSERT INTO chats (chat_id, title, username, bot_member) VALUES (%s, %s, %s, %s)
               ON CONFLICT (chat_id) DO UPDATE SET bot_member = chats.bot_member OR excluded.bot_member""",
            (new_id, old.title, old.username, old.bot_member),
        )
        params = {"old": old_id, "new": new_id}
        counts["messages"] = conn.execute(
            """UPDATE messages m SET chat_id = %(new)s WHERE m.chat_id = %(old)s
               AND NOT EXISTS (SELECT 1 FROM messages n WHERE n.chat_id = %(new)s AND n.msg_id = m.msg_id)""",
            params,
        ).rowcount
        # The vectors carry the chat id too (vector search filters on it).
        conn.execute(
            """UPDATE message_embeddings e SET chat_id = %(new)s FROM messages m
               WHERE e.message_id = m.id AND m.chat_id = %(new)s AND e.chat_id = %(old)s""",
            params,
        )
        counts["members"] = conn.execute(
            """INSERT INTO members (chat_id, user_id, is_member, checked_at)
               SELECT %(new)s, user_id, is_member, checked_at FROM members WHERE chat_id = %(old)s
               ON CONFLICT DO NOTHING""",
            params,
        ).rowcount
        conn.execute("DELETE FROM members WHERE chat_id = %(old)s", params)
        counts["left_behind"] = pg.scalar(conn, "SELECT count(*) FROM messages WHERE chat_id = %(old)s", params)
        if counts["left_behind"] == 0:
            conn.execute("DELETE FROM chats WHERE chat_id = %(old)s", params)
        else:
            log.warning("%d messages of chat %s kept their old id: the same message ids exist in %s", counts["left_behind"], old_id, new_id)
    mentioned = [name for name in ("tg_chats", "tg_open_chats", "extract_skip_chats") if old_id in getattr(settings, name, [])]
    if mentioned or old_id in settings.tg_topics:
        log.warning("chat id %s is still listed in .env (%s): replace it with %s", old_id, ", ".join(mentioned + (["tg_topics"] if old_id in settings.tg_topics else [])), new_id)
    return counts


def upsert_chat(chat_id: int, title: str, username: str | None, *, via_bot: bool = False) -> None:
    write_batch([ChatInfo(chat_id, title, username, via_bot)], [])


def upsert_messages(messages: list[Message]) -> None:
    """Store messages of chats that are already known."""
    write_batch([], messages)


def mark_synced(chat_id: int) -> None:
    with pg.connection() as conn:
        conn.execute("UPDATE chats SET synced_at = now() WHERE chat_id = %s", (chat_id,))


def _set_members(cur, pairs: Collection[tuple[int, int]], is_member: bool) -> None:
    if pairs:
        cur.executemany(
            """INSERT INTO members (chat_id, user_id, is_member, checked_at) VALUES (%s, %s, %s, now())
               ON CONFLICT (chat_id, user_id) DO UPDATE SET is_member = excluded.is_member, checked_at = excluded.checked_at""",
            [(chat_id, user_id, is_member) for chat_id, user_id in pairs],
        )


def set_members(pairs: Collection[tuple[int, int]], is_member: bool) -> None:
    with pg.connection() as conn, conn.cursor() as cur:
        _set_members(cur, pairs, is_member)


def unmark_bot_chat(chat_id: int) -> None:
    with pg.connection() as conn:
        conn.execute("UPDATE chats SET bot_member = false WHERE chat_id = %s", (chat_id,))


# ---- access bookkeeping -----------------------------------------------------------------------------------


def topic_allowed(chat_id: int, topic_id: int | None) -> bool:
    """Whether a message of this chat and topic should be stored (chosen in the bot with /listen, or TG_TOPICS)."""
    return userbot_config.topic_allowed(chat_id, topic_id, GENERAL_TOPIC_ID)


def public_chat_ids() -> set[int]:
    """Chats anyone may see: public (have a username) or explicitly opened in TG_OPEN_CHATS."""
    with pg.connection() as conn:
        public = pg.column(conn, "SELECT chat_id FROM chats WHERE username IS NOT NULL")
    return set(public) | set(settings.tg_open_chats)


def bot_chat_ids() -> set[int]:
    with pg.connection() as conn:
        return set(pg.column(conn, "SELECT chat_id FROM chats WHERE bot_member"))


def membership(user_id: int) -> dict[int, tuple[bool, datetime]]:
    """Cached membership of a user: chat id -> (is_member, when it was checked)."""
    with pg.connection() as conn:
        rows = pg.rows(conn, MemberRow, "SELECT chat_id, is_member, checked_at FROM members WHERE user_id = %s", (user_id,))
    return {r.chat_id: (r.is_member, r.checked_at) for r in rows}


def last_msg_id(chat_id: int, topic_id: int | None = None) -> int | None:
    """Newest stored message of a chat, or of one topic of it."""
    if topic_id is None:
        sql, params = "SELECT max(msg_id) AS m FROM messages WHERE chat_id = %s", (chat_id,)
    elif topic_id == GENERAL_TOPIC_ID:
        sql, params = "SELECT max(msg_id) AS m FROM messages WHERE chat_id = %s AND (topic_id IS NULL OR topic_id = %s)", (chat_id, topic_id)
    else:
        sql, params = "SELECT max(msg_id) AS m FROM messages WHERE chat_id = %s AND topic_id = %s", (chat_id, topic_id)
    with pg.connection() as conn:
        return pg.scalar(conn, sql, params)


# ---- search -----------------------------------------------------------------------------------------------


def _resolve_chats(chat: str | None, chat_ids: Collection[int] | None) -> list[int] | None:
    """Chats to search in: the allowed ones, narrowed to those matching `chat` (title part or @username)."""
    allowed = None if chat_ids is None else list(chat_ids)
    if not chat:
        return allowed
    with pg.connection() as conn:
        found = pg.column(conn, "SELECT chat_id FROM chats WHERE title ILIKE %s OR username = %s", (f"%{chat}%", chat.lstrip("@")))
    return found if allowed is None else [c for c in found if c in set(allowed)]


def _filters(chat_col: str, date_col: str, ids: list[int] | None, date_from: str | None, date_to: str | None) -> tuple[str, dict]:
    sql, params = "", {}
    if ids is not None:
        sql += f" AND {chat_col} = ANY(%(ids)s::bigint[])"
        params["ids"] = ids
    if date_from:
        sql += f" AND {date_col} >= %(date_from)s::date"
        params["date_from"] = date_from
    if date_to:
        sql += f" AND {date_col} < %(date_to)s::date + 1"
        params["date_to"] = date_to
    return sql, params


def _bm25(words: str, ids: list[int] | None, date_from: str | None, date_to: str | None) -> list[int]:
    filters, params = _filters("chat_id", "date", ids, date_from, date_to)
    # The text is indexed twice (Russian and English stemmer); a message matches if either field does.
    sql = f"""SELECT id FROM messages
              WHERE (text ||| %(q)s OR text::pdb.alias('text_en') ||| %(q)s) AND filtered = false{filters}
              ORDER BY pdb.score(id) DESC LIMIT %(n)s"""
    with pg.connection() as conn:
        return pg.column(conn, sql, {"q": words, "n": CANDIDATES, **params})


def _embed_all(queries: list[str]) -> list[list[float]]:
    """Vectors for all queries in one request; empty if the embeddings server is unavailable."""
    try:
        return pg.embed(queries)
    except Exception:  # noqa: BLE001 - search must keep working on words alone if the embeddings server is down
        log.warning("embeddings server unavailable, searching by words only", exc_info=True)
        return []


def _vector(vector: list[float], ids: list[int] | None, date_from: str | None, date_to: str | None) -> list[int]:
    filters, params = _filters("e.chat_id", "m.date", ids, date_from, date_to)
    # Dates live on the message, not on its vector.
    join = " JOIN messages m ON m.id = e.message_id" if date_from or date_to else ""
    sql = f"""SELECT e.message_id AS id FROM message_embeddings e{join}
              WHERE true{filters}
              ORDER BY e.embedding <=> %(v)s::vector LIMIT %(n)s"""
    with pg.connection() as conn, conn.transaction():
        # With a selective filter (the chats a user may see) HNSW would return too few rows; this keeps scanning.
        conn.execute("SET LOCAL hnsw.iterative_scan = relaxed_order")
        return pg.column(conn, sql, {"v": vector, "n": CANDIDATES, **params})


def _words(query: str) -> str:
    """The query as the BM25 side sees it: course aliases added, filler words and bare years removed.

    A year ("мидтерм 2026") is a rare token to BM25, so it outranks the real topic and pulls in every
    announcement that mentions 2026.
    """
    all_words = re.findall(r"\w+", courses.expand_query(query).lower())
    useful = [w for w in all_words if w not in STOPWORDS and not YEAR_RE.match(w)]
    return " ".join(dict.fromkeys(useful or all_words))


def _rrf(*rankings: list[int]) -> dict[int, float]:
    """Reciprocal rank fusion of several rankings (here: words and meaning for one query)."""
    score: dict[int, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, 1):
            score[item] = score.get(item, 0.0) + 1.0 / (RRF_K + rank)
    return score


def _combine(per_query: list[dict[int, float]], limit: int) -> list[int]:
    """Merge the queries' scores into one list of `limit` messages.

    Every query first gets its own best hits reserved (coverage: the query about one course must not lose its
    message to generic ones); the rest of the list is filled by a combined score, where a message counts mostly
    for its best query and a little for the others. The result is ordered by that combined score.
    """
    found: dict[int, list[float]] = {}
    for scores in per_query:
        for item, value in scores.items():
            found.setdefault(item, []).append(value)
    total = {item: max(v) + CROSS_QUERY_BONUS * (sum(v) - max(v)) for item, v in found.items()}

    reserved: list[int] = []
    per_each = max(1, limit // len(per_query))
    for scores in per_query:
        for item in sorted(scores, key=lambda item: scores[item], reverse=True)[:per_each]:
            if item not in reserved:
                reserved.append(item)
    chosen = reserved[:limit]
    for item in sorted(total, key=lambda item: total[item], reverse=True):
        if len(chosen) >= limit:
            break
        if item not in chosen:
            chosen.append(item)
    return sorted(chosen, key=lambda item: total[item], reverse=True)


def search(
    queries: str | list[str],
    *,
    chat: str | None = None,
    chat_ids: Collection[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 15,
) -> list[MessageHit]:
    """Hybrid search from one or several angles: BM25 on the words plus vector similarity for each query, all
    rankings merged by reciprocal rank fusion, so a message found by several angles rises to the top.

    `chat_ids` restricts the search to chats the asker may see (None = all).
    """
    if isinstance(queries, str):
        queries = [queries]
    # Drop empty and repeated queries (the model often repeats itself); embed everything in one request.
    queries = list(dict.fromkeys(q.strip() for q in queries if q.strip()))[:MAX_QUERIES]
    queries = [q for q in queries if _words(q)]
    if not queries:
        return []
    ids = _resolve_chats(chat, chat_ids)
    if ids is not None and not ids:
        return []

    vectors = _embed_all(queries)
    with ThreadPoolExecutor(max_workers=4) as executor:
        jobs = []  # per query: (words job, vector job or None)
        for i, q in enumerate(queries):
            jobs.append((
                executor.submit(_bm25, _words(q), ids, date_from, date_to),
                executor.submit(_vector, vectors[i], ids, date_from, date_to) if vectors else None,
            ))
        per_query = [_rrf(*[job.result() for job in pair if job]) for pair in jobs]
    reranking = settings.reranker_route is not None
    fused = _combine(per_query, max(limit, settings.rerank_candidates) if reranking else limit)
    if not fused:
        return []
    with pg.connection() as conn:
        rows = pg.rows(
            conn,
            MessageHit,
            """SELECT m.id AS ref_id, m.chat_id, m.msg_id, m.date, m.edit_date, m.sender_name, m.reply_to, m.text, m.link,
                      c.title AS chat_title, p.sender_name AS parent_sender, p.text AS parent_text
               FROM messages m
               JOIN chats c ON c.chat_id = m.chat_id
               LEFT JOIN messages p ON p.chat_id = m.chat_id AND p.msg_id = m.reply_to
               WHERE m.id = ANY(%s::bigint[])""",
            (fused,),
        )
    by_id = {r.ref_id: r for r in rows}
    hits = [by_id[i] for i in fused if i in by_id]
    return _rerank(queries, hits, limit) if reranking else hits


def _rerank(queries: list[str], hits: list[MessageHit], limit: int) -> list[MessageHit]:
    """The `limit` messages the reranker finds closest to any of the queries (its best score counts), above the cutoff.

    If the reranker server is down the hybrid ranking stays as it was.
    """
    if len(hits) <= 1:
        return hits[:limit]
    # A short reply ("да, в пятницу") means little without the message it answers.
    documents = [f"{h.parent_text[:200]}\n{h.text[:600]}" if h.parent_text else h.text[:600] for h in hits]
    try:
        with ThreadPoolExecutor(max_workers=len(queries)) as executor:
            scores = list(executor.map(lambda q: pg.rerank(q, documents), queries))
    except Exception:  # noqa: BLE001 - search must keep working without the reranker
        log.warning("reranker server unavailable, keeping the hybrid ranking", exc_info=True)
        return hits[:limit]
    best = [max(per_query[i] for per_query in scores) for i in range(len(hits))]
    order = sorted(range(len(hits)), key=lambda i: best[i], reverse=True)[:limit]
    log.debug("rerank scores of %s: %s", queries, [round(best[i], 2) for i in order])
    if settings.rerank_min_score is not None:
        order = [i for i in order if best[i] >= settings.rerank_min_score]
    return [hits[i] for i in order]


def message_sources(ids: list[int]) -> dict[int, SourceRow]:
    """What a source list needs about messages, by id."""
    if not ids:
        return {}
    with pg.connection() as conn:
        rows = pg.rows(
            conn,
            SourceRow,
            """SELECT m.id, m.date, m.sender_name, m.sender_link, m.link, c.link AS chat_link, c.title AS chat_title
               FROM messages m JOIN chats c ON c.chat_id = m.chat_id WHERE m.id = ANY(%s::bigint[])""",
            (ids,),
        )
    return {r.id: r for r in rows}
