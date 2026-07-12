"""The bounds family: numbers with one legal direction."""

import json
from pathlib import Path

from curvature.gate import bounds as checks
from curvature.gate.ratchet import Ratchet, load, loosened, save


def write(root: Path, relpath: str, text: str) -> Path:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_file_over_ceiling_is_off_curvature(tmp_path):
    write(tmp_path, "app.py", "\n".join(["x = 1"] * 10))
    findings = checks.check_ceilings(tmp_path, Ratchet(ceilings={"py": 5}))
    assert [f.rule for f in findings] == ["ANOM-140"]
    assert "10 lines against a ceiling of 5" in findings[0].message


def test_grandfathered_file_is_honored_at_its_pin(tmp_path):
    write(tmp_path, "legacy.py", "\n".join(["x = 1"] * 10))
    ratchet = Ratchet(ceilings={"py": 5}, exceptions={"legacy.py": 10})
    assert checks.check_ceilings(tmp_path, ratchet) == []


def test_vendored_files_have_no_ceiling(tmp_path):
    write(tmp_path, "static/vendor/big.js", "\n".join(["//"] * 500))
    assert checks.check_ceilings(tmp_path, Ratchet()) == []


def test_coverage_under_floor_is_off_curvature(tmp_path):
    write(tmp_path, "coverage.json", json.dumps({"totals": {"percent_covered": 71.0}}))
    findings = checks.check_coverage(tmp_path, Ratchet(coverage_floor=80.0))
    assert [f.rule for f in findings] == ["ANOM-141"]


def test_missing_report_with_a_floor_is_off_curvature(tmp_path):
    findings = checks.check_coverage(tmp_path, Ratchet(coverage_floor=80.0))
    assert [f.rule for f in findings] == ["ANOM-141"]


def test_no_floor_means_no_coverage_check(tmp_path):
    assert checks.check_coverage(tmp_path, Ratchet()) == []


def test_every_loosening_is_named():
    committed = Ratchet(
        ceilings={"py": 300}, exceptions={"big.py": 500}, coverage_floor=80.0
    )
    current = Ratchet(
        ceilings={"py": 400},
        exceptions={"big.py": 600, "new.py": 999},
        coverage_floor=70.0,
    )
    complaints = loosened(current, committed)
    assert len(complaints) == 4


def test_tightening_is_not_loosening():
    committed = Ratchet(ceilings={"py": 300}, exceptions={"big.py": 500}, coverage_floor=80.0)
    current = Ratchet(ceilings={"py": 250}, exceptions={"big.py": 400}, coverage_floor=90.0)
    assert loosened(current, committed) == []


def test_ratchet_round_trip(tmp_path):
    original = Ratchet(
        ceilings={"py": 300, "css": 250, "js": 150},
        exceptions={"src/big.py": 512},
        coverage_floor=83.4,
    )
    save(tmp_path, original)
    assert load(tmp_path) == original


def test_the_ratchet_wears_its_floor(tmp_path):
    import json

    save(tmp_path, Ratchet(coverage_floor=97.4))
    badge = json.loads((tmp_path / "floor-badge.json").read_text())
    assert badge["schemaVersion"] == 1
    assert badge["message"] == "97.4 · ratcheted"


def test_missing_ratchet_file_yields_defaults(tmp_path):
    ratchet = load(tmp_path)
    assert ratchet.ceilings["py"] == 300
    assert ratchet.coverage_floor == 0.0


def test_a_tagged_version_with_new_commits_is_stale(tmp_path):
    write(tmp_path, "pyproject.toml", '[project]\nname = "x"\nversion = "1.0.0"\n')
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "release")
    _git(tmp_path, "tag", "v1.0.0")
    write(tmp_path, "new_work.py", "x = 1\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "forgot the bump")
    findings = checks.check_version_currency(tmp_path)
    assert [f.rule for f in findings] == ["ANOM-143"]
    assert "bump the version" in findings[0].message


def test_head_at_the_tag_is_current(tmp_path):
    write(tmp_path, "pyproject.toml", '[project]\nname = "x"\nversion = "1.0.0"\n')
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "release")
    _git(tmp_path, "tag", "v1.0.0")
    assert checks.check_version_currency(tmp_path) == []


def test_unpublished_versions_are_unjudged(tmp_path):
    write(tmp_path, "pyproject.toml", '[project]\nname = "x"\nversion = "9.9.9"\n')
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "wip")
    assert checks.check_version_currency(tmp_path) == []


def test_gitless_trees_are_unjudged(tmp_path):
    write(tmp_path, "pyproject.toml", '[project]\nname = "x"\nversion = "1.0.0"\n')
    assert checks.check_version_currency(tmp_path) == []


def _git(tmp_path, *args):
    import subprocess

    return subprocess.run(
        ["git", "-C", str(tmp_path), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        capture_output=True, text=True, check=True,
    )


def test_suffixes_without_ceilings_are_unbounded(tmp_path):
    write(tmp_path, "free.py", "x = 1\n" * 100)
    ratchet = Ratchet(ceilings={"css": 250})  # no py ceiling declared
    assert checks.check_ceilings(tmp_path, ratchet) == []


def test_versionless_pyprojects_are_unjudged(tmp_path):
    write(tmp_path, "pyproject.toml", '[project]\nname = "x"\n')
    assert checks.check_version_currency(tmp_path) == []


def test_git_failures_stay_silent(tmp_path, monkeypatch):
    import subprocess

    write(tmp_path, "pyproject.toml", '[project]\nname = "x"\nversion = "1.0.0"\n')

    def explode(*args, **kwargs):
        raise OSError("no git in this universe")

    monkeypatch.setattr(subprocess, "run", explode)
    assert checks.check_version_currency(tmp_path) == []
