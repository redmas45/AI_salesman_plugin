# AI Salesman Plugin - Project Overview & Status

Date: 2026-06-12

Current fallback milestone: **L3.5** (`L 3.5` GitHub sync comment).

## About the Project
An AI-powered voice shopping assistant ("Voice Orb") injected into the storefront (`AI-KART`). It uses natural language processing (LLM), Text-To-Speech (TTS), Speech-To-Text (STT), and Retrieval-Augmented Generation (RAG) to recommend products, answer customer queries, and execute storefront actions (e.g., adding to cart, navigating, checkout).

---

## Core Components

1. **Voice Orb Widget (Frontend / Injected Script)**
   - **Location**: `plugin/shopbot.js`
   - **Purpose**: Glassmorphic UI element injected onto the storefront. Streams recorded user voice via browser Media API to the backend and handles returning UI action events.
2. **FastAPI Backend (`api/main.py`)**
   - **Location**: `api/main.py`, `run.py`
   - **Purpose**: Runs private API on `127.0.0.1:8585` (proxied same-origin by storefront on `:8484` or `:8584`).
3. **AI Orchestrator & Agents (`agent/`)**
   - **Location**: `agent/orchestrator.py`, `agent/prompt.py`
   - **Purpose**: Connects STT, LLM (with system prompt in `prompt.py`), and TTS.
4. **RAG Database & Ingestion (`db/` & `agent/ingestion.py`)**
   - **Location**: `db/database.py`, `agent/ingestion.py`
   - **Purpose**: Crawls the catalog, calculates embeddings, and runs semantic search in PostgreSQL (pgvector).
5. **Local Spoke Simulator (`Vercel_website/`)**
   - **Location**: `C:/Users/admin/Desktop/Vercel_website`
   - **Purpose**: Local customer-site simulator for AI-KART. This is not part of the reusable AI HUB.

---

## Current Status Overview

### What is Fixed & Working ✅
- **BOM in `.env` (STT Pipeline Heart)**: Resolved a critical pipeline blocker where `OPENAI_API_KEY` was not loaded due to a Byte Order Mark (`\ufeff`) in the `.env` file, causing transcription failures. Stripped the BOM from `.env` and added a robust fallback in `config.py`.
- **Microphone Z-Index Layering**: Changed `#shopbot-widget` z-index to `2147483647` (the absolute maximum possible CSS z-index) to guarantee the Voice Orb and mic button always float above storefront overlays, drawers, and panels.
- **Side-by-Side Product Comparison ("Stat Card")**: Added a premium comparative layout for `SHOW_COMPARISON` intent, displaying compared items side-by-side with matched attributes (Price, Brand, Category, Description) and direct "Add to Cart" actions.
- **Detail-Page Product Auto-Inclusion**: Automatically detects if the customer is on a product details view and prepends the currently viewed product to the comparison grid.
- **Comparison UI Squeezing Fix**: Refactored the results overlay element to use a direct flex-row flow during comparisons to prevent nested containers from adding horizontal or vertical scrollbars to compared product cards.
- **Single-Command Startup**: `python run.py` launches Caddy, the storefront, and backend in a unified supervisor loop.
- **Modular Deployment Modes**: Persistence and setup scripts for `intranet` (LAN Wi-Fi testing) and `public-ip` modes.
- **Voice-Cart Integrations**:
  - Storefront resolves both catalog handles and numeric backend IDs.
  - Large product IDs are serialized as JSON strings to prevent JS precision loss.
  - Interactive actions handled: `ADD_TO_CART`, `NAVIGATE_TO`, `CLEAR_CART`, `CHECKOUT`, `SHOW_PRODUCTS`, `FILTER_PRODUCTS`, `SHOW_PRODUCT_DETAIL`, `SORT_PRODUCTS`.
- **Voice Widget UI**: Clear/reset of conversation history, displaying `Listening...` and `Analyzing...` state indicators.
- **Checkout Process**: Invoice PDF generation verified using `reportlab`.
- **Security Hardening**: Same-origin restrictions and security headers (CSP, HSTS, Frame Options).
- **Multi-tenant isolation**: Sites schema separation backed by `tenant_ai_kart_main`.
- **Crawler Stabilization**: Incremental vectorization of new catalog items only, with startup crawler sync.
- **One-Time Homepage Greeting**: The injected widget auto-greets only once per browser tab/session and only on the homepage.
- **Exact Named Product Retrieval**: Product names mentioned by the customer are matched directly against the catalog and merged into RAG context, preventing misses on short names like `NOVA Sticker`.
- **Turn Transport Logging**: Completed turns print readable `AI_CONVO | user`, `AI_CONVO | ai_reply`, `AI_CONVO | method_used`, and compact `[SHOPBOT TURN]` lines with transport, elapsed time, action count, transcript, and response.
- **Admin Boundary Cleanup**: AI HUB no longer injects or prints client admin UI; demo admin/product editing belongs to `Vercel_website`.
- **Customer-Site Standalone Mode**: `Vercel_website/run.py` runs the storefront/admin without the AI widget by default. Its search bar uses `out/api/products.json` directly and does not depend on the Voice Orb.


