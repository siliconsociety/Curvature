"""The one sanctioned script, proven in an actual browser."""

from __future__ import annotations

import time
from contextlib import suppress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlparse

import pytest
from playwright.sync_api import Browser, expect, sync_playwright

BOOST = Path(__file__).parent.parent / "src/curvature/static/curvature.js"


def _page(fragment: str) -> str:
    return (
        "<!doctype html><html><head>"
        '<script src="/curvature.js" defer></script></head>'
        f'<body data-boost><main>{fragment}</main></body></html>'
    )


def _home() -> str:
    return _page(
        '<section id="panel">home'
        '<a id="next" href="/next">Next</a>'
        '<a id="broken" href="/broken">Broken</a>'
        '<a id="slow" href="/slow">Slow</a>'
        '<a id="fast" href="/fast">Fast</a>'
        '<form id="search" action="/search" method="get">'
        '<input name="q" value="tires">'
        '<button name="scope" value="all">Find</button></form>'
        '<form id="write" action="/write" method="post">'
        '<button name="intent" value="save">Save</button></form>'
        "</section>"
    )


class BoostProbe(BaseHTTPRequestHandler):
    last_query: dict[str, list[str]] = {}
    last_write = ""
    last_write_was_boosted = False
    broken_requests: list[bool] = []

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
        if parsed.path == "/curvature.js":
            self._send(BOOST.read_text(), content_type="text/javascript")
        elif parsed.path == "/":
            self._send(_home())
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


@pytest.fixture(scope="module")
def chrome():
    with sync_playwright() as playwright:
        instance = playwright.chromium.launch(channel="chrome", headless=True)
        yield instance
        instance.close()


@pytest.fixture
def page(chrome: Browser):
    context = chrome.new_context()
    current = context.new_page()
    yield current
    context.close()


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
