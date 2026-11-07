"""Protocol tests: generated tools use only the reviewed executor, never the network."""

import asyncio
from types import SimpleNamespace

import pytest
from fastmcp import Client, FastMCP

from catix.innohassle import actions


@pytest.fixture
def policy(monkeypatch):
    entries = {}
    descriptions = {}
    calls = []
    for service, field, protected in [
        ("maps", "room", False), ("clubs", "club", False),
        ("music-room", "instrument", False), ("printers", "printer", True),
    ]:
        namespace = "music" if service == "music-room" else service
        action_id = f"{namespace}.list"
        entries[action_id] = SimpleNamespace(
            action_id=action_id, service=service, namespace=namespace, method="GET",
            path="/list", prefix=f"/{service}/v0", query_parameters=("limit",),
            requires_token=protected, keywords=f"{namespace} availability", note="Read only.",
        )
        descriptions[action_id] = {
            "action_id": action_id, "description": f"List {namespace} availability",
            "method": "GET", "path": f"/{service}/v0/list",
            "parameters": {"type": "object", "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 5}},
                "additionalProperties": False},
            "returns": {"type": "array", "items": {"type": "object",
                "properties": {field: {"type": "string"}}, "required": [field]}},
            "requires_sign_in": protected, "read_only": True, "note": "Read only.",
        }

    def execute(action_id, parameters, token):
        calls.append((action_id, parameters, token))
        field = next(iter(descriptions[action_id]["returns"]["items"]["properties"]))
        return {"action_id": action_id, "data": [{field: "visible"}],
                "total": 1, "truncated": False, "note": "Read only."}

    monkeypatch.setattr(actions, "ACTIONS", entries)
    monkeypatch.setattr(actions, "describe", lambda name: descriptions[name])
    monkeypatch.setattr(actions, "execute", execute)
    return SimpleNamespace(entries=entries, descriptions=descriptions, calls=calls)


def test_real_generated_tools_search_and_call(policy, monkeypatch):
    from catix.innohassle import mcp_server

    generated = []
    original = FastMCP.from_openapi.__func__

    def generate(cls, *args, **kwargs):
        generated.append(kwargs.get("openapi_spec", args[0] if args else None))
        return original(cls, *args, **kwargs)

    monkeypatch.setattr(FastMCP, "from_openapi", classmethod(generate))

    async def run():
        async with mcp_server.adapter() as root, Client(root) as client:
            assert {tool.name for tool in await client.list_tools()} == {
                "search_tools", "call_tool", "service_status"}
            results = (await client.call_tool("search_tools", {"query": "maps"})).data
            found = next(tool for tool in results if tool["name"] == "maps_list")
            assert found["inputSchema"]["properties"]["limit"]["type"] == "integer"
            assert "outputSchema" in found
            protected = (await client.call_tool("search_tools", {"query": "printers"})).data
            printer = next(tool for tool in protected if tool["name"] == "printers_list")
            assert "Sign-in required" in printer["description"]
            assert "Read only." in printer["description"]
            reply = await client.call_tool("call_tool", {
                "name": found["name"], "arguments": {"limit": 2}})
            assert reply.data["data"] == [{"room": "visible"}]
            assert policy.calls == [("maps.list", {"limit": 2}, None)]

    asyncio.run(run())
    assert len(generated) == 4
    assert all(len(spec["paths"]) == 1 for spec in generated)


