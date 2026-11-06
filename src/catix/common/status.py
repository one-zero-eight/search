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
    "ask_account": "👤 Спрашиваю помощника по вашему аккаунту…",
    "search_wiki": "📚 Ищу в документах университета…",
    "read_wiki": "📖 Читаю документ…",
    "search_chats": "🔎 Ищу в базе знаний…",
    "search_userbot_chats": "🔎 Ищу в чатах…",
    "get_schedule": "🗓 Смотрю расписание…",
    "get_clubs": "🎯 Смотрю клубы…",
    "get_university_events": "📅 Смотрю события…",
    "find_room": "🗺 Ищу на карте…",
    "read_chats": "📜 Читаю последние сообщения чатов…",
    "get_courses": "🎓 Смотрю курсы и преподавателей…",
    "get_room_timetable": "🏫 Смотрю занятость аудиторий…",
    "get_music_room_schedule": "🎸 Смотрю расписание музкомнаты…",
    "get_my_schedule": "🗓 Смотрю ваш календарь InNoHassle…",
    "get_free_rooms": "🏫 Ищу свободные аудитории…",
    "book_music_room": "🎸 Готовлю бронь музкомнаты…",
    "book_room": "🏫 Готовлю бронь аудитории…",
    "enroll_in_event": "📅 Готовлю запись на событие…",
    "cancel_booking": "🗑 Готовлю отмену брони…",
    "get_my_ai_calendar": "🗓 Смотрю ваш AI-календарь…",
    "remove_from_ai_calendar": "🗑 Готовлю удаление из календаря…",
    "get_my_sport": "🏃 Смотрю ваши часы спорта…",
    "get_sport_trainings": "🏃 Смотрю тренировки…",
    "get_sports": "🏃 Смотрю виды спорта…",
    "sport_checkin": "🏃 Готовлю запись на тренировку…",
    "search_web": "🌐 Ищу в интернете…",
    "read_web_page": "🌐 Читаю страницу сайта…",
}
HELPER_TOOLS = frozenset(name for name in STATUS if name.startswith("ask_"))  # when one of them returns, the answer is written
