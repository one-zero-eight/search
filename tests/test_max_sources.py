"""MAX administration through real Dispatcher updates and a captured Telegram transport."""

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest
from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.enums import ChatType, MessageEntityType
from aiogram.methods import AnswerCallbackQuery, EditMessageText, SendMessage
from aiogram.types import CallbackQuery, Chat, Message, MessageEntity, Update, User

from catix import admins, groups, userbot_config
from catix.db import pg
from catix.maxuserbot import state
from catix.tgbot import admin, bot as general, listen, max_sources


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


class CapturedTelegram(BaseSession):
    def __init__(self):
        super().__init__()
        self.methods = []
        self.screens = []
        self.notices = []

    async def close(self):
        pass

    async def stream_content(self, *args, **kwargs):
        raise AssertionError("UI must not download media")
        yield b""  # async-generator protocol required by BaseSession

    async def make_request(self, bot, method, timeout=None):
        self.methods.append(method)
        if isinstance(method, AnswerCallbackQuery):
            self.notices.append(method.text or "")
            return True
        if isinstance(method, (SendMessage, EditMessageText)):
            self.screens.append(method)
            return Message(message_id=900, date=datetime.now(timezone.utc),
                           chat=Chat(id=int(method.chat_id), type=ChatType.PRIVATE), text=method.text)
        # /admin removes a legacy private command menu; no profile or network reads are allowed.
        if method.__api_method__ == "deleteMyCommands":
            return True
        raise AssertionError(f"Unexpected Telegram request: {method.__api_method__}")


class UI:
    def __init__(self):
        self.transport = CapturedTelegram()
        self.bot = Bot("123456:TEST_TOKEN", session=self.transport)
        self.dispatcher = Dispatcher()
        for router in (max_sources.router, admin.router, listen.router, general.router):
            self.dispatcher.include_router(deepcopy(router))
        self.sequence = 0

    @property
    def screen(self):
        return self.transport.screens[-1]

    @property
    def text(self):
        return self.screen.text

    @property
    def notices(self):
        return self.transport.notices

    @property
    def buttons(self):
        markup = self.screen.reply_markup
        return [button for row in markup.inline_keyboard for button in row] if markup else []

    def data(self, label):
        found = [button.callback_data for button in self.buttons if label in button.text]
        assert len(found) == 1, (label, [(b.text, b.callback_data) for b in self.buttons])
        return found[0]

    def action(self, action, value=None):
        suffix = ":" + action + (":" + str(value) if value is not None else "")
        found = [b.callback_data for b in self.buttons
                 if b.callback_data and b.callback_data.rstrip(":").endswith(suffix)]
        assert len(found) == 1, (suffix, [(b.text, b.callback_data) for b in self.buttons])
        return found[0]

    def _message(self, *, user_id=OWNER, chat_id=OWNER, kind=ChatType.PRIVATE, text=None):
        entities = []
        if text and text.startswith("/"):
            entities = [MessageEntity(type=MessageEntityType.BOT_COMMAND, offset=0,
                                      length=len(text.split()[0]))]
        return Message(message_id=900, date=datetime.now(timezone.utc),
                       chat=Chat(id=chat_id, type=kind),
                       from_user=User(id=user_id, is_bot=False, first_name="Admin"),
                       text=text, entities=entities)

    def press(self, payload, *, user_id=OWNER, chat_id=OWNER, kind=ChatType.PRIVATE):
        self.sequence += 1
        message = self._message(user_id=user_id, chat_id=chat_id, kind=kind, text="screen")
        query = CallbackQuery(id=str(self.sequence), from_user=message.from_user,
                              chat_instance="private-test", message=message, data=payload)
        asyncio.run(self.dispatcher.feed_update(self.bot, Update(update_id=self.sequence, callback_query=query)))

    def click(self, label):
        self.press(self.data(label))

    def send(self, text, **scope):
        self.sequence += 1
        asyncio.run(self.dispatcher.feed_update(self.bot, Update(
            update_id=self.sequence, message=self._message(text=text, **scope))))

    def edit(self):
        self.press(f"mx:edit:{CHAT}")

    def review(self, *, code=None, legacy=None):
        self.edit()
        self.press(self.action("group" if code else "all"))
        if code:
            self.send(code)
        if any(":legacy:" in (b.callback_data or "") for b in self.buttons):
            self.press(self.action("legacy", legacy if legacy is not None else "none"))
        return self.action("save")