def test_credentials_are_scoped_and_public_reads_do_not_delegate(policy, monkeypatch):
    from catix.innohassle import mcp_server, token

    validated = []

    def claims(value):
        validated.append(value)
        return {"uid": value} if value in {"alice", "bob"} else {"uid": ""}

    monkeypatch.setattr(token, "claims", claims)

    async def run():
        async with mcp_server.adapter() as root:
            async with Client(root) as client:
                for name, args in [("printers_list", {}), ("call_tool", {"name": "printers_list"})]:
                    result = await client.call_tool(name, args, raise_on_error=False)
                    assert result.is_error
                    assert "sign in" in str(result.content).lower()
            assert policy.calls == []

            async def user(value):
                with mcp_server.credentials(value):
                    async with Client(root) as client:
                        result = await client.call_tool("call_tool", {"name": "printers_list"}, raise_on_error=False)
                        await client.call_tool("maps_list", {})
                        return result

            alice, bob = await asyncio.gather(user("alice"), user("bob"))
            assert not alice.is_error and not bob.is_error
            assert sorted(call[2] for call in policy.calls if call[0] == "printers.list") == ["alice", "bob"]
            assert all(call[2] is None for call in policy.calls if call[0] == "maps.list")
            before = len(policy.calls)
            with mcp_server.credentials("invalid"):
                async with Client(root) as client:
                    result = await client.call_tool("printers_list", {}, raise_on_error=False)
                    assert result.is_error
                    assert "invalid" not in str(result.content) or "sign" in str(result.content).lower()
            assert len(policy.calls) == before
            async with Client(root) as client:
                assert (await client.call_tool("printers_list", {}, raise_on_error=False)).is_error
            assert len(policy.calls) == before

    asyncio.run(run())
    assert {"alice", "bob", "invalid"} <= set(validated)


def test_namespace_collisions_and_validation(policy):
    from catix.innohassle import mcp_server

    async def run():
        async with mcp_server.adapter() as root, Client(root) as client:
            for namespace, field in [("maps", "room"), ("clubs", "club"), ("music", "instrument")]:
                definitions = (await client.call_tool("search_tools", {"query": namespace})).data
                definition = next(item for item in definitions if item["name"] == f"{namespace}_list")
                assert field in str(definition["outputSchema"])
                assert (await client.call_tool(f"{namespace}_list", {})).data["data"] == [{field: "visible"}]
            before = len(policy.calls)
            for name, args in [("maps_list", {"limit": 0}), ("maps_list", {"limit": "2"}),
                               ("maps_list", {"token": "model-token"}), ("maps_delete", {}),
                               ("printers_print", {})]:
                result = await client.call_tool(name, args, raise_on_error=False)
                assert result.is_error, (name, args, result)
                result = await client.call_tool("call_tool", {"name": name, "arguments": args}, raise_on_error=False)
                assert result.is_error
            assert len(policy.calls) == before

    asyncio.run(run())


def test_unavailable_components_are_visible_and_owned_clients_close(policy, monkeypatch, caplog):
    import httpx2
    from catix.innohassle import mcp_server

    original_describe = actions.describe
    original_generate = FastMCP.from_openapi.__func__
    original_client = httpx2.AsyncClient
    owned = []

    def describe(name):
        if name.startswith("clubs."):
            raise RuntimeError("sensitive schema failure")
        return original_describe(name)

    def generate(cls, *args, **kwargs):
        if kwargs["name"] == "music-room":
            raise RuntimeError("sensitive conversion failure")
        return original_generate(cls, *args, **kwargs)

    class TrackedClient(original_client):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            owned.append(self)

    monkeypatch.setattr(actions, "describe", describe)
    monkeypatch.setattr(FastMCP, "from_openapi", classmethod(generate))
    monkeypatch.setattr(httpx2, "AsyncClient", TrackedClient)

    async def run():
        async with mcp_server.adapter() as root, Client(root) as client:
            status = (await client.call_tool("service_status", {})).data
            assert set(status) == {"maps", "clubs", "music", "printers"}
            assert status["maps"]["available"]
            assert not status["clubs"]["available"] and not status["music"]["available"]
            assert "unavailable" in status["clubs"]["message"].lower()
            assert "sensitive" not in str(status)
            assert (await client.call_tool("maps_list", {})).data["data"] == [{"room": "visible"}]
            for service in ["clubs", "music"]:
                assert (await client.call_tool(f"{service}_list", {}, raise_on_error=False)).is_error
                results = (await client.call_tool("search_tools", {"query": service})).data
                assert not any(item["name"] == f"{service}_list" for item in results)
        assert owned and all(client.is_closed for client in owned)

    asyncio.run(run())
    assert "sensitive" not in caplog.text


