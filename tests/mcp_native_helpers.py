"""Exercise MCP without the cAtIx host, approval state, or client package."""
import asyncio
from contextlib import asynccontextmanager

from fastmcp import Client
from catix.innohassle import mcp_server


@asynccontextmanager
async def connection(remote=False, token=None, sport_token=None):
    root = await mcp_server.build_server()
    if remote:
        import httpx2
        from fastmcp.client.transports import StreamableHttpTransport
        from fastmcp.utilities.asgi_transport import StreamingASGITransport, run_asgi_lifespan

        app = root.http_app(stateless_http=True)
        headers = {}
        if token:
            headers['X-Innohassle-Token'] = token
        if sport_token:
            headers['X-Sport-Token'] = sport_token
        def factory(headers: dict[str, str] | None = None, timeout: httpx2.Timeout | None = None,
                    auth: httpx2.Auth | None = None, **kwargs) -> httpx2.AsyncClient:
            return httpx2.AsyncClient(transport=StreamingASGITransport(app), headers=headers, timeout=timeout, auth=auth, **kwargs)
        async with run_asgi_lifespan(app):
            transport = StreamableHttpTransport('http://testserver/mcp', headers=headers,
                                                httpx_client_factory=factory)
            async with Client(transport) as client:
                yield client
    else:
        with mcp_server.credentials(token, sport_token=sport_token):
            async with Client(root) as client:
                yield client


def call(name, arguments, *, token=None, sport_token=None, uid=None):
    # uid keeps explicit test identities readable; verified claims come from the
    # calling fixture, never from business arguments.
    async def run():
        async with connection(token=token, sport_token=sport_token) as client:
            return (await client.call_tool(name, arguments)).data
    return asyncio.run(run())