---

## Deployment Architecture

### Mode Configuration
Controlled via `DEPLOYMENT_MODE` in `.env`:
- `intranet` (Current): LAN testing at `https://192.168.68.71:8484`.
- `public-ip`: Binds storefront and API endpoints directly to a global static IP.
- `domain`: Maps standard domain name (e.g., `example.com`) to public IP.

### Port Mappings (Intranet Mode)
- **Caddy HTTPS Entry**: `8484` (Proxies all traffic to storefront)
- **Local Spoke Storefront Private**: `8584`
- **FastAPI Backend Private**: `8585`
- **Postgres Database**: `5434`

---

### Manual Smoke Test Checklist
1. Start stack: `python run.py`
2. Open storefront: `https://192.168.68.71:8484` (verify widget renders).
3. Test greetings: Say "hello" or "hi" (verify conversational greeting response).
4. Search products: Say "show me mugs" (verify recommendation panel filters grid).
5. Cart: Say "add bomber jacket to cart" (verify item added and drawer opens).
6. Confirm terminal turn summary prints after a voice turn, including `AI_CONVO | user`, `AI_CONVO | ai_reply`, `method_used: ...`, `time_taken: ...ms`, and `[SHOPBOT TURN] transport=...`.

---

## Voice Transport Status

The active widget voice path is the legacy turn-based HTTP flow:
1. Browser records one `audio.webm` blob with `MediaRecorder`.
2. Widget posts the blob to `POST /v1/shop` with `site_id` and conversation history.
3. Backend returns transcript, response text, optional `audio_b64`, and `ui_actions`.
4. Widget plays the returned audio and executes storefront actions.

---

## L3 - Fallback Point (Milestone)
**Date:** 2026-06-12
**Status:** Stable Fallback
**GitHub Sync Comment:** `L3`

The current GitHub-synced state of both `AI_salesman_plugin` and `Vercel_website`, committed/synced with comment `L3`, is our **L3 Fallback Point**. If future modifications break the system, revert to this state first before debugging forward.

**Key achievements in this milestone:**
- **Crawler Automation & Logging:** Implemented auto-schedule (2 mins) and terminal logging in `agent/ingestion.py`.
- **Local Spoke Admin Enhancements:** Admin/product-editing work belongs to `Vercel_website`, not the reusable AI HUB.
- **Frontend Polish:** Stripped useless statistics, cleaned up header nav (auto-hiding category links), overhauled footer with new links and boilerplate pages, and fixed static text-search filtering.
- **Premium Invoices:** Redesigned PDF generation in `api/main.py` using `reportlab` with premium styling (custom border, styled headers, and tables).
- **Checkout Action:** Wired up `CHECKOUT` UI action in frontend (`cart.js`) to securely hit the backend checkout API, generate the PDF invoice, and download it locally.
- **Syntax Fixes:** Fixed f-string javascript injection bugs in `Vercel_website/api/index.py` that caused startup crashes.
- **Support Navigation:** AI can navigate to `support`, `frequently-asked-questions`, `shipping-policy`, and `return-policy`; guardrails now allow these routes.
- **Search Integration:** Fixed the broken `/search/?q=...` path. Post-L3, the standalone customer storefront search reads `products.json`; AI product panels are triggered by the HUB widget actions, not by the normal website search bar.
- **Product Page Dark Theme:** Product pages force dark mode and high-contrast text; browser testing measured product title contrast at about `19.4:1`.
- **Rogue Scrollbar Fix:** Hidden empty template sidebars and hidden `#shopbot-msgs` scrollbars.

---

## L3.5 - Fallback Point (Milestone)
**Date:** 2026-06-12
**Status:** Stable Fallback
**GitHub Sync Comment:** `L 3.5`

This is the new rollback point after L3. If future changes break the hub/spoke setup, revert to the GitHub state synced with comment `L 3.5`.

