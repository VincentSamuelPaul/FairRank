#!/usr/bin/env bash
# Postgres dump (+ uploaded CVs) into ./backups. Old backups are NOT pruned automatically: keep what you need.
# Cron example:  0 2 * * * /path/to/FairRank/scripts/backup.sh
set -euo pipefail
cd "$(dirname "$0")/.."
DC=(docker compose -f docker-compose.yml)
STAMP=$(date +%Y%m%d-%H%M%S)
mkdir -p backups
"${DC[@]}" exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > "backups/db-$STAMP.sql.gz"
"${DC[@]}" exec -T web tar -C /app -czf - media > "backups/media-$STAMP.tar.gz"
echo "backup written: backups/db-$STAMP.sql.gz and backups/media-$STAMP.tar.gz"
# Restore: gunzip -c backups/db-<stamp>.sql.gz | docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"'
