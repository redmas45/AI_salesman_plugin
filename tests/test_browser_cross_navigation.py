"""Cross-navigation continuity, driven through the real built adapter bundle.

An action that needs the record's own page destroys the JavaScript context that
requested it. Previously nothing survived that boundary, so the destination page
could not tell whether the requested state was ever reached - and any claim about
it was unverifiable.

A single bounded record now survives, and it is deliberately refused for money
movement and destructive changes: a stale or duplicated replay of those would
spend money or empty a cart the customer never mentioned on this page.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ADAPTER_BUNDLE = Path("plugin/mayabot-adapter.js")
SITE_ID = "continuity_demo"
STORAGE_KEY = f"aihub:pending-postcondition:{SITE_ID}"


def _runtime_config() -> dict:
    return {
        "site_id": SITE_ID,
        "enabled": True,
        "vertical": {"key": "ecommerce", "label": "Shop", "action_types": ["ADD_TO_CART", "SHOW_PRODUCTS"]},
        "adapter": {
            "routes": {"home": "/", "products": "/products"},
            "actions": {},
            "selectors": {},
            "action_policy": {"blocked_actions": [], "handoff_actions": []},
        },
    }


def _listing_html() -> str:
    return f"""
    <!doctype html>
    <html>
      <head>
        <title>Listing</title>
        <script defer src="https://hub.example.test/mayabot-adapter.js?site={SITE_ID}"></script>
      </head>
      <body>
        <main>
          <div data-product-id="sku-1" data-entity-type="product"><h3>Aster Kurta</h3></div>
          <div data-product-id="sku-2" data-entity-type="product"><h3>Borel Bottle</h3></div>
        </main>
      </body>
    </html>
    """


async def _boot(playwright):
    adapter_js = ADAPTER_BUNDLE.read_text(encoding="utf-8")
    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page()
    page.set_default_timeout(9000)

    async def shell(route) -> None:
        await route.fulfill(status=200, content_type="text/html", body=_listing_html())

    async def adapter(route) -> None:
        await route.fulfill(status=200, content_type="application/javascript", body=adapter_js)

    async def config(route) -> None:
        await route.fulfill(status=200, content_type="application/json", body=json.dumps(_runtime_config()))

    async def ok(route) -> None:
        await route.fulfill(status=200, content_type="application/json", body='{"ok":true}')

    await page.route(re.compile(r"https://shop\.example\.test/.*"), shell)
    await page.route(re.compile(r"https://hub\.example\.test/mayabot-adapter\.js.*"), adapter)
    await page.route(re.compile(r"https://hub\.example\.test/v1/widget/config.*"), config)
    await page.route(re.compile(r"https://hub\.example\.test/v1/widget/.*"), ok)
    await page.route(re.compile(r"https://hub\.example\.test/v1/products.*"), ok)
    await page.goto("https://shop.example.test/", wait_until="networkidle")
    await page.wait_for_function("Boolean(window.AIHubAdapterRuntime)")
    return browser, page


async def _stored_record(page):
    raw = await page.evaluate(f"window.sessionStorage.getItem({STORAGE_KEY!r})")
    return json.loads(raw) if raw else None


@pytest.mark.asyncio
async def test_a_carried_record_is_bounded_and_bound_to_this_site_and_origin() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright)
        await page.evaluate(
            f"""window.sessionStorage.setItem({STORAGE_KEY!r}, JSON.stringify({{
              action: "ADD_TO_CART",
              ids: ["sku-1"],
              target_path: "/products/sku-1",
              origin: window.location.origin,
              site_id: {SITE_ID!r},
              created_at: Date.now(),
            }}))"""
        )
        record = await _stored_record(page)

        assert record["site_id"] == SITE_ID, "a record must name the site it belongs to"
        assert record["origin"] == "https://shop.example.test"
        assert set(record) == {"action", "ids", "target_path", "origin", "site_id", "created_at"}, (
            "only the fields needed to re-check the postcondition may cross the boundary"
        )
        assert all(key not in record for key in ("token", "session", "email", "payment")), (
            "no credential or personal field may be carried across a navigation"
        )
        await browser.close()


@pytest.mark.asyncio
async def test_the_record_is_consumed_exactly_once_on_the_destination_page() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright)
        await page.evaluate(
            f"""window.sessionStorage.setItem({STORAGE_KEY!r}, JSON.stringify({{
              action: "SHOW_PRODUCTS", ids: ["sku-1"], target_path: "/",
              origin: window.location.origin, site_id: {SITE_ID!r}, created_at: Date.now(),
            }}))"""
        )
        await page.reload(wait_until="networkidle")
        await page.wait_for_function("Boolean(window.AIHubAdapterRuntime)")
        await page.wait_for_timeout(500)

        assert await _stored_record(page) is None, (
            "the record must be consumed on arrival so it cannot vouch for a later, unrelated turn"
        )
        await browser.close()


@pytest.mark.asyncio
async def test_an_expired_record_is_discarded_rather_than_honoured() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright)
        await page.evaluate(
            f"""window.sessionStorage.setItem({STORAGE_KEY!r}, JSON.stringify({{
              action: "SHOW_PRODUCTS", ids: ["sku-1"], target_path: "/",
              origin: window.location.origin, site_id: {SITE_ID!r},
              created_at: Date.now() - 600000,
            }}))"""
        )
        await page.reload(wait_until="networkidle")
        await page.wait_for_function("Boolean(window.AIHubAdapterRuntime)")
        await page.wait_for_timeout(500)

        assert await _stored_record(page) is None, "an aged-out record must be cleared, not left behind"
        await browser.close()


@pytest.mark.asyncio
async def test_money_and_destructive_actions_are_never_carried_across_navigation() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright)
        for action in ("CHECKOUT", "CLEAR_CART", "REMOVE_FROM_CART", "UPDATE_CART_QUANTITY"):
            await page.evaluate(
                f"""window.sessionStorage.setItem({STORAGE_KEY!r}, JSON.stringify({{
                  action: {action!r}, ids: ["sku-1"], target_path: "/",
                  origin: window.location.origin, site_id: {SITE_ID!r}, created_at: Date.now(),
                }}))"""
            )
            await page.reload(wait_until="networkidle")
            await page.wait_for_function("Boolean(window.AIHubAdapterRuntime)")
            await page.wait_for_timeout(400)

            assert await _stored_record(page) is None, f"{action} must be dropped, never honoured"
        await browser.close()


@pytest.mark.asyncio
async def test_a_record_from_another_site_is_ignored() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright)
        foreign_key = "aihub:pending-postcondition:some_other_site"
        await page.evaluate(
            f"""window.sessionStorage.setItem({foreign_key!r}, JSON.stringify({{
              action: "SHOW_PRODUCTS", ids: ["sku-1"], target_path: "/",
              origin: window.location.origin, site_id: "some_other_site", created_at: Date.now(),
            }}))"""
        )
        await page.reload(wait_until="networkidle")
        await page.wait_for_function("Boolean(window.AIHubAdapterRuntime)")
        await page.wait_for_timeout(400)

        assert await page.evaluate(f"window.sessionStorage.getItem({foreign_key!r})") is not None, (
            "another site's record is not this site's to consume"
        )
        await browser.close()
