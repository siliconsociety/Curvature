"""The one sanctioned script, proven in an actual browser."""

from __future__ import annotations

import time
from contextlib import suppress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlparse

import pytest
from playwright.sync_api import expect

from curvature.live import TERMINAL_SIGNAL

BOOST = Path(__file__).parents[2] / "src/curvature/static/curvature.js"
LIVE = Path(__file__).parents[2] / "src/curvature/static/live.js"


def _page(fragment: str, version: str = "0.4.3") -> str:
    return (
        "<!doctype html><html><head>"
        f'<script src="/static/lib/curvature.js?v={version}" defer></script></head>'
        f'<body data-boost><main>{fragment}</main></body></html>'
    )


def _home() -> str:
    return _page(
        '<section id="panel">home'
        '<a id="next" href="/next">Next</a>'
        '<a id="broken" href="/broken">Broken</a>'
        '<a id="slow" href="/slow">Slow</a>'
        '<a id="fast" href="/fast">Fast</a>'
        '<a id="add-live" href="/live-added">Add Live</a>'
        '<form id="search" action="/search" method="get">'
        '<input name="q" value="tires">'
        '<button name="scope" value="all">Find</button></form>'
        '<form id="write" action="/write" method="post">'
        '<button name="intent" value="save">Save</button></form>'
        "</section>"
    )


def _live_home() -> str:
    return _page(
        '<section id="status" data-live="/stream">live '
        '<a id="away" href="/live-away">Away</a></section>'
    )


class BoostProbe(BaseHTTPRequestHandler):
    last_query: dict[str, list[str]] = {}
    last_write = ""
    last_write_was_boosted = False
    broken_requests: list[bool] = []
    terminal_requests = 0
    live_module_requests: list[tuple[str, str | None, str | None]] = []
    navigation_requests: list[tuple[str, bool]] = []

    def log_message(self, _format, *_args):
        pass

    def _send(self, body: str, status: int = 200, content_type: str = "text/html"):
        payload = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        with suppress(BrokenPipeError):
            self.wfile.write(payload)

    def do_GET(self):
        parsed = urlparse(self.path)
        boosted = self.headers.get("Curvature-Boost") == "1"
        if parsed.path == "/static/lib/curvature.js":
            self._send(BOOST.read_text(), content_type="text/javascript")
        elif parsed.path == "/static/lib/live.js":
            type(self).live_module_requests.append((
                parsed.query,
                self.headers.get("Sec-Fetch-Dest"),
                self.headers.get("Referer"),
            ))
            if parsed.query == "v=missing":
                self._send("missing", status=404, content_type="text/plain")
            else:
                if parsed.query == "v=slow":
                    time.sleep(0.25)
                self._send(LIVE.read_text(), content_type="text/javascript")
        elif parsed.path == "/":
            self._send(_home())
        elif parsed.path == "/module-failure-home":
            self._send(_page(
                '<section id="panel">module unavailable '
                '<a id="next" href="/next">Next</a></section>',
                version="missing",
            ))
        elif parsed.path == "/live-race-home":
            self._send(_page(
                '<section id="panel">no live yet '
                '<a id="add-live" href="/live-added">Add Live</a></section>',
                version="slow",
            ))
        elif parsed.path == "/live-home":
            self._send(_live_home())
        elif parsed.path == "/live-added":
            fragment = '<section id="panel" data-live="/added-stream">added</section>'
            self._send(fragment if boosted else _page(fragment))
        elif parsed.path == "/live-away":
            fragment = (
                '<section id="status">away '
                '<a id="return" href="/live-return">Return</a></section>'
            )
            self._send(fragment if boosted else _page(fragment))
        elif parsed.path == "/live-return":
            fragment = '<section id="status" data-live="/stream">returned</section>'
            self._send(fragment if boosted else _page(fragment))
        elif parsed.path == "/terminal-home":
            self._send(_page('<section id="status" data-live="/terminal-stream">waiting</section>'))
        elif parsed.path == "/terminal-stream":
            type(self).terminal_requests += 1
            event = 'data: <section id="status" data-live="/terminal-stream">complete</section>\n\n'
            self._send(f"retry: 25\n\n{event}{TERMINAL_SIGNAL}", content_type="text/event-stream")
        elif parsed.path == "/search":
            type(self).last_query = parse_qs(parsed.query)
            fragment = '<section id="panel">searched</section>'
            self._send(fragment if boosted else _page(fragment))
        elif parsed.path == "/broken":
            type(self).broken_requests.append(boosted)
            if boosted:
                self._send("boost failed", status=500, content_type="text/plain")
            else:
                self._send(_page('<section id="panel">native fallback</section>'))
        elif parsed.path in {"/next", "/slow", "/fast"}:
            type(self).navigation_requests.append((parsed.path, boosted))
            if parsed.path == "/slow" and boosted:
                time.sleep(0.25)
            label = parsed.path.removeprefix("/")
            fragment = f'<section id="panel">{label}</section>'
            self._send(fragment if boosted else _page(fragment))
        elif parsed.path == "/written":
            self._send(_page('<section id="panel">written</section>'))
        else:
            self._send("missing", status=404, content_type="text/plain")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        type(self).last_write = self.rfile.read(length).decode()
        type(self).last_write_was_boosted = self.headers.get("Curvature-Boost") == "1"
        self.send_response(303)
        self.send_header("Location", "/written")
        self.end_headers()


