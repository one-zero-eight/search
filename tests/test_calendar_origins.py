"""Automatic calendar offers must not duplicate service recommendations or bookings."""
import asyncio
import json
from datetime import datetime, time, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from catix import personal_calendar
from catix.agent import events
from catix.api import ask
from catix.api.app import app
from catix.innohassle import token
from catix.settings import settings
from tests.test_api import FakeChats


@pytest.fixture
def extraction(monkeypatch):
    day = (datetime.now(settings.tz) + timedelta(days=1)).date()
    calls, proposals = [], []
    result = events.Events(events=[events.Event(title='Football', day=day, start_time=time(18, 30), end_time=time(20, 30), room=None, source=None)])

    class Model:
        def invoke(self, prompt, **kwargs):
            calls.append(prompt)
            return result

    monkeypatch.setattr(events, '_model', Model)
    monkeypatch.setattr(personal_calendar, 'propose', lambda items: proposals.extend(items) or [
        (f'p{i}', item) for i, item in enumerate(items)])
    return day, result, calls, proposals


def service_turn(day, name='get_my_available_trainings', data=None):
    training = {'training_id': 49071, 'name': 'Football', 'starts_at': f'{day}T18:30:00+03:00',
                'ends_at': f'{day}T20:30:00+03:00', 'place': 'Stadium', 'can_check_in': True, 'checked_in': False}
    native = name in {'get_my_available_trainings', 'get_my_schedule', 'get_my_ai_calendar'}
    call = {'id': 'read', 'name': name if native else 'call_api_tool',
            'args': {'day': str(day)} if native else {'name': name, 'arguments': {}}}
    artifact = None
    if name == 'get_my_available_trainings':
        artifact = {'trainings': {'range': [str(day), str(day)], 'trainings': [training]},
                    'training_arguments': {'date_from': str(day), 'date_to': str(day)},
                    'agenda': {'range': [str(day), str(day)], 'events': [], 'total': 0,
                               'sources': {'innohassle': {'status': 'complete', 'truncated': False},
                                           'ai_calendar': {'status': 'complete', 'truncated': False}},
                               'complete': True, 'not_read': [], 'truncated': False}}
    return [HumanMessage('на какие я могу записаться занятия на завтра (спорт)?'),
            AIMessage('', tool_calls=[call]),
            ToolMessage(json.dumps(data or {'available': [training]}), name=call['name'], tool_call_id='read', artifact=artifact),
            AIMessage('Завтра Football — 18:30–20:30, стадион.')]


@pytest.fixture
def http_answer(monkeypatch):
    kept = FakeChats()
    monkeypatch.setattr(ask, 'chats', kept)
    monkeypatch.setattr(ask.attachments, 'list_for_chat', lambda *args: [])
    monkeypatch.setattr(ask.groups, 'scoped_chat_ids', lambda *args: set())
    monkeypatch.setattr(ask.groups, 'effective_group', lambda *args: ask.groups.ALL)
    monkeypatch.setattr(ask.titles, 'name', lambda *args: None)
    monkeypatch.setattr(token, 'claims', lambda value: {'uid': 'calendar-test', 'email': 'test@innopolis.university'})

    def run(messages, *, streamed=False, sources=None):
        class Graph:
            def __init__(self):
                self.checkpointer = self

            async def aget_state(self, config):
                return SimpleNamespace(values={'sources': {}}, config={'configurable': {'checkpoint_id': 'cp'}}, interrupts=[])

            async def adelete_thread(self, thread_id):
                pass

            async def ainvoke(self, *args, **kwargs):
                return {'messages': messages, 'sources': sources or {}}

            async def astream(self, *args, **kwargs):
                yield 'values', await self.ainvoke()

        monkeypatch.setattr(ask, 'agent', Graph)
        response = TestClient(app).post('/ask/stream' if streamed else '/ask/',
                                        json={'query': messages[0].text}, headers={'Authorization': 'Bearer synthetic'})
        assert response.status_code == 200, response.text
        if streamed:
            blocks = response.text.split('\n\n')
            body = next(json.loads(block.split('data: ', 1)[1]) for block in blocks if block.startswith('event: done\n'))
        else:
            body = response.json()
        assert kept.answers[-1]['response'].model_dump(mode='json')['calendar_events'] == body['calendar_events']
        return body

    return run


