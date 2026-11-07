"""Multiple reviewed OpenAPI services stay separate in version, authorization and response policy."""

from copy import deepcopy

import httpx
import pytest

from catix.innohassle import actions


def spec(path, properties, *, parameters=()):
    return {"openapi": "3.1.0", "info": {"title": "Service", "version": "1"}, "paths": {path: {"get": {
        "operationId": "list", "parameters": list(parameters),
        "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {
            "type": "array", "items": {"type": "object", "properties": properties}
        }}}}},
    }}}}


@pytest.fixture
def service_api(monkeypatch):
    seen = []
    docs = {
        "/maps/v0/openapi.json": spec("/scenes/areas/search", {
            "scene_id": {"type": "string"},
            "area": {"type": "object", "properties": {k: {"type": ["string", "null"]} for k in ("title", "ru_title", "description")}},
        }, parameters=[{"name": "query", "in": "query", "required": True, "schema": {"type": "string", "minLength": 1}}]),
        "/events/v1/openapi.json": spec("/events/", {
            "id": {"type": "string"}, "data": {"type": "object", "properties": {
                "name": {"type": ["string", "null"]}, "starts_at": {"type": "string", "format": "date-time"},
                "duration_hours": {"type": "number"},
                "location": {"type": "object", "properties": {"display_name": {"type": "string"}}},
            }},
        }, parameters=[{"name": name, "in": "query", "schema": {"type": "string", "format": "date-time"}} for name in ("from", "to")]),
    }
    bodies = {
        "/maps/v0/scenes/areas/search": [{"scene_id": "floor3", "area": {"title": "301", "ru_title": "301", "description": None,
                                                                           "people": ["do not expose"]}}],
        "/events/v1/events/": [{"id": "e1", "creator_id": "private", "data": {"name": "Lecture", "starts_at": "2026-11-08T15:00:00+03:00",
                                                                                  "duration_hours": 1.5, "location": {"display_name": "108"}}}],
    }

    def handle(request):
        seen.append(request)
        assert request.method == "GET"
        assert "authorization" not in request.headers and "cookie" not in request.headers
        if request.url.path in docs:
            return httpx.Response(200, json=docs[request.url.path])
        return httpx.Response(200, json=bodies[request.url.path])

    with httpx.Client(base_url="https://api.innohassle.ru", transport=httpx.MockTransport(handle)) as client:
        monkeypatch.setattr(actions, "_client", client)
        yield seen, docs, bodies


def test_public_maps_never_receive_even_an_available_user_token(service_api):
    result = actions.execute("maps.scenes_search_areas", {"query": "301"}, "must-not-forward")
    assert result["data"] == [{"scene_id": "floor3", "area": {"title": "301", "ru_title": "301", "description": None}}]
    assert "people" not in str(result)
    assert actions.describe("maps.scenes_search_areas")["requires_sign_in"] is False


def test_events_use_their_own_v1_schema_and_query_names(service_api):
    params = {"from": "2026-11-08T00:00:00+03:00", "to": "2026-11-09T00:00:00+03:00"}
    result = actions.execute("events.events_list_events", params, None)
    seen, _, _ = service_api
    assert [r.url.path for r in seen] == ["/events/v1/openapi.json", "/events/v1/events/"]
    assert dict(seen[-1].url.params) == params
    assert result["data"][0]["data"]["name"] == "Lecture" and "creator_id" not in str(result)


def test_catalogue_contains_only_reviewed_reads_and_no_moodle():
    assert {a.service for a in actions.ACTIONS.values()} == {"maps", "clubs", "music-room", "events", "printers"}
    assert all(a.method == "GET" for a in actions.ACTIONS.values())
    assert all(a.requires_token == (a.service == "printers") for a in actions.ACTIONS.values())


def test_music_bookings_do_not_claim_availability_outside_the_returned_intervals():
    note = actions.ACTIONS["music-room.bookings_daily_bookings"].note
    assert "opening hours" in note and "Do not infer free slots" in note


def test_invalid_datetime_is_rejected_before_network_execution(service_api):
    with pytest.raises(actions.ActionError, match="Invalid API parameters"):
        actions.execute("events.events_list_events", {"from": "tomorrow"}, None)
    assert [r.url.path for r in service_api[0]] == ["/events/v1/openapi.json"]


def test_nullable_optional_query_values_are_omitted_not_sent_as_empty_strings(service_api):
    seen, docs, _ = service_api
    params = docs["/events/v1/openapi.json"]["paths"]["/events/"]["get"]["parameters"]
    for item in params:
        item["schema"] = {"anyOf": [item["schema"], {"type": "null"}]}
    actions.execute("events.events_list_events", {"from": None, "to": None}, None)
    assert not seen[-1].url.query
