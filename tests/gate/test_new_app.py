import ast
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from curvature.gate.cli import main, run_checks
from curvature.gate.scaffold import APP_FILES, _scaffold_git_env, new_app

ATTRIBUTION_START = "Only upstream Curvature field reports"
ATTRIBUTION_END = "verification remain the causal record."


def attribution_doctrine(source: str) -> str:
    start = source.index(ATTRIBUTION_START)
    end = source.index(ATTRIBUTION_END, start) + len(ATTRIBUTION_END)
    return " ".join(source[start:end].split())


@pytest.fixture(scope="module")
def poured(tmp_path_factory):
    return new_app(tmp_path_factory.mktemp("apps"), "pit_stop")


def test_pours_every_file(poured):
    for relpath in APP_FILES.values():
        assert (poured / relpath).exists(), relpath
    assert (poured / "ratchet.toml").exists()
    assert (poured / ".python-version").read_text().strip() == "3.14"
    assert (poured / "satellites/__init__.py").exists()


def test_no_placeholder_residue(poured):
    for relpath in APP_FILES.values():
        assert "__CURVATURE_" not in (poured / relpath).read_text(), relpath


def test_title_derived_from_name(poured):
    assert "Pit Stop" in (poured / "README.md").read_text()
    assert 'title="Pit Stop"' in (poured / "app/main.py").read_text()


def test_poured_readme_explains_the_update_boundary(poured):
    readme = (poured / "README.md").read_text()
    assert "uv lock --upgrade-package curvature" in readme
    assert "upgrades never overwrite" in readme


def test_poured_shell_keeps_the_stable_consumer_entrypoint(poured):
    shell = (poured / "app/components/shell.py").read_text()
    assert 'h.script(src=f"/static/lib/curvature.js?v={ASSETS}")' in shell
    assert "live.js" not in shell


def test_poured_agents_carries_upstream_field_report_doctrine(poured):
    contract = " ".join((poured / "AGENTS.md").read_text().split())
    assert "offer to file an upstream Curvature issue" in contract
    assert "Filing requires the operator's nod" in contract
    assert "creates no issue, attribution policy, or process artifact" in contract
    assert "minimal reproduction" in contract
    assert "desired behavior as checkable invariants" in contract
    assert "Only upstream Curvature field reports" in contract
    assert "Consumer-repository artifacts are excluded" in contract
    assert "ordinary pull requests, commits, and other artifacts" in contract
    assert "active task or harness" in contract
    assert "explicit Factory launch packet" in contract
    assert "~/.codex/config.toml" in contract
    assert "does not prove the active model" in contract
    assert "— GPT-5.6 Luna (<role>)" in contract
    assert "— GPT-5.6 Sol (<role>)" in contract
    assert "exact assigned role" in contract
    assert "Reasoning effort and speed or service tier stay out" in contract
    assert "stop before the upstream GitHub write and ask the operator" in contract
    assert "Never publish an unidentified-model fallback" in contract
    assert "Unidentified model (role) — operator, please amend" not in contract
    assert "qualification-ledger key, not complete provenance" in contract


def test_attribution_doctrine_stays_canonical_across_guidance(poured):
    root = Path(__file__).parents[2]
    sources = (
        (poured / "AGENTS.md").read_text(),
        (root / "AGENTS.md").read_text(),
        (root / "docs/UPGRADING.md").read_text(),
    )
    assert len({attribution_doctrine(source) for source in sources}) == 1


def test_poured_config_knows_its_first_party_import_roots(poured):
    config = (poured / "pyproject.toml").read_text()
    assert 'known-first-party = ["app", "satellites"]' in config


def test_poured_config_uses_starlettes_current_test_client(poured):
    config = tomllib.loads((poured / "pyproject.toml").read_text())
    dependencies = config["dependency-groups"]["dev"]
    assert "httpx2" in dependencies
    assert "httpx" not in dependencies


def test_scripts_are_executable(poured):
    for script in ("gate.sh", "run.sh"):
        assert (poured / script).stat().st_mode & 0o111


def test_poured_python_parses(poured):
    for relpath in APP_FILES.values():
        if relpath.endswith(".py"):
            ast.parse((poured / relpath).read_text(), filename=relpath)


