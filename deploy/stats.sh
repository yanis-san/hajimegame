#!/usr/bin/env bash
# Prints the game statistics (deploy/stats.sql) from the production database. Run it on the server:
#   cd /opt/hajime && ./stats.sh [--days N]
# It only reads. Nothing leaves the server.
set -euo pipefail
cd "$(dirname "$0")"
days=14
if [[ "${1:-}" == "--days" ]]; then days="${2:?usage: stats.sh [--days N]}"; fi
[[ "$days" =~ ^[0-9]{1,3}$ ]] || { echo "--days must be a number" >&2; exit 2; }
docker compose --env-file .env -f compose.prod.yml exec -T postgres \
  psql -U hajime -d hajime -v "days=$days" -v ON_ERROR_STOP=1 -f - <stats.sql
