"""Private Telegram administration for passive MAX account sources.

Only the worker talks to MAX. These handlers read its catalogue and enqueue work;
unsaved configuration and confirmation nonces exist only in this process.
"""

import asyncio
import html
import logging
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.enums import ChatType, ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from catix import admins, groups
from catix import official
from catix.db import store
from catix.tgbot import group_settings
from catix.maxuserbot import state

log = logging.getLogger("catix.max_sources")
router = Router()
PAGE_SIZE = 8
Keyboard = list[list[InlineKeyboardButton]]

ACCESS = {"ready": "доступ есть", "unknown": "доступ не подтверждён",
          "removed": "чат недоступен аккаунту", "no_permission": "нет доступа к сообщениям"}
HISTORY = {"idle": "не запрошена", "pending": "ожидает загрузки", "running": "загружается",
           "complete": "вся история, доступная аккаунту через API, загружена",
           "partial": "загружена частично", "failed": "ошибка загрузки", "cancelled": "остановлена"}
GAP = {"idle": "разрыв не обнаружен", "pending": "ожидает восстановления", "running": "восстанавливается",
       "complete": "доступные сообщения восстановлены", "partial": "восстановлен частично",
       "failed": "ошибка восстановления", "cancelled": "остановлено"}
REASONS = {
    "login_required": "Нужен вход: выполните catix-maxuserbot login в терминале.",
    "account_mismatch": "Сессия принадлежит другому аккаунту; требуется проверка оператора.",
    "identity_range": "Идентификатор источника вне поддерживаемого диапазона.",
    "protocol_error": "Ответ MAX не соответствует ожидаемому протоколу.",
    "processing_error": "Не удалось обработать данные источника.",
    "metadata_error": "Не удалось обновить сведения о доступе.",
    "source_status_unknown": "Статус чата неизвестен; чтение не разрешено.",
    "catalog_pagination_unknown": "MAX не сообщил продолжение каталога; список неполный.",
    "catalog_cursor_stalled": "Продолжение каталога не продвигается; список неполный.",
    "history_error": "Не удалось получить страницу истории.",
    "history_timestamp_boundary": "Граница времени не позволяет продолжить историю; загружена только часть.",
    "message_unavailable": "Сообщение недоступно; отсутствие не считается удалением.",
    "deletion_reconciliation_partial": "Не все массовые удаления удалось подтвердить.",
    "publication_error": "Обновление поискового индекса ожидает повторной отправки.",
}
REPEATABLE = {"complete", "partial", "failed", "cancelled"}
ID = re.compile(r"-?[0-9]{1,19}\Z", re.ASCII)


@dataclass
class Session:
    user_id: int
    private_chat_id: int
    chat_id: int
    config_version: int
    generation: int
    nonce: str = field(default_factory=lambda: secrets.token_hex(4))
    stage: str = "audience"
    group_code: str | None = None
    legacy_chat_id: int | None = None
    page: int = 0
    busy: bool = False
    codes: list[str] = field(default_factory=list)
    mode: str = 'store'


SESSIONS: dict[int, Session] = {}
PAGE: dict[int, int] = {}


def cancel_pending(user_id: int) -> None:
    """Discard only this user's MAX draft; safe for listen's cancellation hook."""
    SESSIONS.pop(user_id, None)


def _leave_other_drafts(user_id: int) -> None:
    # listen.cancel_pending calls our cancel_pending too: call before creating a draft.
    from catix.tgbot import admin, listen

    listen.cancel_pending(user_id)
    admin.PENDING.discard(user_id)
    cancel_pending(user_id)


