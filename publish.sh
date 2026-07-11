#!/usr/bin/env bash
# Publish to PyPI. The button never skips the gate.
set -euo pipefail
cd "$(dirname "$0")"

./gate.sh

if [[ ! -f .env ]]; then
  echo "no .env file; it must contain: UV_PUBLISH_TOKEN=pypi-..." >&2
  exit 1
fi
set -a; source .env; set +a
if [[ -z "${UV_PUBLISH_TOKEN:-}" ]]; then
  echo "UV_PUBLISH_TOKEN is not set; the .env line must read: UV_PUBLISH_TOKEN=pypi-..." >&2
  exit 1
fi

rm -rf dist
uv build
uv tool run twine check dist/*
uv publish

version=$(uv run python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
git tag -a "v${version}" -m "Published v${version} to PyPI"
echo "published ${version} and tagged v${version} — verify with: uvx camber new app anything"