**What L3.5 locks in:**
- **Clean HUB/SPOKE Split:** `AI_salesman_plugin` is the AI HUB. `Vercel_website` is a customer/spoke simulator with its own admin and standalone search.
- **Customer Website Standalone Mode:** Running `python run.py` inside `Vercel_website` starts the website/admin without AI injection. The normal search bar uses `out/api/products.json`.
- **AI-Enabled Spoke Simulation:** `Vercel_website/run.py` injects exactly one hosted `shopbot.js` script only when `ENABLE_AI_WIDGET=true` and `SHOPBOT_HUB_ORIGIN` is set.
- **Static HTML Scrubbing:** `Vercel_website/out/*.html` is clean by default; stale `shopbot.js` and disabled-widget stubs are removed during build and stripped at request time when injection is off.
- **One-Script Client Contract:** Real client websites still only need one script tag; site-specific cart/search/checkout behavior belongs in HUB-hosted adapters.
- **Reliable Terminal Turn Logs:** Each completed turn prints the user text, AI reply, method used (`websocket`, `legacy-http`, `legacy-sse`, or `legacy-ws`), status, time taken, pipeline time when available, action count, and compact `[SHOPBOT TURN]` summary.
- **L3.5 Browser Smoke:** Standalone Vercel smoke verified no AI script/orb, admin link present, `/admin` responds, and search for `sticker` renders `NOVA Rainbow Sticker` and `NOVA Sticker` from `products.json`.
- **L3.5 Injection Smoke:** AI-enabled Vercel mode verified exactly one `shopbot.js?site=ai_kart_main` script in the HTML response.

Expected terminal log shape:

```text
AI_CONVO | user: show me caps
AI_CONVO | ai_reply: Here are two cap options.
AI_CONVO | method_used: websocket | status: ok | time_taken: 1842ms | pipeline: 1750ms | actions: 1
[SHOPBOT TURN] transport=websocket status=ok site=ai_kart_main elapsed=1842ms pipeline=1750ms actions=1 transcript="show me caps" response="Here are two cap options."
```

---

## Post-L3 Hub-Spoke Direction

**HUB:** `AI_salesman_plugin` owns the AI pipeline, RAG, STT, LLM, TTS, widget script, adapters, and optional WebSocket transport.

**SPOKE:** Client websites only paste one script tag. They should not paste a second hook/config block. Any site-specific cart/search/checkout behavior belongs in our hosted widget adapter layer.

Current one-script spoke contract:

```html
<script defer src="https://hub.example.com/shopbot.js?site=client_site_id" data-site-id="client_site_id"></script>
```

For intranet AI-KART testing, static `Vercel_website/out/*.html` no longer contains a baked-in AI embed. The local customer-site simulator can run in two modes:

Standalone customer site:

```powershell
cd C:\Users\admin\Desktop\Vercel_website
python run.py
```

This serves the storefront/admin and normal `products.json` search with no Voice Orb script.

AI-enabled customer simulation:

```powershell
cd C:\Users\admin\Desktop\Vercel_website
$env:ENABLE_AI_WIDGET="true"
$env:SHOPBOT_HUB_ORIGIN="http://127.0.0.1:8585"
python run.py
```

This injects one client-style script at request time:

```html
<script defer src="http://127.0.0.1:8585/shopbot.js?site=ai_kart_main" data-site-id="ai_kart_main" data-brand="AI-KART"></script>
```

The AI HUB `run.py` can still run the full intranet stack behind Caddy: `/shopbot.js`, `/shopbot-widget.js`, `/shopbot-frame`, `/v1/*`, and `/health` route to the HUB backend; normal website pages route to the SPOKE storefront.

Transport status:
- `POST /v1/shop` remains the stable fallback and must not be broken.
- `/v1/ws/shop` is now available as an optional WebSocket transport.
- The widget tries WebSocket first when enabled and automatically falls back to HTTP after connection failure.
- Current WebSocket implementation streams protocol stages safely; true LLM token streaming can be improved later after the JSON/action response contract is split cleanly.

Crawler/RAG ingestion status:
- Crawl4AI remains the HTML renderer for public pages.
- Before rendering pages, the HUB now tries common catalog APIs: `/api/products.json`, `/products.json`, Shopify collection product JSON, and WooCommerce Store API product endpoints.
- If no catalog API is available, the HUB discovers product URLs from `robots.txt`, sitemap indexes, product sitemaps, and common storefront routes such as `/shop`, `/store`, `/products`, `/catalog`, `/collections`, `/category`, and `/inventory`.
- The crawl queue prioritizes product, shop, catalog, category, collection, store, and inventory URLs while avoiding admin, login, cart, checkout, account, and static asset URLs.
- Product extraction supports JSON-LD, Next.js data, React/Next flight payloads, embedded app-state JSON, Shopify product shapes, WooCommerce product shapes, and fallback visible-text heuristics.
- This still cannot crawl private/login-only inventory or endpoints blocked by auth; those require a feed, API key, CSV/admin upload, or client-approved platform adapter.

