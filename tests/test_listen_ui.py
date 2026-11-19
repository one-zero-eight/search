"""Hermetic UI tests: real screens/handlers, in-memory DB boundary and Telegram transport."""

import asyncio
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from catix import userbot_config as config
from catix.tgbot import listen


def buttons(screen):
    return [b for row in screen[1] for b in row]


def data(screen, label):
    found = [b.callback_data for b in buttons(screen) if label in b.text]
    assert len(found) == 1, (label, [b.text for b in buttons(screen)])
    return found[0]


class UI:
    def __init__(self):
        self.screen = None
        self.notices = []
        self.message = SimpleNamespace(
            chat=SimpleNamespace(id=7, type="private"), from_user=SimpleNamespace(id=7),
            text=None, answer=AsyncMock(side_effect=self.render), edit_text=AsyncMock(side_effect=self.render),
        )

    async def render(self, text, **kwargs):
        markup = kwargs.get("reply_markup")
        self.screen = (text, markup.inline_keyboard if markup else [])

    async def notice(self, text=None, **kwargs):
        self.notices.append(text or "")

    def press(self, payload):
        query = SimpleNamespace(from_user=self.message.from_user, message=self.message, data=payload,
                                answer=AsyncMock(side_effect=self.notice))
        asyncio.run(listen.listen_callback(query))
        return self.screen

    def click(self, label):
        return self.press(data(self.screen, label))

    def text(self, text):
        self.message.text = text
        asyncio.run(listen.group_code(self.message))
        return self.screen


@pytest.fixture
def env(monkeypatch):
    state = SimpleNamespace(
        dialogs=[config.Dialog(-1001, "Connected", "group", None, True),
                 config.Dialog(-1002, "Available <forum>", "group", None, True),
                 config.Dialog(-1003, "Bot only", "group", None, False, True, True)],
        chosen={-1001: []}, policies={-1001: {"default": "search", "topics": {}}},
        groups={-1001: "B26-CSE-01"}, readers={-1001: "auto"}, writes=[], allowed=True,
        topics=[config.Topic(i, f"Topic {i}", False) for i in range(1, 51)],
        known=["all", "B26-CSE-01", "A" * 40], official={},
    )
    for name in ("PAGE", "PENDING_GROUP", "SESSIONS"):
        if hasattr(listen, name):
            getattr(listen, name).clear()
    async def is_admin(uid):
        return state.allowed and uid == 7
    monkeypatch.setattr(listen, "_is_admin", is_admin)
    monkeypatch.setattr(config, "dialogs", lambda: state.dialogs)
    monkeypatch.setattr(config, "dialog", lambda cid: next((d for d in state.dialogs if d.chat_id == cid), None))
    monkeypatch.setattr(config, "listened", lambda: dict(state.chosen))
    monkeypatch.setattr(config, "readers", lambda: dict(state.readers))
    monkeypatch.setattr(config, "topics", lambda cid: state.topics)
    monkeypatch.setattr(config, "get_policy", lambda cid: deepcopy(state.policies.get(cid, {"default": "search", "topics": {}})), raising=False)
    monkeypatch.setattr(listen, "_group_of", lambda cid: state.groups.get(cid, "all"))
    monkeypatch.setattr(listen, "_groups_of", lambda ids: {c: state.groups[c] for c in ids if c in state.groups})
    monkeypatch.setattr(listen, "_known_groups", lambda: list(state.known))
    monkeypatch.setattr(listen.official, "flags", lambda ids: {c: state.official.get(c, False) for c in ids})
    monkeypatch.setattr(listen.store, "chat_message_counts", lambda cid: (12, 0))
    def save(cid, group_code, default_mode, topic_modes, reader="auto"):
        state.writes.append(("save", cid, group_code, default_mode, dict(topic_modes), reader))
        state.groups[cid] = group_code
        state.policies[cid] = {"default": default_mode, "topics": dict(topic_modes)}
        state.readers[cid] = reader
        state.chosen[cid] = []
    monkeypatch.setattr(config, "save_configuration", save, raising=False)
    for obj, name in ((config, "set_listen"), (config, "set_reader"), (config, "toggle_topic"),
                      (config, "clear_topics"), (listen.store, "upsert_chat"),
                      (listen.store, "clear_chat"), (listen.groups, "set_chat_group")):
        monkeypatch.setattr(obj, name, lambda *args, _name=name, **kwargs: state.writes.append((_name, *args)))
    return state, UI()