@pytest.fixture(scope="module")
def live_url():
    server = ThreadingHTTPServer(("127.0.0.1", 0), BoostProbe)
    server.daemon_threads = True
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    thread.join(timeout=2)
    server.server_close()


def test_links_and_get_forms_swap_fragments(page, live_url):
    page.goto(live_url)
    page.locator("#next").click()
    page.wait_for_url(f"{live_url}/next")
    expect(page.locator("#panel")).to_have_text("next")

    page.goto(live_url)
    page.locator("#search button").click()
    page.wait_for_url(f"{live_url}/search?q=tires&scope=all")
    expect(page.locator("#panel")).to_have_text("searched")
    assert BoostProbe.last_query == {"q": ["tires"], "scope": ["all"]}


def test_mutating_forms_stay_native(page, live_url):
    page.goto(live_url)
    page.locator("#write button").click()
    page.wait_for_url(f"{live_url}/written")
    expect(page.locator("#panel")).to_have_text("written")
    assert BoostProbe.last_write == "intent=save"
    assert BoostProbe.last_write_was_boosted is False


def test_failed_get_enhancement_falls_back_to_navigation(page, live_url):
    BoostProbe.broken_requests = []
    page.goto(live_url)
    page.locator("#broken").click()
    page.wait_for_url(f"{live_url}/broken")
    expect(page.locator("#panel")).to_have_text("native fallback")
    assert BoostProbe.broken_requests == [True, False]


def test_newer_navigation_wins_response_races(page, live_url):
    page.goto(live_url)
    page.locator("#slow").click()
    page.locator("#fast").click()
    page.wait_for_url(f"{live_url}/fast")
    page.wait_for_timeout(300)
    expect(page.locator("#panel")).to_have_text("fast")


LIVE_SOURCE_PROBE = """(() => {
  window.liveSources = [];
  window.EventSource = class {
    constructor(url) {
      this.url = url;
      this.closed = false;
      this.listeners = {};
      window.liveSources.push(this);
    }
    addEventListener(name, listener) { this.listeners[name] = listener; }
    close() { this.closed = true; }
    message(markup) { this.onmessage({data: markup}); }
    finish() { this.listeners["curvature-end"]({data: "complete"}); }
  };
})()"""


def live_source_state(page):
    return page.evaluate("liveSources.map(source => ({url: source.url, closed: source.closed}))")


def wait_for_live_sources(page, count=1):
    page.wait_for_function(
        "count => window.liveSources?.length === count",
        arg=count,
    )


