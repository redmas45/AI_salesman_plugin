"""Browser regressions for the voice turn transport and lifecycle.

These drive the REAL built bundle and stub only the network, so the actual
`HttpTransport` / `processAudio` code path runs. The previous suites stubbed the
transport object itself, which is why a defect that lives inside the transport
(every non-ok HTTP response collapsing into "Connection issue") survived them.

Reported production defect: recording submits, then the widget shows
"Connection issue" regardless of what actually went wrong.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

WIDGET_BUNDLE = Path("plugin/mayabot.js")
SHOP_URL = re.compile(r"https://hub\.example\.test/v1/shop.*")
DIAGNOSTICS_URL = re.compile(r"https://hub\.example\.test/v1/widget/runtime-event.*")


async def _boot(playwright, *, shop_handler=None, diagnostics_handler=None):
    widget_js = WIDGET_BUNDLE.read_text(encoding="utf-8")
    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page()
    page.set_default_timeout(7000)
    await page.add_init_script(_mock_script())
    await _install_routes(page, widget_js, shop_handler, diagnostics_handler=diagnostics_handler)
    await page.goto("https://shop.example.test/", wait_until="networkidle")
    await page.get_by_text("Welcome to Maya").wait_for()
    return browser, page


async def _record_and_submit(page) -> None:
    """Double-click to record, then a single click to stop and submit."""
    orb = page.locator("#mayabot-btn")
    await orb.dblclick()
    await page.wait_for_timeout(250)
    await orb.click()
    await page.wait_for_timeout(900)


async def _status(page) -> str:
    return await page.locator("#mayabot-status").inner_text()


# --- Error classification: a server fault must not read as a network fault ---


@pytest.mark.asyncio
async def test_backend_502_is_not_reported_as_a_connection_problem() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")

    async def bad_gateway(route) -> None:
        await route.fulfill(
            status=502,
            content_type="application/json",
            body='{"detail":"Upstream provider unavailable"}',
        )

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright, shop_handler=bad_gateway)
        await _record_and_submit(page)
        status = await _status(page)
        assert status != "Connection issue", "a 502 is a server fault, not a connectivity fault"
        assert status.strip()
        await browser.close()


@pytest.mark.asyncio
async def test_quota_429_is_reported_as_a_quota_limit() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")

    async def too_many(route) -> None:
        await route.fulfill(status=429, content_type="application/json", body='{"detail":"Rate limited"}')

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright, shop_handler=too_many)
        await _record_and_submit(page)
        status = (await _status(page)).lower()
        assert "connection" not in status
        assert "busy" in status or "quota" in status or "limit" in status
        await browser.close()


@pytest.mark.asyncio
async def test_payload_too_large_413_is_distinguished() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")

    async def too_large(route) -> None:
        await route.fulfill(status=413, content_type="application/json", body='{"detail":"Payload too large"}')

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright, shop_handler=too_large)
        await _record_and_submit(page)
        status = (await _status(page)).lower()
        assert "connection" not in status
        assert "long" in status or "large" in status
        await browser.close()


@pytest.mark.asyncio
async def test_real_network_failure_is_reported_as_a_connection_problem() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")

    async def dropped(route) -> None:
        await route.abort("failed")

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright, shop_handler=dropped)
        await _record_and_submit(page)
        assert await _status(page) == "Connection issue"
        await browser.close()


@pytest.mark.asyncio
async def test_server_error_never_leaks_internal_detail_to_the_customer() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")

    async def leaky(route) -> None:
        await route.fulfill(
            status=500,
            content_type="application/json",
            body='{"detail":"Traceback (most recent call last): psycopg.OperationalError at 10.0.0.4:5432 token=sk-secret"}',
        )

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright, shop_handler=leaky)
        await _record_and_submit(page)
        body = (await page.locator("#mayabot-widget").inner_text()).lower()
        for leaked in ("traceback", "psycopg", "sk-secret", "10.0.0.4"):
            assert leaked not in body, f"internal detail leaked to the customer: {leaked}"
        await browser.close()


@pytest.mark.asyncio
async def test_failure_diagnostic_is_bounded_and_correlated() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")
    events: list[dict] = []

    async def unavailable(route) -> None:
        await route.fulfill(
            status=503,
            headers={
                "X-Request-ID": "req-safe-1",
                "Access-Control-Expose-Headers": "X-Request-ID",
            },
            content_type="application/json",
            body='{"detail":"private provider failure token=secret","code":"provider_down"}',
        )

    async def capture_diagnostic(route) -> None:
        events.append(route.request.post_data_json)
        await route.fulfill(status=200, content_type="application/json", body='{"status":"ok"}')

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(
            playwright,
            shop_handler=unavailable,
            diagnostics_handler=capture_diagnostic,
        )
        await _record_and_submit(page)
        failed = next(event for event in events if event["event_type"] == "voice_turn_failed")
        assert failed["request_id"] == "req-safe-1"
        assert failed["metadata"]["http_status"] == 503
        serialized = str(failed).lower()
        assert "private provider failure" not in serialized
        assert "token=secret" not in serialized
        await browser.close()


# --- Lifecycle: one recording produces at most one backend turn ---------------


@pytest.mark.asyncio
async def test_one_recording_submits_exactly_one_turn() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")
    calls: list[str] = []

    async def ok(route) -> None:
        calls.append(route.request.url)
        await route.fulfill(
            status=200,
            content_type="application/json",
            body='{"transcript":"hello","response_text":"Hi there.","ui_actions":[]}',
        )

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright, shop_handler=ok)
        await _record_and_submit(page)
        assert len(calls) == 1, f"expected exactly one backend turn, got {len(calls)}"
        await browser.close()


@pytest.mark.asyncio
async def test_extra_click_during_submission_does_not_submit_twice() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")
    calls: list[str] = []

    async def slow_ok(route) -> None:
        calls.append(route.request.url)
        await route.fulfill(
            status=200,
            content_type="application/json",
            body='{"transcript":"hello","response_text":"Hi there.","ui_actions":[]}',
        )

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright, shop_handler=slow_ok)
        orb = page.locator("#mayabot-btn")
        await orb.dblclick()
        await page.wait_for_timeout(250)
        # Stop + submit, then immediately click again (the tail of a double click).
        await orb.click()
        await orb.click(force=True)
        await page.wait_for_timeout(900)
        assert len(calls) == 1, f"a trailing click must not submit again, got {len(calls)}"
        await browser.close()


@pytest.mark.asyncio
async def test_escape_while_recording_cancels_without_submitting() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")
    calls: list[str] = []

    async def ok(route) -> None:
        calls.append(route.request.url)
        await route.fulfill(status=200, content_type="application/json", body='{"response_text":"x"}')

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright, shop_handler=ok)
        await page.locator("#mayabot-btn").dblclick()
        await page.wait_for_timeout(250)
        assert await _status(page) == "Listening..."
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(700)
        assert calls == [], "Escape must discard the recording without submitting"
        assert await _status(page) != "Listening..."
        await browser.close()


@pytest.mark.asyncio
async def test_orb_state_copy_updates_for_each_state() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")

    async def ok(route) -> None:
        await route.fulfill(status=200, content_type="application/json", body='{"response_text":"x"}')

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright, shop_handler=ok)
        orb = page.locator("#mayabot-btn")

        idle_label = (await orb.get_attribute("aria-label") or "").lower()
        assert "double" in idle_label

        await orb.dblclick()
        await page.wait_for_timeout(250)
        recording_label = (await orb.get_attribute("aria-label") or "").lower()
        assert "escape" in recording_label or "cancel" in recording_label
        assert recording_label != idle_label
        await browser.close()


@pytest.mark.asyncio
async def test_websocket_done_settles_processing_without_waiting_for_timeout() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot_websocket(playwright, terminal="done")
        await _record_and_submit(page)
        assert await _status(page) == "Ready"
        assert await page.locator("#mayabot-btn").is_enabled()
        assert await page.evaluate("window.__wsAudioEndCount") == 1
        await browser.close()


@pytest.mark.asyncio
async def test_websocket_close_fails_and_settles_active_turn_once() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot_websocket(playwright, terminal="close")
        await _record_and_submit(page)
        assert await _status(page) == "Connection issue"
        assert await page.locator("#mayabot-btn").is_enabled()
        assert await page.evaluate("window.__wsAudioEndCount") == 1
        await browser.close()


async def _boot_websocket(playwright, *, terminal: str):
    widget_js = WIDGET_BUNDLE.read_text(encoding="utf-8")
    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page()
    page.set_default_timeout(7000)
    await page.add_init_script(_mock_script() + _mock_websocket_script(terminal))
    await _install_routes(page, widget_js, None, use_websocket=True)
    await page.goto("https://shop.example.test/", wait_until="networkidle")
    await page.get_by_text("Welcome to Maya").wait_for()
    return browser, page


async def _install_routes(
    page,
    widget_js: str,
    shop_handler,
    *,
    use_websocket: bool = False,
    diagnostics_handler=None,
) -> None:
    async def bundle(route) -> None:
        await route.fulfill(status=200, content_type="application/javascript", body=widget_js)

    async def status(route) -> None:
        await route.fulfill(status=200, content_type="application/json", body='{"enabled":true}')

    page_html = _page_html(use_websocket=use_websocket)

    async def shell(route) -> None:
        await route.fulfill(status=200, content_type="text/html", body=page_html)

    await page.route("https://shop.example.test/", shell)
    await page.route(re.compile(r"https://hub\.example\.test/mayabot\.js.*"), bundle)
    await page.route(re.compile(r"https://hub\.example\.test/v1/widget/status.*"), status)
    if diagnostics_handler is not None:
        await page.route(DIAGNOSTICS_URL, diagnostics_handler)
    if shop_handler is not None:
        await page.route(SHOP_URL, shop_handler)


def _page_html(*, use_websocket: bool = False) -> str:
    websocket_attribute = ' data-use-websocket="true"' if use_websocket else ""
    return f"""
    <!doctype html>
    <html>
      <head>
        <title>Voice transport smoke</title>
        <script defer src="https://hub.example.test/mayabot.js?site=transport_demo"{websocket_attribute}></script>
      </head>
      <body><main>Shop</main></body>
    </html>
    """


def _mock_websocket_script(terminal: str) -> str:
    return f"""
    window.__wsAudioEndCount = 0;
    window.WebSocket = class {{
      static OPEN = 1;
      static CLOSED = 3;
      constructor() {{
        this.readyState = 0;
        window.setTimeout(() => {{
          this.readyState = 1;
          this.onopen?.();
        }}, 0);
      }}
      send(raw) {{
        const message = JSON.parse(raw);
        if (message.type !== "audio_end") return;
        window.__wsAudioEndCount += 1;
        window.setTimeout(() => {{
          if ({terminal!r} === "done") {{
            this.onmessage?.({{ data: JSON.stringify({{ type: "done", response_text: "Done", ui_actions: [] }}) }});
          }} else {{
            this.readyState = 3;
            this.onclose?.();
          }}
        }}, 20);
      }}
      close() {{
        this.readyState = 3;
        this.onclose?.();
      }}
    }};
    """


def _mock_script() -> str:
    return """
    const nativeSetTimeout = window.setTimeout.bind(window);
    window.setTimeout = (callback, delay, ...args) =>
      nativeSetTimeout(callback, delay === 300 ? 3000 : delay, ...args);
    window.__availableVoices = [];
    window.__speechSpeakCount = 0;
    window.__speechCancelCount = 0;
    window.__mediaRequestCount = 0;
    window.SpeechSynthesisUtterance = class { constructor(text) { this.text = text; } };
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
        if (this.ondataavailable) this.ondataavailable({ data: new Blob(["x".repeat(4000)]) });
        if (this.onstop) this.onstop();
      }
      static isTypeSupported() { return true; }
    };
    """
