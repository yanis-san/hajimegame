#!/usr/bin/env bash
# Runs on the server, normally started by the pipeline over SSH:  ./deploy.sh <image-tag>
#
# 1. pulls the images of that tag (an immutable tag: the commit hash),
# 2. waits a little for games in progress to finish (rooms live in memory: a restart ends them),
# 3. makes sure the database is up and applies its migrations (before the new version starts),
#    then starts the new containers and waits for their health checks,
# 4. on any failure, puts the previous version back and exits with an error.
#
# Needs docker compose, a .env next to this script (see production.env.example) and, to pull private images,
# a prior `docker login ghcr.io` (the pipeline does it).
set -euo pipefail
cd "$(dirname "$0")"

TAG="${1:?usage: deploy.sh <image-tag>}"
[[ "$TAG" =~ ^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$ ]] || { echo "invalid image tag: $TAG" >&2; exit 2; }
[[ -f .env ]] || { echo ".env is missing: copy production.env.example and fill it in" >&2; exit 2; }

# shellcheck disable=SC1091
set -a && source .env && set +a
DRAIN_SECONDS="${DRAIN_SECONDS:-180}"

compose() { docker compose --env-file .env -f compose.prod.yml "$@"; }

previous=""
[[ -f .deployed-tag ]] && previous="$(<.deployed-tag)"

# Number of rooms alive on the running server, or "" when it cannot be asked (first deployment, no token).
active_rooms() {
  compose exec -T server python -c "
import os, re, urllib.request as u
request = u.Request('http://127.0.0.1:8000/metrics')
token = os.environ.get('HAJIME_METRICS_TOKEN')
if token:
    request.add_header('Authorization', 'Bearer ' + token)
body = u.urlopen(request, timeout=3).read().decode()
match = re.search(r'^hajime_rooms_active ([0-9.]+)', body, re.M)
print(int(float(match.group(1))) if match else '')
" 2>/dev/null || true
}

export TAG
echo "==> pulling $TAG"
compose pull

if [[ -n "$previous" ]]; then
  echo "==> waiting up to ${DRAIN_SECONDS}s for games in progress to end"
  deadline=$((SECONDS + DRAIN_SECONDS))
  while :; do
    rooms="$(active_rooms)"
    if [[ -z "$rooms" ]]; then echo "    (cannot count rooms: set HAJIME_METRICS_TOKEN to enable this)"; break; fi
    if [[ "$rooms" == "0" ]]; then echo "    no room alive"; break; fi
    if ((SECONDS >= deadline)); then echo "    $rooms room(s) still alive: deploying anyway"; break; fi
    echo "    $rooms room(s) alive"
    sleep 10
  done
fi

echo "==> database: up, then migrations"
compose up -d --wait --wait-timeout 120 postgres
# Migrations only add (see docs/DEPLOY.md), so the version that is still running keeps working while they
# apply, and so does a rollback to it. If one fails nothing else has been touched: stop here.
if ! compose run --rm --no-deps server alembic upgrade head; then
  echo "!! the database migration failed: nothing was changed, $previous is still running" >&2
  exit 1
fi

echo "==> starting $TAG"
if compose up -d --remove-orphans --wait --wait-timeout 180; then
  echo "$TAG" >.deployed-tag
  # keep a week of older images (a fast rollback needs them), drop the rest
  docker image prune -f --filter "until=168h" >/dev/null || true
  echo "==> deployed $TAG (previous: ${previous:-none})"
  # A backup that silently stopped working is worse than none: say how fresh the last one is.
  newest="$(compose exec -T backup sh -c 'find /backups -name "hajime-*.sql.gz" -mmin -1560 | sort | tail -n 1' 2>/dev/null || true)"
  if [[ -n "$newest" ]]; then echo "==> last backup: $newest"; else echo "!! no database backup in the last 26 hours: see docs/DEPLOY.md" >&2; fi
  exit 0
fi

echo "!! $TAG did not become healthy" >&2
compose ps >&2 || true
compose logs --tail 60 server web caddy >&2 || true
if [[ -n "$previous" && "$previous" != "$TAG" ]]; then
  echo "==> rolling back to $previous" >&2
  TAG="$previous" compose up -d --remove-orphans --wait --wait-timeout 180 >&2 \
    && echo "==> rolled back to $previous" >&2 \
    || echo "!! rollback failed too: look at the server by hand" >&2
fi
exit 1
