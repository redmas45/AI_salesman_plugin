# AI Salesman Plugin - Project Overview & Status

Date: 2026-06-10

## About the Project
This project is an AI-powered voice shopping assistant ("Voice Orb") that can be injected into any storefront (currently integrated with a Vercel-based demo website). The assistant uses a combination of natural language processing (LLM), Text-To-Speech (TTS), Speech-To-Text (STT), and Retrieval-Augmented Generation (RAG) to understand user intent, answer questions, provide product recommendations, and perform storefront navigation actions like adding items to the cart or checking out. 

## Core Components

### 1. **Voice Orb Widget (Frontend / Injected Script)**
- **Location**: `plugin/shopbot.js`
- **Purpose**: A responsive, glassmorphic UI element injected onto the storefront. It listens to user voice input using the browser's MediaRecorder API, streams the audio to the backend, and processes returning JSON to execute UI actions (e.g. `SHOW_PRODUCTS`, `NAVIGATE_TO`, `ADD_TO_CART`).

### 2. **FastAPI Backend (`api/main.py`)**
- **Location**: `api/main.py`, `run.py`
- **Purpose**: Exposes the `/v1/shop` and WebSocket endpoints. It accepts the audio blob from the widget, passes it to the orchestrator, and returns the LLM response alongside actionable UI commands. 
- **Networking**: `run.py` is the single entry point for the current self-hosted stack. It starts Caddy on `:80/:443`, starts the AI-KART storefront/admin service on `0.0.0.0:8000`, starts the backend privately on `127.0.0.1:8011`, and routes widget/API traffic through the storefront same-origin proxy.

### 3. **AI Orchestrator & Agents (`agent/`)**
- **Location**: `agent/orchestrator.py`, `agent/prompt.py`
- **Purpose**: Connects the STT parser, LLM, and TTS engine. The system prompt (`agent/prompt.py`) rigorously instructs the LLM on how to behave as a cheerful AI assistant. It outputs JSON commands embedded within normal responses.

### 4. **RAG Vector Database & Ingestion (`db/` & `agent/ingestion.py`)**
- **Location**: `db/database.py` (PostgreSQL / pgvector), `agent/ingestion.py`
- **Purpose**: Automatically crawls the target store to fetch product details (Name, Brand, Price, Image, description) and loads them into the DB. It uses `pgvector` to build searchable embeddings so the LLM can lookup items semantically without needing the full catalog loaded in its context.

### 5. **Vercel Storefront Clone (External)**
- **Location**: `C:/Users/admin/Desktop/Vercel_website`
- **Purpose**: The demo e-commerce website where the `voice-orb` is embedded. We use a python script (`scripts/update_vercel.py`) to inject the active backend ngrok URL into the Vercel clone.

---

## Current Status

### What We Did Till Now
- **Robust Model Fallbacks**: Modified `agent/stt.py` and `agent/tts.py` to use a non-recursive loop that automatically retries/falls back to standard models (`whisper-1` and `tts-1`) if preferred models (`gpt-4o-mini-transcribe` and `gpt-4o-mini-tts`) fail. 
- **Modular Multi-Tenant Architecture**: Restructured the catalog ingestion storage under site-specific subdirectories (`data/{resolved_site_id}/crawl.json`), backed by isolated schema mappings (`tenant_{site_id}`) in PostgreSQL.
- **Incremental Vectorization**: Modified background crawlers to run every 2 minutes (120s) and only re-calculate embeddings for new or updated catalog items (saving time and API tokens).
- **Frontend Action Normalization**: Unified the backend's `params` response format with the frontend widget's `parameters` expectation inside `plugin/src/actions.js`, correcting button and routing call bugs.
- **Database Call Deduplication**: Cached and reused the fetched user profile object in `orchestrator.py` to eliminate duplicate database hits.
- **Documentation Cleanup**: Cleaned up legacy sqlite and FAISS docstrings and imports across backend orchestrator and server entry points.
- **Test Suite Stabilization**: Fixed guardrail parameters and seeded schema configurations deterministic for tests, bringing the test suite to **50/50 successful tests**.

