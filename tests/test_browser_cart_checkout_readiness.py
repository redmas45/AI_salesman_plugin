"""Browser regressions: cart navigation and state-dependent checkout readiness.

These bundle the REAL host-contract action router (`hostContractActions.js` and
the modules it imports) and run it against the REAL local AI-KART dev server, so
the production routing and DOM verification actually execute.

Two capabilities are proven here, both through the published host contract and
never faked:

* "Open my cart" must reach the storefront's real cart route and leave the cart
  contents intact - a generic NAVIGATE_TO against a published cart nav target.
* Checkout readiness must depend on live cart state: unavailable with an empty
  cart, available once an item is added, and honestly unavailable again the
  moment the checkout capability is removed from the page. A stale success can
  never stand in for a capability the live DOM does not publish.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.test_browser_host_contract_driver import ESBUILD, _aikart_up, _fresh_page

REPO = Path(__file__).resolve().parent.parent
ROUTER_SRC = REPO / "plugin" / "src" / "actionExecutor" / "hostContractActions.js"

# A real AI-KART catalog record; the storefront resolves it by its exact name.
GALAXY_NAME = "Samsung Galaxy S26"

CART_COUNT_JS = (
    "() => Number(document.querySelector('[data-aihub-role=\"cart-button\"]')"
    ".getAttribute('data-cart-count'))"
)
CAN_CHECKOUT_JS = "() => window.__aihubRouter.canExecuteHostContractAction({ action: 'CHECKOUT' })"
STRIP_CHECKOUT_JS = (
    "() => {"
    " const strip = () => document.querySelectorAll('[data-aihub-role=\"checkout\"]')"
    ".forEach((node) => node.removeAttribute('data-aihub-role'));"
    " strip();"
    " window.__checkoutContractStripper = new MutationObserver(strip);"
    " window.__checkoutContractStripper.observe(document.documentElement, {"
    "  subtree: true, childList: true, attributes: true, attributeFilter: ['data-aihub-role']"
    " });"
    "}"
)


@pytest.fixture(scope="module")
def router_probe(tmp_path_factory) -> str:
    """Bundle the real action router to an IIFE exposing it on window."""
    if ESBUILD is None or not Path(ESBUILD).exists():
        pytest.skip("plugin esbuild not installed; run pnpm install in plugin/")
    tmp_path = tmp_path_factory.mktemp("cart_router")
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


async def _add_galaxy(page) -> None:
    outcome = await _route(page, {"action": "ADD_TO_CART", "params": {"product_name": GALAXY_NAME}})
    assert outcome["claimed"] is True, outcome
    assert outcome["result"]["status"] == "succeeded", outcome["result"]


# --- CP4: cart navigation -----------------------------------------------------


@pytest.mark.asyncio
async def test_open_my_cart_reaches_the_real_cart_route(router_probe) -> None:
    if not _aikart_up():
        pytest.skip("AI-KART dev server not reachable at localhost:5173")
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _fresh_page(playwright, router_probe)
        # Put a real item in the cart so there is state to preserve across the move.
        await _add_galaxy(page)
        before = await page.evaluate(CART_COUNT_JS)
        assert before >= 1, "the add must have changed the real cart"

        outcome = await _route(page, {"action": "NAVIGATE_TO", "params": {"page": "cart"}})
        assert outcome["claimed"] is True, "opening the cart is a published nav target"
        assert outcome["result"]["status"] == "succeeded", outcome["result"]

        # The customer's own page is now the store's real cart route, rendered.
        assert page.url.rstrip("/").endswith("/cart"), page.url
        await page.wait_for_selector("main")
        body = await page.locator("main").inner_text()
        assert "Galaxy" in body, "the cart page must show the item that was added"

        # Cart state survived the navigation - the count is unchanged, not reset.
        after = await page.evaluate(CART_COUNT_JS)
        assert after == before, (before, after)
        await browser.close()


@pytest.mark.asyncio
async def test_cart_navigation_is_a_precise_target_not_the_broad_shop(router_probe) -> None:
    """'cart' must reach the cart route, never bleed into the whole catalogue."""
    if not _aikart_up():
        pytest.skip("AI-KART dev server not reachable at localhost:5173")
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _fresh_page(playwright, router_probe)
        outcome = await _route(page, {"action": "NAVIGATE_TO", "params": {"page": "cart"}})
        assert outcome["result"]["status"] == "succeeded", outcome
        assert page.url.rstrip("/").endswith("/cart"), page.url
        assert "/shop" not in page.url and "category=" not in page.url, page.url
        await browser.close()


# --- CP5: state-dependent checkout readiness ---------------------------------


@pytest.mark.asyncio
async def test_checkout_is_unavailable_with_an_empty_cart(router_probe) -> None:
    if not _aikart_up():
        pytest.skip("AI-KART dev server not reachable at localhost:5173")
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _fresh_page(playwright, router_probe)
        # An empty cart publishes no checkout control, so the capability is absent.
        assert await page.evaluate(CAN_CHECKOUT_JS) is False
        outcome = await _route(page, {"action": "CHECKOUT"})
        assert outcome["claimed"] is False, "checkout must not be claimed on an empty cart"
        await browser.close()


@pytest.mark.asyncio
async def test_checkout_becomes_ready_and_executes_after_adding_an_item(router_probe) -> None:
    if not _aikart_up():
        pytest.skip("AI-KART dev server not reachable at localhost:5173")
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _fresh_page(playwright, router_probe)
        assert await page.evaluate(CAN_CHECKOUT_JS) is False  # baseline: empty

        await _add_galaxy(page)
        # Open the real cart route, where the checkout control is published.
        nav = await _route(page, {"action": "NAVIGATE_TO", "params": {"page": "cart"}})
        assert nav["result"]["status"] == "succeeded", nav

        # The capability is now live, and executing it reaches the real checkout.
        assert await page.evaluate(CAN_CHECKOUT_JS) is True
        outcome = await _route(page, {"action": "CHECKOUT"})
        assert outcome["claimed"] is True
        assert outcome["result"]["status"] == "succeeded", outcome["result"]
        assert page.url.rstrip("/").endswith("/checkout"), page.url
        await browser.close()


@pytest.mark.asyncio
async def test_removing_the_checkout_capability_fails_readiness_honestly(router_probe) -> None:
    """A missing live control can never be papered over by a past success."""
    if not _aikart_up():
        pytest.skip("AI-KART dev server not reachable at localhost:5173")
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _fresh_page(playwright, router_probe)
        await _add_galaxy(page)
        nav = await _route(page, {"action": "NAVIGATE_TO", "params": {"page": "cart"}})
        assert nav["result"]["status"] == "succeeded", nav
        assert await page.evaluate(CAN_CHECKOUT_JS) is True  # ready a moment ago

        # Break the capability: strip the published checkout control from the DOM.
        await page.evaluate(STRIP_CHECKOUT_JS)

        # Readiness is read from the live DOM every time, so it is honestly gone.
        assert await page.evaluate(CAN_CHECKOUT_JS) is False
        outcome = await _route(page, {"action": "CHECKOUT"})
        assert outcome["claimed"] is False, "a removed control must not still be claimed"
        # The URL never advanced to checkout on the broken capability.
        assert not page.url.rstrip("/").endswith("/checkout"), page.url
        await browser.close()
