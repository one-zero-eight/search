"""Client-owned names and credential routing, independent of server implementations.

This is not a business-operation registry: no schemas, endpoints or callables live
here. Only these concrete mutations trigger host consent. Server validation and
user authorization remain separate from that user-interface decision.
"""

from types import MappingProxyType

CONFIRMATION_TOOLS = frozenset({
    "rooms_book_room",
    "music_book_music_room",
    "account_cancel_booking",
    "events_enroll_in_event",
    "sport_sport_checkin",
    "when2meet_create_meeting",
    "when2meet_set_my_availability",
})

CREDENTIAL_MODES = MappingProxyType({
    "schedule_get_schedule": "public",
    "timetable_get_courses": "public",
    "timetable_get_instructor_schedule": "public",
    "timetable_get_room_timetable": "public",
    "maps_find_room": "public",
    "clubs_get_clubs": "public",
    "events_get_university_events": "public",
    "music_get_music_room_schedule": "public",
    "maps_scenes_search_areas": "public",
    "maps_scenes_scenes": "public",
    "clubs_get_clubs_list_clubs__get": "public",
    "music_bookings_daily_bookings": "public",
    "events_events_list_events": "public",
    "printers_print_get_printers_status": "innohassle",
    "account_get_my_schedule": "innohassle",
    "rooms_get_free_rooms": "innohassle",
    "rooms_book_room": "innohassle",
    "music_get_available_windows": "innohassle",
    "music_book_music_room": "innohassle",
    "account_cancel_booking": "innohassle",
    "events_enroll_in_event": "innohassle",
    "sport_get_my_sport": "sport",
    "sport_get_sport_trainings": "sport",
    "sport_get_sports": "sport",
    "sport_sport_checkin": "sport",
    "when2meet_get_my_meetings": "innohassle",
    "when2meet_get_meeting": "innohassle",
    "when2meet_create_meeting": "innohassle",
    "when2meet_set_my_availability": "innohassle",
})

READ_TOOLS = frozenset(CREDENTIAL_MODES) - CONFIRMATION_TOOLS