def test_group_list_only_shows_connected_chats_with_add_entry(env):
    state, ui = env
    ui.press("ls:l:0")
    labels = [b.text for b in buttons(ui.screen)]
    assert any("Connected" in label for label in labels)
    assert not any("Available" in label or "Bot only" in label for label in labels)
    assert data(ui.screen, "Добавить группу")
    assert data(ui.screen, "Администрирование") == "adm:home"


def test_onboarding_is_a_draft_until_review_confirmation(env):
    state, ui = env
    ui.press("ls:add")
    ui.click("Available")
    assert "Учебная группа" in ui.screen[0]
    ui.click("B26-CSE-01")
    assert "Остальные и новые" in ui.screen[0]
    assert "Только поиск" in ui.screen[0]
    ui.click("Topic 1 ·")
    ui.click("Хранить")
    ui.click("Проверить")
    assert "Проверка" in ui.screen[0]
    assert "B26-CSE-01" in ui.screen[0]
    assert "Хранить: 1" in ui.screen[0]
    assert state.writes == []
    ui.click("Подтвердить")
    assert state.writes == [("save", -1002, "B26-CSE-01", "search", {1: "store"}, "auto")]
    assert "Сохранено" in " ".join(ui.notices)


def test_topic_editor_paginates_every_topic_and_none_stored_means_none(env):
    state, ui = env
    ui.press("ls:add")
    ui.click("Available")
    ui.click("all")
    seen = set()
    while True:
        topic_buttons = [b for b in buttons(ui.screen) if b.text.startswith("Topic ")]
        assert len(topic_buttons) <= listen.PAGE_SIZE
        seen.update(int(b.text.split()[1]) for b in topic_buttons)
        if not any(b.text == "▶" for b in buttons(ui.screen)):
            break
        ui.click("▶")
    assert seen == set(range(1, 51))
    ui.click("Topic 50 ·")
    ui.click("Хранить")
    ui.click("Topic 50 ·")
    ui.click("Только поиск")
    ui.click("Остальные и новые")
    ui.click("Выключен")
    ui.click("Проверить")
    assert "Хранить: 0" in ui.screen[0]
    assert "Остальные и новые: Выключен" in ui.screen[0]
    ui.click("Подтвердить")
    assert state.policies[-1002] == {"default": "off", "topics": {50: "search"}}


@pytest.mark.parametrize("bot_only", [False, True])
def test_nonforum_whole_chat_mode_and_bot_only_never_offers_search(env, bot_only):
    state, ui = env
    state.dialogs = [config.Dialog(-1003, "Plain chat", "group", None, False, bot_only, bot_only)]
    ui.press("ls:add")
    ui.click("Plain chat")
    ui.click("all")
    assert "Весь чат: " + ("Выключен" if bot_only else "Только поиск") in ui.screen[0]
    assert not any("Topic " in b.text for b in buttons(ui.screen))
    ui.click("Весь чат")
    labels = [b.text for b in buttons(ui.screen)]
    assert any("Только поиск" in label for label in labels) is not bot_only
    ui.click("Хранить")
    ui.click("Проверить")
    assert "Весь чат: Хранить" in ui.screen[0]
    ui.click("Подтвердить")
    assert state.policies[-1003] == {"default": "store", "topics": {}}


@pytest.mark.parametrize("query", ["Chat 19", "-2019"])
def test_available_picker_paginates_and_searches_title_or_id(env, query):
    state, ui = env
    state.dialogs.extend(config.Dialog(-2000-i, f"Chat {i}", "group", None, False) for i in range(20))
    ui.press("ls:add")
    assert not any("Connected" in b.text for b in buttons(ui.screen))
    assert len([b for b in buttons(ui.screen) if ":pick:" in b.callback_data]) <= listen.PAGE_SIZE
    ui.click("▶")
    ui.click("Найти")
    ui.message.text = query
    assert listen._waiting_for_group(ui.message)
    ui.text(query)
    assert any("Chat 19" in b.text for b in buttons(ui.screen))
    assert not any("Chat 18" in b.text for b in buttons(ui.screen))
    assert state.writes == []
    ui.click("Chat 19")
    ui.click("A" * 40)
    ui.click("Проверить")
    for b in buttons(ui.screen):
        assert len(b.callback_data.encode()) <= 64
    ui.click("Подтвердить")
    assert state.groups[-2019] == "A" * 40


