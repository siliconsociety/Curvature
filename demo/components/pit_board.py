"""The board: create form, filter nav, and the lap list — one fragment
root, so boosted and unboosted requests re-render the same truth."""

from __future__ import annotations

from curvature import Element, Props
from curvature import html as h
from demo.store import Task

FILTERS = ("all", "open", "done")


class PitBoardProps(Props):
    tasks: tuple[Task, ...]
    status: str
    open_count: int
    done_count: int
    editing_task_id: int | None = None


class TaskRowProps(Props):
    task: Task
    status: str
    editing: bool = False


def task_row(props: TaskRowProps) -> Element:
    task = props.task
    if props.editing:
        return h.li(
            h.form(
                h.input_(
                    type="text", name="title", value=task.title,
                    required=True, maxlength=120, autofocus=True,
                ),
                h.input_(type="hidden", name="status", value=props.status),
                h.button("Save", class_="save"),
                h.a("Cancel", href=f"/?status={props.status}", class_="cancel"),
                action=f"/tasks/{task.id}/edit",
                method="post",
                class_="edit-form",
            ),
            class_="lap lap-edit done" if task.done else "lap lap-edit",
        )
    return h.li(
        h.form(
            h.input_(type="hidden", name="status", value=props.status),
            h.button(
                "✓" if task.done else "○",
                class_="lap-toggle",
                aria_label=f"toggle {task.title}",
            ),
            action=f"/tasks/{task.id}/toggle",
            method="post",
            class_="lap-toggle-form",
        ),
        h.span(task.title, class_="lap-title"),
        h.a("Edit", href=f"/tasks/{task.id}/edit?status={props.status}", class_="edit"),
        class_="lap done" if task.done else "lap",
    )


def filter_nav(props: PitBoardProps) -> Element:
    counts = {
        "all": props.open_count + props.done_count,
        "open": props.open_count,
        "done": props.done_count,
    }
    return h.nav(
        (
            h.a(
                f"{name} ({counts[name]})",
                href=f"/?status={name}",
                class_="filter current" if props.status == name else "filter",
            )
            for name in FILTERS
        ),
        class_="filters",
    )


def pit_board(props: PitBoardProps) -> Element:
    return h.section(
        h.form(
            h.input_(
                type="text", name="title", placeholder="Next lap…",
                required=True, maxlength=120, autocomplete="off",
            ),
            h.input_(type="hidden", name="status", value=props.status),
            h.button("Add", class_="add"),
            action="/tasks",
            method="post",
            class_="add-form",
        ),
        filter_nav(props),
        h.ul(
            (
                task_row(TaskRowProps(
                    task=task,
                    status=props.status,
                    editing=task.id == props.editing_task_id,
                ))
                for task in props.tasks
            ),
            class_="laps",
        )
        if props.tasks
        else h.p("Nothing on the board. The stint is yours.", class_="empty"),
        id="pit-board",
    )
