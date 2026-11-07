"""Explicit test-only MCP HTTP harness; production never creates a server."""

from contextlib import asynccontextmanager
from contextvars import ContextVar

from fastmcp.utilities.asgi_transport import StreamingASGITransport, run_asgi_lifespan

from catix.innohassle import mcp_client, mcp_server
from catix.settings import settings


def install_http_adapter(monkeypatch):
    """Run the real production connection over ASGI, without sockets or upstream I/O.

    The caller supplies synthetic action/backend/auth fixtures. Each invocation owns
    its test server lifespan; ContextVar routing isolates parallel graph requests.
    """
    current_app = ContextVar("test_mcp_http_app")
    original_connection = mcp_client._connection
    original_http = mcp_client._http_client
    monkeypatch.setattr(settings, "innohassle_mcp_url", "http://127.0.0.1:8010/mcp")

    def factory(**kwargs):
        return original_http(transport=StreamingASGITransport(current_app.get()), **kwargs)

    @asynccontextmanager
    async def connection(token, **kwargs):
        async with mcp_server.adapter() as root:
            app = root.http_app(stateless_http=True)
            async with run_asgi_lifespan(app):
                scope = current_app.set(app)
                try:
                    async with original_connection(token, **kwargs) as client:
                        yield client
                finally:
                    current_app.reset(scope)

    monkeypatch.setattr(mcp_client, "_http_client", factory)
    monkeypatch.setattr(mcp_client, "_connection", connection)
