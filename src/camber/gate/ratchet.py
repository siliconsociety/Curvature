"""ratchet.toml — the numbers that move one way (C-400, C-401, C-402).

`camber ratchet` is the only hand on the mechanism: it lowers ceilings to
current actuals, raises the coverage floor to the current actual, drops
exceptions that fit under the defaults, and never once turns the other
direction. Loosening is a human editing the file, and OC-142 catches it
against git history."""

from __future__ import annotations

import subprocess
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

RATCHET_FILE = "ratchet.toml"
DEFAULT_CEILINGS = {"py": 300, "css": 250, "js": 150}


@dataclass
class Ratchet:
    ceilings: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_CEILINGS))
    exceptions: dict[str, int] = field(default_factory=dict)
    coverage_floor: float = 0.0

    def ceiling_for(self, path: Path, relpath: str) -> int | None:
        if relpath in self.exceptions:
            return self.exceptions[relpath]
        return self.ceilings.get(path.suffix.lstrip("."))


def load(root: Path) -> Ratchet:
    file = root / RATCHET_FILE
    if not file.exists():
        return Ratchet()
    data = tomllib.loads(file.read_text())
    ceilings = {k: v for k, v in data.get("ceilings", {}).items() if not isinstance(v, dict)}
    return Ratchet(
        ceilings={**DEFAULT_CEILINGS, **ceilings},
        exceptions=dict(data.get("ceilings", {}).get("exceptions", {})),
        coverage_floor=float(data.get("floors", {}).get("coverage", 0.0)),
    )


def dump(ratchet: Ratchet) -> str:
    lines = ["# Managed by `camber ratchet`. The numbers in this file move one way.",
             "", "[ceilings]"]
    for suffix, ceiling in sorted(ratchet.ceilings.items()):
        lines.append(f"{suffix} = {ceiling}")
    if ratchet.exceptions:
        lines += ["", "[ceilings.exceptions]",
                  "# Grandfathered files pinned at their high-water mark; they only shrink."]
        for relpath, ceiling in sorted(ratchet.exceptions.items()):
            lines.append(f'"{relpath}" = {ceiling}')
    lines += ["", "[floors]", f"coverage = {ratchet.coverage_floor}", ""]
    return "\n".join(lines)


def save(root: Path, ratchet: Ratchet) -> None:
    (root / RATCHET_FILE).write_text(dump(ratchet))


def previous_committed(root: Path) -> Ratchet | None:
    """The ratchet as git last saw it, for the loosening check (OC-142)."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "show", f"HEAD:{RATCHET_FILE}"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    data = tomllib.loads(result.stdout)
    ceilings = {k: v for k, v in data.get("ceilings", {}).items() if not isinstance(v, dict)}
    return Ratchet(
        ceilings={**DEFAULT_CEILINGS, **ceilings},
        exceptions=dict(data.get("ceilings", {}).get("exceptions", {})),
        coverage_floor=float(data.get("floors", {}).get("coverage", 0.0)),
    )


def loosened(current: Ratchet, committed: Ratchet) -> list[str]:
    """Every way the working ratchet is looser than the committed one."""
    complaints: list[str] = []
    for suffix, ceiling in current.ceilings.items():
        old = committed.ceilings.get(suffix)
        if old is not None and ceiling > old:
            complaints.append(f"ceiling .{suffix} raised {old} -> {ceiling}")
    for relpath, ceiling in current.exceptions.items():
        old = committed.exceptions.get(relpath)
        if old is None:
            complaints.append(f"new grandfather exception {relpath!r} = {ceiling}")
        elif ceiling > old:
            complaints.append(f"exception {relpath!r} raised {old} -> {ceiling}")
    if current.coverage_floor < committed.coverage_floor:
        complaints.append(
            f"coverage floor lowered {committed.coverage_floor} -> {current.coverage_floor}"
        )
    return complaints
