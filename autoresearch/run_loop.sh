#!/usr/bin/env bash
# Run the autoresearch loop. Usage: autoresearch/run_loop.sh [--iterations N] [--model opus] [--budget-per-call 2.0]
# Requires: autoresearch/setup_heldout.py run once beforehand, a clean working tree, and the `claude` CLI.
set -euo pipefail
cd "$(dirname "$0")/.."
exec uv run python autoresearch/loop.py "$@"
