"""Pit Board — the living roadmap, and the canonical Curvature demo.

One page. The tower streams itself: change a card through git or an
editor and every open browser updates. Git keeps the time.

Run it:  uv run uvicorn demo.app:app --reload --timeout-graceful-shutdown 1
(the flag matters: Live holds connections open, and graceful shutdown
waits for them — without it, every reload hangs)
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

import curvature
from curvature import redirect, respond
from curvature.atlas import atlas
from curvature.live import live_stream
from demo.components.shell import shell
from demo.components.tower import TowerProps, tower
from demo.roadmap_store import RoadmapStore

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
        purpose="The living Curvature roadmap: current work, what comes next, "
                "and recently shipped changes, reflected live from git.",
    )


@app.get("/roadmap")
async def old_address():
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
        request, atlas(app, exclude=("/live",)), shell=shell,
        purpose="Every readable region of Pit Board; agents fetch each region's chart.",
    )
