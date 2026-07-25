"""Project-shape checks that operate on branches rather than source text."""

from __future__ import annotations

import subprocess
from pathlib import Path

from curvature.gate.findings import EXCLUDED_DIRS, Finding


def check_hollow_branches(root: Path) -> list[Finding]:
    """ANOM-153: a branch with no meaningful leaves must be pruned (C-603)."""
    root = root.resolve()
    evidenced = {
        *(_cache_hollows(root)),
        *(_tracked_hollows(root)),
    }
    hollow = {
        directory
        for directory in evidenced
        if directory.is_dir() and not _has_meaningful_files(directory)
    }
    highest = [
        directory
        for directory in hollow
        if not any(parent in hollow for parent in directory.parents if parent != root)
    ]
    return [
        Finding(
            "ANOM-153",
            str(directory.relative_to(root)),
            None,
            "hollow branch: no meaningful files remain; prune the directory (C-603)",
        )
        for directory in sorted(highest)
    ]


def _cache_hollows(root: Path) -> set[Path]:
    directories = set()
    for directory, dirnames, _filenames in root.walk():
        if "__pycache__" in dirnames:
            cache = directory / "__pycache__"
            if any(cache.glob("*.pyc")):
                directories.update(_ancestors_inside(root, directory))
        dirnames[:] = [name for name in dirnames if name not in EXCLUDED_DIRS]
    return directories


def _tracked_hollows(root: Path) -> set[Path]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-tree", "-r", "--name-only", "-z", "HEAD"],
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return set()
    if result.returncode != 0:
        return set()
    directories = set()
    for encoded in result.stdout.split(b"\0"):
        if not encoded:
            continue
        path = root / encoded.decode(errors="surrogateescape")
        if path.exists():
            continue
        directories.update(_ancestors_inside(root, path.parent))
    return directories


def _has_meaningful_files(directory: Path) -> bool:
    for _current, dirnames, filenames in directory.walk():
        dirnames[:] = [name for name in dirnames if name not in EXCLUDED_DIRS]
        if any(name != ".DS_Store" for name in filenames):
            return True
    return False


def _is_excluded(root: Path, directory: Path) -> bool:
    return bool(set(directory.relative_to(root).parts) & EXCLUDED_DIRS)


def _ancestors_inside(root: Path, directory: Path) -> set[Path]:
    ancestors = set()
    while directory != root and directory.is_relative_to(root):
        if directory.is_dir() and not _is_excluded(root, directory):
            ancestors.add(directory)
        directory = directory.parent
    return ancestors
