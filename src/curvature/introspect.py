"""In-process chart reading (C-900 consumed through the ASGI front door).

Server-side tooling can read a screen's chart through the app's ASGI
interface: no network socket and no parallel component API. It remains an
ordinary chart consumer and receives exactly the public projection.
"""

from __future__ import annotations

import json
from typing import Any

from curvature.fragments import CHART_HEADER


async def fetch_chart(app: Any, path: str, query: str = "") -> dict[str, Any] | None:
    """Call the app's own front door with the chart header and return the
    projection, or None for regions that don't answer with one."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query.encode(),
        "headers": [
            (CHART_HEADER.encode(), b"1"),
            (b"host", b"manifold.internal"),
        ],
        "scheme": "http",
        "server": ("manifold.internal", 80),
        "client": ("127.0.0.1", 0),
        "root_path": "",
    }
    status = 0
    body = bytearray()

    async def receive() -> dict[str, Any]:  # pragma: no cover — ASGI
        # requires the callable; a bodyless GET never invokes it
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        nonlocal status
        if message["type"] == "http.response.start":
            status = message["status"]
        elif message["type"] == "http.response.body":
            body.extend(message.get("body", b""))

    await app(scope, receive, send)
    if status != 200:
        return None
    try:
        payload = json.loads(bytes(body))
    except ValueError:
        return None
    return payload if isinstance(payload, dict) and "chart" in payload else None
