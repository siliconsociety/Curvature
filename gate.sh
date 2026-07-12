#!/usr/bin/env bash
# The gate. One command, one definition of green.
set -euo pipefail
cd "$(dirname "$0")"
uv run ruff check src tests demo
uv run pytest -q --cov --cov-report=json
uv run curvature check
