"""Pit Board — the canonical Curvature demo.

Three routes, two of them writes. Every write is POST -> redirect -> GET.
The whole app works with JavaScript switched off; curvature.js only makes it
feel like it never left the page.

Run it:  uv run uvicorn demo.app:app --reload
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Form, Request
from fastapi.staticfiles import StaticFiles

import curvature
from curvature import redirect, respond
from demo.components.pit_board import FILTERS, PitBoardProps, pit_board
from demo.components.shell import shell
from demo.store import board

app = FastAPI(title="Pit Board")
app.mount("/static/lib", StaticFiles(directory=Path(curvature.__file__).parent / "static"))
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"))


def clean_status(status: str) -> str:
    return status if status in FILTERS else "all"


@app.get("/")
async def index(request: Request, status: str = "all", editing_task_id: int | None = None):
    status = clean_status(status)
    props = PitBoardProps(
        tasks=tuple(board.visible(status)),
        status=status,
        open_count=len(board.visible("open")),
        done_count=len(board.visible("done")),
        editing_task_id=editing_task_id,
    )
    return respond(request, pit_board(props), shell=shell)


@app.get("/tasks/{task_id}/edit")
async def edit_task(request: Request, task_id: int, status: str = "all"):
    status = clean_status(status)
    if task_id not in board.tasks:
        return redirect(f"/?status={status}")
    return await index(request, status=status, editing_task_id=task_id)


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


@app.post("/tasks/{task_id}/edit")
async def save_task_title(
    task_id: int,
    title: Annotated[str, Form()],
    status: Annotated[str, Form()] = "all",
):
    board.update_title(task_id, title.strip())
    return redirect(f"/?status={clean_status(status)}")