### What is Working ✅
- **Single-Command Startup**: `python run.py` starts the HTTPS proxy, storefront/admin service, and backend service together for the current static-IP topology.
- **Widget Injection**: The build script successfully injects `shopbot.js` into the Vercel site.
- **Audio Recording**: The `shopbot.js` successfully records user voice via the browser Media API and transmits it to the backend.
- **Database Search**: Postgres + pgvector indexing is functional, allowing product retrieval.
- **Navigation Commands**: General LLM navigation tasks (`NAVIGATE_TO` cart, etc.) are working.
- **LLM Product Identification (Precision Loss)**: Fixed the 64-bit ID corruption issue. The LLM outputs IDs as strings, and the entire pipeline safely handles string-based IDs.
- **Admin Panel UI Placement**: The Admin Panel link on the Vercel site is an aesthetic glassmorphic SVG gear icon with hover effects, matching the Voice Orb.
- **Debugging Auditability**: The backend writes timestamped logs to the `logs/` directory alongside standard output.
- **Multi-Turn Cart Operations**: The agent correctly resolves ordinal product references from previous conversational turns.

### Edge Cases Resolved
- Fixed `run_stream` crash bugs in `orchestrator.py` by adding missing `site_id` arguments.
- Added `CLEAR_HISTORY` and `UPDATE_PREFERENCES` to allowed action whitelists so they are no longer silently dropped.
- Fixed duplicated prompt example numbering in `prompt.py`.

### What is Not Working / Broken ❌
- **Manual QA on 2026-06-11 found integration issues.** The automated tests still pass, but the deployed/customer-facing flow is not fully working. See the audit section below.

---

## Manual QA Audit - 2026-06-11

### Test Coverage Run
- `pytest -q`: **50 passed**, 3 warnings.
- `plugin`: `npm run build` completed successfully.
- Local backend started on `http://127.0.0.1:8011`; `/health` returned OK.
- Verified local `/v1/shop`, `/v1/shop/stream`, and `/ws/chat` text flows for "Show me mugs".
- Verified TTS with `skip_tts=false`; response included non-empty `audio_b64` (about 211 KB).
- Generated a local WAV using Windows speech synthesis and posted it as `audio`; STT transcribed it as "Show me mugs." and returned the expected product action.
- Verified manual storefront cart behavior in Playwright: product page "Add To Cart" adds `acme-slip-on-shoes` and opens the cart.

### Issues Found

1. **Production storefront has no Voice Orb widget.**
   - URL tested: `https://vercelclonedwebsite.vercel.app/`
   - Playwright result: `#shopbot-widget` count = 0 and `#shopbot-btn` count = 0.
   - The deployed HTML only contains a warning stub: `Voice orb widget disabled: failed to fetch shopbot.js from https://6275-103-97-243-133.ngrok-free.app`.
   - The ngrok URLs currently present in local `.env` / built HTML did not return the backend `/health` endpoint.
   - Impact: a real customer cannot open or use the assistant on the deployed website.

2. **The external `/shopbot.js` loader points the widget at `http://localhost:8000`, not the backend that served it.**
   - Served bundle from `http://127.0.0.1:8011/shopbot.js?site=ai_kart_main` still contains:
     `apiUrl: currentScript?.getAttribute("data-api-url") || "http://localhost:8000"`.
   - `_load_widget_script()` tries to replace `"__AI_PUBLIC_API_URL__"`, but the built bundle does not contain that placeholder.
   - Browser voice-click test attempted `http://localhost:8000/v1/shop` and failed with CSP/fetch errors.
   - Impact: the manual script tag (`<script src=".../shopbot.js?..."></script>`) is not sufficient for a customer site. It needs a working embedded API URL or required `data-api-url`.

3. **Voice cart actions use backend product IDs, but the storefront cart expects product handles.**
   - Backend action for Acme Slip-On Shoes used product ID `2467198976006386294`.
   - Storefront catalog/cart uses handle/id `acme-slip-on-shoes`.
   - Playwright test: `window.ShopBotConfig.onAddToCart("2467198976006386294", 1)` left the cart empty; `window.ShopBotConfig.onAddToCart("acme-slip-on-shoes", 1)` added the item.
   - Impact: even after the orb loads, `ADD_TO_CART` from the assistant will not add the intended storefront item unless IDs are mapped.

