"""The prompts must offer the account tools, not the retired button-only calendar or Moodle integration."""

from catix.agent import roles


def test_calendar_requests_are_routed_to_actions_on_the_site_and_buttons_in_bots():
    assert "add_to_ai_calendar" in roles.ACCOUNT and "update_ai_calendar" in roles.ACCOUNT
    assert "Nobody adds an event" not in roles.SUPERVISOR
    assert "only by its button" not in roles.ACCOUNT
    assert "adding" in roles.ROLES["account"].offers and "updating" in roles.ROLES["account"].offers
    assert "button" in roles.CALENDAR_BUTTON


def test_printer_status_is_offered_without_promising_printing_or_moodle():
    from catix.agent.tools import TOOLS

    api_names = {"search_api_tools", "call_api_tool"}
    assert api_names <= roles.ROLES["account"].tools
    assert api_names <= roles.ROLES["campus"].tools
    assert api_names <= {tool.name for tool in TOOLS}
    assert not api_names & roles.ROLES["account"].approval, "the pilot contains only read-only operations"
    assert "get_printer_status" not in roles.ACCOUNT
    assert all(name in roles.ACCOUNT for name in api_names)
    assert not {"find_api_actions", "describe_api_action", "execute_api_action"} & {tool.name for tool in TOOLS}
    assert "printer" in roles.ROLES["account"].offers
    assert "Moodle" not in roles.ACCOUNT
    assert "print files" in roles.ACCOUNT, "the prompt must explicitly distinguish status from printing"
