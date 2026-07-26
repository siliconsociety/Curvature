"""Native form semantics and observable intent, proven in Chrome."""

from __future__ import annotations

import time
from contextlib import suppress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlparse

import pytest
from playwright.sync_api import Browser, expect

BOOST = Path(__file__).parents[2] / "src/curvature/static/curvature.js"
LIVE = Path(__file__).parents[2] / "src/curvature/static/live.js"


def _page(fragment: str) -> str:
    return (
        "<!doctype html><html><head>"
        '<script src="/curvature.js?v=0.4.3" defer></script></head>'
        f'<body data-boost><main>{fragment}</main></body></html>'
    )


def _forms() -> str:
    return (
        '<section id="panel">'
        '<form id="search" action="/search" method="get">'
        '<input id="search-input" name="q" value="tires">'
        '<button id="search-submit" name="scope" value="all">Find</button></form>'
        '<form id="override" action="/wrong" method="post">'
        '<input name="q" value="brakes">'
        '<button id="override-get" type="submit" formaction="/search" formmethod="get" '
        'name="scope" value="override">Choose</button></form>'
        '<form id="target" action="/search" method="get" target="_blank">'
        '<button id="target-submit" name="scope" value="target">Open</button>'
        '<button id="target-self" formtarget="_self" name="scope" value="self">Reuse</button>'
        "</form>"
        '<form id="pending" action="/pending-fast" method="get">'
        '<button id="slow" formaction="/pending-slow" name="choice" value="slow">Slow</button>'
        '<button id="fast" name="choice" value="fast">Fast</button>'
        '<button id="http-failure" formaction="/http-failure">HTTP failure</button>'
        '<button id="network-failure" formaction="/network-failure">Network failure</button>'
        "</form></section>"
        '<section id="result">idle</section>'
    )


def _focus_fragment(label: str) -> str:
    return (
        '<section id="focus-panel">'
        '<div style="height: 900px"></div>'
        '<form id="focus-form" action="/focus" method="get">'
        '<input id="focus-field" name="q" value="alignment">'
        '<button id="focus-submit">Refresh</button></form>'
        f'<output id="focus-result">{label}</output>'
        '<div style="height: 900px"></div></section>'
    )


class FormProbe(BaseHTTPRequestHandler):
    last_query: dict[str, list[str]] = {}
    last_search_was_boosted = False
    writes = 0

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
        elif parsed.path == "/live.js":
            self._send(LIVE.read_text(), content_type="text/javascript")
        elif parsed.path == "/":
            self._send(_page(_forms()))
        elif parsed.path == "/search":
            type(self).last_query = parse_qs(parsed.query)
            type(self).last_search_was_boosted = boosted
            fragment = '<section id="panel">searched</section>'
            self._send(fragment if boosted else _page(fragment))
        elif parsed.path in {"/pending-fast", "/pending-slow"}:
            time.sleep(0.1 if parsed.path.endswith("fast") else 1.0)
            label = parsed.path.removeprefix("/pending-")
            fragment = f'<section id="result">{label}</section>'
            self._send(fragment if boosted else _page(fragment))
        elif parsed.path == "/http-failure":
            if boosted:
                time.sleep(0.08)
                self._send("boost failed", status=500, content_type="text/plain")
            else:
                time.sleep(0.6)
                self._send(_page(_forms()))
        elif parsed.path == "/network-failure":
            if boosted:
                with suppress(OSError):
                    self.connection.shutdown(2)
                self.connection.close()
            else:
                time.sleep(0.6)
                self._send(_page(_forms()))
        elif parsed.path == "/focus-home":
            self._send(_page(_focus_fragment("before")))
        elif parsed.path == "/focus":
            fragment = _focus_fragment("after")
            self._send(fragment if boosted else _page(fragment))
        elif parsed.path == "/written":
            self._send(_page('<section id="panel">written</section>'))
        else:
            self._send("missing", status=404, content_type="text/plain")

    def do_POST(self):
        type(self).writes += 1
        self.send_response(303)
        self.send_header("Location", "/written")
        self.end_headers()


@pytest.fixture(scope="module")
def form_url():
    server = ThreadingHTTPServer(("127.0.0.1", 0), FormProbe)
    server.daemon_threads = True
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    thread.join(timeout=2)
    server.server_close()


