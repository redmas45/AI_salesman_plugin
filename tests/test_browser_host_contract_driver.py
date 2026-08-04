"""The Hub host-contract driver, exercised against the REAL local AI-KART site.

This is the "real widget bundle against the real local website" evidence. The
actual driver source (`plugin/src/actionExecutor/hostContract.js`, with its real
`deepDom` / `eventDriver` dependencies) is bundled with the project's own esbuild
and injected into the running AI-KART storefront, then its `runHostSearch` /
`runHostAddToCart` are driven and their results checked against the real DOM.

Nothing here asserts on Maya's text: every claim is a re-read of the storefront
(route, `data-aihub-role="search-results"` count, `data-cart-count` transition,
`data-aihub-role="cart-line-item"`). The driver is vertical-neutral - it only
reads the published contract - so this same test would pass on any host that
publishes it.

Requires the local AI-KART dev server (`pnpm --filter frontend dev`, default
http://localhost:5173) and its backend. If either is unreachable the test SKIPS
with a message rather than passing - an unavailable dependency is not a pass.
"""

from __future__ import annotations

import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DRIVER_SRC = REPO / "plugin" / "src" / "actionExecutor" / "hostContract.js"
# The platform esbuild binary (bin/esbuild is a Node wrapper, not a Windows exe).
ESBUILD = next(REPO.glob("plugin/node_modules/@esbuild/*/esbuild*"), None) or (
    REPO / "plugin" / "node_modules" / "esbuild" / "bin" / "esbuild"
)
AIKART_URL = "http://localhost:5173/"


def _aikart_up() -> bool:
    """True only when the storefront AND its product API are serving, so a card
    with the contract markers can actually render. A frontend without its backend
    is treated as unavailable (skip), not as a failure."""
    try:
        with urllib.request.urlopen(AIKART_URL, timeout=3) as response:
            if response.status != 200:
                return False
        with urllib.request.urlopen("http://127.0.0.1:8000/api/products?search=samsung", timeout=3) as api:
            return api.status == 200
    except Exception:
        return False


