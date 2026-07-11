"""The boost protocol, server side (C-500, C-501, C-103).

One header decides everything. A boosted request gets the identified
subtrees; a plain request gets the full document wrapped by the shell.
Both come from the same render, so there is nothing to drift.
"""

from __future__ import annotations

from collections.abc import Callable

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from camber.errors import OffCamber
from camber.html import Element, render

BOOST_HEADER = "camber-boost"


def is_boosted(request: Request) -> bool:
    return request.headers.get(BOOST_HEADER) == "1"


def respond(
    request: Request,
    *fragments: Element,
    shell: Callable[..., Element],
    status_code: int = 200,
) -> HTMLResponse:
    """Answer a view with fragments or the full page — same tree either way.

    Every fragment root must carry an id (C-501): the boost layer swaps by
    id, and an anonymous fragment would strand the client. The shell is a
    callable receiving the fragments and returning the full document; it
    runs only for unboosted requests.
    """
    for fragment in fragments:
        if fragment.id is None:
            raise OffCamber(
                f"fragment root <{fragment.tag}> has no id (C-501): the boost "
                "layer swaps subtrees by id; give the root a stable identity"
            )
    headers = {"vary": "Camber-Boost"}
    if is_boosted(request):
        markup = "".join(render(fragment) for fragment in fragments)
        return HTMLResponse(markup, status_code=status_code, headers=headers)
    return HTMLResponse(render(shell(*fragments)), status_code=status_code, headers=headers)


def redirect(url: str, *, status_code: int = 303) -> RedirectResponse:
    """POST -> redirect -> GET (C-201). 303 turns any verb into a GET, which
    is exactly the promise a mutation makes about its after-state."""
    return RedirectResponse(url, status_code=status_code)
