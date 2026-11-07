"""Discovery and execution share the same allowlist, with a real HTTP boundary and no live accounts."""

from copy import deepcopy
from types import SimpleNamespace

import httpx
import pytest
from pydantic import SecretStr

ACTION = "printers.print_get_printers_status"
PATH = "/printers/v0/print/get_printers_status"
SPEC_PATH = "/printers/v0/openapi.json"
SPEC = {
    "openapi": "3.1.0",
    "info": {"title": "Printers", "version": "0"},
    "paths": {
        "/print/get_printers_status": {"get": {
            "operationId": "print_get_printers_status", "summary": "Get Printers Status",
            "security": [{"Bearer": []}],
            "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {
                "type": "array", "items": {"$ref": "#/components/schemas/PrinterStatus"}
            }}}}},
        }},
        "/print/print": {"post": {"operationId": "print_actual_print", "summary": "Print a file"}},
    },
    "components": {"schemas": {
        "PrinterStatus": {"type": "object", "required": ["printer", "offline", "paper_percentage", "toner_percentage"], "properties": {
            "printer": {"$ref": "#/components/schemas/Printer"}, "offline": {"type": "boolean"},
            "paper_percentage": {"type": ["integer", "null"]}, "toner_percentage": {"type": ["integer", "null"]},
        }},
        "Printer": {"type": "object", "required": ["display_name", "cups_name", "ipp"], "properties": {
            "display_name": {"type": "string"}, "cups_name": {"type": "string"}, "ipp": {"type": "string"},
        }},
    }},
}
STATUS = [{"printer": {"display_name": "Library", "cups_name": "library", "ipp": "192.168.1.1:631"},
           "offline": False, "paper_percentage": 0, "toner_percentage": None}]


def runtime(token: str | None = "user-secret"):
    return SimpleNamespace(context=SimpleNamespace(innohassle_token=SecretStr(token) if token is not None else None))


@pytest.fixture
def gateway(monkeypatch):
    from catix.innohassle import actions

    monkeypatch.setattr(actions, "ACTIONS", {ACTION: actions.ACTIONS[ACTION]})
    state = SimpleNamespace(spec=deepcopy(SPEC), body=deepcopy(STATUS), status=200, asked=[], error=None,
                            headers={}, spec_status=200, spec_headers={}, token="user-secret", content=None)

    def respond(request):
        state.asked.append(request)
        assert request.method == "GET"
        if request.url.path == SPEC_PATH:
            assert "authorization" not in request.headers
            return httpx.Response(state.spec_status, json=state.spec, headers=state.spec_headers)
        assert request.url.path == PATH
        assert request.headers["authorization"] == f"Bearer {state.token}"
        assert not request.url.query and not request.content
        if state.error:
            raise state.error("secret diagnostic", request=request)
        if state.content is not None:
            return httpx.Response(state.status, content=state.content)
        return httpx.Response(state.status, json=state.body, headers=state.headers)

    with httpx.Client(base_url="https://api.innohassle.ru", cookies=actions._client.cookies.jar,
                      transport=httpx.MockTransport(respond)) as transport:
        monkeypatch.setattr(actions, "_client", transport)
        yield state


def test_discover_describe_execute_uses_live_openapi_without_exposing_other_operations(gateway):
    from catix.agent import api_tools

    found = api_tools.find_api_actions.func("есть ли бумага в принтерах")
    assert [a["action_id"] for a in found["actions"]] == [ACTION]
    described = api_tools.describe_api_action.func(ACTION)
    assert described["method"] == "GET" and described["path"] == PATH
    assert described["parameters"]["properties"] == {} and described["requires_sign_in"] is True
    assert "print_actual_print" not in str(found) and "ipp" not in str(described)
    result = api_tools.execute_api_action.func(ACTION, runtime(), parameters={})
    assert result["data"] == [{"printer": {"display_name": "Library", "cups_name": "library"},
                               "offline": False, "paper_percentage": 0, "toner_percentage": None}]
    assert "192.168" not in str(result) and "user-secret" not in str(result)
    assert [r.url.path for r in gateway.asked] == [SPEC_PATH, PATH]


