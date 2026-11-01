#!/usr/bin/env bash
# The server side of the self-maintaining wiki: brings the latest commit of the `wiki` branch (only commits that passed the
# checks reach it) into the search index. Run it from cron, e.g. every 15 minutes:
#   */15 * * * * /srv/cAtIx/scripts/wiki-pull.sh >> /var/log/catix-wiki-pull.log 2>&1
set -euo pipefail
cd "$(dirname "$0")/.."
WIKI_DIR=${WIKI_DIR:-../catix-wiki}
before=$(git -C "$WIKI_DIR" rev-parse HEAD)
git -C "$WIKI_DIR" pull -q --ff-only
after=$(git -C "$WIKI_DIR" rev-parse HEAD)
if [ "$before" = "$after" ]; then
  exit 0
fi
echo "$(date -Is) wiki $before -> $after"
docker compose -f docker-compose.prod.yml run --rm wiki
