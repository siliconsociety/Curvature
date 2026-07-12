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


def test_the_demo_board_streams_its_state():
    from demo.app import _board_events
    from demo.store import board

    board.reset()
    board.add("Live lap")

    async def first_event():
        generator = _board_events()
        return await anext(generator)

    fragment = asyncio.run(first_event())
    assert fragment.id == "pit-board"
    assert fragment.attrs.get("data_live") == "/live"


def test_the_board_declares_its_stream():
    from demo.components.pit_board import PitBoardProps, pit_board

    fragment = pit_board(PitBoardProps(tasks=(), status="all", open_count=0, done_count=0))
    assert 'data-live="/live"' in str(fragment)


def test_store_versions_bump_on_every_write():
    from demo.store import PitBoard

    board = PitBoard()
    task = board.add("a")
    board.toggle(task.id)
    board.update_title(task.id, "b")
    assert board.version == 3
    board.reset()
    assert board.version == 0
