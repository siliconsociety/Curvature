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
    for mark in ("ON TRACK", "NEXT UP", "SHIPPED"):
        assert mark in text
    assert "P1" in text                      # shipped items hold positions
    assert 'alt="Pit Board emblem"' in text
    assert '/static/favicon.png' in text


def test_active_then_planned_then_shipped(client):
    text = client.get("/").text
    assert text.index("ON TRACK") < text.index("NEXT UP") < text.index("SHIPPED")


def test_every_lane_is_recent_first(client):
    lanes = app.state.roadmap_store.by_lane()
    assert [item.id for item in lanes["queued"]] == [
        "public-live-playground", "live-production-hardening",
    ]
    assert lanes["shipped"][0].id == "pit-board-roadmap-cleanup"
    assert lanes["shipped"][-1].id == "founding"


def test_new_items_are_recent_first(client):
    store = app.state.roadmap_store
    newest = store.add("Newest", "", "queued")
    assert store.by_lane()["queued"][0].id == newest.id


def test_duplicate_titles_get_distinct_slugs(client):
    store = app.state.roadmap_store
    store.add("Twin", "", "queued")
    store.add("Twin", "", "queued")
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
    assert "LIVE ROADMAP · RECENT FIRST" in text


def test_agents_read_the_tower_through_the_chart(client):
    chart = client.get("/", headers={"Curvature-Chart": "1"}).json()
    assert "roadmap" in chart["purpose"]
    assert chart["affordances"]["forms"] == []
    headings = chart["headings"]
    assert headings.index("ON TRACK") < headings.index("NEXT UP") < headings.index("SHIPPED")


def test_the_boost_layer_is_cache_busted_by_version(client):
    from importlib.metadata import version

    assert f'/static/lib/curvature.js?v={version("curvature")}' in client.get("/").text
