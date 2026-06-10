# Voice Orb Not Showing - Investigation Report

Date checked: 2026-06-10

## Fixed State

This issue has now been fixed and redeployed. The live production page at `https://vercelclonedwebsite.vercel.app/` now contains the inlined `voice-orb` widget code, contains the active ngrok API URL, and no longer contains `127.0.0.1`.

Latest verified production deployment:

```text
https://vercelclonedwebsite-7b6kudutr-splitmoney.vercel.app
```

Latest build log confirmed:

```text
[inject-shopbot] Successfully fetched and inlined shopbot.js
```

## Short Answer

The voice orb is not showing because the live Vercel site is currently loading this broken script:

```html
<script src="http://127.0.0.1:8001/shopbot.js?site=https_demo_vercel_store"></script>
```

That URL cannot work on the live HTTPS site. In a visitor browser, `127.0.0.1` means the visitor's own computer, not your backend. Also, because the page is HTTPS and the script is HTTP, the browser can block it as mixed content. Since the browser never downloads `shopbot.js`, the widget code never runs and the `.voice-orb` DOM is never created.

The admin panel itself is not directly hiding the orb. The admin work exposed/developed around a deployment sync problem: the backend `.env` and Vercel `SHOPBOT_API_URL` were updated with a localhost fallback instead of the active ngrok HTTPS URL.

## Evidence

1. Backend widget code is healthy.

   The active backend is listening on `127.0.0.1:8002`, and ngrok is forwarding this public URL to it:

   ```text
   https://e30c-2401-4900-7fa1-25cd-adf4-1538-55dd-8af0.ngrok-free.app
   ```

   Fetching either of these returned a valid `shopbot.js` with the `.voice-orb` code:

   ```text
   http://127.0.0.1:8002/shopbot.js?site=https_demo_vercel_store
   https://e30c-2401-4900-7fa1-25cd-adf4-1538-55dd-8af0.ngrok-free.app/shopbot.js?site=https_demo_vercel_store
   ```

2. The live Vercel page is not using that active backend.

   The source of `https://vercelclonedwebsite.vercel.app/` contains `shopbot`, but it contains `127.0.0.1` and does not contain `voice-orb`. The injected script is:

   ```html
   <script src="http://127.0.0.1:8001/shopbot.js?site=https_demo_vercel_store"></script>
   ```

3. The latest Vercel build log proves the bad value came from the deploy environment.

   Latest production build log:

   ```text
   [inject-shopbot] Fetching shopbot.js from http://127.0.0.1:8001...
   [inject-shopbot] Failed to fetch shopbot.js: fetch failed. Falling back to script src tag.
   [inject-shopbot] Using script src tag:
   <script src="http://127.0.0.1:8001/shopbot.js?site=https_demo_vercel_store"></script>
   [inject-shopbot] Done. Injected into 37 files, skipped 0.
   ```

4. The backend `.env` currently has the stale/bad public URL.

   Current relevant values:

   ```env
   PUBLIC_API_URL='http://127.0.0.1:8001'
   PUBLIC_WIDGET_SCRIPT_URL='http://127.0.0.1:8001/shopbot.js?site=https_demo_vercel_store'
   MANUAL_WIDGET_SCRIPT='<script src="http://127.0.0.1:8001/shopbot.js?site=https_demo_vercel_store"></script>'
   ```

   But the active backend is on port `8002`, and the active public URL is the ngrok HTTPS URL above.

5. `scripts/update_vercel.py` explains how the bad value reached Vercel.

   The updater reads `PUBLIC_API_URL` from `AI_salesman_plugin/.env`, writes it into Vercel as `SHOPBOT_API_URL`, and redeploys. Since `.env` contained `http://127.0.0.1:8001`, the production build injected that same bad URL.

## Relation To Admin Panel Changes

The `/admin` route caused or could cause a separate crawler problem because it is Basic Auth protected and returns `401 Unauthorized`. The current `agent/ingestion.py` change that skips URLs containing `/admin` is the right direction for preventing crawler crashes.

But this is not the direct reason the orb is invisible. The orb is invisible because production is loading a dead localhost script URL.

The admin link injected into storefront pages is also not the direct issue. It is bottom-left with `z-index: 9999`; the orb would be bottom-center with `z-index: 999999`, so it should still appear if `shopbot.js` loads.

## Actual Fix Sequence

1. Start the backend cleanly and wait for a real ngrok URL.

   The backend output must show something like:

   ```text
   Ngrok public URL: https://...ngrok-free.app
   Widget will be served from: https://...ngrok-free.app
   ```

   Do not deploy if it falls back to `http://127.0.0.1:8001` or any other localhost URL.

2. Confirm `.env` has the ngrok HTTPS URL.

   These must all point to the active ngrok URL, not `127.0.0.1`:

   ```env
   PUBLIC_API_URL=https://...ngrok-free.app
   PUBLIC_WIDGET_SCRIPT_URL=https://...ngrok-free.app/shopbot.js?site=https_demo_vercel_store
   MANUAL_WIDGET_SCRIPT=<script src="https://...ngrok-free.app/shopbot.js?site=https_demo_vercel_store"></script>
   ```

3. Run the Vercel updater only after `.env` is correct.

   ```powershell
   python scripts\update_vercel.py
   ```

4. Verify the Vercel build log.

   The good build log should say:

   ```text
   [inject-shopbot] Fetching shopbot.js from https://...ngrok-free.app...
   [inject-shopbot] Successfully fetched and inlined shopbot.js
   ```

   It should not say:

   ```text
   Falling back to script src tag
   http://127.0.0.1
   ```

5. Verify production HTML.

   After redeploy, the live page should contain `voice-orb` and should not contain `127.0.0.1`.

## Hardening Recommendations

These are implementation recommendations only; I did not change code.

1. Make `scripts/update_vercel.py` refuse bad public URLs.

   It should fail before updating Vercel if `PUBLIC_API_URL` is empty, starts with `http://`, contains `127.0.0.1`, contains `localhost`, or does not look like a real public HTTPS URL.

2. Do not persist localhost into `PUBLIC_API_URL` when ngrok fails.

   `run.py` currently can fall back to a local URL. For this workflow, that is dangerous because `PUBLIC_API_URL` is later deployed to Vercel. If ngrok is unavailable, the deploy path should stop instead of writing localhost as the public URL.

3. Make `inject-shopbot.mjs` fail the build if it cannot fetch `shopbot.js`.

   The current fallback creates a broken production site silently. A failed build would be easier to diagnose than a successful deployment with no orb.

4. Remove old inline widget scripts during injection.

   The current cleanup removes old `<script src=".../shopbot.js">` tags, but not previously inlined widget scripts. If a future build starts from HTML that already has an inline widget, stale inline code could remain before the new one.

5. Keep `/admin` excluded from crawling.

   The current `/admin` exclusion prevents the protected admin page from breaking catalog ingestion. A stricter path-based check would be cleaner than a broad substring check, but the current direction is correct.

## Final Diagnosis

Fix the public URL sync first. The current production site is built against `http://127.0.0.1:8001`, while the working widget is available from the active ngrok HTTPS URL forwarding to local port `8002`. Once Vercel is redeployed with the active ngrok URL and the build inlines `shopbot.js`, the voice orb should render again.
