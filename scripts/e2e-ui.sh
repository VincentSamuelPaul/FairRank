#!/usr/bin/env bash
# Usage: scripts/e2e-ui.sh
# Browser end-to-end for every role. Needs the dev stack up (ideally with docker-compose.e2e.yml so scoring is the offline provider)
# and the synthetic CVs: docker compose exec web python manage.py generate_cvs /tmp/cvs && docker compose cp web:/tmp/cvs/. .review/cvs/
cd "$(dirname "$0")/.." || exit 1
# remove the requisitions a previous run created (titles start with "E2E"); seed data is never touched
docker compose exec -T web python manage.py shell < scripts/e2e_cleanup.py 2>&1 | tail -1
exec docker run --rm --network host --user "$(id -u):$(id -g)" -e HOME=/tmp -e FAIRRANK_DEMO_PASSWORD -v "$PWD":/work -w /work \
  mcr.microsoft.com/playwright/python:v1.52.0-noble \
  sh -c 'pip install -q --target /tmp/pw playwright==1.52.0 2>&1 | grep -v -i "warning\|notice"; PYTHONPATH=/tmp/pw python3 scripts/e2e_ui.py "$@"' sh "$@"
