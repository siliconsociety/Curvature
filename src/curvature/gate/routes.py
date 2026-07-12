"""Route-shape checks for the read-render/write-redirect contract."""

from __future__ import annotations

import ast
from pathlib import Path

from curvature.gate.findings import Finding, walk_source

MUTATING_VERBS = frozenset({"post", "put", "delete", "patch"})
JSON_ESCAPE_HATCH = "# curvature: json-endpoint"


def _decorator_verbs(decorator: ast.expr) -> set[str]:
    match decorator:
        case ast.Call(func=ast.Attribute(attr=attr)) if attr in MUTATING_VERBS:
            return {attr}
        case ast.Call(func=ast.Attribute(attr="api_route" | "route"), keywords=keywords):
            methods = next((kw.value for kw in keywords if kw.arg == "methods"), None)
            if isinstance(methods, ast.List | ast.Tuple | ast.Set):
                return {
                    value.value.casefold()
                    for value in methods.elts
                    if isinstance(value, ast.Constant)
                    and isinstance(value.value, str)
                    and value.value.casefold() in MUTATING_VERBS
                }
    return set()


def _has_json_exemption(segment: str) -> bool:
    for line in segment.splitlines():
        if JSON_ESCAPE_HATCH not in line:
            continue
        reason = line.split(JSON_ESCAPE_HATCH, 1)[1].strip(" :-—")
        if reason:
            return True
    return False


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
            verbs = set().union(*(_decorator_verbs(d) for d in node.decorator_list))
            if not verbs:
                continue
            segment = ast.get_source_segment(source, node) or ""
            if _has_json_exemption(segment):
                continue
            verb = "/".join(sorted(value.upper() for value in verbs))
            returns = [
                n.value
                for n in ast.walk(node)
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
                _is_redirect_call(value)
                or (isinstance(value, ast.Name) and value.id in redirect_names)
                for value in returns
            )
            if redirects == 0 or redirects < len(returns):
                findings.append(
                    Finding(
                        "ANOM-131",
                        str(path.relative_to(root)),
                        node.lineno,
                        f"{verb} route {node.name}() must return redirect() on "
                        f"every path (C-201), or carry '{JSON_ESCAPE_HATCH}'",
                    )
                )
    return findings