@pytest.mark.parametrize("interface", ["protocol", "request_sync"])
def test_slow_components_do_not_block_healthy_tools(policy, monkeypatch, interface):
    import threading
    from catix.innohassle import mcp_client, mcp_server

    # Put healthy services after blocked ones: neither ordering nor fast failure
    # may be what allows the healthy tool to execute.
    monkeypatch.setattr(actions, "ACTIONS", {
        name: policy.entries[name]
        for name in ("music.list", "printers.list", "maps.list", "clubs.list")
    })
    monkeypatch.setattr(mcp_server, "COMPONENT_INIT_TIMEOUT", 0.05, raising=False)
    monkeypatch.setattr(mcp_client, "TIMEOUT", 1)
    monkeypatch.setattr(mcp_client.settings, "innohassle_mcp_url", None)
    blocked = {name: threading.Event() for name in ("music.list", "printers.list")}
    release = threading.Event()
    original_execute = actions.execute

    def describe(name):
        if name in blocked:
            blocked[name].set()
            assert release.wait(3), "test failed to release the blocked description worker"
            raise actions.ActionError("sensitive unavailable upstream")
        return policy.descriptions[name]

    def execute(*args):
        # Both components must have started, without waiting for either to fail.
        assert all(event.is_set() for event in blocked.values())
        assert not release.is_set()
        result = original_execute(*args)
        release.set()
        return result

    monkeypatch.setattr(actions, "describe", describe)
    monkeypatch.setattr(actions, "execute", execute)

    async def protocol():
        try:
            async with asyncio.timeout(1):
                async with mcp_server.adapter() as root, Client(root) as client:
                    status = (await client.call_tool("service_status", {})).data
                    assert list(status) == ["music", "printers", "maps", "clubs"]
                    assert all(status[name]["available"] for name in ("maps", "clubs"))
                    for name in ("music", "printers"):
                        assert not status[name]["available"]
                        assert status[name]["tools"] == 0
                        assert "sensitive" not in str(status[name])
                    result = await client.call_tool("call_tool", {"name": "maps_list"})
                    return result.data
        finally:
            release.set()

    try:
        if interface == "protocol":
            result = asyncio.run(protocol())
        else:
            # asyncio.run waits for default-executor workers on shutdown, even
            # after cancellation. Release them on failure as well as execution.
            timer = threading.Timer(1.5, release.set)
            timer.start()
            try:
                result = mcp_client.request_sync("call_tool", {"name": "maps_list"})
            finally:
                timer.cancel()
        assert result["data"] == [{"room": "visible"}], result
        assert policy.calls == [("maps.list", {}, None)]
    finally:
        release.set()


