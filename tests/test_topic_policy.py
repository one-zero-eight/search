"""Topic policy semantics; database tests use only an explicitly disposable DSN."""

import pytest

from catix import userbot_config as config



@pytest.fixture(autouse=True)
def clean_cache():
    config._forget()
    yield
    config._forget()


def test_policy_of_an_unconfigured_chat_is_search_without_enabling_it(monkeypatch):
    monkeypatch.setattr(config, "_rows", lambda: {})
    assert hasattr(config, "get_policy"), "the configuration wizard needs get_policy"
    assert config.get_policy(-42) == {"default": "search", "topics": {}}
    assert config.listened() == {}


@pytest.mark.parametrize("scope,reader,expected", [
    (None, "auto", {"default": "store", "topics": {}}),
    ([1, 7], "bot", {"default": "search", "topics": {1: "store", 7: "store"}}),
    ([], "userbot", {"default": "search", "topics": {}}),
    ([7], "search", {"default": "search", "topics": {}}),
])
def test_legacy_policy_preserves_storage_and_unrestricted_live_search(monkeypatch, scope, reader, expected):
    monkeypatch.setattr(config, "_rows", lambda: {-42: (scope, reader)})
    assert config.get_policy(-42) == expected


def test_mixed_policy_controls_storage_general_and_live_chat_discovery(monkeypatch):
    rows = {
        -42: (None, "auto", {"default": "search", "topics": {"1": "store", "7": "off"}}),
        -43: (None, "auto", {"default": "store", "topics": {"7": "off", "8": "search"}}),
        -44: (None, "auto", {"default": "off", "topics": {}}),
        -45: ([], "auto"),
    }
    monkeypatch.setattr(config, "_rows", lambda: rows)
    monkeypatch.setattr(config, "userbot_chat_ids", lambda: set(rows))
    assert config.userbot_reads() == {-42: [1], -43: None}
    assert config.listened() == {-42: [1], -43: None, -44: [], -45: []}
    assert config.listened_cached() == config.listened()
    assert config.readers() == {c: "auto" for c in rows}
    assert config.live_chats() == {-42, -43, -45}
    assert config.searchable_chats() == {-42, -43, -45}
    assert config.topic_allowed(-42, None, 1)
    assert not config.topic_allowed(-42, 7, 1)
    assert not config.topic_allowed(-42, 99, 1)
    assert config.topic_allowed(-43, 99, 1)
    assert not config.topic_allowed(-43, 7, 1)
    assert not config.topic_allowed(-43, 8, 1)
    assert not config.topic_allowed(-44, None, 1)
    assert not config.topic_allowed(-45, None, 1)
    assert not config.topic_allowed(-46, None, 1)
    assert config.search_topic_allowed(-42, None)
    assert not config.search_topic_allowed(-42, 7)
    assert config.search_topic_allowed(-42, 99)
    assert not config.search_topic_allowed(-46, 99)


def test_legacy_search_reader_overrides_explicit_storage_without_erasing_off(monkeypatch):
    rows = {-42: (None, "search", {"default": "store", "topics": {"7": "off", "8": "store"}})}
    monkeypatch.setattr(config, "_rows", lambda: rows)
    monkeypatch.setattr(config, "userbot_chat_ids", lambda: {-42})
    assert config.get_policy(-42) == {"default": "search", "topics": {7: "off", 8: "search"}}
    assert config.userbot_reads() == {}
    assert config.live_chats() == {-42}
    assert not config.topic_allowed(-42, 8, 1)
    assert not config.search_topic_allowed(-42, 7)