@pytest.fixture
def env(monkeypatch):
    domain = MemorySources()
    for module in (max_sources, listen):
        for name in ("SESSIONS", "PAGE", "PENDING_GROUP"):
            if hasattr(module, name):
                getattr(module, name).clear()
    admin.PENDING.clear()
    monkeypatch.setattr(admins, "everyone", lambda: set(domain.admin_ids))
    for name in ("list_sources", "get_source", "list_legacy", "save_configuration",
                 "request_history", "request_catalog"):
        monkeypatch.setattr(state, name, getattr(domain, name))
    monkeypatch.setattr(state, "get_account", lambda: deepcopy(domain.account))
    monkeypatch.setattr(state, "allowed", lambda cid: bool(
        cid in domain.sources and domain.sources[cid]["enabled"] and domain.sources[cid]["access"] == "ready"))
    # Telegram navigation stays real, but its unrelated read boundary is empty and hermetic.
    monkeypatch.setattr(userbot_config, "dialogs", lambda: [])
    monkeypatch.setattr(userbot_config, "listened", lambda: {})
    monkeypatch.setattr(userbot_config, "readers", lambda: {})
    monkeypatch.setattr(listen, "_groups_of", lambda ids: {})
    monkeypatch.setattr(listen, "_known_groups", lambda: ["all", "B26"])
    monkeypatch.setattr(listen.official, "flags", lambda ids: {})
    def no_database(*args, **kwargs):
        raise AssertionError("UI handlers must use the patched public state boundary")
    monkeypatch.setattr(pg, "connection", no_database)
    ui = UI()
    yield domain, ui
    max_sources.SESSIONS.clear()
    listen.SESSIONS.clear()
    admin.PENDING.clear()


def assert_not_saved(ui):
    assert not any("Сохранено" in text for text in ui.notices)


def test_list_card_and_pagination_capture_actual_telegram_screens(env):
    domain, ui = env
    for offset in range(1, 10):
        domain.sources[CHAT + offset] = dict(domain.sources[CHAT], chat_id=CHAT + offset,
                                           raw_chat_id=-101 + offset, title=f"Course {offset}")
    ui.press("mx:list:0")
    chat_buttons = [b for b in ui.buttons if (b.callback_data or "").startswith("mx:chat:")]
    assert len(chat_buttons) == 8
    assert "online" in ui.text.lower() or "онлайн" in ui.text.lower()
    assert ui.data("Группы и источники") == "ls:l:keep"
    ui.press("mx:list:1")
    assert len([b for b in ui.buttons if (b.callback_data or "").startswith("mx:chat:")]) == 2
    ui.press(f"mx:chat:{CHAT}")
    assert "MAX &lt;course&gt;" in ui.text
    assert str(CHAT) in ui.text and "-101" in ui.text
    assert ui.data("Настроить") == f"mx:edit:{CHAT}"
    assert domain.writes == []


def test_review_is_read_only_and_save_is_nonce_bound_exactly_once(env):
    domain, ui = env
    before = deepcopy(domain.sources)
    save = ui.review(code=" b26-cse-01 ")
    assert "B26-CSE-01" in ui.text
    assert "истори" in ui.text.lower() and "новые" in ui.text.lower()
    assert domain.sources == before and domain.writes == []
    ui.press(save)
    source = domain.sources[CHAT]
    assert source["enabled"] and source["group_code"] == "B26-CSE-01"
    assert source["history_status"] == "pending"
    assert OWNER not in max_sources.SESSIONS
    assert any("Сохранено" in text for text in ui.notices)
    ui.press(save)
    assert len(domain.writes) == 1