def test_existing_configuration_edit_is_draft_with_custom_group_and_cancel(env):
    state, ui = env
    state.policies[-1001] = {"default": "off", "topics": {1: "store"}}
    state.readers[-1001] = "userbot"
    ui.press("ls:c:-1001")
    ui.click("Изменить")
    ui.click("Другая группа")
    ui.text("b27-cse-02")
    assert "Остальные и новые: Выключен" in ui.screen[0]
    ui.click("Topic 1 ·")
    ui.click("Только поиск")
    ui.click("Проверить")
    assert "B27-CSE-02" in ui.screen[0]
    assert "Хранить: 0" in ui.screen[0]
    assert state.writes == []
    ui.click("Отмена")
    assert state.policies[-1001] == {"default": "off", "topics": {1: "store"}}
    assert state.writes == []
    ui.press("ls:c:-1001")
    ui.click("Изменить")
    ui.click("B26-CSE-01")
    ui.click("Проверить")
    ui.click("Подтвердить")
    assert state.readers[-1001] == "userbot"


@pytest.mark.parametrize("private", [False, True])
@pytest.mark.parametrize("payload", ["ls:o:-1001", "ls:cy:-1001", "ls:of:-1001", "ls:w:-1001:bot"])
def test_every_callback_requires_private_chat_and_current_admin(env, monkeypatch, private, payload):
    state, ui = env
    monkeypatch.setattr(listen, "_toggle_official", lambda cid: state.writes.append(("official", cid)))
    if private:
        state.allowed = False
    else:
        ui.message.chat.type = "supergroup"
    ui.press(payload)
    assert state.writes == []
    assert ui.notices


@pytest.mark.parametrize("exit_action", ["list", "chat", "hook", "slash", "cancel", "listen"])
def test_leaving_wizard_clears_prompts_and_stale_confirmation(env, exit_action):
    state, ui = env
    ui.press("ls:add")
    ui.click("Available")
    ui.click("all")
    ui.click("Проверить")
    stale_save = data(ui.screen, "Подтвердить")
    if exit_action == "list":
        ui.press("ls:l:0")
    elif exit_action == "chat":
        ui.press("ls:c:-1001")
    elif exit_action == "hook":
        listen.cancel_pending(7)
    elif exit_action == "slash":
        ui.message.text = "/start"
        assert not listen._waiting_for_group(ui.message)
    elif exit_action == "cancel":
        asyncio.run(listen.cancel_command(ui.message))
    else:
        asyncio.run(listen.listen_command(ui.message))
    ui.press(stale_save)
    assert state.writes == []
    assert "устарел" in ui.notices[-1]


def test_listen_section_clears_admin_add_prompt(env):
    from catix.tgbot import admin
    _, ui = env
    admin.PENDING.add(7)
    ui.press("ls:add")
    assert 7 not in admin.PENDING
    admin.PENDING.add(7)
    asyncio.run(listen.listen_command(ui.message))
    assert 7 not in admin.PENDING


@pytest.mark.parametrize("prompt", ["search", "custom"])
@pytest.mark.parametrize("reject", ["revoked", "other_private_chat", "group"])
def test_text_prompt_rechecks_authorization_and_private_session(env, prompt, reject):
    state, ui = env
    ui.press("ls:add")
    if prompt == "custom":
        ui.click("Available")
        ui.click("Другая группа")
    else:
        ui.click("Найти")
    if reject == "revoked":
        state.allowed = False
    elif reject == "group":
        ui.message.chat.type = "supergroup"
    else:
        ui.message.chat.id = 999
    ui.text("B27-CSE-02")
    assert state.writes == []
    assert ui.screen[0].startswith("Только для администратора") or "экран устарел" in ui.screen[0]


