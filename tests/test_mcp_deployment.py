"""The MCP HTTP lifecycle and local launcher behavior."""

import asyncio
import re
import shlex
import subprocess
from pathlib import Path

import httpx2

from catix.innohassle import mcp_server


def test_mcp_http_health_is_available_without_credentials():
    async def run():
        async with mcp_server.adapter() as server:
            app = server.http_app(stateless_http=True)
            async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app), base_url="http://127.0.0.1") as client:
                first = await client.get("/health")
                second = await client.get("/health")
                assert first.status_code == second.status_code == 200
                assert first.json() == second.json() == {"status": "ok"}

    asyncio.run(run())


def _launcher(command, *, ready=True, session=None):
    # Execute real lifecycle functions, replacing only OS/network side effects.
    source = Path("scripts/catix.sh").read_text().split('case "${1:-}" in', 1)[0]
    fake = '''
docker() { :; }
uv() {
  if [ "${3:-}" = python ]; then printf '%s\n' "$SYNTHETIC_MAX_SESSION"; else printf 'synthetic schema ready\n'; fi
}
check_models() { return 0; }
start_app() { printf 'START %s\n' "$*"; }
sleep() { :; }
running() { return 0; }
pkill() { printf 'STOP %s\\n' "$*"; }
USERBOT_SESSION=/nonexistent-synthetic-userbot-session
'''
    fake += 'health() { printf 200; }\n' if ready else 'health() { if [ "$1" = 8010 ]; then printf 000; else printf 200; fi; }\n'
    fake += 'SYNTHETIC_MAX_SESSION=' + shlex.quote(str(session or '/nonexistent-synthetic-max-session')) + '\n'
    return subprocess.run(["bash", "-c", source + fake + command, "scripts/catix.sh"], capture_output=True, text=True)


def test_local_up_waits_for_http_before_starting_callers():
    result = _launcher("up")
    assert result.returncode == 0, result.stderr
    assert re.findall(r"^START (.+)$", result.stdout, re.M) == [
        "catix-mcp", "catix-tgbot", "catix-worker", "catix-api",
    ]
    failed = _launcher("up", ready=False)
    assert failed.returncode != 0
    assert re.findall(r"^START (.+)$", failed.stdout, re.M) == ["catix-mcp"]


def test_local_up_starts_max_only_with_saved_session(tmp_path):
    session = tmp_path / "private account.db"
    session.touch()
    result = _launcher("up", session=session)
    assert result.returncode == 0, result.stderr
    assert re.findall(r"^START (.+)$", result.stdout, re.M)[-1] == "catix-maxuserbot listen"


def test_local_down_stops_mcp_last():
    result = _launcher("down")
    assert result.returncode == 0, result.stderr
    stopped = re.findall(r"^STOP .*?(catix-[a-z]+)", result.stdout, re.M)
    assert stopped[-1] == "catix-mcp"
    assert {"catix-api", "catix-maxuserbot"} <= set(stopped[:-1])
