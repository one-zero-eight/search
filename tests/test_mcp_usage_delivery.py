"""Per-service rules ride with the tool (`usage` of a search result), not in the always-on supervisor prompt (MCP_RULES)."""

import asyncio
import re

import pytest

from catix.agent import roles
from tests.mcp_native_helpers import connection, registered_tools


HOST_TOOLS = {"get_my_schedule", "search_api_tools", "call_api_tool"}


def _search(query: str) -> dict[str, dict]:
    async def run():
        async with connection(token="alice", sport_token="sport-alice") as client:
            return (await client.call_tool("search_tools", {"query": query})).data
    return {item["name"]: item for item in asyncio.run(run())}


@pytest.mark.parametrize("query, tool, moved", [
    ("принтер бумага", "printers_print_get_printers_status", ["cannot print files", "cancel print jobs", "scan", "location"]),
    ("music room free window", "music_get_available_windows", ["never a classroom", "music_get_music_room_schedule"]),
    ("music room free window", "music_get_music_room_schedule", ["never a classroom", "music_get_available_windows"]),
    ("book music room", "music_book_music_room", ["never a classroom", "HH:MM"]),
    ("sport trainings", "sport_get_my_sport", ["hours", "medical group", "check-ins"]),
    ("sport trainings", "sport_get_sports", ["trainers", "sport_get_my_sport"]),
    ("map room location", "maps_find_room", ["location only", "printers_print_get_printers_status", "English"]),
    ("who teaches course", "timetable_get_courses", ["search_wiki", "term"]),
    ("group timetable", "schedule_get_schedule", ["get_my_schedule", "fallback"]),
    ("room free of classes", "timetable_get_room_timetable", ["rooms_get_free_rooms", "not a classroom"]),
    ("events enroll", "events_get_university_events", ["English", "enrol"]),
    ("when2meet", "when2meet_get_my_meetings", ["when2meet_get_meeting"]),
    ("when2meet", "when2meet_set_my_availability", ["+03:00"]),
])
def test_a_moved_rule_arrives_with_the_search_result_of_its_tool(query, tool, moved):
    found = _search(query)
    assert tool in found, f"{tool} is not among the matches of {query!r}: {list(found)}"
    usage = found[tool]["usage"]
    for part in moved:
        assert part.lower() in usage.lower(), f"{part!r} missing from the usage of {tool}: {usage}"


@pytest.mark.parametrize("query, tool", [
    ("принтер бумага", "printers_print_get_printers_status"),
    ("музыкальная комната свободно", "music_get_available_windows"),
    ("тренировки по плаванию", "sport_get_sport_trainings"),
    ("аудитория свободна", "rooms_get_free_rooms"),
    ("расписание группы", "schedule_get_schedule"),
    ("клубы", "clubs_get_clubs"),
    ("мероприятия", "events_get_university_events"),
])
def test_russian_words_still_find_the_tool_by_its_description(query, tool):
    # `usage` is not indexed: the words one searches by must stay in the description.
    assert tool in _search(query)


def test_the_prompt_keeps_the_routing_map_and_the_confusable_pairs_but_not_the_moved_rules():
    rules = roles.MCP_RULES
    tools = set(registered_tools())
    named = set(re.findall(r"\b[a-z0-9]+(?:_[a-z0-9]+)+\b", rules)) - HOST_TOOLS
    assert named <= tools, f"unknown tool names in the prompt: {sorted(named - tools)}"
    # routing: one name per service
    for name in ("schedule_get_schedule", "timetable_get_instructor_schedule", "timetable_get_courses",
                 "timetable_get_room_timetable", "rooms_get_free_rooms", "music_get_available_windows",
                 "music_get_music_room_schedule", "maps_find_room", "clubs_get_clubs", "events_get_university_events",
                 "sport_get_my_sport", "sport_get_sport_trainings", "sport_get_sports", "when2meet_get_my_meetings",
                 "when2meet_get_meeting", "printers_print_get_printers_status", "get_my_schedule"):
        assert name in rules
    assert "search_api_tools" in rules and "call_api_tool" in rules
    # confusable pairs are told apart in the line itself
    room = next(line for line in rules.split("  - ") if "timetable_get_room_timetable" in line)
    assert "rooms_get_free_rooms" in room and "music_get_available_windows" in room and "never a classroom" in room
    agenda = next(line for line in rules.split("  - ") if "get_my_schedule" in line and "schedule_get_schedule" in line)
    assert "own agenda" in agenda
    maps = next(line for line in rules.split("  - ") if "maps_find_room" in line)
    assert "location only" in maps and "printers_print_get_printers_status" in maps
    # moved to the tools' `usage`
    for moved in ("print files", "cancel print jobs", "free windows", "occupied intervals", "trainers", "how to enrol",
                  "labelled partial fallback"):
        assert moved not in rules
    assert roles.SUPERVISOR.endswith(rules)


def test_every_write_tool_needs_approval_in_the_prompt_and_timeouts_are_not_repeated():
    writes = {name for name, tool in registered_tools().items() if tool.annotations.read_only_hint is False}
    approved = set(re.findall(r"\b[a-z0-9]+(?:_[a-z0-9]+)+\b", roles.MCP_RULES.split("Mutations")[1].split("A write")[0])) - HOST_TOOLS
    assert writes == approved
    assert "never repeat it" in " ".join(roles.MCP_RULES.split())
    assert "RFC 3339" in roles.MCP_RULES and "HH:MM" in roles.MCP_RULES