def _build_driver_probe(tmp_path: Path) -> str:
    """Bundle the real driver (+ real deps) to an IIFE exposing it on window."""
    entry = tmp_path / "probe_entry.js"
    entry.write_text(
        f"import {{ runHostSearch, runHostAddToCart, runHostNavigate, hostPublishesSearch, "
        f"hostPublishesCart, hostPublishesNav }} from {DRIVER_SRC.as_posix()!r};\n"
        "window.__aihubDriver = { runHostSearch, runHostAddToCart, runHostNavigate, "
        "hostPublishesSearch, hostPublishesCart, hostPublishesNav };\n",
        encoding="utf-8",
    )
    out = tmp_path / "probe.js"
    result = subprocess.run(
        [str(ESBUILD), str(entry), "--bundle", "--format=iife", f"--outfile={out}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"esbuild unavailable to bundle the driver: {result.stderr[:200]}")
    return out.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def driver_probe(tmp_path_factory):
    if ESBUILD is None or not Path(ESBUILD).exists():
        pytest.skip("plugin esbuild not installed; run pnpm install in plugin/")
    return _build_driver_probe(tmp_path_factory.mktemp("driver"))


async def _fresh_page(playwright, driver_js: str):
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context()
    await context.clear_cookies()
    page = await context.new_page()
    page.set_default_timeout(12000)
    # The Vite dev server keeps HMR sockets open, so "networkidle" never fires;
    # wait for the DOM and an actual product card instead.
    await page.goto(AIKART_URL, wait_until="domcontentloaded")
    await page.wait_for_selector('[data-aihub-role="add-to-cart"]')
    await page.evaluate("() => window.localStorage.removeItem('aikart-cart')")
    await page.reload(wait_until="domcontentloaded")
    await page.wait_for_selector('[data-aihub-role="add-to-cart"]')
    await page.add_script_tag(content=driver_js)
    await page.wait_for_function("Boolean(window.__aihubDriver)")
    return browser, page


@pytest.mark.asyncio
async def test_real_search_drives_the_storefront_and_verifies_results(driver_probe) -> None:
    if not _aikart_up():
        pytest.skip("AI-KART dev server not reachable at localhost:5173")
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _fresh_page(playwright, driver_probe)
        result = await page.evaluate("() => window.__aihubDriver.runHostSearch('samsung')")

        assert result["status"] == "succeeded", result
        assert result["self_verified"] is True
        assert result["evidence"]["route_reflects_query"] is True
        assert result["evidence"]["result_count"] >= 1
        # The DOM itself moved to the search route with visible Samsung results.
        assert "/search" in page.url and "samsung" in page.url
        names = await page.evaluate(
            "() => Array.from(document.querySelectorAll('[data-aihub-role=\"search-results\"] [data-entity-name]'))"
            ".map(n => n.getAttribute('data-entity-name')).filter(Boolean).slice(0,5)"
        )
        assert any("samsung" in (n or "").lower() for n in names), names
        await browser.close()


@pytest.mark.asyncio
async def test_real_add_to_cart_changes_the_cart_and_verifies(driver_probe) -> None:
    if not _aikart_up():
        pytest.skip("AI-KART dev server not reachable at localhost:5173")
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _fresh_page(playwright, driver_probe)
        # A real product id from the current catalog (first card on the home grid).
        product_id = await page.evaluate(
            "() => document.querySelector('[data-aihub-role=\"add-to-cart\"]').getAttribute('data-product-id')"
        )
        before = await page.evaluate(
            "() => Number(document.querySelector('[data-aihub-role=\"cart-button\"]').getAttribute('data-cart-count'))"
        )
        result = await page.evaluate(
            "(id) => window.__aihubDriver.runHostAddToCart({ product_id: id })", product_id
        )

        assert result["status"] == "succeeded", result
        assert result["self_verified"] is True
        assert result["evidence"]["cart_after"] == before + 1
        assert result["evidence"]["line_item_present"] is True
        line = await page.evaluate(
            "(id) => Boolean(document.querySelector(`[data-aihub-role=\"cart-line-item\"][data-product-id=\"${id}\"]`))",
            product_id,
        )
        assert line, "the cart line item for the added product must be present"
        await browser.close()


@pytest.mark.asyncio
async def test_naming_a_product_not_on_the_page_fails_not_fakes(driver_probe) -> None:
    if not _aikart_up():
        pytest.skip("AI-KART dev server not reachable at localhost:5173")
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _fresh_page(playwright, driver_probe)
        result = await page.evaluate(
            "() => window.__aihubDriver.runHostAddToCart({ product_id: 'no-such-product-xyz' })"
        )
        assert result["status"] == "failed", result
        assert result["reason"] == "product_not_on_page"
        after = await page.evaluate(
            "() => Number(document.querySelector('[data-aihub-role=\"cart-button\"]').getAttribute('data-cart-count'))"
        )
        assert after == 0, "a failed add must not have changed the cart"
        await browser.close()


@pytest.mark.asyncio
async def test_empty_query_search_is_rejected_without_navigation(driver_probe) -> None:
    if not _aikart_up():
        pytest.skip("AI-KART dev server not reachable at localhost:5173")
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _fresh_page(playwright, driver_probe)
        result = await page.evaluate("() => window.__aihubDriver.runHostSearch('   ')")
        assert result["status"] in {"failed", "unsupported_host"}, result
        assert "/search" not in page.url
        await browser.close()


@pytest.mark.asyncio
async def test_real_navigation_reaches_the_target_route_and_verifies(driver_probe) -> None:
    if not _aikart_up():
        pytest.skip("AI-KART dev server not reachable at localhost:5173")
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _fresh_page(playwright, driver_probe)
        result = await page.evaluate("() => window.__aihubDriver.runHostNavigate('shop')")
        assert result["status"] == "succeeded", result
        assert result["self_verified"] is True
        assert result["evidence"]["expected"] == "/shop"
        assert page.url.endswith("/shop"), page.url
        # The destination actually rendered product cards (the listing loads them
        # asynchronously), not just a URL change.
        await page.wait_for_selector('[data-aihub-role="add-to-cart"]')
        assert await page.locator('[data-aihub-role="add-to-cart"]').count() >= 1
        await browser.close()


@pytest.mark.asyncio
async def test_navigation_to_an_unknown_target_fails_not_fakes(driver_probe) -> None:
    if not _aikart_up():
        pytest.skip("AI-KART dev server not reachable at localhost:5173")
    playwright_api = pytest.importorskip("playwright.async_api")
    async with playwright_api.async_playwright() as playwright:
        browser, page = await _fresh_page(playwright, driver_probe)
        start = page.url
        result = await page.evaluate("() => window.__aihubDriver.runHostNavigate('nonexistent-section-xyz')")
        assert result["status"] == "failed", result
        assert result["reason"] == "no_matching_nav_target"
        assert page.url == start, "a failed navigation must not have moved the page"
        await browser.close()
