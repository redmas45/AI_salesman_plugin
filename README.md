# AI Salesman Hub

AI Salesman Hub is the backend, RAG pipeline, voice pipeline, and hosted one-line widget script for the Voice Orb shopping assistant. Client websites paste one script tag; site-specific behavior lives inside our hosted `shopbot.js` adapter layer, not in client website source code.

## Current Milestone

**L7** is the current fallback point.

- GitHub sync comment: `L 7`
- Date: 2026-06-17
- Meaning: if later work breaks the React CRM, Docker Hub build, crawler sync, or hub/spoke setup, roll back to the GitHub state synced with `L 7` before debugging forward.

Key L7 behavior:
- One-line client embed remains the contract.
- Docker is the preferred HUB startup path: app, CRM, widget host, Nginx, PostgreSQL, and pgvector.
- CRM frontend is now React/Vite/TypeScript/Tailwind under `crm/`; Docker builds `crm/dist` automatically and FastAPI serves it at `/crm`.
- The client website remains external to the HUB Docker stack.
- Client website admin/product management belongs to the client site, not AI Hub CRM.
- The crawler supports the new AI-KART FastAPI catalog endpoint at `/api/products`.
- Docker defaults run a startup crawl and then a periodic crawl every 120 seconds; CRM still has a manual `Crawl now` button.
- Product-detail routing is handled in the HUB-hosted adapter before falling back to client website hooks.
- Numeric backend product IDs are not treated as client product route handles.
- Client/spoke website code is not modified for adapter fixes.
- CRM analytics shows catalog-backed product names only in `Most mentioned products`.
- CRM summaries are store-manager bullet points for demand, stock, and operations decisions.

## Architecture

```text
Client website
  -> one script tag loads /shopbot.js from the HUB
  -> Voice Orb records audio and sends turns to /v1/shop or /v1/ws/shop
  -> HUB returns speech, text, and UI actions
  -> hosted adapter in shopbot.js handles navigation, product panels, cart hooks, and fallback events

AI Salesman Hub
  -> FastAPI backend
  -> CRM admin panel at /crm
  -> STT, LLM, TTS orchestration
  -> crawler/RAG ingestion
  -> PostgreSQL + pgvector tenant catalog
  -> hosted widget bundle
```

Flow diagram:

![AI Salesman Plugin Flow](docs/ai_salesman_plugin_flow.svg)

## One-Line Client Script

Current intranet AI-KART manual-paste script:

```html
<script defer src="https://192.168.68.51:8484/shopbot.js?site=ai_kart" data-site-id="ai_kart"></script>
```

Generic client script:

```html
<script defer src="https://hub.example.com/shopbot.js?site=client_site_id" data-site-id="client_site_id"></script>
```

The adapter is bundled inside `shopbot.js`. A real client should not need a second hook block. If a client needs Shopify, WooCommerce, custom cart, checkout, or variant behavior, we add that adapter logic to the HUB-hosted script for that site.

For local AI-KART testing, this script is intentionally pasted into the client simulator HTML just like a real client would paste it. Keep the pasted script absolute and HUB-facing. The simulator server should preserve the pasted script instead of replacing it with a same-origin `/shopbot.js` script.

### Local Hub Address Model

The AI Hub is locally hosted on this PC in Docker, but it is exposed to browsers through the PC's Wi-Fi/LAN address:

```text
Browser/CRM/widget public origin: https://<this-pc-lan-ip>:8484
Docker app private origin:        http://app:8585
Docker database origin:           db:5432
Local client simulator:           http://127.0.0.1:8584
Docker crawler target:            http://host.docker.internal:8584
Website proxy to HUB:             http://127.0.0.1:8080
```

If the Wi-Fi/LAN IP changes, update the public HUB URL and pasted script/certificate values. Do not change the Docker database host, the crawler target, or the website proxy target for local simulator testing.

## AI Hub CRM

The HUB now includes a local admin CRM at:

```text
/crm
```

Current CRM scope:

- Dashboard: store-manager analytics layout with range-driven KPIs, sparklines, intent donut, product-demand bars, recent activity, and active clients.
- Dashboard navigation: KPI cards and panels are clickable and route to Conversations, Catalogs, Usage, Analytics, Clients, or Client detail for deeper work.
- Theme support: CRM supports both light and dark mode; the default local dashboard opens in the light option-3 style.
- Client management: add, remove, enable/disable, copy one-line script.
- CRM auth: when `CRM_ADMIN_TOKEN` is configured, the React CRM shows a token screen instead of browser prompt loops.
- Crawler control: trigger a crawl for a client site.
- Catalog visibility: tenant product counts, categories, vectorization status, previews.
- Usage tracking: turn counts, estimated tokens, latency, session quotas, recent events.
- Conversation review: date-wise sessions with user transcript, AI reply, intent, tokens, and latency.
- Analytics: range filters, turn trends, intent mix, product-only demand signals, and CRM summaries.
- Settings: whitelisted `.env` keys for providers, models, deployment, and crawler settings.

Set `CRM_ADMIN_TOKEN` in `.env` to protect `/v1/admin/*`. If it is empty, the CRM is open for local development.

## Client Panel

The separate `client_panel` repo is the client-facing portal. It consumes scoped Hub APIs under `/v1/client-panel/*` and only returns data for the logged-in client site.

Current scope:

- Client login by `site_id` and client-panel password.
- Client-only graphs, summaries, token usage, catalog counts, and conversation review.
- Per-shopper/session token limit updates. Logged-in spoke users can provide stable session IDs; anonymous visitors remain browser-session based. The purchased client token limit remains Hub-owned.

Hub `.env` keys:

```text
CLIENT_PANEL_DEFAULT_PASSWORD=change-this-client-password
CLIENT_PANEL_TOKEN_SECRET=change-this-signing-secret
```

### CRM Analytics Behavior

Analytics is designed for store-manager decisions, not raw word counting.

- The Dashboard is a navigation-first summary surface; it keeps the range selector and removes non-essential actions from the header.
- Changing the Dashboard range reloads analytics/conversation data and updates the range-backed cards and panels.
- AI summary generation belongs in the Analytics tab, not the Dashboard header.
- `Most mentioned products` shows catalog product names only.
- Filler words, verbs, pronouns, and casual words such as `yaar`, `great`, `choice`, and `interested` are filtered out.
- Product mentions are matched against each tenant's catalog, so analytics stays separated per client.
- The CRM summary is shown as readable bullet points, for example what customers are looking for, what to stock, and what operations should improve.
- If `OPENAI_API_KEY` is configured, the `Generate AI summary` button asks OpenAI for a concise store-manager summary. Without OpenAI, the HUB still returns a deterministic heuristic summary.

## Prerequisites

Install these before running the project:

- Windows 10/11 PowerShell, or equivalent shell on Linux/macOS.
- Python 3.11 or 3.12. Python 3.13 is not the primary target because some audio and ML dependencies may lag.
- Docker Desktop, for PostgreSQL with pgvector.
- Node.js 18+ and npm, for rebuilding `plugin/shopbot.js`.
- Docker-managed Nginx, for HTTPS/LAN proxy mode.
- Chrome or Chromium, used by Crawl4AI / browser-based crawling.
- Git.

## Full Dependency List

### System Services

- PostgreSQL 16 with pgvector, provided by Docker image `pgvector/pgvector:pg16`.
- Nginx HTTPS proxy, provided by Docker image `nginx:1.27-alpine`.
- Chrome/Chromium browser runtime.

### Python Packages

Installed from `requirements.txt`:

```text
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
python-multipart>=0.0.12
pydantic>=2.10.0
openai>=1.55.0
groq>=0.31.0
sentence-transformers>=3.3.0
numpy>=2.0.0
pgvector>=0.3.2
psycopg[binary]>=3.2.0
httpx>=0.27.0
python-dotenv>=1.0.0
tenacity>=9.0.0
structlog>=24.0.0
crawl4ai>=0.4.0
undetected-chromedriver>=3.5.5
reportlab>=4.2.5
cryptography>=44.0.0
pytest>=8.3.0
pytest-asyncio>=0.24.0
pyngrok>=7.0.0
```

### Node Packages

Installed from `plugin/package.json`:

```text
esbuild ^0.28.1
```

## Installation

From the repo root:

```powershell
cd C:\Users\admin\Desktop\AI_salesman_plugin

python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

docker compose up -d db

cd plugin
npm install
npm run build
cd ..
```

If Crawl4AI needs browser setup on a fresh machine, run:

```powershell
crawl4ai-setup
```

## Environment Setup

Create `.env` in the repo root. Minimal intranet example:

```env
OPENAI_API_KEY=
GROQ_API_KEY=

STT_PROVIDER=groq
GROQ_STT_MODEL=whisper-large-v3-turbo

TTS_PROVIDER=groq
GROQ_TTS_MODEL=canopylabs/orpheus-v1-english
GROQ_TTS_VOICE=troy
GROQ_TTS_RESPONSE_FORMAT=wav
GROQ_FALLBACK_TO_OPENAI=true

DATABASE_URL=postgresql://shopbot:shopbot_password@localhost:5434/shopping_db

CURRENT_URL=http://127.0.0.1:8584/
CURRENT_SITE_ID=ai_kart
AI_DEFAULT_SITE_ID=ai_kart
DEFAULT_SITE_ID=ai_kart

DEPLOYMENT_MODE=intranet
STOREFRONT_PORT=8584
BACKEND_PORT=8585
HTTPS_PORT=8484
HTTP_REDIRECT_PORT=0

CRAWL_MAX_PAGES=1024
CRAWL_MAX_DEPTH=100
CRAWL_ON_STARTUP=true
CRAWL_PERIODIC_ENABLED=true

PUBLIC_API_URL=
PUBLIC_WIDGET_SCRIPT_URL=
MANUAL_WIDGET_SCRIPT=
PUBLIC_STOREFRONT_ORIGIN=
PUBLIC_HTTPS_ORIGIN=

HUB_PUBLIC_URL=https://192.168.68.51:8484
CLIENT_STORE_URL=http://host.docker.internal:8584
CRM_ADMIN_TOKEN=
CLIENT_PANEL_DEFAULT_PASSWORD=client123
CLIENT_PANEL_TOKEN_SECRET=change-this-signing-secret
AUTO_OPEN_CRM=true
```

Keep `CURRENT_SITE_ID`, `AI_DEFAULT_SITE_ID`, `DEFAULT_SITE_ID`, and the `site=` query parameter aligned. The value is a tenant/catalog namespace, not a URL.

For Docker runs, `CLIENT_STORE_URL` is the crawler URL for the client site. Keep the local simulator value as `http://host.docker.internal:8584`; using `http://127.0.0.1:8584` inside Docker points at the wrong container/network namespace. `CURRENT_URL` is mainly for the legacy local supervisor path.

## Legacy Local Supervisor

Docker is the preferred path for the HUB. The older local supervisor is kept for development fallback when you explicitly want one process to start the HUB, local spoke storefront, and legacy HTTPS proxy:

```powershell
python run.py
```

Default intranet topology:

```text
Caddy HTTPS:       https://<this-pc-lan-ip>:8484
Spoke storefront:  http://0.0.0.0:8584
AI HUB backend:    http://127.0.0.1:8585
Postgres:          localhost:5434
```

Open the printed Wi-Fi/LAN URL. In intranet mode, the browser may warn about the local certificate. Accept it for internal testing.

`python run.py` also exposes and auto-opens the CRM when that legacy path is used:

```text
https://<this-pc-lan-ip>:8484/crm
```

Stop:

```powershell
Ctrl+C
```

## Running The AI Hub Docker Stack

This is the preferred production-shaped startup path. Docker runs only our AI Hub services:

```text
CRM
FastAPI backend
shopbot.js widget host
crawler/RAG APIs
PostgreSQL + pgvector
Nginx proxy
```

The client website is not part of this Docker stack. For local AI-KART testing, start `Vercel_website` separately. In production, the real client runs their own website.

Single command from this repo, with startup logs visible:

```powershell
docker compose up --build
```

The app container prints:

```text
AI Hub Docker is booting
CRM:    https://localhost:8484/crm
Widget: https://localhost:8484/shopbot.js?site=ai_kart
API:    http://localhost:8585
```

Then open:

```text
https://localhost:8484/crm
```

If you want detached/background mode:

```powershell
docker compose up -d --build
docker compose logs -f app
```

Optional local helper, if you want PowerShell to start Docker and open the CRM browser tab:

```powershell
.\scripts\start_crm.ps1
```

On EC2, use the same Docker command and open the CRM from your own browser:

```text
https://your-hub-domain.com/crm
```

Important Docker variables:

```env
HUB_PUBLIC_URL=https://your-hub-domain.com
CLIENT_STORE_URL=https://client-store.com
HUB_TLS_CERT_FILE=/certs/ip-192_168_68_51.crt
HUB_TLS_KEY_FILE=/certs/ip-192_168_68_51.key
CRM_ADMIN_TOKEN=choose-a-strong-admin-token
CRAWL_ON_STARTUP=true
CRAWL_PERIODIC_ENABLED=true
```

For a new client, use the CRM `Add client` flow. The CRM creates the tenant, gives the script tag, and can trigger the crawler. The client website still only receives one pasted script line.

In intranet mode, `HUB_PUBLIC_URL` must be the AI Hub machine's current LAN URL, for example:

```env
HUB_PUBLIC_URL=https://192.168.68.51:8484
```

Then a client website on another same-Wi-Fi machine can paste a script like:

```html
<script defer src="https://192.168.68.51:8484/shopbot.js?site=client_site_id" data-site-id="client_site_id"></script>
```

The client website can run on a different LAN IP. Add that website URL in the CRM and trigger its crawler from there. Docker crawls once during startup when `CRAWL_ON_STARTUP=true`, then crawls every 120 seconds when `CRAWL_PERIODIC_ENABLED=true`. The CRM also keeps the per-client `Crawl now` button for manual refreshes.

The bundled Docker Nginx HTTPS config uses files from `deploy/certs`. For this machine it is currently:

```env
HUB_TLS_CERT_FILE=/certs/ip-192_168_68_51.crt
HUB_TLS_KEY_FILE=/certs/ip-192_168_68_51.key
```

If the HUB machine gets a different LAN IP, generate/use the matching cert pair and update those two variables.

For local AI-KART testing with the rebuilt React/Vite AI-KART site, start the client backend and frontend manually from the separate project:

```powershell
cd C:\Users\admin\Desktop\Vercel_website
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000

cd ..\frontend
npm run dev
```

To test the AI connection, paste the one-line Hub script into `Vercel_website/frontend/index.html`. The React/Vite client no longer reads Hub URL environment variables.

## Deployment Modes

Mode is controlled by `DEPLOYMENT_MODE`:

- `intranet`: local Wi-Fi/LAN testing without router forwarding.
- `public-ip`: direct public IP hosting after router/firewall forwarding.
- `domain`: DNS hostname with Caddy-managed HTTPS.
- `custom`: tunnel or external HTTPS origin, such as Cloudflare Tunnel or ngrok.

Switch modes:

```powershell
.\scripts\set_deployment_mode.ps1 -Mode intranet
.\scripts\set_deployment_mode.ps1 -Mode public-ip -Origin https://103.97.243.133
.\scripts\set_deployment_mode.ps1 -Mode domain -Domain shop.example.com
.\scripts\set_deployment_mode.ps1 -Mode custom -Origin https://example.trycloudflare.com
```

Restart after switching:

```powershell
python run.py
```

## Local Spoke Simulator

`C:\Users\admin\Desktop\Vercel_website` is a customer/spoke simulator. It is not the reusable HUB.

Standalone customer-site mode:

```powershell
cd C:\Users\admin\Desktop\Vercel_website
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000

cd ..\frontend
npm run dev
```

AI-enabled customer simulation uses the same one-line script a real client would paste:

```html
<script defer src="https://192.168.68.51:8484/shopbot.js?site=ai_kart" data-site-id="ai_kart"></script>
```

The client website does not dynamically load Hub code from frontend environment variables. No pasted script means no mic. A disabled client in AI Hub CRM also means no mic.

## Build The Widget

After editing files in `plugin/src`, rebuild the served bundle:

```powershell
cd plugin
npm run build
cd ..
```

Important source files:

```text
plugin/src/index.js
plugin/src/actions.js
plugin/src/productOverlay.js
plugin/src/productResolver.js
plugin/src/constants.js
plugin/shopbot.js
```

## Build The CRM

The CRM frontend is a React/Vite app in `crm/`. Docker builds it automatically and FastAPI serves the compiled `crm/dist` bundle at `/crm`.

For local non-Docker FastAPI runs, build it first:

```powershell
cd crm
npm install
npm run build
cd ..
```

## Tests And Verification

Run backend tests:

```powershell
pytest
```

Run focused tests:

```powershell
pytest tests/test_api.py -v
pytest tests/test_guardrails.py -v
pytest tests/test_ingestion.py -v
pytest tests/test_ws_shop.py -v
```

Check widget syntax and rebuild:

```powershell
node --check plugin\src\actions.js
node --check plugin\src\productResolver.js
node --check plugin\shopbot.js
cd plugin
npm run build
cd ..
```

Manual smoke test:

1. Start HUB stack: `docker compose up -d --build`.
2. Start the client website separately. For AI-KART local testing, run `Vercel_website` with the manual HUB script pasted in `out/index.html`.
3. Open CRM: `https://127.0.0.1:8484/crm` or the current LAN HUB URL.
4. Open the client storefront at `http://127.0.0.1:8584` and confirm the Voice Orb appears.
5. Say `hello`.
6. Say `show me NOVA dog sweater`.
7. Say `add it to cart`.
8. Confirm navigation uses the real product page, not `/product/<numeric_backend_id>/`.
9. Say `checkout`, provide address and payment method, and confirm `bill.pdf` downloads or the modal shows `Download bill`.
10. Confirm terminal turn logs print `AI_CONVO` and `[SHOPBOT TURN]`.

CRM analytics smoke test after Docker boot:

```powershell
docker compose up -d --build
curl.exe -k -s "https://127.0.0.1:8484/v1/admin/analytics?range=7d"
```

Expected analytics contract:

- `summary` is newline-separated bullet guidance for a store manager.
- `top_products` contains product names from the tenant catalog only.
- `top_terms` is kept for backward compatibility and mirrors product-only entries.
- Non-product words from conversations must not appear in the product ranking.

CRM dashboard smoke test:

1. Open `https://localhost:8484/crm`.
2. Confirm the Dashboard header shows `Store Manager Analytics` and only the range selector.
3. Change the range and confirm KPI labels/panels update to that selected range.
4. Click dashboard cards and panels:
   - Voice turns or Recent activity opens Conversations.
   - Products indexed opens Catalogs.
   - Latency or tokens opens Usage.
   - Intent mix or product-demand bars opens Analytics.
   - Active clients opens Clients.
   - A client row opens Client detail.
5. Toggle Dark mode and confirm the dashboard remains readable.

## Terminal Turn Logs

Expected shape:

```text
AI_CONVO | user: show me caps
AI_CONVO | ai_reply: Here are two cap options.
AI_CONVO | method_used: websocket | status: ok | time_taken: 1842ms | pipeline: 1750ms | actions: 1
[SHOPBOT TURN] transport=websocket status=ok site=ai_kart elapsed=1842ms pipeline=1750ms actions=1 transcript="show me caps" response="Here are two cap options."
```

`method_used` / `transport` may be `websocket`, `legacy-http`, `legacy-sse`, or `legacy-ws`.

## Catalog Storage

Each site uses a tenant schema:

```text
tenant_<site_id>
```

Main tables:

```text
products
categories
catalog_source_products
catalog_sync_runs
cart
user_profile
```

The crawler prefers public catalog APIs when available:

```text
/api/products.json
/api/products
/products.json
/collections/all/products.json
/wp-json/wc/store/products?per_page=100
```

If no catalog API is available, it falls back to sitemap, robots, common collection routes, rendered HTML, JSON-LD, Next.js data, React flight payloads, embedded app state, and visible-text heuristics.

## Admin Boundary

This repo is the AI HUB. It does not own the client website admin.

For AI-KART testing, storefront admin/product editing belongs to `C:\Users\admin\Desktop\Vercel_website`. The HUB owns AI/admin operations through the CRM and APIs such as:

```text
/crm
/v1/admin/*
/v1/catalog/status
/v1/catalog/crawler/run
/v1/products
/v1/products/by-ids
```

## Troubleshooting

Database not reachable:

```powershell
docker-compose up -d
docker ps
```

Legacy `run.py` Caddy proxy not found:

```powershell
winget install --id CaddyServer.Caddy --accept-source-agreements --accept-package-agreements
```

Widget changes not visible:

```powershell
cd plugin
npm run build
cd ..
python run.py
```

Voice recording blocked:
- Use HTTPS for browser microphone access.
- In intranet mode, accept the local certificate warning.
- Check browser microphone permission for the site.

Catalog stale:
- For Docker runs, confirm `CLIENT_STORE_URL=http://host.docker.internal:8584`.
- Confirm the CRM client row for `ai_kart` uses `http://host.docker.internal:8584`, not `http://127.0.0.1:8584`.
- Restart with `CRAWL_ON_STARTUP=true`, or call `/v1/catalog/crawler/run`.
