import ast
import subprocess
import sys

import pytest

from camber.gate.cli import main, run_checks
from camber.gate.scaffold import APP_FILES, new_app


@pytest.fixture(scope="module")
def poured(tmp_path_factory):
    return new_app(tmp_path_factory.mktemp("apps"), "pit_stop")


def test_pours_every_file(poured):
    for relpath in APP_FILES.values():
        assert (poured / relpath).exists(), relpath
    assert (poured / "ratchet.toml").exists()
    assert (poured / ".python-version").read_text().strip() == "3.14"


def test_no_placeholder_residue(poured):
    for relpath in APP_FILES.values():
        assert "__CAMBER_" not in (poured / relpath).read_text(), relpath


def test_title_derived_from_name(poured):
    assert "Pit Stop" in (poured / "README.md").read_text()
    assert 'title="Pit Stop"' in (poured / "app/main.py").read_text()


def test_scripts_are_executable(poured):
    for script in ("gate.sh", "run.sh"):
        assert (poured / script).stat().st_mode & 0o111


def test_poured_python_parses(poured):
    for relpath in APP_FILES.values():
        if relpath.endswith(".py"):
            ast.parse((poured / relpath).read_text(), filename=relpath)


def test_poured_app_is_on_camber_from_birth(poured):
    findings, _info = run_checks(poured)
    assert findings == []


def test_poured_app_is_a_git_repo_with_one_commit(poured):
    done = subprocess.run(
        ["git", "-C", str(poured), "log", "--oneline"], capture_output=True, text=True
    )
    assert done.returncode == 0
    assert "Poured by camber new app" in done.stdout


def test_refuses_to_overwrite(poured):
    with pytest.raises(FileExistsError, match="never overwrite"):
        new_app(poured.parent, "pit_stop")


def test_rejects_invalid_names(tmp_path):
    for bad in ("pit-stop", "PitStop", "1stop"):
        with pytest.raises(ValueError, match="snake_case"):
            new_app(tmp_path, bad)


def test_cli_pours_an_app(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["new", "app", "night_race"]) == 0
    out = capsys.readouterr().out
    assert "poured" in out and "AGENTS.md" in out
    assert (tmp_path / "night_race/app/main.py").exists()


def test_python_dash_m_camber_works(tmp_path):
    done = subprocess.run(
        [sys.executable, "-m", "camber", "check", str(tmp_path)],
        capture_output=True, text=True, timeout=60,
    )
    assert done.returncode == 0
    assert "the road holds" in done.stdout