4. **Product APIs serialize large IDs as JSON numbers, causing JavaScript precision loss.**
   - `/v1/products` returned `2467198976006386294` as a JSON number.
   - Node/JS parsed it as `2467198976006386000`; `Number.isSafeInteger(...)` was `false`.
   - Impact: any browser code that consumes product endpoint IDs can corrupt IDs before sending follow-up actions.

5. **`SHOW_PRODUCTS` / `FILTER_PRODUCTS` actions are not implemented by the Vercel storefront.**
   - `plugin/src/actions.js` dispatches a `shopbot:action` event for unhandled actions.
   - `Vercel_website/scripts/cart.js` listens for `ADD_TO_CART`, `CLEAR_CART`, `NAVIGATE_TO cart`, and `CHECKOUT`, but not `SHOW_PRODUCTS`, `FILTER_PRODUCTS`, or `SHOW_PRODUCT_DETAIL`.
   - Impact: assistant recommendations do not visibly update the product grid/search/detail page; customers only see the chat text.

6. **Checkout endpoint fails because `reportlab` is missing from dependencies.**
   - After adding a valid backend cart item, `POST /v1/cart/checkout` returned 500.
   - Server stderr: `POST /v1/cart/checkout failed: No module named 'reportlab'`.
   - Impact: invoice generation/checkout is broken in a fresh environment unless `reportlab` is installed manually.

7. **Cart API returns 500 for storefront-style product IDs instead of a client error.**
   - `POST /v1/cart/add` with `product_id="gid://shopify/Product/9401822679353"` returned 500.
   - Server stderr: `invalid literal for int() with base 10`.
   - Impact: malformed or storefront-native IDs produce internal server errors instead of a clear 400/404 response.

8. **Storefront clone has a broken Next.js chunk route / MIME error.**
   - Local and public Playwright console error:
     `Refused to execute script from .../_next/static/chunks/e5c1221b6d8eaf1c.js... because its MIME type ('text/html') is not executable`.
   - The cart shim still works, but this indicates part of the cloned app hydration/static asset routing is broken.
   - Impact: native storefront interactions may be unreliable beyond the injected cart shim.

9. **Direct FastAPI startup can serve a stale/mixed catalog until the periodic crawler runs.**
   - On direct `uvicorn api.main:app` startup, early `/v1/products` samples returned dummy categories/products such as Kitchen Accessories and Toys.
   - After the periodic crawler ran, Acme products became active and product questions worked.
   - `run.py` crawls before starting the server, so this mainly affects direct API startup and tests that do not run the crawl first.

10. **Fresh setup docs/defaults still have a Postgres port mismatch.**
    - `docker-compose.yml` publishes Postgres on host port `5434`.
    - `README.md` required env example and `config.py` default use port `5433`.
    - Local `.env` has the correct `5434`, but a fresh setup following defaults can fail to connect.

---

## Static IP / Self-Hosting Decision - 2026-06-11

### Public IP Check
- Current external IPv4 observed from two independent public IP checks: `103.97.243.133`.
- Classification: public/global IPv4.
- It is **not** private, loopback, or reserved from the network classification checks.

### Hosting Conclusion
- Yes, this project can be hosted directly from the PC instead of using localhost or ngrok, **if** the router and ISP path expose this same public IP to the internet.
- This removes the brittle ngrok URL rotation problem and gives us direct control over the storefront, widget script, backend API, WebSocket, and checkout routes.
- This check confirms the current connection has a proper public IPv4. It does **not** prove the IP is static forever from one snapshot. Static status must be confirmed by the ISP plan/router WAN page, or by checking that the public IP stays the same after router reconnect/reboot and over time.

### Required Production Setup
- Router WAN IP should match the observed public IP: `103.97.243.133`.
- Router port forwarding:
  - External `80` -> PC reverse proxy HTTP port.
  - External `443` -> PC reverse proxy HTTPS port.
- Windows Firewall must allow inbound traffic for the reverse proxy on `80` and `443`.
- DNS should point the domain/subdomain `A` record to the public IP.
- HTTPS should be terminated by a reverse proxy such as Caddy or Nginx.

### Recommended Local Topology
- `Internet -> Domain DNS -> Router public IP -> Port forward 80/443 -> Reverse proxy on PC`
- Reverse proxy routes:
  - `/` -> storefront/static site service, currently `http://127.0.0.1:8000`
  - `/shopbot.js`, `/shopbot-widget.js`, `/shopbot-frame`, `/health`, `/v1/*`, `/ws/*` -> AI backend, currently `http://127.0.0.1:8011`

