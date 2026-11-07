#!/usr/bin/env bash
# Usage: scripts/screenshots.sh [login|components|ranked|candidate|portal|portal-candidate|all ...]
# Runs in the official Playwright image (browsers included); the Python package is installed into /tmp at run time.
cd "$(dirname "$0")/.." || exit 1
exec docker run --rm --network host --user "$(id -u):$(id -g)" -e HOME=/tmp -e OUT -e CLIP -e FAIRRANK_DEMO_PASSWORD -v "$PWD":/work -w /work \
  mcr.microsoft.com/playwright/python:v1.52.0-noble \
  sh -c 'pip install -q --target /tmp/pw playwright==1.52.0 2>&1 | grep -v WARNING; PYTHONPATH=/tmp/pw python3 scripts/screenshots.py "$@"' sh "$@"
