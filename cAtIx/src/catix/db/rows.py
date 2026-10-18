"""The shape of every row the application reads from Postgres.

A query that returns one of these is run through `pg.rows` / `pg.row`, which builds the dataclass from the columns
by name: a column that is missing or extra fails at once, in the query that is wrong, instead of as a KeyError in
whatever reads the row later. Keep each SELECT list in step with its class.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

ChangeKind = Literal["reschedule", "room_change", "cancel", "announcement"]
ChangeStatus = Literal["pending", "approved", "rejected"]


@dataclass(frozen=True, slots=True)
class ChatRow:
    chat_id: int
    title: str
    username: str | None
    bot_member: bool


@dataclass(frozen=True, slots=True)
class ChatGroup:
    chat_id: int
    title: str
    group_code: str


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
    parent_sender: str | None
    parent_text: str | None


@dataclass(frozen=True, slots=True)
class SourceRow:
    """What the source list of an answer needs to know about a message."""

    id: int
    date: datetime
    sender_name: str | None
    sender_link: str | None
    link: str | None
    chat_link: str | None
    chat_title: str


@dataclass(frozen=True, slots=True)
class QueuedMessage:
    id: int
    chat_id: int
    text: str


@dataclass(frozen=True, slots=True)
class MessageToRead:
    """A stored message the changes worker looks at."""

    id: int
    date: datetime
    text: str
    chat_title: str
    parent_text: str | None
    known: bool  # It was already turned into a schedule change.


@dataclass(frozen=True, slots=True)
class ChangeView:
    """A schedule change with the message and chat it came from."""

    id: int
    message_id: int
    kind: ChangeKind
    subject: str | None
    starts_at: datetime
    ends_at: datetime | None
    all_day: bool
    room: str | None
    summary: str
    status: ChangeStatus
    created_at: datetime
    notified_at: datetime | None
    decided_at: datetime | None
    text: str
    date: datetime
    link: str | None
    sender_name: str | None
    chat_title: str
    chat_link: str | None
    group_code: str


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