### Recommended Environment Direction
- Replace ngrok-based URLs with the final domain:
  - `PUBLIC_API_URL=https://your-domain.com`
  - `LAB_INJECTION_HTML=<script src="https://your-domain.com/shopbot.js?site=ai_kart_main"></script>`
  - `LAB_ALLOWED_SCRIPT_ORIGINS=https://your-domain.com`
- After this setup, `run.py` / `update_vercel.py` should no longer need to depend on ngrok for customer-facing traffic.

---

## Premium UI Makeover - 2026-06-11

### Completed Direction
- Rebranded the cloned storefront away from the old ACME/Vercel presentation.
- New public storefront brand direction: `AI-KART` with a premium neutral/cobalt/copper interface style.
- Updated storefront shell, navigation, footer, product cards, product detail pages, cart drawer, checkout modal, and voice-widget visual treatment.
- Added rebuild-safe UI assets and post-processing scripts in the storefront project so future static builds keep the new visual direction.

### Verification
- Local desktop and mobile Playwright smoke checks passed.
- No visible old `ACME`, `Acme`, or `Vercel` footer branding remained in the checked storefront views.
- Cart drawer opened correctly and the Voice Orb rendered once.
- The previous broken `_next` static chunk MIME issue was no longer reproduced during the local smoke test.

---

## Final Remediation Pass - 2026-06-11

### Hosting Topology Implemented
- Updated `run.py` as the primary single entry point for the current static-IP/self-hosted stack.
- Added helper scripts: `scripts/start_static_ip_host.ps1` and `scripts/stop_static_ip_host.ps1`.
- Added a production HTTPS reverse-proxy template: `deploy/Caddyfile.example`.
- Current app topology:
  - Caddy HTTPS proxy bind: `:80` and `:443`
  - Storefront/admin public bind: `0.0.0.0:8000`
  - Backend private bind: `127.0.0.1:8011`
  - Storefront proxies `/health`, `/shopbot.js`, `/shopbot-widget.js`, `/shopbot-frame`, and `/v1/*` to the backend.
  - Public widget/API origin is configured as `http://103.97.243.133:8000`.
- Local same-origin proxy is working through `http://127.0.0.1:8000`.
- Public-IP URL is **not reachable yet** from this machine:
  - `http://103.97.243.133:8000`
  - `http://103.97.243.133:8000/health`
- Windows Firewall rule for inbound TCP `8000` was added from an elevated PowerShell session.
- Remaining network requirement: configure router port forwarding, or verify that the router supports NAT loopback if testing the public IP from inside the same network. For real customer microphone use, put the final domain behind HTTPS using Caddy/Nginx on ports `80` and `443`.

### Admin Panel Implemented
- Admin URL: `/admin`.
- Default credentials are controlled by environment variables:
  - `ADMIN_USERNAME`
  - `ADMIN_PASSWORD`
  - Development default: `admin` / `admin`
- Admin capabilities:
  - Add product.
  - Update product by reusing the same product ID/handle.
  - Delete product.
  - Replenish all stock.
  - View storefront product count.
  - View backend catalog/RAG sync status from `/v1/catalog/status`.
- Storefront now renders a live catalog from `/api/products.json`, so admin-added products appear without rebuilding static pages and deleted products stop showing in the customer grid.
- The backend crawler now treats `/api/products.json` as the authoritative catalog when present. This makes admin edits visible to the periodic crawler and RAG sync path.

### Pending Audit Issues Resolved
1. **No production Voice Orb / ngrok dependency**
   - Added same-origin self-hosting proxy and static-IP launcher.
   - Storefront injects `/shopbot.js?site=ai_kart_main` instead of depending on ngrok.

2. **`/shopbot.js` pointed at localhost**
   - Widget bundle now receives the public storefront origin through `PUBLIC_API_URL`.
   - Proxied `/shopbot.js` currently contains `http://103.97.243.133:8000` as the API origin.

3. **Voice cart actions used backend IDs while storefront expected handles**
   - Storefront cart can now resolve local handles and backend/RAG numeric IDs.
   - If a numeric backend ID is not in the local catalog, the storefront looks it up through `/v1/products/by-ids`.