def test_versioned_entrypoint_loads_versioned_live_module(page, live_url):
    BoostProbe.live_module_requests = []
    page.add_init_script(LIVE_SOURCE_PROBE)
    page.goto(f"{live_url}/live-home")
    wait_for_live_sources(page)

    assert BoostProbe.live_module_requests == [
        (
            "v=0.4.3",
            "script",
            f"{live_url}/static/lib/curvature.js?v=0.4.3",
        )
    ]


def test_swapped_in_live_root_starts_without_duplicate_module_import(page, live_url):
    BoostProbe.live_module_requests = []
    page.add_init_script(LIVE_SOURCE_PROBE)
    page.goto(f"{live_url}/live-race-home")
    page.locator("#add-live").click()
    page.wait_for_url(f"{live_url}/live-added")
    wait_for_live_sources(page)

    assert live_source_state(page) == [{"url": "/added-stream", "closed": False}]
    assert len(BoostProbe.live_module_requests) == 1


def test_live_module_failure_leaves_boosted_navigation_usable(page, live_url):
    BoostProbe.live_module_requests = []
    BoostProbe.navigation_requests = []
    page.goto(f"{live_url}/module-failure-home")
    page.wait_for_timeout(100)

    page.locator("#next").click()
    page.wait_for_url(f"{live_url}/next")
    expect(page.locator("#panel")).to_have_text("next")
    assert BoostProbe.live_module_requests == [
        (
            "v=missing",
            "script",
            f"{live_url}/static/lib/curvature.js?v=missing",
        )
    ]
    assert BoostProbe.navigation_requests == [("/next", True)]


def test_live_swaps_transfer_ownership_without_duplicates(page, live_url):
    page.add_init_script(LIVE_SOURCE_PROBE)
    page.goto(f"{live_url}/live-home")
    wait_for_live_sources(page)

    page.evaluate("""() => {
      liveSources[0].message('<section id="status" data-live="/stream">one</section>');
      liveSources[0].message('<section id="status" data-live="/stream">two</section>');
    }""")

    assert live_source_state(page) == [{"url": "/stream", "closed": False}]
    expect(page.locator("#status")).to_have_text("two")


def test_detached_live_owner_closes_and_returning_starts_fresh(page, live_url):
    page.add_init_script(LIVE_SOURCE_PROBE)
    page.goto(f"{live_url}/live-home")
    wait_for_live_sources(page)
    page.locator("#away").click()
    page.wait_for_url(f"{live_url}/live-away")
    assert live_source_state(page) == [{"url": "/stream", "closed": True}]

    page.locator("#return").click()
    page.wait_for_url(f"{live_url}/live-return")
    assert live_source_state(page) == [
        {"url": "/stream", "closed": True},
        {"url": "/stream", "closed": False},
    ]


def test_changed_live_url_closes_the_old_source(page, live_url):
    page.add_init_script(LIVE_SOURCE_PROBE)
    page.goto(f"{live_url}/live-home")
    wait_for_live_sources(page)
    page.evaluate(
        "liveSources[0].message('<section id=\"status\" data-live=\"/other\">changed</section>')"
    )
    assert live_source_state(page) == [
        {"url": "/stream", "closed": True},
        {"url": "/other", "closed": False},
    ]


def test_terminal_event_closes_without_native_reconnection(page, live_url):
    BoostProbe.terminal_requests = 0
    page.goto(f"{live_url}/terminal-home")
    expect(page.locator("#status")).to_have_text("complete")
    page.wait_for_timeout(250)
    assert BoostProbe.terminal_requests == 1


def test_return_after_terminal_event_starts_fresh(page, live_url):
    page.add_init_script(LIVE_SOURCE_PROBE)
    page.goto(f"{live_url}/live-home")
    wait_for_live_sources(page)
    page.evaluate("liveSources[0].finish()")
    assert live_source_state(page) == [{"url": "/stream", "closed": True}]

    page.locator("#away").click()
    page.locator("#return").click()
    page.wait_for_url(f"{live_url}/live-return")
    assert live_source_state(page)[-1] == {"url": "/stream", "closed": False}
    assert len(live_source_state(page)) == 2
