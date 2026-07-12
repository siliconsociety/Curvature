"""Live — the boost swap flowing downhill (C-502).

The server pushes rendered fragments over SSE; the boost layer swaps
them by id, exactly as it swaps boosted responses. Same tree, same law
(C-501), one direction more. The app author writes an async generator
that yields Elements when state changes; everything else is this
module's problem.

Live regions are display surfaces. Don't stream a form someone might
be typing into.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from starlette.responses import StreamingResponse

from curvature.errors import Anomaly
from curvature.html import Element, render

SSE_HEADERS = {
    "cache-control": "no-store",
    "x-accel-buffering": "no",  # nginx: do not buffer the stream
}


def sse_event(*fragments: Element) -> str:
    """One server-sent event carrying one or more identified subtrees."""
    for fragment in fragments:
        if fragment.id is None:
            raise Anomaly(
                f"live fragment <{fragment.tag}> has no id (C-501): the boost "
                "layer swaps subtrees by id, downhill included"
            )
    markup = "".join(render(fragment) for fragment in fragments)
    lines = "".join(f"data: {line}\n" for line in markup.splitlines() or [""])
    return f"{lines}\n"


def live_stream(events: AsyncIterator[tuple[Element, ...] | Element]) -> StreamingResponse:
    """Wrap an async generator of Elements into an SSE response."""

    async def body() -> AsyncIterator[str]:
        async for event in events:
            fragments = event if isinstance(event, tuple) else (event,)
            yield sse_event(*fragments)

    return StreamingResponse(body(), media_type="text/event-stream", headers=SSE_HEADERS)
