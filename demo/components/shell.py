"""The document shell — a combinator, not a component: it takes rendered
fragments and pours the page around them. Runs only for unboosted requests."""

from __future__ import annotations

from importlib.metadata import version

from curvature import Element
from curvature import html as h

ASSETS = version("curvature")


def shell(*fragments: Element) -> Element:
    return h.html(
        h.head(
            h.meta(charset="utf-8"),
            h.meta(name="viewport", content="width=device-width, initial-scale=1"),
            h.title("Pit Board — a Curvature demo"),
            h.style_link("/static/manifold.css"),
            h.style_link("/static/tower.css"),
            h.script(src=f"/static/lib/curvature.js?v={ASSETS}"),
        ),
        h.body(
            h.header(
                h.h1("Pit Board"),
                h.p("Curvature's living roadmap. With JavaScript switched off, "
                    "nothing changes — with it on, the board keeps itself."),
            ),
            h.main(*fragments),
            data_boost=True,
            data_offline_cache="/curvature-offline.js",
        ),
        lang="en",
    )
