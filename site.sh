#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
uv run uvicorn website.app:app --reload --port 8095
