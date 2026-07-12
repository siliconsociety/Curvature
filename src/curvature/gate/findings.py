"""The vocabulary of the gate: findings are flat spots, not 'errors'.

Rule IDs map one-to-one to SPEC.md's finding index. A finding names the
invariant it serves, because the traceback should teach."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

EXCLUDED_DIRS = frozenset(
    {".git", ".venv", ".cache", "__pycache__", "node_modules",
     "dist", "htmlcov", ".pytest_cache", ".idea", ".ruff_cache"}
)


@dataclass(frozen=True)
class Finding:
    rule: str
    path: str
    line: int | None
    message: str

    def __str__(self) -> str:
        location = f"{self.path}:{self.line}" if self.line else self.path
        return f"{self.rule} {location} — {self.message}"


def walk_source(root: Path, suffixes: frozenset[str]) -> list[Path]:
    """Every source file the gate can see, deterministic order."""
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in suffixes:
            continue
        parts = set(path.relative_to(root).parts[:-1])
        if parts & EXCLUDED_DIRS:
            continue
        files.append(path)
    return files


def is_vendored(path: Path) -> bool:
    parts = path.parts
    return any(
        parts[i] == "static" and parts[i + 1] == "vendor"
        for i in range(len(parts) - 1)
    )


def is_boost_layer(path: Path) -> bool:
    """curvature.js under a static/ directory is the one first-party script."""
    return path.name == "curvature.js" and "static" in path.parts
