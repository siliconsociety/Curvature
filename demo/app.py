"""Pit Board — the canonical Camber demo.

Three routes, two of them writes. Every write is POST -> redirect -> GET.
The whole app works with JavaScript switched off; camber.js only makes it
feel like it never left the page.

Run it:  uv run uvicorn demo.app:app --reload
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Form, Request
from fastapi.staticfiles import StaticFiles

import camber
from camber import redirect, respond
from demo.components.pit_board import FILTERS, PitBoardProps, pit_board
from demo.components.shell import shell
from demo.store import board

app = FastAPI(title="Pit Board")
app.mount("/static/lib", StaticFiles(directory=Path(camber.__file__).parent / "static"))
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"))


def clean_status(status: str) -> str:
    return status if status in FILTERS else "all"


@app.get("/")
async def index(request: Request, status: str = "all"):
    status = clean_status(status)
    props = PitBoardProps(
        tasks=tuple(board.visible(status)),
        status=status,
        open_count=len(board.visible("open")),
        done_count=len(board.visible("done")),
    )
    return respond(request, pit_board(props), shell=shell)


@app.post("/tasks")
async def create_task(
    title: Annotated[str, Form()], status: Annotated[str, Form()] = "all"
):
    board.add(title.strip())
    return redirect(f"/?status={clean_status(status)}")


@app.post("/tasks/{task_id}/toggle")
async def toggle_task(task_id: int, status: Annotated[str, Form()] = "all"):
    board.toggle(task_id)
    return redirect(f"/?status={clean_status(status)}")
