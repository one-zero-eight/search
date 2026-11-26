"""The cAtIx admin API (/admin/*): who gets in, and the MAX, Telegram and abuse calls behind it."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from catix import abuse, admins, groups, official, userbot_config
from catix import userbot_config as config
from catix.api.app import app
from catix.db import store
from catix.innohassle import token
from catix.maxuserbot import state
from tests.test_topic_policy_db import db, policy_database  # noqa: F401  (the real-DB fixtures)

ADMIN_ID = "a" * 24
USER_ID = "b" * 24
ADMIN = {"Authorization": "Bearer admin"}
USER = {"Authorization": "Bearer user"}


CHAT = 4 * 10**15 - 101
LEGACY = 2 * 10**15 - 101
OWNER = 71


class MemorySources:
    """Public state boundary, including optimistic configuration and archive semantics.

    No SQL or handlers are mocked. Reads return detached values just like DB rows;
    rejected writes leave the complete domain unchanged.
    """

    def __init__(self):
        now = datetime.now(timezone.utc)
        self.sources = {CHAT: dict(
            chat_id=CHAT, raw_chat_id=-101, title="MAX <course>", kind="chat", link=None,
            group_code="all", requires_verified_group=True, enabled=False, access="ready",
            generation=0, config_version=0, checked_at=now, last_error=None,
            metadata_pending=False, history_status="idle", history_before_ms=None,
            catchup_status="idle", catchup_before_ms=None, catchup_until_ms=None,
            catchup_after_ms=None, legacy_chat_id=None,
            official=False,
        )}
        self.account = dict(account_id=123, connected_at=now, heartbeat_at=now,
                            catalog_status="complete", catalog_error=None,
                            catalog_requested=False, catalog_checked_at=now)
        self.legacy = {}
        self.messages = {CHAT: ["retained userbot message"], LEGACY: ["old archive message"]}
        self.writes = []
        self.refreshes = 0
        self.failure = None
        self.admin_ids = {OWNER, 72}
        self.known_groups = ["all", "B26"]

    def flags(self, chat_ids):
        return {cid: self.sources[cid]["official"] for cid in chat_ids if cid in self.sources}

    def set_official(self, chat_id, value):
        if self.failure:
            raise self.failure
        if chat_id not in self.sources:
            return False
        self.sources[chat_id]["official"] = value
        self.writes.append(("official", chat_id, value))
        return True

    def chat_message_count(self, chat_id):
        return len(self.messages.get(chat_id, []))

    def clear_history(self, chat_id, *, expected_version, expected_generation):
        source = self._source(chat_id, expected_version, expected_generation)
        deleted = len(self.messages.get(chat_id, []))
        self.messages[chat_id] = []
        source["config_version"] += 1
        source["generation"] += 1
        source["history_status"] = "cancelled"
        source["catchup_status"] = "cancelled"
        self.writes.append(("clear", chat_id))
        return deleted

    def list_sources(self):
        return deepcopy(list(self.sources.values()))

    def get_source(self, chat_id):
        return deepcopy(self.sources.get(chat_id))

    def list_legacy(self):
        return deepcopy(list(self.legacy.values()))

    def request_catalog(self):
        self.refreshes += 1
        self.account["catalog_requested"] = True

    def _source(self, chat_id, version, generation):
        source = self.sources.get(chat_id)
        if source is None:
            raise state.SourceNotFound()
        if (source["config_version"], source["generation"]) != (version, generation):
            raise state.ConfigurationConflict()
        if self.failure:
            raise self.failure
        return source

    def _fresh(self, source):
        now = datetime.now(timezone.utc)
        return (source["access"] == "ready" and source["checked_at"] is not None
                and source["checked_at"] >= now - timedelta(minutes=5)
                and self.account["heartbeat_at"] is not None
                and self.account["heartbeat_at"] >= now - timedelta(seconds=60))

    def save_configuration(self, chat_id, group_code, *, enabled, expected_version,
                           expected_generation, legacy_chat_id=None):
        source = self._source(chat_id, expected_version, expected_generation)
        code = groups.normalize(group_code)
        if code is None:
            raise ValueError("invalid_group")
        if enabled and not self._fresh(source):
            self.request_catalog()
            raise state.SourceUnavailable()
        previous_legacy = source["legacy_chat_id"]
        if previous_legacy is not None:
            if legacy_chat_id not in (None, previous_legacy):
                raise state.ConfigurationConflict()
            legacy_chat_id = previous_legacy
        if legacy_chat_id is not None:
            legacy = self.legacy.get(legacy_chat_id)
            if (not legacy or not groups.MAX_CHAT_BASE - 10**13 < legacy_chat_id < groups.MAX_CHAT_BASE + 10**13
                    or legacy.get("linked_chat_id") not in (None, chat_id)):
                raise state.ConfigurationConflict()
        toggled = enabled != source["enabled"]
        changed = toggled or code != source["group_code"] or legacy_chat_id != previous_legacy
        source.update(group_code=code, requires_verified_group=code != "all", enabled=enabled,
                      legacy_chat_id=legacy_chat_id,
                      config_version=source["config_version"] + int(changed),
                      generation=source["generation"] + int(toggled))
        if enabled and legacy_chat_id is not None:
            self.legacy[legacy_chat_id].update(max_legacy_archived=True, linked_chat_id=chat_id)
        if toggled and enabled:
            source.update(history_status="pending", catchup_status="idle")
        elif toggled and source["history_status"] in {"pending", "running"}:
            source["history_status"] = "cancelled"
        self.writes.append(("save", chat_id, code, enabled, legacy_chat_id))

    def request_history(self, chat_id, *, expected_version, expected_generation):
        source = self._source(chat_id, expected_version, expected_generation)
        if not source["enabled"] or not self._fresh(source):
            self.request_catalog()
            raise state.SourceUnavailable()
        source["history_status"] = "pending"
        if source["catchup_status"] in {"partial", "failed"}:
            source["catchup_status"] = "pending"
        source["config_version"] += 1
        self.writes.append(("history", chat_id))

    def add_legacy(self, chat_id=LEGACY, title="Old MAX course", **overrides):
        row = dict(chat_id=chat_id, title=title, group_code="B25", message_count=37,
                   max_legacy_archived=False, linked_chat_id=None)
        row.update(overrides)
        self.legacy[chat_id] = row
        return row

@pytest.fixture
def seen_calls():
    return []


@pytest.fixture
def client(monkeypatch, seen_calls):
    claims = {
        "admin": {"uid": ADMIN_ID, "email": "a@innopolis.university", "telegram_id": 5},
        "user": {"uid": USER_ID, "email": "b@innopolis.university"},
    }
    monkeypatch.setattr(token, "claims", lambda t: claims.get(t))
    monkeypatch.setattr(admins, "is_admin", lambda i: i == ADMIN_ID)
    monkeypatch.setattr(admins, "seen", lambda *args: seen_calls.append(args))
    return TestClient(app)


@pytest.fixture
def domain(monkeypatch):
    domain = MemorySources()
    domain.add_legacy()
    for name in ("list_sources", "get_source", "list_legacy", "save_configuration", "request_history", "request_catalog", "clear_history"):
        monkeypatch.setattr(state, name, getattr(domain, name))
    monkeypatch.setattr(state, "get_account", lambda: deepcopy(domain.account))
    monkeypatch.setattr(official, "flags", domain.flags)
    monkeypatch.setattr(official, "set_official", domain.set_official)
    monkeypatch.setattr(store, "chat_message_count", domain.chat_message_count)
    return domain


def body(domain, **overrides):
    source = domain.sources[CHAT]
    data = {"group_code": "B26", "enabled": True, "legacy_chat_id": None,
            "config_version": source["config_version"], "generation": source["generation"]}
    return {**data, **overrides}


def test_a_non_admin_is_refused_and_an_admin_is_remembered(client, seen_calls, monkeypatch):
    monkeypatch.setattr(userbot_config, "dialogs", lambda: [])
    monkeypatch.setattr(state, "list_sources", lambda: [])
    monkeypatch.setattr(state, "get_account", lambda: None)
    response = client.get("/admin/chats", headers=USER)
    assert response.status_code == 403 and response.json()["detail"] == "Only for cAtIx admins"
    assert seen_calls == []
    assert client.get("/admin/chats", headers=ADMIN).status_code == 200
    assert seen_calls == [(ADMIN_ID, "a@innopolis.university", 5)]


def test_me_tells_a_non_admin_their_id(client):
    response = client.get("/admin/me", headers=USER)
    assert response.json() == {"innohassle_id": USER_ID, "is_admin": False}


def test_a_stale_max_save_is_a_conflict_and_writes_nothing(client, domain):
    response = client.put(f"/admin/max/{CHAT}", json=body(domain, config_version=99), headers=ADMIN)
    assert (response.status_code, response.json()["detail"]) == (409, "changed")
    assert domain.writes == []


def test_a_valid_max_save_enables_the_source(client, domain):
    response = client.put(f"/admin/max/{CHAT}", json=body(domain), headers=ADMIN)
    assert response.status_code == 200, response.text
    assert response.json()["enabled"] is True and response.json()["group_code"] == "B26"


def test_an_unconfirmed_access_asks_for_a_catalog_refresh(client, domain):
    domain.sources[CHAT]["checked_at"] = datetime.now(timezone.utc) - timedelta(hours=1)
    response = client.put(f"/admin/max/{CHAT}", json=body(domain), headers=ADMIN)
    assert (response.status_code, response.json()["detail"]) == (409, "source_unavailable")
    assert domain.refreshes >= 1  # (the fake asks itself too; the real save_configuration does as well)


def test_a_forged_legacy_source_is_refused_before_saving(client, domain):
    response = client.put(f"/admin/max/{CHAT}", json=body(domain, legacy_chat_id=str(LEGACY + 5)), headers=ADMIN)
    assert (response.status_code, response.json()["detail"]) == (409, "changed")
    assert domain.writes == []
    ok = client.put(f"/admin/max/{CHAT}", json=body(domain, legacy_chat_id=str(LEGACY)), headers=ADMIN)
    assert ok.status_code == 200 and ok.json()["legacy_chat_id"] == str(LEGACY)


def test_forgiving_nobody_is_not_found(client, monkeypatch):
    monkeypatch.setattr(abuse, "forgive", lambda key: False)
    assert client.delete("/admin/abuse/ih:x", headers=ADMIN).status_code == 404


def test_an_admin_cannot_remove_themselves_or_a_fixed_admin(client, monkeypatch):
    monkeypatch.setattr(admins, "configured", lambda: ["c" * 24])
    assert client.delete(f"/admin/admins/{ADMIN_ID}", headers=ADMIN).json()["detail"] == "cannot_remove_self"
    assert client.delete(f"/admin/admins/{'c' * 24}", headers=ADMIN).json()["detail"] == "fixed_admin"
    assert client.post("/admin/admins", json={"innohassle_id": "xyz"}, headers=ADMIN).status_code == 422


def test_put_telegram_chat_saves_policy(client, db):  # noqa: F811
    response = client.put(
        "/admin/telegram/chats/-82001", headers=ADMIN,
        json={"group_code": "b26-cse-01", "default_mode": "search", "topic_modes": {"7": "store", "8": "off"}, "reader": "auto"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["group_code"] == "B26-CSE-01"
    assert config.get_policy(-82001) == {"default": "search", "topics": {7: "store", 8: "off"}}
    assert config.userbot_reads()[-82001] == [7]


def test_admins_roundtrip_in_the_database(db, monkeypatch):  # noqa: F811
    first, second = "d" * 24, "e" * 24
    monkeypatch.setattr(admins.settings, "admin_innohassle_ids", [first])
    monkeypatch.setattr(admins.settings, "admin_telegram_ids", [])
    with admins.pg.connection() as conn:
        conn.execute("DELETE FROM admins WHERE innohassle_id IN (%s, %s)", (first, second))
    admins.seen(first, "d@innopolis.university", 11)  # a fixed admin: only contacts are kept
    assert admins.is_admin(first) and not admins.is_admin(second)
    assert admins.add(second, first) and not admins.add(second, first) and not admins.add(first, second)
    admins.seen(second, "e@innopolis.university", 22)
    assert [(a.innohassle_id, a.fixed, a.telegram_id) for a in admins.listing()] == [(first, True, 11), (second, False, 22)]
    assert admins.telegram_ids() == [11, 22]
    assert admins.remove(second) and not admins.remove(first)
    assert admins.telegram_ids() == [11]
    with admins.pg.connection() as conn:
        conn.execute("DELETE FROM admins WHERE innohassle_id IN (%s, %s)", (first, second))


def test_the_chat_list_joins_telegram_and_max(client, domain, monkeypatch):
    dialog = userbot_config.Dialog(-5, "TG chat", "group", None, False)
    monkeypatch.setattr(userbot_config, "dialogs", lambda: [dialog])
    monkeypatch.setattr(userbot_config, "listened", lambda: {-5: None})
    monkeypatch.setattr(userbot_config, "readers", lambda: {-5: "search"})
    monkeypatch.setattr("catix.api.admin._groups_of", lambda ids: {-5: "B26"})
    body = client.get("/admin/chats", headers=ADMIN).json()
    assert [(c["platform"], c["chat_id"], c["connected"], c["group_code"]) for c in body["chats"]] == [
        ("telegram", "-5", True, "B26"), ("max", str(CHAT), False, "all")]
    assert body["chats"][0]["search_only"] is True and body["max_account"]["online"] is True