def test_advanced_controls_are_separate_and_reader_changes_require_save(env):
    state, ui = env
    state.dialogs[0] = config.Dialog(-1001, "Connected", "group", None, True, False, True)
    ui.press("ls:c:-1001")
    assert not any("официаль" in b.text or "Очистить" in b.text or "Авто" in b.text for b in buttons(ui.screen))
    assert "все" not in ui.screen[0]
    ui.click("Дополнительно")
    assert "Официальный чат" in ui.screen[0]
    assert data(ui.screen, "Очистить")
    ui.click("Кто читает")
    assert not any("Поиск" in b.text or "поиск" in b.text for b in buttons(ui.screen))
    ui.click("бот")
    assert state.writes == []
    ui.click("Проверить")
    ui.click("Подтвердить")
    assert state.readers[-1001] == "bot"


@pytest.mark.parametrize("payload", ["ls:x:-1001:1", "ls:a:-1001", "ls:s:-1001:all",
                                      "ls:w:-1001:search", "ls:cy:-1001", "ls:o:-1002"])
def test_legacy_write_buttons_cannot_bypass_draft_confirmation(env, payload):
    state, ui = env
    ui.press(payload)
    assert state.writes == []


def test_disable_and_clear_are_distinct_nonce_bound_confirmations(env, monkeypatch):
    state, ui = env
    counts = {"stored": 12}
    def disable(cid, enabled):
        state.writes.append(("set_listen", cid, enabled))
        state.chosen.pop(cid, None)
    def clear(cid):
        state.writes.append(("clear_chat", cid))
        deleted = counts["stored"]
        counts["stored"] = 0
        return deleted
    monkeypatch.setattr(config, "set_listen", disable)
    monkeypatch.setattr(listen.store, "clear_chat", clear)
    monkeypatch.setattr(listen.store, "chat_message_counts", lambda cid: (counts["stored"], 0))
    ui.press("ls:adv:-1001")
    ui.click("Отключить группу")
    assert state.writes == []
    assert "сохранённые сообщения" in ui.screen[0].lower()
    ui.click("Да, отключить")
    assert state.writes == [("set_listen", -1001, False)]
    ui.press("ls:adv:-1001")
    ui.click("Очистить")
    clear = data(ui.screen, "Да, удалить")
    assert len(state.writes) == 1
    ui.press(clear)
    assert state.writes[-1] == ("clear_chat", -1001)
    ui.press(clear)
    assert len(state.writes) == 2


@pytest.mark.parametrize("bad", ["other_private_chat", "forged_mode", "forged_save", "truncated", "unknown_topic"])
def test_draft_callback_rejects_wrong_scope_or_nonexistent_buttons(env, bad):
    state, ui = env
    ui.press("ls:add")
    ui.click("Bot only")
    ui.click("all")
    ui.click("Весь чат")
    payload = data(ui.screen, "Хранить")
    if bad == "other_private_chat":
        ui.message.chat.id = 42
    elif bad == "forged_mode":
        payload = payload.replace(":mode:store", ":mode:search")
    elif bad == "forged_save":
        payload = payload.replace(":mode:store", ":save:")
    elif bad == "unknown_topic":
        payload = payload.replace(":mode:store", ":topic:987654")
    else:
        payload = payload.split(":mode:")[0]
    before = deepcopy(listen.SESSIONS[7])
    ui.press(payload)
    assert listen.SESSIONS[7] == before
    assert state.writes == []
    assert "устарел" in ui.notices[-1] or "Недопустим" in ui.notices[-1]


def test_save_verification_accepts_backend_normalization_and_migrates_legacy_reader(env, monkeypatch):
    state, ui = env
    state.readers[-1001] = "search"
    original = config.save_configuration
    def save(*args):
        original(*args)
        policy = state.policies[args[0]]
        policy["topics"] = {tid: mode for tid, mode in policy["topics"].items() if mode != policy["default"]}
    monkeypatch.setattr(config, "save_configuration", save)
    ui.press("ls:edit:-1001")
    ui.click("all")
    ui.click("Topic 1 ·")
    ui.click("Только поиск")
    ui.click("Проверить")
    ui.click("Подтвердить")
    assert state.readers[-1001] == "auto"
    assert "Сохранено" in ui.notices[-1]


