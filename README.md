# AI Salesman Hub

AI Salesman Hub is the central backend for AI-enabled commerce sites. It serves the hosted voice widget, CRM, crawler, RAG catalog, AI orchestration, analytics, tenant APIs, and Client Panel APIs.

The client website receives one script tag. The Hub owns the AI layer, catalog ingestion, hosted widget bundle, and adapter logic. The storefront keeps ownership of its own users, products, cart, checkout, and admin system.

## Current Baseline

Current deployment checkpoint: **L8**

Date: 2026-06-18

L8 is the current public path-routed deployment baseline:

- AI Hub runs through Docker Compose with only `db` and `app`.
- Public routing is handled by the shared system Nginx config from AI-KART.
- AI Hub is served publicly at `/aihub/`.
- CRM is served at `/aihub/crm/`.
- The active tenant is `ai_kart`.
- `docs/` is local-only and ignored.
- AI-KART runtime SQLite data is not owned by this repo.

## Public Topology

Current no-DNS public server layout:

```text
AI-KART website: http://143.198.5.97/
AI Hub CRM:      http://143.198.5.97/aihub/crm/
AI Hub API:      http://143.198.5.97/aihub/
Client Panel:    http://143.198.5.97/client-panel/ai_kart
```

Shared Nginx routes:

```text
/                         -> AI-KART frontend on 127.0.0.1:5175
/api/                     -> AI-KART backend on 127.0.0.1:8000
/aihub/                   -> AI Hub Docker app on 127.0.0.1:5176
/client-panel/<client_id> -> Client Panel on 127.0.0.1:5177
```

AI Hub does not own public Nginx in this setup. Public route changes belong in `Vercel_website/aikart.md`.

## Responsibilities

AI Hub owns:

- Voice widget serving at `/shopbot.js`.
- Voice turn APIs under `/v1/shop`.
- STT, LLM, TTS, prompts, guardrails, and orchestration.
- Tenant catalog ingestion and RAG search.
- Product crawling, readiness scanning, crawl reports, and vectorization.
- CRM admin UI and `/v1/admin/*` APIs.
- Client Panel scoped APIs under `/v1/client-panel/*`.
- Hosted adapter behavior for navigation, product panels, cart actions, and checkout handoff where supported.

AI Hub does not own:

- AI-KART website admin credentials.
- AI-KART product database as runtime state.
- Client storefront user accounts.
- Payment or checkout ownership.
- Public root Nginx routing.

## Repository Layout

