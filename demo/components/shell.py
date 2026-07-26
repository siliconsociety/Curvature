"""The Pit Board document shell pours the page around demo fragments."""

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
            h.title("Pit Board — Curvature's release-history demo"),
            h.link(rel="icon", type="image/png", href="/static/favicon.png"),
            h.style_link("/static/manifold.css"),
            h.style_link("/static/tower.css"),
            h.script(src=f"/static/lib/curvature.js?v={ASSETS}"),
        ),
        h.body(
            h.header(
                h.img(src="/static/tower-emblem.png", alt="Pit Board emblem",
                      width="72", height="72", class_="emblem"),
                h.div(
                    h.h1("PIT BOARD"),
                    h.p("An illustrative Curvature release-history demo.",
                        class_="board-sub"),
                ),
                class_="board-head",
            ),
            h.main(*fragments),
            data_boost=True,
        ),
        lang="en",
    )