def test_poured_app_is_on_curvature_from_birth(poured):
    findings, _info = run_checks(poured)
    assert findings == []


def test_poured_app_is_a_git_repo_with_one_commit(poured):
    done = subprocess.run(
        ["git", "-C", str(poured), "log", "--oneline"], capture_output=True, text=True
    )
    assert done.returncode == 0
    assert "Poured by curvature new app" in done.stdout


def test_pour_isolates_every_parent_git_variable(tmp_path, monkeypatch):
    parent = tmp_path / "parent"
    parent.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=parent, check=True)
    tracked = parent / "tracked.txt"
    tracked.write_text("committed parent content\n")
    subprocess.run(["git", "add", "-A"], cwd=parent, check=True)
    subprocess.run(
        [
            "git", "-c", "user.name=parent", "-c", "user.email=parent@example.test",
            "commit", "--quiet", "-m", "Parent commit",
        ],
        cwd=parent,
        check=True,
    )
    tracked.write_text("uncommitted parent content\n")
    untracked = parent / "untracked.txt"
    untracked.write_text("parent-only file\n")

    def git(*args):
        done = subprocess.run(
            ["git", "-C", str(parent), *args],
            capture_output=True,
            check=True,
            text=True,
        )
        return done.stdout.strip()

    local_vars = set(git("rev-parse", "--local-env-vars").splitlines())
    before = {
        "head": git("rev-parse", "HEAD"),
        "status": git("status", "--porcelain"),
        "index": (parent / ".git/index").read_bytes(),
        "config": (parent / ".git/config").read_bytes(),
        "tracked": tracked.read_bytes(),
        "untracked": untracked.read_bytes(),
    }
    inherited = {name: "inherited-parent-context" for name in local_vars}
    inherited.update(
        {
            "GIT_DIR": str(parent / ".git"),
            "GIT_WORK_TREE": str(parent),
            "GIT_INDEX_FILE": str(parent / ".git/index"),
            "GIT_COMMON_DIR": str(parent / ".git"),
            "GIT_OBJECT_DIRECTORY": str(parent / ".git/objects"),
            "GIT_CONFIG": str(parent / ".git/config"),
        }
    )
    real_run = subprocess.run
    git_calls = []

    def isolated_run(command, **kwargs):
        if command[0] == "git":
            git_calls.append(command)
            assert local_vars.isdisjoint(kwargs["env"])
        return real_run(command, **kwargs)

    with monkeypatch.context() as context:
        for name, value in inherited.items():
            context.setenv(name, value)
        context.setattr(subprocess, "run", isolated_run)
        poured = new_app(tmp_path / "apps", "isolated_app")

    assert len(git_calls) == 4
    assert git("log", "-1", "--format=%s") == "Parent commit"
    assert git("rev-parse", "--is-bare-repository") == "false"
    assert {
        "head": git("rev-parse", "HEAD"),
        "status": git("status", "--porcelain"),
        "index": (parent / ".git/index").read_bytes(),
        "config": (parent / ".git/config").read_bytes(),
        "tracked": tracked.read_bytes(),
        "untracked": untracked.read_bytes(),
    } == before
    poured_log = subprocess.run(
        ["git", "-C", str(poured), "log", "-1", "--format=%s"],
        capture_output=True,
        check=True,
        text=True,
    )
    assert poured_log.stdout.strip() == "Poured by curvature new app"


def test_git_env_discovery_failure_falls_back_to_no_git_variables(monkeypatch):
    def failed_discovery(command, **kwargs):
        assert not any(name.startswith("GIT_") for name in kwargs["env"])
        return subprocess.CompletedProcess(command, 1, "", "git unavailable")

    monkeypatch.setenv("GIT_DIR", "/inherited/parent.git")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "inherited author")
    monkeypatch.setattr(subprocess, "run", failed_discovery)
    assert not any(name.startswith("GIT_") for name in _scaffold_git_env())


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


def test_python_dash_m_curvature_works(tmp_path):
    done = subprocess.run(
        [sys.executable, "-m", "curvature", "check", str(tmp_path)],
        capture_output=True, text=True, timeout=60,
    )
    assert done.returncode == 0
    assert "the geometry holds" in done.stdout
