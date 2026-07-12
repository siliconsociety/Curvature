"""The demo's tests are the no-JS user: httpx executes no JavaScript, so
every assertion here is a promise about the degraded path (C-202)."""

import pytest
from fastapi.testclient import TestClient

from curvature import BOOST_HEADER
from demo.app import app
from demo.store import board


@pytest.fixture
def client():
    board.reset()
    return TestClient(app)


def test_index_renders_a_full_document(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.text.startswith("<!doctype html>")
    assert 'id="pit-board"' in response.text


def test_the_create_form_is_a_real_form(client):
    text = client.get("/").text
    assert '<form' in text
    assert 'action="/tasks"' in text
    assert 'method="post"' in text


def test_create_redirects_then_shows_the_task(client):
    response = client.post("/tasks", data={"title": "Bed the brakes"}, follow_redirects=False)
    assert response.status_code == 303
    followed = client.get(response.headers["location"])
    assert "Bed the brakes" in followed.text


def test_toggle_flips_done_state_through_a_real_form(client):
    task = board.add("Scrub tires")
    response = client.post(
        f"/tasks/{task.id}/toggle", data={"status": "all"}, follow_redirects=False
    )
    assert response.status_code == 303
    assert board.tasks[task.id].done is True
    assert 'class="lap done"' in client.get("/").text


def test_filters_narrow_the_board(client):
    board.add("Open one")
    done = board.add("Done one")
    board.toggle(done.id)
    open_view = client.get("/?status=open").text
    assert "Open one" in open_view and "Done one" not in open_view
    done_view = client.get("/?status=done").text
    assert "Done one" in done_view and "Open one" not in done_view


def test_filter_links_are_real_links(client):
    text = client.get("/").text
    for status in ("all", "open", "done"):
        assert f'href="/?status={status}"' in text


def test_edit_link_opens_the_task_in_a_real_form(client):
    task = board.add("Set tire pressures")
    text = client.get(f"/tasks/{task.id}/edit?status=open").text
    assert f'action="/tasks/{task.id}/edit"' in text
    assert 'name="title" value="Set tire pressures"' in text
    assert 'name="status" value="open"' in text
    assert 'href="/?status=open"' in text


def test_save_edit_redirects_and_preserves_the_filter(client):
    task = board.add("Old title")
    response = client.post(
        f"/tasks/{task.id}/edit",
        data={"title": "  New title  ", "status": "done"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/?status=done"
    assert board.tasks[task.id].title == "New title"


def test_cancel_edit_returns_to_the_current_filter(client):
    task = board.add("Leave this alone")
    board.toggle(task.id)
    response = client.get(f"/tasks/{task.id}/edit?status=done")
    assert response.status_code == 200
    assert 'href="/?status=done"' in response.text
    assert board.tasks[task.id].title == "Leave this alone"


def test_unknown_status_falls_back_to_all(client):
    board.add("Visible")
    assert "Visible" in client.get("/?status=nonsense").text


def test_boosted_request_gets_the_fragment_only(client):
    response = client.get("/", headers={BOOST_HEADER: "1"})
    assert response.text.startswith('<section id="pit-board">')
    assert "<!doctype html>" not in response.text
    assert response.headers["vary"] == "Curvature-Boost, Curvature-Chart"


def test_boosted_create_lands_on_a_fragment(client):
    response = client.post(
        "/tasks",
        data={"title": "Fuel calc", "status": "open"},
        headers={BOOST_HEADER: "1"},
    )
    assert response.text.startswith('<section id="pit-board">')
    assert "Fuel calc" in response.text


def test_fragment_and_page_render_the_same_board(client):
    board.add("Same truth")
    fragment = client.get("/", headers={BOOST_HEADER: "1"}).text
    page = client.get("/").text
    assert fragment in page
