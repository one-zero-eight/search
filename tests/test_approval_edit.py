"""What the user may change in an action waiting for approval: the form, and how a change becomes the action to run."""

from types import SimpleNamespace

import pytest

from catix.agent import approval_edit
from catix.agent.approval_edit import InvalidEdit, edit, fields
from catix.api import ask
from catix.api.schemas import ActionEdit

BOOKING = {"room_id": "su-office", "day": "2099-01-01", "title": "Planning", "time_from": "10:00", "time_to": "12:00"}
CALENDAR = {"title": "Meeting", "day": "2099-01-01", "start_time": "15:00", "end_time": "16:00", "all_day": False, "room": "108"}
FEEDBACK = {"subject": "catix", "feedback": "More chats, please"}
SCHEMA = {"type": "object", "required": ["room_id", "day", "title", "time_from", "time_to"],
          "properties": {key: {"type": "string"} for key in BOOKING}}


def _shown(form):
    return {field["name"]: field["value"] for field in form}


def test_a_room_booking_offers_its_editable_arguments_with_current_values():
    form = fields("call_api_tool", {"name": "rooms_book_room", "arguments": BOOKING})
    assert [(f["name"], f["kind"], f["required"]) for f in form] == [
        ("title", "text", True), ("day", "date", True), ("time_from", "time", True), ("time_to", "time", True)]
    assert _shown(form) == {"title": "Planning", "day": "2099-01-01", "time_from": "10:00", "time_to": "12:00"}
    assert fields("call_api_tool", {"name": "unknown_operation", "arguments": BOOKING}) == []


def test_a_calendar_event_offers_its_fields_and_an_all_day_event_only_the_date_part():
    form = fields("add_to_ai_calendar", CALENDAR)
    assert [f["name"] for f in form] == ["title", "day", "start_time", "end_time", "room"]
    assert next(f for f in form if f["name"] == "title")["max_length"] == 100
    assert not next(f for f in form if f["name"] == "room")["required"]
    all_day = {**CALENDAR, "all_day": True, "start_time": None, "end_time": None}
    assert [f["name"] for f in fields("add_to_ai_calendar", all_day)] == ["title", "day", "room"]


def test_feedback_offers_both_texts_and_ignores_the_models_runtime():
    form = fields("leave_feedback", {**FEEDBACK, "runtime": {"context": {}}})
    assert [(f["name"], f["kind"], f["max_length"]) for f in form] == [("subject", "text", 100), ("feedback", "textarea", 4000)]
    assert _shown(form) == FEEDBACK


def test_a_valid_change_replaces_only_that_field():
    assert edit("add_to_ai_calendar", CALENDAR, {"title": "New title"}) == {**CALENDAR, "title": "New title"}
    assert edit("leave_feedback", FEEDBACK, {"subject": "idea"}) == {**FEEDBACK, "subject": "idea"}


def test_an_empty_optional_value_clears_the_field():
    assert edit("add_to_ai_calendar", CALENDAR, {"room": "  "})["room"] is None
    assert edit("add_to_ai_calendar", CALENDAR, {"end_time": ""})["end_time"] is None


def test_a_field_the_form_did_not_offer_is_refused():
    with pytest.raises(InvalidEdit):
        edit("add_to_ai_calendar", CALENDAR, {"all_day": "true"})
    with pytest.raises(InvalidEdit):
        edit("call_api_tool", {"name": "rooms_book_room", "arguments": BOOKING}, {"room_id": "other"}, SCHEMA)


@pytest.mark.parametrize("values", [{"day": "not-a-date"}, {"title": ""}, {"start_time": "17:00"}, {"end_time": "9am"}])
def test_a_value_that_does_not_hold_is_refused(values):
    with pytest.raises(InvalidEdit):
        edit("add_to_ai_calendar", CALENDAR, values)


def test_the_proposed_duration_is_dropped_once_the_user_gives_the_end():
    proposed = {"title": "Meeting", "day": "2099-01-01", "start_time": "09:00", "proposed_duration_minutes": 90}
    changed = edit("add_to_ai_calendar", proposed, {"end_time": "10:15"})
    assert changed["end_time"] == "10:15" and "proposed_duration_minutes" not in changed
    assert edit("add_to_ai_calendar", proposed, {"title": "Other"})["proposed_duration_minutes"] == 90


def test_an_edited_api_call_is_validated_by_its_schema_and_keeps_the_operation():
    call = {"name": "rooms_book_room", "arguments": BOOKING}
    assert edit("call_api_tool", call, {"title": "Retro"}, SCHEMA) == {
        "name": "rooms_book_room", "arguments": {**BOOKING, "title": "Retro"}}
    with pytest.raises(InvalidEdit):
        edit("call_api_tool", call, {"title": ""}, {**SCHEMA, "properties": {**SCHEMA["properties"], "title": {"type": "string", "minLength": 1}}})
    with pytest.raises(InvalidEdit):
        edit("call_api_tool", call, {"title": "Retro"}, None)


def test_a_number_follows_the_schema_type():
    schema = {"type": "object", "properties": {"duration_hours": {"type": "integer"}}}
    call = {"name": "events_create_draft", "arguments": {"name": "Evening"}}
    assert edit("call_api_tool", call, {"duration_hours": "3"}, schema)["arguments"]["duration_hours"] == 3
    with pytest.raises(InvalidEdit):
        edit("call_api_tool", call, {"duration_hours": "three"}, schema)


def _paused(name, args, prepared=()):
    interrupt = SimpleNamespace(id="i1", value={"action_requests": [{"name": name, "args": args}]})
    return SimpleNamespace(interrupts=[interrupt], values={"api_prepared": list(prepared)})


def test_a_decision_with_edits_resumes_with_the_edited_action():
    found = [{"id": "i1", "actions": 1}]
    resume = ask._decisions(found, "approve", [ActionEdit(index=0, values={"subject": "idea"})], _paused("leave_feedback", FEEDBACK))
    assert resume == {"i1": {"decisions": [{"type": "edit", "edited_action": {
        "name": "leave_feedback", "args": {**FEEDBACK, "subject": "idea"}}}]}}
    call = {"name": "rooms_book_room", "arguments": BOOKING}
    prepared = [{"call_id": "c", "target": "rooms_book_room", "arguments": BOOKING, "schema": SCHEMA}]
    resume = ask._decisions(found, "approve", [ActionEdit(index=0, values={"title": "Retro"})], _paused("call_api_tool", call, prepared))
    assert resume["i1"]["decisions"][0]["edited_action"]["args"] == {"name": "rooms_book_room", "arguments": {**BOOKING, "title": "Retro"}}


def test_a_decision_without_changes_stays_a_plain_approve_and_bad_changes_are_refused():
    found = [{"id": "i1", "actions": 1}]
    paused = _paused("leave_feedback", FEEDBACK)
    assert ask._decisions(found, "approve", [ActionEdit(index=0, values={})], paused) == {"i1": {"decisions": [{"type": "approve"}]}}
    with pytest.raises(InvalidEdit):
        ask._decisions(found, "approve", [ActionEdit(index=1, values={"subject": "x"})], paused)
    with pytest.raises(InvalidEdit):
        ask._decisions(found, "reject", [ActionEdit(index=0, values={"subject": "x"})], paused)
    with pytest.raises(InvalidEdit):
        ask._decisions(found, "approve", [ActionEdit(index=0, values={"nope": "x"})], paused)
