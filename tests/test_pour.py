import ast

import pytest

from curvature.gate.cli import main, run_checks
from curvature.gate.scaffold import available_pours, new_app, pour_satellite


@pytest.fixture(scope="module")
def manifold(tmp_path_factory):
    """A poured app with the auth satellite poured into it."""
    root = new_app(tmp_path_factory.mktemp("apps"), "paddock")
    pour_satellite(root, "auth")
    return root


def test_the_constellation_is_available():
    assert {"auth", "concierge"} <= set(available_pours())


def test_pour_lands_in_satellites_and_tests(manifold):
    assert (manifold / "satellites/auth/satellite.py").exists()
    assert (manifold / "satellites/auth/store_sqlite.py").exists()
    assert (manifold / "satellites/auth/components/auth_forms.py").exists()
    assert (manifold / "tests/test_auth_satellite.py").exists()
    assert not (manifold / "satellites/auth/_tests").exists()


def test_poured_packages_are_importable_shapes(manifold):
    assert (manifold / "satellites/__init__.py").exists()
    assert (manifold / "satellites/auth/__init__.py").exists()
    assert (manifold / "satellites/auth/components/__init__.py").exists()


def test_poured_source_parses(manifold):
    for path in (manifold / "satellites").rglob("*.py"):
        ast.parse(path.read_text(), filename=str(path))


def test_poured_satellite_passes_the_gate_natively(manifold):
    """The whole point: poured code answers to the app's own gate —
    Props-first components, redirecting writes, no JS, all of it."""
    findings, _info = run_checks(manifold)
    assert findings == []


def test_pours_never_overwrite(manifold):
    with pytest.raises(FileExistsError, match="never overwrite"):
        pour_satellite(manifold, "auth")


def test_unknown_satellite_names_the_available(tmp_path):
    with pytest.raises(ValueError, match="available"):
        pour_satellite(tmp_path, "warp_drive")


def test_cli_pour(tmp_path, capsys):
    new_app(tmp_path, "night_shift")
    assert main(["pour", "auth", str(tmp_path / "night_shift")]) == 0
    out = capsys.readouterr().out
    assert "poured satellites/auth/satellite.py" in out
    assert "your gate" in out


def test_cli_pour_unknown_is_polite(tmp_path, capsys):
    assert main(["pour", "warp_drive", str(tmp_path)]) == 1
    assert "available" in capsys.readouterr().out
