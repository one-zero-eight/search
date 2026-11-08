"""Durable image OCR claims. No network/model calls; all operations are short transactions.

One independent 300-second lease covers all messenger processes, even if a message is
edited or deleted during recognition. Workers must bound their work below that lease.
Completion operations release only their own token, including stale/deleted jobs.
"""

from uuid import uuid4

from catix.db import pg


LEASE_SECONDS = 300
MAX_ATTEMPTS = 3


def claim(source: str) -> dict | None:
    """Return message_id, chat_id, msg_id, topic_id, refs (list), token; None if busy/not ready.

    Source is tguserbot, tgbot or maxbot; refs are opaque client-owned identifiers.
    """
    with pg.connection() as conn:
        # Serialize claim decisions across all three source processes, not the HTTP work.
        conn.execute("SELECT pg_advisory_xact_lock(727014, 1)")
        if conn.execute("SELECT 1 FROM image_queue_lease WHERE lease_until > now()").fetchone():
            return None
        # A process killed on its last attempt cannot call fail(). Keep its failure visible.
        conn.execute(
            """UPDATE image_queue SET status = 'failed', token = NULL, lease_until = NULL
               WHERE status = 'claimed' AND lease_until <= now() AND attempts >= %s""",
            (MAX_ATTEMPTS,),
        )
        job = conn.execute(
            """SELECT q.message_id, m.chat_id, m.msg_id, m.topic_id, m.image_refs AS refs
               FROM image_queue q JOIN messages m ON m.id = q.message_id
               WHERE m.image_source = %s
                 AND ((q.status = 'pending' AND q.available_at <= now())
                      OR (q.status = 'claimed' AND q.lease_until <= now()))
               ORDER BY q.available_at, q.message_id LIMIT 1 FOR UPDATE OF q SKIP LOCKED""",
            (source,),
        ).fetchone()
        if job is None:
            return None
        job = dict(job)
        job["token"] = uuid4().hex
        conn.execute(
            """UPDATE image_queue SET status = 'claimed', token = %s,
                   lease_until = now() + %s * interval '1 second', attempts = attempts + 1
               WHERE message_id = %s""",
            (job["token"], LEASE_SECONDS, job["message_id"]),
        )
        conn.execute(
            "UPDATE image_queue_lease SET token = %s, lease_until = now() + %s * interval '1 second'",
            (job["token"], LEASE_SECONDS),
        )
        return job


def _release(conn, job: dict) -> None:
    """Only this worker's token may release the singleton, including invalidated/deleted jobs."""
    conn.execute(
        "UPDATE image_queue_lease SET token = NULL, lease_until = NULL WHERE token = %s",
        (job["token"],),
    )


def finish(job: dict, text: str) -> bool:
    """Save OCR only for the current claim. The normal text trigger queues its embedding."""
    text = text.strip()
    with pg.connection() as conn:
        # Same lock order as write_batch and message deletion: message first, then its queue row.
        message = conn.execute(
            "SELECT image_caption FROM messages WHERE id = %s FOR UPDATE", (job["message_id"],),
        ).fetchone()
        if message is None:
            _release(conn, job)
            return False
        claimed = conn.execute(
            """DELETE FROM image_queue WHERE message_id = %s AND token = %s AND status = 'claimed'
               AND lease_until > now()
               RETURNING message_id""",
            (job["message_id"], job["token"]),
        ).fetchone()
        _release(conn, job)
        if claimed is None:
            return False
        caption = message["image_caption"] or ""
        combined = caption
        if text:
            combined += ("\n\n" if caption else "") + "[image text, OCR]\n" + text
        conn.execute(
            "UPDATE messages SET image_text = %s, text = %s WHERE id = %s",
            (text, combined, job["message_id"]),
        )
        return True


def fail(job: dict) -> bool:
    """Retry after bounded backoff, or retain an explicit failed row after three claims."""
    with pg.connection() as conn:
        changed = conn.execute(
            """UPDATE image_queue
               SET status = CASE WHEN attempts >= %s THEN 'failed' ELSE 'pending' END,
                   available_at = now() + least(300, 15 * power(2, attempts - 1)) * interval '1 second',
                   token = NULL, lease_until = NULL
               WHERE message_id = %s AND token = %s AND status = 'claimed' AND lease_until > now()
               RETURNING message_id""",
            (MAX_ATTEMPTS, job["message_id"], job["token"]),
        ).fetchone()
        _release(conn, job)
        return changed is not None


def discard(job: dict) -> bool:
    """Cancel this claim after access removal, without storing recognition output."""
    with pg.connection() as conn:
        deleted = conn.execute(
            """DELETE FROM image_queue WHERE message_id = %s AND token = %s AND status = 'claimed'
               AND lease_until > now() RETURNING message_id""",
            (job["message_id"], job["token"]),
        ).fetchone()
        _release(conn, job)
        return deleted is not None
