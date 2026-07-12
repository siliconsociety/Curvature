"""The timing tower — the living roadmap wearing its true clothes.

A pit board is the sign the crew hangs over the wall: what's on track,
what's done, what the stint plan says. One vertical tower, monospace
discipline, and every control a real form wearing a pit-crew paddle:
OUT sends a planned item onto the track, FLAG takes the flag, PIT
brings one back in. Git is the timekeeper.
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


class PaddleProps(Props):
    item: Item
    direction: str
    label: str


PADDLE_HINTS = {
    "OUT": "Send onto the track — start this work",
    "FLAG": "Take the flag — mark it shipped",
    "PIT": "Pull back one lane",
}


def _paddle(props: PaddleProps) -> Element:
    return h.form(
        h.input_(type="hidden", name="direction", value=props.direction),
        h.button(props.label, class_="paddle",
                 title=PADDLE_HINTS.get(props.label, props.label),
                 aria_label=f"{props.label}: {props.item.title}"),
        action=f"/roadmap/items/{props.item.id}/move",
        method="post",
        class_="paddle-form",
    )


def _row(props: RowProps, *paddles: Element) -> Element:
    item = props.item
    classes = "row"
    if props.dim:
        classes += " row-dim"
    return h.li(
        h.span(props.marker, class_="marker pulse" if props.pulse else "marker"),
        h.div(
            h.h3(item.title),
            h.p(item.note, class_="row-note") if item.note else None,
            class_="row-body",
        ),
        h.div(*paddles, class_="paddles"),
        class_=classes,
    )


def tower(props: TowerProps) -> Element:
    return h.section(
        h.header(
            h.img(src="/static/tower-emblem.png", alt="Pit Board timing tower emblem",
                  width="72", height="72", class_="emblem"),
            h.div(
                h.h2("ROADMAP"),
                h.p("The crew's board. Git keeps the time.", class_="tower-sub"),
                h.p("OUT → on track · FLAG → shipped · PIT → back one",
                    class_="tower-legend"),
            ),
            class_="tower-head",
        ),
        h.h3("PLAN A STINT", class_="lane-mark"),
        h.form(
            h.input_(type="text", name="title", placeholder="Next stint…",
                     required=True, maxlength=120),
            h.input_(type="text", name="note", placeholder="One honest sentence",
                     maxlength=300),
            h.input_(type="hidden", name="lane", value="queued"),
            h.button("PLAN IT", class_="plan"),
            action="/roadmap/items",
            method="post",
            class_="plan-form",
        ),
        h.h3("ON TRACK", class_="lane-mark lane-mark-track"),
        h.ul(
            (
                _row(
                    RowProps(item=item, marker="●", pulse=True),
                    _paddle(PaddleProps(item=item, direction="back", label="PIT")),
                    _paddle(PaddleProps(item=item, direction="advance", label="FLAG")),
                )
                for item in props.on_track
            ),
            class_="rows",
        ) if props.on_track else h.p("Track is clear.", class_="empty"),
        h.h3("SHIPPED", class_="lane-mark lane-mark-shipped"),
        h.ul(
            (
                _row(
                    RowProps(item=item, marker=f"P{position}"),
                    _paddle(PaddleProps(item=item, direction="back", label="PIT")),
                )
                for position, item in enumerate(props.shipped, 1)
            ),
            class_="rows",
        ),
        h.h3("STINT PLAN", class_="lane-mark"),
        h.ul(
            (
                _row(
                    RowProps(item=item, marker="—", dim=True),
                    _paddle(PaddleProps(item=item, direction="advance", label="OUT")),
                )
                for item in props.queued
            ),
            class_="rows",
        ),
        id="pit-tower",
        data_live="/live",
    )
