"""Browser-level smoke tests for universal form action contracts."""

from __future__ import annotations

import pytest

from agent.adapter_discovery import build_discovery
from tests.test_live_policy_quote_flow import _collector_js


@pytest.mark.asyncio
async def test_browser_result_form_discovers_intent_submit_and_executes_sequence() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")

    async with playwright_api.async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        page.set_default_timeout(5000)
        await page.set_content(
            """
            <html>
              <head><title>Coverage Quote Demo</title></head>
              <body>
                <h1>Compare insurance policy coverage and premium quotes</h1>
                <form id="quote-form" onsubmit="event.preventDefault(); window.__quoteSubmitted = true;">
                  <button type="button" class="pill">Self</button>
                  <button type="button" class="pill">Family</button>
                  <label>Age of eldest member
                    <select name="age">
                      <option value="26">26 years</option>
                      <option value="27">27 years</option>
                    </select>
                  </label>
                  <label>City
                    <input name="city" placeholder="e.g. Mumbai" />
                  </label>
                  <button type="button" class="secondary">Learn more</button>
                  <button data-action="show-quotes">Show Quotes</button>
                </form>
              </body>
            </html>
            """,
            wait_until="load",
        )

        payload = await page.evaluate(_collector_js())
        payload.update(
            {
                "site_id": "synthetic_quote_demo",
                "origin": "https://quote.example.com",
                "url": "https://quote.example.com/",
            }
        )
        discovery = build_discovery(payload).to_dict()
        action = discovery["vertical_config"]["actions"]["START_QUOTE"]

        assert discovery["vertical_key"] == "insurance"
        assert action["submit_mode"] == "submit"
        assert action["steps"][-1] == {"op": "submit", "selector": 'button[data-action="show-quotes"]'}

        await _run_sequence(page, action["steps"], {"age_of_eldest_member": "27", "city": "Mumbai"})

        assert await page.evaluate("window.__quoteSubmitted === true")
        await browser.close()


@pytest.mark.asyncio
async def test_browser_sensitive_quote_form_remains_prepare_only() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")

    async with playwright_api.async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        page.set_default_timeout(5000)
        await page.set_content(
            """
            <html>
              <head><title>Advisor Quote Demo</title></head>
              <body>
                <h1>Request an insurance quote and advisor callback</h1>
                <form id="lead-form" onsubmit="event.preventDefault(); window.__leadSubmitted = true;">
                  <label>Full name <input name="full_name" /></label>
                  <label>Phone <input name="phone" type="tel" /></label>
                  <button data-action="get-quote">Get Quote</button>
                </form>
              </body>
            </html>
            """,
            wait_until="load",
        )

        payload = await page.evaluate(_collector_js())
        payload.update(
            {
                "site_id": "synthetic_sensitive_quote_demo",
                "origin": "https://advisor.example.com",
                "url": "https://advisor.example.com/",
            }
        )
        discovery = build_discovery(payload).to_dict()
        action = discovery["vertical_config"]["actions"]["START_QUOTE"]

        assert discovery["vertical_key"] == "insurance"
        assert action["submit_mode"] == "fill_only"
        assert all(step.get("op") != "submit" for step in action["steps"])

        await _run_sequence(page, action["steps"], {"full_name": "Alex", "phone": "9999999999"})

        assert await page.evaluate("window.__leadSubmitted !== true")
        await browser.close()


async def _run_sequence(page, steps: list[dict], params: dict[str, str]) -> None:
    for step in steps:
        op = step.get("op")
        selector = step.get("selector")
        if op == "select":
            await page.locator(selector).first.select_option(value=params[step["param"]])
        elif op == "fill":
            await page.locator(selector).first.fill(params[step["param"]])
        elif op == "submit":
            await page.locator(selector).first.click()