def test_submitter_overrides_post_form_to_boosted_get(page, form_url):
    FormProbe.writes = 0
    page.goto(form_url)
    page.locator("#override-get").click()
    page.wait_for_url(f"{form_url}/search?q=brakes&scope=override")

    assert FormProbe.last_search_was_boosted is True
    assert FormProbe.last_query == {"q": ["brakes"], "scope": ["override"]}
    assert FormProbe.writes == 0


def test_form_values_win_without_submitter_overrides_and_when_submitter_is_null(
    page,
    form_url,
):
    page.goto(form_url)
    page.locator("#search-submit").click()
    page.wait_for_url(f"{form_url}/search?q=tires&scope=all")
    assert FormProbe.last_search_was_boosted is True

    page.goto(form_url)
    page.evaluate("document.querySelector('#search').requestSubmit()")
    page.wait_for_url(f"{form_url}/search?q=tires")
    assert FormProbe.last_query == {"q": ["tires"]}


def test_submitter_target_controls_native_or_boosted_navigation(page, form_url):
    page.goto(form_url)
    with page.context.expect_page() as opened:
        page.locator("#target-submit").click()
    popup = opened.value
    popup.wait_for_load_state()

    assert popup.url == f"{form_url}/search?scope=target"
    assert FormProbe.last_search_was_boosted is False
    popup.close()

    page.locator("#target-self").click()
    page.wait_for_url(f"{form_url}/search?scope=self")
    assert FormProbe.last_search_was_boosted is True


def test_pending_state_belongs_to_the_newest_navigation(page, form_url):
    page.goto(form_url)
    first = page.evaluate("""() => {
      document.querySelector("#slow").click();
      return [
        document.querySelector("#pending").getAttribute("aria-busy"),
        document.querySelector("#pending").hasAttribute("data-curvature-pending"),
        document.querySelector("#slow").hasAttribute("data-curvature-pending"),
      ];
    }""")
    assert first == ["true", True, True]

    second = page.evaluate("""() => {
      document.querySelector("#fast").click();
      return [
        document.querySelector("#slow").hasAttribute("data-curvature-pending"),
        document.querySelector("#fast").hasAttribute("data-curvature-pending"),
      ];
    }""")
    assert second == [False, True]
    page.wait_for_url(f"{form_url}/pending-fast?choice=fast")

    expect(page.locator("#result")).to_have_text("fast")
    expect(page.locator("#pending")).to_have_attribute("aria-busy", "false")
    expect(page.locator("#pending")).not_to_have_attribute("data-curvature-pending", "")
    expect(page.locator("#fast")).not_to_have_attribute("data-curvature-pending", "")
    page.wait_for_timeout(1000)
    expect(page.locator("#result")).to_have_text("fast")


@pytest.mark.parametrize("submitter", ["http-failure", "network-failure"])
def test_pending_state_clears_before_native_failure_fallback(page, form_url, submitter):
    page.goto(form_url)
    pending = page.evaluate("""submitter => {
      document.querySelector(`#${submitter}`).click();
      return document.querySelector("#pending").getAttribute("aria-busy");
    }""", submitter)
    assert pending == "true"
    page.wait_for_url(f"{form_url}/{submitter}")
    expect(page.locator("#pending")).not_to_have_attribute("aria-busy", "true")
    expect(page.locator("#pending")).not_to_have_attribute("data-curvature-pending", "")


def test_identified_swap_restores_focus_without_scrolling(page, form_url):
    page.goto(f"{form_url}/focus-home")
    before = page.evaluate("""() => {
      document.querySelector("#focus-field").focus();
      window.scrollTo(0, 600);
      document.querySelector("#focus-form").requestSubmit(
        document.querySelector("#focus-submit")
      );
      return window.scrollY;
    }""")
    page.wait_for_url(f"{form_url}/focus?q=alignment")

    expect(page.locator("#focus-result")).to_have_text("after")
    assert page.evaluate("document.activeElement.id") == "focus-field"
    assert abs(page.evaluate("window.scrollY") - before) <= 1


def test_submitter_override_remains_native_without_javascript(chrome: Browser, form_url):
    context = chrome.new_context(java_script_enabled=False)
    page = context.new_page()
    page.goto(form_url)
    page.locator("#override-get").click()
    page.wait_for_url(f"{form_url}/search?q=brakes&scope=override")

    assert FormProbe.last_search_was_boosted is False
    assert FormProbe.writes == 0
    context.close()
