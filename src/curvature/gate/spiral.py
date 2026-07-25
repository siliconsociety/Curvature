"""Spiral: Fibonacci growth without unbounded local branching (C-602)."""

from __future__ import annotations

import math
import tomllib
from dataclasses import dataclass
from pathlib import Path

from curvature.gate.findings import Finding, is_vendored, walk_source
from curvature.gate.ratchet import DEFAULT_CEILINGS, Ratchet

BRANCH_TARGET = 8
BRANCH_LIMIT = 13
GROWTH_ORIGIN = 13
SOURCE_SUFFIXES = frozenset(f".{suffix}" for suffix in DEFAULT_CEILINGS)


@dataclass(frozen=True)
class SpiralTree:
    path: Path
    relpath: str
    mass: float
    scale: int
    growth: float
    fanout: dict[Path, int]


@dataclass(frozen=True)
class Spiral:
    project_root: Path
    trees: tuple[SpiralTree, ...]

    def tree_for(self, path: Path) -> SpiralTree | None:
        return next((tree for tree in self.trees if path.is_relative_to(tree.path)), None)

    def ceiling_for(self, path: Path, ratchet: Ratchet) -> int | None:
        relpath = str(path.relative_to(self.project_root))
        if relpath in ratchet.exceptions:
            return ratchet.exceptions[relpath]
        base = ratchet.ceilings.get(path.suffix.lstrip("."))
        tree = self.tree_for(path)
        if base is None or tree is None:
            return base
        if tree.fanout.get(path.parent, 0) > BRANCH_LIMIT:
            return base
        return scaled_ceiling(base, tree.growth)

    def branch_findings(self) -> list[Finding]:
        findings = []
        for tree in self.trees:
            for directory, children in sorted(tree.fanout.items()):
                if children <= BRANCH_LIMIT:
                    continue
                relpath = str(directory.relative_to(self.project_root))
                findings.append(Finding(
                    "ANOM-152",
                    relpath,
                    None,
                    f"{children} meaningful children against Spiral's branch span of "
                    f"{BRANCH_LIMIT}; branch by responsibility toward "
                    f"{BRANCH_TARGET} + {BRANCH_LIMIT - BRANCH_TARGET} (C-602)",
                ))
        return findings

    def info(self, ratchet: Ratchet) -> list[str]:
        lines = []
        for tree in self.trees:
            ceilings = ", ".join(
                f".{suffix} {scaled_ceiling(ceiling, tree.growth)}"
                for suffix, ceiling in sorted(ratchet.ceilings.items())
            )
            lines.append(
                f"Spiral {tree.relpath}: mass {tree.mass:.1f}, scale {tree.scale}, "
                f"healthy-leaf ceilings {ceilings}"
            )
        return lines


def fibonacci_scale(mass: float) -> int:
    """The greatest distinct Fibonacci threshold not exceeding mass."""
    previous, current = 1, 2
    scale = 0
    while previous <= mass:
        scale = previous
        previous, current = current, previous + current
    return scale


def growth_for(scale: int) -> float:
    if scale < GROWTH_ORIGIN:
        return 1.0
    return math.sqrt(scale / GROWTH_ORIGIN)


def scaled_ceiling(base: int, growth: float) -> int:
    return round(base * growth)


def load(root: Path) -> tuple[Spiral | None, list[Finding]]:
    """Load an optional [tool.curvature.spiral] protocol from pyproject.toml."""
    root = root.resolve()
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return None, []
    try:
        data = tomllib.loads(pyproject.read_text())
    except tomllib.TOMLDecodeError as error:
        return None, [_config_finding(f"cannot read configuration: {error}")]
    tool = data.get("tool", {})
    if not isinstance(tool, dict):
        return None, []
    curvature = tool.get("curvature", {})
    if not isinstance(curvature, dict):
        return None, [_config_finding("configuration must be a table")]
    table = curvature.get("spiral")
    if table is None:
        return None, []
    if not isinstance(table, dict):
        return None, [_config_finding("configuration must be a table")]
    unknown = sorted(set(table) - {"enabled", "roots"})
    if unknown:
        return None, [_config_finding(f"unknown option {unknown[0]!r}")]
    enabled = table.get("enabled", True)
    if not isinstance(enabled, bool):
        return None, [_config_finding("enabled must be true or false")]
    if not enabled:
        return None, []
    configured_roots = table.get("roots", ["app"])
    if (
        not isinstance(configured_roots, list)
        or not configured_roots
        or not all(isinstance(item, str) and item for item in configured_roots)
    ):
        return None, [_config_finding("roots must be a non-empty list of paths")]
    paths, errors = _resolve_roots(root, configured_roots)
    if errors:
        return None, [_config_finding(error) for error in errors]
    return Spiral(root, tuple(_analyze(root, path) for path in paths)), []


def _resolve_roots(root: Path, configured: list[str]) -> tuple[list[Path], list[str]]:
    paths = []
    errors = []
    for value in configured:
        relative = Path(value)
        candidate = (root / relative).resolve()
        if relative.is_absolute() or ".." in relative.parts or not candidate.is_relative_to(root):
            errors.append(f"root {value!r} must stay inside the project")
        elif not candidate.is_dir():
            errors.append(f"root {value!r} is not a directory")
        elif candidate in paths:
            errors.append(f"root {value!r} is repeated")
        else:
            paths.append(candidate)
    for index, path in enumerate(paths):
        if any(
            path != other and (path.is_relative_to(other) or other.is_relative_to(path))
            for other in paths[index + 1 :]
        ):
            errors.append("roots must not overlap")
            break
    return paths, errors


def _analyze(project_root: Path, tree_root: Path) -> SpiralTree:
    lines = {
        path: len(path.read_text(errors="replace").splitlines())
        for path in walk_source(tree_root, SOURCE_SUFFIXES)
        if not is_vendored(path)
    }
    meaningful = {path for path, count in lines.items() if count}
    fanout: dict[Path, int] = {}
    directories = {tree_root}
    for path in meaningful:
        directory = path.parent
        while directory.is_relative_to(tree_root):
            directories.add(directory)
            if directory == tree_root:
                break
            directory = directory.parent
    for directory in directories:
        children = {
            directory / path.relative_to(directory).parts[0]
            for path in meaningful
            if path.is_relative_to(directory)
        }
        fanout[directory] = len(children)
    mass = sum(
        count / DEFAULT_CEILINGS[path.suffix.lstrip(".")]
        for path, count in lines.items()
    )
    scale = fibonacci_scale(mass)
    relpath = str(tree_root.relative_to(project_root)) or "."
    return SpiralTree(tree_root, relpath, mass, scale, growth_for(scale), fanout)


def _config_finding(message: str) -> Finding:
    return Finding("ANOM-152", "pyproject.toml", None, f"Spiral {message} (C-602)")
