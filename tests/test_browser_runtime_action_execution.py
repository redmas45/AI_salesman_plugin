"""Browser runtime execution tests for generated adapter actions."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

import pytest


ADAPTER_BUNDLE = Path("plugin/mayabot-adapter.js")


@pytest.mark.asyncio
async def test_runtime_executes_generated_quote_sequence_and_navigates() -> None:
    """Server-style START_QUOTE actions must execute the discovered browser sequence."""
    playwright_api = pytest.importorskip("playwright.async_api")
    adapter_js = ADAPTER_BUNDLE.read_text(encoding="utf-8")
    runtime_config = _runtime_config(
        {
            "START_QUOTE": {
                "type": "sequence",
                "label": "Show Quotes",
                "submit_mode": "submit",
                "required_fields": ["age_of_eldest_member", "city"],
                "field_schema": [
                    {
                        "param": "age_of_eldest_member",
                        "label": "Age of eldest member",
                        "type": "select",
                        "required": True,
                        "options": [{"label": "27 years", "value": "27"}],
                    },
                    {"param": "city", "label": "City", "type": "text", "required": True},
                ],
                "steps": [
                    {"op": "select", "selector": "select[name='age']", "param": "age_of_eldest_member"},
                    {"op": "fill", "selector": "input[name='city']", "param": "city"},
                    {"op": "submit", "selector": "button[data-action='show-quotes']"},
                ],
            }
        }
    )

    async with playwright_api.async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        page.set_default_timeout(5000)
        await _install_routes(page, adapter_js, runtime_config)

        await page.goto("https://policy.example.test/", wait_until="networkidle")
        await page.evaluate("window.AIHubAdapterRuntime.ready")
        succeeded = await page.evaluate(
            """
            () => window.AIHubAdapterRuntime.executeAction({
              action: "START_QUOTE",
              params: { age_of_eldest_member: "27", city: "Mumbai" }
            })
            """
        )

        await page.wait_for_url("**/insurance/health", wait_until="networkidle", timeout=5000)

        submitted = await page.evaluate("window.__quoteSubmitted")
        assert succeeded is True
        assert submitted == {"age": "27", "city": "Mumbai"}
        assert urlparse(page.url).path == "/insurance/health"
        await browser.close()


@pytest.mark.asyncio
async def test_runtime_navigation_ignores_generated_navigate_to_config() -> None:
    """NAVIGATE_TO must honor the requested page, not a generated generic action config."""
    playwright_api = pytest.importorskip("playwright.async_api")
    adapter_js = ADAPTER_BUNDLE.read_text(encoding="utf-8")
    runtime_config = _runtime_config(
        {
            "NAVIGATE_TO": {
                "type": "navigate",
                "path": "/",
                "source": "flow_discovery",
            }
        }
    )
    runtime_config["adapter"]["routes"] = {
        "home": "/",
        "motor": "/insurance/motor",
    }

    async with playwright_api.async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        page.set_default_timeout(5000)
        await _install_navigation_routes(page, adapter_js, runtime_config)

        await page.goto("https://policy.example.test/current", wait_until="networkidle")
        await page.evaluate("window.AIHubAdapterRuntime.ready")
        succeeded = await page.evaluate(
            """
            () => window.AIHubAdapterRuntime.executeAction({
              action: "NAVIGATE_TO",
              params: { page: "insurance/motor" }
            })
            """
        )

        await page.wait_for_url("**/insurance/motor", wait_until="networkidle", timeout=5000)

        assert succeeded is True
        assert urlparse(page.url).path == "/insurance/motor"
        await browser.close()


@pytest.mark.asyncio
async def test_runtime_filter_products_carries_search_query_to_action_page() -> None:
    """Product listing sync must preserve the requested search term during page navigation."""
    playwright_api = pytest.importorskip("playwright.async_api")
    adapter_js = ADAPTER_BUNDLE.read_text(encoding="utf-8")
    runtime_config = _runtime_config(
        {
            "FILTER_PRODUCTS": {
                "type": "form",
                "page_path": "/shop",
                "input_selector": "input[name='q']",
                "submit_selector": "button[type='submit']",
            }
        }
    )

    async with playwright_api.async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        page.set_default_timeout(5000)
        await _install_product_filter_routes(page, adapter_js, runtime_config)

        await page.goto("https://shop.example.test/", wait_until="networkidle")
        await page.evaluate("window.AIHubAdapterRuntime.ready")
        succeeded = await page.evaluate(
            """
            () => window.AIHubAdapterRuntime.executeAction({
              action: "FILTER_PRODUCTS",
              params: { search_query: "smartwatches" }
            })
            """
        )

        await page.wait_for_url("**/shop?q=smartwatches", wait_until="networkidle", timeout=5000)

        assert succeeded is True
        parsed = urlparse(page.url)
        assert parsed.path == "/shop"
        assert parsed.query == "q=smartwatches"
        await browser.close()


async def _install_routes(page, adapter_js: str, runtime_config: dict) -> None:
    async def home(route) -> None:
        await route.fulfill(status=200, content_type="text/html", body=_quote_page_html())

    async def adapter(route) -> None:
        await route.fulfill(status=200, content_type="application/javascript", body=adapter_js)

    async def config(route) -> None:
        await route.fulfill(status=200, content_type="application/json", body=json.dumps(runtime_config))

    async def ok(route) -> None:
        await route.fulfill(status=200, content_type="application/json", body='{"ok":true}')

    await page.route("https://policy.example.test/", home)
    await page.route(re.compile(r"https://hub\.example\.test/mayabot-adapter\.js\?site=runtime_quote_demo"), adapter)
    await page.route(re.compile(r"https://hub\.example\.test/v1/widget/config.*"), config)
    await page.route(re.compile(r"https://hub\.example\.test/v1/widget/register.*"), ok)
    await page.route(re.compile(r"https://hub\.example\.test/v1/widget/action-event.*"), ok)


async def _install_navigation_routes(page, adapter_js: str, runtime_config: dict) -> None:
    async def shell(route) -> None:
        await route.fulfill(status=200, content_type="text/html", body=_navigation_page_html())

    async def adapter(route) -> None:
        await route.fulfill(status=200, content_type="application/javascript", body=adapter_js)

    async def config(route) -> None:
        await route.fulfill(status=200, content_type="application/json", body=json.dumps(runtime_config))

    async def ok(route) -> None:
        await route.fulfill(status=200, content_type="application/json", body='{"ok":true}')

    await page.route(re.compile(r"https://policy\.example\.test/(?:current|insurance/motor|)$"), shell)
    await page.route(re.compile(r"https://hub\.example\.test/mayabot-adapter\.js\?site=runtime_quote_demo"), adapter)
    await page.route(re.compile(r"https://hub\.example\.test/v1/widget/config.*"), config)
    await page.route(re.compile(r"https://hub\.example\.test/v1/widget/register.*"), ok)
    await page.route(re.compile(r"https://hub\.example\.test/v1/widget/action-event.*"), ok)


async def _install_product_filter_routes(page, adapter_js: str, runtime_config: dict) -> None:
    async def shell(route) -> None:
        await route.fulfill(status=200, content_type="text/html", body=_product_filter_page_html())

    async def adapter(route) -> None:
        await route.fulfill(status=200, content_type="application/javascript", body=adapter_js)

    async def config(route) -> None:
        await route.fulfill(status=200, content_type="application/json", body=json.dumps(runtime_config))

    async def ok(route) -> None:
        await route.fulfill(status=200, content_type="application/json", body='{"ok":true}')

    await page.route(re.compile(r"https://shop\.example\.test/(?:shop.*)?$"), shell)
    await page.route(re.compile(r"https://hub\.example\.test/mayabot-adapter\.js\?site=runtime_quote_demo"), adapter)
    await page.route(re.compile(r"https://hub\.example\.test/v1/widget/config.*"), config)
    await page.route(re.compile(r"https://hub\.example\.test/v1/widget/register.*"), ok)
    await page.route(re.compile(r"https://hub\.example\.test/v1/widget/action-event.*"), ok)


def _runtime_config(actions: dict) -> dict:
    return {
        "site_id": "runtime_quote_demo",
        "enabled": True,
        "vertical": {
            "key": "insurance",
            "label": "Insurance",
            "action_types": ["SHOW_ENTITIES", "START_QUOTE", "HANDOFF_TO_AGENT"],
        },
        "adapter": {
            "routes": {"home": "/", "quote": "/", "plans": "/insurance/health"},
            "actions": actions,
            "selectors": {},
            "action_policy": {"blocked_actions": [], "handoff_actions": []},
        },
    }


def _navigation_page_html() -> str:
    return """
    <!doctype html>
    <html>
      <head>
        <title>Policy Navigation Runtime Smoke</title>
        <script defer src="https://hub.example.test/mayabot-adapter.js?site=runtime_quote_demo"></script>
      </head>
      <body>
        <a href="/insurance/motor">Motor</a>
      </body>
    </html>
    """


def _product_filter_page_html() -> str:
    return """
    <!doctype html>
    <html>
      <head>
        <title>Product Filter Runtime Smoke</title>
        <script defer src="https://hub.example.test/mayabot-adapter.js?site=runtime_quote_demo"></script>
      </head>
      <body>
        <form action="/shop">
          <input name="q" />
          <button type="submit">Search</button>
        </form>
      </body>
    </html>
    """


def _quote_page_html() -> str:
    return """
    <!doctype html>
    <html>
      <head>
        <title>Policy Quote Runtime Smoke</title>
        <script defer src="https://hub.example.test/mayabot-adapter.js?site=runtime_quote_demo"></script>
      </head>
      <body>
        <h1>Compare health insurance quotes</h1>
        <form id="quote-form">
          <label>Age of eldest member
            <select name="age">
              <option value="26">26 years</option>
              <option value="27">27 years</option>
            </select>
          </label>
          <label>City <input name="city" /></label>
          <button type="button">Learn more</button>
          <button data-action="show-quotes">Show Quotes</button>
        </form>
        <script>
          document.getElementById("quote-form").addEventListener("submit", (event) => {
            event.preventDefault();
            window.__quoteSubmitted = {
              age: document.querySelector("select[name='age']").value,
              city: document.querySelector("input[name='city']").value,
            };
            history.pushState({}, "", "/insurance/health");
            window.dispatchEvent(new PopStateEvent("popstate"));
          });
        </script>
      </body>
    </html>
    """