## Client Website Integration: One Script vs Adapter Work

### Goal
For a client website, the cleanest sales pitch is exactly one pasted script tag:

```html
<script defer src="https://hub.example.com/shopbot.js?site=client_site_id" data-site-id="client_site_id"></script>
```

With that one script, the Voice Orb appears on the client's page and talks to our HUB backend. Client-specific behavior must be handled inside our hosted widget/adapters or by APIs already present on the client site. We should not ask the client to paste a second hook block.

The reusable client-facing template now lives at `docs/client-embed-snippet.html`. For the customer-style simulation, `Vercel_website` is treated like a client's site: static `out/*.html` stays free of AI scripts in standalone mode, and AI mode injects exactly one hosted `shopbot.js` script at request time.

### Works With Script-Only Setup
These do not require editing the client's website code beyond adding our script tag:

- **Voice Orb UI:** Floating mic button, listening/analyzing states, voice recording, AI response playback.
- **Voice Conversation:** STT, LLM response, TTS audio, conversation history, greetings, product Q&A, comparison explanations, and general shopping guidance.
- **Catalog-Aware Answers:** Works if we can crawl/import the client's catalog into our backend using their public website, sitemap, product feed, Shopify/WooCommerce API, CSV, or admin upload.
- **Product Recommendations in Speech/Text:** AI can recommend products from the client's catalog and speak the answer.
- **Simple Page Navigation:** AI can navigate by setting `window.location.href` for known pages like home, support, FAQ, shipping, returns, category pages, or product pages if we know the URLs.
- **Lead Capture / Assisted Support:** We can collect name, phone/email, preferences, address, or intent in conversation and store it in our backend, if legally/contractually allowed.
- **Analytics on AI Usage:** We can log transcripts, intents, products discussed, failed searches, and conversion intent on our backend.
- **No Native Cart Dependency Mode:** AI can still act as a product advisor even if the site gives us no cart access.

### Works If The Client Already Has Usable Browser APIs
These can work with the same one script when the client site already exposes usable APIs or DOM events that our hosted adapter can call:

- **Native Add to Cart:** Our adapter calls the client's existing cart API, such as `window.ShopCart.addItem`, Shopify cart endpoints, WooCommerce endpoints, or a site-specific adapter.
- **Native Filtering/Search UI:** Our adapter calls existing search/filter APIs or dispatches `shopbot:action` events that the site already handles.
- **Open Native Cart Drawer:** Our adapter calls the client's existing cart open method when available.
- **Show Product Results in Their UI:** Our adapter can render our own overlay, or call existing client result components if exposed.
- **Product Detail Routing:** Our adapter maps our product ID/handle to the client's real product URLs.
- **Checkout Start:** Our adapter starts the client's checkout flow if the site's platform exposes it.

For AI-KART, the current adapter maps actions to `window.ShopCart.addItem`, `window.ShopCart.filterProducts`, `window.ShopCart.open`, `window.location.href`, and `window.ShopCart.checkout`. On a real client website, those mappings move into a site/platform adapter that is served from our HUB.

### Requires Website-Specific Changes Or Adapter Work
These are not reliably possible from a generic script alone:

- **Guaranteed Add to Cart on Any Website:** Every platform has different cart APIs, button structures, variant IDs, CSRF tokens, and checkout rules.
- **Variant Selection:** Size/color/material selections need site-specific product data and UI/cart mapping.
- **Real Checkout Completion:** Payment, tax, shipping rates, coupons, and order creation must remain inside the client's commerce platform.
- **Inventory-Safe Cart Mutations:** Requires live stock and platform cart API access.
- **Account/Login Actions:** Requires platform auth integration and explicit security design.
- **Deep SPA State Changes:** React/Next/Vue apps often need official callbacks or route APIs; DOM clicking is fragile.
- **Styling The Client Site's Native UI:** We should not force broad CSS on a client site unless they approve the visual integration.

### Current Practical Client Offering
1. **Basic Plan - Script Only:** Voice Orb, AI product advisor, catalog Q&A, product recommendations, support answers, simple navigation, analytics.
2. **Commerce Plan - One Script + Adapter:** Everything above plus native add-to-cart, open cart, product result rendering, product detail routing, and checkout handoff through a HUB-owned adapter.
3. **Full Integration - Adapter/API Work:** Platform-specific Shopify/WooCommerce/custom cart adapter, variants, live inventory, stronger order/checkout workflows, and polished native UI integration.

### Rule Of Thumb
If the action only needs our AI backend and browser navigation, the generic one script is enough. If the action changes the client's cart, checkout, account, inventory, or native UI state, our HUB script must include or load a site-specific adapter for that client's platform.
