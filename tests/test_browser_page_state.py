"""Browser regressions for page state, action truth, and session reset.

These drive the REAL built `plugin/mayabot.js` and stub only the network, so the
production `readPageState`, `verifyPostcondition`, `confirmedResponseText`, and
session-reset code paths actually execute.

Reproduced defects:

* the turn carried no description of the screen, so a question about "these
  results" had nothing to be answered from;
* a browser action that returned successfully but changed nothing on screen was
  still narrated as done;
* signing out of the host site left the conversation, the referenced records, and
  the session identity in place for the next person on the same browser.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

WIDGET_BUNDLE = Path("plugin/mayabot.js")
SHOP_URL = re.compile(r"https://hub\.example\.test/v1/shop.*")

HOST_STORAGE_KEY = "store:cart-draft"
HOST_STORAGE_VALUE = "two-items"


def _page_html() -> str:
    """A listing page whose rows carry stable ids, plus host-owned storage."""
    return f"""
    <!doctype html>
    <html>
      <head>
        <title>Listing</title>
        <script defer src="https://hub.example.test/mayabot.js?site=state_demo"></script>
      </head>
      <body>
        <main>
          <div class="row" data-product-id="p1" data-entity-type="product">
            <h3>Aster Kurta</h3>
            <span class="price">499</span>
            <a href="/products/p1">open</a>
          </div>
          <div class="row" data-product-id="p2" data-entity-type="product">
            <h3>Borel Bottle</h3>
            <span class="price">199</span>
            <a href="/products/p2">open</a>
          </div>
          <span data-cart-count="0" id="cart-count">0</span>
        </main>
        <script>
          window.localStorage.setItem({HOST_STORAGE_KEY!r}, {HOST_STORAGE_VALUE!r});
          window.localStorage.setItem("mayabot:leftover", "stale");
        </script>
      </body>
    </html>
    """


def _mock_script() -> str:
    return """
    const nativeSetTimeout = window.setTimeout.bind(window);
    window.setTimeout = (callback, delay, ...args) =>
      nativeSetTimeout(callback, delay === 300 ? 3000 : delay === 2400 ? 24000 : delay, ...args);
    window.__availableVoices = [];
    window.SpeechSynthesisUtterance = class { constructor(text) { this.text = text; } };
    Object.defineProperty(window, "speechSynthesis", {
      configurable: true,
      value: {
        speaking: false, pending: false, onvoiceschanged: null,
        getVoices: () => window.__availableVoices,
        cancel() { this.speaking = false; },
        resume: () => {},
        speak() { this.speaking = true; },
      },
    });
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: async () => ({ getTracks: () => [{ stop() {} }] }) },
    });
    window.MediaRecorder = class {
      static isTypeSupported() { return true; }
      constructor() { this.state = "inactive"; this.ondataavailable = null; this.onstop = null; }
      start() { this.state = "recording"; }
      stop() {
        this.state = "inactive";
        if (this.ondataavailable) this.ondataavailable({ data: new Blob(["x".repeat(4000)]) });
        if (this.onstop) this.onstop();
      }
    };
    // The widget clears the transcript on a timer, so what Maya said is recorded
    // as it is rendered rather than read afterwards.
    window.__mayaSaid = [];
    const recordRenderedText = (records) => {
      for (const record of records) {
        for (const node of record.addedNodes) {
          if (node.nodeType === 1) window.__mayaSaid.push(node.innerText || node.textContent || "");
        }
      }
    };
    const installRenderRecorder = () => {
      if (!document.documentElement) {
        nativeSetTimeout(installRenderRecorder, 5);
        return;
      }
      new MutationObserver(recordRenderedText).observe(document.documentElement, {
        childList: true,
        subtree: true,
      });
    };
    installRenderRecorder();
    """


async def _spoken_text(page) -> str:
    return "\n".join(await page.evaluate("window.__mayaSaid || []"))


async def _boot(playwright, shop_handler):
    widget_js = WIDGET_BUNDLE.read_text(encoding="utf-8")
    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page()
    page.set_default_timeout(9000)
    await page.add_init_script(_mock_script())

    async def bundle(route) -> None:
        await route.fulfill(status=200, content_type="application/javascript", body=widget_js)

    async def status(route) -> None:
        await route.fulfill(status=200, content_type="application/json", body='{"enabled":true}')

    async def shell(route) -> None:
        await route.fulfill(status=200, content_type="text/html", body=_page_html())

    await page.route("https://shop.example.test/", shell)
    await page.route(re.compile(r"https://hub\.example\.test/mayabot\.js.*"), bundle)
    await page.route(re.compile(r"https://hub\.example\.test/v1/widget/status.*"), status)
    await page.route(re.compile(r"https://hub\.example\.test/v1/widget/runtime-event.*"),
                     lambda route: route.fulfill(status=204, body=""))
    await page.route(SHOP_URL, shop_handler)
    await page.goto("https://shop.example.test/", wait_until="networkidle")
    await page.get_by_text("Welcome to Maya").wait_for()
    return browser, page


async def _record_and_submit(page) -> None:
    orb = page.locator("#mayabot-btn")
    await page.keyboard.press("Escape")
    await page.wait_for_timeout(100)
    await orb.click()
    await page.wait_for_timeout(250)
    await orb.click()
    await page.wait_for_timeout(1600)


def _page_context_from(post_data: str) -> dict:
    """Pull the page_context part out of the multipart turn body."""
    marker = 'name="page_context"'
    index = post_data.find(marker)
    assert index != -1, "the turn must carry a page context"
    body = post_data[index + len(marker):]
    start = body.find("{")
    end = body.rfind("}", 0, body.find("------"))
    return json.loads(body[start : end + 1])


# --- The screen travels with the turn ---------------------------------------


@pytest.mark.asyncio
async def test_turn_carries_the_records_currently_visible_on_screen() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")
    captured: list[str] = []

    async def capture(route) -> None:
        captured.append(route.request.post_data or "")
        await route.fulfill(
            status=200,
            content_type="application/json",
            body='{"transcript":"hi","response_text":"Sure.","ui_actions":[],"audio_b64":""}',
        )

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright, capture)
        await _record_and_submit(page)
        assert captured, "the turn was never submitted"
        context = _page_context_from(captured[0])
        entities = context.get("visible_entities") or []
        assert [entity["id"] for entity in entities] == ["p1", "p2"]
        assert entities[0]["entity_type"] == "product"
        assert entities[0]["label"] == "Aster Kurta"
        assert entities[0]["facts"].get("price") == "499"
        assert context["route"]["path"] == "/"
        await browser.close()


@pytest.mark.asyncio
async def test_hidden_records_are_not_reported_as_visible() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")
    captured: list[str] = []

    async def capture(route) -> None:
        captured.append(route.request.post_data or "")
        await route.fulfill(
            status=200,
            content_type="application/json",
            body='{"transcript":"hi","response_text":"Sure.","ui_actions":[],"audio_b64":""}',
        )

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright, capture)
        await page.evaluate("document.querySelector('[data-product-id=\"p2\"]').style.display = 'none'")
        await _record_and_submit(page)
        entities = _page_context_from(captured[0]).get("visible_entities") or []
        assert [entity["id"] for entity in entities] == ["p1"]
        await browser.close()


@pytest.mark.asyncio
async def test_offscreen_records_are_not_reported_as_visible() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")
    captured: list[str] = []

    async def capture(route) -> None:
        captured.append(route.request.post_data or "")
        await route.fulfill(
            status=200,
            content_type="application/json",
            body='{"transcript":"hi","response_text":"Sure.","ui_actions":[],"audio_b64":""}',
        )

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright, capture)
        await page.evaluate(
            "document.querySelector('[data-product-id=\"p2\"]').style.cssText = "
            "'position:absolute;top:5000px;left:0;width:200px;height:100px'"
        )
        await _record_and_submit(page)
        entities = _page_context_from(captured[0]).get("visible_entities") or []
        assert [entity["id"] for entity in entities] == ["p1"], (
            "a rendered card below the viewport is not one of the products the customer can see"
        )
        await browser.close()


# --- Action truth: a return value is a claim, the page is the evidence -------


@pytest.mark.asyncio
async def test_a_sort_the_page_ignored_is_not_narrated_as_done() -> None:
    """The executor reports success, but nothing on screen changed."""
    playwright_api = pytest.importorskip("playwright.async_api")

    async def sorted_claim(route) -> None:
        await route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "transcript": "sort by price",
                    "response_text": "Sorted by price, showing the cheapest first.",
                    "ui_actions": [{"action": "SORT_PRODUCTS", "params": {"sort_by": "price_asc"}}],
                    "audio_b64": "",
                }
            ),
        )

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright, sorted_claim)
        await _record_and_submit(page)
        await page.wait_for_timeout(1400)
        transcript = await _spoken_text(page)
        assert "Sorted by price" not in transcript, (
            "the visible order never changed, so the sort claim is untrue"
        )
        assert "could not complete" in transcript.lower()
        await browser.close()


@pytest.mark.asyncio
async def test_a_display_action_whose_records_are_visible_keeps_its_wording() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")

    async def show(route) -> None:
        await route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "transcript": "show me those",
                    "response_text": "Here they are.",
                    "ui_actions": [{"action": "SHOW_PRODUCTS", "params": {"product_ids": ["p1"]}}],
                    "audio_b64": "",
                }
            ),
        )

    async def by_ids(route) -> None:
        await route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps([{"id": "p1", "name": "Aster Kurta", "price": 499, "brand": "Aster"}]),
        )

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright, show)
        await page.route(re.compile(r"https://hub\.example\.test/v1/products/by-ids.*"), by_ids)
        await _record_and_submit(page)
        await page.wait_for_timeout(1400)
        transcript = await _spoken_text(page)
        assert "Here they are." in transcript, (
            "p1 is on screen, so the display postcondition holds and the wording stands"
        )
        await browser.close()


@pytest.mark.asyncio
async def test_wrong_navigation_destination_is_not_narrated_as_success() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")

    async def navigate(route) -> None:
        await route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "transcript": "take me to Fashion Women",
                    "response_text": "I opened Fashion Women.",
                    "ui_actions": [{"action": "NAVIGATE_TO", "params": {"page": "/fashion-women"}}],
                    "audio_b64": "",
                }
            ),
        )

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright, navigate)
        await page.evaluate(
            """
            window.AIHubAdapterRuntime = {
              lastActionResult: null,
              config: { adapter: { routes: {} } },
              async executeAction() {
                history.pushState({}, '', '/wrong-section');
                this.lastActionResult = { handled: true, status: 'ok', stage: 'test-adapter' };
                return true;
              },
            };
            """
        )
        await _record_and_submit(page)
        transcript = await _spoken_text(page)
        assert "I opened Fashion Women" not in transcript
        assert "could not complete" in transcript.lower()
        await browser.close()


@pytest.mark.asyncio
async def test_wrong_filter_value_is_not_narrated_as_success() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")

    async def filter_products(route) -> None:
        await route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "transcript": "show Fashion Women",
                    "response_text": "I filtered the page to Fashion Women.",
                    "ui_actions": [
                        {"action": "FILTER_PRODUCTS", "params": {"filters": {"category": "women"}}}
                    ],
                    "audio_b64": "",
                }
            ),
        )

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright, filter_products)
        await page.evaluate(
            """
            window.AIHubAdapterRuntime = {
              lastActionResult: null,
              config: { adapter: { routes: {} } },
              async executeAction() {
                history.pushState({}, '', '/?category=men');
                this.lastActionResult = { handled: true, status: 'ok', stage: 'test-adapter' };
                return true;
              },
            };
            """
        )
        await _record_and_submit(page)
        transcript = await _spoken_text(page)
        assert "I filtered the page to Fashion Women" not in transcript
        assert "could not complete" in transcript.lower()
        await browser.close()


# --- Session reset ----------------------------------------------------------


@pytest.mark.asyncio
async def test_logout_clears_hub_state_and_leaves_host_storage_untouched() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")

    async def answer(route) -> None:
        await route.fulfill(
            status=200,
            content_type="application/json",
            body='{"transcript":"my budget is 5000","response_text":"Noted.","ui_actions":[],"audio_b64":""}',
        )

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright, answer)
        await _record_and_submit(page)
        await page.wait_for_timeout(600)

        assert await page.evaluate("typeof window.AIHub?.resetSession") == "function", (
            "the host needs an explicit reset entry point"
        )
        before = await page.evaluate(
            "Object.keys(window.sessionStorage).filter((k) => k.startsWith('mayabot:session:'))[0]"
        )
        previous_session_id = await page.evaluate(f"window.sessionStorage.getItem({before!r})")

        outcome = await page.evaluate("window.AIHub.resetSession()")

        assert outcome["session_id"] and outcome["session_id"] != previous_session_id, (
            "a reset must mint a new identity so the next turn cannot be joined to the old one"
        )
        assert await page.evaluate(f"window.localStorage.getItem({HOST_STORAGE_KEY!r})") == HOST_STORAGE_VALUE, (
            "host website storage is not ours to clear"
        )
        assert await page.evaluate('window.localStorage.getItem("mayabot:leftover")') is None
        assert (await page.locator("#mayabot-msgs").inner_text()).strip() == "", (
            "the previous customer's conversation must not remain on screen"
        )
        await browser.close()


@pytest.mark.asyncio
async def test_reset_does_not_intercept_host_logout_links() -> None:
    """AI Hub resets when the host says so, never by guessing at a link."""
    playwright_api = pytest.importorskip("playwright.async_api")

    async def answer(route) -> None:
        await route.fulfill(
            status=200,
            content_type="application/json",
            body='{"transcript":"hi","response_text":"Hello.","ui_actions":[],"audio_b64":""}',
        )

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright, answer)
        await _record_and_submit(page)
        await page.wait_for_timeout(400)
        session_before = await page.evaluate(
            "window.sessionStorage.getItem(Object.keys(window.sessionStorage)"
            ".find((k) => k.startsWith('mayabot:session:')))"
        )
        await page.evaluate(
            "const a = document.createElement('a');"
            "a.href = '/logout'; a.textContent = 'Log out';"
            # The host owns the navigation; this test only proves AI Hub does not
            # act on the click itself, so the navigation is suppressed.
            "a.addEventListener('click', (event) => event.preventDefault());"
            "document.body.appendChild(a);"
            "a.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));"
        )
        await page.wait_for_timeout(200)
        session_after = await page.evaluate(
            "window.sessionStorage.getItem(Object.keys(window.sessionStorage)"
            ".find((k) => k.startsWith('mayabot:session:')))"
        )
        assert session_after == session_before, "a host link click must not trigger a reset"
        await browser.close()
