# AI Salesman Plugin - Project Overview & Status

Date: 2026-06-17

Current fallback milestone: **L7** (`L 7` GitHub sync comment).

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
- **Legacy Local Supervisor**: `python run.py` can still launch Caddy, the storefront, and backend for local fallback testing, but Docker is now the preferred HUB startup path.
- **Modular Deployment Modes**: Persistence and setup scripts for `intranet` (LAN Wi-Fi testing) and `public-ip` modes.
- **Voice-Cart Integrations**:
  - Storefront resolves both catalog handles and numeric backend IDs.
  - Large product IDs are serialized as JSON strings to prevent JS precision loss.
  - Interactive actions handled: `ADD_TO_CART`, `NAVIGATE_TO`, `CLEAR_CART`, `CHECKOUT`, `SHOW_PRODUCTS`, `FILTER_PRODUCTS`, `SHOW_PRODUCT_DETAIL`, `SORT_PRODUCTS`.
- **Voice Widget UI**: Clear/reset of conversation history, displaying `Listening...` and `Analyzing...` state indicators.
- **Checkout Process**: Invoice PDF generation verified using `reportlab`.
- **Security Hardening**: Same-origin restrictions and security headers (CSP, HSTS, Frame Options).
- **Multi-tenant isolation**: Sites schema separation backed by `tenant_ai_kart`.
- **Crawler Stabilization**: Incremental vectorization of new catalog items only, with startup crawler sync.
- **One-Time Homepage Greeting**: The injected widget auto-greets only once per browser tab/session and only on the homepage.
- **Exact Named Product Retrieval**: Product names mentioned by the customer are matched directly against the catalog and merged into RAG context, preventing misses on short names like `NOVA Sticker`.
- **Turn Transport Logging**: Completed turns print readable `AI_CONVO | user`, `AI_CONVO | ai_reply`, `AI_CONVO | method_used`, and compact `[SHOPBOT TURN]` lines with transport, elapsed time, action count, transcript, and response.
- **Admin Boundary Cleanup**: AI HUB no longer injects or prints client admin UI; demo admin/product editing belongs to `Vercel_website`.
- **Customer-Site Standalone Mode**: `Vercel_website` is now a React/Vite storefront plus FastAPI/SQLite backend. The customer website remains external to the Hub and its own admin/product management is not part of AI Hub CRM.
- **One-Line Hosted Adapter Contract**: Client websites still paste exactly one script tag. Adapter behavior lives inside HUB-hosted `shopbot.js`; client website source code should not be edited for AI action fixes.
- **HUB-Side Product Detail Routing**: `plugin/src/productResolver.js` resolves backend numeric product IDs to real same-origin product pages by checking HUB products and host catalog endpoints before falling back to client hooks. This prevents bad routes like `/product/<numeric_backend_id>/`.
- **AI Hub CRM**: `/crm` manages clients, enables/disables the widget, triggers crawls, shows tenant catalog status, usage, conversations, settings, adapters, and health.
- **CRM Conversation Storage**: Voice turns are saved with session ID, transcript, AI reply, intent, estimated tokens, and latency so sessions can be reviewed date-wise.
- **CRM Analytics Cleanup**: Analytics now uses catalog-backed product mention detection. `Most mentioned products` contains product names only, not filler words like `yaar`, verbs, pronouns, or generic conversation terms.
- **Store-Manager Summary**: CRM summaries are readable bullet points focused on demand, stock decisions, and operations. OpenAI can generate the summary when configured; otherwise the HUB returns a deterministic heuristic summary.
- **Docker Hub Startup**: `docker compose up -d --build` runs the HUB app, CRM, widget host, Nginx, PostgreSQL, and pgvector. The client website remains external and is started by the client or by the separate `Vercel_website` simulator for local testing.
- **CRM Option-3 Dashboard Refresh**: Dashboard now uses the store-manager analytics layout with a purple sidebar, compact KPI cards, sparklines, intent donut, product-demand bars, active clients, recent activity, light/dark mode, and a simplified header that keeps only the range selector.
- **Clickable Dashboard Routing**: Dashboard KPI cards and panels route to their detailed tabs: Conversations, Catalogs, Usage, Analytics, Clients, and Client detail. The brand block routes back to Dashboard.
- **React CRM Build**: The Hub CRM frontend is now a React/Vite/TypeScript/Tailwind app under `crm/`. Docker builds `crm/dist` automatically, and FastAPI serves the compiled bundle at `/crm`.
- **CRM Token Screen**: The React CRM now handles `CRM_ADMIN_TOKEN` with an in-app token screen and load-error state instead of parallel browser prompt loops.
- **AI-KART API Catalog Crawl**: The crawler now tries `/api/products` before legacy JSON and platform catalog endpoints, matching the rebuilt React/FastAPI AI-KART storefront.
- **Crawler Schedule Defaults**: Docker defaults run a startup crawl and then a periodic crawl every 120 seconds, while CRM still provides a manual per-client `Crawl now` action.
- **Pure Spoke Website Contract**: `Vercel_website` no longer renders its own Voice Orb or injects Hub script through frontend env vars. The Hub connection is only the manually pasted one-line script.
- **Client Website Admin**: `Vercel_website` owns customer login/signup, store admin users, product add/delete, and local product image uploads.
- **Client Panel Scaffold**: `client_panel` is now a separate React/Vite client portal using scoped `/v1/client-panel/*` Hub APIs for client-only analytics, usage, conversations, and per-shopper token policy.


