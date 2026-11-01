"""What the API remembers between requests, in this process only (the search service kept it in MongoDB).

A restart forgets it: a `chat_id` that is not known any more starts a new conversation (as the search service did for an
id it did not find), and feedback for a forgotten `search_query_id` is answered with 404.
"""

import threading
import uuid
from collections import OrderedDict

MAX_ITEMS = 5000  # the oldest are dropped first


class _Bounded(OrderedDict):
    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        while len(self) > MAX_ITEMS:
            self.popitem(last=False)


_lock = threading.Lock()
# search_query_id -> the feedback of each of its responses ("like", "dislike" or None)
searches: dict[str, list[str | None]] = _Bounded()
# chat_id -> InNoHassle id of the owner; the agent's thread of the chat is `api:<chat_id>`
chats: dict[str, str] = _Bounded()
# chat_id -> the checkpoint of the agent's thread to go on from: a question that was cancelled (or failed) halfway leaves
# its messages in the thread, and a tool call without its result would break the next question; the next one forks from here
resume_from: dict[str, str] = _Bounded()


def new_id() -> str:
    return uuid.uuid4().hex[:24]  # as long as the Mongo ids the clients had before


def remember_search(responses: int) -> str:
    search_id = new_id()
    with _lock:
        searches[search_id] = [None] * responses
    return search_id


def remember_chat(innohassle_id: str) -> str:
    chat_id = new_id()
    with _lock:
        chats[chat_id] = innohassle_id
    return chat_id


def thread_of(chat_id: str) -> str:
    return f"api:{chat_id}"