@pytest.mark.parametrize('streamed', [False, True])
def test_sport_recommendations_do_not_start_calendar_extraction(http_answer, extraction, streamed):
    day, _, calls, proposals = extraction
    response = http_answer(service_turn(day), streamed=streamed)
    assert response['calendar_events'] == []
    assert [offer['title'] for offer in response['signup_offers']] == ['Football']
    assert calls == [], 'A service-only answer must not spend another model call extracting the same events'
    assert proposals == []


@pytest.mark.parametrize('name', ['get_my_schedule', 'get_my_ai_calendar', 'account_get_my_schedule',
                                  'account_get_booking', 'sport_get_my_sport', 'sport_get_training',
                                  'sport_get_sport_trainings', 'rooms_book_room', 'music_book_music_room'])
def test_schedule_and_booking_answers_do_not_offer_duplicates(http_answer, extraction, name):
    day, _, calls, proposals = extraction
    response = http_answer(service_turn(day, name))
    assert response['calendar_events'] == []
    assert calls == proposals == []


@pytest.mark.parametrize('enrollment', ['internal', 'external', None])
def test_events_with_internal_signup_only_skip_calendar_extraction(http_answer, extraction, enrollment):
    day, _, calls, proposals = extraction
    item: dict = {'id': 'a' * 24, 'title': 'Football', 'starts_at': f'{day}T18:30:00+03:00',
            'ends_at': f'{day}T20:30:00+03:00'}
    if enrollment:
        item['enrollment_info'] = {'type': enrollment, 'capacity': None, 'enrolled_count': 0,
                                   'url': 'https://example.org/register' if enrollment == 'external' else None}
    response = http_answer(service_turn(day, 'events_get_event', {'event': item}))
    assert bool(response['calendar_events']) is (enrollment != 'internal')
    assert bool(calls) is (enrollment != 'internal')
    assert bool(proposals) is (enrollment != 'internal')


def with_deadline(messages):
    """A service recommendation and a retrieved deadline in the same answer/paragraph."""
    report = 'Дедлайн по математике завтра в 18:30 [m0].'
    messages[-1:] = [AIMessage('', tool_calls=[{'id': 'docs', 'name': 'ask_docs', 'args': {'question': 'дедлайн'}}]),
                    ToolMessage(report, name='ask_docs', tool_call_id='docs'),
                    AIMessage('Завтра Football — 18:30–20:30; дедлайн по математике в 18:30 [m0].')]
    return {'m0': {'wiki': True, 'key': 'wiki:1', 'title': 'Дедлайны', 'link': 'https://example.org/deadlines'}}


@pytest.mark.parametrize('streamed', [False, True])
def test_mixed_answer_keeps_deadline_not_service_event_even_with_wrong_citation(http_answer, extraction, streamed):
    day, result, calls, proposals = extraction
    messages = service_turn(day)
    sources = with_deadline(messages)
    result.events[0].source = 1  # Even a model misattribution must not reoffer the known service event.
    result.events.extend([
        events.Event(title='Дедлайн по математике', day=day, start_time=time(18, 30), end_time=None, room=None, source=1),
        events.Event(title='Выдуманный дедлайн', day=day, start_time=time(19), end_time=None, room=None, source=99),
    ])
    response = http_answer(messages, sources=sources, streamed=streamed)
    assert [item['title'] for item in response['calendar_events']] == ['Дедлайн по математике']
    assert response['calendar_events'][0]['source_url'] == 'https://example.org/deadlines'
    assert len(calls) == 1 and len(proposals) == 1


def test_retrieval_only_sport_title_is_not_a_keyword_blacklist(http_answer, extraction):
    day, _, calls, _ = extraction
    messages = [HumanMessage('когда футбол?'), AIMessage('')]
    sources = with_deadline(messages)
    messages[-1] = AIMessage('Футбол завтра в 18:30 [m0].')
    response = http_answer(messages, sources=sources)
    assert len(response['calendar_events']) == 1 and len(calls) == 1


