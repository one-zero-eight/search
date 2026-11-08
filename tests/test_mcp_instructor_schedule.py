"""Dated instructor classes through registered public MCP tools."""

from copy import deepcopy

import pytest

from catix.innohassle import client as backend
from tests.mcp_native_helpers import call, registered_tools
from tests.test_timetable import DATA

NAME = "timetable_get_instructor_schedule"
ARGS = {"instructor": "Зуев", "date_from": "2026-11-02", "date_to": "2026-11-10"}
TEACHER = "e.zuev@innopolis.ru"


@pytest.fixture
def source(monkeypatch):
    data = deepcopy(DATA)
    requests = []
    monkeypatch.setattr(backend, "timetable", lambda: requests.append("/timetable") or data)
    return data, requests


def test_dated_instructor_classes_use_actual_assignments_not_course_staff(source):
    assert NAME in registered_tools()
    result = call(NAME, ARGS)
    assert source[1] == ["/timetable"]
    assert result["instructor"] == {
        "id": TEACHER, "name": "Evgeny Zuyev", "name_ru": "Зуев Евгений Александрович",
    }
    assert result["range"] == ["2026-11-02", "2026-11-10"]
    assert result["timezone"] == "Europe/Moscow"
    assert result["total"] == 2
    assert result["classes"] == [
        {"date": "2026-11-02", "start": "09:00", "end": "10:30", "course": "Compiler Construction",
         "kind": "lecture", "room": "108", "groups": ["B24-CSE-01"]},
        {"date": "2026-11-10", "start": "12:40", "end": "14:10", "course": "Compiler Construction",
         "kind": "lab", "room": "313", "groups": ["B24-CSE-01"], "notes": "extra lab"},
    ]
    assert result["days"][0] == {
        "date": "2026-11-02", "class_count": 1, "first_class_start": "09:00", "last_class_end": "10:30",
    }
    assert result["days"][7] == {
        "date": "2026-11-09", "class_count": 0, "first_class_start": None, "last_class_end": None,
    }
    assert "personal meetings" in result["note"]
    assert "free time" in result["note"]


def test_same_surname_requires_selection_but_exact_id_or_full_name_resolves(source):
    data, _ = source
    data["instructors"].append({"id": "other", "name_en": "Alex Zuyev", "name_ru": "Зуев Алексей"})
    ambiguous = call(NAME, ARGS)
    assert ambiguous["code"] == "ambiguous_instructor"
    assert {p["id"] for p in ambiguous["candidates"]} == {TEACHER, "other"}
    assert "classes" not in ambiguous
    for query in (TEACHER, "Evgeny Zuyev", "Зуев Евгений Александрович", "@zouev"):
        assert call(NAME, {**ARGS, "instructor": query})["instructor"]["id"] == TEACHER
    missing = call(NAME, {**ARGS, "instructor": "Nobody"})
    assert missing["code"] == "instructor_not_found"
    assert "classes" not in missing


@pytest.mark.parametrize("changes", [
    {"instructor": "   "}, {"instructor": "@!"},
    {"date_from": "2026-11-10", "date_to": "2026-11-02"},
    {"date_from": "2026-11-01", "date_to": "2026-12-02"},
])
def test_invalid_ranges_and_empty_search_do_not_read_upstream(source, changes):
    from fastmcp.exceptions import ToolError

    try:
        result = call(NAME, {**ARGS, **changes})
    except ToolError:
        pass
    else:
        assert "error" in result
    assert source[1] == []


def test_exactly_31_inclusive_days_are_returned_without_clamping(source):
    result = call(NAME, {**ARGS, "date_from": "2026-11-01", "date_to": "2026-12-01"})
    assert result["range"] == ["2026-11-01", "2026-12-01"]
    assert len(result["days"]) == 31
    assert result["days"][0]["date"] == "2026-11-01"
    assert result["days"][-1]["date"] == "2026-12-01"
    assert result["total"] == len(result["classes"])
    assert source[1] == ["/timetable"]


def test_dates_outside_published_term_are_unknown_not_empty_schedule(source):
    result = call(NAME, {**ARGS, "date_from": "2027-01-01", "date_to": "2027-01-01"})
    assert result["code"] == "outside_published_term"
    assert result["term"]["semester"] == DATA["term"]["semester"]
    assert "classes" not in result


def test_unavailable_or_malformed_source_does_not_become_empty(source, monkeypatch):
    from fastmcp.exceptions import ToolError

    for data in ({}, {"term": {}}, {"term": DATA["term"], "instructors": DATA["instructors"]}):
        monkeypatch.setattr(backend, "timetable", lambda: data)
        result = call(NAME, ARGS)
        assert "error" in result and "classes" not in result
    def unavailable():
        raise RuntimeError("source unavailable")
    monkeypatch.setattr(backend, "timetable", unavailable)
    with pytest.raises(ToolError):
        call(NAME, ARGS)


@pytest.mark.parametrize("empty", [False, True])
def test_host_accepts_dated_read_and_valid_empty_result(source, empty):
    from catix.agent import core
    from catix.innohassle.mcp_access import CREDENTIAL_MODES, READ_TOOLS
    from tests.test_main_mcp_routing import mixed_read_messages

    assert CREDENTIAL_MODES.get(NAME) == "public" and NAME in READ_TOOLS
    day = "2026-11-03" if empty else "2026-11-02"
    payload = call(NAME, {**ARGS, "date_from": day, "date_to": day})
    assert core._read_parts(NAME, payload) == (payload["classes"],)
    messages = mixed_read_messages(NAME, payload)
    assert core.successful_read(messages)
    assert core.read_evidence(messages) is not empty
    assert core.final_answer(messages, {}) == messages[-1].text


