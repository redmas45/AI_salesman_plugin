# AI Salesman Hub

AI Salesman Hub is the backend, CRM, crawler/RAG pipeline, voice pipeline, and hosted one-line widget script for AI-enabled commerce sites.

The client website gets one script tag. The Hub owns the AI pipeline, catalog ingestion, analytics, hosted widget, and platform/site adapters.

## Current Milestone

**L8** is the current deployment checkpoint.

- Git sync comment: `L 8`
- Date: 2026-06-18
- Meaning: public path-routed deployment is the active baseline. AI Hub runs as Docker `db` + `app` only, served publicly through shared system Nginx at `/aihub/`.

L8 includes:

- `run.py`, local Caddy, local HTTPS helper scripts, and Docker Nginx are removed.
- `ai_kart` is the active AI-KART tenant ID.
- AI Hub defaults to `public-ip` and `http://143.198.5.97/aihub`.
- CRM client detail is tabbed and less cramped.
- Client Panel is redesigned into tabbed Overview, Demand, Conversations, Catalog, and Token policy sections.
- AI-KART SQLite runtime DB is removed from git tracking; `backend/products.seed.json` remains the dummy catalog source.
- `docs/` is ignored and local-only.

## Current Deployment

Current no-DNS public server shape:

```text
AI-KART website: http://143.198.5.97/
AI Hub CRM:      http://143.198.5.97/aihub/crm/
AI Hub API:      http://143.198.5.97/aihub/
Client Panel:    http://143.198.5.97/client-panel/ai_kart
```

Shared system Nginx, configured from `Vercel_website/aikart.md`, routes traffic:

```text
/                         -> AI-KART frontend on 127.0.0.1:5175
/api/                     -> AI-KART backend on 127.0.0.1:8000
/aihub/                   -> AI Hub Docker app on 127.0.0.1:5176
/client-panel/<client_id> -> Client Panel on 127.0.0.1:5177
```

Use Docker Compose for AI Hub and the shared public Nginx edge for routing.

## Architecture

```text
Client website
  -> loads /shopbot.js from AI Hub
  -> Voice Orb records audio and sends turns to /v1/shop
  -> Hub returns text, audio, and UI actions
  -> hosted adapter handles navigation, product panels, cart actions, and checkout handoff

AI Salesman Hub
  -> FastAPI backend
  -> React CRM at /crm
  -> STT, LLM, TTS orchestration
  -> crawler and RAG ingestion
  -> PostgreSQL + pgvector tenant catalog
  -> hosted widget bundle
```

## One-Line Client Script

Current AI-KART script:

```html
<script defer src="http://143.198.5.97/aihub/shopbot.js?site=ai_kart" data-site-id="ai_kart"></script>
```

Generic client script:

```html
<script defer src="https://hub.example.com/shopbot.js?site=client_site_id" data-site-id="client_site_id"></script>
```

The adapter is bundled inside the Hub-served script. A normal client should not paste a second hook block. If a client needs Shopify, WooCommerce, custom cart, checkout, or variant behavior, we add that behavior to the Hub-hosted adapter for that site or platform.

## Main Capabilities

- Voice assistant widget with STT, LLM, TTS, conversation history, and UI actions.
- Multi-tenant catalog isolation by `site_id`.
- Public crawler with API-first discovery, sitemap/robots discovery, priority URL planning, and Crawl4AI fallback.
- Product extraction from catalog APIs, JSON-LD, Shopify/Woo-like JSON, Next.js/React payloads, visible text, and optional gated LLM extraction.
- CRM for clients, crawler runs, catalog status, readiness reports, usage, conversations, analytics, adapters, settings, and health.
- Client Panel APIs for scoped client-facing analytics, usage, conversations, catalog status, and token policy.
- Hosted platform/site adapters for navigation, product display, add to cart, cart updates, checkout handoff, and variants where supported.

## Environment

Root `.env` belongs to AI Hub only. Do not store AI-KART website admin credentials here.

Minimal server shape:

```env
HUB_PUBLIC_URL=http://143.198.5.97/aihub
PUBLIC_API_URL=http://143.198.5.97/aihub
VOICE_ORB_API_URL=http://143.198.5.97/aihub
PUBLIC_STOREFRONT_ORIGIN=http://143.198.5.97

CURRENT_SITE_ID=ai_kart
DEFAULT_SITE_ID=ai_kart
AI_DEFAULT_SITE_ID=ai_kart

DEPLOYMENT_MODE=public-ip
CLIENT_STORE_URL=http://143.198.5.97/
CURRENT_URL=http://143.198.5.97/

CRAWL_ON_STARTUP=true
CRAWL_PERIODIC_ENABLED=true
CRAWL_MAX_PAGES=1024
CRAWL_MAX_DEPTH=100

STT_PROVIDER=groq
GROQ_STT_MODEL=whisper-large-v3-turbo
TTS_PROVIDER=groq
GROQ_TTS_MODEL=canopylabs/orpheus-v1-english
GROQ_TTS_VOICE=troy
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.30
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
RAG_TOP_K=10
RAG_TOP_N=3
LLM_EXTRACTOR_ENABLED=false

OPENAI_API_KEY=
GROQ_API_KEY=
CRM_ADMIN_TOKEN=
CLIENT_PANEL_DEFAULT_PASSWORD=
CLIENT_PANEL_TOKEN_SECRET=
```

