"""Personal schedule routing: subscribed calendars, not the whole academic group."""
import json
from datetime import datetime, timedelta

import httpx
import pytest
from icalendar import Calendar, Event
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import Field, SecretStr

from catix.agent import calendar_tools, core
from catix.agent.tools import AgentContext
from catix.innohassle import client as backend, mcp_account, mcp_server
from catix.settings import settings
from tests.mcp_helpers import install_http_adapter
from tests.test_roles import ScriptedModel

NOW = datetime(2026, 11, 8, 4, 38, tzinfo=settings.tz)
START, END = '2026-11-08', '2026-11-14'


class PromptCapture(ScriptedModel):
    seen: list = Field(default_factory=list, exclude=True)
    offered: list = Field(default_factory=list, exclude=True)

    def bind_tools(self, tools, **kwargs):
        self.offered = list(tools)
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.seen = list(messages)
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


def context(*, signed_in=True, group='B26-CSE-01'):
    return AgentContext(innohassle_id='synthetic-owner',
                        innohassle_token=SecretStr('synthetic-user') if signed_in else None,
                        study_group=group, asked_at=NOW)


def capture_prompt(monkeypatch, *, signed_in=True, group='B26-CSE-01'):
    monkeypatch.setattr(core.store, 'visible_chats', lambda *args: [])
    model = PromptCapture(responses=[AIMessage(content='sentinel')])
    core.build_agent(model, guardrail=False).invoke(
        {'messages': [HumanMessage('какое у меня рассписание?')]},
        {'configurable': {'thread_id': 'capture-personal-agenda'}}, context=context(signed_in=signed_in, group=group))
    return next(m.content for m in model.seen if isinstance(m, SystemMessage)), model


def test_signed_in_schedule_prompt_does_not_replace_personal_calendar_with_known_group(monkeypatch):
    prompt, _ = capture_prompt(monkeypatch)
    assert 'Use it for schedule questions' not in prompt
    assert 'Personal agenda source: account_get_my_schedule' in prompt
    assert 'date_from=2026-11-08, date_to=2026-11-14' in prompt
    assert 'get_my_ai_calendar' in prompt


@pytest.mark.parametrize('signed_in,group', [(True, None), (True, 'B26-CSE-01'), (False, 'B26-CSE-01'), (False, None)])
def test_agenda_source_is_selected_by_credentials_not_presence_of_group(monkeypatch, signed_in, group):
    prompt, _ = capture_prompt(monkeypatch, signed_in=signed_in, group=group)
    assert ('Personal agenda source: account_get_my_schedule' in prompt) is signed_in
    assert ('Personal agenda access: no InNoHassle credential' in prompt) is not signed_in
    assert 'date_from=2026-11-08, date_to=2026-11-14' in prompt


@pytest.fixture
def personal_sources(monkeypatch):
    """MCP and calendar parsing are real; all external/user data is synthetic."""
    install_http_adapter(monkeypatch)
    monkeypatch.setattr(core.store, 'visible_chats', lambda *args: [])
    monkeypatch.setattr(mcp_account, '_now', lambda: NOW)
    monkeypatch.setattr(mcp_server.token_verifier, 'claims',
                        lambda value: {'uid': 'synthetic-owner'} if value == 'synthetic-user' else None)
    observed = {'http': [], 'local': []}

    def ics(*titles):
        calendar = Calendar()
        for index, title in enumerate(titles):
            event = Event()
            event.add('uid', title)
            event.add('summary', title)
            start = NOW.replace(day=9, hour=9, minute=0) + timedelta(hours=index * 2)
            event.add('dtstart', start)
            event.add('dtend', start + timedelta(hours=1))
            calendar.add_component(event)
        return calendar.to_ical()

    def respond(request):
        observed['http'].append(request)
        assert request.method == 'GET'
        path = request.url.path
        if path == '/schedule/v0/event-groups/':
            return httpx.Response(200, json={'event_groups': [
                {'name': 'B26-CSE-01', 'alias': 'public-group', 'tags': [{'type': 'core-courses'}]},
                {'name': 'Selected English', 'alias': 'english-e7', 'tags': []},
                {'name': 'Robotics', 'alias': 'robotics', 'tags': []},
            ]})
        if path == '/schedule/v0/public-group.ics':
            return httpx.Response(200, content=ics('Wrong English stream A', 'Wrong English stream B'))
        assert request.headers['authorization'] == 'Bearer synthetic-user'
        if path == '/schedule/v0/users/me':
            return httpx.Response(200, json={'id': 73, 'favorite_event_groups': ['english-e7', 'robotics'],
                                           'hidden_event_groups': []})
        if path == '/schedule/v0/users/me/predefined':
            return httpx.Response(200, json={'event_groups': ['public-group']})
        if path == '/schedule/v0/english-e7.ics':
            return httpx.Response(200, content=ics('Selected English E7'))
        if path == '/schedule/v0/robotics.ics':
            return httpx.Response(200, content=ics('Selected Course Robotics'))
        if path == '/schedule/v0/users/me/sport.ics':
            return httpx.Response(200, content=ics('Personal Swimming'))
        if path == '/events/v1/users/me/events.ics':
            return httpx.Response(200, content=ics('Enrolled Workshop'))
        if path == '/music-room/v0/bookings/my_bookings':
            return httpx.Response(200, json=[{'id': 7, 'time_start': '2026-11-09T18:00:00', 'time_end': '2026-11-09T19:00:00'}])
        if path == '/room-booking/v0/bookings/my':
            return httpx.Response(200, json=[{'outlook_booking_id': 'room-booking-7', 'room_id': '313',
                                           'title': 'Personal room booking', 'start': '2026-11-09T19:00:00',
                                           'end': '2026-11-09T20:00:00'}])
        raise AssertionError(f'Unexpected synthetic API path: {path}')

    def local_events(key, start, end):
        observed['local'].append((key, start, end))
        return [{'calendar_event_id': 1, 'date': '2026-11-09 Mon', 'time': '20:00', 'title': 'AI calendar guitar practice'}]

    monkeypatch.setattr(calendar_tools.personal_calendar, 'account_key', lambda *args: 'ih:synthetic-owner')
    monkeypatch.setattr(calendar_tools, 'events_between', local_events)
    with backend._http_client('https://synthetic.test', transport=httpx.MockTransport(respond)) as http:
        monkeypatch.setattr(backend, '_client', http)
        yield observed


