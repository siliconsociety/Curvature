"""The timing tower — the living roadmap wearing its true clothes.

A pit board is the sign the crew hangs over the wall: what's on track,
what comes next, and what shipped. One vertical tower, monospace
discipline, recent work first. Git is the editor and timekeeper; Live
reflects its changes into every open page.
"""

from __future__ import annotations

from curvature import Element, Props
from curvature import html as h
from demo.roadmap_store import Item


class TowerProps(Props):
    on_track: tuple[Item, ...]
    shipped: tuple[Item, ...]
    queued: tuple[Item, ...]


class RowProps(Props):
    item: Item
    marker: str
    dim: bool = False
    pulse: bool = False


def _row(props: RowProps) -> Element:
    item = props.item
    classes = "row"
    if props.dim:
        classes += " row-dim"
    return h.li(
        h.span(props.marker, class_="marker pulse" if props.pulse else "marker"),
        h.div(
            h.h4(item.title),
            h.p(item.note, class_="row-note") if item.note else None,
            class_="row-body",
        ),
        class_=classes,
    )


def tower(props: TowerProps) -> Element:
    return h.section(
        h.p("LIVE ROADMAP · RECENT FIRST", class_="tower-legend"),
        h.h3("ON TRACK", class_="lane-mark lane-mark-track"),
        h.ul(
            (
                _row(RowProps(item=item, marker="●", pulse=True))
                for item in props.on_track
            ),
            class_="rows",
        ) if props.on_track else h.p("Track is clear.", class_="empty"),
        h.h3("NEXT UP", class_="lane-mark"),
        h.ul(
            (
                _row(RowProps(item=item, marker="—", dim=True))
                for item in props.queued
            ),
            class_="rows",
        ),
        h.h3("SHIPPED", class_="lane-mark lane-mark-shipped"),
        h.ul(
            (
                _row(RowProps(item=item, marker=item.pit_id or "—"))
                for item in props.shipped
            ),
            class_="rows",
        ),
        id="pit-tower",
        data_live="/live",
    )
