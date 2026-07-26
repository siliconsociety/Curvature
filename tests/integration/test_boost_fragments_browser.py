"""Fragment navigation stays native unless a cross-page boost owns the swap."""

from __future__ import annotations

from contextlib import suppress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlparse

import pytest
from playwright.sync_api import Browser, expect

BOOST = Path(__file__).parents[2] / "src/curvature/static/curvature.js"


def _page(fragment: str) -> str:
    return (
        "<!doctype html><html><head>"
        '<script src="/curvature.js" defer></script></head>'
        f'<body data-boost><main>{fragment}</main></body></html>'
    )


def _home() -> str:
    return _page(
        '<section id="panel">'
        '<a id="same-id" href="#target%20id">ID target</a>'
        '<a id="same-name" href="#legacy%20target">Named target</a>'
        '<a id="cross-id" href="/fragment-redirect#target%20id">Cross-page ID</a>'
        '<a id="cross-name" href="/fragment-redirect#legacy%20target">Cross-page name</a>'
        '<a id="plain" href="/plain">Plain boost</a>'
        '<div style="height: 1200px"></div>'
        '<h2 id="target id">decoded ID</h2>'
        '<div style="height: 1200px"></div>'
        '<a name="legacy target">legacy name</a>'
        "</section>"
    )


def _fragment_page() -> str:
    return (
        '<section id="panel">fragment page'
        '<div style="height: 1200px"></div>'
        '<h2 id="target id">cross-page target</h2>'
        '<div style="height: 1200px"></div>'
        '<a name="legacy target">cross-page named target</a>'
        "</section>"
    )


class FragmentProbe(BaseHTTPRequestHandler):
    requests: list[tuple[str, bool]] = []

    def log_message(self, _format, *_args):
        pass

    def _send(self, body: str, content_type: str = "text/html"):
        payload = body.encode()
        self.send_response(200)
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
            return
        if parsed.path in {"/", "/fragment-redirect", "/fragment-page", "/plain"}:
            type(self).requests.append((parsed.path, boosted))
        if parsed.path == "/":
            self._send(_home())
        elif parsed.path == "/fragment-redirect":
            self.send_response(302)
            self.send_header("Location", "/fragment-page")
            self.end_headers()
        elif parsed.path == "/fragment-page":
            fragment = _fragment_page()
            self._send(fragment if boosted else _page(fragment))
        elif parsed.path == "/plain":
            fragment = '<section id="panel">plain</section>'
            self._send(fragment if boosted else _page(fragment))
        else:
            self._send("missing", content_type="text/plain")


@pytest.fixture(scope="module")
def fragment_url():
    server = ThreadingHTTPServer(("127.0.0.1", 0), FragmentProbe)
    server.daemon_threads = True
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    thread.join(timeout=2)
    server.server_close()


def test_same_page_fragments_and_history_stay_native(page, fragment_url):
    FragmentProbe.requests = []
    page.goto(fragment_url)
    page.evaluate(
        """document.addEventListener("click", event => {
          if (event.target.id === "same-id") window.sameFragmentPrevented = event.defaultPrevented;
        })"""
    )

    page.locator("#same-id").click()
    page.wait_for_url(f"{fragment_url}/#target%20id")
    expect(page.locator("#target\\ id")).to_be_in_viewport()
    assert page.evaluate("window.sameFragmentPrevented") is False

    page.locator("#same-name").click()
    page.wait_for_url(f"{fragment_url}/#legacy%20target")
    expect(page.locator('a[name="legacy target"]')).to_be_in_viewport()

    page.go_back()
    page.wait_for_url(f"{fragment_url}/#target%20id")
    expect(page.locator("#target\\ id")).to_be_in_viewport()
    page.go_forward()
    page.wait_for_url(f"{fragment_url}/#legacy%20target")
    expect(page.locator('a[name="legacy target"]')).to_be_in_viewport()
    assert FragmentProbe.requests == [("/", False)]


@pytest.mark.parametrize(
    ("link_id", "fragment", "target"),
    [
        ("cross-id", "target%20id", "#target\\ id"),
        ("cross-name", "legacy%20target", 'a[name="legacy target"]'),
    ],
)
def test_cross_page_fragment_survives_boosted_redirect(
    page, fragment_url, link_id, fragment, target
):
    FragmentProbe.requests = []
    page.goto(fragment_url)
    page.locator(f"#{link_id}").click()

    page.wait_for_url(f"{fragment_url}/fragment-page#{fragment}")
    expect(page.locator(target)).to_be_in_viewport()
    assert FragmentProbe.requests == [
        ("/", False),
        ("/fragment-redirect", True),
        ("/fragment-page", True),
    ]


def test_plain_cross_page_link_still_boosts(page, fragment_url):
    FragmentProbe.requests = []
    page.goto(fragment_url)
    page.locator("#plain").click()

    page.wait_for_url(f"{fragment_url}/plain")
    expect(page.locator("#panel")).to_have_text("plain")
    assert FragmentProbe.requests == [("/", False), ("/plain", True)]


def test_javascript_off_keeps_native_fragment_navigation(chrome: Browser, fragment_url):
    FragmentProbe.requests = []
    context = chrome.new_context(java_script_enabled=False)
    page = context.new_page()
    try:
        page.goto(fragment_url)
        page.locator("#same-id").click()
        page.wait_for_url(f"{fragment_url}/#target%20id")
        expect(page.locator("#target\\ id")).to_be_in_viewport()

        page.locator("#cross-id").click()
        page.wait_for_url(f"{fragment_url}/fragment-page#target%20id")
        expect(page.locator("#target\\ id")).to_be_in_viewport()
        assert FragmentProbe.requests == [
            ("/", False),
            ("/fragment-redirect", False),
            ("/fragment-page", False),
        ]
    finally:
        context.close()
