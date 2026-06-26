# AI Salesman Hub

AI Salesman Hub is the central "mothership" for AI assistants on client websites. A client website should only need one script tag. The Hub owns the widget, adapter runtime, crawling, vertical detection, prompt profiles, RAG/catalog ingestion, CRM, analytics, and Client Panel APIs.

The client website stays independent. It owns its own users, products or business records, checkout or booking flows, admin system, and public pages.

## Current State

Current development checkpoint: **L9 automatic vertical and hosted adapter foundation**

Date: **2026-06-26**

This repo has moved past the old ecommerce-only baseline. The current foundation supports:

- Universal one-line installer: `/install.js?site=<site_id>`.
- Hosted browser adapter runtime: `/shopbot-adapter.js`.
- Hosted widget bundle: `/shopbot.js` and `/shopbot-widget.js`.
- Browser discovery beacon: `POST /v1/widget/register`.
- Automatic client bootstrap when an installed site is first seen.
- Deterministic vertical classification across ecommerce, travel, insurance, finance, healthcare, food, real estate, education, automotive, legal services, jobs, events/ticketing, and generic websites.
- Generated adapter runtime config for routes, selectors, actions, platform hints, and discovery metadata.
- CRM vertical selector and vertical-aware client workspace labels/tabs.
- CRM Adapter tab showing the generated adapter code and runtime config for each client.
- CRM Prompt tab for draft/published prompt profile editing and version history.
- Generic knowledge tables and product-to-knowledge sync for future non-commerce RAG.
- Existing AI-KART ecommerce behavior preserved.

Important reality: this is a strong automatic foundation, not a magic 100% automation guarantee for every website on the internet. Public pages with readable HTML, standard forms/buttons, Shopify/WooCommerce hints, and accessible APIs work best. Login-only pages, CAPTCHA, payment steps, private APIs, anti-bot systems, and heavily custom SPAs still need validation, feeds, API access, or explicit client support.

## Public Topology

Current public-IP deployment:

```text
AI-KART website: http://143.198.5.97/
AI Hub CRM:      http://143.198.5.97/aihub/crm/
AI Hub API:      http://143.198.5.97/aihub/
Client Panel:    http://143.198.5.97/client-panel/ai_kart
```

Shared Nginx routing is owned by AI-KART:

```text
/                         -> AI-KART frontend on 127.0.0.1:5175
/api/                     -> AI-KART backend on 127.0.0.1:8000
/aihub/                   -> AI Hub Docker app on 127.0.0.1:5176
/client-panel/<client_id> -> Client Panel on 127.0.0.1:5177
```

Public route changes belong in `C:\Users\admin\Desktop\Vercel_website\aikart.md`, not in this repo.

## One-Line Install Contract

Current AI-KART script:

```html
<script defer src="http://143.198.5.97/aihub/install.js?site=ai_kart" data-site-id="ai_kart"></script>
```

Generic client script:

```html
<script defer src="https://hub.example.com/install.js?site=client_site_id" data-site-id="client_site_id"></script>
```

The installer loads the hosted adapter runtime first, then the widget. Normal clients should not paste separate hook blocks. Client-specific behavior belongs in Hub-owned runtime config, generated selectors/actions, platform adapters, prompts, and CRM controls.

## Automatic Onboarding Flow

```text
Client site
  pastes one script tag
    |
    v
/install.js
  loads /shopbot-adapter.js
  loads /shopbot.js
    |
    v
Browser adapter discovery
  reads safe page signals:
    title, URL, text sample, links, buttons, forms, platform hints
    |
    v
POST /v1/widget/register
  creates or updates Hub client
  classifies vertical
  generates routes/selectors/actions
  saves adapter config
  seeds prompt profile
  schedules crawl when needed
    |
    v
CRM client workspace
  Overview, Readiness, Catalog/Knowledge, Crawl, Activity,
  Adapter, Prompt, Controls, plus vertical-specific tabs
```

## Adapter Meaning

In this project, an adapter is not code the client must write.

The adapter is the Hub-controlled execution layer that tells the widget how to operate on a client website:

- What vertical the site belongs to.
- Which routes look like shop, search, booking, quote, cart, checkout, contact, policy, or support pages.
- Which selectors map to visible buttons/forms.
- Which actions are allowed for the vertical.
- Which platform hints were detected, such as Shopify or WooCommerce.
- Which safe fallback behavior should be used when direct platform APIs are not available.

The browser runtime lives in `plugin/src/adapter/` and is served as `/shopbot-adapter.js`.

The generated per-client runtime config is returned by:

```text
GET /v1/widget/config?site_id=<site_id>
GET /v1/admin/clients/<site_id>/adapter
```

The CRM Adapter tab shows the generated code/config so admins can inspect what the Hub decided.

## Vertical System

The vertical is the real runtime selector. It is not just a visual label.

Built-in verticals currently include:

```text
ecommerce
travel
insurance
finance_broker
healthcare
food
real_estate
education
automotive
legal_services
jobs_recruiting
events_ticketing
generic
```

Vertical definitions live in:

```text
agent/verticals/
crm/src/verticals/
```

Each vertical defines entity labels, entity types, readiness checks, risk level, workspace tabs, and allowed action categories.

Key endpoints:

```text
GET   /v1/admin/verticals
GET   /v1/admin/verticals/{vertical_key}
PATCH /v1/admin/clients/{site_id}/vertical
```

## Prompts

Prompt profiles are stored per client. CRM can create drafts, publish versions, and review version history.

Key files:

```text
db/prompts.py
agent/prompts/
crm/src/views/client-workspace/PromptTab.tsx
```

Key endpoints:

```text
GET  /v1/admin/clients/{site_id}/prompt-profile
POST /v1/admin/clients/{site_id}/prompt-profile
POST /v1/admin/prompt-versions/{version_id}/publish
```

Prompt assembly is layered:

```text
platform policy
  + vertical prompt
  + client published prompt profile
  + runtime capabilities
  + retrieved product or knowledge context
  + conversation context
```

High-risk verticals must stay conservative. The assistant must not diagnose, underwrite, approve, make legal conclusions, promise returns, promise eligibility, or invent live availability/price/terms.

## RAG And Knowledge

Ecommerce product RAG still works through the existing product tables. The generic RAG foundation has been added for other domains.

Key files:

```text
db/knowledge.py
agent/retrieval/generic_rag.py
agent/prompts/generic.py
```

Key endpoints:

```text
GET /v1/knowledge?site_id=<site_id>
GET /v1/admin/clients/{site_id}/knowledge
```

Current rule: keep ecommerce stable while generic knowledge is introduced gradually. Do not delete product tables or ecommerce prompt wrappers until the generic path is proven in production.

## Repository Layout

```text
agent/       AI orchestration, prompts, RAG, crawler, verticals, actions, adapters
api/         FastAPI app shell, route modules, CRM APIs, Client Panel APIs, widget serving
crm/         React/Vite CRM frontend
db/          Admin facade, schema, clients, prompts, knowledge, quota, analytics
plugin/      Hosted browser widget and adapter runtime source
tests/       Backend, ingestion, guardrail, vertical, knowledge, and widget tests
data/        Local development data and fixtures
docker/      Container entrypoint
```

Compatibility rule:

```text
Existing imports from db.admin should keep working.
Public API paths should stay stable.
AI-KART must keep working without AI Hub.
```

## Local Development

Use this when you want the full Hub exactly like deployment:

```powershell
cd C:\Users\admin\Desktop\AI_salesman_plugin
docker compose up -d --build db app
```

Open:

```text
http://127.0.0.1:5176/health
http://127.0.0.1:5176/crm/
```

Use this when you want backend hot reload from local Python:

```powershell
cd C:\Users\admin\Desktop\AI_salesman_plugin
docker compose up -d db

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

uvicorn api.main:app --reload --host 127.0.0.1 --port 5176
```

Build CRM:

```powershell
cd C:\Users\admin\Desktop\AI_salesman_plugin\crm
npm install
npm run lint
npm run build
```

Build widget and adapter bundles:

```powershell
cd C:\Users\admin\Desktop\AI_salesman_plugin\plugin
npm install
npm run build
```

If you see `ModuleNotFoundError: No module named 'app'`, you are probably running an AI-KART command in the Hub repo, or a Hub command in the AI-KART repo. AI Hub runs with:

```powershell
uvicorn api.main:app --reload --host 127.0.0.1 --port 5176
```

AI-KART runs separately from `C:\Users\admin\Desktop\Vercel_website\backend` with:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Environment

Root `.env` belongs to AI Hub only.

Do not put AI-KART website admin credentials here. AI-KART admin credentials belong in:

```text
C:\Users\admin\Desktop\Vercel_website\backend\.env
```

Local DB default:

```env
DATABASE_URL=postgresql://shopbot:shopbot_password@localhost:5434/shopping_db
```

Server Docker DB default:

```env
DATABASE_URL=postgresql://shopbot:shopbot_password@db:5432/shopping_db
```

Important Hub environment keys:

```env
HUB_PUBLIC_URL=http://143.198.5.97/aihub
PUBLIC_API_URL=http://143.198.5.97/aihub
PUBLIC_STOREFRONT_ORIGIN=http://143.198.5.97
CORS_ORIGINS=http://143.198.5.97
CURRENT_SITE_ID=ai_kart
DEFAULT_SITE_ID=ai_kart
AI_DEFAULT_SITE_ID=ai_kart
OPENAI_API_KEY=
GROQ_API_KEY=
CRM_ADMIN_TOKEN=
CLIENT_PANEL_DEFAULT_PASSWORD=
CLIENT_PANEL_TOKEN_SECRET=
```

## Deployment

Use:

```text
aihub.md
```

High-level order:

1. Deploy AI Hub from `/var/www/AI_salesman_plugin/aihub.md`.
2. Deploy or reload AI-KART shared Nginx from `/var/www/Vercel_website/aikart.md`.
3. Deploy Client Panel from `/var/www/client_panel/clientpanel.md`.
4. Open CRM and confirm the client workspace, adapter tab, prompt tab, and crawl status.

Production AI Hub runs in Docker Compose:

```text
db  -> PostgreSQL with pgvector
app -> FastAPI app, CRM static files, widget bundle, AI pipeline
```

AI Hub production does not use a host Python venv for runtime.

## Testing

Backend:

```powershell
cd C:\Users\admin\Desktop\AI_salesman_plugin
python -m pytest -q
python -m compileall api db agent tests
```

CRM:

```powershell
cd C:\Users\admin\Desktop\AI_salesman_plugin\crm
npm run lint
npm run build
```

Widget:

```powershell
cd C:\Users\admin\Desktop\AI_salesman_plugin\plugin
npm run build
```

Useful focused tests:

```powershell
python -m pytest tests/test_verticals.py -q
python -m pytest tests/test_vertical_runtime.py -q
python -m pytest tests/test_widget_install.py -q
python -m pytest tests/test_knowledge.py -q
```

Recent local verification after the automatic adapter/vertical work:

```text
python -m pytest -q                         -> 112 passed
python -m compileall api db agent tests      -> passed
cd crm; npm run lint                         -> passed
cd crm; npm run build                        -> passed
cd plugin; npm run build                     -> passed
```

## Operational Boundaries

AI Hub owns:

- Widget serving.
- Hosted adapter runtime.
- CRM and admin APIs.
- Client Panel APIs.
- Conversation logs and analytics.
- Crawled/vectorized copies of client data.
- Prompt profiles.
- Vertical definitions.
- Generated adapter configuration.

AI Hub does not own:

- Client website source code.
- Client user accounts.
- Client checkout, booking, payment, claim, quote, or application finalization.
- AI-KART website admin credentials.
- Public root Nginx routing.

## Reliability Roadmap

The next major reliability layer should be browser-based action validation:

- Server-side Playwright discovery for multi-page flows.
- Dry-run validation of generated selectors/actions.
- Confidence scores per route/action.
- CRM override editor for adapter config.
- Regression checks when a client site changes.
- Human handoff rules for payment, login, regulated decisions, CAPTCHA, and uncertain flows.

Until that exists, the system should be presented as automatic discovery plus admin-verifiable setup, not as guaranteed perfect autonomous control on every site.

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

Widget appears but microphone recording fails on public HTTP:

```text
Production microphone access needs HTTPS. DNS plus HTTPS is required for reliable public mic support.
```