def test_current_printer_openapi_shape_keeps_nullable_percentages_and_nested_fields(gateway):
    from jsonschema import Draft202012Validator
    from catix.innohassle import actions

    # Shape from the public printers/v0/openapi.json: local refs, an object with
    # additionalProperties=false, and scalar anyOf (not type lists) for supplies.
    schemas = gateway.spec["components"]["schemas"]
    schemas["Printer"]["additionalProperties"] = False
    nullable = {"anyOf": [{"type": "integer"}, {"type": "null"}]}
    for name in ("paper_percentage", "toner_percentage"):
        schemas["PrinterStatus"]["properties"][name] = {**deepcopy(nullable), "title": name}
    described = actions.describe(ACTION)["returns"]
    assert described == {"type": "array", "items": {"type": "object", "properties": {
        "printer": {"type": "object", "properties": {
            "display_name": {"type": "string"}, "cups_name": {"type": "string"},
        }},
        "offline": {"type": "boolean"}, "paper_percentage": nullable, "toner_percentage": nullable,
    }}}
    result = actions.execute(ACTION, {}, "user-secret")
    Draft202012Validator(described).validate(result["data"])
    assert result["data"][0]["paper_percentage"] == 0
    assert result["data"][0]["toner_percentage"] is None
    assert "ipp" not in str(described) and "192.168" not in str(result)
    assert [request.url.path for request in gateway.asked] == [SPEC_PATH, PATH]


@pytest.mark.parametrize("parameters", [{"url": "http://127.0.0.1"}, {"Authorization": "Bearer other"},
                                         {"printer_cups_name": "library"}, {"user_id": "other"}, []])
def test_unsupported_parameters_are_refused_before_the_authenticated_request(gateway, parameters):
    from catix.agent import api_tools

    result = api_tools.execute_api_action.func(ACTION, runtime(), parameters=parameters)
    assert "Invalid API parameters" in result["error"]
    assert [r.url.path for r in gateway.asked] == [SPEC_PATH]


@pytest.mark.parametrize("action_id", ["printers.print_actual_print", "accounts.tokens_impersonate", "https://evil.example/",
                                       "printers/../accounts/users", "GET /print/get_printers_status"])
def test_unknown_actions_cannot_be_described_or_executed(gateway, action_id):
    from catix.agent import api_tools

    assert "not allowed" in api_tools.describe_api_action.func(action_id)["error"]
    assert "not allowed" in api_tools.execute_api_action.func(action_id, runtime())["error"]
    assert gateway.asked == []


@pytest.mark.parametrize("context", [runtime(None), runtime(""), SimpleNamespace(context=None)])
def test_no_user_token_never_falls_back_to_a_service_token(gateway, context, monkeypatch):
    from catix.agent import api_tools
    from catix.settings import settings

    monkeypatch.setattr(settings, "innohassle_service_token", SecretStr("service-secret"))
    out = api_tools.execute_api_action.func(ACTION, context)
    assert "sign in" in out["error"] and gateway.asked == []


def test_results_are_fresh_and_missing_supplies_are_not_zero(gateway):
    from catix.agent import api_tools

    first = api_tools.execute_api_action.func(ACTION, runtime())
    gateway.body[0].update(offline=True, paper_percentage=None, toner_percentage=0)
    second = api_tools.execute_api_action.func(ACTION, runtime())
    assert first["data"][0]["offline"] is False and second["data"][0]["offline"] is True
    assert second["data"][0]["paper_percentage"] is None and second["data"][0]["toner_percentage"] == 0
    assert [r.url.path for r in gateway.asked] == [SPEC_PATH, PATH, PATH]


@pytest.mark.parametrize("status", [301, 302, 307, 401, 403, 404, 429, 500])
def test_errors_are_not_empty_results_or_raw_private_details(gateway, status):
    from catix.agent import api_tools

    gateway.status, gateway.body = status, {"detail": "user-secret ipp://192.168.1.1 private diagnostics"}
    out = api_tools.execute_api_action.func(ACTION, runtime())
    assert "error" in out and "data" not in out
    assert all(text not in str(out) for text in ("user-secret", "192.168", "private diagnostics"))


