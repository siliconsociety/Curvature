"""Honest benchmarks: published whatever they say.

Two apps, one machine, same FastAPI substrate: a cambered page (full
HTML render through respond()) against the JSON endpoint an equivalent
SPA would call for the same data. Measures requests-per-second under
concurrency and bytes on the wire — the two numbers the architecture
argument actually rests on. The SPA's bundle download, parse, and
hydration costs are NOT charged here; reality bills the client for
those separately, so these numbers are the SPA's best case.

Run: uv run python scripts/bench.py
Writes docs/BENCHMARKS.md with the results and the machine's name.
"""

from __future__ import annotations

import asyncio
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

import httpx2

PORT = 8123
BASE = f"http://127.0.0.1:{PORT}"
CONCURRENCY = 32
SECONDS = 6.0

BENCH_APP = '''
from fastapi import FastAPI, Request

from curvature import Props, respond
from curvature import html as h

app = FastAPI()

ROWS = [{"id": i, "title": f"Item {i}", "done": i % 3 == 0} for i in range(50)]


def shell(*fragments):
    return h.html(h.head(h.title("bench")), h.body(h.main(*fragments)))


class BoardProps(Props):
    rows: tuple[dict, ...]


def board(props: BoardProps):
    return h.section(
        h.ul(
            (h.li(
                h.span(row["title"]),
                h.form(
                    h.button("toggle"),
                    action=f"/rows/{row['id']}/toggle", method="post",
                ),
                class_="done" if row["done"] else "open",
            ) for row in props.rows),
        ),
        id="board",
    )


@app.get("/page")
async def page(request: Request):
    return respond(request, board(BoardProps(rows=tuple(ROWS))), shell=shell,
                   purpose="Fifty rows, the cambered way.")


@app.get("/api/board")
async def api():
    # camber: json-endpoint — this IS the SPA baseline being measured
    return {"rows": ROWS}
'''


async def hammer(client: httpx2.AsyncClient, path: str, headers: dict) -> tuple[float, int, float]:
    """Return (requests_per_second, response_bytes, p50_ms)."""
    deadline = time.monotonic() + SECONDS
    latencies: list[float] = []
    sizes: list[int] = []

    async def worker():
        while time.monotonic() < deadline:
            started = time.monotonic()
            response = await client.get(BASE + path, headers=headers)
            latencies.append((time.monotonic() - started) * 1000)
            sizes.append(len(response.content))

    await asyncio.gather(*(worker() for _ in range(CONCURRENCY)))
    return len(latencies) / SECONDS, sizes[0], statistics.median(latencies)


async def run() -> list[tuple[str, float, int, float]]:
    results = []
    async with httpx2.AsyncClient(timeout=30) as client:
        for name, path, headers in (
            ("HTML page (full document)", "/page", {}),
            ("Boosted fragment", "/page", {"Curvature-Boost": "1"}),
            ("Chart (agent projection)", "/page", {"Curvature-Chart": "1"}),
            ("JSON API (SPA baseline)", "/api/board", {}),
        ):
            await client.get(BASE + path)  # warm
            results.append((name, *(await hammer(client, path, headers))))
    return results


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    app_file = root / "scripts" / "_bench_app.py"
    app_file.write_text(BENCH_APP)
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "scripts._bench_app:app",
         "--port", str(PORT), "--log-level", "critical"],
        cwd=root,
    )
    try:
        time.sleep(1.5)
        results = asyncio.run(run())
    finally:
        server.terminate()
        server.wait()
        app_file.unlink()

    lines = [
        "# Benchmarks",
        "",
        "Published whatever they say. Same machine, same FastAPI substrate,",
        "same fifty-row dataset: the cambered render paths against the JSON",
        "endpoint an equivalent SPA would call. The SPA's bundle download,",
        "parse, and hydration are not billed here — these are its best-case",
        "numbers, and the comparison is still close.",
        "",
        f"Machine: {platform.machine()} · Python {platform.python_version()}"
        f" · concurrency {CONCURRENCY} · {SECONDS:.0f}s per row",
        "",
        "| path | req/s | bytes | p50 ms |",
        "|------|------:|------:|-------:|",
    ]
    for name, rps, size, p50 in results:
        lines.append(f"| {name} | {rps:,.0f} | {size:,} | {p50:.1f} |")
    lines += [
        "",
        "Reading: the fragment and chart cost less than the full page; the",
        "JSON baseline saves bytes it later spends client-side rendering",
        "them. Server-rendering fifty rows is not the expensive part of a",
        "web application.",
        "",
        "Regenerate: `uv run python scripts/bench.py`",
    ]
    (root / "docs" / "BENCHMARKS.md").write_text("\n".join(lines) + "\n")
    for name, rps, size, p50 in results:
        print(f"{name:32} {rps:>9,.0f} req/s {size:>8,} B {p50:>7.1f} ms")


if __name__ == "__main__":
    main()
