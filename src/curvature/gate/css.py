"""ANOM-150: orphan selectors (C-600).

A class selector no markup references is sediment — the lap board left
eleven families of it behind, found by hand on a garden walk. Now the
gate walks that bed itself: every `.class` token in project CSS must
appear in some class_ attribute (or literal class string) in the
project's source. Vendored CSS is pinned and exempt; tokens, element
selectors, ids, and at-rules are not class selectors and are ignored.
"""

from __future__ import annotations

import re
from pathlib import Path

from curvature.gate.findings import Finding, is_vendored, walk_source

CLASS_IN_SELECTOR = re.compile(r"\.([A-Za-z][A-Za-z0-9_-]*)")
SELECTOR_LINE = re.compile(r"^([^{}@/]+)\{", re.MULTILINE)


def _defined_classes(css_text: str) -> dict[str, int]:
    """class name -> first line of definition."""
    defined: dict[str, int] = {}
    for match in SELECTOR_LINE.finditer(css_text):
        selector = match.group(1)
        line = css_text.count("\n", 0, match.start()) + 1
        for cls in CLASS_IN_SELECTOR.findall(selector):
            defined.setdefault(cls, line)
    return defined


def _referenced_classes(root: Path) -> set[str]:
    referenced: set[str] = set()
    for path in walk_source(root, frozenset({".py", ".html"})):
        text = path.read_text(errors="replace")
        for match in re.finditer(r'class_?="([^"]*)"', text):
            referenced.update(match.group(1).split())
        for match in re.finditer(r"class_?='([^']*)'", text):
            referenced.update(match.group(1).split())
        # f-strings and conditionals build class strings in pieces;
        # harvest words from every plain string literal as a backstop
        for match in re.finditer(r'"([A-Za-z0-9_ -]{1,80})"', text):
            referenced.update(match.group(1).split())
        for match in re.finditer(r"'([A-Za-z0-9_ -]{1,80})'", text):
            referenced.update(match.group(1).split())
    return referenced


def check_orphan_css(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    referenced = None  # built lazily; most repos have no CSS at all
    for path in walk_source(root, frozenset({".css"})):
        if is_vendored(path):
            continue
        if referenced is None:
            referenced = _referenced_classes(root)
        for cls, line in sorted(_defined_classes(path.read_text(errors="replace")).items()):
            if cls not in referenced:
                findings.append(Finding(
                    "ANOM-150", str(path.relative_to(root)), line,
                    f"selector .{cls} matches nothing in this manifold (C-600); "
                    "dead style is sediment — prune it",
                ))
    return findings
