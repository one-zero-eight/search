"""The shape of every row the application reads from Postgres.

A query that returns one of these is run through `pg.rows` / `pg.row`, which builds the dataclass from the columns
by name: a column that is missing or extra fails at once, in the query that is wrong, instead of as a KeyError in
whatever reads the row later. Keep each SELECT list in step with its class.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ChatRow:
    chat_id: int
    title: str
    username: str | None
    bot_member: bool




@dataclass(frozen=True, slots=True)
class MessageHit:
    """A search result: the message, its chat and the message it replies to."""

    ref_id: int
    chat_id: int
    msg_id: int
    date: datetime
    edit_date: datetime | None
    sender_name: str | None
    reply_to: int | None
    text: str
    link: str | None
    chat_title: str
    chat_official: bool
    chat_group: str  # `all` or a study group code: whom the chat is for
    parent_sender: str | None
    parent_text: str | None
    relevance: float | None = None  # (not a column) its second best score of the reranker over the queries, from store._rerank


@dataclass(frozen=True, slots=True)
class SourceRow:
    """What the source list of an answer needs to know about a message."""

    id: int
    date: datetime
    sender_name: str | None
    sender_link: str | None
    link: str | None
    text: str
    chat_official: bool
    chat_link: str | None
    chat_title: str


@dataclass(frozen=True, slots=True)
class QueuedMessage:
    id: int
    chat_id: int
    text: str


@dataclass(frozen=True, slots=True)
class ChatStatus:
    """One line of `catix-db status`."""

    title: str
    chat_id: int
    messages: int
    with_vector: int
    queued: int
    neither: int
    newest: str | None


@dataclass(frozen=True, slots=True)
class AbuseUser:
    """A user with stopped messages in the window, or paused."""

    user_key: str
    strikes: int
    pauses: int
    paused_until: datetime | None


@dataclass(frozen=True, slots=True)
class AbuseEntry:
    category: str
    at: datetime
    preview: str
