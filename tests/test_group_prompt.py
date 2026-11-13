"""Trusted memberships are model context, never model-controlled access rules."""

import pytest
from langchain.agents.middleware import ModelRequest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.runtime import Runtime
from pydantic import Field, SecretStr

from catix.agent import core
from catix.agent.tools import AgentContext
from tests.test_roles import ScriptedModel, _ask


@pytest.mark.parametrize("role", [None, "docs", "chats"])
@pytest.mark.parametrize("verified, legacy", [
    (("B26-CSE-01", "B26-CSE-02"), None),
    (("B26-CSE-01",), "B26-CSE-01"),
    ((), None),
    ((), "B25-CSE-01"),
])
def test_all_roles_receive_trusted_memberships(monkeypatch, role, verified, legacy):
    monkeypatch.setattr(core.store, "visible_chats", lambda *args: [])
    context = AgentContext(study_group=legacy, verified_study_groups=verified,
                           innohassle_token=SecretStr("synthetic-user-token"))
    request = ModelRequest(
        model=ScriptedModel(responses=[AIMessage("ok")]), messages=[HumanMessage("Какая у меня группа?")],
        tools=[], state={"messages": []}, runtime=Runtime(context=context),
    )
    seen = []
    core.prompt_for(role).wrap_model_call(request, seen.append)
    prompt = seen[0].system_message.text
    assert "get_my_schedule" in prompt
    if verified:
        assert all(group in prompt for group in verified)
    if len(verified) > 1:
        assert "verified study groups are" in prompt
        assert "Do not choose the first" in prompt
        assert "only when the request requires one specific group" in prompt
        assert "has no study group" not in prompt
        assert "limited every chat search to the chats of group `all`" not in prompt
    elif verified or legacy:
        assert f"study group is {(verified or (legacy,))[0]}" in prompt
        assert "never ask for it" in prompt
    else:
        assert "not known or verified" in prompt
        assert "has no study group" not in prompt
    assert "synthetic-user-token" not in prompt


@pytest.mark.parametrize("helper", ["docs", "chats"])
def test_memberships_reach_the_helper_in_the_real_graph(monkeypatch, helper):
    class CaptureModel(ScriptedModel):
        prompts: list[str] = Field(default_factory=list)

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            self.prompts.extend(message.text for message in messages if message.type == "system")
            return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

    monkeypatch.setattr(core.store, "visible_chats", lambda *args: [])
    model = CaptureModel(responses=[
        _ask(f"ask_{helper}", "Какие учебные группы известны из профиля?"),
        AIMessage("Известны B26-CSE-01 и B26-CSE-02."),
        AIMessage("Ваши группы: B26-CSE-01 и B26-CSE-02."),
    ])
    context = AgentContext(verified_study_groups=("B26-CSE-01", "B26-CSE-02"),
                           allowed_chat_ids=frozenset({17, 18}))
    out = core.build_agent(model, guardrail=False).invoke(
        {"messages": [HumanMessage("Какие учебные группы у меня в профиле?")]},
        {"configurable": {"thread_id": f"group-context-{helper}"}}, context=context,
    )
    assert any(message.type == "tool" and message.name == f"ask_{helper}" for message in out["messages"])
    assert len(model.prompts) >= 3
    assert any("You are a helper" in prompt for prompt in model.prompts)
    assert all("verified study groups are: B26-CSE-01, B26-CSE-02" in prompt for prompt in model.prompts)
    assert context.study_group is None and context.allowed_chat_ids == frozenset({17, 18})
