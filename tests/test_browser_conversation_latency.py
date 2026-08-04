"""Conversation payload must stay bounded as turns accumulate (real bundle).

The reported regression is "the conversation gets slower every turn". A first-order
cause of per-turn cost growing without bound is the request payload growing without
bound - the whole transcript being resent each turn. This harness drives 30 real
turns through the built widget and records, per turn, how large the request is and
how many history entries it carries, then asserts:

* the history entry count is bounded (never grows past the configured limit);
* the payload at turn 30 is not materially larger than at turn 12 (a plateau, not
  a line);
* exactly one /v1/shop request is made per turn (no duplicate in-flight request).

Only the network is stubbed; the widget code that assembles the payload is real.
The measured table is printed for the handoff latency ledger.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

WIDGET_BUNDLE = Path("plugin/mayabot.js")
SHOP_URL = re.compile(r"https://hub\.example\.test/v1/shop.*")
TURNS = 30
SAMPLE_TURNS = (1, 5, 10, 20, 30)
HISTORY_LIMIT = 12  # plugin/src/core/constants.js CONVERSATION_HISTORY_LIMIT


def _page_html() -> str:
    return """
    <!doctype html><html><head><title>Latency</title>
    <script defer src="https://hub.example.test/mayabot.js?site=lat_demo"></script></head>
    <body><main>Shop</main></body></html>
    """


def _mock_script() -> str:
    return """
    const nativeSetTimeout = window.setTimeout.bind(window);
    window.setTimeout = (cb, delay, ...a) => nativeSetTimeout(cb, delay === 300 ? 3000 : delay === 2400 ? 24000 : delay, ...a);
    window.__availableVoices = [{ name: 'Samantha', lang: 'en-US', default: true }];
    window.SpeechSynthesisUtterance = class { constructor(t){ this.text=t; } };
    Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: {
      speaking: false, pending: false, onvoiceschanged: null,
      getVoices: () => window.__availableVoices,
      cancel(){ this.speaking = false; }, resume(){},
      speak(u){ if (u && u.onstart) u.onstart(); if (u && u.onend) u.onend(); this.speaking = false; },
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


def _shop_body(turn: int) -> str:
    # Each answer carries product ids so history entries are non-trivial, the
    # worst case for payload growth.
    ids = [f"prod-{turn}-{i}" for i in range(6)]
    return json.dumps({
        "transcript": f"question {turn}",
        "response_text": f"Answer {turn} with several matching products for your query.",
        "ui_actions": [{"action": "SHOW_PRODUCTS", "params": {"product_ids": ids}}],
        "audio_b64": "",
    })


def _history_from(post_data: str):
    """Extract the conversation_history field from the multipart turn body."""
    marker = 'name="conversation_history"'
    index = post_data.find(marker)
    if index == -1:
        return []
    body = post_data[index + len(marker):]
    start = body.find("[")
    end = body.find("------", start)
    chunk = body[start:end].strip() if start != -1 else ""
    try:
        return json.loads(chunk)
    except Exception:
        return []


@pytest.mark.asyncio
async def test_history_payload_stays_bounded_across_thirty_turns() -> None:
    playwright_api = pytest.importorskip("playwright.async_api")
    captured: list[str] = []
    turn_counter = {"n": 0}

    async def shop(route):
        captured.append(route.request.post_data or "")
        turn_counter["n"] += 1
        await route.fulfill(status=200, content_type="application/json", body=_shop_body(turn_counter["n"]))

    async with playwright_api.async_playwright() as playwright:
        widget_js = WIDGET_BUNDLE.read_text(encoding="utf-8")
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        page.set_default_timeout(9000)
        await page.add_init_script(_mock_script())
        await page.route("https://shop.example.test/", lambda r: r.fulfill(status=200, content_type="text/html", body=_page_html()))
        await page.route(re.compile(r"https://hub\.example\.test/mayabot\.js.*"),
                         lambda r: r.fulfill(status=200, content_type="application/javascript", body=widget_js))
        await page.route(re.compile(r"https://hub\.example\.test/v1/widget/status.*"),
                         lambda r: r.fulfill(status=200, content_type="application/json", body='{"enabled":true}'))
        await page.route(re.compile(r"https://hub\.example\.test/v1/widget/runtime-event.*"),
                         lambda r: r.fulfill(status=204, body=""))
        await page.route(SHOP_URL, shop)
        await page.goto("https://shop.example.test/", wait_until="networkidle")
        await page.get_by_text("Welcome to Maya").wait_for()

        orb = page.locator("#mayabot-btn")
        await page.keyboard.press("Escape")

        async def idle():
            await page.wait_for_function(
                "() => document.getElementById('mayabot-btn')?.getAttribute('data-orb-state') === 'idle'"
            )

        for turn in range(TURNS):
            before = len(captured)
            await idle()
            await orb.click()            # start recording
            await page.wait_for_timeout(150)
            await orb.click()            # stop -> submit
            # Wait for THIS turn's request to be observed before the next turn, so
            # a start-click can never land on an in-flight turn and cancel it.
            for _ in range(60):
                if len(captured) > before:
                    break
                await page.wait_for_timeout(50)
            await page.wait_for_timeout(120)

        assert len(captured) == TURNS, f"expected one request per turn, got {len(captured)} for {TURNS} turns"

        table = []
        for turn in SAMPLE_TURNS:
            body = captured[turn - 1]
            history = _history_from(body)
            table.append((turn, len(history), len(body), len(body) // 4))

        print("\nturn | history_entries | payload_bytes | approx_tokens")
        for turn, entries, size, tokens in table:
            print(f"{turn:>4} | {entries:>15} | {size:>13} | {tokens:>13}")

        entries_by_turn = {turn: entries for turn, entries, _s, _t in table}
        size_by_turn = {turn: size for turn, _e, size, _t in table}

        # Bounded entry count: never past the configured window.
        for turn, entries in entries_by_turn.items():
            assert entries <= HISTORY_LIMIT, f"turn {turn} sent {entries} history entries (> {HISTORY_LIMIT})"

        # Older turns are summarized: from turn 10 on, the sent history is one
        # system summary + the recent verbatim window (not the whole transcript).
        late = _history_from(captured[19])  # turn 20
        assert late and late[0].get("role") == "system", f"expected a leading summary, got {late[:1]}"
        assert "[CONVERSATION_SUMMARY]" in late[0].get("content", "")
        assert len(late) <= 7, f"summary + recent window only; got {len(late)} entries"
        # The latest exchanges are kept verbatim (accuracy for the current task).
        assert any(e.get("role") == "user" for e in late[1:])

        # Plateau, not a line: turn 30 must not be materially larger than turn 12's
        # steady state (turn 20 is already at the cap). Linear growth would make
        # turn 30 ~2.5x turn 20.
        assert size_by_turn[30] <= size_by_turn[20] * 1.25, (
            f"payload grew with transcript length: t20={size_by_turn[20]} t30={size_by_turn[30]}"
        )
        await browser.close()
