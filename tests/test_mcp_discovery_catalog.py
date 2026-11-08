"""Compact tool discovery must not hide the existence of registered capabilities."""
import asyncio

import pytest
from fastmcp import Client

from catix.innohassle import mcp_server
from tests.mcp_native_helpers import registered_tools, input_schema


def test_search_uses_one_compact_format_without_losing_argument_constraints():
    async def run():
        async with mcp_server.adapter() as root, Client(root) as client:
            tools = (await client.call_tool("search_tools", {"query": "rooms_get_free_rooms"})).data
            assert tools
            for item in tools:
                assert set(item) == {"name", "description", "inputSchema"}
                assert item["inputSchema"] == input_schema(item["name"])
            rooms = next(item for item in tools if item["name"] == "rooms_get_free_rooms")
            assert set(rooms["inputSchema"]["required"]) == {"time_from", "time_to"}
            assert "pattern" in rooms["inputSchema"]["properties"]["time_from"]

    asyncio.run(run())


@pytest.mark.parametrize("name", sorted(registered_tools()))
def test_exact_name_search_includes_every_registered_tool_with_input_schema(name):
    async def run():
        async with mcp_server.adapter() as root, Client(root) as client:
            matches = (await client.call_tool("search_tools", {"query": name})).data
            by_name = {item["name"]: item for item in matches}
            assert name in by_name, list(by_name)
            tool = by_name[name]
            assert set(tool) == {"name", "description", "inputSchema"}
            assert tool["inputSchema"] == input_schema(name)

    asyncio.run(run())


@pytest.mark.parametrize("query,target", [
    ("room booking availability", "rooms_get_free_rooms"),
    ("отменить бронь аудитории", "account_cancel_booking"),
    ("расписание музыкальной комнаты", "music_get_music_room_schedule"),
    ("записаться на тренировку", "sport_sport_checkin"),
    ("printer paper toner status", "printers_print_get_printers_status"),
])
def test_five_distinct_intents_find_their_tool_first(query, target):
    async def run():
        async with mcp_server.adapter() as root, Client(root) as client:
            matches = (await client.call_tool("search_tools", {"query": query})).data
            assert matches and matches[0]["name"] == target, [item["name"] for item in matches]

    asyncio.run(run())


@pytest.mark.parametrize("query", ["booking room reservation", "room booking tool", "booking room", "room booking"])
def test_trace_paraphrases_include_availability_and_booking(query):
    async def run():
        async with mcp_server.adapter() as root, Client(root) as client:
            matches = (await client.call_tool("search_tools", {"query": query})).data
            assert {"rooms_get_free_rooms", "rooms_book_room"} <= {item["name"] for item in matches}

    asyncio.run(run())


def test_catalogue_keeps_every_concrete_name_visible_when_search_has_no_matches():
    async def run():
        async with mcp_server.adapter() as root, Client(root) as client:
            assert (await client.call_tool("search_tools", {"query": "unmatchedxyz987"})).data == []
            services = (await client.call_tool("service_status", {})).data
            names = [name for service in services.values() for name in service["tool_names"]]
            assert len(names) == len(set(names)) == len(registered_tools())
            assert set(names) == set(registered_tools())
            assert {"rooms_get_free_rooms", "rooms_book_room"} <= set(services["rooms"]["tool_names"])
            assert all(service["tools"] == len(service["tool_names"]) for service in services.values())
            assert not {"preview_tool", "service_status", "call_tool", "search_tools"} & set(names)

    asyncio.run(run())
