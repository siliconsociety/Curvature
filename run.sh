#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
uv run uvicorn demo.app:app --reload --timeout-graceful-shutdown 1