@pytest.mark.parametrize('helper', ['docs', 'chats'])
def test_real_helper_graph_preserves_calendar_origin(monkeypatch, extraction, helper):
    from catix.agent import core, schedule_tools
    from catix.agent.tools import AgentContext
    from tests.test_roles import ScriptedModel

    day, _, calls, _ = extraction
    agenda = {'range': [str(day), str(day)], 'events': [
        {'title': 'Football', 'starts_at': f'{day}T18:30:00+03:00', 'ends_at': f'{day}T20:30:00+03:00'}],
        'total': 1, 'sources': {}, 'complete': True, 'not_read': [], 'truncated': False}
    monkeypatch.setattr(schedule_tools, 'read_my_schedule', lambda *args: agenda)
    monkeypatch.setattr(core.store, 'visible_chats', lambda *args: [])
    model = ScriptedModel(responses=[
        AIMessage('', tool_calls=[{'name': f'ask_{helper}', 'args': {'question': 'Что у меня завтра?'}, 'id': 'helper'}]),
        AIMessage('', tool_calls=[{'name': 'get_my_schedule', 'args': {'date_from': str(day), 'date_to': str(day)}, 'id': 'agenda'}]),
        AIMessage('Завтра Football в 18:30.'), AIMessage('Завтра Football в 18:30.'),
    ])
    result = core.build_agent(model, guardrail=False).invoke({'messages': [HumanMessage('Что у меня завтра?')]},
                {'configurable': {'thread_id': f'calendar-origins-{helper}'}}, context=AgentContext())
    report = next(m for m in result['messages'] if isinstance(m, ToolMessage))
    assert report.artifact.get('calendar_origins', {}).get('service') is True
    assert events.extract(core.final_answer(result['messages'], {}), origins=events.origins(result['messages'])) == []
    assert calls == []


@pytest.mark.parametrize('mixed', [False, True])
def test_telegram_passes_provenance_to_background_calendar_offers(monkeypatch, extraction, mixed):
    from catix.tgbot import bot

    day, extracted, calls, proposals = extraction
    messages = service_turn(day)
    sources = with_deadline(messages) if mixed else {}
    if mixed:
        extracted.events.append(events.Event(title='Дедлайн по математике', day=day, start_time=time(18, 30),
                                             end_time=None, room=None, source=1))
    edits = []
    monkeypatch.setattr(bot.groups, 'scoped_chat_ids', lambda *args: set())
    monkeypatch.setattr(bot.groups, 'effective_group', lambda *args: bot.groups.ALL)

    async def run(*args):
        return {'messages': messages, 'sources': sources}

    monkeypatch.setattr(bot.stream, 'run', run)

    async def check():
        result = await bot._run_agent('Предложи спорт', 'calendar-origins-tg', 123, None)
        assert len(result) == 3, 'The bot must retain tool provenance, not just the final text'
        answer, trace, context = result

        async def edit_reply_markup(**kwargs):
            edits.append(kwargs)

        await bot._offer_events(SimpleNamespace(edit_reply_markup=edit_reply_markup), answer, trace, context)

    asyncio.run(check())
    assert len(calls) == len(proposals) == len(edits) == int(mixed)
    if mixed:
        assert proposals[0]['title'] == 'Дедлайн по математике'


@pytest.mark.parametrize('mode', ['old', 'unpaired', 'wrong_name', 'discovery', 'unrelated'])
def test_noncurrent_or_unrelated_tools_cannot_suppress_calendar_offers(extraction, mode):
    day, _, calls, _ = extraction
    messages = service_turn(day)
    if mode == 'old':
        messages.extend([HumanMessage('Новый вопрос'), AIMessage('Экзамен завтра в 18:30.')])
    elif mode == 'unpaired':
        messages[2].tool_call_id = 'not-the-call'
    elif mode == 'wrong_name':
        messages[2].name = 'get_my_schedule'
    else:
        name = 'search_api_tools' if mode == 'discovery' else 'printers_print_get_printers_status'
        messages = service_turn(day, name)
    assert events.origins(messages) == {}
    assert events.extract(messages[-1].text, origins=events.origins(messages))
    assert len(calls) == 1


