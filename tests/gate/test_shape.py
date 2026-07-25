import subprocess
from pathlib import Path

from curvature.gate.cli import run_checks
from curvature.gate.shape import check_hollow_branches


def write(root: Path, relpath: str, text: str = "") -> Path:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_orphaned_python_cache_marks_a_hollow_branch(tmp_path):
    write(tmp_path, "app/main.py", "app = object()\n")
    write(tmp_path, "app/blog/__pycache__/routes.cpython-314.pyc", "bytecode")
    findings = check_hollow_branches(tmp_path)
    assert [(finding.rule, finding.path) for finding in findings] == [
        ("ANOM-153", "app/blog")
    ]
    assert findings[0].message == (
        "hollow branch: no meaningful files remain; prune the directory (C-603)"
    )


def test_complete_gate_includes_the_hollow_branch_check(tmp_path):
    write(tmp_path, "app/main.py", "app = object()\n")
    write(tmp_path, "app/blog/__pycache__/routes.cpython-314.pyc", "bytecode")
    findings, _info = run_checks(tmp_path)
    assert [finding.rule for finding in findings] == ["ANOM-153"]


def test_cache_beside_live_source_does_not_make_the_branch_hollow(tmp_path):
    write(tmp_path, "app/blog/routes.py", "routes = []\n")
    write(tmp_path, "app/blog/__pycache__/routes.cpython-314.pyc", "bytecode")
    assert check_hollow_branches(tmp_path) == []


def test_empty_cache_directory_is_not_evidence_of_removed_source(tmp_path):
    (tmp_path / "app/blog/__pycache__").mkdir(parents=True)
    assert check_hollow_branches(tmp_path) == []


def test_empty_directory_without_removed_source_evidence_is_allowed(tmp_path):
    (tmp_path / "data/uploads").mkdir(parents=True)
    assert check_hollow_branches(tmp_path) == []


def test_empty_package_marker_is_a_meaningful_leaf(tmp_path):
    write(tmp_path, "app/future/__init__.py")
    write(tmp_path, "app/future/__pycache__/old.cpython-314.pyc", "bytecode")
    assert check_hollow_branches(tmp_path) == []


def test_directory_left_after_tracked_file_deletion_is_hollow(tmp_path):
    write(tmp_path, "app/main.py", "app = object()\n")
    write(tmp_path, "app/static/site.css", "body {}\n")
    write(tmp_path, "app/static/lib/http.js", "export const get = 1;\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Curvature",
            "-c",
            "user.email=curvature@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        cwd=tmp_path,
        check=True,
    )
    (tmp_path / "app/static/lib/http.js").unlink()
    findings = check_hollow_branches(tmp_path)
    assert [(finding.rule, finding.path) for finding in findings] == [
        ("ANOM-153", "app/static/lib")
    ]


def test_hollow_nested_branches_report_the_highest_prunable_directory(tmp_path):
    write(tmp_path, "app/main.py", "app = object()\n")
    write(tmp_path, "app/retired/deep/__pycache__/old.cpython-314.pyc", "bytecode")
    findings = check_hollow_branches(tmp_path)
    assert [finding.path for finding in findings] == ["app/retired"]


def test_deleted_file_beside_a_live_leaf_does_not_hollow_the_directory(tmp_path):
    write(tmp_path, "app/feature/old.py", "old = True\n")
    write(tmp_path, "app/feature/live.py", "live = True\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Curvature",
            "-c",
            "user.email=curvature@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        cwd=tmp_path,
        check=True,
    )
    (tmp_path / "app/feature/old.py").unlink()
    assert check_hollow_branches(tmp_path) == []


def test_missing_tracked_file_inside_excluded_directory_is_ignored(tmp_path):
    write(tmp_path, ".cache/generated.py", "generated = True\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Curvature",
            "-c",
            "user.email=curvature@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        cwd=tmp_path,
        check=True,
    )
    (tmp_path / ".cache/generated.py").unlink()
    assert check_hollow_branches(tmp_path) == []


def test_git_inspection_failure_leaves_cache_detection_available(tmp_path, monkeypatch):
    write(tmp_path, "app/main.py", "app = object()\n")
    write(tmp_path, "app/blog/__pycache__/old.cpython-314.pyc", "bytecode")

    def unavailable(*_args, **_kwargs):
        raise OSError("git unavailable")

    monkeypatch.setattr(subprocess, "run", unavailable)
    assert [finding.path for finding in check_hollow_branches(tmp_path)] == ["app/blog"]
