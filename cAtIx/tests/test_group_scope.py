"""Study groups in the search (groups.py, store.py, tools.py), without a model.

The group of the asker is taken from the context by code: `scoped_chat_ids` decides which chats a search may use, and the model
never passes it. What the model does see is the `group` of every chat it reads (`all`, or a study group code), so that it can say
whom a fact is for.
"""

import json
from types import SimpleNamespace

import pytest

from catix import groups
from catix.agent import sqlquery
from catix.db import pg, store
from tests.conftest import CHAT_ID

OTHER = "B26-ZZ-99"
KEYS = ["tg:999000001", "tg:999000002"]


@pytest.fixture
def grouped_chat(chat):
    """The synthetic chat belongs to a study group for the duration of the test."""
    groups.set_chat_group(chat, OTHER)
    yield chat
    groups.set_chat_group(chat, groups.ALL)
    with pg.connection() as conn:
        conn.execute("DELETE FROM user_groups WHERE user_key = ANY(%s)", (KEYS,))


def test_a_search_result_says_the_group_of_its_chat(grouped_chat):
    hits = store.search(["орнитологии"], chat_ids={grouped_chat}, limit=5)
    assert hits and {h.chat_group for h in hits} == {OTHER}
    groups.set_chat_group(grouped_chat, groups.ALL)
    assert {h.chat_group for h in store.search(["орнитологии"], chat_ids={grouped_chat}, limit=5)} == {groups.ALL}


def test_the_chats_of_other_groups_are_cut_by_code(grouped_chat):
    groups.set_user_group(KEYS[0], "B26-AA-01")
    groups.set_user_group(KEYS[1], OTHER)
    assert grouped_chat not in (groups.scoped_chat_ids(KEYS[0]) or set()), "a user of another group must not search this chat"
    assert grouped_chat in groups.scoped_chat_ids(KEYS[1])
    everything = groups.scoped_chat_ids("tg:999000003")  # no group: `all`, every chat
    assert everything is None


def test_the_search_tool_never_leaves_the_allowed_chats(grouped_chat):
    """What the agent's tool does with the context: only the allowed chats are searched, whatever the model asks for."""
    from catix.agent.tools import AgentContext, search_chats

    context = AgentContext(allowed_chat_ids=frozenset({grouped_chat + 1}))  # a chat that is not the synthetic one
    runtime = SimpleNamespace(context=context, state={"messages": []}, config={"configurable": {"thread_id": "t"}}, tool_call_id="c")
    out = search_chats.func(queries=["орнитология"], runtime=runtime, chat="synthetic")  # the model even names the chat
    payload = json.loads(out.update["messages"][0].content)
    assert payload["messages"] == []


def test_query_db_shows_the_group_and_only_the_allowed_chats(grouped_chat):
    seen = sqlquery.run(f"SELECT chat_id, chat_group FROM visible.chats WHERE chat_id = {CHAT_ID} LIMIT 5", {grouped_chat})
    assert seen["rows"] == [[CHAT_ID, OTHER]] or seen["rows"] == [{"chat_id": CHAT_ID, "chat_group": OTHER}], seen
    hidden = sqlquery.run("SELECT count(*) AS n FROM visible.messages", {grouped_chat + 1})
    assert "0" in json.dumps(hidden["rows"]), hidden