@pytest.mark.parametrize("failure", ["validation", "transport", "policy", "group", "reader"])
def test_failed_or_unverified_save_never_reports_success(env, monkeypatch, failure):
    state, ui = env
    original = config.save_configuration
    def save(*args):
        if failure == "validation":
            raise ValueError("chat disappeared")
        if failure == "transport":
            raise RuntimeError("connection lost")
        original(*args)
        if failure == "policy":
            state.policies[args[0]]["default"] = "off"
        elif failure == "group":
            state.groups[args[0]] = "WRONG"
        else:
            state.readers[args[0]] = "bot"
    monkeypatch.setattr(config, "save_configuration", save)
    ui.press("ls:add")
    ui.click("Available")
    ui.click("all")
    ui.click("Проверить")
    ui.click("Подтвердить")
    assert not any("Сохранено" in n for n in ui.notices)
    assert "Не удалось" in ui.notices[-1]


def test_wizard_has_back_cancel_and_paged_group_codes(env):
    state, ui = env
    state.known.extend(f"B27-{i}" for i in range(30))
    ui.press("ls:add")
    assert data(ui.screen, "Отмена")
    ui.click("Available")
    assert len([b for b in buttons(ui.screen) if ":group:" in b.callback_data]) <= listen.PAGE_SIZE
    ui.click("▶")
    ui.click("B27-12")
    assert data(ui.screen, "Отмена")
    ui.click("Topic 1 ·")
    ui.click("Назад")
    ui.click("Проверить")
    assert "Выключен" in ui.screen[0] and "сохранённые" in ui.screen[0].lower()
    assert "Читает:" in ui.screen[0]
    ui.click("Назад")
    ui.click("Назад")
    assert "Учебная группа: B27-12" in ui.screen[0]
    assert state.writes == []


def test_official_callback_returns_to_advanced_controls(env, monkeypatch):
    state, ui = env
    monkeypatch.setattr(listen.official, "set_official", lambda cid, value: state.official.update({cid: value}))
    ui.press("ls:adv:-1001")
    ui.click("Сделать официальным")
    assert state.official[-1001] is True
    assert "Официальный чат: да" in ui.screen[0]
    ui.click("Снять отметку")
    assert state.official[-1001] is False


def test_official_toggle_does_not_report_unverified_write(env, monkeypatch):
    _, ui = env
    monkeypatch.setattr(listen.official, "set_official", lambda cid, value: None)
    ui.press("ls:of:-1001")
    assert "Не удалось" in ui.notices[-1]


@pytest.mark.parametrize("payload", ["ls:", "ls:l", "ls:c:nope", "ls:c:--1001", "ls:c:²", "ls:edit:-999", "ls:reader:-999", "ls:cl:-999"])
def test_invalid_or_missing_chat_buttons_are_safe(env, payload):
    state, ui = env
    ui.press(payload)
    assert state.writes == []
    assert 7 not in listen.SESSIONS


def test_disappeared_dialog_cannot_be_confirmed(env):
    state, ui = env
    ui.press("ls:add")
    ui.click("Available")
    ui.click("all")
    ui.click("Проверить")
    save = data(ui.screen, "Подтвердить")
    state.dialogs = [d for d in state.dialogs if d.chat_id != -1002]
    ui.press(save)
    assert state.writes == []


def test_unconnected_bot_chat_opened_directly_also_defaults_off(env):
    _, ui = env
    ui.press("ls:edit:-1003")
    ui.click("all")
    assert "Весь чат: Выключен" in ui.screen[0]


@pytest.mark.parametrize("action,label,forbidden", [("ls:o:-1001", "Да, отключить", "Группа отключена"),
                                                   ("ls:cl:-1001", "Да, удалить", "Удалено сообщений")])
def test_destructive_confirmation_checks_readback_before_reporting_success(env, action, label, forbidden):
    _, ui = env
    ui.press(action)
    ui.click(label)
    assert forbidden not in ui.notices[-1]
    assert "Не удалось" in ui.notices[-1]