@pytest.mark.parametrize("changes", [
    {"instructor": None}, {"instructor": {}}, {"range": ["2026-02-30", "2026-11-02"]},
    {"total": True}, {"total": 0}, {"total": 20}, {"classes": None}, {"classes": [{}]},
    {"classes": [{"date": "2026-11-02", "course": "X", "start": "25:00", "end": "26:00"}], "total": 1},
])
def test_host_rejects_malformed_schedule_envelopes(source, changes):
    from catix.agent import core

    payload = call(NAME, ARGS)
    assert core._read_parts(NAME, payload) is not None
    assert core._read_parts(NAME, {**payload, **changes}) is None
    assert core._read_parts(NAME, {"term": {}, "courses": []}) is None


def test_instructor_schedule_discovery_and_shared_guidance():
    import asyncio
    from catix.agent import roles
    from tests.mcp_native_helpers import connection

    async def check():
        async with connection() as client:
            directory = (await client.call_tool("service_status", {})).data
            assert NAME in directory["timetable"]["tool_names"]
            for query in (NAME, "расписание преподавателя", "где у преподавателя пары завтра",
                          "когда заканчиваются занятия в пятницу", "instructor schedule rooms last class"):
                matches = (await client.call_tool("search_tools", {"query": query})).data
                assert NAME in [item["name"] for item in matches], (query, matches)
            operation = registered_tools()[NAME]
            assert operation.annotations.read_only_hint
            assert set(operation.parameters["required"]) == {"instructor", "date_from", "date_to"}
            assert operation.parameters["properties"]["date_from"]["format"] == "date"
    asyncio.run(check())
    assert NAME in roles.MCP_RULES
    assert "personal meetings" in roles.MCP_RULES


def test_co_teaching_and_substitution_use_occurrence_instructors(source):
    data, _ = source
    pattern = data["courses"][0]["components"][0]["sessions"][0]["weekly_pattern"][0]
    pattern["instructor"] = [TEACHER, "other"]
    assert call(NAME, ARGS)["total"] == 2
    pattern["edits"] = [{"select_week": "2026-11-02", "instructor": "other"}]
    assert [row["date"] for row in call(NAME, ARGS)["classes"]] == ["2026-11-09", "2026-11-10"]
    room = call("timetable_get_room_timetable", {"room": "108", "day": "2026-11-09"})
    assert room["classes"][0]["instructor"] == "Evgeny Zuyev, other"


def test_last_class_end_is_latest_end_not_last_start(source):
    data, _ = source
    series = data["courses"][0]["components"][1]["sessions"][0]
    series["dates_pattern"] = [
        {"date": "2026-11-02", "start_time": "09:00:00", "end_time": "16:00:00",
         "room": "ONLINE", "instructor": TEACHER},
        {"date": "2026-11-02", "start_time": "11:00:00", "end_time": "12:00:00",
         "room": None, "instructor": TEACHER},
    ]
    result = call(NAME, {**ARGS, "date_to": "2026-11-02"})
    assert result["days"][0]["last_class_end"] == "16:00"
    assert result["classes"][-1]["room"] is None
    assert result["classes"][1]["room"] == "ONLINE"


def test_http_direct_and_generic_are_anonymous_public_reads(monkeypatch):
    import asyncio
    import httpx
    from catix.innohassle import mcp_server
    from tests.mcp_native_helpers import connection

    # Bypass caching so every allowed control and rejected call is observable.
    monkeypatch.setattr(backend.cache, "cached", lambda key, ttl, load: load())
    seen = []
    def reply(request):
        seen.append(request)
        assert request.method == "GET" and request.url.path == "/schedule-assistant/v0/timetable"
        assert not request.url.query
        assert not {"authorization", "cookie", "x-innohassle-token", "x-sport-token"} & request.headers.keys()
        return httpx.Response(200, json=DATA)

    monkeypatch.setattr(mcp_server.token_verifier, "claims", lambda token: {"uid": "synthetic"})
    async def run():
        for signed_in in (False, True):
            async with connection(remote=True, token="synthetic-ih" if signed_in else None,
                                  sport_token="synthetic-sport" if signed_in else None) as client:
                for generic in (False, True):
                    result = await client.call_tool("call_tool" if generic else NAME,
                        {"name": NAME, "arguments": ARGS} if generic else ARGS)
                    assert result.data["total"] == 2
                    before = len(seen)
                    for bad in (
                        {k: v for k, v in ARGS.items() if k != "date_to"},
                        {**ARGS, "instructor": False}, {**ARGS, "instructor": ""},
                        {**ARGS, "date_from": "2026-02-30"}, {**ARGS, "date_from": 0},
                        {**ARGS, "date_from": "2026-11-02T00:00:00Z"},
                        {**ARGS, "date_to": "2026-11-01"}, {**ARGS, "date_to": "2027-01-01"},
                        {**ARGS, "token": "injected"}, {**ARGS, "url": "https://other.invalid"},
                    ):
                        refused = await client.call_tool("call_tool" if generic else NAME,
                            {"name": NAME, "arguments": bad} if generic else bad, raise_on_error=False)
                        assert refused.is_error or "error" in refused.data
                    assert len(seen) == before
    with backend._http_client("https://public.invalid", transport=httpx.MockTransport(reply)) as http:
        monkeypatch.setattr(backend, "_client", http)
        asyncio.run(run())
    assert len(seen) == 4
