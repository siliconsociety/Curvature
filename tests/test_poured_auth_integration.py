"""Release proof: pour Auth into a stranger app and execute its owned suite."""

from __future__ import annotations

import os
import subprocess
import sys

from curvature.gate.scaffold import new_app, pour_satellite


def test_poured_auth_suite_is_green_and_warning_free(tmp_path):
    root = new_app(tmp_path, "auth_stranger")
    pour_satellite(root, "auth")
    main = root / "app/main.py"
    source = main.read_text()
    source = source.replace(
        "from curvature import respond\n",
        "from curvature import respond\n"
        "from curvature.satellites import capture\n"
        "from satellites.auth.satellite import auth\n"
        "from satellites.auth.sessions import AuthConfig\n"
        "from satellites.auth.store import choose\n",
    )
    source = source.replace(
        'app = FastAPI(title="Auth Stranger")\n',
        'app = FastAPI(title="Auth Stranger")\n'
        'app.state.auth_store = choose(Path("data"))\n'
        "app.state.auth_config = AuthConfig.testing()\n"
        'capture(app, auth, orbit="/auth")\n',
    )
    main.write_text(source)
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(root), environment.get("PYTHONPATH", "")]
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-W",
            "error",
            "tests/test_auth_store.py",
            "tests/test_auth_satellite.py",
            "tests/test_auth_factors.py",
        ],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
