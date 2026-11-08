"""Client-owned confirmation text, not business validation or authorization."""


def describe_action(name: str, arguments: dict, language: str) -> str:
    """Describe schema-checked arguments without I/O or model-generated prose."""
    a, ru = arguments, language == "ru"
    if name in {"rooms_book_room", "music_book_music_room"}:
        when = f"{a['day']}, {a['time_from']}–{a['time_to']}"
        if name == "music_book_music_room":
            return (f"Забронировать музыкальную комнату (спорткомплекс) на {when}." if ru
                    else f"Book the music room (sports complex) for {when}.")
        return (f"Забронировать аудиторию {a['room_id']} на {when}: «{a['title']}»." if ru
                else f"Book room {a['room_id']} for {when}: “{a['title']}”.")
    if name == "account_cancel_booking":
        music = a["service"] == "music_room"
        if ru:
            return f"Отменить вашу бронь {'музыкальной комнаты' if music else 'аудитории'}: {a['booking_id']}."
        return f"Cancel your {'music room' if music else 'room'} booking: {a['booking_id']}."
    if name == "events_enroll_in_event":
        if ru:
            return f"{'Отменить вашу запись' if a['leave'] else 'Записать вас'} на мероприятие {a['event_id']}."
        return f"{'Cancel your enrolment in' if a['leave'] else 'Enrol you in'} event {a['event_id']}."
    if name == "sport_sport_checkin":
        if ru:
            return f"{'Отменить вашу запись' if a['cancel'] else 'Записать вас'} на тренировку #{a['training_id']}."
        return f"{'Cancel your check-in to' if a['cancel'] else 'Check you in to'} the training #{a['training_id']}."
    if name == "when2meet_create_meeting":
        slots = ", ".join(a["slots"])
        description = a["description"] if a["description"] is not None else ("не задано" if ru else "none")
        if ru:
            return (f"Создать опрос When2Meet «{a['name']}». Часовой пояс: {a['timezone']}. "
                    f"Режим: {'время' if a['specific_time'] else 'даты'}. Слоты: {slots}. Описание: {description}.")
        return (f"Create When2Meet poll “{a['name']}”. Timezone: {a['timezone']}. "
                f"Mode: {'times' if a['specific_time'] else 'dates'}. Slots: {slots}. Description: {description}.")
    if name == "when2meet_set_my_availability":
        if not a["availability"]:
            return (f"Очистить все ваши отмеченные слоты в When2Meet {a['meeting_ref']}." if ru
                    else f"Clear all your marked slots in When2Meet {a['meeting_ref']}.")
        slots = ", ".join(a["availability"])
        return (f"Заменить все ваши отмеченные слоты в When2Meet {a['meeting_ref']} на: {slots}." if ru
                else f"Replace all your marked slots in When2Meet {a['meeting_ref']} with: {slots}.")
    raise ValueError("No confirmation template for this operation.")
