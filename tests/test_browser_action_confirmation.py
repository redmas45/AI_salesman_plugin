"""Browser regressions: a tentative action promise must resolve to the truth.

These drive the REAL built `plugin/mayabot.js` and stub only the network, so the
production `confirmedResponseText` gate runs against a real add-to-cart executed
through the published `data-aihub-role` contract.

Reproduced defect (public conversation, 2026-08-04):

* Maya said "I'll try to add Samsung Smartwatch to your cart now." and
  "I'll try to open the iPhone 17 product page for you now." The server de-claims
  every optimistic claim into this tentative "I'll try to <verb>" wording because
  it cannot verify a browser action itself, and delegates the final word to the
  widget. But the widget's claim gate only matched past/continuous verbs
  ("opened", "added to cart"), never the tentative promise the server actually
  sends - so on both success and failure the tentative text was the final word.
  A failed cart add still sounded like it was happening; a successful one never
  confirmed.

The fix: an action-bearing turn whose wording depends on the outcome must speak
the recovery line when the browser could not verify the action, and the confirmed
`success_text` when it did.
"""

from __future__ import annotations

import json

import pytest

from tests.test_browser_page_state import _boot, _record_and_submit, _spoken_text

# A tentative promise in exactly the shape the server emits after de-claiming.
TENTATIVE_CART_TEXT = "I'll try to add Aster Kurta to your cart now."
CONFIRMED_CART_TEXT = "Aster Kurta is now in your cart."

# An add-to-cart control published through the host contract on product p1. The
# failing variant never changes the cart; the succeeding variant increments the
# host's own cart-count marker, which is what the widget re-reads as proof.
_INERT_ADD_CONTROL = """
(() => {
  const card = document.querySelector('[data-product-id="p1"]');
  const button = document.createElement('button');
  button.setAttribute('data-aihub-role', 'add-to-cart');
  button.setAttribute('data-product-id', 'p1');
  button.textContent = 'Add to cart';
  card.appendChild(button);
})();
"""

_WORKING_ADD_CONTROL = """
(() => {
  const card = document.querySelector('[data-product-id="p1"]');
  const counter = document.querySelector('#cart-count');
  const button = document.createElement('button');
  button.setAttribute('data-aihub-role', 'add-to-cart');
  button.setAttribute('data-product-id', 'p1');
  button.textContent = 'Add to cart';
  button.addEventListener('click', () => {
    const next = Number(counter.getAttribute('data-cart-count') || '0') + 1;
    counter.setAttribute('data-cart-count', String(next));
    counter.textContent = String(next);
  });
  card.appendChild(button);
})();
"""


def _cart_turn(success_text: str = "") -> str:
    payload = {
        "transcript": "add Aster Kurta to my cart",
        "response_text": TENTATIVE_CART_TEXT,
        "ui_actions": [{"action": "ADD_TO_CART", "params": {"product_id": "p1"}}],
        "audio_b64": "",
    }
    if success_text:
        payload["success_text"] = success_text
    return json.dumps(payload)


@pytest.mark.asyncio
async def test_a_failed_cart_add_is_not_narrated_as_in_progress() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")

    async def add_to_cart(route) -> None:
        await route.fulfill(status=200, content_type="application/json", body=_cart_turn())

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright, add_to_cart)
        await page.evaluate(_INERT_ADD_CONTROL)
        await _record_and_submit(page)
        await page.wait_for_timeout(5200)
        transcript = await _spoken_text(page)
        assert TENTATIVE_CART_TEXT not in transcript, (
            "the cart never changed, so the tentative promise must not be the final word"
        )
        assert "could not complete" in transcript.lower(), (
            "a cart add the host did not confirm must fall back to the recovery message"
        )
        await browser.close()


@pytest.mark.asyncio
async def test_a_verified_cart_add_speaks_the_confirmed_outcome() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")

    async def add_to_cart(route) -> None:
        await route.fulfill(
            status=200,
            content_type="application/json",
            body=_cart_turn(success_text=CONFIRMED_CART_TEXT),
        )

    async with playwright_api.async_playwright() as playwright:
        browser, page = await _boot(playwright, add_to_cart)
        await page.evaluate(_WORKING_ADD_CONTROL)
        await _record_and_submit(page)
        await page.wait_for_timeout(5200)
        transcript = await _spoken_text(page)
        assert CONFIRMED_CART_TEXT in transcript, (
            "the host cart increased, so Maya states the completed outcome"
        )
        assert TENTATIVE_CART_TEXT not in transcript, (
            "a verified add must not stay tentative"
        )
        assert "could not complete" not in transcript.lower()
        await browser.close()
