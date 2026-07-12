"""Live: the boost swap flowing downhill, tested from the server side."""

import asyncio

import pytest

from curvature import Anomaly
from curvature import html as h
from curvature.live import live_stream, sse_event


def test_an_event_is_data_lines_and_a_blank():
    event = sse_event(h.div("lap 3", id="counter"))
    assert event == 'data: <div id="counter">lap 3</div>\n\n'


def test_multiple_fragments_ride_one_event():
    event = sse_event(h.div("a", id="one"), h.span("b", id="two"))
    assert '<div id="one">a</div><span id="two">b</span>' in event
    assert event.endswith("\n\n")


def test_anonymous_fragments_are_refused_downhill_too():
    with pytest.raises(Anomaly, match="C-501"):
        sse_event(h.div("nameless"))


def test_live_stream_speaks_event_stream():
    async def events():
        yield h.div("x", id="only")

    response = live_stream(events())
    assert response.media_type == "text/event-stream"
    assert response.headers["cache-control"] == "no-store"


def test_live_stream_renders_each_yield():
    async def events():
        yield h.div("first", id="tick")
        yield (h.div("second", id="tick"), h.div("extra", id="tock"))

    async def collect():
        response = live_stream(events())
        return [chunk async for chunk in response.body_iterator]

    chunks = asyncio.run(collect())
    assert 'data: <div id="tick">first</div>' in chunks[0]
    assert "tock" in chunks[1]


def test_the_tower_streams_its_state(tmp_path):
    import shutil
    from pathlib import Path

    from demo.app import _tower_events
    from demo.roadmap_store import RoadmapStore

    seed = Path(__file__).parent.parent / "demo" / "data" / "roadmap.json"
    working = tmp_path / "roadmap.json"
    shutil.copy(seed, working)
    store = RoadmapStore(working)

    async def first_event():
        generator = _tower_events(store)
        return await anext(generator)

    fragment = asyncio.run(first_event())
    assert fragment.id == "pit-tower"
    assert fragment.attrs.get("data_live") == "/live"


def test_store_version_tracks_the_file(tmp_path):
    import shutil
    import time
    from pathlib import Path

    from demo.roadmap_store import RoadmapStore

    seed = Path(__file__).parent.parent / "demo" / "data" / "roadmap.json"
    working = tmp_path / "roadmap.json"
    shutil.copy(seed, working)
    store = RoadmapStore(working)
    before = store.version()
    time.sleep(0.01)
    store.add("bump", "", "queued")
    assert store.version() != before
