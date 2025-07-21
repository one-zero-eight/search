BOOK_MUSIC_ROOM_FN = {
    "type": "function",
    "function": {
        "name": "book_music_room",
        "description": (
            "Use this function when the user wants to book a music room.(for example: book from 14:00 to 16:00)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "start_datetime": {
                    "type": "string",
                    "format": "date-time",
                    "description": "Booking start",
                },
                "end_datetime": {
                    "type": "string",
                    "format": "date-time",
                    "description": "Booking end",
                },
            },
            "required": ["start_datetime", "end_datetime"],
        },
    },
}


CANCEL_BOOKING_FN = {
    "type": "function",
    "function": {
        "name": "cancel_booking",
        "description": (
            "Use this function when the user wants to delete or cancel a music room booking."
            "(for example: delete the booking for tomorrow at 11:00). "
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "time_start": {
                    "type": "string",
                    "format": "date-time",
                    "description": "Booking start",
                }
            },
            "required": ["time_start"],
        },
    },
}


LIST_MY_BOOKINGS_FN = {
    "type": "function",
    "function": {
        "name": "list_my_bookings",
        "description": (
            "Use this function when the user asks to view or show all their bookings."
            "(for example: what bookings do I have, show me the bookings for tomorrow)."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}