---

## Deployment Architecture

### Public Deployment Reference: One DigitalOcean IP

Current target server:
- Public IP: `143.198.5.97`
- AI-KART storefront: PM2 app, expected local upstream `http://127.0.0.1:5175`
- AI Hub: Docker Compose app, expected local upstream `http://127.0.0.1:5176`
- Nginx is the public entrypoint on `80` and, when enabled, `443`.

Important rule: one public IP plus one public port can only receive one default `/` request. Browser requests to `http://143.198.5.97/` do not include the internal upstream port, so Nginx cannot know whether to send that request to `5175` or `5176` unless the request differs by hostname, path, or public port.

#### Option 1: DNS + Hostname Routing (Best)

Use when DNS is available:
- `aikart.ergobite.com -> 143.198.5.97`
- `aihub.ergobite.com -> 143.198.5.97`
- `panel.ergobite.com -> 143.198.5.97`

All records can point to the same IP. Nginx separates traffic by the `Host` header:
- `https://aikart.ergobite.com/` proxies to `127.0.0.1:5175`
- `https://aihub.ergobite.com/` proxies to `127.0.0.1:5176`
- `https://panel.ergobite.com/` proxies to `127.0.0.1:5177`

This is the cleanest production setup because Let's Encrypt certificates are normal, auto-renewal is reliable, URLs are clean, and browser microphone access works over HTTPS.

#### Option 2: Same IP + Path Routing (Current No-DNS Setup)

Use when there is no DNS yet and AI-KART owns the root storefront path:
- `http://143.198.5.97/` proxies to `127.0.0.1:5175`
- `http://143.198.5.97/api/` proxies to the AI-KART backend at `127.0.0.1:8000`
- `http://143.198.5.97/aihub/` proxies to `127.0.0.1:5176`
- `http://143.198.5.97/aihub/crm/` opens the AI Hub CRM
- `http://143.198.5.97/client-panel/<client_id>` proxies to `127.0.0.1:5177`

This works on one IP and the standard web port because AI-KART uses `/` and `/api/`, AI Hub uses `/aihub/`, and Client Panel uses `/client-panel/<client_id>`. Current client URL is `/client-panel/ai_kart`.

For microphone support, this same setup must be moved to HTTPS:
- `https://143.198.5.97/`
- `https://143.198.5.97/aihub/`
- `https://143.198.5.97/client-panel/ai_kart`

Chrome allows microphone access only on secure contexts such as HTTPS or localhost. Public plain HTTP will load the pages, but the mic button will not work correctly.

#### Option 3: Same IP + Different Public Ports

Use only for quick testing:
- `http://143.198.5.97:7001/` proxies to `127.0.0.1:5175`
- `http://143.198.5.97:7002/` proxies to `127.0.0.1:5176`