def test_http_credentials_are_per_request_and_never_from_meta_or_other_headers(policy, monkeypatch, caplog):
    import httpx2
    from fastmcp.client.transports import StreamableHttpTransport
    from fastmcp.utilities.asgi_transport import StreamingASGITransport, run_asgi_lifespan
    from catix.innohassle import mcp_server, token

    monkeypatch.setattr(token, "claims", lambda value: {"uid": value} if value in {"alice-secret", "bob-secret"} else None)

    async def run():
        async with mcp_server.adapter() as root:
            app = root.http_app(stateless_http=True)
            async with run_asgi_lifespan(app):
                async def user(value):
                    clients = []

                    def factory(**kwargs):
                        client = httpx2.AsyncClient(transport=StreamingASGITransport(app), **kwargs)
                        clients.append(client)
                        return client

                    transport = StreamableHttpTransport("http://testserver/mcp", headers={
                        "X-Innohassle-Token": value,
                        "Authorization": "Bearer unrelated-secret", "Cookie": "session=unrelated-secret",
                    }, httpx_client_factory=factory)
                    async with Client(transport) as client:
                        await client.list_tools()
                        await client.call_tool("search_tools", {"query": "printers"})
                        assert not (await client.call_tool("call_tool", {"name": "printers_list"})).is_error
                        await client.call_tool("maps_list", {})
                        # Change credentials on the SAME wire session: no identity cache.
                        for http in clients:
                            http.headers.pop("x-innohassle-token", None)
                        result = await client.call_tool("printers_list", {}, raise_on_error=False,
                            meta={"token": value, "uid": value, "x-innohassle-token": value})
                        assert result.is_error
                        assert "sign in" in str(result.content).lower()
                        # Authorization and Cookie never become upstream identity.
                        await client.call_tool("maps_list", {})
                        for http in clients:
                            http.headers["x-innohassle-token"] = "bad-secret"
                        assert (await client.call_tool("maps_list", {}, raise_on_error=False)).is_error
                        assert (await client.call_tool("call_tool", {"name": "printers_list"}, raise_on_error=False)).is_error

                with mcp_server.credentials("process-admin-secret"):
                    await asyncio.gather(user("alice-secret"), user("bob-secret"))
        assert sorted(call[2] for call in policy.calls if call[0] == "printers.list") == ["alice-secret", "bob-secret"]
        assert len([call for call in policy.calls if call[0] == "maps.list"]) == 4
        assert all(call[2] is None for call in policy.calls if call[0] == "maps.list")

    asyncio.run(run())
    assert not any(secret in caplog.text for secret in ["alice-secret", "bob-secret", "bad-secret", "unrelated-secret", "process-admin-secret"])


def test_realistic_nullable_query_schemas_and_formats(policy):
    from catix.innohassle import mcp_server

    parameters = {
        "type": "object", "properties": {
            "from": {"anyOf": [{"type": "string", "format": "date-time"}, {"type": "null"}]},
            "club": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
            "query": {"type": "string"},
        }, "additionalProperties": False,
    }
    policy.descriptions["maps.list"]["parameters"] = parameters
    policy.entries["maps.list"].query_parameters = ("from", "club", "query")

    async def run():
        async with mcp_server.adapter() as root, Client(root) as client:
            args = {"from": "2026-11-07T12:00:00+03:00", "club": 3, "query": "Принтер & room"}
            assert not (await client.call_tool("maps_list", args)).is_error
            assert policy.calls == [("maps.list", args, None)]
            for value in ["not-a-date", "2026-99-99T12:00:00", "2026-11-07"]:
                result = await client.call_tool("call_tool", {"name": "maps_list", "arguments": {"from": value}}, raise_on_error=False)
                assert result.is_error
            assert len(policy.calls) == 1

    asyncio.run(run())


@pytest.mark.parametrize("arguments,expected", [
    ({"club": None, "query": None}, {}),
    ({"club": 0, "query": ""}, {"club": 0, "query": ""}),
    ({"query": "null"}, {"query": "null"}),
])
def test_nullable_protocol_parameters_omit_only_none(policy, arguments, expected):
    from catix.innohassle import mcp_server

    policy.descriptions["maps.list"]["parameters"] = {
        "type": "object", "properties": {
            "club": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
            "query": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        }, "additionalProperties": False,
    }
    policy.entries["maps.list"].query_parameters = ("club", "query")

    async def run():
        async with mcp_server.adapter() as root, Client(root) as client:
            result = await client.call_tool("call_tool", {"name": "maps_list", "arguments": arguments})
            assert not result.is_error
            assert policy.calls == [("maps.list", expected, None)]

    asyncio.run(run())