def test_trace_calendar_day_argument_is_refused_instead_of_silently_expanding_period(personal_sources):
    model = ScriptedModel(responses=[
        AIMessage(content='', tool_calls=[{'name': 'get_my_ai_calendar', 'args': {'day': START},
                                          'id': 'bad-day', 'type': 'tool_call'}]),
        AIMessage(content='sentinel'),
    ])
    out = core.build_agent(model, guardrail=False).invoke(
        {'messages': [HumanMessage('какое у меня рассписание?')]},
        {'configurable': {'thread_id': 'bad-calendar-day'}}, context=context())
    assert personal_sources['local'] == []
    result = next(m for m in out['messages'] if isinstance(m, ToolMessage))
    assert result.status == 'error' or 'error' in result.content.lower()


def test_current_personal_feeds_and_ai_calendar_cover_all_sources_for_the_same_period(personal_sources):
    period = {'date_from': START, 'date_to': END}
    model = ScriptedModel(responses=[
        AIMessage(content='', tool_calls=[
            {'name': 'call_api_tool', 'args': {'name': 'account_get_my_schedule', 'arguments': period},
             'id': 'external', 'type': 'tool_call'},
            {'name': 'get_my_ai_calendar', 'args': period, 'id': 'local', 'type': 'tool_call'},
        ]), AIMessage(content='sentinel'),
    ])
    agent = core.build_agent(model, guardrail=False)
    config = {'configurable': {'thread_id': 'personal-all-sources'}}
    out = agent.invoke({'messages': [HumanMessage('какое у меня рассписание?')]}, config, context=context())
    assert not agent.get_state(config).interrupts
    payloads = {m.name: json.loads(m.content) for m in out['messages'] if isinstance(m, ToolMessage)}
    external, local = payloads['call_api_tool'], payloads['get_my_ai_calendar']
    assert external['range'] == local['range'] == [START, END]
    assert {item['title'] for item in external['schedule']} == {
        'Selected English E7', 'Selected Course Robotics', 'Personal Swimming', 'Enrolled Workshop',
    }
    assert {item['service'] for item in external['bookings']} == {'music_room', 'room'}
    assert local['events'][0]['title'] == 'AI calendar guitar practice'
    assert 'ai_calendar' not in external
    assert 'Wrong English' not in str(payloads)
    assert core.successful_read(out['messages']) and core.read_evidence(out['messages'])
    paths = [r.url.path for r in personal_sources['http']]
    assert sorted(paths) == sorted([
        '/schedule/v0/users/me', '/schedule/v0/users/me/predefined', '/schedule/v0/event-groups/',
        '/schedule/v0/public-group.ics', '/schedule/v0/english-e7.ics', '/schedule/v0/robotics.ics',
        '/schedule/v0/users/me/sport.ics', '/events/v1/users/me/events.ics',
        '/music-room/v0/bookings/my_bookings', '/room-booking/v0/bookings/my',
    ])
    assert all(r.method == 'GET' for r in personal_sources['http'])
    assert all(r.headers.get('authorization') == (None if r.url.path == '/schedule/v0/event-groups/' else 'Bearer synthetic-user')
               for r in personal_sources['http'])


def test_explicit_public_group_request_remains_public_even_when_signed_in(personal_sources):
    from tests.mcp_native_helpers import call
    data = call('schedule_get_schedule', {'group': 'B26-CSE-01', 'date_from': START, 'date_to': END},
                token='synthetic-user')
    assert data['schedule'] == 'B26-CSE-01'
    assert {item['title'] for item in data['classes']} == {'Wrong English stream A', 'Wrong English stream B'}
    assert all('authorization' not in r.headers for r in personal_sources['http'])
    assert personal_sources['local'] == []


def test_explicit_ai_calendar_read_does_not_fetch_external_calendars(personal_sources):
    model = ScriptedModel(responses=[
        AIMessage(content='', tool_calls=[{'name': 'get_my_ai_calendar', 'args': {'date_from': START, 'date_to': START},
                                          'id': 'local-only', 'type': 'tool_call'}]), AIMessage(content='sentinel'),
    ])
    core.build_agent(model, guardrail=False).invoke({'messages': [HumanMessage('Что в AI-календаре на 8 ноября?')]},
        {'configurable': {'thread_id': 'local-only'}}, context=context())
    assert personal_sources['http'] == []
    assert len(personal_sources['local']) == 1
    assert personal_sources['local'][0][1] == personal_sources['local'][0][2]
