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
    "get_schedule": "🗓 Смотрю расписание…",
    "get_clubs": "🎯 Смотрю клубы…",
    "get_university_events": "📅 Смотрю события…",
    "find_room": "🗺 Ищу на карте…",
    "read_chats": "📜 Читаю последние сообщения чатов…",
}
HELPER_TOOLS = frozenset(name for name in STATUS if name.startswith("ask_"))  # when one of them returns, the answer is written