@pytest.mark.parametrize("body", [{}, [None], [{"offline": "false"}], [{**STATUS[0], "offline": "false"}]])
def test_malformed_results_are_not_facts(gateway, body):
    from catix.agent import api_tools

    gateway.body = body
    out = api_tools.execute_api_action.func(ACTION, runtime())
    assert "error" in out and "data" not in out


@pytest.mark.parametrize("entrypoint", ["describe", "execute", "find"])
@pytest.mark.parametrize("location", ["root", "items", "printer", "offline", "display_name"])
@pytest.mark.parametrize("schema", [True, False])
def test_boolean_response_schemas_fail_closed_before_execution(gateway, entrypoint, location, schema):
    from catix.innohassle import actions

    response = gateway.spec["paths"]["/print/get_printers_status"]["get"]["responses"]["200"]["content"]["application/json"]
    if location == "root":
        response["schema"] = schema
    elif location == "items":
        response["schema"]["items"] = schema
    elif location == "display_name":
        gateway.spec["components"]["schemas"]["Printer"]["properties"][location] = schema
    else:
        gateway.spec["components"]["schemas"]["PrinterStatus"]["properties"][location] = schema

    with pytest.raises(actions.ActionError, match="unsupported response schema"):
        if entrypoint == "execute":
            actions.execute(ACTION, {}, "user-secret")
        elif entrypoint == "describe":
            actions.describe(ACTION)
        else:
            actions.find("printers")
    assert [request.url.path for request in gateway.asked] == [SPEC_PATH]


@pytest.mark.parametrize("entrypoint", ["describe", "execute"])
@pytest.mark.parametrize("location, schema", [
    ("root", {}),
    ("root", {"type": "object"}),
    ("root", {"type": "string"}),
    ("root", {"allOf": [SPEC["paths"]["/print/get_printers_status"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]]}),
    ("items", {}),
    ("items", {"type": "string"}),
    ("items", {"type": "array", "items": {"$ref": "#/components/schemas/PrinterStatus"}}),
    ("items", {"allOf": [{"$ref": "#/components/schemas/PrinterStatus"}]}),
    ("items", {"$ref": "#/components/schemas/PrinterStatus", "description": "ref siblings must not hide fields"}),
    ("items", {**SPEC["components"]["schemas"]["PrinterStatus"], "allOf": [{"required": ["offline"]}]}),
    ("printer", {"allOf": [{"$ref": "#/components/schemas/Printer"}]}),
    ("printer", {"$ref": "#/components/schemas/Printer", "description": "ref sibling"}),
    ("printer", {"anyOf": [{"$ref": "#/components/schemas/Printer"}, {"type": "null"}]}),
    ("printer", {"type": "array", "items": {"$ref": "#/components/schemas/Printer"}}),
    ("offline", {}),
    ("offline", {"type": "object", "properties": {"secret": {"type": "string"}}}),
    ("offline", {"type": ["boolean", "object"]}),
    ("offline", {"allOf": [{"type": "boolean"}]}),
    ("offline", {"oneOf": [{"type": "boolean"}, {"type": "null"}]}),
    ("offline", {"anyOf": [True, {"type": "null"}]}),
    ("offline", {"anyOf": [{"type": "boolean"}, {"type": "object"}]}),
    ("offline", {"type": "boolean", "not": {"const": True}}),
])
def test_unrepresentable_response_shapes_fail_closed(gateway, entrypoint, location, schema):
    from catix.innohassle import actions

    response = gateway.spec["paths"]["/print/get_printers_status"]["get"]["responses"]["200"]["content"]["application/json"]
    if location == "root":
        response["schema"] = deepcopy(schema)
    elif location == "items":
        response["schema"]["items"] = deepcopy(schema)
    else:
        gateway.spec["components"]["schemas"]["PrinterStatus"]["properties"][location] = deepcopy(schema)
    with pytest.raises(actions.ActionError, match="unsupported response schema"):
        if entrypoint == "execute":
            actions.execute(ACTION, {}, "user-secret")
        else:
            actions.describe(ACTION)
    assert [request.url.path for request in gateway.asked] == [SPEC_PATH]


