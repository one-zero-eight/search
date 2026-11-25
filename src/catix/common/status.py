"""What the user is told while the agent works on a question: the Telegram bot shows it in a draft, the API sends it as
`status` events."""

CHECKING = "🛡 Проверяю запрос…"
WRITING = "✍️ Формулирую ответ…"
# The status of a tool while it runs, between the model deciding to call it and the answer starting.
STATUS = {
    "search": "🔎 Ищу в документах, чатах и материалах курсов…",
    "read_wiki": "📖 Читаю документ…",
    "read_chats": "📜 Читаю последние сообщения чатов…",
    "search_api_tools": "🔎 Ищу подходящий инструмент…",
    "call_api_tool": "🔧 Обращаюсь к сервису…",
    "get_my_ai_calendar": "🗓 Смотрю ваш AI-календарь…",
    "get_my_schedule": "🗓 Смотрю ваше расписание и личные события…",
    "read_attachment": "📄 Читаю прикреплённый файл…",
    "add_to_ai_calendar": "🗓 Готовлю добавление в календарь…",
    "update_ai_calendar": "🗓 Готовлю изменение календаря…",
    "remove_from_ai_calendar": "🗑 Готовлю удаление из календаря…",
    "search_web": "🌐 Ищу в интернете…",
    "read_web_page": "🌐 Читаю страницу сайта…",
    "get_my_moodle": "🎓 Смотрю ваши данные Moodle…",
}
SEARCH_TOOLS = frozenset({"search"})  # when it returns, the answer is written
