"""The MCP catalogue has one HTTP-server lifecycle and private deployment wiring."""

import asyncio
import re
import subprocess
from pathlib import Path

import httpx2
import yaml

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


def test_production_mcp_is_private_and_agent_apps_wait_for_it():
    config = yaml.safe_load(Path("docker-compose.prod.yml").read_text())
    services = config["services"]
    assert "mcp" in services, "Production needs a persistent MCP service"
    mcp = services["mcp"]
    assert mcp["command"] == ["catix-mcp", "--host", "0.0.0.0", "--port", "8010"]
    assert not mcp.get("ports"), "MCP must not be published on the host or public interface"
    assert "/health" in str(mcp["healthcheck"]["test"])
    assert "mcp" not in mcp["depends_on"], "No inherited self-dependency"
    for name in ("api", "tgbot", "maxbot"):
        assert services[name]["environment"]["INNOHASSLE_MCP_URL"] == "http://mcp:8010/mcp"
        assert services[name]["depends_on"]["mcp"] == {"condition": "service_healthy"}
        assert services[name]["environment"]["REDIS_URL"] == mcp["environment"]["REDIS_URL"]


def test_local_launcher_manages_mcp_before_agents():
    text = Path("scripts/catix.sh").read_text()
    assert "APPS=(catix-mcp " in text
    assert "health 8010" in text
    assert '{mcp,tgbot,maxbot,worker,api,tguserbot}.log' in text


def _launcher(command, *, ready=True):
    # Execute real lifecycle functions, replacing only OS/network side effects.
    source = Path("scripts/catix.sh").read_text().split('case "${1:-}" in', 1)[0]
    fake = '''
docker() { :; }
uv() { printf 'synthetic schema ready\\n'; }
check_models() { return 0; }
start_app() { printf 'START %s\\n' "$1"; }
sleep() { :; }
running() { return 0; }
pkill() { printf 'STOP %s\\n' "$*"; }
USERBOT_SESSION=/nonexistent-synthetic-userbot-session
'''
    fake += 'health() { printf 200; }\n' if ready else 'health() { if [ "$1" = 8010 ]; then printf 000; else printf 200; fi; }\n'
    return subprocess.run(["bash", "-c", source + fake + command, "scripts/catix.sh"], capture_output=True, text=True)


def test_local_up_waits_for_http_before_starting_callers():
    result = _launcher("up")
    assert result.returncode == 0, result.stderr
    assert re.findall(r"^START (.+)$", result.stdout, re.M) == [
        "catix-mcp", "catix-tgbot", "catix-maxbot", "catix-worker", "catix-api",
    ]
    failed = _launcher("up", ready=False)
    assert failed.returncode != 0
    assert re.findall(r"^START (.+)$", failed.stdout, re.M) == ["catix-mcp"]


def test_local_down_stops_mcp_last():
    result = _launcher("down")
    assert result.returncode == 0, result.stderr
    stopped = re.findall(r"^STOP .*?(catix-[a-z]+)", result.stdout, re.M)
    assert stopped[-1] == "catix-mcp" and "catix-api" in stopped[:-1]
