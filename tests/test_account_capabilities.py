"""The prompts must offer the account tools, not the retired button-only calendar or Moodle integration."""

from catix.agent import roles


def test_calendar_requests_are_routed_to_actions_on_the_site_and_buttons_in_bots():
    assert "add_to_ai_calendar" in roles.SUPERVISOR and "update_ai_calendar" in roles.SUPERVISOR
    assert "AI Calendar" not in roles.ACCOUNT and "calendar_" not in roles.ACCOUNT
    assert "Nobody adds an event" not in roles.SUPERVISOR
    assert "only by its button" not in roles.ACCOUNT
    assert "AI Calendar" not in roles.ROLES["account"].offers
    assert "account_get_my_schedule" in roles.SUPERVISOR and "get_my_ai_calendar" in roles.SUPERVISOR
    assert "button" in roles.CALENDAR_BUTTON


def test_account_uses_discovery_for_native_reads_and_confirmed_mutations():
    assert "call_api_tool" in roles.ACCOUNT and "act_api_tool" not in roles.ACCOUNT
    assert "reads and mutations" in roles.ACCOUNT and "approval" in roles.ACCOUNT
    assert "calendar_update_ai_calendar" not in roles.ACCOUNT
    assert "sport_sport_checkin" in roles.ACCOUNT
    assert "music_book_music_room" in roles.ACCOUNT
    assert "Do not retry" in roles.ACCOUNT or "do not repeat" in roles.ACCOUNT


def test_printer_status_is_offered_without_promising_printing_or_moodle():
    from catix.agent.tools import TOOLS

    api_names = {"search_api_tools", "call_api_tool"}
    assert api_names <= roles.ROLES["account"].tools
    assert api_names <= roles.MAIN_TOOLS
    assert all(api_names <= role.tools for role in roles.ROLES.values())
    assert api_names <= {tool.name for tool in TOOLS}
    assert all(not hasattr(role, "approval") for role in roles.ROLES.values()), "approval follows the shared tool, not a role"
    assert "get_printer_status" not in roles.ACCOUNT
    assert all(name in roles.ACCOUNT for name in api_names)
    assert not {"find_api_actions", "describe_api_action", "execute_api_action"} & {tool.name for tool in TOOLS}
    assert "printer" in roles.ROLES["account"].offers
    assert "Moodle" not in roles.ACCOUNT
    assert "print files" in roles.ACCOUNT, "the prompt must explicitly distinguish status from printing"