@pytest.mark.parametrize("scope", [dict(user_id=999), dict(kind=ChatType.GROUP, chat_id=-7)])
@pytest.mark.parametrize("payload", ["mx:list:0", f"mx:edit:{CHAT}", "mx:refresh", f"mx:off:{CHAT}"])
def test_every_navigation_requires_current_admin_and_private_chat(env, scope, payload):
    domain, ui = env
    ui.press(payload, **scope)
    assert domain.writes == [] and domain.refreshes == 0
    assert not max_sources.SESSIONS
    assert ui.notices


@pytest.mark.parametrize("attack", ["foreign_owner", "other_private_chat", "nonce", "version", "generation", "revoked"])
def test_foreign_stale_or_revoked_confirmation_cannot_write(env, attack):
    domain, ui = env
    save = ui.review()
    scope = {}
    if attack == "foreign_owner":
        scope = dict(user_id=72, chat_id=72)
    elif attack == "other_private_chat":
        scope = dict(chat_id=999)
    elif attack == "nonce":
        save = save.replace(save.split(":")[2], "deadbeef")
    elif attack in {"version", "generation"}:
        domain.sources[CHAT]["config_version" if attack == "version" else "generation"] += 1
    else:
        domain.admin_ids.remove(OWNER)
    ui.press(save, **scope)
    assert not domain.sources[CHAT]["enabled"]
    assert domain.writes == []
    assert_not_saved(ui)


@pytest.mark.parametrize("scope", [dict(user_id=72, chat_id=72), dict(chat_id=999)])
def test_group_input_is_bound_to_private_chat_and_owner(env, scope):
    domain, ui = env
    ui.edit()
    ui.press(ui.action("group"))
    ui.send("B27", **scope)
    assert max_sources.SESSIONS[OWNER].group_code is None
    assert domain.writes == []


def test_invalid_group_stays_in_wizard_and_valid_retry_normalizes(env):
    domain, ui = env
    ui.edit()
    ui.press(ui.action("group"))
    ui.send("not a group / invalid")
    assert OWNER in max_sources.SESSIONS and domain.writes == []
    assert max_sources.SESSIONS[OWNER].group_code is None
    ui.send(" b26.cse-01 ")
    assert "B26.CSE-01" in ui.text
    ui.press(ui.action("save"))
    assert domain.sources[CHAT]["group_code"] == "B26.CSE-01"


def test_group_text_rechecks_dynamic_admin_membership(env):
    domain, ui = env
    ui.edit()
    ui.press(ui.action("group"))
    domain.admin_ids.remove(OWNER)
    ui.send("B27")
    assert domain.writes == []
    assert OWNER not in max_sources.SESSIONS


@pytest.mark.parametrize("failure", [RuntimeError("database offline"), state.ConfigurationConflict()])
def test_database_failure_preserves_expected_version_and_draft_without_success(env, failure):
    domain, ui = env
    save = ui.review()
    session = max_sources.SESSIONS[OWNER]
    expected = (session.config_version, session.generation)
    domain.failure = failure
    ui.press(save)
    assert domain.writes == [] and not domain.sources[CHAT]["enabled"]
    assert OWNER in max_sources.SESSIONS
    assert (session.config_version, session.generation) == expected
    assert_not_saved(ui)
    domain.failure = None
    ui.press(ui.action("save"))
    assert domain.sources[CHAT]["enabled"] and len(domain.writes) == 1


@pytest.mark.parametrize("lost", ["access", "offline", "old_metadata"])
def test_lost_or_stale_access_requests_refresh_without_false_success(env, lost):
    domain, ui = env
    save = ui.review()
    source = domain.sources[CHAT]
    if lost == "access":
        source["access"] = "no_permission"
    elif lost == "offline":
        domain.account["heartbeat_at"] = None
    else:
        source["checked_at"] -= timedelta(minutes=6)
    ui.press(save)
    assert domain.writes == [] and not source["enabled"]
    assert OWNER in max_sources.SESSIONS
    assert domain.refreshes > 0
    assert_not_saved(ui)


