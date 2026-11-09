"""The prompts must offer the account tools, not the retired button-only calendar or Moodle integration."""

from catix.agent import roles


def test_root_exposes_shared_api_and_only_retrieval_helpers():
    from langchain_core.messages import AIMessage, HumanMessage
    from pydantic import SecretStr

    from catix.agent.core import build_agent
    from catix.agent.tools import AgentContext
    from tests.test_roles import ScriptedModel

    bound = []

    class RecordingModel(ScriptedModel):
        def bind_tools(self, tools, **kwargs):
            bound.append({tool.name for tool in tools})
            return self

    for context in (AgentContext(), AgentContext(innohassle_token=SecretStr("synthetic"), innohassle_id="u1")):
        graph = build_agent(RecordingModel(responses=[AIMessage(content="Привет!")]), guardrail=False)
        graph.invoke({"messages": [HumanMessage("Привет!")]},
                     {"configurable": {"thread_id": "no-account-helper"}}, context=context)
        assert {name for name in bound[-1] if name.startswith("ask_")} == {"ask_docs", "ask_chats"}
        assert {"search_api_tools", "call_api_tool"} <= bound[-1]
    assert set(roles.ROLES) == {"docs", "chats"}


def test_printer_status_is_offered_without_promising_printing_or_moodle():
    from catix.agent.tools import TOOLS

    api_names = {"search_api_tools", "call_api_tool"}
    assert api_names <= roles.MAIN_TOOLS
    assert all(api_names <= role.tools for role in roles.ROLES.values())
    assert api_names <= {tool.name for tool in TOOLS}
    assert all(not hasattr(role, "approval") for role in roles.ROLES.values()), "approval follows the shared tool, not a role"
    assert "get_printer_status" not in roles.MCP_RULES
    assert all(name in roles.MCP_RULES for name in api_names)
    assert not {"find_api_actions", "describe_api_action", "execute_api_action"} & {tool.name for tool in TOOLS}
    assert "printer" in roles.ACCOUNT_OFFERS
    assert "Moodle" not in roles.MCP_RULES
    assert "print files" in roles.MCP_RULES, "the prompt must explicitly distinguish status from printing"