```text
agent/       AI orchestration, prompts, RAG, crawler, STT/TTS, adapters
api/         FastAPI routes, CRM APIs, Client Panel APIs, widget serving
crm/         React/Vite CRM frontend served by the Hub
db/          Database schema, tenant catalog access, seed helpers
plugin/      Hosted browser widget source and built shopbot.js
tests/       Backend, ingestion, guardrail, API, and widget contract tests
data/        Local development data and source product fixtures
docker/      Container entrypoint
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

Normal clients should not paste separate hook blocks. Site-specific behavior belongs in the Hub-hosted adapter layer.

## Runtime Model

Production AI Hub runs in Docker:

```text
db  -> PostgreSQL with pgvector
app -> FastAPI app, CRM static files, widget bundle, AI pipeline
```

Important server rule:

```text
AI Hub production does not use a host Python venv.
```

Local development can use `.venv`, but the public server deploy uses Docker Compose only.

## Environment

Root `.env` belongs to AI Hub only.

Do not put AI-KART website admin credentials here. AI-KART admin credentials belong in:

```text
Vercel_website/backend/.env
```

Minimal server `.env` shape:

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

## Local Development

Backend Python environment for local work:

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

Docker app:

```powershell
docker compose up -d --build db app
```

Local URLs:

```text
http://127.0.0.1:5176/health
http://127.0.0.1:5176/crm/
```

## Deployment

Use [aihub.md](aihub.md) for deployment.

The runbook handles:

- Safe Git pull using `git pull --ff-only`.
- Automatic stash of tracked server-local edits.
- Preservation of ignored runtime files.
- Docker Compose sanity checks.
- Fresh app image build and restart.
- Local and public smoke checks.

High-level order:

1. Deploy AI Hub from `/var/www/AI_salesman_plugin/aihub.md`.
2. Deploy or reload AI-KART shared Nginx from `/var/www/Vercel_website/aikart.md`.
3. Deploy Client Panel from `/var/www/client_panel/clientpanel.md`.
4. Crawl AI-KART for `site_id=ai_kart`.

If Docker space is exhausted:

```bash
sudo docker system df
sudo docker builder prune -af
sudo docker system prune -af
```

Do not run `docker system prune --volumes` unless database volumes are intentionally backed up and disposable.

## CRM

CRM is served by the Hub at:

```text
/aihub/crm/
```

Current CRM scope:

- Dashboard KPIs, demand trend, operations, active clients, and recent activity.
- Client create, remove, enable, disable, copy script, and crawl actions.
- Client detail tabs: Overview, Readiness, Catalog, Crawl, Activity, and Controls.
- Catalog review with counts, categories, vector status, product images, filters, and pagination.
- Usage and conversation review with turns, tokens, latency, transport, status, and session data.
- Analytics for product demand, intent mix, transport mix, latency buckets, and recent events.
- Settings for whitelisted AI, crawler, CRM, and Client Panel environment keys.

Protect `/v1/admin/*` with `CRM_ADMIN_TOKEN`.

## Client Panel API

The separate `client_panel` project uses Hub APIs under:

```text
/v1/client-panel/*
```

Required Hub keys:

```env
CLIENT_PANEL_DEFAULT_PASSWORD=change-this-client-password
CLIENT_PANEL_TOKEN_SECRET=change-this-signing-secret
```

These values control Client Panel login and token signing. They do not control AI-KART storefront admin login.

## Crawler And Adapters

The crawler prefers public product APIs first:

```text
/api/products
/api/products.json
/products.json
/collections/all/products.json
/wp-json/wc/store/products?per_page=100
```

Then it uses robots, sitemaps, product/category/shop URL planning, rendered HTML, JSON-LD, framework payloads, and visible-text extraction.

Integration levels:

- Script only: product advice, catalog Q&A, comparison, support answers, simple navigation, analytics.
- Script plus adapter: better catalog routing, add/remove cart, quantity updates, variant selection, filters, checkout handoff where supported.
- Full support: product feeds, platform API keys, live inventory, variant IDs, custom checkout/order handoff rules, staging/test access.

## Tests

Backend:

```powershell
python -m pytest
```

Focused examples:

```powershell
python -m pytest tests/test_api.py -v
python -m pytest tests/test_ingestion.py -v
python -m pytest tests/test_guardrails.py -v
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

- Active tenant is `ai_kart`.
- Disabling a client removes the widget for shoppers, but admin-triggered crawling can still run.
- Removing a client is a CRM soft delete and does not drop tenant catalog data.
- Public HTTP can load the UI, but browser microphone access requires HTTPS on public origins.
- DNS plus HTTPS is the production target for reliable microphone behavior.
- Server deploy stashes are backup records. Do not run `git stash pop` during normal deployment.

## Troubleshooting

`/aihub/health` fails publicly but `127.0.0.1:5176/health` works:

```text
Shared Nginx route is missing or stale. Apply Vercel_website/aikart.md.
```

CRM shows old assets:

```text
Rebuild the Docker app with --no-cache using aihub.md, then hard refresh the browser.
```

Client Panel login fails:

```text
Check CLIENT_PANEL_DEFAULT_PASSWORD and CLIENT_PANEL_TOKEN_SECRET in AI Hub .env, then redeploy AI Hub.
```

AI-KART admin login fails:

```text
Do not change AI Hub .env. AI-KART admin credentials live in Vercel_website/backend/.env.
```
