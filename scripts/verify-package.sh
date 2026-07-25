#!/usr/bin/env bash
# Prove both source artifacts and a wheel without touching a working application.
set -euo pipefail
cd "$(dirname "$0")/.."

./gate.sh

work=$(mktemp -d "${TMPDIR:-/tmp}/curvature-package.XXXXXX")
trap 'rm -rf "$work"' EXIT
artifacts="$work/artifacts"
mkdir -p "$artifacts"

uv build --out-dir "$artifacts"
wheel=$(find "$artifacts" -maxdepth 1 -name '*.whl' -print -quit)
source_archive=$(find "$artifacts" -maxdepth 1 -name '*.tar.gz' -print -quit)
if [[ -z "$wheel" || -z "$source_archive" ]]; then
  echo "expected one wheel and one source archive" >&2
  exit 1
fi

uv venv "$work/source-env"
uv pip install --python "$work/source-env/bin/python" "$source_archive"
"$work/source-env/bin/python" -c \
  'import curvature; from importlib.metadata import version; print("source artifact", version("curvature"))'

uv venv "$work/wheel-env"
uv pip install --python "$work/wheel-env/bin/python" "${wheel}[fastapi,auth]"
(
  cd "$work"
  "$work/wheel-env/bin/python" -m curvature new app stranger
)

(
  cd "$work/stranger"
  uv add "${wheel}[fastapi,auth]"
  ./gate.sh
  uv run curvature pour auth
  uv run python - <<'PY'
from pathlib import Path

main = Path("app/main.py")
source = main.read_text()
source = source.replace(
    "from curvature import respond\n",
    "from curvature import respond\n"
    "from curvature.satellites import capture\n",
)
source = source.replace(
    "from app.components.welcome import WelcomeProps, welcome\n",
    "from app.components.welcome import WelcomeProps, welcome\n"
    "from satellites.auth.satellite import auth\n"
    "from satellites.auth.sessions import AuthConfig\n"
    "from satellites.auth.store import choose\n",
)
source = source.replace(
    'app = FastAPI(title="Stranger")\n',
    'app = FastAPI(title="Stranger")\n'
    'app.state.auth_store = choose(Path("data"))\n'
    "app.state.auth_config = AuthConfig.testing()\n"
    'capture(app, auth, orbit="/auth")\n',
)
if source == main.read_text():
    raise SystemExit("could not assemble the Auth proof")
main.write_text(source)
PY
  ./gate.sh
)

echo "package proof passed: source artifact, wheel, stranger app, and Auth pour"
