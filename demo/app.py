"""Pit Board — the living roadmap, and the canonical Curvature demo.

One page. The tower streams itself: ship a card from anywhere — the
app, a git pull, an editor — and every open browser updates. Real
paddle forms move items; git keeps the time.

Run it:  uv run uvicorn demo.app:app --reload
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Form, Request
from fastapi.staticfiles import StaticFiles

import curvature
from curvature import redirect, respond
from curvature.atlas import atlas
from curvature.live import live_stream
from demo.components.shell import shell
from demo.components.tower import TowerProps, tower
from demo.roadmap_store import LANES, RoadmapStore

app = FastAPI(title="Pit Board")
app.mount("/static/lib", StaticFiles(directory=Path(curvature.__file__).parent / "static"))
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"))

app.state.roadmap_store = RoadmapStore(Path(__file__).parent / "data" / "roadmap.json")


def _tower_fragment(store: RoadmapStore):
    lanes = store.by_lane()
    return tower(TowerProps(
        on_track=tuple(lanes["pouring"]),
        shipped=tuple(lanes["shipped"]),
        queued=tuple(lanes["queued"]),
    ))


@app.get("/")
async def board(request: Request):
    return respond(
        request, _tower_fragment(request.app.state.roadmap_store), shell=shell,
        purpose="The living roadmap as a timing tower: send a stint OUT, take the "
                "FLAG, or PIT it back; git keeps the time.",
    )


@app.get("/roadmap")
async def old_address():
    return redirect("/")


@app.post("/roadmap/items")
async def plan_item(
    request: Request,
    title: Annotated[str, Form()],
    note: Annotated[str, Form()] = "",
    lane: Annotated[str, Form()] = "queued",
):
    if lane not in LANES:
        lane = "queued"
    request.app.state.roadmap_store.add(title.strip(), note.strip(), lane)
    return redirect("/")


@app.post("/roadmap/items/{item_id}/move")
async def move_item(
    request: Request, item_id: str, direction: Annotated[str, Form()]
):
    if direction in {"advance", "back"}:
        request.app.state.roadmap_store.move(item_id, direction)
    return redirect("/")


async def _tower_events(store: RoadmapStore):
    seen = -1
    while True:
        current = store.version()
        if current != seen:
            seen = current
            yield _tower_fragment(store)
        await asyncio.sleep(0.5)


@app.get("/live")
async def live(request: Request):
    return live_stream(_tower_events(request.app.state.roadmap_store))


@app.get("/atlas")
async def atlas_page(request: Request):
    return respond(
        request, atlas(app), shell=shell,
        purpose="Every readable region of Pit Board; agents fetch each region's chart.",
    )
