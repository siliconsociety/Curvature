"""The site is a manifold; these tests are its no-JS user — and its
no-eyes user, via the chart."""

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from website.app import app
from website.store import RoadmapStore


@pytest.fixture
def client(tmp_path):
    seed = Path(__file__).parent.parent / "website" / "data" / "roadmap.json"
    working = tmp_path / "roadmap.json"
    shutil.copy(seed, working)
    app.state.roadmap_store = RoadmapStore(working)
    return TestClient(app)


def test_home_speaks_the_pitch(client):
    text = client.get("/").text
    assert "agents maintain" in text
    assert "uvx curvature new app" in text


def test_the_board_renders_all_lanes_from_git_data(client):
    text = client.get("/roadmap").text
    for lane in ("Queued", "Pouring", "Shipped"):
        assert f"<h2>{lane}</h2>" in text
    assert "0.1.0 — the founding" in text
    assert "The website-manifold" in text


def test_queueing_an_item_is_a_real_form_round_trip(client):
    response = client.post(
        "/roadmap/items",
        data={"title": "Test the board", "note": "From the suite", "lane": "queued"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "Test the board" in client.get("/roadmap").text


def test_items_advance_and_retreat_between_lanes(client):
    client.post("/roadmap/items/website-manifold/move", data={"direction": "advance"})
    board = app.state.roadmap_store.by_lane()
    assert any(item.id == "website-manifold" for item in board["shipped"])
    client.post("/roadmap/items/website-manifold/move", data={"direction": "back"})
    board = app.state.roadmap_store.by_lane()
    assert any(item.id == "website-manifold" for item in board["pouring"])


def test_shipped_items_cannot_fall_off_the_edge(client):
    client.post("/roadmap/items/founding/move", data={"direction": "advance"})
    board = app.state.roadmap_store.by_lane()
    assert any(item.id == "founding" for item in board["shipped"])


def test_bogus_directions_change_nothing(client):
    before = json.dumps([i.id for lane in app.state.roadmap_store.by_lane().values() for i in lane])
    client.post("/roadmap/items/founding/move", data={"direction": "sideways"})
    after = json.dumps([i.id for lane in app.state.roadmap_store.by_lane().values() for i in lane])
    assert before == after


def test_duplicate_titles_get_distinct_slugs(client):
    client.post("/roadmap/items", data={"title": "Twin", "lane": "queued"})
    client.post("/roadmap/items", data={"title": "Twin", "lane": "queued"})
    ids = [item.id for item in app.state.roadmap_store.by_lane()["queued"]]
    assert "twin" in ids and "twin-2" in ids


def test_agents_read_the_roadmap_through_the_chart(client):
    chart = client.get("/roadmap", headers={"Curvature-Chart": "1"}).json()
    assert "living roadmap" in chart["purpose"]
    add = next(f for f in chart["affordances"]["forms"] if f["action"] == "/roadmap/items")
    assert add["fields"]["required"] == ["title"]
    move_actions = [f["action"] for f in chart["affordances"]["forms"] if "/move" in f["action"]]
    assert any("website-manifold" in action for action in move_actions)