4. **Large product IDs serialized as JSON numbers**
   - API product response IDs now serialize as strings.
   - Regression test added.

5. **`SHOW_PRODUCTS` / `FILTER_PRODUCTS` / `SHOW_PRODUCT_DETAIL` not implemented**
   - Storefront now renders a customer-visible recommendation/results panel for these actions.
   - `SORT_PRODUCTS` is also handled for the active panel/catalog.

6. **Checkout failed due to missing `reportlab`**
   - Added `reportlab>=4.2.5` to `requirements.txt`.
   - Installed in the active environment.
   - Checkout PDF generation verified.

7. **Bad cart IDs returned 500**
   - Malformed IDs now return `400`.
   - Missing numeric product IDs now return `404`.
   - Regression tests added.

8. **Broken `_next` static chunk MIME issue**
   - Static wrapper keeps mirrored `_next` asset fallback.
   - Latest Playwright smoke test had no console errors.

9. **Direct API startup served stale catalog until periodic crawler**
   - Added `CRAWL_ON_STARTUP`.
   - Backend startup performs an initial crawl before API readiness when enabled.
   - Crawler now reads `/api/products.json` first when available.

10. **Postgres port mismatch**
    - `config.py` default now matches Docker: `5434`.
    - README env example updated to `5434`.

11. **Database seed was not repeatable against an already-used database**
    - `db.seed` now reuses an existing category by `name` or `slug` before inserting.
    - This prevents repeated test/seed runs from failing on the `categories_name_key` unique constraint.

### Security Hardening Completed
- `run.py` now generates a strong `ADMIN_PASSWORD` if the password is missing or still set to the development default `admin`.
- Admin credentials are stored in `.env`; `run.py` prints only where the password is stored, not the password itself.
- Default `admin` / `admin` access is rejected after the generated password exists.
- Admin write actions require same-origin `Origin` or `Referer`, so cross-origin product mutations are blocked.
- Basic admin login attempts are rate-limited per client IP.
- Storefront security headers are now applied:
  - `X-Content-Type-Options: nosniff`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `X-Frame-Options: SAMEORIGIN`
  - `Permissions-Policy: camera=(), microphone=(self), geolocation=(), payment=()`
  - `Content-Security-Policy`
  - `Cross-Origin-Opener-Policy: same-origin`
  - `Cross-Origin-Resource-Policy: same-origin`
- `Strict-Transport-Security` is emitted when the request is HTTPS or forwarded as HTTPS by the reverse proxy.
- CORS is no longer wildcard by default; it only emits an allowed origin when `API_CORS_ORIGIN` is explicitly configured.
- Admin pages send `Cache-Control: no-store`.

### Site ID Note
- `site=ai_kart_main` is the current tenant/catalog namespace used by the widget and backend.
- It maps to database schema `tenant_ai_kart_main` and keeps crawler/RAG/cart calls on the same catalog.
- It is not a public URL and does not mean the old Vercel/ACME owner is active.
- Renaming it is possible later, but `CURRENT_SITE_ID`, `AI_DEFAULT_SITE_ID`, `DEFAULT_SITE_ID`, and the widget `site=` parameter must all be changed together.
- Rename completed from the old demo namespace to `ai_kart_main` in `.env`, runtime defaults, storefront scripts, docs, and tests.

### Verification Run
- Backend tests: `pytest -q` -> **55 passed**, 3 warnings.
- Plugin build: `npm run build` -> passed.
- Storefront build: `npm run build` -> passed.
  - Current HTTP public origin causes the build-time deployment injector to emit its expected safety warning and use a static stub for deployment output.
  - Runtime self-hosting still injects the working same-origin `/shopbot.js` through `run.py` / `api.index`.
- Syntax checks:
  - `python -m py_compile api/main.py api/models.py db/database.py agent/ingestion.py config.py`
  - `python -m py_compile db/seed.py`
  - `python -m py_compile C:/Users/admin/Desktop/Vercel_website/api/index.py`
  - `node --check scripts/cart.js`
  - `node --check scripts/premium-ui.js`