AI-KART website admin credentials belong in:

```text
Vercel_website/backend/.env
```

## Local Development

Backend dependencies:

```powershell
cd C:\Users\admin\Desktop\AI_salesman_plugin
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

CRM:

```powershell
cd crm
npm install
npm run lint
npm run build
cd ..
```

Widget:

```powershell
cd plugin
npm install
npm run build
cd ..
```

Docker Hub app:

```powershell
docker compose up -d --build db app
```

Local AI Hub is then available at:

```text
http://127.0.0.1:5176/health
http://127.0.0.1:5176/crm/
```

## Deployment

Use [aihub.md](aihub.md) for the server deployment process. The runbook includes the safe Git pull step: tracked server edits are stashed automatically, ignored runtime files are preserved, and deployment uses `git pull --ff-only`.

High-level order:

1. Deploy AI Hub from `/var/www/AI_salesman_plugin/aihub.md`.
2. Verify `.env` uses public `/aihub` URLs and `DEPLOYMENT_MODE=public-ip`.
3. Build and restart `db` and `app` with Docker Compose.
4. Verify `http://127.0.0.1:5176/health`.
5. Apply shared Nginx routing from `Vercel_website/aikart.md`.
6. Verify `http://143.198.5.97/aihub/health` and `http://143.198.5.97/aihub/crm/`.
7. Crawl `http://143.198.5.97/` for `site_id=ai_kart`.

If Docker space is full:

```bash
sudo docker system df
sudo docker builder prune -af
sudo docker system prune -af
```

## CRM

CRM is served by the Hub at:

```text
/aihub/crm/
```

Current CRM scope:

- Dashboard: range-driven KPIs, demand trend, operations, active clients, and recent activity.
- Clients: add, remove, enable/disable, copy script, and crawl.
- Client detail: tabbed Overview, Readiness, Catalog, Crawl, Activity, and Controls.
- Catalog: product counts, categories, vectorization status, previews, images, and filters.
- Usage: turns, tokens, latency, session quotas, and events.
- Conversations: session review with transcript, AI reply, intent, tokens, and latency.
- Analytics: product demand, intent mix, transport/status/latency breakdowns, and recent events.
- Settings: whitelisted environment keys for providers, models, crawler, CRM, and Client Panel.

Set `CRM_ADMIN_TOKEN` in `.env` to protect `/v1/admin/*`.

## Client Panel

The separate `client_panel` project is the client-facing portal. It consumes scoped Hub APIs under `/v1/client-panel/*` and returns only that client's analytics, usage, catalog, conversations, and token policy.

Hub keys:

```env
CLIENT_PANEL_DEFAULT_PASSWORD=change-this-client-password
CLIENT_PANEL_TOKEN_SECRET=change-this-signing-secret
```

## Crawler And Adapters

The crawler prefers product APIs first:

```text
/api/products
/api/products.json
/products.json
/collections/all/products.json
/wp-json/wc/store/products?per_page=100
```

Then it uses robots, sitemaps, common product/category/shop URLs, rendered HTML, JSON-LD, framework payloads, and visible-text heuristics.

The adapter layer decides what the browser can safely do on a client site:

- Basic script-only mode: product advice, catalog Q&A, comparison explanations, support answers, simple navigation, and analytics.
- Commerce adapter mode: native add to cart, remove from cart, cart quantity updates, product detail routing, variants, filters, and checkout handoff when platform/site APIs allow it.
- Full integration mode: platform API keys, feeds, live inventory, variant IDs, order/checkout handoff, stronger stock confidence, and custom client-approved adapters.

## Tests

Backend:

```powershell
python -m pytest
```

Focused tests:

```powershell
python -m pytest tests/test_api.py -v
python -m pytest tests/test_ingestion.py -v
python -m pytest tests/test_crm_api.py -v
```

CRM:

```powershell
cd crm
npm run lint
npm run build
```

Widget:

```powershell
node --check plugin\src\actions.js
node --check plugin\src\productResolver.js
cd plugin
npm run build
```

Docker config:

```powershell
docker compose config --services
```

## Operational Notes

- Disabling a client removes the mic/widget for that client, but admin-triggered crawling can still run.
- Removing a client is a CRM soft delete; it does not drop tenant catalog tables.
- Public HTTP pages can load the UI, but browser microphone access requires HTTPS on public origins. DNS plus HTTPS should be the production target.
- `ai_kart` is the active tenant ID.
- Use the Docker/shared Nginx deployment path documented in `aihub.md`.
