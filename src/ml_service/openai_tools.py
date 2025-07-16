BOOK_MUSIC_ROOM_FN = {
    "type": "function",
    "function": {
        "name": "book_music_room",
        "description": (
            "Book a music room via InNoHassle SSO: checks availability and immediately finalizes the booking."
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
