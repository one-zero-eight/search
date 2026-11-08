"""What the user is told while the agent works on a question: the Telegram bot shows it in a draft, the API sends it as
`status` events."""

QUEUED = "⏳ Отвечаю на другие вопросы, ваш в очереди. Перед вами: {ahead}"
CHECKING = "🛡 Проверяю запрос…"
WRITING = "✍️ Формулирую ответ…"
# The status of a tool while it runs, between the model deciding to call it and the answer starting.
STATUS = {
    "ask_chats": "💬 Спрашиваю помощника по чатам…",
    "ask_campus": "🧭 Спрашиваю помощника по кампусу…",
    "ask_docs": "📚 Спрашиваю помощника по документам…",
    "search_wiki": "📚 Ищу в документах университета…",
    "read_wiki": "📖 Читаю документ…",
    "search_chats": "🔎 Ищу в базе знаний…",
    "search_userbot_chats": "🔎 Ищу в чатах…",
    "read_chats": "📜 Читаю последние сообщения чатов…",
    "search_api_tools": "🔎 Ищу подходящий инструмент…",
    "call_api_tool": "🔧 Обращаюсь к сервису…",
    "get_my_ai_calendar": "🗓 Смотрю ваш AI-календарь…",
    "get_my_schedule": "🗓 Смотрю ваше расписание и личные события…",
    "get_my_available_trainings": "🏃 Подбираю тренировки без пересечений…",
    "get_my_available_music_windows": "🎵 Подбираю время в музкомнате без пересечений…",
    "get_my_available_rooms": "🚪 Проверяю доступные комнаты и ваше расписание…",
    "get_my_available_meeting_slots": "👥 Проверяю варианты встречи по вашему расписанию…",
    "read_attachment": "📄 Читаю прикреплённый файл…",
    "view_attachment": "🖼 Рассматриваю изображение или страницу…",
    "add_to_ai_calendar": "🗓 Готовлю добавление в календарь…",
    "update_ai_calendar": "🗓 Готовлю изменение календаря…",
    "remove_from_ai_calendar": "🗑 Готовлю удаление из календаря…",
    "search_web": "🌐 Ищу в интернете…",
    "read_web_page": "🌐 Читаю страницу сайта…",
}
HELPER_TOOLS = frozenset(name for name in STATUS if name.startswith("ask_"))  # when one of them returns, the answer is written
