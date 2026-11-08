#!/usr/bin/env bash
# Pull, build, migrate, collect static and restart the production stack (Docker Compose + Caddy).
# Usage: scripts/deploy.sh            (add --tunnel to also start the Cloudflare Tunnel profile)
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || { echo "Missing .env - copy .env.example and fill it in (see deployment.md)"; exit 1; }
PROFILES=(--profile deploy); [ "${1:-}" = "--tunnel" ] && PROFILES+=(--profile tunnel)
DC=(docker compose -f docker-compose.yml "${PROFILES[@]}")   # -f alone: ignore the dev override file

git pull --ff-only
echo "==> building the frontend"
docker run --rm -v "$PWD/frontend:/app" -w /app -e HOME=/tmp -u "$(id -u):$(id -g)" node:22-alpine sh -c "npm ci && npm run build"
echo "==> building images and (re)starting"
"${DC[@]}" up -d --build        # web runs migrate + collectstatic on start
echo "==> waiting for web to be healthy"
for _ in $(seq 1 40); do
  state=$("${DC[@]}" ps --format '{{.Service}} {{.Health}}' | awk '$1=="web"{print $2}')
  if [ "$state" = "healthy" ]; then break; fi
  sleep 3
done
[ "$state" = "healthy" ] || { echo "web did not become healthy: run  docker compose logs web"; exit 1; }
sleep 8   # let restart loops show up before judging the other services
"${DC[@]}" ps
bad=$("${DC[@]}" ps --format '{{.Service}} {{.State}} {{.Health}}' | awk '$2!="running" || $3=="unhealthy"')
[ -z "$bad" ] || { echo "NOT OK:"; echo "$bad"; exit 1; }
echo "All services are up."; exit 0
