"""The off-camber checks. One function per rule; each returns findings.

These are deliberately unclever. A check an agent cannot predict is a
check an agent cannot steer by; boring, greppable rules are the product.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

from camber.gate.findings import Finding, is_boost_layer, is_vendored, walk_source
from camber.gate.ratchet import Ratchet, loosened, previous_committed

HTTP_TOKENS = ("fetch(", "XMLHttpRequest", "WebSocket(", "EventSource(")
MUTATING_VERBS = frozenset({"post", "put", "delete", "patch"})
JSON_ESCAPE_HATCH = "# camber: json-endpoint"
ALLOW_PRAGMA = "camber-allow"


def _allowed(line: str) -> bool:
    """Token checks honor an explicit, greppable pragma. Enforcement code
    and tests that exercise refusals need to spell the forbidden words;
    the pragma is counted (see cli info lines) so it cannot hide."""
    return ALLOW_PRAGMA in line


def check_ceilings(root: Path, ratchet: Ratchet) -> list[Finding]:
    """OC-140: no file outgrows its ceiling. Split while the split is cheap."""
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
                "OC-140", relpath, None,
                f"{lines} lines against a ceiling of {ceiling}; split it (C-400)",
            ))
    return findings


def check_js_placement(root: Path) -> list[Finding]:
    """OC-120: the only first-party script is the boost layer (C-300)."""
    findings = []
    for path in walk_source(root, frozenset({".js"})):
        if is_vendored(path) or is_boost_layer(path):
            continue
        findings.append(Finding(
            "OC-120", str(path.relative_to(root)), None,
            "first-party JavaScript outside the boost layer (C-300); "
            "move the behavior server-side or into native HTML",
        ))
    return findings


def check_js_http(root: Path) -> list[Finding]:
    """OC-121: JavaScript never speaks HTTP on its own (C-301)."""
    findings = []
    for path in walk_source(root, frozenset({".js"})):
        if is_vendored(path) or is_boost_layer(path):
            continue
        for number, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            if _allowed(line):
                continue
            for token in HTTP_TOKENS:
                if token in line:
                    findings.append(Finding(
                        "OC-121", str(path.relative_to(root)), number,
                        f"{token.rstrip('(')} outside the boost layer (C-301)",
                    ))
    return findings


def check_dom_sins(root: Path) -> list[Finding]:
    """OC-130: no click handlers in attributes, no script-scheme URLs (C-200)."""
    findings = []
    for path in walk_source(root, frozenset({".py", ".html"})):
        relpath = str(path.relative_to(root))
        for number, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            if _allowed(line):
                continue
            if "onclick" in line.casefold():  # camber-allow: enforcement
                findings.append(Finding(
                    "OC-130", relpath, number,
                    "a click handler is a behavior with no URL (C-200); use a form",
                ))
            if "javascript:" in line.casefold():  # camber-allow: enforcement
                findings.append(Finding(
                    "OC-130", relpath, number, "javascript: URL (C-200)",  # camber-allow: message
                ))
    return findings


def _returns_element(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    match node.returns:
        case ast.Name(id="Element"):
            return True
        case ast.Attribute(attr="Element"):
            return True
    return False


def check_component_signatures(root: Path) -> list[Finding]:
    """OC-110: in components/ trees, Element-returning functions take Props
    first (C-100). Zero-positional combinators (shells) are composition,
    not components, and pass."""
    findings = []
    for path in walk_source(root, frozenset({".py"})):
        if "components" not in path.parts:
            continue
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            if not _returns_element(node) or not node.args.args:
                continue
            annotation = node.args.args[0].annotation
            name = ""
            match annotation:
                case ast.Name(id=id_):
                    name = id_
                case ast.Attribute(attr=attr):
                    name = attr
            if not name.endswith("Props"):
                findings.append(Finding(
                    "OC-110", str(path.relative_to(root)), node.lineno,
                    f"component {node.name}() must take a Props model first (C-100); "
                    f"got {name or 'no annotation'}",
                ))
    return findings


def _decorator_verb(decorator: ast.expr) -> str | None:
    match decorator:
        case ast.Call(func=ast.Attribute(attr=attr)) if attr in MUTATING_VERBS:
            return attr
    return None


def check_mutating_routes(root: Path) -> list[Finding]:
    """OC-131: mutating routes redirect; they never render (C-201)."""
    findings = []
    for path in walk_source(root, frozenset({".py"})):
        source = path.read_text()
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            verb = next(
                (v for d in node.decorator_list if (v := _decorator_verb(d))), None
            )
            if verb is None:
                continue
            segment = ast.get_source_segment(source, node) or ""
            if JSON_ESCAPE_HATCH in segment:
                continue
            returns = [
                n.value for n in ast.walk(node)
                if isinstance(n, ast.Return) and n.value is not None
            ]
            redirects = sum(
                isinstance(r, ast.Call)
                and (
                    (isinstance(r.func, ast.Name) and r.func.id == "redirect")
                    or (isinstance(r.func, ast.Attribute) and r.func.attr == "redirect")
                )
                for r in returns
            )
            if redirects == 0 or redirects < len(returns):
                findings.append(Finding(
                    "OC-131", str(path.relative_to(root)), node.lineno,
                    f"{verb.upper()} route {node.name}() must return redirect() on "
                    f"every path (C-201), or carry '{JSON_ESCAPE_HATCH}'",
                ))
    return findings


def check_coverage(root: Path, ratchet: Ratchet) -> list[Finding]:
    """OC-141: the coverage floor holds (C-401)."""
    if ratchet.coverage_floor <= 0:
        return []
    report = root / "coverage.json"
    if not report.exists():
        return [Finding(
            "OC-141", "coverage.json", None,
            f"floor is {ratchet.coverage_floor} but no coverage report exists; "
            "run pytest --cov --cov-report=json first (C-401)",
        )]
    percent = json.loads(report.read_text())["totals"]["percent_covered"]
    if percent < ratchet.coverage_floor:
        return [Finding(
            "OC-141", "coverage.json", None,
            f"coverage {percent:.1f} is under the floor {ratchet.coverage_floor} (C-401)",
        )]
    return []


def check_ratchet_integrity(root: Path, ratchet: Ratchet) -> list[Finding]:
    """OC-142: nothing loosened since the last commit (C-402)."""
    committed = previous_committed(root)
    if committed is None:
        return []
    return [
        Finding("OC-142", "ratchet.toml", None, f"{complaint} (C-402)")
        for complaint in loosened(ratchet, committed)
    ]


def raw_census(root: Path) -> int:
    """OC-122: how many places admit unescaped markup. Informational."""
    count = 0
    for path in walk_source(root, frozenset({".py"})):
        count += path.read_text(errors="replace").count("raw(")
    return count


def pragma_census(root: Path) -> int:
    """Every camber-allow pragma in the project. Informational: the escape
    hatch stays visible so it can be argued about in review."""
    count = 0
    for path in walk_source(root, frozenset({".py", ".js", ".html"})):
        count += path.read_text(errors="replace").count(ALLOW_PRAGMA)
    return count