This can work if Nginx listens on `7001` and `7002` and the DigitalOcean cloud firewall allows those inbound TCP ports. If the browser times out while local server checks return `200`, the cloud firewall or provider networking is blocking the public port. This option is less user-friendly, often blocked on networks, and still needs HTTPS for microphone access.

#### Current Recommended Path

For this project, use Option 2 until DNS is ready:
1. Deploy AI Hub first and confirm `http://127.0.0.1:5176/health` returns `200` on the server.
2. Deploy AI-KART second and confirm its local upstream responds on `127.0.0.1:5175`.
3. Deploy Client Panel third and confirm its local upstream responds on `127.0.0.1:5177`.
4. Configure the shared Nginx edge routing from `Vercel_website/aikart.md` for `/`, `/api/`, `/aihub/`, and `/client-panel/`.
5. Add HTTPS for the IP address or switch to Option 1 with DNS and normal Let's Encrypt certificates.

### Mode Configuration
Controlled via `DEPLOYMENT_MODE` in `.env`:
- `intranet` (Current): LAN testing at `https://192.168.68.51:8484`.
- `public-ip`: Binds storefront and API endpoints directly to a global static IP.
- `domain`: Maps standard domain name (e.g., `example.com`) to public IP.

### Port Mappings (Intranet Mode)
- **Docker Nginx HTTPS Entry**: `8484` (HUB CRM, widget, and `/v1/*` APIs)
- **Legacy `run.py` HTTPS Entry**: Caddy can still be used for local full-stack simulation.
- **Local Spoke Storefront Private**: `8584`
- **FastAPI Backend Private**: `8585`
- **Postgres Database**: `5434`

---

### Manual Smoke Test Checklist
1. Start HUB Docker stack: `docker compose up -d --build`.
2. Start the client simulator separately from `C:/Users/admin/Desktop/Vercel_website` when testing AI-KART locally.
3. Open CRM: `https://192.168.68.51:8484/crm`.
4. Open the separately hosted client site URL, such as `http://127.0.0.1:8584` for the local AI-KART simulator, and verify the widget renders from the pasted HUB script.
5. In CRM Analytics, confirm `Most mentioned products` contains catalog product names only.
6. Confirm CRM summary is bullet-style store-manager guidance.
7. In CRM Dashboard, confirm the header shows `Store Manager Analytics` with only the range selector; changing the range updates the range-backed cards and panels.
8. Click CRM Dashboard cards/panels and confirm they route to Conversations, Catalogs, Usage, Analytics, Clients, and Client detail.
9. Toggle CRM dark mode and confirm the option-3 dashboard remains readable.
10. Test greetings: Say "hello" or "hi" (verify conversational greeting response).
11. Search products: Say "show me mugs" (verify recommendation panel filters grid).
12. Cart: Say "add bomber jacket to cart" (verify item added and drawer opens).
13. Confirm terminal turn summary prints after a voice turn, including `AI_CONVO | user`, `AI_CONVO | ai_reply`, `method_used: ...`, `time_taken: ...ms`, and `[SHOPBOT TURN] transport=...`.

---

## Voice Transport Status

The active widget voice path is the legacy turn-based HTTP flow:
1. Browser records one `audio.webm` blob with `MediaRecorder`.
2. Widget posts the blob to `POST /v1/shop` with `site_id` and conversation history.
3. Backend returns transcript, response text, optional `audio_b64`, and `ui_actions`.
4. Widget plays the returned audio and executes storefront actions.

---

## L7 - Fallback Point (Milestone)
**Date:** 2026-06-17
**Status:** Stable Fallback
**GitHub Sync Comment:** `L 7`

This is the current rollback point after L5. If future changes break the React CRM, Docker Hub build, crawler sync, analytics, or one-script client setup, revert to the GitHub state synced with comment `L 7`.