def test_policy_transport_rejects_arbitrary_requests_and_ignores_headers(policy):
    import httpx2
    from fastmcp.exceptions import ToolError
    from catix.innohassle import mcp_server

    async def run():
        transport = mcp_server._PolicyTransport({"maps.list": policy.descriptions["maps.list"]})
        async with httpx2.AsyncClient(transport=transport) as client:
            good = "https://catix-policy.invalid/maps/v0/list"
            response = await client.get(good, params={"limit": 2}, headers={
                "Authorization": "Bearer secret", "Cookie": "session=secret", "X-Innohassle-Token": "secret"})
            assert response.json()["data"] == [{"room": "visible"}]
            for method, url, kwargs in [
                ("POST", good, {}), ("DELETE", good, {}), ("GET", good, {"content": b"body"}),
                ("GET", "https://evil.test/maps/v0/list", {}),
                ("GET", "http://catix-policy.invalid/maps/v0/list", {}),
                ("GET", "https://catix-policy.invalid:444/maps/v0/list", {}),
                ("GET", "https://catix-policy.invalid/clubs/v0/list", {}),
                ("GET", good + "?limit=1&limit=2", {}), ("GET", good + "?token=secret", {}),
                ("GET", "https://catix-policy.invalid/maps/v0/%6cist", {}),
            ]:
                with pytest.raises(ToolError):
                    await client.request(method, url, **kwargs)
            assert policy.calls == [("maps.list", {"limit": 2}, None)]

    asyncio.run(run())


@pytest.mark.parametrize("change,value", [("method", "POST"), ("path", "/clubs/v0/list"),
                                          ("read_only", False), ("requires_sign_in", True)])
def test_document_cannot_change_code_owned_policy(policy, change, value):
    from catix.innohassle import mcp_server

    policy.descriptions["maps.list"][change] = value

    async def run():
        async with mcp_server.adapter() as root, Client(root) as client:
            status = (await client.call_tool("service_status", {})).data
            assert not status["maps"]["available"]
            assert (await client.call_tool("maps_list", {}, raise_on_error=False)).is_error
            assert policy.calls == []

    asyncio.run(run())


def test_main_serves_loopback_http_by_default(policy, monkeypatch):
    import sys
    from catix.innohassle import mcp_server

    options = []

    async def serve(self, **kwargs):
        options.append(kwargs)
        async with Client(self) as client:
            assert (await client.call_tool("service_status", {})).data["maps"]["available"]

    monkeypatch.setattr(FastMCP, "run_async", serve)
    monkeypatch.setattr(sys, "argv", ["catix-mcp"])
    mcp_server.main()
    assert options == [{"transport": "http", "host": "127.0.0.1", "port": 8010,
                        "path": "/mcp", "stateless_http": True, "show_banner": False}]


@pytest.mark.parametrize("safe", [True, False])
def test_executor_errors_are_useful_but_never_leak_diagnostics(policy, monkeypatch, caplog, safe):
    from catix.innohassle import mcp_server

    def fail(*args):
        if safe:
            raise actions.ActionError("This account does not have permission for that API action.")
        raise RuntimeError("upstream-secret-body-token")

    monkeypatch.setattr(actions, "execute", fail)

    async def run():
        async with mcp_server.adapter() as root, Client(root) as client:
            result = await client.call_tool("call_tool", {"name": "maps_list"}, raise_on_error=False)
            assert result.is_error
            if safe:
                assert "permission" in str(result.content)
            else:
                assert "unavailable" in str(result.content).lower()
            assert "upstream-secret" not in str(result)

    asyncio.run(run())
    assert "upstream-secret" not in caplog.text


def test_operation_ids_keep_double_underscores_and_validation(policy):
    from catix.innohassle import mcp_server

    action = policy.entries.pop("clubs.list")
    action.action_id = "clubs.get_clubs_list_clubs__get"
    policy.entries[action.action_id] = action
    description = policy.descriptions.pop("clubs.list")
    description["action_id"] = action.action_id
    policy.descriptions[action.action_id] = description

    async def run():
        async with mcp_server.adapter() as root, Client(root) as client:
            results = (await client.call_tool("search_tools", {"query": "clubs"})).data
            assert any(tool["name"] == "clubs_get_clubs_list_clubs__get" for tool in results)
            assert not (await client.call_tool("clubs_get_clubs_list_clubs__get", {"limit": 2})).is_error
            assert (await client.call_tool("clubs_get_clubs_list_clubs__get", {"limit": "2"}, raise_on_error=False)).is_error
            assert policy.calls == [(action.action_id, {"limit": 2}, None)]

    asyncio.run(run())


