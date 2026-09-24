#!/usr/bin/env bash
set -euo pipefail
cd /opt/trakora
mkdir -p backups
ts=$(date -u +%Y%m%dT%H%M%SZ)
docker compose exec -T db pg_dump -U trakora -d trakora | gzip > "backups/trakora-${ts}.sql.gz"
find backups -type f -name 'trakora-*.sql.gz' -mtime +7 -delete
