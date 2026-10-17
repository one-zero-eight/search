#!/usr/bin/env bash
# Starts, stops and checks everything cAtIx needs. Run from anywhere.
#   scripts/catix.sh up [--tunnel]   docker (db, redis) -> schema -> SSH tunnel to the GPU server -> model check -> apps
#   scripts/catix.sh down            stops the apps (docker and the SSH tunnel stay)
#   scripts/catix.sh status          what runs and what answers
#   scripts/catix.sh logs [app]      follows a log (tgbot, maxbot, worker, tguserbot; default: all)
# --tunnel also starts a `tuna` tunnel (tuna.am) for the calendar feed and prints the address to give to `catix-feed link`.
# TUNA_SUBDOMAIN (environment or .env) pins the address: your permanent free domain, shown by tuna on start, e.g. grand-tundra-5389.
# The Telegram userbot (reads chats under your own account) starts only after `uv run catix-tguserbot login` was done once.
set -euo pipefail

cd "$(dirname "$0")/.."
LOGS=data/logs
APPS=(catix-tgbot catix-maxbot catix-worker)
USERBOT=catix-tguserbot
USERBOT_SESSION=data/telegram.session
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
  echo "1/5 docker (postgres, redis)"
  docker compose up -d --wait db redis > /dev/null && ok "db, redis healthy"

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
  for app in "${APPS[@]}"; do start_app "$app"; done
  if [ -f "$USERBOT_SESSION" ]; then
    start_app "$USERBOT" listen
  else
    echo "  $USERBOT skipped: no Telegram session yet (uv run catix-tguserbot login)"
  fi

  if [ "${1:-}" = "--tunnel" ]; then
    if tunnel_running; then
      ok "tuna already running: $(tunnel_url)"
    else
      : > "$LOGS/tunnel.log"
      subdomain=$(tuna_subdomain)
      nohup tuna http 8090 --log "$LOGS/tunnel.log" --no-colors ${subdomain:+--subdomain="$subdomain"} > /dev/null 2>&1 &
      for _ in $(seq 20); do
        url=$(tunnel_url)
        [ -n "$url" ] && break
        sleep 1
      done
      ok "tunnel: ${url:-no address yet, see $LOGS/tunnel.log}"
      echo "  If the address changed, link it: uv run catix-feed link ${url:-<address>}"
      [ -n "$subdomain" ] || echo "  (random address: set TUNA_SUBDOMAIN to keep it between restarts)"
    fi
  fi
}

down() {
  for app in "${APPS[@]}" "$USERBOT"; do
    if running "$app"; then pkill -f "[b]in/$app( |\$)" && ok "$app stopped"; else echo "  $app not running"; fi
  done
}

status() {
  echo "docker:"; docker compose ps --format '  {{.Service}}: {{.Status}}' db redis
  echo "models:"; check_models || true
  echo "apps:"
  for app in "${APPS[@]}"; do if running "$app"; then ok "$app"; else bad "$app is not running"; fi; done
  if running "$USERBOT"; then ok "$USERBOT"; elif [ -f "$USERBOT_SESSION" ]; then bad "$USERBOT is not running"; else echo "  $USERBOT: no session yet (login first)"; fi
  if tunnel_running; then ok "tuna: $(tunnel_url)"; else echo "  tuna not running (only needed for the calendar feed: up --tunnel)"; fi
  echo "database:"; uv run --quiet catix-db status 2>&1 | grep -v WARNING | sed 's/^/  /' | head -8
}

logs() {
  if [ -n "${1:-}" ]; then tail -f "$LOGS/$1.log"; else tail -f "$LOGS"/{tgbot,maxbot,worker,tguserbot}.log 2> /dev/null; fi
}

case "${1:-}" in
  up) up "${2:-}" ;;
  down) down ;;
  status) status ;;
  logs) logs "${2:-}" ;;
  *) sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; exit 1 ;;
esac
