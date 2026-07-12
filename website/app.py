"""Curvature's website — a manifold, of course.

The roadmap lives here as an app; its data lives in git; its chart is
served to agents. Run it: ./site.sh
"""

from __future__ import annotations

from importlib.metadata import version as package_version
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Form, Request
from fastapi.staticfiles import StaticFiles

import curvature
from curvature import redirect, respond
from curvature.atlas import atlas
from website.components.board import BoardProps, board
from website.components.pages import HomeProps, home, shell
from website.store import LANES, RoadmapStore

app = FastAPI(title="Curvature")
app.mount("/static/lib", StaticFiles(directory=Path(curvature.__file__).parent / "static"))
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"))

app.state.roadmap_store = RoadmapStore(Path(__file__).parent / "data" / "roadmap.json")


@app.get("/")
async def index(request: Request):
    props = HomeProps(version=package_version("curvature"))
    return respond(
        request, home(props), shell=shell,
        purpose="Curvature's front door: what the framework is and the one command "
                "that starts an app.",
    )


@app.get("/roadmap")
async def roadmap(request: Request):
    lanes = {
        lane: tuple(items)
        for lane, items in request.app.state.roadmap_store.by_lane().items()
    }
    return respond(
        request, board(BoardProps(lanes=lanes)), shell=shell,
        purpose="The living roadmap: queue an item, advance it through pouring to "
                "shipped; git is the audit trail.",
    )


@app.post("/roadmap/items")
async def add_item(
    request: Request,
    title: Annotated[str, Form()],
    note: Annotated[str, Form()] = "",
    lane: Annotated[str, Form()] = "queued",
):
    if lane not in LANES:
        lane = "queued"
    request.app.state.roadmap_store.add(title.strip(), note.strip(), lane)
    return redirect("/roadmap")


@app.post("/roadmap/items/{item_id}/move")
async def move_item(
    request: Request, item_id: str, direction: Annotated[str, Form()]
):
    if direction in {"advance", "back"}:
        request.app.state.roadmap_store.move(item_id, direction)
    return redirect("/roadmap")


@app.get("/atlas")
async def atlas_page(request: Request):
    return respond(
        request, atlas(app), shell=shell,
        purpose="Every readable region of this site; agents fetch each region's chart.",
    )