@pytest.mark.parametrize('body', ['not json', '[]', '{"error": "unavailable"}'])
def test_failed_service_results_do_not_become_independent_reminders(extraction, body):
    day, _, calls, _ = extraction
    messages = service_turn(day)
    messages[2].content = body
    assert events.extract(messages[-1].text, origins=events.origins(messages)) == []
    assert calls == []


def test_mixed_external_and_internal_events_preserve_only_external(extraction):
    day, result, calls, _ = extraction
    items = [
        {'title': 'Football', 'starts_at': f'{day}T15:30:00Z', 'enrollment_info': {'type': 'internal'}},
        {'title': 'Open lecture', 'starts_at': f'{day}T20:00:00+03:00', 'enrollment_info': {'type': 'external'}},
    ]
    messages = service_turn(day, 'events_get_university_events', {'events': items})
    result.events[0].title = 'Football: тренировка'
    result.events.append(events.Event(title='Open lecture', day=day, start_time=time(20), end_time=None, room=None, source=None))
    answer = 'Завтра Football в 18:30 и Open lecture в 20:00.'
    found = events.extract(answer, origins=events.origins(messages))
    assert [item['title'] for item in found] == ['Open lecture']
    assert len(calls) == 1


@pytest.mark.parametrize('decoration', ['training', 'тренировка'])
@pytest.mark.parametrize('evidence', ['same-start', 'wrong-citation'])
def test_decorated_service_event_cannot_borrow_independent_evidence(extraction, decoration, evidence):
    day, result, calls, _ = extraction
    items = [{'title': 'Football', 'starts_at': f'{day}T20:00:00+03:00',
              'enrollment_info': {'type': 'internal'}}]
    if evidence == 'same-start':
        items.append({'title': 'Open robotics lecture', 'starts_at': f'{day}T20:00:00+03:00',
                      'enrollment_info': {'type': 'external'}})
        display, source = 'Robotics talk', None
        answer = 'Tomorrow Football and Open robotics lecture at 20:00.'
    else:
        display, source = 'Homework deadline: Mathematical Analysis', 1
        answer = ('Tomorrow Football at 20:00; Homework deadline: Mathematical Analysis tomorrow at 20:00 [1].'
                  '\n\nSources:\n[1] https://example.org/homework')
    messages = service_turn(day, 'events_get_university_events', {'events': items})
    result.events[:] = [
        events.Event(title=f'Football: {decoration}', day=day, start_time=time(20), end_time=None, room=None, source=source),
        events.Event(title=display, day=day, start_time=time(20), end_time=None, room=None, source=source),
    ]
    found = events.extract(answer, origins=events.origins(messages))
    assert [item['title'] for item in found] == [display]
    assert found[0]['source_url'] == ('https://example.org/homework' if source else None)
    assert len(calls) == 1


@pytest.mark.parametrize('enrollment', ['external', None])
@pytest.mark.parametrize('mixed', [False, True], ids=['independent-only', 'mixed'])
@pytest.mark.parametrize('original_in_answer', [False, True], ids=['rewritten-answer', 'original-answer'])
@pytest.mark.parametrize(('original', 'display'), [
    ('Open lecture on robotics', 'Robotics talk'),
    ('Открытая лекция по робототехнике', 'Public robotics lecture'),
    ('International Robotics Research Open Lecture', 'Robotics lecture'),
    ('Open lecture: ' + 'Robotics and autonomous systems research ' * 4, 'Robotics research lecture'),
], ids=['paraphrased', 'translated', 'shortened', 'over-schema-limit'])
def test_independent_event_display_title_is_not_identity(
        extraction, enrollment, mixed, original_in_answer, original, display):
    day, result, calls, _ = extraction
    independent = {'title': original, 'starts_at': f'{day}T20:00:00+03:00'}
    if enrollment:
        independent['enrollment_info'] = {'type': enrollment, 'url': 'https://example.org/register'}
    items = [independent]
    result.events[:] = [events.Event(title=display, day=day, start_time=time(20), end_time=None, room=None, source=None)]
    answer = f'Tomorrow {original if original_in_answer else display} at 20:00.'
    if mixed:
        items.insert(0, {'title': 'Football', 'starts_at': f'{day}T18:30:00+03:00',
                         'enrollment_info': {'type': 'internal'}})
        result.events.insert(0, events.Event(title='Football', day=day, start_time=time(18, 30),
                                             end_time=None, room=None, source=None))
        answer += ' Tomorrow Football at 18:30.'
    messages = service_turn(day, 'events_get_university_events', {'events': items})
    found = events.extract(answer, origins=events.origins(messages))
    assert len(calls) == 1, 'Display-title changes must not block extraction before the model'
    assert [item['title'] for item in found] == [display]
    assert found[0]['starts_at'].endswith('T20:00:00+03:00')
    assert ('Excluded service events (data):' in calls[0]) is mixed