- Browser QA through Playwright:
  - Premium storefront rendered.
  - Voice Orb rendered exactly once.
  - Cart add/open worked from live catalog.
  - `FILTER_PRODUCTS` rendered results.
  - `SHOW_PRODUCTS` rendered selected result.
  - Admin add product worked.
  - Admin-added product appeared on storefront.
  - Admin delete product worked.
  - `/v1/catalog/status` returned backend/RAG status.
  - Mobile widget click opened chat and entered `Listening...` with fake microphone input.
  - No browser console errors during the main desktop admin/customer QA run.
- Proxied API QA:
  - `/health` returned OK through storefront port `8000`.
  - `/v1/products` returned product IDs as strings.
  - Bad cart product ID returned `400`.
  - Missing numeric cart product ID returned `404`.
  - Valid cart add returned `200`.
  - Checkout returned `application/pdf` with non-empty content.
  - `/v1/shop` text query returned `SHOW_PRODUCTS` actions.
- `python run.py` single-entry startup smoke:
  - Supervisor PID started successfully.
  - Caddy listener: `:80` and `:443`.
  - Storefront/admin listener: `0.0.0.0:8000`.
  - Backend listener: `127.0.0.1:8011`.
  - `http://127.0.0.1:8000/health` returned OK through the storefront proxy.
- Security smoke after the firewall rule was added:
  - `http://127.0.0.1:8000/` returned `200`.
  - `http://127.0.0.1:8000/health` returned `200`.
  - `http://103.97.243.133:8000/health` still failed with `Unable to connect to the remote server`.
  - Default admin credentials returned `401`.
  - Configured admin credentials returned `200`.
  - Cross-origin admin product POST returned `403`.
  - Same-origin admin add product returned `303` and the temporary product appeared in `products.json`.
  - Same-origin admin delete product returned `303` and removed the temporary product.
  - Required security headers were present.
- Final backend regression run after seed idempotency fix:
  - `pytest -q` -> **55 passed**, 3 warnings.
- Tenant rename verification:
  - `python -m db.seed` populated `tenant_ai_kart_main`.
  - `pytest tests/test_ingestion.py tests/test_api.py tests/test_api_contract.py -q` -> **23 passed**, 3 warnings.
  - Runtime storefront HTML includes `site=ai_kart_main`.
  - Runtime storefront HTML and widget script contain no `https_demo_vercel_store`.
  - Runtime widget script contains no `site_1` fallback.
- Post-build runtime smoke:
  - `http://127.0.0.1:8000/` returned `200`.
  - `http://127.0.0.1:8000/health` returned `200`.
  - `http://127.0.0.1:8000/shopbot.js?site=ai_kart_main` returned `200`.
  - The served storefront HTML contains the runtime same-origin widget script.
  - `http://103.97.243.133:8000/health` still failed with `Unable to connect to the remote server`.

### Current Known Blocker
- Application hosting is ready locally, but public access to `103.97.243.133:8000` is blocked outside the app.
- Required next infrastructure steps:
  - Confirm router port forwarding from the public IP to this PC for port `8000`, or forward `80`/`443` to a local HTTPS reverse proxy.
  - Use a domain/subdomain with an `A` record pointing to `103.97.243.133`.
  - Use Caddy/Nginx for trusted HTTPS on ports `80`/`443`; raw public-IP HTTP is not suitable for customer sharing or browser microphone access.

### HTTPS Infrastructure Check - 2026-06-11
- Windows Firewall rules are now present and enabled for inbound TCP `80`, `443`, and `8000`.
- This PC's LAN address is `192.168.68.71`; Wi-Fi MAC is `2C-6D-C1-A7-9A-C2`.
- Router gateway is `192.168.68.1`.
- Public IP still resolves as `103.97.243.133`.
- Local listeners:
  - `0.0.0.0:8000` -> storefront/admin.
  - `127.0.0.1:8011` -> backend.
  - No local listener on `80` or `443` until Caddy starts.
- Public checks from this PC:
  - `103.97.243.133:8000` fails TCP/HTTP connection.
  - `103.97.243.133:80` returns `404`.
  - `103.97.243.133:443` returns `404` over HTTPS.
- Because this PC is not listening on `80` or `443`, the public `80/443` responses are coming from the router/ISP path or another port-forward target, not from AI-KART.
- Added Caddy setup helpers:
  - `scripts/setup_https_caddy.ps1`
  - `scripts/stop_caddy_https.ps1`