def test_external_schema_reference_is_never_fetched(gateway):
    from catix.agent import api_tools

    gateway.spec["components"]["schemas"]["PrinterStatus"] = {"$ref": "https://evil.example/schema"}
    assert "unsupported references" in api_tools.execute_api_action.func(ACTION, runtime())["error"]
    assert [r.url.path for r in gateway.asked] == [SPEC_PATH]


def test_documentation_cannot_grant_new_query_parameters(gateway):
    from catix.agent import api_tools

    gateway.spec["paths"]["/print/get_printers_status"]["get"]["parameters"] = [
        {"name": "url", "in": "query", "schema": {"type": "string"}}
    ]
    out = api_tools.execute_api_action.func(ACTION, runtime(), parameters={"url": "http://internal.example/"})
    assert "error" in out
    assert [r.url.path for r in gateway.asked] == [SPEC_PATH]


def test_changed_output_schema_cannot_expose_nested_secrets_in_a_visible_leaf(gateway):
    from catix.agent import api_tools

    gateway.spec["components"]["schemas"]["PrinterStatus"]["properties"]["offline"] = {}
    gateway.body[0]["offline"] = {"token": "private-value", "ipp": "192.168.1.2"}
    out = api_tools.execute_api_action.func(ACTION, runtime())
    assert "error" in out and "private-value" not in str(out)


def test_a_redirect_never_sends_the_token_to_another_endpoint(gateway):
    from catix.agent import api_tools

    gateway.status, gateway.headers = 307, {"Location": "https://evil.example/collect"}
    assert "error" in api_tools.execute_api_action.func(ACTION, runtime())
    assert [r.url.path for r in gateway.asked] == [SPEC_PATH, PATH]


@pytest.mark.parametrize("status, spec_status", [(200, 200), (302, 200), (307, 200), (401, 200),
                                                (403, 200), (500, 200), (200, 307), (200, 503)])
def test_cookies_and_bearers_are_isolated_across_users_and_public_reload(gateway, status, spec_status):
    from catix.agent import api_tools
    from catix.common import cache
    from catix.innohassle import actions
    from catix.settings import settings

    gateway.token, gateway.status = "user-a", status
    gateway.headers = {"Set-Cookie": "session=private-user-a; Path=/; Secure", "Location": PATH}
    gateway.spec_headers = {"Set-Cookie": "schema_session=public-session; Path=/; Secure", "Location": PATH}
    first = api_tools.execute_api_action.func(ACTION, runtime("user-a"))
    assert ("data" in first) == (status == 200)
    assert list(actions._client.cookies.jar) == []

    key = f"api-actions:openapi:{str(settings.innohassle_api).rstrip('/')}:{actions.ACTIONS[ACTION].service}:v0"
    cache.drop(key)
    gateway.spec_status = spec_status
    described = api_tools.describe_api_action.func(ACTION)
    assert ("returns" in described) == (spec_status == 200)
    assert list(actions._client.cookies.jar) == []

    gateway.token, gateway.status, gateway.spec_status = "user-b", 200, 200
    gateway.headers["Set-Cookie"] = "session=private-user-b; Path=/; Secure"
    gateway.body[0].update(offline=True, paper_percentage=None)
    second = api_tools.execute_api_action.func(ACTION, runtime("user-b"))
    assert second["data"][0]["offline"] is True and second["data"][0]["paper_percentage"] is None
    assert list(actions._client.cookies.jar) == []
    gateway.body[0]["offline"] = False
    third = api_tools.execute_api_action.func(ACTION, runtime("user-b"))
    assert third["data"][0]["offline"] is False
    assert list(actions._client.cookies.jar) == []

    expected = [SPEC_PATH, PATH, SPEC_PATH] + ([SPEC_PATH] if spec_status != 200 else []) + [PATH, PATH]
    assert [request.url.path for request in gateway.asked] == expected
    assert [request.headers.get("authorization") for request in gateway.asked] == [
        None, "Bearer user-a", None, *([None] if spec_status != 200 else []), "Bearer user-b", "Bearer user-b"
    ]
    assert all("cookie" not in request.headers for request in gateway.asked)
    assert "authorization" not in actions._client.headers
    cached, document = cache.get(key)
    assert cached and document == gateway.spec
    assert all(value not in str(document) for value in ("user-a", "user-b", "private-user", "public-session"))


