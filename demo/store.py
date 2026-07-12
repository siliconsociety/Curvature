"""An in-memory store, exactly as boring as a demo deserves."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Task:
    id: int
    title: str
    done: bool = False


@dataclass
class PitBoard:
    tasks: dict[int, Task] = field(default_factory=dict)
    next_id: int = 1
    version: int = 0

    def add(self, title: str) -> Task:
        task = Task(id=self.next_id, title=title)
        self.tasks[task.id] = task
        self.next_id += 1
        self.version += 1
        return task

    def toggle(self, task_id: int) -> None:
        if task_id in self.tasks:
            self.tasks[task_id].done = not self.tasks[task_id].done
            self.version += 1

    def update_title(self, task_id: int, title: str) -> None:
        if task_id in self.tasks:
            self.tasks[task_id].title = title
            self.version += 1

    def visible(self, status: str) -> list[Task]:
        tasks = list(self.tasks.values())
        match status:
            case "open":
                return [t for t in tasks if not t.done]
            case "done":
                return [t for t in tasks if t.done]
            case _:
                return tasks

    def reset(self) -> None:
        self.tasks.clear()
        self.next_id = 1
        self.version = 0


board = PitBoard()