**What L7 locks in:**
- **React CRM:** The old monolithic `crm/app.js` and `crm/styles.css` frontend is replaced by a React/Vite/TypeScript/Tailwind CRM app under `crm/src`.
- **Docker-Built CRM:** The Hub Docker image builds `crm/dist` in a Node build stage and FastAPI serves the compiled CRM at `/crm`.
- **Admin Boundary Preserved:** AI Hub CRM manages clients, crawling, catalog visibility, usage, analytics, settings, adapters, health, and widget enablement. Client storefront/product admin remains on the client website.
- **Crawler API Compatibility:** The Hub crawler supports the rebuilt AI-KART catalog endpoint `GET /api/products`, plus legacy `/api/products.json`, `/products.json`, Shopify, and WooCommerce endpoints.
- **Crawler Schedule:** Docker defaults to `CRAWL_ON_STARTUP=true` and `CRAWL_PERIODIC_ENABLED=true`, so the Hub crawls once before startup completes and then refreshes every 120 seconds. Manual CRM crawl remains available.
- **Root AI-KART Deployment:** Current public no-DNS deployment serves AI-KART at `http://143.198.5.97/` and AI Hub at `http://143.198.5.97/aihub/`.
- **Verification:** Backend tests pass, the CRM builds/lints, the AI-KART frontend builds/lints, Docker image build passes, and a local crawl against `http://143.198.5.97/` imports `NOVA Dog Sweater` successfully.

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
- **AI-Enabled Spoke Simulation:** `Vercel_website` is treated like a customer site. In manual-paste mode, `out/index.html` keeps the absolute HUB `shopbot.js` script and the server preserves that pasted tag when serving HTML.
- **Static HTML Script Handling:** Build/request-time helpers remove generated inline/stub widget scripts, but they must preserve a manually pasted external `shopbot.js` script. Manual embed is the expected AI-KART local simulator mode.
- **One-Script Client Contract:** Real client websites still only need one script tag; site-specific cart/search/checkout behavior belongs in HUB-hosted adapters.
- **Reliable Terminal Turn Logs:** Each completed turn prints the user text, AI reply, method used (`websocket`, `legacy-http`, `legacy-sse`, or `legacy-ws`), status, time taken, pipeline time when available, action count, and compact `[SHOPBOT TURN]` summary.
- **L3.5 Browser Smoke:** Standalone Vercel smoke verified no AI script/orb, admin link present, `/admin` responds, and search for `sticker` renders `NOVA Rainbow Sticker` and `NOVA Sticker` from `products.json`.
- **L3.5 Injection Smoke:** AI-enabled Vercel mode verified exactly one `shopbot.js?site=ai_kart` script in the HTML response.

Expected terminal log shape:

```text
AI_CONVO | user: show me caps
AI_CONVO | ai_reply: Here are two cap options.
AI_CONVO | method_used: websocket | status: ok | time_taken: 1842ms | pipeline: 1750ms | actions: 1
[SHOPBOT TURN] transport=websocket status=ok site=ai_kart elapsed=1842ms pipeline=1750ms actions=1 transcript="show me caps" response="Here are two cap options."
```

---

## L5 - Fallback Point (Milestone)
**Date:** 2026-06-15
**Status:** Stable Fallback
**GitHub Sync Comment:** `L 5`

This was the rollback point after L4.0. If future changes break the Docker-first HUB, CRM, analytics, or one-script client setup, revert to the GitHub state synced with comment `L 5`.

**What L5 locks in:**
- **Docker-First HUB Startup:** `docker compose up -d --build` runs the HUB app, CRM, widget host, crawler/RAG APIs, Nginx, PostgreSQL, and pgvector.
- **External Client Website Boundary:** The client website is not part of the HUB Docker stack. For AI-KART testing, `Vercel_website` is started separately; in production, the client runs their own site.
- **One-Line Client Contract Preserved:** Real client websites paste one script tag only. Client source code should not be edited for HUB adapter or CRM fixes.
- **CRM Admin Surface:** `/crm` manages clients, widget enable/disable, crawler triggers, tenant catalog visibility, usage, date-wise conversations, analytics, settings, adapters, and health.
- **Session And Usage Tracking:** Conversation turns are stored with session ID, transcript, AI reply, intent, estimated tokens, latency, and quota context.
- **Product-Only Analytics:** `Most mentioned products` is catalog-backed and contains product names only, not filler words, pronouns, verbs, greetings, or casual phrases.
- **Store-Manager Summaries:** CRM summaries are bullet points focused on customer demand, stock decisions, and operations. OpenAI generation is optional; deterministic summaries remain available without `OPENAI_API_KEY`.
- **Nginx Docker Proxy:** Docker uses Nginx for the HUB HTTPS/LAN proxy path. The older `run.py`/Caddy route remains a legacy local fallback.

