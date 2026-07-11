"""The document shell — a combinator, not a component: it takes rendered
fragments and pours the page around them. Runs only for unboosted requests."""

from __future__ import annotations

from camber import Element
from camber import html as h


def shell(*fragments: Element) -> Element:
    return h.html(
        h.head(
            h.meta(charset="utf-8"),
            h.meta(name="viewport", content="width=device-width, initial-scale=1"),
            h.title("Pit Board — a Camber demo"),
            h.style_link("/static/tarmac.css"),
            h.script(src="/static/lib/camber.js"),
        ),
        h.body(
            h.header(
                h.h1("Pit Board"),
                h.p("Every lap counted. With JavaScript switched off, nothing changes."),
            ),
            h.main(*fragments),
            data_boost=True,
        ),
        lang="en",
    )
