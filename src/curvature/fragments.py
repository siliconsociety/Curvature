"""The boost protocol, server side (C-500, C-501, C-103).

One header decides everything. A boosted request gets the identified
subtrees; a plain request gets the full document wrapped by the shell.
Both come from the same render, so there is nothing to drift.
"""

from __future__ import annotations

from collections.abc import Callable

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse

from curvature.chart import build_chart
from curvature.errors import Anomaly
from curvature.html import Element, render

BOOST_HEADER = "curvature-boost"
CHART_HEADER = "curvature-chart"
VARY = "Curvature-Boost, Curvature-Chart"


def is_boosted(request: Request) -> bool:
    return request.headers.get(BOOST_HEADER) == "1"


def wants_chart(request: Request) -> bool:
    return request.headers.get(CHART_HEADER) == "1"


def respond(
    request: Request,
    *fragments: Element,
    shell: Callable[..., Element],
    status_code: int = 200,
    purpose: str | None = None,
) -> HTMLResponse | JSONResponse:
    """Answer a view with the page, the fragments, or the chart — one
    tree, three heads (C-103, C-500, C-900).

    Every fragment root must carry an id (C-501): the boost layer swaps by
    id, and an anonymous fragment would strand the client. The shell runs
    only for unboosted page requests. A Curvature-Chart: 1 request gets
    the machine-legible projection of the same tree; HTML responses
    advertise the chart's existence so visiting agents can discover it.
    """
    for fragment in fragments:
        if fragment.id is None:
            raise Anomaly(
                f"fragment root <{fragment.tag}> has no id (C-501): the boost "
                "layer swaps subtrees by id; give the root a stable identity"
            )
    if wants_chart(request):
        chart = build_chart(fragments, url=str(request.url.path), purpose=purpose)
        return JSONResponse(chart, status_code=status_code, headers={"vary": VARY})
    headers = {"vary": VARY, "curvature-chart": "available"}
    if is_boosted(request):
        markup = "".join(render(fragment) for fragment in fragments)
        return HTMLResponse(markup, status_code=status_code, headers=headers)
    return HTMLResponse(render(shell(*fragments)), status_code=status_code, headers=headers)


def redirect(url: str, *, status_code: int = 303) -> RedirectResponse:
    """POST -> redirect -> GET (C-201). 303 turns any verb into a GET, which
    is exactly the promise a mutation makes about its after-state."""
    return RedirectResponse(url, status_code=status_code)
