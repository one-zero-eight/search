#!/usr/bin/env bash
# Starts, stops and checks everything cAtIx needs. Run from anywhere.
#   scripts/catix.sh up [--tunnel]   docker (db, redis) -> schema -> SSH tunnel to the GPU server -> model check -> apps
#   scripts/catix.sh down            stops the apps (docker and the SSH tunnel stay)
#   scripts/catix.sh status          what runs and what answers
#   scripts/catix.sh logs [app]      follows a log (mcp, tgbot, maxuserbot, worker, api, tguserbot; default: all)
# --tunnel also starts a `tuna` tunnel (tuna.am) to the HTTP API (catix-api, API_PORT) for the calendar
# (https://<address>/users/my-calendar.ics) and prints the address.
# TUNA_SUBDOMAIN (environment or .env) pins the address: your permanent free domain, shown by tuna on start, e.g. grand-tundra-5389.
# The Telegram userbot (reads chats under your own account) starts only after `uv run catix-tguserbot login` was done once.
# The MAX account listener starts only with an existing MAX_SESSION (operator QR login first).
set -euo pipefail

cd "$(dirname "$0")/.."
LOGS=data/logs
APPS=(catix-mcp catix-tgbot catix-worker catix-api)
USERBOT=catix-tguserbot
USERBOT_SESSION=data/telegram.session
MAX_ACCOUNT=catix-maxuserbot
GPU_HOST=inh-compute
mkdir -p "$LOGS"

running() { pgrep -f "[b]in/$1( |\$)" > /dev/null; }
health() { curl -s -m 5 -o /dev/null -w '%{http_code}' "http://localhost:$1/health" 2> /dev/null || true; }
ok() { printf '  \033[32mok\033[0m   %s\n' "$*"; }
bad() { printf '  \033[31mFAIL\033[0m %s\n' "$*"; }
logfile() { echo "$LOGS/${1#catix-}.log"; }
tunnel_running() { pgrep -f "[t]una http" > /dev/null; }
tunnel_url() { grep -o 'Forwarding https://[^ ]*' "$LOGS/tunnel.log" 2> /dev/null | tail -1 | cut -d' ' -f2 || true; }
tuna_subdomain() { echo "${TUNA_SUBDOMAIN:-$(grep -E '^TUNA_SUBDOMAIN=' .env 2> /dev/null | cut -d= -f2- | tr -d "\"'")}"; }
api_port() { local port="${API_PORT:-$(grep -E '^API_PORT=' .env 2> /dev/null | cut -d= -f2- | tr -d "\"'")}"; echo "${port:-8000}"; }
max_account_session() { uv run --quiet python -c 'from catix.settings import settings; print(settings.max_session)'; }

