"""The roadmap's store: a JSON file checked into the repo. Single
writer, whole-file rewrites — the honest tier, chosen on purpose: git
is the audit trail, diffs are the changelog, and the markdown this
replaces never had transactions either."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

LANES = ("queued", "pouring", "shipped")


@dataclass
class Item:
    id: str
    title: str
    lane: str
    note: str = ""


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "item"


class RoadmapStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def _read(self) -> list[Item]:
        data = json.loads(self._path.read_text())
        return [Item(**item) for item in data["items"]]

    def _write(self, items: list[Item]) -> None:
        payload = {"items": [asdict(item) for item in items]}
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2) + "\n")
        tmp.replace(self._path)

    def by_lane(self) -> dict[str, list[Item]]:
        lanes: dict[str, list[Item]] = {lane: [] for lane in LANES}
        for item in self._read():
            lanes.setdefault(item.lane, []).append(item)
        return lanes

    def add(self, title: str, note: str, lane: str) -> Item:
        items = self._read()
        base = slugify(title)
        taken = {item.id for item in items}
        slug = base
        counter = 2
        while slug in taken:
            slug = f"{base}-{counter}"
            counter += 1
        item = Item(id=slug, title=title, lane=lane, note=note)
        items.append(item)
        self._write(items)
        return item

    def move(self, item_id: str, direction: str) -> None:
        items = self._read()
        for item in items:
            if item.id != item_id:
                continue
            position = LANES.index(item.lane)
            if direction == "advance" and position < len(LANES) - 1:
                item.lane = LANES[position + 1]
            elif direction == "back" and position > 0:
                item.lane = LANES[position - 1]
        self._write(items)