def test_explicit_legacy_selection_only_archives_after_review_save(env):
    domain, ui = env
    legacy = domain.add_legacy()
    ui.edit()
    ui.press(ui.action("all"))
    assert legacy["title"] in ui.text or any(legacy["title"] in b.text for b in ui.buttons)
    assert domain.sources[CHAT]["legacy_chat_id"] is None
    assert not legacy["max_legacy_archived"]
    ui.press(ui.action("legacy", LEGACY))
    assert str(LEGACY) in ui.text and str(CHAT) in ui.text and "-101" in ui.text
    assert "37" in ui.text and "архив" in ui.text.lower()
    assert domain.writes == [] and not legacy["max_legacy_archived"]
    ui.press(ui.action("save"))
    assert legacy["max_legacy_archived"] and legacy["linked_chat_id"] == CHAT
    assert domain.sources[CHAT]["legacy_chat_id"] == LEGACY
    assert domain.messages[LEGACY] == ["old archive message"]


def test_no_legacy_choice_does_not_implicitly_match_same_raw_id(env):
    domain, ui = env
    legacy = domain.add_legacy()
    ui.press(ui.review())
    assert domain.sources[CHAT]["legacy_chat_id"] is None
    assert not legacy["max_legacy_archived"]


@pytest.mark.parametrize("forged", [LEGACY + 1, 71])
def test_forged_legacy_id_cannot_be_selected_or_saved(env, forged):
    domain, ui = env
    domain.add_legacy()
    ui.edit()
    ui.press(ui.action("all"))
    nonce = max_sources.SESSIONS[OWNER].nonce
    ui.press(f"mx:d:{nonce}:legacy:{forged}")
    assert domain.writes == []
    assert max_sources.SESSIONS[OWNER].legacy_chat_id is None
    assert not domain.legacy[LEGACY]["max_legacy_archived"]


def test_legacy_linked_to_another_source_is_not_selectable(env):
    domain, ui = env
    domain.add_legacy(linked_chat_id=CHAT + 1)
    ui.edit()
    ui.press(ui.action("all"))
    assert all((b.callback_data or "").split(":")[-1] != str(LEGACY) for b in ui.buttons)
    assert domain.writes == []


def test_existing_legacy_link_is_immutable_in_audience_edit(env):
    domain, ui = env
    legacy = domain.add_legacy(linked_chat_id=CHAT, max_legacy_archived=True)
    source = domain.sources[CHAT]
    source.update(enabled=True, legacy_chat_id=LEGACY, history_status="complete")
    save = ui.review(code="B27")
    assert not any(":legacy:" in (b.callback_data or "") for b in ui.buttons)
    ui.press(save)
    assert source["legacy_chat_id"] == LEGACY and legacy["max_legacy_archived"]
    assert source["history_status"] == "complete"  # audience changes do not restart the archive


def test_disable_confirmation_keeps_userbot_and_legacy_content(env):
    domain, ui = env
    legacy = domain.add_legacy(linked_chat_id=CHAT, max_legacy_archived=True)
    source = domain.sources[CHAT]
    source.update(enabled=True, legacy_chat_id=LEGACY, history_status="complete")
    before = deepcopy(domain.messages)
    ui.press(f"mx:chat:{CHAT}")
    ui.click("Выключить")
    off = ui.action("off")
    assert source["enabled"] and domain.writes == []
    assert "оста" in ui.text.lower()
    ui.press(off)
    assert not source["enabled"] and domain.messages == before
    assert legacy["max_legacy_archived"]
    ui.press(off)
    assert len(domain.writes) == 1


def test_full_history_and_gap_recovery_are_independent_visible_statuses(env):
    domain, ui = env
    source = domain.sources[CHAT]
    source.update(enabled=True, history_status="complete", catchup_status="partial",
                  last_error="history_timestamp_boundary")
    ui.press(f"mx:chat:{CHAT}")
    text = ui.text.lower()
    assert "истори" in text and ("разрыв" in text or "пропуск" in text or "catchup" in text)
    assert "partial" in text or "частич" in text
    ui.click("Повторить историю")
    assert source["history_status"] == "complete" and domain.writes == []
    confirm = ui.action("history")
    ui.press(confirm)
    assert source["history_status"] == "pending" and source["catchup_status"] == "pending"
    assert domain.writes == [("history", CHAT)]
    ui.press(confirm)
    assert len(domain.writes) == 1


