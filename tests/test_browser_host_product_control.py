"""Browser regressions: Maya operates the real storefront, not a stand-in overlay.

These bundle the REAL action router (`hostContractActions.js` and the driver
modules it imports) and run it against the REAL local AI-KART dev server, so the
production routing, identity resolution, and DOM verification all execute.

Reproduced defects (local probe, 2026-08-05):

* "Do you have Samsung phones?" produced SHOW_PRODUCTS, which no host executor
  claimed, so a placard opened while the storefront stayed on the home page.
* "Take me to the iPhone 17 page" produced SHOW_PRODUCT_DETAIL, which had no host
  executor at all, so no product route was ever opened.
* ADD_TO_CART carried the Hub catalog's own product id. The storefront keys the
  same product by its own slug, so the control was never found and the add could
  not happen - the customer's real cart never changed.

The fix keeps identity honest: the host's id wins when it is present, the exact
unique record name is the fallback, and anything ambiguous or absent is reported
rather than guessed at.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.test_browser_host_contract_driver import ESBUILD, _aikart_up, _fresh_page

REPO = Path(__file__).resolve().parent.parent
ROUTER_SRC = REPO / "plugin" / "src" / "actionExecutor" / "hostContractActions.js"

# Real AI-KART catalog records. The storefront owns these ids; the Hub's ingested
# copy keys the same products differently, which is exactly the case under test.
IPHONE_NAME = "iPhone 17"
IPHONE_HOST_ID = "phone-iphone-17"
GALAXY_NAME = "Samsung Galaxy S26"
GALAXY_HOST_ID = "phone-galaxy-s26"
# An id shaped like the Hub's ingested catalog, which the storefront never uses.
HUB_ONLY_ID = "4793851372839505515"

CART_COUNT_JS = (
    "() => Number(document.querySelector('[data-aihub-role=\"cart-button\"]')"
    ".getAttribute('data-cart-count'))"
)


@pytest.fixture(scope="module")
def router_probe(tmp_path_factory) -> str:
    """Bundle the real action router to an IIFE exposing it on window."""
    if ESBUILD is None or not Path(ESBUILD).exists():
        pytest.skip("plugin esbuild not installed; run pnpm install in plugin/")
    tmp_path = tmp_path_factory.mktemp("router")
    entry = tmp_path / "router_entry.js"
    entry.write_text(
        f"import {{ canExecuteHostContractAction, executeHostContractAction }} from {ROUTER_SRC.as_posix()!r};\n"
        "window.__aihubRouter = { canExecuteHostContractAction, executeHostContractAction };\n"
        # The shared page bootstrap waits on the driver global before handing the
        # page back, so publish the router under that name too.
        "window.__aihubDriver = window.__aihubRouter;\n",
        encoding="utf-8",
    )
    out = tmp_path / "router.js"
    result = subprocess.run(
        [str(ESBUILD), str(entry), "--bundle", "--format=iife", f"--outfile={out}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"esbuild unavailable to bundle the router: {result.stderr[:200]}")
    return out.read_text(encoding="utf-8")


async def _route(page, action: dict) -> dict:
    """Ask the real router whether it claims this action, and run it if so."""
    return await page.evaluate(
        """async (action) => {
            const claimed = window.__aihubRouter.canExecuteHostContractAction(action);
            if (!claimed) return { claimed: false };
            const result = await window.__aihubRouter.executeHostContractAction(action);
            return { claimed: true, result };
        }""",
        action,
    )


@pytest.mark.asyncio
async def test_ordinary_discovery_drives_the_real_storefront_not_an_overlay(router_probe) -> None:
    if not _aikart_up():
        pytest.skip("AI-KART dev server not reachable at localhost:5173")
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _fresh_page(playwright, router_probe)
        outcome = await _route(
            page,
            {"action": "SHOW_PRODUCTS", "params": {"product_ids": ["1", "2"], "search_query": "samsung"}},
        )
        assert outcome["claimed"] is True, "normal discovery must be driven on the host page"
        result = outcome["result"]
        assert result["status"] == "succeeded", result
        assert result["self_verified"] is True
        assert result["evidence"]["result_count"] >= 1
        # The customer's own page moved to the store's real results.
        assert "samsung" in page.url.lower(), page.url
        await page.wait_for_selector('[data-aihub-role="search-results"][data-results-loading="false"]')
        assert await page.locator('[data-aihub-role="search-results"] [data-aihub-role="product-card"]').count() >= 1
        await browser.close()


@pytest.mark.parametrize(
    ("requested_section", "expected_query"),
    [
        # The Hub may phrase a section as a bare key or as a path-ish target; both
        # must reach the same published link. Several sections are covered because
        # a site's visible label often differs from its published key
        # ("fashion-women" is labelled "Women's fashion"), and matching the label
        # alone silently found nothing.
        ("category/electronics", "category=electronics"),
        ("electronics", "category=electronics"),
        ("category/fashion-women", "category=fashion-women"),
        ("home-kitchen", "category=home-kitchen"),
        # The reported live failure: this target overlaps the broad "shop" link as
        # well as the section link, and the broad one used to win, dropping the
        # shopper into the entire catalogue.
        ("shop?category=electronics", "category=electronics"),
        ("shop?category=fashion-women", "category=fashion-women"),
    ],
)
@pytest.mark.asyncio
async def test_category_navigation_reaches_the_published_section(
    router_probe, requested_section: str, expected_query: str
) -> None:
    if not _aikart_up():
        pytest.skip("AI-KART dev server not reachable at localhost:5173")
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _fresh_page(playwright, router_probe)
        outcome = await _route(page, {"action": "NAVIGATE_TO", "params": {"page": requested_section}})
        assert outcome["claimed"] is True
        result = outcome["result"]
        assert result["status"] == "succeeded", result
        assert expected_query in page.url, page.url
        # The section actually rendered its own, narrower result set.
        await page.wait_for_selector('[data-aihub-role="search-results"][data-results-loading="false"]')
        count = await page.locator('[data-aihub-role="search-results"]').get_attribute("data-result-count")
        assert count and 0 < int(count), "the section must show its own products"
        await browser.close()


@pytest.mark.asyncio
async def test_a_broad_section_target_still_opens_the_broad_listing(router_probe) -> None:
    """Preferring the most specific match must not narrow an unqualified request."""
    if not _aikart_up():
        pytest.skip("AI-KART dev server not reachable at localhost:5173")
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _fresh_page(playwright, router_probe)
        outcome = await _route(page, {"action": "NAVIGATE_TO", "params": {"page": "shop"}})
        assert outcome["result"]["status"] == "succeeded", outcome
        assert "category=" not in page.url, page.url
        await browser.close()


@pytest.mark.asyncio
async def test_comparison_is_left_to_the_placard(router_probe) -> None:
    """Comparison stays the one product action that is answered by an overlay."""
    if not _aikart_up():
        pytest.skip("AI-KART dev server not reachable at localhost:5173")
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _fresh_page(playwright, router_probe)
        outcome = await _route(
            page,
            {"action": "SHOW_COMPARISON", "params": {"product_ids": ["1", "2"], "search_query": "samsung"}},
        )
        assert outcome["claimed"] is False, "a side-by-side comparison is not a storefront search"
        await browser.close()


@pytest.mark.asyncio
async def test_product_detail_opens_the_real_product_page(router_probe) -> None:
    if not _aikart_up():
        pytest.skip("AI-KART dev server not reachable at localhost:5173")
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _fresh_page(playwright, router_probe)
        # The Hub's own id is unknown to this storefront: the exact name resolves it.
        outcome = await _route(
            page,
            {
                "action": "SHOW_PRODUCT_DETAIL",
                "params": {"product_id": HUB_ONLY_ID, "product_name": IPHONE_NAME},
            },
        )
        assert outcome["claimed"] is True
        result = outcome["result"]
        assert result["status"] == "succeeded", result
        assert result["self_verified"] is True
        assert result["evidence"]["matched_by"] == "product_name"
        assert result["evidence"]["verified_by"], "arrival must be proven from the page"
        # The route came from the host's own product link, not from a pattern the
        # Hub guessed, so it is only asserted to be a product route on this origin.
        assert "/product/" in page.url, page.url
        title = await page.locator('[data-aihub-role="product-title"]').inner_text()
        assert title.strip() == IPHONE_NAME
        detail_id = await page.locator('[data-aihub-role="product-detail"]').get_attribute("data-product-id")
        assert detail_id == IPHONE_HOST_ID, "the page must publish the requested record's identity"
        await browser.close()


@pytest.mark.asyncio
async def test_add_to_cart_resolves_the_product_when_catalog_ids_differ(router_probe) -> None:
    if not _aikart_up():
        pytest.skip("AI-KART dev server not reachable at localhost:5173")
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _fresh_page(playwright, router_probe)
        before = await page.evaluate(CART_COUNT_JS)
        outcome = await _route(
            page,
            {
                "action": "ADD_TO_CART",
                "params": {"product_id": HUB_ONLY_ID, "product_name": GALAXY_NAME},
            },
        )
        assert outcome["claimed"] is True
        result = outcome["result"]
        assert result["status"] == "succeeded", result
        assert result["self_verified"] is True
        assert result["evidence"]["matched_by"] == "product_name"
        assert result["evidence"]["product_id"] == GALAXY_HOST_ID
        after = await page.evaluate(CART_COUNT_JS)
        assert after == before + 1, "the real cart must have changed"
        await browser.close()


@pytest.mark.asyncio
async def test_the_assistants_own_panel_never_stands_in_for_the_website(router_probe) -> None:
    """A record card inside our overlay must not satisfy a website action.

    The comparison placard renders its cards keyed by the HUB's product ids. Those
    ids resolved before the storefront's own card, so the add landed inside our own
    panel - which has no host add control - and the customer's real cart never
    changed even though everything upstream was correct.
    """
    if not _aikart_up():
        pytest.skip("AI-KART dev server not reachable at localhost:5173")
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _fresh_page(playwright, router_probe)
        # Stand in for the placard: our own panel, holding the Hub-keyed record.
        await page.evaluate(
            """(hubId) => {
                const panel = document.createElement('div');
                panel.id = 'mayabot-product-panel';
                const card = document.createElement('article');
                card.setAttribute('data-product-id', hubId);
                card.setAttribute('data-entity-name', 'Samsung Galaxy S26');
                panel.appendChild(card);
                document.body.appendChild(panel);
            }""",
            HUB_ONLY_ID,
        )
        before = await page.evaluate(CART_COUNT_JS)
        outcome = await _route(
            page,
            {"action": "ADD_TO_CART", "params": {"product_id": HUB_ONLY_ID, "product_name": GALAXY_NAME}},
        )
        result = outcome["result"]
        assert result["status"] == "succeeded", result
        assert result["evidence"]["product_id"] == GALAXY_HOST_ID, "the storefront's card must win"
        assert await page.evaluate(CART_COUNT_JS) == before + 1
        await browser.close()


@pytest.mark.asyncio
async def test_an_ambiguous_product_name_is_never_added(router_probe) -> None:
    """Two records sharing a name is a question to ask, not a coin to flip."""
    if not _aikart_up():
        pytest.skip("AI-KART dev server not reachable at localhost:5173")
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _fresh_page(playwright, router_probe)
        # Publish a second card carrying the same name as an existing one.
        await page.evaluate(
            """() => {
                const card = document.querySelector('[data-aihub-role="product-card"]');
                const twin = card.cloneNode(true);
                twin.setAttribute('data-product-id', 'twin-of-the-first-card');
                card.parentElement.appendChild(twin);
            }"""
        )
        name = await page.evaluate(
            "() => document.querySelector('[data-aihub-role=\"product-card\"]').getAttribute('data-entity-name')"
        )
        before = await page.evaluate(CART_COUNT_JS)
        outcome = await _route(page, {"action": "ADD_TO_CART", "params": {"product_name": name}})
        result = outcome["result"]
        assert result["status"] == "failed", result
        assert result["reason"] == "ambiguous_product"
        assert result["evidence"]["match_count"] >= 2
        assert await page.evaluate(CART_COUNT_JS) == before, "an unresolved add must not touch the cart"
        await browser.close()


@pytest.mark.asyncio
async def test_a_product_the_store_does_not_have_is_reported_not_faked(router_probe) -> None:
    if not _aikart_up():
        pytest.skip("AI-KART dev server not reachable at localhost:5173")
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _fresh_page(playwright, router_probe)
        before = await page.evaluate(CART_COUNT_JS)
        outcome = await _route(
            page,
            {"action": "ADD_TO_CART", "params": {"product_id": HUB_ONLY_ID, "product_name": "Nonexistent Gadget 9000"}},
        )
        result = outcome["result"]
        assert result["status"] == "failed", result
        assert result["reason"] == "product_not_on_page"
        assert await page.evaluate(CART_COUNT_JS) == before
        await browser.close()