@pytest.mark.parametrize("stop", ["cancel", "timeout"])
def test_prepared_clients_are_owned_before_component_join(policy, monkeypatch, stop):
    import httpx2
    from contextlib import AsyncExitStack
    from catix.innohassle import mcp_server

    original_client = httpx2.AsyncClient
    original_list = FastMCP.list_tools
    owned = []

    class TrackedClient(original_client):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            owned.append(self)

    monkeypatch.setattr(httpx2, "AsyncClient", TrackedClient)
    monkeypatch.setattr(mcp_server, "COMPONENT_INIT_TIMEOUT", 0.1 if stop == "timeout" else 10)

    async def run():
        completed = asyncio.Event()
        all_entered = asyncio.Event()
        entered = set()
        clients_by_service = {}
        original_generate = FastMCP.from_openapi.__func__

        def generate(cls, *args, **kwargs):
            clients_by_service[kwargs["name"]] = kwargs["client"]
            return original_generate(cls, *args, **kwargs)

        async def list_tools(self, *args, **kwargs):
            if self.name in {"maps", "clubs", "music-room", "printers"}:
                entered.add(self.name)
                if len(entered) == 4:
                    all_entered.set()
                if self.name == "maps":
                    # Signal only after the preparation task has actually exited,
                    # not just after creating its client or listing its tools.
                    task = asyncio.current_task()
                    assert task is not None
                    task.add_done_callback(lambda _: completed.set())
                else:
                    await asyncio.Event().wait()
            return await original_list(self, *args, **kwargs)

        monkeypatch.setattr(FastMCP, "from_openapi", classmethod(generate))
        monkeypatch.setattr(FastMCP, "list_tools", list_tools)
        async with AsyncExitStack() as stack:
            build = asyncio.create_task(mcp_server.build_server(stack=stack))
            try:
                async with asyncio.timeout(1):
                    await all_entered.wait()
                    await completed.wait()
                assert len(owned) == 4
                assert not clients_by_service["maps"].is_closed
                if stop == "cancel":
                    build.cancel()
                    with pytest.raises(asyncio.CancelledError):
                        await build
                    # Check before the caller's stack exits: even completed,
                    # uncollected components belong to the cancelled builder.
                    assert all(client.is_closed for client in owned)
                else:
                    root = await build
                    assert all(client.is_closed for service, client in clients_by_service.items() if service != "maps")
                    assert not clients_by_service["maps"].is_closed
                    async with Client(root) as client:
                        status = (await client.call_tool("service_status", {})).data
                        assert status["maps"]["available"]
                        assert all(not status[name]["available"] for name in ("clubs", "music", "printers"))
                        assert (await client.call_tool("maps_list", {})).data["data"] == [{"room": "visible"}]
            finally:
                if not build.done():
                    build.cancel()
                    with pytest.raises(asyncio.CancelledError):
                        await build
        assert all(client.is_closed for client in owned)

    asyncio.run(run())


def test_clients_close_on_cancellation(policy, monkeypatch):
    import httpx2
    from catix.innohassle import mcp_server

    original = httpx2.AsyncClient
    owned = []

    class TrackedClient(original):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            owned.append(self)

    monkeypatch.setattr(httpx2, "AsyncClient", TrackedClient)

    async def run():
        with pytest.raises(asyncio.CancelledError):
            async with mcp_server.adapter() as root, Client(root) as client:
                assert (await client.call_tool("service_status", {})).data["maps"]["available"]
                raise asyncio.CancelledError()
        assert len(owned) == 4 and all(client.is_closed for client in owned)

    asyncio.run(run())
