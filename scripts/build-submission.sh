#!/usr/bin/env bash
# Builds the submission: submission/FairRank-TDD.pdf (from docs/TDD.md) and FairRank-submission.zip with exactly two files:
# the TDD (PDF) and deployment.md. Usage: scripts/build-submission.sh
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p submission
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD":/work -w /work mcr.microsoft.com/playwright/python:v1.52.0-noble \
  sh -c 'pip install -q --target /tmp/pw playwright==1.52.0 markdown 2>&1 | grep -v -i "warning\|notice"; PYTHONPATH=/tmp/pw python3 scripts/build_tdd.py submission/FairRank-TDD.pdf'
rm -f FairRank-submission.zip
cp deployment.md submission/deployment.md
(cd submission && zip -q -j ../FairRank-submission.zip FairRank-TDD.pdf deployment.md)
unzip -l FairRank-submission.zip
ls -l FairRank-submission.zip
