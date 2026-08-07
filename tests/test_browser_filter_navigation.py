"""Browser regression: a resolved hard constraint reaches the filtered page.

Reported (2026-08-07): "phones under 20000 rupees" answered with three phones all
under budget, but the storefront navigated to `/search?q=smartphones` and showed
53 results - the price constraint never left the Hub. The answer and the page
disagreed about how many records matched.

The fix carries hard constraints as a typed `filters` object on SHOW_PRODUCTS; the
host publishes a filter slot per canonical key on its search form, so the widget's
one SPA submit lands on a real filtered results page. These run the REAL router
and the REAL local AI-KART, so the whole contract executes.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.test_browser_host_contract_driver import ESBUILD, _aikart_up, _fresh_page

REPO = Path(__file__).resolve().parent.parent
ROUTER_SRC = REPO / "plugin" / "src" / "actionExecutor" / "hostContractActions.js"

PRICES_JS = (
    "() => Array.from(document.querySelectorAll("
    "'[data-aihub-role=\"search-results\"] [data-aihub-role=\"product-card\"] [data-price]'))"
    ".map((el) => Number(el.getAttribute('data-price')))"
)
COUNT_JS = (
    "() => Number(document.querySelector('[data-aihub-role=\"search-results\"]')"
    ".getAttribute('data-result-count'))"
)


@pytest.fixture(scope="module")
def router_probe(tmp_path_factory) -> str:
    if ESBUILD is None or not Path(ESBUILD).exists():
        pytest.skip("plugin esbuild not installed; run pnpm install in plugin/")
    tmp_path = tmp_path_factory.mktemp("filter_router")
    entry = tmp_path / "router_entry.js"
    entry.write_text(
        f"import {{ canExecuteHostContractAction, executeHostContractAction }} from {ROUTER_SRC.as_posix()!r};\n"
        "window.__aihubRouter = { canExecuteHostContractAction, executeHostContractAction };\n"
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
    return await page.evaluate(
        """async (action) => {
            const claimed = window.__aihubRouter.canExecuteHostContractAction(action);
            if (!claimed) return { claimed: false };
            const result = await window.__aihubRouter.executeHostContractAction(action);
            return { claimed: true, result };
        }""",
        action,
    )


async def _settle(page) -> None:
    await page.wait_for_selector('[data-aihub-role="search-results"][data-results-loading="false"]')


@pytest.mark.asyncio
async def test_query_only_search_is_unfiltered_and_unchanged(router_probe) -> None:
    if not _aikart_up():
        pytest.skip("AI-KART dev server not reachable at localhost:5173")
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _fresh_page(playwright, router_probe)
        outcome = await _route(page, {"action": "SHOW_PRODUCTS", "params": {"search_query": "smartphones"}})
        assert outcome["result"]["status"] == "succeeded", outcome
        await _settle(page)
        assert "price_max" not in page.url, page.url
        assert await page.evaluate(COUNT_JS) == 53
        await browser.close()


@pytest.mark.asyncio
async def test_budget_constraint_reaches_a_filtered_page(router_probe) -> None:
    if not _aikart_up():
        pytest.skip("AI-KART dev server not reachable at localhost:5173")
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _fresh_page(playwright, router_probe)
        outcome = await _route(
            page,
            {"action": "SHOW_PRODUCTS", "params": {"search_query": "smartphones", "filters": {"max_price": 20000}}},
        )
        assert outcome["result"]["status"] == "succeeded", outcome
        assert outcome["result"]["evidence"]["applied_filters"] == ["max_price"], outcome["result"]["evidence"]
        await _settle(page)
        # The customer's own page is a real filtered results page, not the broad 53.
        assert "price_max=20000" in page.url, page.url
        assert await page.evaluate(COUNT_JS) == 15
        prices = await page.evaluate(PRICES_JS)
        assert prices and all(price <= 20000 for price in prices), prices
        await browser.close()


@pytest.mark.asyncio
async def test_brand_and_budget_combine_on_the_page(router_probe) -> None:
    if not _aikart_up():
        pytest.skip("AI-KART dev server not reachable at localhost:5173")
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _fresh_page(playwright, router_probe)
        outcome = await _route(
            page,
            {
                "action": "SHOW_PRODUCTS",
                "params": {"search_query": "smartphones", "filters": {"max_price": 20000, "brand": "Samsung"}},
            },
        )
        assert outcome["result"]["status"] == "succeeded", outcome
        assert set(outcome["result"]["evidence"]["applied_filters"]) == {"max_price", "brand"}
        await _settle(page)
        assert "price_max=20000" in page.url and "brand=Samsung" in page.url, page.url
        assert await page.evaluate(COUNT_JS) == 4
        prices = await page.evaluate(PRICES_JS)
        assert prices and all(price <= 20000 for price in prices), prices
        await browser.close()


@pytest.mark.asyncio
async def test_an_impossible_budget_reports_no_results_honestly(router_probe) -> None:
    if not _aikart_up():
        pytest.skip("AI-KART dev server not reachable at localhost:5173")
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _fresh_page(playwright, router_probe)
        outcome = await _route(
            page,
            {"action": "SHOW_PRODUCTS", "params": {"search_query": "smartphones", "filters": {"max_price": 1}}},
        )
        result = outcome["result"]
        # An empty filtered page is a failure, never a success on top of "0 results".
        assert result["status"] == "failed", result
        assert result["reason"] == "no_results", result
        assert "price_max=1" in page.url, page.url
        await browser.close()
