"""Shared group selection, official marks and history-clear presentation."""

import html
from collections.abc import Callable

from aiogram.types import InlineKeyboardButton

from catix import groups, official
from catix.db import pg

Keyboard = list[list[InlineKeyboardButton]]
PAGE_SIZE = 8


def known_groups() -> list[str]:
    """Return all first, then codes in use ordered by popularity and code."""
    with pg.connection() as conn:
        used = pg.column(conn, "SELECT group_code FROM chats WHERE group_code <> %s GROUP BY 1 ORDER BY count(*) DESC, 1", (groups.ALL,))
    return [groups.ALL, *used]


def group_picker(
    title: str,
    current: str,
    codes: list[str],
    page: int,
    button: Callable[[str, str, str], InlineKeyboardButton],
) -> tuple[str, Keyboard]:
    """Present known codes with caller-owned callbacks and cancellation."""
    pages = max(1, (len(codes) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, pages - 1))
    rows = [[button(code, "group", str(i))] for i, code in enumerate(codes)
            if page * PAGE_SIZE <= i < (page + 1) * PAGE_SIZE]
    nav = []
    if page:
        nav.append(button("◀", "page", str(page - 1)))
    nav.append(button(f"{page + 1}/{pages}", "noop", ""))
    if page < pages - 1:
        nav.append(button("▶", "page", str(page + 1)))
    rows.extend([nav, [button("🎓 Другая группа…", "custom", "")]])
    return f"<b>{html.escape(title)}</b>\nУчебная группа: {html.escape(current)}", rows


def official_notice(chat_id: int) -> str:
    """Toggle the existing chat's official mark and confirm persisted state."""
    value = not official.flags([chat_id]).get(chat_id, False)
    official.set_official(chat_id, value)
    if official.flags([chat_id]).get(chat_id, False) != value:
        return "Не удалось подтвердить изменение отметки."
    return "Чат отмечен официальным: его сообщения можно называть официальными" if value else "Отметка «официальный» снята"


def clear_text(title: str, stored: int, changes: int, enabled: bool) -> str:
    """Describe irreversible content deletion without changing chat policy."""
    return (
        f"Удалить все <b>{stored}</b> сообщений чата «{html.escape(title)}» и их эмбеддинги? Это необратимо.\n"
        + (f"Вместе с ними удалятся найденные в них изменения расписания: {changes}.\n" if changes else "")
        + "Сам чат, его учебная группа и выбор «слушать» остаются. "
        + ("Пока чат включён, новые сообщения продолжат сохраняться." if enabled else "")
    ).strip()
