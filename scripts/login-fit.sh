#!/usr/bin/env bash
# Usage: scripts/login-fit.sh   (runs scripts/login_fit.py in the Playwright image)
cd "$(dirname "$0")/.." || exit 1
exec docker run --rm --network host --user "$(id -u):$(id -g)" -e HOME=/tmp -e OUT -v "$PWD":/work -w /work \
  mcr.microsoft.com/playwright/python:v1.52.0-noble \
  sh -c 'pip install -q --target /tmp/pw playwright==1.52.0 2>&1 | grep -v -i "warning\|notice"; PYTHONPATH=/tmp/pw python3 scripts/login_fit.py "$@"' sh "$@"
