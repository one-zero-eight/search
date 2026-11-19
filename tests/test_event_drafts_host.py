"""Organizer tools use the existing host confirmation and receipt path."""
import asyncio

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.types import Command
from pydantic import SecretStr

from catix.agent import core
from catix.agent.api_descriptions import describe_action
from catix.agent.tools import AgentContext
from catix.innohassle.mcp_access import CONFIRMATION_TOOLS, CREDENTIAL_MODES
from tests.test_mcp_event_drafts import CREATE, ID, signed, upstream
from tests.test_roles import ScriptedModel

MUTATIONS = [('events_create_draft', CREATE),
             ('events_update_draft', {'draft_id': ID, 'locale': 'en', 'description': '',
                                      'registration_url': CREATE['registration_url']})]


@pytest.mark.parametrize('name,arguments', MUTATIONS)
@pytest.mark.parametrize('language', ['ru', 'en'])
def test_draft_confirmation_covers_exact_requested_fields(name, arguments, language):
    assert name in CONFIRMATION_TOOLS
    assert CREDENTIAL_MODES[name] == 'innohassle'
    text = describe_action(name, arguments, language)
    for value in arguments.values():
        if value != '':
            assert str(value) in text
    assert ('модерац' in text if language == 'ru' else 'moderation' in text)
    if name == 'events_update_draft':
        assert ('Очистить описание' in text if language == 'ru' else 'Clear description' in text)
        assert ('внешнюю регистрацию' in text if language == 'ru' else 'external registration' in text)


@pytest.mark.parametrize('name,arguments', MUTATIONS)
@pytest.mark.parametrize('helper', [None, 'ask_docs', 'ask_chats'])
@pytest.mark.parametrize('decision', ['approve', 'reject'])
@pytest.mark.parametrize('asynchronous', [False, True])
def test_draft_host_consent_then_real_protocol_readback(
    signed, upstream, mcp_http_protocol, monkeypatch, name, arguments, helper, decision, asynchronous,
):
    _, requests = upstream
    monkeypatch.setattr(core.store, 'visible_chats', lambda *a: [])
    monkeypatch.setattr(core, 'tool_call_token', lambda: None)
    script: list[BaseMessage] = []
    if helper:
        script.append(AIMessage(content='', tool_calls=[{
            'name': helper, 'args': {'question': 'Подготовь черновик мероприятия.'}, 'id': 'helper'}]))
    script.append(AIMessage(content='', tool_calls=[{
        'name': 'call_api_tool', 'args': {'name': name, 'arguments': arguments}, 'id': 'write'}]))
    script.extend(AIMessage(content='Обработано.') for _ in range(4))
    agent = core.build_agent(ScriptedModel(responses=script), guardrail=False)
    config = {'configurable': {'thread_id': 'draft-consent'}}
    context = AgentContext(innohassle_token=SecretStr(signed))

    def run(value):
        return (asyncio.run(agent.ainvoke(value, config, context=context)) if asynchronous
                else agent.invoke(value, config, context=context))

    run({'messages': [HumanMessage('Подготовь черновик мероприятия.')]})
    paused = agent.get_state(config).interrupts
    assert len(paused) == 1
    assert requests == [], 'No upstream details/permissions or writes before consent'
    action = paused[0].value['action_requests'][0]
    assert action['args'] == {'name': name, 'arguments': arguments}
    assert ('Создать черновик' if name == 'events_create_draft' else 'Изменить черновик') in action['description']
    out = run(Command(resume={paused[0].id: {'decisions': [{'type': decision}]}}))
    assert not agent.get_state(config).interrupts
    if decision == 'reject':
        assert requests == []
        assert not core.action_receipt(out['messages'])
    else:
        assert [r.method for r in requests] == (
            ['GET', 'POST', 'PUT', 'POST', 'GET'] if name == 'events_create_draft'
            else ['GET', 'PATCH', 'PUT', 'GET'])
        assert core.action_receipt(out['messages'])
        assert core._action_receipts(out['messages'])[0]['outcome'] == 'confirmed'
        assert all('/submissions' not in r.url.path for r in requests)


@pytest.mark.parametrize('name,arguments', MUTATIONS)
def test_permissions_are_checked_after_approval(signed, upstream, mcp_http_protocol, monkeypatch, name, arguments):
    state, requests = upstream
    monkeypatch.setattr(core.store, 'visible_chats', lambda *a: [])
    monkeypatch.setattr(core, 'tool_call_token', lambda: None)
    script: list[BaseMessage] = [AIMessage(content='', tool_calls=[{
        'name': 'call_api_tool', 'args': {'name': name, 'arguments': arguments}, 'id': 'write'}]),
        AIMessage(content='Нет доступа.')]
    agent = core.build_agent(ScriptedModel(responses=script), guardrail=False)
    config = {'configurable': {'thread_id': 'draft-permission-revoked'}}
    context = AgentContext(innohassle_token=SecretStr(signed))
    agent.invoke({'messages': [HumanMessage('Подготовь черновик мероприятия.')]}, config, context=context)
    paused = agent.get_state(config).interrupts
    assert len(paused) == 1 and requests == []
    state['profile']['roles'] = []
    state['draft']['can_edit'] = False
    out = agent.invoke(Command(resume={paused[0].id: {'decisions': [{'type': 'approve'}]}}), config, context=context)
    assert [r.method for r in requests] == ['GET']
    assert not core.action_receipt(out['messages'])
