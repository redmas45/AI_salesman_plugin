"""Browser regression coverage for interrupting Maya speech from the orb."""

from __future__ import annotations

import re
from pathlib import Path

import pytest


WIDGET_BUNDLE = Path("plugin/mayabot.js")


@pytest.mark.asyncio
async def test_orb_stop_cancels_voice_that_is_waiting_for_browser_voices() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")
    widget_js = WIDGET_BUNDLE.read_text(encoding="utf-8")

    async with playwright_api.async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        page.set_default_timeout(5000)
        await page.add_init_script(_speech_mock_script())
        await _install_routes(page, widget_js)

        await page.goto("https://shop.example.test/", wait_until="networkidle")
        await page.get_by_text("Welcome to Maya").wait_for()
        await page.locator("#mayabot-btn").click()

        await page.evaluate(
            """
            () => {
              window.__availableVoices = [{ name: "Samantha", default: true }];
              const callback = window.speechSynthesis.onvoiceschanged;
              if (callback) callback();
            }
            """
        )
        await page.wait_for_timeout(450)

        assert await page.evaluate("window.__speechSpeakCount") == 0
        assert await page.evaluate("window.__mediaRequestCount") == 0
        assert await page.locator("#mayabot-status").inner_text() == "Ready"
        await browser.close()


async def _install_routes(page, widget_js: str) -> None:
    async def shell(route) -> None:
        await route.fulfill(status=200, content_type="text/html", body=_page_html())

    async def widget(route) -> None:
        await route.fulfill(status=200, content_type="application/javascript", body=widget_js)

    async def status(route) -> None:
        await route.fulfill(status=200, content_type="application/json", body='{"enabled":true}')

    await page.route("https://shop.example.test/", shell)
    await page.route(re.compile(r"https://hub\.example\.test/mayabot\.js.*"), widget)
    await page.route(re.compile(r"https://hub\.example\.test/v1/widget/status.*"), status)


def _page_html() -> str:
    return """
    <!doctype html>
    <html>
      <head>
        <title>Widget voice stop smoke</title>
        <script defer src="https://hub.example.test/mayabot.js?site=voice_stop_demo"></script>
      </head>
      <body><main>Shop</main></body>
    </html>
    """


def _speech_mock_script() -> str:
    return """
    const nativeSetTimeout = window.setTimeout.bind(window);
    window.setTimeout = (callback, delay, ...args) =>
      nativeSetTimeout(callback, delay === 300 ? 3000 : delay, ...args);
    window.__availableVoices = [];
    window.__speechSpeakCount = 0;
    window.__mediaRequestCount = 0;
    window.SpeechSynthesisUtterance = class {
      constructor(text) { this.text = text; }
    };
    Object.defineProperty(window, "speechSynthesis", {
      configurable: true,
      value: {
        speaking: false,
        pending: false,
        onvoiceschanged: null,
        getVoices: () => window.__availableVoices,
        cancel: () => {},
        resume: () => {},
        speak: () => { window.__speechSpeakCount += 1; },
      },
    });
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: async () => {
          window.__mediaRequestCount += 1;
          throw new Error("Recording must not start while stopping speech");
        },
      },
    });
    """
