#!/usr/bin/env bash
# Freeze the candidate after the loop: record its hash, then score it once on the held-out benchmark.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p results/tables
{
  echo "method.py sha256: $(shasum -a 256 src/wapusk_greenup/method.py | cut -d' ' -f1)"
  echo "frozen utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "git commit: $(git rev-parse HEAD)"
  echo "iterations in ledger: $(wc -l < autoresearch/ledger.jsonl | tr -d ' ')"
} > results/method_lock.txt
uv run python autoresearch/evaluate.py --mode final > results/tables/autoresearch_final.json
cat results/method_lock.txt