def test_offline_refresh_only_queues_catalog_and_empty_catalog_explains_login(env):
    domain, ui = env
    domain.account.update(heartbeat_at=None, catalog_status="partial",
                          catalog_error="catalog_pagination_unknown")
    ui.press("mx:list:0")
    assert "offline" in ui.text.lower() or "офлайн" in ui.text.lower()
    assert "partial" in ui.text.lower() or "частич" in ui.text.lower()
    ui.press("mx:refresh")
    assert domain.refreshes == 1 and domain.writes == []
    domain.sources.clear()
    ui.press("mx:list:0")
    assert "catix-maxuserbot login" in ui.text
    assert "аккаунт" in ui.text.lower()


@pytest.mark.parametrize("command", ["/cancel", "/admin", "/listen", "/start"])
def test_slash_commands_cancel_max_draft_and_reach_downstream_router(env, command):
    domain, ui = env
    save = ui.review()
    ui.send(command)
    assert OWNER not in max_sources.SESSIONS
    assert domain.writes == []
    expected = {"/cancel": "Отмен", "/admin": "Управление", "/listen": "Подключённые", "/start": "Привет"}
    assert expected[command].lower() in ui.text.lower()
    ui.press(save)
    assert domain.writes == []


@pytest.mark.parametrize("exit_payload", ["mx:list:0", f"mx:chat:{CHAT}", "ls:l:keep", "adm:home"])
def test_navigation_cancels_max_draft_and_stale_save(env, exit_payload):
    domain, ui = env
    save = ui.review()
    ui.press(exit_payload)
    assert OWNER not in max_sources.SESSIONS
    ui.press(save)
    assert domain.writes == []


def test_telegram_to_max_cancels_listen_and_admin_prompts_before_new_session(env):
    domain, ui = env
    ui.press("ls:add")
    assert OWNER in listen.SESSIONS
    admin.PENDING.add(OWNER)
    ui.edit()
    assert OWNER not in listen.SESSIONS and OWNER not in admin.PENDING
    assert OWNER in max_sources.SESSIONS
    ui.press("ls:add")
    assert OWNER not in max_sources.SESSIONS and OWNER in listen.SESSIONS
    assert domain.writes == []


def test_cancel_and_back_destroy_draft_without_mutation(env):
    domain, ui = env
    save = ui.review()
    ui.press(ui.action("cancel"))
    assert OWNER not in max_sources.SESSIONS
    ui.press(save)
    assert domain.writes == []


@pytest.mark.parametrize("payload", ["mx:", "mx:chat:nope", "mx:edit:999", "mx:d:deadbeef:save", "mx:d:deadbeef:off"])
def test_malformed_and_missing_source_callbacks_are_safe(env, payload):
    domain, ui = env
    ui.press(payload)
    assert domain.writes == [] and domain.refreshes == 0
    assert_not_saved(ui)


def test_legacy_picker_paginates_and_stale_save_cannot_archive(env):
    domain, ui = env
    for offset in range(11):
        domain.add_legacy(LEGACY + offset, f"Old course {offset:02}")
    ui.edit()
    ui.press(ui.action("all"))
    picks = [b for b in ui.buttons if ":legacy:" in (b.callback_data or "")
             and not (b.callback_data or "").endswith(":none")]
    assert len(picks) == 8
    ui.press(ui.action("page", 1))
    picks = [b for b in ui.buttons if ":legacy:" in (b.callback_data or "")
             and not (b.callback_data or "").endswith(":none")]
    assert len(picks) == 3
    selected = int(picks[0].callback_data.split(":")[-1])
    ui.press(picks[0].callback_data)
    save = ui.action("save")
    domain.sources[CHAT]["config_version"] += 1
    ui.press(save)
    assert domain.writes == []
    assert not domain.legacy[selected]["max_legacy_archived"]
    assert domain.sources[CHAT]["legacy_chat_id"] is None


