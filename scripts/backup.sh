#!/usr/bin/env bash
# Dump the database of the production stack to a compressed file; keep the last KEEP dumps.
#   scripts/backup.sh [directory]      run it from cron, e.g. every night: 0 3 * * * /srv/catix/scripts/backup.sh /srv/backups
set -euo pipefail
cd "$(dirname "$0")/.."
DIR=${1:-backups}
KEEP=${KEEP:-14}
mkdir -p "$DIR"
FILE="$DIR/catix-$(date +%Y%m%d-%H%M%S).sql.gz"
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U ctx -d ctx | gzip > "$FILE"
echo "wrote $FILE ($(du -h "$FILE" | cut -f1))"
ls -1t "$DIR"/catix-*.sql.gz | tail -n +$((KEEP + 1)) | xargs -r rm --
