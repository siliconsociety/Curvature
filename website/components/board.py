"""The living roadmap: three lanes, real forms, git as the audit trail."""

from __future__ import annotations

from curvature import Element, Props
from curvature import html as h
from website.store import LANES, Item

LANE_TITLES = {"queued": "Queued", "pouring": "Pouring", "shipped": "Shipped"}


class BoardProps(Props):
    lanes: dict[str, tuple[Item, ...]]


class ItemCardProps(Props):
    item: Item


class MoveFormProps(Props):
    item: Item
    direction: str
    label: str


def _move_form(props: MoveFormProps) -> Element:
    return h.form(
        h.input_(type="hidden", name="direction", value=props.direction),
        h.button(props.label, class_="move",
                 aria_label=f"move {props.item.title} {props.direction}"),
        action=f"/roadmap/items/{props.item.id}/move",
        method="post",
        class_="move-form",
    )


def item_card(props: ItemCardProps) -> Element:
    item = props.item
    position = LANES.index(item.lane)
    return h.li(
        h.header(
            _move_form(MoveFormProps(item=item, direction="back", label="◂"))
            if position > 0 else None,
            h.h3(item.title),
            _move_form(MoveFormProps(item=item, direction="advance", label="▸"))
            if position < len(LANES) - 1 else None,
            class_="item-title-row",
        ),
        h.p(item.note, class_="item-note") if item.note else None,
        class_=f"item lane-{item.lane}",
    )


def board(props: BoardProps) -> Element:
    return h.section(
        h.div(
            (
                h.section(
                    h.h2(LANE_TITLES[lane]),
                    h.ul(
                        (item_card(ItemCardProps(item=item)) for item in items),
                        class_="items",
                    ),
                    class_="lane",
                )
                for lane, items in props.lanes.items()
            ),
            class_="lanes",
        ),
        h.form(
            h.input_(type="text", name="title", placeholder="What's next…",
                     required=True, maxlength=120),
            h.input_(type="text", name="note", placeholder="One honest sentence",
                     maxlength=300),
            h.input_(type="hidden", name="lane", value="queued"),
            h.button("Queue it", class_="add"),
            action="/roadmap/items",
            method="post",
            class_="add-form",
        ),
        id="roadmap-board",
    )
