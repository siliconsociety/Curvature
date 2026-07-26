"""The vocabulary of the gate: findings are anomalies, not 'errors'.

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


CLIENT_ENTRIES = frozenset({"curvature.js", "live.js"})
CLIENT_NETWORK_AUTHORITY = {
    "curvature.js": frozenset({"fetch"}),
    "live.js": frozenset({"EventSource"}),
}
FRAMEWORK_PACKAGE_DIRECTORY = Path(__file__).resolve().parents[1]


def framework_client_directory(root: Path) -> Path | None:
    """Locate entries owned by the exact Curvature package running this gate.

    Filesystem identity is bounded ownership evidence, not cryptographic
    provenance. Project metadata and lookalike paths grant no authority.
    """
    package = FRAMEWORK_PACKAGE_DIRECTORY.resolve()
    if root.resolve() == package:
        return package / "static"
    source_package = (root / "src/curvature").resolve()
    if source_package == package:
        return source_package / "static"
    return None


def is_framework_client(path: Path, root: Path) -> bool:
    """A chartered public entry at the exact package-owned path (C-300)."""
    directory = framework_client_directory(root)
    return bool(
        directory
        and path.parent.resolve() == directory.resolve()
        and path.name in CLIENT_ENTRIES
    )
