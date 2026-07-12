"""The atlas — every chart a manifold serves (C-903).

In differential geometry an atlas is the collection of charts that
covers a manifold. Here it is simply a screen: a nav of real links to
every readable region. Humans get a sitemap; agents request the same
screen's chart and receive the atlas as machine-readable link
affordances. No second format, no special endpoint semantics — the
atlas is made of the same stuff as everything else.
"""

from __future__ import annotations

from typing import Any

from curvature import html as h
from curvature.html import Element


def _readable_routes(app: Any) -> list[tuple[str, str]]:
    regions: list[tuple[str, str]] = []
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if path is None or methods is None or "GET" not in methods:
            continue
        if "{" in path:
            continue  # parameterized regions are reached from their parents
        name = getattr(route, "name", "") or path
        regions.append((path, name.replace("_", " ")))
    return sorted(set(regions))


def atlas(app: Any, *, exclude: tuple[str, ...] = ()) -> Element:
    """The fragment: link every readable region. Mount it on a route of
    your choosing and pass the same purpose you'd give any screen."""
    skips = set(exclude)
    return h.nav(
        h.h2("Atlas"),
        h.ul(
            (
                h.li(h.a(name, href=path))
                for path, name in _readable_routes(app)
                if path not in skips
            ),
            class_="atlas-regions",
        ),
        id="atlas",
    )
