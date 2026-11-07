"""Explicit standalone FastMCP declarations, shared by host policy and server.

The SDK @tool attaches metadata without constructing a server. Business functions
are imported normally from service modules and own their implementations.
"""

from datetime import date, datetime
from typing import Annotated

from fastmcp.tools import tool
from pydantic import Field

from catix.innohassle import actions
from catix.innohassle.mcp_account import (
    account_cancel_booking as account_cancel_booking,
)

# Ordinary re-exports make this the single definition facade.
from catix.innohassle.mcp_account import (
    account_get_my_schedule as account_get_my_schedule,
)
from catix.innohassle.mcp_account import (
    events_enroll_in_event as events_enroll_in_event,
)
from catix.innohassle.mcp_account import (
    music_book_music_room as music_book_music_room,
)
from catix.innohassle.mcp_account import (
    rooms_book_room as rooms_book_room,
)
from catix.innohassle.mcp_account import (
    rooms_get_free_rooms as rooms_get_free_rooms,
)
from catix.innohassle.mcp_campus import (
    music_get_music_room_schedule as music_get_music_room_schedule,
)
from catix.innohassle.mcp_campus import (
    timetable_get_courses as timetable_get_courses,
)
from catix.innohassle.mcp_campus import (
    timetable_get_room_timetable as timetable_get_room_timetable,
)
from catix.innohassle.mcp_declarations import metadata as _metadata
from catix.innohassle.mcp_public import (
    clubs_get_clubs as clubs_get_clubs,
)
from catix.innohassle.mcp_public import (
    events_get_university_events as events_get_university_events,
)
from catix.innohassle.mcp_public import (
    maps_find_room as maps_find_room,
)
from catix.innohassle.mcp_public import (
    schedule_get_schedule as schedule_get_schedule,
)
from catix.innohassle.mcp_sport import (
    sport_get_my_sport as sport_get_my_sport,
)
from catix.innohassle.mcp_sport import (
    sport_get_sport_trainings as sport_get_sport_trainings,
)
from catix.innohassle.mcp_sport import (
    sport_get_sports as sport_get_sports,
)
from catix.innohassle.mcp_sport import (
    sport_sport_checkin as sport_sport_checkin,
)


async def _read(
    function, arguments: dict, path: str, response_model: type[actions.Projection], action_id: str, note: str
) -> dict:
    from catix.innohassle import mcp_server

    def execute(normalized, *, token, sport_token, uid):
        return actions.read(path, response_model, normalized, token, action_id=action_id, note=note)

    return await mcp_server._dispatch(function.__name__, arguments, execute=execute)


@tool(**_metadata("innohassle"))
async def printers_print_get_printers_status() -> actions.ReadResult[actions.PrinterStatus]:
    """Printer availability, paper and toner / Состояние принтеров, бумага и тонер.

    Sign-in required. offline=false means reachable, not ready to print. Null
    percentages mean unknown, not zero. No printing, print jobs or scanning.
    Принтер принтеры печать распечатать бумага тонер картридж состояние доступность.
    """
    result = await _read(
        printers_print_get_printers_status,
        {},
        "/printers/v0/print/get_printers_status",
        actions.PrinterStatus,
        "printers.print_get_printers_status",
        "offline=false only means reachable, not ready to print. Null percentages mean unknown, not zero. "
        "Read-only: printing, print jobs and scanning are not available.",
    )
    return actions.ReadResult[actions.PrinterStatus].model_validate(result)


@tool(**_metadata("public"))
async def maps_scenes_search_areas(query: Annotated[str, Field(min_length=1)]) -> actions.ReadResult[actions.AreaHit]:
    """Find a room, place or printer on the campus map / Найти аудиторию, место или принтер на карте.

    Public read. Location only, not live printer state or room availability.
    English keywords can match English map names.
    """
    result = await _read(
        maps_scenes_search_areas,
        {"query": query},
        "/maps/v0/scenes/areas/search",
        actions.AreaHit,
        "maps.scenes_search_areas",
        "Location only, not live printer state or room availability. English keywords can match English map names.",
    )
    return actions.ReadResult[actions.AreaHit].model_validate(result)


@tool(**_metadata("public"))
async def maps_scenes_scenes() -> actions.ReadResult[actions.Scene]:
    """Campus map scenes floors buildings / Карты кампуса этажи здания. Public read."""
    result = await _read(
        maps_scenes_scenes,
        {},
        "/maps/v0/scenes/",
        actions.Scene,
        "maps.scenes_scenes",
        "Map scenes only; use area search to locate a specific room.",
    )
    return actions.ReadResult[actions.Scene].model_validate(result)


@tool(**_metadata("public"))
async def clubs_get_clubs_list_clubs__get() -> actions.ReadResult[actions.Club]:
    """University clubs hobby community / Университетские клубы кружки объединения.

    Public read. Report truncation; is_active=false means the club is not active.
    """
    result = await _read(
        clubs_get_clubs_list_clubs__get,
        {},
        "/clubs/v0/clubs/",
        actions.Club,
        "clubs.get_clubs_list_clubs__get",
        "Report truncation; is_active=false means the club is not active.",
    )
    return actions.ReadResult[actions.Club].model_validate(result)


@tool(**_metadata("public"))
async def music_bookings_daily_bookings(date: date) -> actions.ReadResult[actions.Booking]:
    """Music room bookings for a day / Занятость музыкальной комнаты за день.

    Public read, occupied slots only. Does not give opening hours. Do not infer
    free slots; use the dedicated music-room domain tools for booking rules.
    """
    result = await _read(
        music_bookings_daily_bookings,
        {"date": date},
        "/music-room/v0/bookings/daily_bookings",
        actions.Booking,
        "music-room.bookings_daily_bookings",
        "Occupied slots only; does not book the music room. Times are local to Innopolis. "
        "The response does not give opening hours. Do not infer free slots: report the occupied intervals only.",
    )
    return actions.ReadResult[actions.Booking].model_validate(result)


@tool(**_metadata("public"))
async def events_events_list_events(
    from_: Annotated[datetime | None, Field(alias="from")] = None,
    to: datetime | None = None,
    club: int | None = None,
) -> actions.ReadResult[actions.Event]:
    """Published university events lectures workshops / Мероприятия университета события лекции.

    Public read. Optional from/to date-time range; defaults to the current month.
    No enrolment or participant data.
    """
    result = await _read(
        events_events_list_events,
        {"from": from_, "to": to, "club": club},
        "/events/v1/events/",
        actions.Event,
        "events.events_list_events",
        "Published events; optional from/to date-time range. Defaults to the current month. No enrolment or participant data.",
    )
    return actions.ReadResult[actions.Event].model_validate(result)
