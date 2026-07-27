"""Portable Markdown rules for repository-rendered documentation."""

from __future__ import annotations

import subprocess
from pathlib import Path

from curvature.gate.findings import Finding, walk_source

# GitHub and package indexes do not expose the same math renderer. Keep this
# registry to syntax observed to fail on a supported public surface.
UNSAFE_MATH_TOKENS = {
    "\\operatorname": "macro is rejected by GitHub's math allowlist",
    "\\(": "inline math delimiter is not portable; use backticked notation",
    "\\)": "inline math delimiter is not portable; use backticked notation",
}


def _governed_markdown(root: Path) -> list[Path]:
    """Tracked and trackable Markdown, with a filesystem fallback outside git."""
    try:
        listed = subprocess.run(
            [
                "git", "-C", str(root), "ls-files",
                "--cached", "--others", "--exclude-standard", "-z", "--", "*.md",
            ],
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return walk_source(root, frozenset({".md"}))
    if listed.returncode != 0:
        return walk_source(root, frozenset({".md"}))
    return sorted(
        path
        for entry in listed.stdout.decode(errors="surrogateescape").split("\0")
        if entry and (path := root / entry).is_file()
    )


def check_math(root: Path) -> list[Finding]:
    """ANOM-124: governed Markdown uses the portable public math register."""
    findings = []
    for path in _governed_markdown(root):
        relpath = str(path.relative_to(root))
        for number, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            for token, reason in UNSAFE_MATH_TOKENS.items():
                if token in line:
                    findings.append(Finding(
                        "ANOM-124",
                        relpath,
                        number,
                        f"{token} is not portable Markdown math (C-304): {reason}",
                    ))
    return findings
