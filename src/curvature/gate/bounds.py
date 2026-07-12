"""The bounds family: every check about a NUMBER with one legal
direction. Ceilings fall, floors rise, versions climb, and the ratchet
file may never loosen. Split out of checks.py the day the ceiling
caught its own module at 304 lines — the mechanism working on its
keeper.
"""

from __future__ import annotations

import json
from pathlib import Path

from curvature.gate.findings import Finding, is_vendored, walk_source
from curvature.gate.ratchet import Ratchet, loosened, previous_committed


def check_ceilings(root: Path, ratchet: Ratchet) -> list[Finding]:
    """ANOM-140: no file outgrows its ceiling. Split while the split is cheap."""
    findings = []
    for path in walk_source(root, frozenset({".py", ".css", ".js"})):
        if is_vendored(path):
            continue
        relpath = str(path.relative_to(root))
        ceiling = ratchet.ceiling_for(path, relpath)
        if ceiling is None:
            continue
        lines = len(path.read_text(errors="replace").splitlines())
        if lines > ceiling:
            findings.append(Finding(
                "ANOM-140", relpath, None,
                f"{lines} lines against a ceiling of {ceiling}; split it (C-400)",
            ))
    return findings


def check_coverage(root: Path, ratchet: Ratchet) -> list[Finding]:
    """ANOM-141: the coverage floor holds (C-401)."""
    if ratchet.coverage_floor <= 0:
        return []
    report = root / "coverage.json"
    if not report.exists():
        return [Finding(
            "ANOM-141", "coverage.json", None,
            f"floor is {ratchet.coverage_floor} but no coverage report exists; "
            "run pytest --cov --cov-report=json first (C-401)",
        )]
    percent = json.loads(report.read_text())["totals"]["percent_covered"]
    if percent < ratchet.coverage_floor:
        return [Finding(
            "ANOM-141", "coverage.json", None,
            f"coverage {percent:.2f} is under the floor {ratchet.coverage_floor} (C-401)",
        )]
    return []


def check_ratchet_integrity(root: Path, ratchet: Ratchet) -> list[Finding]:
    """ANOM-142: nothing loosened since the last commit (C-402)."""
    committed = previous_committed(root)
    if committed is None:
        return []
    return [
        Finding("ANOM-142", "ratchet.toml", None, f"{complaint} (C-402)")
        for complaint in loosened(ratchet, committed)
    ]


def check_version_currency(root: Path) -> list[Finding]:
    """ANOM-143: the version moves like a ratchet (C-403). publish.sh
    tags every release; if the tag for pyproject's current version
    exists and HEAD has moved past it, someone forgot the bump — the
    thing the kids always forget, now unforgettable."""
    import subprocess
    import tomllib

    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return []
    version = tomllib.loads(pyproject.read_text()).get("project", {}).get("version")
    if not version:
        return []
    try:
        tag_commit = subprocess.run(
            ["git", "-C", str(root), "rev-list", "-1", f"v{version}"],
            capture_output=True, text=True, timeout=10,
        )
        head_commit = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if tag_commit.returncode != 0 or head_commit.returncode != 0:
        return []  # no such tag (unpublished version) or no git: nothing to hold
    if tag_commit.stdout.strip() != head_commit.stdout.strip():
        return [Finding(
            "ANOM-143", "pyproject.toml", None,
            f"version {version} is already tagged v{version} but HEAD has "
            "moved on — bump the version (C-403: versions move like ratchets)",
        )]
    return []