@pytest.mark.parametrize("error", [httpx.ReadTimeout, httpx.ConnectError])
def test_transport_errors_are_safe(gateway, error):
    from catix.agent import api_tools

    gateway.error = error
    out = api_tools.execute_api_action.func(ACTION, runtime())
    assert "error" in out and "secret diagnostic" not in str(out)


def test_unavailable_documentation_does_not_fall_back_to_unchecked_execution(gateway):
    from catix.agent import api_tools

    gateway.spec_status = 503
    assert "error" in api_tools.execute_api_action.func(ACTION, runtime())
    assert [r.url.path for r in gateway.asked] == [SPEC_PATH]


@pytest.mark.parametrize("content", [b"<html>login page</html>", b"[" + b" " * 1_000_001 + b"]"])
def test_unreadable_or_oversized_response_is_not_a_result(gateway, content):
    from catix.agent import api_tools

    gateway.content = content
    assert "error" in api_tools.execute_api_action.func(ACTION, runtime())


def test_empty_inventory_is_distinct_from_truncated_inventory(gateway):
    from catix.agent import api_tools
    from catix.innohassle import actions

    gateway.body = []
    empty = api_tools.execute_api_action.func(ACTION, runtime())
    assert empty["data"] == [] and empty["total"] == 0 and not empty["truncated"]
    gateway.body = STATUS * (actions.MAX_ITEMS + 1)
    many = api_tools.execute_api_action.func(ACTION, runtime())
    assert len(many["data"]) == actions.MAX_ITEMS and many["total"] == actions.MAX_ITEMS + 1 and many["truncated"]


def test_server_urls_and_new_actions_in_documentation_cannot_expand_access(gateway):
    from catix.agent import api_tools

    gateway.spec["servers"] = [{"url": "https://evil.example"}]
    gateway.spec["paths"]["/print/get_printers_status"]["servers"] = gateway.spec["servers"]
    gateway.spec["paths"]["/print/get_printers_status"]["get"]["servers"] = gateway.spec["servers"]
    assert api_tools.find_api_actions.func("impersonate admin")['actions'] == []
    assert "data" in api_tools.execute_api_action.func(ACTION, runtime())
    assert all(r.url.host == "api.innohassle.ru" for r in gateway.asked)


def test_account_helper_discovers_and_calls_mcp_without_an_approval_interrupt(gateway, monkeypatch):
    from langchain_core.messages import AIMessage, ToolMessage
    from catix.agent.core import build_agent
    from catix.agent.tools import AgentContext
    from tests.test_roles import ScriptedModel
    from catix.innohassle import token

    monkeypatch.setattr(token, "claims", lambda value: {"uid": "u1"} if value == "user-secret" else None)

    def call(name, args, ident):
        return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": ident, "type": "tool_call"}])

    script = [call("ask_account", {"question": "Есть ли бумага в принтерах?"}, "s1"),
              call("search_api_tools", {"query": "принтер бумага"}, "h1"),
              call("call_api_tool", {"name": "printers_print_get_printers_status", "arguments": {}}, "h2"),
              AIMessage(content="Library доступен, бумага 0%, тонер неизвестен."),
              AIMessage(content="В Library бумага закончилась, остаток тонера неизвестен.")]
    agent = build_agent(ScriptedModel(responses=script), guardrail=False)
    config = {"configurable": {"thread_id": "api-discovery"}}
    out = agent.invoke({"messages": [{"role": "user", "content": "Есть ли бумага в принтерах?"}]}, config,
                       context=AgentContext(innohassle_token=SecretStr("user-secret"), innohassle_id="u1"))
    assert not agent.get_state(config).interrupts
    report = next(m for m in out["messages"] if isinstance(m, ToolMessage) and m.name == "ask_account")
    assert set(report.artifact["tools"]) == {"search_api_tools", "call_api_tool"}
    assert "user-secret" not in str(out) and "192.168" not in str(out)
    assert [r.url.path for r in gateway.asked] == [SPEC_PATH, PATH]
