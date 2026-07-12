"""The timing tower: the living roadmap, at home in the demo."""

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from demo.app import app
from demo.roadmap_store import RoadmapStore


@pytest.fixture
def client(tmp_path):
    seed = Path(__file__).parent.parent / "demo" / "data" / "roadmap.json"
    working = tmp_path / "roadmap.json"
    shutil.copy(seed, working)
    app.state.roadmap_store = RoadmapStore(working)
    return TestClient(app)


def test_the_tower_reads_like_a_pit_board(client):
    text = client.get("/").text
    for mark in ("PLAN A STINT", "ON TRACK", "SHIPPED", "STINT PLAN"):
        assert mark in text
    assert "P1" in text                      # shipped items hold positions
    assert 'alt="Pit Board timing tower emblem"' in text


def test_the_plan_form_leads_the_board(client):
    text = client.get("/").text
    assert text.index("PLAN A STINT") < text.index("ON TRACK") < text.index("SHIPPED")


def test_paddles_are_real_forms(client):
    text = client.get("/").text
    for label in ("OUT", "PIT"):
        assert f">{label}</button>" in text
    assert 'method="post"' in text


def test_planning_a_stint_round_trips(client):
    response = client.post(
        "/roadmap/items",
        data={"title": "Test the tower", "note": "From the suite", "lane": "queued"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "Test the tower" in client.get("/").text


def test_out_flag_and_pit_move_items(client):
    store = app.state.roadmap_store
    item = store.add("Mover", "", "queued")
    client.post(f"/roadmap/items/{item.id}/move", data={"direction": "advance"})
    assert any(i.id == item.id for i in store.by_lane()["pouring"])
    client.post(f"/roadmap/items/{item.id}/move", data={"direction": "advance"})
    assert any(i.id == item.id for i in store.by_lane()["shipped"])
    client.post(f"/roadmap/items/{item.id}/move", data={"direction": "back"})
    assert any(i.id == item.id for i in store.by_lane()["pouring"])


def test_bogus_directions_change_nothing(client):
    store = app.state.roadmap_store
    before = [i.id for lane in store.by_lane().values() for i in lane]
    client.post("/roadmap/items/founding/move", data={"direction": "sideways"})
    after = [i.id for lane in store.by_lane().values() for i in lane]
    assert before == after


def test_duplicate_titles_get_distinct_slugs(client):
    client.post("/roadmap/items", data={"title": "Twin", "lane": "queued"})
    client.post("/roadmap/items", data={"title": "Twin", "lane": "queued"})
    ids = [item.id for item in app.state.roadmap_store.by_lane()["queued"]]
    assert "twin" in ids and "twin-2" in ids


def test_the_old_address_redirects_home(client):
    response = client.get("/roadmap", follow_redirects=False)
    assert response.status_code == 303


def test_the_page_is_whole_without_js_and_fragment_when_boosted(client):
    page = client.get("/")
    assert page.text.startswith("<!doctype html>")
    assert page.headers["vary"] == "Curvature-Boost, Curvature-Chart"
    fragment = client.get("/", headers={"Curvature-Boost": "1"})
    assert fragment.text.startswith('<section id="pit-tower"')


def test_the_tower_declares_its_stream_and_legend(client):
    app.state.roadmap_store.add("On track fixture", "", "pouring")
    text = client.get("/").text
    assert 'data-live="/live"' in text
    assert "OUT → on track" in text
    assert 'title="Take the flag — mark it shipped"' in text
    assert 'title="Send onto the track — start this work"' in text


def test_agents_read_the_tower_through_the_chart(client):
    chart = client.get("/", headers={"Curvature-Chart": "1"}).json()
    assert "timing tower" in chart["purpose"]
    plan = next(
        f for f in chart["affordances"]["forms"] if f["action"] == "/roadmap/items"
    )
    assert plan["fields"]["required"] == ["title"]
    moves = [f for f in chart["affordances"]["forms"] if "/move" in f["action"]]
    assert moves and all(f["method"] == "post" for f in moves)


def test_the_demo_enrolls_in_offline_replay(client):
    text = client.get("/").text
    assert 'data-offline-cache="/curvature-offline.js"' in text
    worker = client.get("/curvature-offline.js")
    assert worker.status_code == 200
    assert "never a database" in worker.text


def test_the_boost_layer_is_cache_busted_by_version(client):
    from importlib.metadata import version

    assert f'/static/lib/curvature.js?v={version("curvature")}' in client.get("/").text
