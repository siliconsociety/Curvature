"""The source checks: tokens and syntax trees. One function per rule.
The bounds family (ceilings, floors, versions) lives in bounds.py.

These are deliberately unclever. A check an agent cannot predict is a
check an agent cannot steer by; boring, greppable rules are the product.
"""

from __future__ import annotations

import ast
from pathlib import Path

from curvature.gate.findings import Finding, is_boost_layer, is_vendored, walk_source

HTTP_TOKENS = ("fetch(", "XMLHttpRequest", "WebSocket(", "EventSource(")
MUTATING_VERBS = frozenset({"post", "put", "delete", "patch"})
JSON_ESCAPE_HATCH = "# curvature: json-endpoint"
ALLOW_PRAGMA = "curvature-allow"


def _allowed(line: str) -> bool:
    """Token checks honor an explicit, greppable pragma. Enforcement code
    and tests that exercise refusals need to spell the forbidden words;
    the pragma is counted (see cli info lines) so it cannot hide."""
    return ALLOW_PRAGMA in line


def check_js_placement(root: Path) -> list[Finding]:
    """ANOM-120: the only first-party script is the boost layer (C-300)."""
    findings = []
    for path in walk_source(root, frozenset({".js"})):
        if is_vendored(path) or is_boost_layer(path):
            continue
        findings.append(Finding(
            "ANOM-120", str(path.relative_to(root)), None,
            "first-party JavaScript outside the boost layer (C-300); "
            "move the behavior server-side or into native HTML",
        ))
    return findings


def check_js_http(root: Path) -> list[Finding]:
    """ANOM-121: JavaScript never speaks HTTP on its own (C-301)."""
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
                        "ANOM-121", str(path.relative_to(root)), number,
                        f"{token.rstrip('(')} outside the boost layer (C-301)",
                    ))
    return findings


def check_dom_sins(root: Path) -> list[Finding]:
    """ANOM-130: no click handlers in attributes, no script-scheme URLs (C-200)."""
    findings = []
    for path in walk_source(root, frozenset({".py", ".html"})):
        relpath = str(path.relative_to(root))
        for number, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            if _allowed(line):
                continue
            if "onclick" in line.casefold():  # curvature-allow: enforcement
                findings.append(Finding(
                    "ANOM-130", relpath, number,
                    "a click handler is a behavior with no URL (C-200); use a form",
                ))
            if "javascript:" in line.casefold():  # curvature-allow: enforcement
                message = "javascript: URL (C-200)"  # curvature-allow: message
                findings.append(Finding("ANOM-130", relpath, number, message))
    return findings


def _returns_element(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    match node.returns:
        case ast.Name(id="Element"):
            return True
        case ast.Attribute(attr="Element"):
            return True
    return False


def check_component_signatures(root: Path) -> list[Finding]:
    """ANOM-110: in components/ trees, Element-returning functions take Props
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
                    "ANOM-110", str(path.relative_to(root)), node.lineno,
                    f"component {node.name}() must take a Props model first (C-100); "
                    f"got {name or 'no annotation'}",
                ))
    return findings


def _decorator_verb(decorator: ast.expr) -> str | None:
    match decorator:
        case ast.Call(func=ast.Attribute(attr=attr)) if attr in MUTATING_VERBS:
            return attr
    return None


def _is_redirect_call(node: ast.expr) -> bool:
    return isinstance(node, ast.Call) and (
        (isinstance(node.func, ast.Name) and node.func.id == "redirect")
        or (isinstance(node.func, ast.Attribute) and node.func.attr == "redirect")
    )


def check_mutating_routes(root: Path) -> list[Finding]:
    """ANOM-131: mutating routes redirect; they never render (C-201)."""
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
            redirect_names = {
                target.id
                for stmt in ast.walk(node)
                if isinstance(stmt, ast.Assign) and _is_redirect_call(stmt.value)
                for target in stmt.targets
                if isinstance(target, ast.Name)
            }
            redirects = sum(
                _is_redirect_call(r)
                or (isinstance(r, ast.Name) and r.id in redirect_names)
                for r in returns
            )
            if redirects == 0 or redirects < len(returns):
                findings.append(Finding(
                    "ANOM-131", str(path.relative_to(root)), node.lineno,
                    f"{verb.upper()} route {node.name}() must return redirect() on "
                    f"every path (C-201), or carry '{JSON_ESCAPE_HATCH}'",
                ))
    return findings


def check_purposes(root: Path) -> list[Finding]:
    """ANOM-170: every respond() call in app code authors a purpose
    (C-902) — the one orientation line derivation cannot supply. Tests
    exercise the runtime, not screens, and are exempt."""
    findings = []
    for path in walk_source(root, frozenset({".py"})):
        if "tests" in path.parts or path.name.startswith("test_"):
            continue
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = ""
            match node.func:
                case ast.Name(id=id_):
                    name = id_
                case ast.Attribute(attr=attr):
                    name = attr
            if name != "respond":
                continue
            if not any(kw.arg == "purpose" for kw in node.keywords):
                findings.append(Finding(
                    "ANOM-170", str(path.relative_to(root)), node.lineno,
                    "respond() without purpose= (C-902): the chart needs its "
                    "one authored line of orientation",
                ))
    return findings


def raw_census(root: Path) -> int:
    """ANOM-122: how many places admit unescaped markup. Informational."""
    count = 0
    for path in walk_source(root, frozenset({".py"})):
        count += path.read_text(errors="replace").count("raw(")
    return count


def pragma_census(root: Path) -> int:
    """Every curvature-allow pragma in the project. Informational: the escape
    hatch stays visible so it can be argued about in review."""
    count = 0
    for path in walk_source(root, frozenset({".py", ".js", ".html"})):
        count += path.read_text(errors="replace").count(ALLOW_PRAGMA)
    return count
