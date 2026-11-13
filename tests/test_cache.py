"""The shared cache in Redis (common/cache.py), with Redis faked (conftest.shared_cache): a value is read once for every
process and comes back as JSON gives it; a failed read and a TTL of 0 keep nothing; without Redis every call reads again
and nothing fails. And the caches built on it: InNoHassle, the group of a Telegram id, the choice of /listen."""

import time
from datetime import date

import httpx
import pytest
import redis
from pydantic import SecretStr

from catix import groups, userbot_config
from catix.common import cache
from catix.innohassle import client as innohassle
from catix.settings import settings

REAL_REDIS = cache._redis  # (conftest puts the fake in its place for every test)


def _counting(value):
    calls = []

    def load():
        calls.append(1)
        return value

    return load, calls


def test_a_value_is_read_once_and_comes_back_as_json_gives_it(shared_cache):
    load, calls = _counting({7: ("a", None)})
    first, again = cache.cached("k", 60, load), cache.cached("k", 60, load)
    assert first == again == {"7": ["a", None]} and len(calls) == 1, "the same on a miss and on a hit"
    assert shared_cache.ttl[cache.PREFIX + "k"] == 60
    first["7"].append("changed")
    assert cache.cached("k", 60, load) == {"7": ["a", None]}, "a caller changes its own copy"


def test_none_is_a_value_and_a_failed_read_is_not_kept():
    load, calls = _counting(None)
    assert cache.cached("none", 60, load) is None and cache.cached("none", 60, load) is None and len(calls) == 1

    def down():
        raise httpx.ConnectError("down")

    with pytest.raises(httpx.ConnectError):
        cache.cached("failed", 60, down)
    assert cache.get("failed") == (False, None)


def test_a_ttl_of_zero_keeps_nothing_and_drop_forgets():
    load, calls = _counting([1])
    cache.cached("zero", 0, load), cache.cached("zero", 0, load)
    assert len(calls) == 2
    cache.put("kept", 1, 60)
    cache.drop("kept")
    assert cache.get("kept") == (False, None)


def test_without_redis_every_call_reads_again_and_nothing_fails(monkeypatch):
    monkeypatch.setattr(cache, "_redis", REAL_REDIS)
    monkeypatch.setattr(cache, "_client", None)
    monkeypatch.setattr(cache, "_down_until", 0.0)
    monkeypatch.setattr(settings, "redis_url", None)
    load, calls = _counting("x")
    assert cache.cached("k", 60, load) == cache.cached("k", 60, load) == "x" and len(calls) == 2

    monkeypatch.setattr(settings, "redis_url", "redis://127.0.0.1:1/0")  # nobody listens there
    assert cache.cached("k", 60, load) == "x" and cache._down_until > time.monotonic()

    class Untouchable:
        def __getattr__(self, name):
            raise AssertionError("Redis was asked again right after it failed")

    monkeypatch.setattr(cache, "_client", Untouchable())
    assert cache.cached("k", 60, load) == "x" and len(calls) == 4
    cache.drop("k")


def test_a_redis_error_is_not_the_callers(monkeypatch):
    class Broken:
        def get(self, *args, **kwargs):
            raise redis.ConnectionError("gone")

        set = delete = get

    monkeypatch.setattr(cache, "_redis", lambda: Broken())
    monkeypatch.setattr(cache, "_down_until", 0.0)
    assert cache.cached("k", 60, lambda: 5) == 5
    cache.drop("k")


def test_inno_hassle_is_asked_once_for_every_process(monkeypatch, shared_cache):
    asked: list[str] = []

    def answer(request: httpx.Request) -> httpx.Response:
        asked.append(str(request.url))
        return httpx.Response(200, json=[{"id": 1}])

    monkeypatch.setattr(innohassle, "_client", httpx.Client(base_url=str(settings.innohassle_api), transport=httpx.MockTransport(answer)))
    assert innohassle.clubs() == innohassle.clubs() == [{"id": 1}] and len(asked) == 1
    innohassle.music_room_bookings(date(2026, 11, 6))
    assert shared_cache.ttl[cache.PREFIX + "innohassle:" + asked[-1]] == innohassle.BOOKINGS_TTL
    monkeypatch.setattr(settings, "innohassle_cache_ttl", 0)
    innohassle.scenes(), innohassle.scenes()
    assert len(asked) == 4, "a TTL of 0 is no cache"


def test_the_group_of_a_telegram_id_is_kept_longer_than_a_miss(monkeypatch, shared_cache):
    monkeypatch.setattr(settings, "innohassle_groups", True)
    monkeypatch.setattr(settings, "innohassle_service_token", SecretStr("service"))
    known = {1: "b26-cse-01", 2: None}
    asked: list[int] = []

    def lookup(telegram_id):
        asked.append(telegram_id)
        return known[telegram_id]

    monkeypatch.setattr(innohassle, "study_group_by_telegram_id", lookup)
    assert groups.auto_group(1) == groups.auto_group(1) == "B26-CSE-01"
    assert groups.auto_group(2) is None and groups.auto_group(2) is None
    assert asked == [1, 2], "a miss is kept too"
    assert shared_cache.ttl[cache.PREFIX + "group:tg:1"] == groups.AUTO_TTL
    assert shared_cache.ttl[cache.PREFIX + "group:tg:2"] == groups.AUTO_MISS_TTL


def test_a_change_of_listen_is_seen_at_once(monkeypatch):
    rows = {-100: ([5], "auto")}
    monkeypatch.setattr(userbot_config, "_rows", lambda: dict(rows))
    assert userbot_config.listened_cached() == {-100: [5]}, "the chat ids are numbers again"
    assert userbot_config.topic_allowed(-100, 5, 1) and not userbot_config.topic_allowed(-100, 6, 1)
    rows[-100] = (None, "auto")
    assert userbot_config.listened_cached() == {-100: [5]}, "kept for CACHE_TTL"
    userbot_config._forget()  # what set_listen, toggle_topic, ... do after their change
    assert userbot_config.topic_allowed(-100, 6, 1)
