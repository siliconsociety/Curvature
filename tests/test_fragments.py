import pytest
from starlette.requests import Request

from curvature import FlatSpot, respond
from curvature import html as h
from curvature.fragments import redirect


def make_request(*, boosted: bool) -> Request:
    headers = [(b"curvature-boost", b"1")] if boosted else []
    return Request({"type": "http", "method": "GET", "headers": headers})


def shell(*fragments):
    return h.html(h.body(h.main(*fragments)))


def test_boosted_request_gets_fragments_only():
    response = respond(make_request(boosted=True), h.div("x", id="panel"), shell=shell)
    assert response.body == b'<div id="panel">x</div>'


def test_unboosted_request_gets_the_full_document():
    response = respond(make_request(boosted=False), h.div("x", id="panel"), shell=shell)
    assert response.body.startswith(b"<!doctype html>")
    assert b'<div id="panel">x</div>' in response.body


def test_multiple_fragments_render_in_order():
    response = respond(
        make_request(boosted=True),
        h.div("a", id="one"),
        h.div("b", id="two"),
        shell=shell,
    )
    assert response.body == b'<div id="one">a</div><div id="two">b</div>'


def test_both_branches_vary_on_the_boost_header():
    for boosted in (True, False):
        response = respond(make_request(boosted=boosted), h.div(id="p"), shell=shell)
        assert response.headers["vary"] == "Curvature-Boost"


def test_fragment_without_id_is_refused():
    with pytest.raises(FlatSpot, match="C-501"):
        respond(make_request(boosted=True), h.div("anonymous"), shell=shell)


def test_redirect_is_303_by_default():
    response = redirect("/tasks")
    assert response.status_code == 303
    assert response.headers["location"] == "/tasks"