- Caddy package installed: `CaddyServer.Caddy` version `2.11.4`.
- Caddy executable path:
  - `C:\Users\admin\AppData\Local\Microsoft\WinGet\Packages\CaddyServer.Caddy_Microsoft.Winget.Source_8wekyb3d8bbwe\caddy.exe`
- `scripts/setup_https_caddy.ps1` now auto-detects the winget-installed Caddy executable.
- IP-only HTTPS POC mode implemented:
  - `scripts/generate_ip_cert.py` creates a local self-signed certificate with `IP:103.97.243.133` in Subject Alternative Name.
  - `scripts/setup_https_caddy.ps1 -IpPoc -IpAddress 103.97.243.133 -Start` writes `deploy/Caddyfile`, updates `.env`, and starts Caddy.
  - Current Caddy listeners:
    - `:80` -> redirects to HTTPS.
    - `:443` -> reverse proxies to `127.0.0.1:8000`.
  - Current app origin in `.env`: `https://103.97.243.133`.
  - `run.py` was restarted with `public URL target: https://103.97.243.133`.
  - Local forced-route HTTPS test passed:
    - `https://103.97.243.133/health` through local Caddy returned `200`.
    - TLS negotiated successfully with the generated IP SAN certificate.
    - `https://103.97.243.133/` through local Caddy returned the premium storefront HTML.
    - The served storefront includes `/shopbot.js?site=ai_kart_main`.
    - The widget script contains `https://103.97.243.133` and no `http://103.97.243.133` origin.
  - Direct public-IP test still returns the old `404`, proving router/ISP forwarding still is not sending public `443` traffic to this PC.
- Remaining HTTPS requirements:
  - Configure router port forwarding:
    - TCP `80` -> `192.168.68.71:80`
    - TCP `443` -> `192.168.68.71:443`
  - For IP-only POC, visitors will see a browser certificate warning unless they explicitly trust/import the generated cert chain on their device.
  - For a clean customer URL without warnings, use a domain/subdomain and run `scripts/setup_https_caddy.ps1 -Domain your-domain.com -Start`.

## Intranet Deployment Pivot - 2026-06-11

### Decision
- Public internet deployment is paused for now because router access/port-forwarding is not available and the public IP currently serves the TP-Link Omada login page.
- Active deployment target is now intranet/Wi-Fi access from devices on the same LAN.
- `run.py` has been changed from static-IP-first behavior to modular deployment mode behavior.

### Current Mode
- `.env` now uses:
  - `DEPLOYMENT_MODE=intranet`
  - `PUBLIC_STOREFRONT_ORIGIN=https://192.168.68.71`
  - `PUBLIC_API_URL=https://192.168.68.71`
- `python run.py` now resolves the browser URL from deployment mode:
  - `intranet` -> `https://<this-PC-LAN-IP>`
  - `public-ip` -> `https://<public-ip>`
  - `domain` -> `https://<domain>`
  - `custom` -> configured tunnel/custom origin
- Added `scripts/set_deployment_mode.ps1` so future migration is a config switch instead of code edits.

### Intranet Requirements
- This PC must stay reachable on the LAN, currently `192.168.68.71`.
- Windows Firewall must allow inbound TCP `80`, `443`, and optionally `8000`.
- Other devices should open `https://192.168.68.71` while connected to the same Wi-Fi/LAN.
- Browsers may show a warning because intranet IP HTTPS uses a local self-signed certificate. This is expected for internal testing.

### Future Migration
- Public static IP:
  - Run `scripts/set_deployment_mode.ps1 -Mode public-ip -Origin https://103.97.243.133`.
  - Then configure router forwarding for TCP `80/443` to this PC.
- Domain/DNS:
  - Run `scripts/set_deployment_mode.ps1 -Mode domain -Domain your-domain.com`.
  - Point DNS to the public IP and allow Caddy to issue trusted HTTPS.
- Tunnel:
  - Run `scripts/set_deployment_mode.ps1 -Mode custom -Origin https://your-tunnel-url`.

---

## Future Addons / Planned Changes
- Finish the infrastructure cutover: firewall, router forwarding, DNS, and HTTPS.
- Replace development admin credentials before any real public exposure.
- Keep the static-IP stack running only behind HTTPS for real customer voice use.
