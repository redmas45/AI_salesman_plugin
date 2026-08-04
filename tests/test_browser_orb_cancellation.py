"""Orb state machine: cancellation is cancellation, not a connection error.

Reproduced defects (real built bundle, only the network stubbed):

* stopping a turn mid-flight showed "Connection issue" / an error banner, because
  the aborted request's AbortError was classified as a network failure;
* a delayed older response could still render after the customer moved on;
* the idle orb was a filled brand orb, not the approved red mic on white.

Every assertion reads the widget's real state (status text, orb class/attribute,
rendered messages), never Maya's wording.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

import pytest

WIDGET_BUNDLE = Path("plugin/mayabot.js")
SHOP_URL = re.compile(r"https://hub\.example\.test/v1/shop.*")


def _page_html() -> str:
    return """
    <!doctype html>
    <html>
      <head>
        <title>Orb</title>
        <script defer src="https://hub.example.test/mayabot.js?site=orb_demo"></script>
      </head>
      <body><main>Shop</main></body>
    </html>
    """


def _mock_script() -> str:
    return """
    const nativeSetTimeout = window.setTimeout.bind(window);
    window.setTimeout = (cb, delay, ...a) => nativeSetTimeout(cb, delay === 300 ? 3000 : delay, ...a);
    window.__availableVoices = [{ name: 'Samantha', lang: 'en-US', default: true }];
    window.__spoke = 0; window.__cancelled = 0;
    window.SpeechSynthesisUtterance = class { constructor(t){ this.text=t; } };
    Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: {
      speaking: false, pending: false, onvoiceschanged: null,
      getVoices: () => window.__availableVoices,
      cancel(){ window.__cancelled += 1; this.speaking = false; },
      resume(){}, speak(){ window.__spoke += 1; this.speaking = true; },
    }});
    Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: {
      getUserMedia: async () => ({ getTracks: () => [{ stop(){} }] }),
    }});
    window.MediaRecorder = class {
      static isTypeSupported(){ return true; }
      constructor(){ this.state='inactive'; this.ondataavailable=null; this.onstop=null; }
      start(){ this.state='recording'; }
      requestData(){ if (this.ondataavailable) this.ondataavailable({ data: new Blob(['x'.repeat(4000)]) }); }
      stop(){ this.state='inactive'; if (this.onstop) this.onstop(); }
    };
    """


async def _boot(playwright, shop_handler):
    widget_js = WIDGET_BUNDLE.read_text(encoding="utf-8")
    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page()
    page.set_default_timeout(9000)
    await page.add_init_script(_mock_script())

    async def bundle(route):
        await route.fulfill(status=200, content_type="application/javascript", body=widget_js)

    async def status(route):
        await route.fulfill(status=200, content_type="application/json", body='{"enabled":true}')

    async def shell(route):
        await route.fulfill(status=200, content_type="text/html", body=_page_html())

    await page.route("https://shop.example.test/", shell)
    await page.route(re.compile(r"https://hub\.example\.test/mayabot\.js.*"), bundle)
    await page.route(re.compile(r"https://hub\.example\.test/v1/widget/status.*"), status)
    await page.route(re.compile(r"https://hub\.example\.test/v1/widget/runtime-event.*"),
                     lambda r: r.fulfill(status=204, body=""))
    await page.route(SHOP_URL, shop_handler)
    await page.goto("https://shop.example.test/", wait_until="networkidle")
    await page.get_by_text("Welcome to Maya").wait_for()
    return browser, page


async def _record_submit(page):
    orb = page.locator("#mayabot-btn")
    await page.keyboard.press("Escape")
    await page.wait_for_timeout(80)
    await orb.click()          # start recording
    await page.wait_for_timeout(200)
    await orb.click()          # stop -> submit -> processing
    await page.wait_for_timeout(150)


async def _status_text(page):
    return (await page.locator("#mayabot-status").inner_text()).strip()


# --- Idle visual --------------------------------------------------------------


@pytest.mark.asyncio
async def test_idle_orb_is_a_red_mic_on_white_with_no_ripple() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")

    async def ok(route):
        await route.fulfill(status=200, content_type="application/json",
                            body='{"transcript":"hi","response_text":"Hello.","ui_actions":[],"audio_b64":""}')

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright, ok)
        state = await page.evaluate(
            "() => { const b = document.getElementById('mayabot-btn');"
            " const ring = b.querySelector('.mayabot-btn-ring');"
            " const cs = getComputedStyle(b); const rs = ring && getComputedStyle(ring);"
            " return { orb_state: b.getAttribute('data-orb-state'), bg: cs.backgroundColor,"
            "   mic: cs.color, ring_opacity: rs ? Number(rs.opacity) : null,"
            "   recording: b.classList.contains('recording') }; }"
        )
        assert state["orb_state"] == "idle"
        assert state["bg"] == "rgb(255, 255, 255)", state
        assert state["mic"] == "rgb(239, 68, 68)", state  # red microphone
        assert state["recording"] is False
        assert state["ring_opacity"] == 0, "no listening ripple at idle"
        await browser.close()


# --- Cancellation -------------------------------------------------------------


@pytest.mark.asyncio
async def test_stopping_a_processing_turn_is_not_a_connection_error() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")
    served = {"count": 0}

    async def slow(route):
        served["count"] += 1
        await asyncio.sleep(2.0)  # still processing when the customer stops it
        await route.fulfill(status=200, content_type="application/json",
                            body='{"transcript":"hi","response_text":"Late answer.","ui_actions":[],"audio_b64":""}')

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright, slow)
        await _record_submit(page)
        assert await _status_text(page) == "Analyzing..."

        await page.locator("#mayabot-btn").click()   # single click -> stop
        await page.wait_for_timeout(150)
        status = await _status_text(page)
        assert status != "Connection issue", "a user stop must never read as a connection problem"
        assert status == "Ready", status

        # The page stayed mounted and the late answer never overwrites the screen.
        await page.wait_for_timeout(2200)
        assert await page.locator("#mayabot-widget").count() == 1
        assert await _status_text(page) == "Ready"
        rendered = await page.locator("#mayabot-msgs").inner_text()
        assert "Late answer" not in rendered, "a cancelled turn's delayed response must not render"
        await browser.close()


@pytest.mark.asyncio
async def test_a_fresh_turn_works_after_a_cancellation() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")
    state = {"n": 0}

    async def handler(route):
        state["n"] += 1
        if state["n"] == 1:
            await asyncio.sleep(2.0)
            await route.fulfill(status=200, content_type="application/json", body='{"response_text":"one","ui_actions":[]}')
        else:
            await route.fulfill(status=200, content_type="application/json",
                                body='{"transcript":"again","response_text":"Second answer.","ui_actions":[],"audio_b64":""}')

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright, handler)
        await _record_submit(page)
        await page.locator("#mayabot-btn").click()   # cancel the first
        await page.wait_for_timeout(150)
        assert await _status_text(page) == "Ready"

        await _record_submit(page)                   # a brand-new turn
        await page.wait_for_timeout(400)
        rendered = await page.locator("#mayabot-msgs").inner_text()
        assert "Second answer." in rendered, "the widget must accept a new turn after a stop"
        await browser.close()
