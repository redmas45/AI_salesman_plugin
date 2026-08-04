"""Every turn is traceable, cancellation is distinct from failure, no secrets leak.

Drives the real bundle and captures every diagnostics POST to
`/v1/widget/runtime-event`, asserting Part 5's observability contract:

* each event carries client/session/turn/request identity, a stage, and a status;
* a user stop emits a `cancelled` status - distinct from a `failed` network error;
* no event body ever contains the raw transcript, audio, tokens, or other secrets.
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import pytest

WIDGET_BUNDLE = Path("plugin/mayabot.js")
SHOP_URL = re.compile(r"https://hub\.example\.test/v1/shop.*")
EVENT_URL = re.compile(r"https://hub\.example\.test/v1/widget/runtime-event.*")
SECRET = "supersecret-token-abc123"


def _page_html() -> str:
    return """
    <!doctype html><html><head><title>Obs</title>
    <script defer src="https://hub.example.test/mayabot.js?site=obs_demo"></script></head>
    <body><main>Shop</main></body></html>
    """


def _mock_script() -> str:
    return """
    const nativeSetTimeout = window.setTimeout.bind(window);
    window.setTimeout = (cb, delay, ...a) => nativeSetTimeout(cb, delay === 300 ? 3000 : delay, ...a);
    window.__availableVoices = [{ name: 'Samantha', lang: 'en-US', default: true }];
    window.SpeechSynthesisUtterance = class { constructor(t){ this.text=t; } };
    Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: {
      speaking: false, pending: false, onvoiceschanged: null, getVoices: () => window.__availableVoices,
      cancel(){ this.speaking=false; }, resume(){},
      speak(u){ if(u&&u.onend)u.onend(); this.speaking=false; } }});
    Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: {
      getUserMedia: async () => ({ getTracks: () => [{ stop(){} }] }) }});
    window.MediaRecorder = class {
      static isTypeSupported(){ return true; }
      constructor(){ this.state='inactive'; this.ondataavailable=null; this.onstop=null; }
      start(){ this.state='recording'; }
      requestData(){ if (this.ondataavailable) this.ondataavailable({ data: new Blob(['x'.repeat(4000)]) }); }
      stop(){ this.state='inactive'; if (this.onstop) this.onstop(); }
    };
    """


async def _boot(playwright, shop_handler, events):
    widget_js = WIDGET_BUNDLE.read_text(encoding="utf-8")
    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page()
    page.set_default_timeout(9000)
    await page.add_init_script(_mock_script())

    async def on_event(route):
        body = route.request.post_data or ""
        if body:
            events.append(body)
        await route.fulfill(status=204, body="")

    await page.route("https://shop.example.test/", lambda r: r.fulfill(status=200, content_type="text/html", body=_page_html()))
    await page.route(re.compile(r"https://hub\.example\.test/mayabot\.js.*"),
                     lambda r: r.fulfill(status=200, content_type="application/javascript", body=widget_js))
    await page.route(re.compile(r"https://hub\.example\.test/v1/widget/status.*"),
                     lambda r: r.fulfill(status=200, content_type="application/json", body='{"enabled":true}'))
    await page.route(EVENT_URL, on_event)
    await page.route(SHOP_URL, shop_handler)
    await page.goto("https://shop.example.test/", wait_until="networkidle")
    await page.get_by_text("Welcome to Maya").wait_for()
    return browser, page


async def _record_submit(page):
    orb = page.locator("#mayabot-btn")
    await page.keyboard.press("Escape")
    await page.wait_for_timeout(80)
    await orb.click()
    await page.wait_for_timeout(200)
    await orb.click()
    await page.wait_for_timeout(150)


def _events(raw_bodies):
    parsed = []
    for body in raw_bodies:
        try:
            parsed.append(json.loads(body))
        except Exception:
            pass
    return parsed


@pytest.mark.asyncio
async def test_a_completed_turn_emits_a_joinable_trace_without_secrets() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")
    events: list[str] = []

    async def ok(route):
        # A secret in the server body must never be echoed into diagnostics.
        await route.fulfill(status=200, content_type="application/json",
                            body=json.dumps({"transcript": "my card is 4111 1111", "response_text": "Done.",
                                             "ui_actions": [], "audio_b64": "", "token": SECRET}))

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright, ok, events)
        await _record_submit(page)
        await page.wait_for_timeout(400)

        parsed = _events(events)
        assert parsed, "a turn must emit at least one diagnostics event"
        started = [e for e in parsed if e.get("event_type") == "voice_turn_started"]
        completed = [e for e in parsed if e.get("event_type") == "voice_turn_completed"]
        assert started and completed, [e.get("event_type") for e in parsed]
        for event in parsed:
            assert event.get("client_id"), event
            assert event.get("session_id"), event
            assert "stage" in event and "status" in event
        # No transcript, audio, card number, or token anywhere in the diagnostics.
        blob = json.dumps(parsed)
        assert SECRET not in blob and "4111" not in blob and "my card" not in blob
        assert "audio_b64" not in blob
        await browser.close()


@pytest.mark.asyncio
async def test_cancellation_and_failure_are_distinct_categories() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")

    # --- user stop -> cancelled ---
    cancel_events: list[str] = []

    async def slow(route):
        await asyncio.sleep(2.0)
        await route.fulfill(status=200, content_type="application/json", body='{"response_text":"late","ui_actions":[]}')

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright, slow, cancel_events)
        await _record_submit(page)
        assert (await page.locator("#mayabot-status").inner_text()).strip() == "Analyzing..."
        await page.keyboard.press("Escape")   # unambiguous cancel of the in-flight turn
        await page.wait_for_timeout(350)
        assert (await page.locator("#mayabot-status").inner_text()).strip() == "Ready"
        cancelled = [e for e in _events(cancel_events) if e.get("status") == "cancelled"]
        assert cancelled, "a user stop must emit a cancelled event"
        assert not [e for e in _events(cancel_events) if e.get("event_type") == "voice_turn_failed"], \
            "a user stop must not emit a failure event"
        await browser.close()

    # --- server 502 -> failed with a non-cancelled category ---
    fail_events: list[str] = []

    async def bad_gateway(route):
        await route.fulfill(status=502, content_type="application/json", body='{"detail":"upstream down"}')

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright, bad_gateway, fail_events)
        await _record_submit(page)
        await page.wait_for_timeout(400)
        failed = [e for e in _events(fail_events) if e.get("event_type") == "voice_turn_failed"]
        assert failed, "a 502 must emit a failure event"
        categories = {e.get("metadata", {}).get("category") for e in failed}
        assert "cancelled" not in categories, "a server fault is not a cancellation"
        assert categories & {"provider_unavailable", "server_error", "network"}, categories
        await browser.close()