def _button(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def _draft_button(s: Session, text: str, action: str, value: str | int | None = None) -> InlineKeyboardButton:
    data = f"mx:d:{s.nonce}:{action}"
    return _button(text, data if value is None else f"{data}:{value}")


def _title(source: dict, size: int = 160) -> str:
    title = str(source.get("title") or "Без названия")
    return title if len(title) <= size else title[:size - 1] + "…"


def _audience(code: str | None) -> str:
    return "Для всех" if code == groups.ALL else f"Учебная группа {code or 'не выбрана'}"


def _reason(code: str | None) -> str:
    return REASONS.get(code, "Не удалось завершить операцию; обновите сведения и повторите.")


def _online(account: dict | None) -> bool:
    heartbeat = account.get("heartbeat_at") if account else None
    return isinstance(heartbeat, datetime) and heartbeat.tzinfo is not None and heartbeat >= datetime.now(timezone.utc) - timedelta(seconds=60)


def _account_lines(account: dict | None) -> list[str]:
    if account and account.get("catalog_error") == "login_required":
        lines = ["Аккаунт: требуется вход (login_required).", _reason("login_required")]
    else:
        lines = ["Аккаунт: онлайн." if _online(account) else "Аккаунт: офлайн."]
    status = account.get("catalog_status", "idle") if account else "idle"
    labels = {"idle": "не обновлён", "running": "обновляется", "complete": "обновлён",
              "partial": "неполный (partial)", "failed": "ошибка обновления"}
    lines.append(f"Каталог: {labels.get(status, 'статус неизвестен')}.")
    if account and account.get("catalog_error"):
        lines.append(_reason(account["catalog_error"]))
    return lines


def _list_screen(user_id: int) -> tuple[str, Keyboard]:
    sources = state.list_sources()
    lines = ["<b>Источники MAX</b>", *_account_lines(state.get_account())]
    page = min(max(PAGE.get(user_id, 0), 0), max((len(sources) - 1) // PAGE_SIZE, 0))
    PAGE[user_id] = page
    rows: Keyboard = []
    for source in sources[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]:
        title = _title(source, 56)
        lines.append(f"\n<b>{html.escape(title)}</b> · raw ID <code>{source['raw_chat_id']}</code>\n"
                     f"{html.escape(_audience(source.get('group_code')))} · "
                     f"{'включён' if source['enabled'] else 'выключен'} · {ACCESS.get(source['access'], 'доступ неизвестен')}\n"
                     f"История: {HISTORY.get(source.get('history_status'), 'статус неизвестен')}")
        rows.append([_button(f"{'🏛 ' if source.get('official') else ''}{_title(source, 28)} · {source['raw_chat_id']}", f"mx:chat:{source['chat_id']}")])
    if not sources:
        lines.append("\nВыполните catix-maxuserbot login, добавьте аккаунт в нужные чаты и обновите список. "
                     "Показываются группы и каналы, не личные диалоги. Права администратора MAX не требуются.")
    else:
        lines.append(f"\nСтраница {page + 1}/{(len(sources) - 1) // PAGE_SIZE + 1}")
    nav = []
    if page:
        nav.append(_button("←", f"mx:list:{page - 1}"))
    if (page + 1) * PAGE_SIZE < len(sources):
        nav.append(_button("→", f"mx:list:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.extend([[_button("Обновить список", "mx:refresh")], [_button("← Группы и источники", "ls:l:keep")]])
    return "\n".join(lines), rows


def _source_lines(source: dict) -> list[str]:
    return [f"<b>{html.escape(_title(source))}</b>",
            f"MAX raw ID: <code>{source['raw_chat_id']}</code>",
            f"ID в базе: <code>{source['chat_id']}</code>",
            f"Аудитория: {html.escape(_audience(source.get('group_code')))}",
            f"Чтение: {'включено' if source['enabled'] else 'выключено'}; {ACCESS.get(source['access'], 'доступ неизвестен')}.",
            f"Официальный чат: {'да' if source.get('official') else 'нет'}"]


def _chat_screen(source: dict) -> tuple[str, Keyboard]:
    lines = _source_lines(source)
    lines.extend([f"Полная история: {HISTORY.get(source.get('history_status'), 'статус неизвестен')}.",
                  f"Восстановление разрыва: {GAP.get(source.get('catchup_status', 'idle'), 'статус неизвестен')}.",
                  "Восстановление доступных сообщений не гарантирует все правки и удаления за время отключения."])
    if source.get("last_error"):
        lines.append(_reason(source["last_error"]))
    if source.get("legacy_chat_id") is not None:
        lines.append(f"Связанный старый источник: <code>{source['legacy_chat_id']}</code>. "
                     "Привязка неизменна; скрытый архив не возвращается в поиск после выключения.")
    rows = [[_button("Настроить", f"mx:edit:{source['chat_id']}")],
            [_button("⚙️ Дополнительно", f"mx:adv:{source['chat_id']}")]]
    if source["enabled"]:
        rows.append([_button("Выключить", f"mx:off:{source['chat_id']}")])
        if source["access"] == "ready" and source.get("history_status") in REPEATABLE:
            rows.append([_button("Повторить историю", f"mx:history:{source['chat_id']}")])
    rows.extend([[_button("Обновить сведения", "mx:refresh")], [_button("← Источники MAX", "mx:list:0")]])
    return "\n".join(lines), rows


def _advanced_screen(source: dict) -> tuple[str, Keyboard]:
    chat_id = source['chat_id']
    marked = official.flags([chat_id]).get(chat_id, False)
    stored, _ = store.chat_message_counts(chat_id)
    lines = _source_lines(source) + [
        'Читает: MAX userbot (с историей).',
        f"Официальный чат: {'да' if marked else 'нет'} (только такие сообщения агент называет официальными)",
        f'Сообщений в базе: {stored}',
        'Выключение сохраняет сообщения. Очистка удаляет сообщения, но не настройки источника.']
    rows = [[_button('🏛 Снять отметку «официальный»' if marked else '🏛 Сделать официальным', f'mx:official:{chat_id}')]]
    if stored:
        rows.append([_button(f'🗑 Очистить сообщения ({stored})', f'mx:clear:{chat_id}')])
    if source['enabled']:
        rows.append([_button('🔕 Отключить группу', f'mx:off:{chat_id}')])
    rows.append([_button('← Назад', f'mx:chat:{chat_id}')])
    return '\n'.join(lines), rows


def _legacy_candidates(s: Session, source: dict, legacy: list[dict]) -> list[dict]:
    candidates = [row for row in legacy if row.get("linked_chat_id") in (None, s.chat_id)]
    return sorted(candidates, key=lambda row: (row["chat_id"] - groups.MAX_CHAT_BASE != source["raw_chat_id"],
                                               _title(row).casefold(), row["chat_id"]))


def _after_audience(s: Session, source: dict, legacy: list[dict]) -> None:
    s.page = 0
    s.stage = "legacy" if source.get("legacy_chat_id") is None and _legacy_candidates(s, source, legacy) else "review"


def _draft_screen(s: Session, source: dict, legacy: list[dict]) -> tuple[str, Keyboard]:
    lines = _source_lines(source)
    rows: Keyboard = []
    if s.stage == "audience":
        lines.append("\nВыберите аудиторию явно. Это определяет доступ к сообщениям на сайте.")
        rows.extend([[_draft_button(s, "Для всех", "all")], [_draft_button(s, "Учебная группа", "group")]])
    elif s.stage == "group":
        lines.append("\nПришлите код учебной группы. Латиница, цифры, точка, дефис или подчёркивание, до 40 символов.")
    elif s.stage == 'groups':
        def button(label, action, value=''):
            mapped = {'group': 'group_pick', 'page': 'group_page'}.get(action, action)
            return _draft_button(s, label, mapped, value) if value != '' else _draft_button(s, label, mapped)
        text, rows = group_settings.group_picker(_title(source), s.group_code or source['group_code'], s.codes, s.page, button)
        rows.append([_draft_button(s, 'Отмена', 'cancel')])
        return text, rows
    elif s.stage == 'mode':
        lines.append(f"Выбранная аудитория: {html.escape(_audience(s.group_code))}")
        lines.append(f"\nВесь чат: {'Хранить' if s.mode == 'store' else 'Выключен'}")
        lines.append('MAX не предоставляет подключённый поиск без хранения; топики не настраиваются.')
        rows.extend([[_draft_button(s, 'Весь чат — выбрать режим', 'default')],
                     [_draft_button(s, 'Проверить →', 'review')]])
    elif s.stage == 'mode_pick':
        rows.extend([[_draft_button(s, 'Хранить', 'mode', 'store')],
                     [_draft_button(s, 'Выключен', 'mode', 'off')]])
    elif s.stage == "legacy":
        candidates = _legacy_candidates(s, source, legacy)
        page = min(max(s.page, 0), max((len(candidates) - 1) // PAGE_SIZE, 0))
        lines.append("\nВыберите старый MAX-источник для явной привязки либо «Нет старого источника». "
                     "Совпадение ID — только подсказка, не автоматическая привязка.")
        for old in candidates[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]:
            raw = old["chat_id"] - groups.MAX_CHAT_BASE
            hint = " · совпадает raw ID" if raw == source["raw_chat_id"] else ""
            lines.append(f"\n{html.escape(_title(old, 56))}{hint}\nraw <code>{raw}</code> · "
                         f"DB <code>{old['chat_id']}</code> · сообщений: {old['message_count']}")
            rows.append([_draft_button(s, f"{_title(old, 28)} · {raw}", "legacy", old["chat_id"])])
        nav = []
        if page:
            nav.append(_draft_button(s, "←", "page", page - 1))
        if (page + 1) * PAGE_SIZE < len(candidates):
            nav.append(_draft_button(s, "→", "page", page + 1))
        if nav:
            rows.append(nav)
        rows.append([_draft_button(s, "Нет старого источника", "legacy", "none")])
    elif s.stage == "review":
        lines.extend(["\n<b>Проверьте перед сохранением</b>",
                      f"Аудитория: {html.escape(_audience(s.group_code))}",
                      'Читать новые сообщения и всю доступную историю.' if s.mode == 'store' else
                      'Выключить чтение. Сохранённые сообщения остаются в базе.',
                      "Изменение только аудитории уже включённого источника не перезагружает историю."])
        if s.legacy_chat_id is None:
            lines.append("Старый источник: не выбран; старые сообщения не будут скрыты.")
        else:
            old = next((row for row in legacy if row["chat_id"] == s.legacy_chat_id), None)
            lines.append(f"\n<b>Старый источник: {html.escape(_title(old)) if old else 'недоступен'}</b>\n"
                         f"MAX raw ID: <code>{s.legacy_chat_id - groups.MAX_CHAT_BASE}</code>\n"
                         f"ID в базе: <code>{s.legacy_chat_id}</code>\n"
                         f"Сообщений: {old['message_count'] if old else 'неизвестно'}")
            lines.append(('При подтверждении старый архив будет скрыт из поиска. ' if s.mode == 'store' else
                          'При выключенном чтении новый архив не скрывается. ')
                         + 'Сообщения и прежняя аудитория сохранятся в базе; выключение нового источника '
                         'не вернёт уже скрытый архив в поиск. Привязку изменить нельзя.')
        rows.extend([[_draft_button(s, "Сохранить", "save")], [_draft_button(s, "Обновить сведения", "refresh")]])
    elif s.stage == "off":
        lines.append("\n<b>Выключить чтение?</b> Новые сообщения не будут индексироваться. "
                     "Сохранённая история и её аудитория остаются; скрытый старый архив не возвращается в поиск.")
        rows.append([_draft_button(s, "Подтвердить выключение", "off")])
    elif s.stage == "history":
        lines.append("\n<b>Повторить всю доступную историю?</b> Возрастного ограничения нет. "
                     "Существующие сообщения не очищаются. Состояние восстановления разрыва учитывается отдельно.")
        rows.append([_draft_button(s, "Подтвердить повтор истории", "history")])
    elif s.stage == 'clear':
        stored, changes = store.chat_message_counts(s.chat_id)
        lines.append(group_settings.clear_text(_title(source), stored, changes, source['enabled']))
        lines.append('Текущая загрузка архива остановится. Для новой загрузки используйте «Повторить историю».')
        rows.append([_draft_button(s, '✅ Да, удалить', 'clear')])
    rows.append([_draft_button(s, "Отмена", "cancel")])
    return "\n".join(lines), rows


async def _is_admin(user_id: int) -> bool:
    return user_id in await asyncio.to_thread(admins.everyone)


async def _show(query: CallbackQuery, screen: tuple[str, Keyboard]) -> None:
    text, rows = screen
    try:
        await query.message.edit_text(text, parse_mode=ParseMode.HTML,
                                      reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    except TelegramBadRequest as error:
        if "not modified" not in str(error):
            raise


def _same_version(s: Session, source: dict) -> bool:
    return source["config_version"] == s.config_version and source["generation"] == s.generation


async def _draft_callback(query: CallbackQuery, args: list[str]) -> None:
    user_id = query.from_user.id
    s = SESSIONS.get(user_id)
    if (s is None or s.user_id != user_id or s.private_chat_id != query.message.chat.id
            or len(args) not in (2, 3) or args[0] != s.nonce or s.busy):
        await query.answer("Этот экран устарел. Откройте настройки заново.", show_alert=True)
        return
    # Claim before any await. Failed writes release the claim without changing the draft.
    s.busy = True
    committed = False
    try:
        action = args[1]
        if action == "cancel" and len(args) == 2:
            cancel_pending(user_id)
            await query.answer("Отменено")
            await _show(query, await asyncio.to_thread(_list_screen, user_id))
            return
        source = await asyncio.to_thread(state.get_source, s.chat_id)
        legacy = await asyncio.to_thread(state.list_legacy)
        if SESSIONS.get(user_id) is not s:
            await query.answer("Этот экран устарел", show_alert=True)
            return
        if source is None:
            await query.answer("Источник больше недоступен", show_alert=True)
            return
        if not _same_version(s, source):
            await query.answer("Настройки или доступ изменились. Откройте карточку заново.", show_alert=True)
            return
        _, rows = _draft_screen(s, source, legacy)
        if query.data not in {button.callback_data for row in rows for button in row}:
            await query.answer("Недопустимая или устаревшая кнопка", show_alert=True)
            return
        if action in {"save", "off", "history", "clear"}:
            if action == 'clear':
                deleted = await asyncio.to_thread(state.clear_history, s.chat_id,
                    expected_version=s.config_version, expected_generation=s.generation)
            elif action == "history":
                if not source["enabled"] or source["access"] != "ready" or source.get("history_status") not in REPEATABLE:
                    await query.answer("Повтор истории сейчас недоступен", show_alert=True)
                    return
                await asyncio.to_thread(state.request_history, s.chat_id,
                                        expected_version=s.config_version, expected_generation=s.generation)
            else:
                if action == "off" and not source["enabled"]:
                    await query.answer("Источник уже выключен", show_alert=True)
                    return
                if action == "save" and s.group_code is None:
                    await query.answer("Сначала выберите аудиторию", show_alert=True)
                    return
                if s.legacy_chat_id is not None:
                    old = next((row for row in legacy if row["chat_id"] == s.legacy_chat_id), None)
                    if old is None or old.get("linked_chat_id") not in (None, s.chat_id):
                        await query.answer("Старый источник уже недоступен для привязки. Откройте настройки заново.", show_alert=True)
                        return
                await asyncio.to_thread(state.save_configuration, s.chat_id,
                                        s.group_code if action == "save" else source["group_code"],
                                        enabled=action == "save" and s.mode == 'store', expected_version=s.config_version,
                                        expected_generation=s.generation, legacy_chat_id=s.legacy_chat_id)
            committed = True
            if SESSIONS.get(user_id) is s:
                cancel_pending(user_id)
            await query.answer({"save": "Сохранено", "off": "Выключено. Сохранённая история остаётся.",
                                "history": "Загрузка всей доступной истории запрошена",
                                "clear": f"Удалено сообщений: {deleted}" if action == 'clear' else ''}[action])
            current = await asyncio.to_thread(state.get_source, s.chat_id)
            await _show(query, _chat_screen(current) if current else await asyncio.to_thread(_list_screen, user_id))
            return
        if action == "refresh":
            await asyncio.to_thread(state.request_catalog)
            await query.answer("Обновление запрошено. После обновления повторите сохранение; черновик сохранён.", show_alert=True)
            return
        if action == "all":
            s.group_code = groups.ALL
            s.stage = 'mode'
        elif action == "group":
            s.stage = 'groups'
            s.page = 0
        elif action == 'group_pick':
            s.group_code = s.codes[int(args[2])]
            s.stage = 'mode'
        elif action == 'group_page':
            s.page = int(args[2])
        elif action == 'custom':
            s.stage = 'group'
        elif action == 'default':
            s.stage = 'mode_pick'
        elif action == 'mode':
            s.mode = args[2]
            s.stage = 'mode'
        elif action == 'review':
            _after_audience(s, source, legacy)
        elif action == 'noop':
            await query.answer()
            return
        elif action == "legacy":
            value = args[2]
            s.legacy_chat_id = None if value == "none" else int(value)
            s.stage = "review"
        elif action == "page":
            s.page = int(args[2])
        s.nonce = secrets.token_hex(4)
        await query.answer()
        await _show(query, _draft_screen(s, source, legacy))
    except state.SourceUnavailable:
        try:
            await asyncio.to_thread(state.request_catalog)
        except Exception:
            log.warning("MAX catalogue refresh request failed")
            await query.answer("Нет свежего подтверждения доступа. Не удалось запросить обновление; "
                               "черновик сохранён. Повторите позже.", show_alert=True)
        else:
            await query.answer("Нет свежего подтверждения доступа или аккаунт офлайн. Обновление запрошено; "
                               "черновик сохранён. Повторите после обновления.", show_alert=True)
    except (state.ConfigurationConflict, state.SourceNotFound):
        await query.answer("Настройки или доступ изменились. Откройте карточку заново; изменения не сохранены.", show_alert=True)
    except Exception:
        log.warning("MAX draft operation failed for chat %s", s.chat_id)
        if not committed:
            await query.answer("Не удалось завершить операцию. Черновик сохранён; повторите или откройте карточку.", show_alert=True)
    finally:
        s.busy = False


@router.callback_query(F.data.startswith("mx:"))
async def max_sources_callback(query: CallbackQuery) -> None:
    user_id = query.from_user.id
    if not query.message or query.message.chat.type != ChatType.PRIVATE or not await _is_admin(user_id):
        cancel_pending(user_id)
        await query.answer("Только для администратора в личном чате", show_alert=True)
        return
    parts = (query.data or "").split(":")
    if len(parts) < 2:
        await query.answer("Недопустимая кнопка", show_alert=True)
        return
    action, args = parts[1], parts[2:]
    if action == "d":
        await _draft_callback(query, args)
        return
    valid = ((action == "refresh" and not args) or
             (action == "list" and len(args) == 1 and args[0].isascii() and args[0].isdigit() and len(args[0]) <= 9) or
             (action in {"chat", "edit", "off", "history", "adv", "official", "clear"} and len(args) == 1 and ID.fullmatch(args[0])))
    if not valid:
        await query.answer("Недопустимая кнопка", show_alert=True)
        return
    _leave_other_drafts(user_id)
    try:
        notice = None
        if action == "refresh":
            await asyncio.to_thread(state.request_catalog)
            notice = "Обновление запрошено. Его выполнит MAX userbot, когда будет онлайн."
            screen = await asyncio.to_thread(_list_screen, user_id)
        elif action == "list":
            PAGE[user_id] = int(args[0])
            screen = await asyncio.to_thread(_list_screen, user_id)
        else:
            chat_id = int(args[0])
            if not -(2**63) <= chat_id < 2**63:
                await query.answer("Недопустимый идентификатор", show_alert=True)
                return
            source = await asyncio.to_thread(state.get_source, chat_id)
            if source is None:
                await query.answer("Источник больше недоступен", show_alert=True)
                return
            if action == "chat":
                screen = _chat_screen(source)
            elif action == 'adv':
                screen = await asyncio.to_thread(_advanced_screen, source)
            elif action == 'official':
                notice = await asyncio.to_thread(group_settings.official_notice, chat_id)
                screen = await asyncio.to_thread(_advanced_screen, source)
            else:
                if action == "off" and not source["enabled"]:
                    await query.answer("Источник уже выключен", show_alert=True)
                    return
                if action == "history" and (not source["enabled"] or source["access"] != "ready"
                                             or source.get("history_status") not in REPEATABLE):
                    await query.answer("Повтор истории сейчас недоступен", show_alert=True)
                    return
                s = Session(user_id=user_id, private_chat_id=query.message.chat.id, chat_id=chat_id,
                            config_version=source["config_version"], generation=source["generation"],
                            stage={"edit": "audience", "off": "off", "history": "history", "clear": "clear"}[action],
                            legacy_chat_id=source.get("legacy_chat_id"),
                            codes=await asyncio.to_thread(group_settings.known_groups))
                legacy = await asyncio.to_thread(state.list_legacy)
                SESSIONS[user_id] = s
                screen = _draft_screen(s, source, legacy)
        await query.answer(notice)
        await _show(query, screen)
    except Exception:
        log.warning("MAX navigation operation failed")
        await query.answer("Не удалось загрузить настройки MAX. Повторите позже.", show_alert=True)


def _waiting_for_group(message: Message) -> bool:
    if message.from_user and (message.text or "").startswith("/"):
        cancel_pending(message.from_user.id)
        return False
    s = SESSIONS.get(message.from_user.id) if message.from_user else None
    return bool(s and s.stage == "group" and message.text)


@router.message(F.chat.type == ChatType.PRIVATE, F.text, _waiting_for_group)
async def group_code(message: Message) -> None:
    if not message.from_user:
        return
    user_id = message.from_user.id
    if message.chat.type != ChatType.PRIVATE or not await _is_admin(user_id):
        cancel_pending(user_id)
        await message.answer("Только для администратора в личном чате.")
        return
    s = SESSIONS.get(user_id)
    if (s is None or s.user_id != user_id or s.private_chat_id != message.chat.id or s.stage != "group" or s.busy):
        await message.answer("Этот экран устарел. Откройте настройки заново.")
        return
    code = groups.normalize(message.text or "")
    if code is None or code == groups.ALL:
        await message.answer("Введите код учебной группы: латиница, цифры, точка, дефис или подчёркивание, "
                             "до 40 символов. Для общей аудитории выберите «Для всех» в настройках.")
        return
    s.busy = True
    try:
        source = await asyncio.to_thread(state.get_source, s.chat_id)
        legacy = await asyncio.to_thread(state.list_legacy)
        if SESSIONS.get(user_id) is not s:
            return
        if source is None or not _same_version(s, source):
            await message.answer("Настройки или доступ изменились. Откройте карточку заново.")
            return
        s.group_code = code
        s.stage = 'mode'
        s.nonce = secrets.token_hex(4)
        text, rows = _draft_screen(s, source, legacy)
        await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    except Exception:
        log.warning("MAX group prompt failed for chat %s", s.chat_id)
        await message.answer("Не удалось загрузить настройки. Черновик сохранён; повторите ввод.")
    finally:
        s.busy = False
