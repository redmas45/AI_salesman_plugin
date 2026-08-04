"""Comparison placard: ask once whether to speak, one scroll area, real ratings.

Drives a real comparison turn through the built bundle (only the network stubbed)
and asserts the placard behaviour the reviewer required:

* the speak-choice is offered exactly once - "Would you like me to speak all the
  comparison points?";
* "No" leaves the written comparison and speaks nothing;
* "Yes" speaks;
* there is a single scroll area (the grid), no nested scroll trap;
* the shown rating is the real value, never 0/5.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

WIDGET_BUNDLE = Path("plugin/mayabot.js")
SHOP_URL = re.compile(r"https://hub\.example\.test/v1/shop.*")
BY_IDS_URL = re.compile(r"https://hub\.example\.test/v1/products/by-ids.*")

PRODUCTS = [
    {"id": "p1", "name": "Corvi Smartphone X1", "brand": "Corvi", "price": 42999, "currency": "INR",
     "rating": 4.4, "review_count": 120, "image_url": ""},
    {"id": "p2", "name": "Delta Smartphone Lite", "brand": "Delta", "price": 18999, "currency": "INR",
     "rating": 4.1, "review_count": 55, "image_url": ""},
]
COMPARISON = [
    {"product_id": "p1", "facts": [
        {"label": "Price", "value": "₹42,999"}, {"label": "Rating", "value": "4.4 (120 reviews)"},
        {"label": "Availability", "value": "In stock"}]},
    {"product_id": "p2", "facts": [
        {"label": "Price", "value": "₹18,999"}, {"label": "Rating", "value": "4.1 (55 reviews)"},
        {"label": "Availability", "value": "In stock"}]},
]

SHOP_BODY = json.dumps({
    "transcript": "compare them",
    "response_text": "Here is the comparison.",
    "ui_actions": [{"action": "SHOW_COMPARISON", "params": {"product_ids": ["p1", "p2"], "comparison": COMPARISON}}],
    "audio_b64": "",
})


def _page_html() -> str:
    return """
    <!doctype html><html><head><title>Compare</title>
    <script defer src="https://hub.example.test/mayabot.js?site=cmp_demo"></script></head>
    <body><main>Shop</main></body></html>
    """


def _mock_script() -> str:
    return """
    const nativeSetTimeout = window.setTimeout.bind(window);
    window.setTimeout = (cb, delay, ...a) => nativeSetTimeout(cb, delay === 300 ? 3000 : delay === 2400 ? 24000 : delay, ...a);
    window.__availableVoices = [{ name: 'Samantha', lang: 'en-US', default: true }];
    window.__spokenTexts = [];
    window.SpeechSynthesisUtterance = class { constructor(t){ this.text=t; } };
    Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: {
      speaking: false, pending: false, onvoiceschanged: null,
      getVoices: () => window.__availableVoices,
      cancel(){ this.speaking = false; }, resume(){},
      speak(u){ window.__spokenTexts.push(String(u && u.text || '')); this.speaking = true; },
    }});
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


async def _boot(playwright):
    widget_js = WIDGET_BUNDLE.read_text(encoding="utf-8")
    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page()
    page.set_default_timeout(9000)
    await page.add_init_script(_mock_script())

    async def bundle(route):
        await route.fulfill(status=200, content_type="application/javascript", body=widget_js)

    async def shell(route):
        await route.fulfill(status=200, content_type="text/html", body=_page_html())

    await page.route("https://shop.example.test/", shell)
    await page.route(re.compile(r"https://hub\.example\.test/mayabot\.js.*"), bundle)
    await page.route(re.compile(r"https://hub\.example\.test/v1/widget/status.*"),
                     lambda r: r.fulfill(status=200, content_type="application/json", body='{"enabled":true}'))
    await page.route(re.compile(r"https://hub\.example\.test/v1/widget/runtime-event.*"),
                     lambda r: r.fulfill(status=204, body=""))
    await page.route(BY_IDS_URL, lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(PRODUCTS)))
    await page.route(SHOP_URL, lambda r: r.fulfill(status=200, content_type="application/json", body=SHOP_BODY))
    await page.goto("https://shop.example.test/", wait_until="networkidle")
    await page.get_by_text("Welcome to Maya").wait_for()
    return browser, page


async def _run_comparison(page):
    orb = page.locator("#mayabot-btn")
    await page.keyboard.press("Escape")
    await page.wait_for_timeout(80)
    await orb.click()
    await page.wait_for_timeout(200)
    await orb.click()
    await page.wait_for_selector("#mayabot-product-panel.active")
    await page.wait_for_selector("#mayabot-product-panel.ask-speak")


@pytest.mark.asyncio
async def test_comparison_asks_once_and_no_leaves_it_silent() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright)
        await _run_comparison(page)

        prompts = page.locator(".mayabot-compare-speak")
        assert await prompts.count() == 1
        assert "Would you like me to speak all the comparison points?" in (await prompts.inner_text())

        # Ratings are the real values, never 0/5.
        facts_text = await page.locator("#mayabot-product-panel .mayabot-product-grid").inner_text()
        assert "4.4 (120 reviews)" in facts_text and "4.1 (55 reviews)" in facts_text
        assert "0/5" not in facts_text and "0 / 5" not in facts_text

        # A single scroll area: the grid scrolls, the facts do not nest a scroller.
        overflow = await page.evaluate(
            "() => { const f = document.querySelector('.mayabot-product-facts');"
            " return f ? getComputedStyle(f).overflowY : 'none'; }"
        )
        assert overflow in {"visible", "none"}, f"facts must not be an independent scroll area: {overflow}"

        await page.locator(".mayabot-compare-no").click()
        await page.wait_for_timeout(120)
        # "No" must not speak the comparison POINTS (the per-fact detail). Maya's
        # normal turn reply may still have been spoken; that is a different thing.
        spoken = await page.evaluate("() => window.__spokenTexts.join(' || ')")
        assert "42,999" not in spoken and "Rating:" not in spoken, f"No spoke the points: {spoken!r}"
        assert await page.locator("#mayabot-product-panel.ask-speak").count() == 0, "prompt dismissed after choice"
        # Placard remains readable.
        assert await page.locator("#mayabot-product-panel.active").count() == 1
        await browser.close()


@pytest.mark.asyncio
async def test_comparison_yes_speaks_the_points() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright)
        await _run_comparison(page)
        await page.evaluate("() => { window.__spokenTexts = []; }")  # ignore the turn reply
        await page.locator(".mayabot-compare-yes").click()
        await page.wait_for_timeout(150)
        spoken = await page.evaluate("() => window.__spokenTexts.join(' || ')")
        assert "42,999" in spoken and "Rating:" in spoken, f"Yes must speak the points: {spoken!r}"
        assert await page.locator("#mayabot-product-panel.ask-speak").count() == 0
        await browser.close()
