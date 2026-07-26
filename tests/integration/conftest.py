from __future__ import annotations

import pytest
from playwright.sync_api import Browser, sync_playwright


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