def test_legacy_claimed_after_review_does_not_archive_or_report_success(env):
    domain, ui = env
    legacy = domain.add_legacy()
    save = ui.review(legacy=LEGACY)
    legacy["linked_chat_id"] = CHAT + 1
    ui.press(save)
    assert domain.writes == [] and not legacy["max_legacy_archived"]
    assert domain.sources[CHAT]["legacy_chat_id"] is None
    assert_not_saved(ui)


def test_reenable_requests_entire_history_without_restoring_legacy_search(env):
    domain, ui = env
    legacy = domain.add_legacy(linked_chat_id=CHAT, max_legacy_archived=True)
    source = domain.sources[CHAT]
    source.update(enabled=False, generation=8, config_version=12,
                  legacy_chat_id=LEGACY, history_status="cancelled")
    ui.press(ui.review(code="B26"))
    assert source["enabled"] and source["history_status"] == "pending"
    assert source["generation"] == 9 and source["config_version"] == 13
    assert legacy["max_legacy_archived"]
    assert domain.messages[CHAT] == ["retained userbot message"]


def test_group_chat_text_cannot_finish_private_group_prompt(env, monkeypatch):
    domain, ui = env
    # The real generic group handler is downstream; its ingest boundary is unrelated
    # to the MAX wizard and must not reach a real DB during this routing test.
    ingested = []
    async def capture_group(message, **kwargs):
        ingested.append(message.text)
    monkeypatch.setattr(general, "_save", capture_group)
    ui.edit()
    ui.press(ui.action("group"))
    ui.send("B27", kind=ChatType.GROUP, chat_id=-900)
    assert max_sources.SESSIONS[OWNER].group_code is None
    assert domain.writes == []
    assert ingested == ["B27"]


def test_navigation_to_admin_add_cancels_max_and_opens_admin_prompt(env):
    domain, ui = env
    save = ui.review()
    ui.press("adm:add")
    assert OWNER not in max_sources.SESSIONS
    assert OWNER in admin.PENDING
    ui.press(save)
    assert domain.writes == []


def test_cancel_pending_public_hook_does_not_cancel_other_admin_session(env):
    domain, ui = env
    ui.edit()
    owner_session = max_sources.SESSIONS[OWNER]
    ui.press(f"mx:edit:{CHAT}", user_id=72, chat_id=72)
    assert max_sources.SESSIONS[72].nonce != owner_session.nonce
    max_sources.cancel_pending(72)
    assert 72 not in max_sources.SESSIONS
    assert max_sources.SESSIONS[OWNER] is owner_session
    assert domain.writes == []


def test_review_refresh_retains_draft_and_can_save_after_account_recovers(env):
    domain, ui = env
    save = ui.review(code="B26")
    session = max_sources.SESSIONS[OWNER]
    snapshot = deepcopy(session)
    domain.account["heartbeat_at"] = None
    ui.press(ui.action("refresh"))
    assert domain.refreshes == 1
    assert max_sources.SESSIONS[OWNER] == snapshot
    assert domain.writes == []
    domain.account["heartbeat_at"] = datetime.now(timezone.utc)
    ui.press(save)
    assert domain.sources[CHAT]["enabled"]
    assert domain.sources[CHAT]["group_code"] == "B26"


@pytest.mark.parametrize("action", ["save", "off", "history", "legacy:71"])
def test_action_not_offered_in_current_stage_cannot_mutate(env, action):
    domain, ui = env
    ui.edit()
    session = max_sources.SESSIONS[OWNER]
    ui.press(f"mx:d:{session.nonce}:{action}")
    assert domain.writes == []
    assert session.stage == "audience" and session.group_code is None


def test_login_required_account_is_visible_without_triggering_login(env):
    domain, ui = env
    domain.account.update(heartbeat_at=None, catalog_status="failed", catalog_error="login_required")
    ui.press("mx:list:0")
    assert "login_required" in ui.text and "catix-maxuserbot login" in ui.text
    assert domain.refreshes == 0 and domain.writes == []


def test_disappeared_source_after_review_cannot_be_saved(env):
    domain, ui = env
    save = ui.review()
    del domain.sources[CHAT]
    ui.press(save)
    assert domain.writes == []
    assert_not_saved(ui)
