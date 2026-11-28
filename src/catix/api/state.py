"""What the API remembers between requests in this process only: the likes of the search cards (the search service kept
them in MongoDB). A restart forgets them, and feedback for a forgotten `search_query_id` is answered with 404.

The chats of the assistant are kept in Postgres (api/chats.py).
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


def new_id() -> str:
    return uuid.uuid4().hex[:24]  # as long as the Mongo ids the clients had before


def remember_search(responses: int) -> str:
    search_id = new_id()
    with _lock:
        searches[search_id] = [None] * responses
    return search_id
