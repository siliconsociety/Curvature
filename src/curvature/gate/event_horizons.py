"""Declared consumer client enclaves: different physics, bounded at the fence."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from curvature.gate.findings import Finding

SCHEMA = "curvature-event-horizon/0.2"
TOP_LEVEL_FIELDS = frozenset(
    {
        "spec",
        "name",
        "purpose",
        "entrypoint",
        "stylesheet",
        "server_contract",
        "capabilities",
        "budget_bytes",
    }
)
REQUIRED_FIELDS = TOP_LEVEL_FIELDS - {"stylesheet"}
CAPABILITY_FIELDS = frozenset(
    {"network", "storage", "html_injection", "history", "local_time"}
)
REQUIRED_CAPABILITIES = frozenset({"network", "storage", "html_injection"})
CAPABILITY_PATTERNS = {
    "storage": {
        "localStorage": re.compile(r"\blocalStorage\b"),
        "sessionStorage": re.compile(r"\bsessionStorage\b"),
        "indexedDB": re.compile(r"\bindexedDB\b"),
        "document.cookie": re.compile(r"\bdocument\s*\.\s*cookie\b"),
    },
    "html_injection": {
        "innerHTML": re.compile(r"\.\s*innerHTML\b"),
        "outerHTML": re.compile(r"\.\s*outerHTML\b"),
        "insertAdjacentHTML": re.compile(r"\.\s*insertAdjacentHTML\s*\("),
        "document.write": re.compile(r"\bdocument\s*\.\s*write\s*\("),
    },
    "history": {
        "history.pushState": re.compile(r"\bhistory\s*\.\s*pushState\s*\("),
        "history.replaceState": re.compile(r"\bhistory\s*\.\s*replaceState\s*\("),
    },
    "local_time": {
        "Intl.DateTimeFormat": re.compile(r"\bIntl\s*\.\s*DateTimeFormat\s*\("),
        "toLocaleString": re.compile(r"\.\s*toLocaleString\s*\("),
        "toLocaleDateString": re.compile(r"\.\s*toLocaleDateString\s*\("),
        "toLocaleTimeString": re.compile(r"\.\s*toLocaleTimeString\s*\("),
    },
}
ALLOW_WITH_REASON = re.compile(r"curvature-allow:\s*\S")


@dataclass(frozen=True)
class EventHorizon:
    directory: Path
    manifest: Path
    entrypoint: Path
    stylesheet: Path | None
    capabilities: dict[str, bool]
    budgets: dict[str, int]

    @property
    def network_authority(self) -> frozenset[str]:
        # v0.2's boolean deliberately means fetch, not arbitrary networking.
        return frozenset({"fetch"}) if self.capabilities["network"] else frozenset()


@dataclass(frozen=True)
class HorizonCatalog:
    root: Path
    horizons: tuple[EventHorizon, ...]
    findings: tuple[Finding, ...]

    def entrypoint_for(self, path: Path) -> EventHorizon | None:
        exact = path.absolute()
        return next(
            (horizon for horizon in self.horizons if horizon.entrypoint == exact),
            None,
        )

    def horizon_for_directory(self, directory: Path) -> EventHorizon | None:
        resolved = directory.resolve()
        return next(
            (horizon for horizon in self.horizons if horizon.directory == resolved),
            None,
        )


def load(root: Path) -> HorizonCatalog:
    """Read exact v0.2 manifests and return only structurally valid charters."""
    root = root.resolve()
    vendor = root / "app/static/vendor"
    horizons: list[EventHorizon] = []
    findings: list[Finding] = []
    if not vendor.is_dir():
        return HorizonCatalog(root, (), ())
    if vendor.absolute() != vendor.resolve():
        return HorizonCatalog(root, (), (Finding(
            "ANOM-120",
            "app/static/vendor",
            None,
            "Event Horizon root must be a real directory inside app/static (C-300)",
        ),))
    for manifest in sorted(vendor.glob("*/event-horizon.json")):
        horizon, problems = _load_one(root, manifest)
        findings.extend(problems)
        if horizon is not None:
            horizons.append(horizon)
            findings.extend(_budget_findings(root, horizon))
    return HorizonCatalog(root, tuple(horizons), tuple(findings))


def check_capabilities(root: Path) -> list[Finding]:
    """ANOM-123: machine-visible enclave capabilities stay inside the charter."""
    catalog = load(root)
    findings: list[Finding] = []
    for horizon in catalog.horizons:
        source = horizon.entrypoint.read_text(errors="replace")
        lines = source.splitlines()
        for capability, patterns in CAPABILITY_PATTERNS.items():
            if horizon.capabilities.get(capability, False):
                continue
            for token, pattern in patterns.items():
                for match in pattern.finditer(source):
                    line = source.count("\n", 0, match.start()) + 1
                    if ALLOW_WITH_REASON.search(lines[line - 1]):
                        continue
                    findings.append(Finding(
                        "ANOM-123",
                        str(horizon.entrypoint.relative_to(catalog.root)),
                        line,
                        f"manifest field capabilities.{capability} is false; "
                        f"observed {token} (C-305)",
                    ))
    return findings


def _load_one(
    root: Path,
    manifest: Path,
) -> tuple[EventHorizon | None, list[Finding]]:
    problems: list[Finding] = []
    if (
        manifest.is_symlink()
        or manifest.parent.absolute() != manifest.parent.resolve()
        or manifest.resolve().parent != manifest.parent.resolve()
    ):
        return None, [_finding(
            root,
            manifest,
            "must be a regular file inside the declared horizon",
        )]
    try:
        data = json.loads(manifest.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return None, [_finding(root, manifest, f"cannot read valid JSON: {error}")]
    if not isinstance(data, dict):
        return None, [_finding(root, manifest, "manifest root must be an object")]

    missing = sorted(REQUIRED_FIELDS - set(data))
    unknown = sorted(set(data) - TOP_LEVEL_FIELDS)
    for field in missing:
        problems.append(_finding(root, manifest, f"required field {field!r} is missing"))
    for field in unknown:
        problems.append(_finding(root, manifest, f"unknown field {field!r}"))

    if data.get("spec") != SCHEMA:
        problems.append(_finding(
            root,
            manifest,
            f"field 'spec' must be {SCHEMA!r}; observed {data.get('spec')!r}",
        ))
    name = data.get("name")
    if not _nonempty(name) or name != manifest.parent.name:
        problems.append(_finding(
            root,
            manifest,
            f"field 'name' must match directory {manifest.parent.name!r}; observed {name!r}",
        ))
    if not _nonempty(data.get("purpose")):
        problems.append(_finding(root, manifest, "field 'purpose' must be a non-empty string"))
    if not _string_map(data.get("server_contract")):
        problems.append(_finding(
            root,
            manifest,
            "field 'server_contract' must be a non-empty string map",
        ))

    entrypoint = _declared_file(
        root, manifest, data.get("entrypoint"), ".js", "entrypoint", problems
    )
    stylesheet = None
    if "stylesheet" in data:
        stylesheet = _declared_file(
            root, manifest, data.get("stylesheet"), ".css", "stylesheet", problems
        )
    capabilities = _capabilities(root, manifest, data.get("capabilities"), problems)
    budgets = _budgets(
        root, manifest, data.get("budget_bytes"), stylesheet is not None, problems
    )
    if problems or entrypoint is None or capabilities is None or budgets is None:
        return None, problems
    return EventHorizon(
        manifest.parent.resolve(),
        manifest.resolve(),
        entrypoint,
        stylesheet,
        capabilities,
        budgets,
    ), []


def _declared_file(
    root: Path,
    manifest: Path,
    value: Any,
    suffix: str,
    field: str,
    problems: list[Finding],
) -> Path | None:
    if not _nonempty(value):
        problems.append(_finding(root, manifest, f"field {field!r} must be a filename"))
        return None
    relative = Path(value)
    declared = manifest.parent / relative
    candidate = declared.resolve()
    if (
        relative.is_absolute()
        or len(relative.parts) != 1
        or relative.suffix != suffix
        or declared.is_symlink()
        or candidate.parent != manifest.parent.resolve()
    ):
        problems.append(_finding(
            root, manifest, f"field {field!r} must name one {suffix} file inside its horizon"
        ))
        return None
    if not candidate.is_file():
        problems.append(_finding(
            root, manifest, f"field {field!r} declares missing file {value!r}"
        ))
        return None
    return candidate


def _capabilities(
    root: Path,
    manifest: Path,
    value: Any,
    problems: list[Finding],
) -> dict[str, bool] | None:
    if not isinstance(value, dict):
        problems.append(_finding(root, manifest, "field 'capabilities' must be an object"))
        return None
    for field in sorted(REQUIRED_CAPABILITIES - set(value)):
        problems.append(_finding(
            root, manifest, f"required field 'capabilities.{field}' is missing"
        ))
    for field in sorted(set(value) - CAPABILITY_FIELDS):
        problems.append(_finding(
            root, manifest, f"unknown capability {field!r}; the schema grants authority"
        ))
    for field, enabled in sorted(value.items()):
        if type(enabled) is not bool:
            problems.append(_finding(
                root, manifest, f"field 'capabilities.{field}' must be boolean"
            ))
    if problems:
        return None
    return {field: bool(value.get(field, False)) for field in CAPABILITY_FIELDS}


def _budgets(
    root: Path,
    manifest: Path,
    value: Any,
    has_stylesheet: bool,
    problems: list[Finding],
) -> dict[str, int] | None:
    if not isinstance(value, dict):
        problems.append(_finding(root, manifest, "field 'budget_bytes' must be an object"))
        return None
    expected = {"javascript", *(("css",) if has_stylesheet else ())}
    for field in sorted(expected - set(value)):
        problems.append(_finding(
            root, manifest, f"required field 'budget_bytes.{field}' is missing"
        ))
    for field in sorted(set(value) - expected):
        problems.append(_finding(
            root, manifest, f"field 'budget_bytes.{field}' has no declared artifact"
        ))
    for field, budget in sorted(value.items()):
        if type(budget) is not int or budget <= 0:
            problems.append(_finding(
                root, manifest, f"field 'budget_bytes.{field}' must be a positive integer"
            ))
    if problems:
        return None
    return {field: int(value[field]) for field in expected}


def _budget_findings(root: Path, horizon: EventHorizon) -> list[Finding]:
    artifacts = {"javascript": horizon.entrypoint}
    if horizon.stylesheet is not None:
        artifacts["css"] = horizon.stylesheet
    findings = []
    for medium, path in artifacts.items():
        observed = len(path.read_bytes())
        budget = horizon.budgets[medium]
        if observed > budget:
            findings.append(Finding(
                "ANOM-120",
                str(path.relative_to(root)),
                None,
                f"manifest field budget_bytes.{medium} declares {budget} bytes; "
                f"observed {observed} (C-300)",
            ))
    return findings


def _finding(root: Path, manifest: Path, message: str) -> Finding:
    return Finding(
        "ANOM-120",
        str(manifest.relative_to(root)),
        None,
        f"Event Horizon manifest {message} (C-300)",
    )


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_map(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and bool(value)
        and all(_nonempty(key) and _nonempty(item) for key, item in value.items())
    )
