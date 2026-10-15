#!/usr/bin/env bash
# Adversarial referee pass on the report. Read-only agent; the report is written to results/review.md.
set -euo pipefail
cd "$(dirname "$0")/.."
claude -p "$(cat autoresearch/review.md)" \
  --tools "Read,Grep,Glob,WebSearch,WebFetch" \
  --allowedTools "Read" "Grep" "Glob" "WebSearch" "WebFetch" \
  --permission-mode dontAsk \
  --safe-mode \
  --strict-mcp-config \
  --max-budget-usd "${REVIEW_BUDGET_USD:-5}" \
  --output-format text > results/review.md
echo "wrote results/review.md"