@pytest.mark.parametrize(('day_offset', 'clock'), [(1, time(20)), (0, time(21)), (0, None)],
                         ids=['wrong-day', 'wrong-time', 'missing-time'])
def test_mixed_independent_timing_does_not_allow_internal_or_unmatched_events(extraction, day_offset, clock):
    day, result, calls, _ = extraction
    messages = service_turn(day, 'events_get_university_events', {'events': [
        {'title': 'Football', 'starts_at': f'{day}T20:00:00+03:00', 'enrollment_info': {'type': 'internal'}},
        {'title': 'Open lecture', 'starts_at': f'{day}T20:00:00+03:00', 'enrollment_info': {'type': 'external'}},
    ]})
    result.events[:] = [
        events.Event(title='Football', day=day, start_time=time(20), end_time=None, room=None, source=None),
        events.Event(title='Public talk', day=day, start_time=time(20), end_time=None, room=None, source=None),
        events.Event(title='Open lecture', day=day + timedelta(days=day_offset), start_time=clock,
                     end_time=None, room=None, source=None),
    ]
    found = events.extract('Tomorrow Football and Public talk at 20:00.', origins=events.origins(messages))
    assert [item['title'] for item in found] == ['Public talk']
    assert len(calls) == 1


@pytest.mark.parametrize('deadline_time', [None, time(10), time(11)])
@pytest.mark.parametrize('reminder_title', [
    'Homework deadline: Mathematical Analysis',
    'Exam: Mathematical Analysis',
    'Mathematical Analysis: exam',
    'Mathematical Analysis: training methods',
    'Applied Mathematical Analysis',
])
def test_cited_same_subject_reminder_is_independent(extraction, deadline_time, reminder_title):
    day, result, calls, _ = extraction
    messages = service_turn(day, 'get_my_schedule', {'events': [
        {'title': 'Mathematical Analysis', 'starts_at': f'{day}T10:00:00+03:00'},
    ]})
    result.events[:] = [
        events.Event(title='Mathematical Analysis', day=day, start_time=time(10), end_time=None, room=None, source=1),
        events.Event(title=reminder_title, day=day,
                     start_time=deadline_time, end_time=None, room=None, source=1),
    ]
    clock = f' at {deadline_time:%H:%M}' if deadline_time else ''
    answer = ('Tomorrow Mathematical Analysis at 10:00; '
              f'{reminder_title} tomorrow{clock} [1].'
              '\n\nSources:\n[1] https://example.org/homework')
    found = events.extract(answer, origins=events.origins(messages))
    assert [item['title'] for item in found] == [reminder_title]
    assert found[0]['all_day'] is (deadline_time is None)
    assert found[0]['source_url'] == 'https://example.org/homework'
    assert len(calls) == 1


def test_cited_chat_without_public_link_keeps_its_deadline(extraction):
    day, result, _, _ = extraction
    result.events[:] = [events.Event(title='Дедлайн', day=day, start_time=None, end_time=None, room=None, source=1)]
    answer = 'Завтра Football в 18:30. Дедлайн завтра [1].\n\nИсточники:\n[1] «Закрытый чат»'
    found = events.extract(answer, origins=events.origins(service_turn(day)))
    assert [item['title'] for item in found] == ['Дедлайн']
    assert found[0]['source_url'] is None and found[0]['all_day'] is True
