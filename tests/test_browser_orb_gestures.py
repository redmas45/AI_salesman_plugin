"""Browser regressions for the orb gesture state machine.

A single click must never open the microphone: it either stops Maya or does
nothing. Recording starts only on a deliberate double click, and the two click
events a double click emits must start it exactly once.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

WIDGET_BUNDLE = Path("plugin/mayabot.js")
DOUBLE_CLICK_DELAY_MS = 60


async def _boot(playwright_api, playwright):
    widget_js = WIDGET_BUNDLE.read_text(encoding="utf-8")
    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page()
    page.set_default_timeout(5000)
    await page.add_init_script(_mock_script())
    await _install_routes(page, widget_js)
    await page.goto("https://shop.example.test/", wait_until="networkidle")
    await page.get_by_text("Welcome to Maya").wait_for()
    return browser, page


async def _double_click(page) -> None:
    # A real double click. Two separate locator.click() calls are ~360ms apart in
    # Playwright, which is outside the widget's double-click window by design.
    await page.locator("#mayabot-btn").dblclick()


@pytest.mark.asyncio
async def test_single_click_while_idle_does_not_open_the_microphone() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright_api, playwright)
        await page.evaluate("window.speechSynthesis.cancel()")
        await page.locator("#mayabot-btn").click()
        await page.wait_for_timeout(400)
        assert await page.evaluate("window.__mediaRequestCount") == 0
        await browser.close()


@pytest.mark.asyncio
async def test_double_click_while_idle_requests_the_microphone_once() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright_api, playwright)
        await page.evaluate("window.speechSynthesis.cancel()")
        await _double_click(page)
        await page.wait_for_timeout(400)
        assert await page.evaluate("window.__mediaRequestCount") == 1
        await browser.close()


@pytest.mark.asyncio
async def test_double_click_while_speaking_stops_audio_then_records_once() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        # The greeting is still pending playback, so Maya counts as speaking.
        browser, page = await _boot(playwright_api, playwright)
        await _double_click(page)
        await page.wait_for_timeout(400)
        assert await page.evaluate("window.__speechCancelCount") >= 1
        assert await page.evaluate("window.__mediaRequestCount") == 1
        await browser.close()


@pytest.mark.asyncio
async def test_single_click_while_recording_stops_and_submits_once() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright_api, playwright)
        await page.evaluate("window.speechSynthesis.cancel()")
        await _double_click(page)
        await page.wait_for_timeout(300)
        assert await page.locator("#mayabot-status").inner_text() == "Listening..."

        await page.locator("#mayabot-btn").click()
        await page.wait_for_timeout(400)
        assert await page.locator("#mayabot-status").inner_text() != "Listening..."
        # Stopping must not re-open the microphone.
        assert await page.evaluate("window.__mediaRequestCount") == 1
        await browser.close()


@pytest.mark.asyncio
async def test_escape_cancels_speech_without_recording() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright_api, playwright)
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)
        assert await page.evaluate("window.__speechCancelCount") >= 1
        assert await page.evaluate("window.__mediaRequestCount") == 0
        await browser.close()


async def _install_routes(page, widget_js: str) -> None:
    async def shell(route) -> None:
        await route.fulfill(status=200, content_type="text/html", body=_page_html())

    async def bundle(route) -> None:
        await route.fulfill(status=200, content_type="application/javascript", body=widget_js)

    async def status(route) -> None:
        await route.fulfill(status=200, content_type="application/json", body='{"enabled":true}')

    await page.route("https://shop.example.test/", shell)
    await page.route(re.compile(r"https://hub\.example\.test/mayabot\.js.*"), bundle)
    await page.route(re.compile(r"https://hub\.example\.test/v1/widget/status.*"), status)


def _page_html() -> str:
    return """
    <!doctype html>
    <html>
      <head>
        <title>Orb gesture smoke</title>
        <script defer src="https://hub.example.test/mayabot.js?site=gesture_demo"></script>
      </head>
      <body><main>Shop</main></body>
    </html>
    """


def _mock_script() -> str:
    # speechSynthesis and mediaDevices are read-only accessors, so they must be
    # replaced with defineProperty rather than plain assignment.
    return """
    // Keep the "waiting for browser voices" window open for the whole test so the
    // greeting stays pending (i.e. Maya is still speaking) while gestures are sent.
    const nativeSetTimeout = window.setTimeout.bind(window);
    window.setTimeout = (callback, delay, ...args) =>
      nativeSetTimeout(callback, delay === 300 ? 3000 : delay, ...args);
    window.__availableVoices = [];
    window.__speechSpeakCount = 0;
    window.__speechCancelCount = 0;
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
        cancel() { window.__speechCancelCount += 1; this.speaking = false; },
        resume: () => {},
        speak() { window.__speechSpeakCount += 1; this.speaking = true; },
      },
    });
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: async () => {
          window.__mediaRequestCount += 1;
          return { getTracks: () => [{ stop() {} }] };
        },
      },
    });
    window.MediaRecorder = class {
      constructor() {
        this.state = "inactive";
        this.ondataavailable = null;
        this.onstop = null;
      }
      start() { this.state = "recording"; }
      stop() {
        this.state = "inactive";
        if (this.ondataavailable) this.ondataavailable({ data: new Blob(["x".repeat(400)]) });
        if (this.onstop) this.onstop();
      }
      static isTypeSupported() { return true; }
    };
    """
