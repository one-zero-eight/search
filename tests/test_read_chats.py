"""read_chats (store.latest): the newest messages of the chats with filters, and the list of chats in the chats helper's prompt.

It replaced query_db, the model's own SQL: of 52 calls in the traces all 52 were `text ILIKE '%…%'` searches, none a count,
and a substring matched any word with those letters ('%дм%'). Needs the database, not the model.
"""

from datetime import date, timedelta

from catix.db import pg, store


def _count(chat: int) -> int:
    with pg.connection() as conn:
        return pg.scalar(conn, "SELECT count(*) FROM messages WHERE chat_id = %s", (chat,))


def test_the_newest_come_first_with_how_many_there_are(chat):
    total, rows = store.latest(chat_ids={chat}, limit=3)
    assert total == _count(chat) > 3
    assert len(rows) == 3 and [r.date for r in rows] == sorted((r.date for r in rows), reverse=True)


def test_words_match_in_any_form_and_never_as_a_part_of_a_word(chat):
    total, rows = store.latest(chat_ids={chat}, words=["смены"])  # the messages say "Смена белья"
    assert total == 2 and all("Смена" in r.text for r in rows)
    assert store.latest(chat_ids={chat}, words=["мена"])[0] == 0


def test_the_dates_are_the_days_the_messages_were_written(chat):
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    total, rows = store.latest(chat_ids={chat}, words=["смена"], date_from=week_ago)
    assert total == 1 and "сегодня" in rows[0].text  # the one of 40 days ago is left out


def test_a_chat_is_chosen_by_its_title_and_only_among_the_allowed_ones(chat):
    assert store.latest(chat="synthetic", chat_ids={chat})[0] == _count(chat)
    assert store.latest(chat="synthetic", chat_ids={chat + 1}) is None  # not one the asker may see
    assert store.latest(chat="нет такого чата", chat_ids={chat}) is None
    assert store.latest(chat_ids={chat + 1})[0] == 0


def test_a_person_is_chosen_by_a_part_of_the_name(chat):
    """A real question: 'что писал пользователь Новиков Иван за последнюю неделю в чатах' (query_db took sender_name)."""
    assert store.latest(chat_ids={chat}, sender="анн")[0] == _count(chat)  # every message is of Анна
    assert store.latest(chat_ids={chat}, sender="Новиков")[0] == 0


def test_official_only_leaves_out_the_students_chats(chat):
    assert store.latest(chat_ids={chat}, official_only=True)[0] == 0


def test_the_list_of_chats_shows_only_the_allowed_ones(chat):
    assert [(c["title"], c["stored"]) for c in store.visible_chats({chat})] == [("tests: synthetic chat", True)]
    assert store.visible_chats({chat + 1}) == []
