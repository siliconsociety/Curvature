"""Poured with the Concierge. The target screen is created inside the
test so the suite stays self-contained wherever it lands."""

import pytest
from app.components.shell import shell
from app.main import app
from fastapi import Request
from fastapi.testclient import TestClient

from curvature import html as h
from curvature import respond


@pytest.fixture(scope="module")
def client():
    @app.get("/laps")
    async def laps(request: Request):
        board = h.section(
            h.form(
                h.input_(type="text", name="title", required=True),
                h.input_(type="hidden", name="status", value="open"),
                h.button("Add lap"),
                action="/laps", method="post",
            ),
            h.a("done laps", href="/laps?status=done"),
            id="lap-board",
        )
        return respond(request, board, shell=shell, purpose="A lap board for tests.")

    return TestClient(app)


def test_the_ask_box_is_a_get_form(client):
    text = client.get("/concierge").text
    assert 'action="/concierge"' in text
    assert 'method="get"' in text  # asking is not a mutation


def test_a_request_becomes_a_prefilled_real_form(client):
    text = client.get("/concierge", params={"q": "add lap bed the brakes", "context": "/laps"}).text
    assert 'action="/laps"' in text and 'method="post"' in text
    assert 'value="bed the brakes"' in text          # remainder became the title
    assert 'name="status" value="open"' in text      # const carried as hidden
    assert "Add lap" in text                          # the human fires it


def test_links_are_drafted_too(client):
    text = client.get("/concierge", params={"q": "show done laps", "context": "/laps"}).text
    assert 'href="/laps?status=done"' in text


def test_no_match_offers_the_atlas(client):
    text = client.get("/concierge", params={"q": "zebra xylophone", "context": "/laps"}).text
    assert "Nothing on this screen matches" in text


def test_unknown_context_degrades_to_root(client):
    response = client.get("/concierge", params={"q": "anything", "context": "no-slash"})
    assert response.status_code == 200


def test_the_concierge_never_executes(client):
    """The whole constitution in one assertion: asking changes nothing."""
    routes_before = len(app.routes)
    client.get("/concierge", params={"q": "add lap sneaky write", "context": "/laps"})
    assert len(app.routes) == routes_before
    # and the concierge's own orbit exposes no mutating routes at all
    concierge_writes = [
        r for r in app.routes
        if getattr(r, "path", "").startswith("/concierge")
        and getattr(r, "methods", set()) - {"GET", "HEAD"}
    ]
    assert concierge_writes == []