---

## L4.0 - Fallback Point (Milestone)
**Date:** 2026-06-15
**Status:** Stable Fallback
**GitHub Sync Comment:** `L 4.0`

This is the new rollback point after L3.5. If future changes break the one-script HUB/spoke setup, revert to the GitHub state synced with comment `L 4.0`.

**What L4.0 locks in:**
- **One-Line Client Contract Preserved:** Real client websites paste one script tag only. They should not paste a second adapter/hook block for normal operation.
- **Hosted Adapter Ownership:** Product routing, product overlay behavior, browser navigation, cart hook delegation, and event fallback are owned by HUB-hosted `shopbot.js`.
- **No Client Website Source Edits For Adapter Fixes:** The AI-KART spoke simulator can be used for testing, but adapter fixes belong in `AI_salesman_plugin/plugin/src/*` and the rebuilt `plugin/shopbot.js`.
- **Product Detail Resolver:** Added `plugin/src/productResolver.js`, which resolves `SHOW_PRODUCT_DETAIL` actions from backend numeric IDs to real same-origin product URLs by checking HUB product data and common host catalog endpoints such as `/api/products`, `/api/products.json`, `/products.json`, and `/collections/all/products.json`.
- **Numeric Route Guard:** The hosted adapter does not fabricate product URLs from numeric backend IDs, preventing routes such as `/product/4483885457220840101/`.
- **Bundle Rebuild Requirement:** Changes under `plugin/src` must be rebuilt with `cd plugin && npm run build` so `/shopbot.js` serves the current adapter.
- **README Refactor:** README now documents installation, full dependency list, environment setup, run modes, one-line script contract, tests, and troubleshooting.

Current AI-KART intranet one-line script:

```html
<script defer src="https://192.168.68.51:8484/shopbot.js?site=ai_kart" data-site-id="ai_kart"></script>
```

---

## Post-L7 Hub-Spoke Direction

**HUB:** `AI_salesman_plugin` owns the AI pipeline, RAG, STT, LLM, TTS, widget script, adapters, and optional WebSocket transport.

**SPOKE:** Client websites only paste one script tag. They should not paste a second hook/config block. Any site-specific cart/search/checkout behavior belongs in our hosted widget adapter layer.

**CRM:** The HUB now includes an admin CRM at `/crm` for client management, tenant catalog visibility, crawler triggers, usage tracking, date-wise conversations, analytics, settings, adapters, and health. This is a HUB admin surface; it is not client website code.

CRM analytics rules:
- Dashboard should stay navigation-first: the header keeps the range selector, and summary generation stays in the Analytics tab.
- Dashboard metrics and panels should respect the selected analytics range where range-scoped data exists.
- Dashboard cards and panels should be clickable entry points into the detailed CRM tabs.
- `Most mentioned products` must contain product names from the tenant catalog only.
- Non-product transcript words such as filler words, pronouns, verbs, greetings, and casual phrases must not appear as demand signals.
- Summaries should read like store-manager notes: what customers are looking for, what to stock, and what operations need attention.
- OpenAI summary generation is optional; deterministic heuristic summaries remain available when `OPENAI_API_KEY` is not configured.

Current one-script spoke contract:

```html
<script defer src="https://hub.example.com/shopbot.js?site=client_site_id" data-site-id="client_site_id"></script>
```

For intranet AI-KART testing, the local customer-site simulator runs as its own React/FastAPI app:

Backend:

```powershell
cd C:\Users\admin\Desktop\Vercel_website
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd C:\Users\admin\Desktop\Vercel_website
cd frontend
npm run dev
```

The client website has no built-in Hub URL and renders no local mic. To connect it, paste one client-style script into `frontend/index.html`:

```html
<script defer src="https://192.168.68.51:8484/shopbot.js?site=ai_kart" data-site-id="ai_kart"></script>
```

No pasted script means no mic. If AI Hub CRM disables the client, the served script is disabled and the mic is removed. Do not use `127.0.0.1:8584` as the Docker crawler URL; Docker must crawl the local simulator through `http://host.docker.internal:8584`.

The legacy AI HUB `run.py` path can still run the full intranet stack behind Caddy: `/crm`, `/shopbot.js`, `/shopbot-widget.js`, `/shopbot-frame`, `/v1/*`, and `/health` route to the HUB backend; normal website pages route to the SPOKE storefront. `run.py` prints and auto-opens the CRM URL unless `AUTO_OPEN_CRM=false`.

Docker/EC2 direction:
- `docker compose up -d --build` runs the HUB app, CRM, widget host, crawler/RAG APIs, Nginx, PostgreSQL, and pgvector.
- The client website is external to this Docker stack. For local AI-KART testing, start `Vercel_website` manually; in production, the client runs their own website.
- `scripts/start_crm.ps1` is the local Windows launcher that starts Docker and opens `https://localhost:8484/crm`.
- On EC2, Docker exposes the CRM and widget origin; a remote admin opens `https://your-hub-domain.com/crm` from their own browser.
- Use `HUB_PUBLIC_URL` for the browser-visible HUB domain and `CLIENT_STORE_URL` for the client website being crawled. In local Docker AI-KART testing, keep `CLIENT_STORE_URL=http://host.docker.internal:8584`.
- Docker defaults `CRAWL_ON_STARTUP=true` and `CRAWL_PERIODIC_ENABLED=true`, so the Hub crawls once before startup completes and then refreshes every 120 seconds. The CRM also keeps a manual per-client crawl button.
- The CRM `Add client` flow creates the client record, tenant schema, script tag, and crawler entrypoint without editing client website source.
- CRM analytics can be checked through the Docker-served API at `/v1/admin/analytics?range=7d`; it should return `summary`, `top_products`, `top_intents`, and trend `series`.

Transport status:
- `POST /v1/shop` remains the stable fallback and must not be broken.
- `/v1/ws/shop` is now available as an optional WebSocket transport.
- The widget tries WebSocket first when enabled and automatically falls back to HTTP after connection failure.
- Current WebSocket implementation streams protocol stages safely; true LLM token streaming can be improved later after the JSON/action response contract is split cleanly.

Crawler/RAG ingestion status:
- Crawl4AI remains the HTML renderer for public pages.
- Before rendering pages, the HUB now tries common catalog APIs: `/api/products`, `/api/products.json`, `/products.json`, Shopify collection product JSON, and WooCommerce Store API product endpoints.
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

The reusable client-facing template now lives at `docs/client-embed-snippet.html`. For the customer-style simulation, `Vercel_website` is treated like a client's site: standalone mode can run without the widget, while manual-paste AI mode keeps exactly one external hosted `shopbot.js` script in the client HTML.

### Works With Script-Only Setup
These do not require editing the client's website code beyond adding our script tag:

- **Voice Orb UI:** Floating mic button, listening/analyzing states, voice recording, AI response playback.
- **Voice Conversation:** STT, LLM response, TTS audio, conversation history, greetings, product Q&A, comparison explanations, and general shopping guidance.
- **Catalog-Aware Answers:** Works if we can crawl/import the client's catalog into our backend using their public website, sitemap, product feed, Shopify/WooCommerce API, CSV, or admin upload.
- **Product Recommendations in Speech/Text:** AI can recommend products from the client's catalog and speak the answer.
- **Simple Page Navigation:** AI can navigate by setting `window.location.href` for known pages like home, support, FAQ, shipping, returns, category pages, or product pages if we know the URLs.
- **Lead Capture / Assisted Support:** We can collect name, phone/email, preferences, address, or intent in conversation and store it in our backend, if legally/contractually allowed.
- **Analytics on AI Usage:** We can log transcripts, intents, product-only demand signals, failed searches, estimated tokens, latency, and conversion intent on our backend.
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