check_models() {
  local failed=0
  for pair in "8080:chat model" "8081:embeddings"; do
    port=${pair%%:*}; name=${pair#*:}
    if [ "$(health "$port")" = 200 ]; then ok "$name (localhost:$port)"; else bad "$name (localhost:$port) does not answer"; failed=1; fi
  done
  return $failed
}

start_app() { # start_app <command> [args...]
  local app=$1; shift
  if running "$app"; then ok "$app already running"; return; fi
  nohup uv run --quiet "$app" "$@" > "$(logfile "$app")" 2>&1 &
  sleep 4
  if running "$app"; then ok "$app started (log: $(logfile "$app"))"; else bad "$app exited, see $(logfile "$app")"; fi
}

up() {
  echo "1/5 docker (postgres, redis, phoenix)"
  docker compose up -d --wait db redis > /dev/null && ok "db, redis healthy"
  docker compose up -d phoenix > /dev/null && ok "phoenix (traces: http://localhost:6006)"

  echo "2/5 database schema"
  uv run --quiet catix-db init 2>&1 | grep -v WARNING | tail -1

  echo "3/5 SSH tunnel to $GPU_HOST"
  if [ "$(health 8080)" = 200 ] && [ "$(health 8081)" = 200 ]; then
    ok "models already reachable"
  else
    ssh -o BatchMode=yes -o ConnectTimeout=10 -fN -L 8080:localhost:8080 -L 8081:localhost:8081 "$GPU_HOST" 2> /dev/null \
      || echo "  (tunnel not started: it may already exist)"
  fi

  echo "4/5 models"
  if ! check_models; then
    echo "The llama.cpp servers on $GPU_HOST are not running: start them there, then run this again."
    exit 1
  fi

  echo "5/5 apps"
  start_app catix-mcp
  local ready=0
  for _ in $(seq 30); do
    if [ "$(health 8010)" = 200 ]; then ready=1; break; fi
    sleep 1
  done
  if [ "$ready" != 1 ]; then bad "MCP (localhost:8010) is not ready; see $(logfile catix-mcp)"; return 1; fi
  ok "MCP ready (http://127.0.0.1:8010/mcp)"
  for app in "${APPS[@]:1}"; do start_app "$app"; done
  if [ -f "$USERBOT_SESSION" ]; then
    start_app "$USERBOT" listen
  else
    echo "  $USERBOT skipped: no Telegram session yet (uv run catix-tguserbot login)"
  fi
  local max_session
  max_session=$(max_account_session)
  if [ -f "$max_session" ]; then
    start_app "$MAX_ACCOUNT" listen
  else
    echo "  $MAX_ACCOUNT skipped: no MAX session yet (uv run catix-maxuserbot login)"
  fi

  if [ "${1:-}" = "--tunnel" ]; then
    if tunnel_running; then
      ok "tuna already running: $(tunnel_url)"
    else
      : > "$LOGS/tunnel.log"
      subdomain=$(tuna_subdomain)
      nohup tuna http "$(api_port)" --log "$LOGS/tunnel.log" --no-colors ${subdomain:+--subdomain="$subdomain"} > /dev/null 2>&1 &
      for _ in $(seq 20); do
        url=$(tunnel_url)
        [ -n "$url" ] && break
        sleep 1
      done
      ok "tunnel: ${url:-no address yet, see $LOGS/tunnel.log}"
      [ -n "$url" ] && echo "  calendar: $url/users/my-calendar.ics (Authorization: Bearer <InNoHassle token>)"
      [ -n "$subdomain" ] || echo "  (random address: set TUNA_SUBDOMAIN to keep it between restarts)"
    fi
  fi
}

down() {
  # Stop callers before their MCP dependency.
  for app in "${APPS[@]:1}" "$USERBOT" "$MAX_ACCOUNT" catix-mcp; do
    if running "$app"; then pkill -f "[b]in/$app( |\$)" && ok "$app stopped"; else echo "  $app not running"; fi
  done
}

status() {
  echo "docker:"; docker compose ps --format '  {{.Service}}: {{.Status}}' db redis phoenix
  echo "models:"; check_models || true
  echo "apps:"
  for app in "${APPS[@]}"; do if running "$app"; then ok "$app"; else bad "$app is not running"; fi; done
  if [ "$(health 8010)" = 200 ]; then ok "MCP HTTP (localhost:8010)"; else bad "MCP HTTP (localhost:8010) does not answer"; fi
  if running "$USERBOT"; then ok "$USERBOT"; elif [ -f "$USERBOT_SESSION" ]; then bad "$USERBOT is not running"; else echo "  $USERBOT: no session yet (login first)"; fi
  local max_session
  max_session=$(max_account_session)
  if running "$MAX_ACCOUNT"; then ok "$MAX_ACCOUNT"; elif [ -f "$max_session" ]; then bad "$MAX_ACCOUNT is not running"; else echo "  $MAX_ACCOUNT: no session yet (uv run catix-maxuserbot login)"; fi
  if tunnel_running; then ok "tuna: $(tunnel_url)"; else echo "  tuna not running (only needed for the calendar from outside: up --tunnel)"; fi
  echo "database:"; uv run --quiet catix-db status 2>&1 | grep -v WARNING | sed 's/^/  /' | head -8
}

logs() {
  if [ -n "${1:-}" ]; then tail -f "$LOGS/$1.log"; else tail -f "$LOGS"/{mcp,tgbot,maxuserbot,worker,api,tguserbot}.log 2> /dev/null; fi
}

case "${1:-}" in
  up) up "${2:-}" ;;
  down) down ;;
  status) status ;;
  logs) logs "${2:-}" ;;
  *) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 1 ;;
esac
