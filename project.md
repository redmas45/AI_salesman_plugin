# AI Salesman Plugin - Project Overview

Date: 2026-06-18

## Goal

AI Salesman Plugin provides a plug-and-play voice commerce layer for client websites.

The client adds one Hub script to their site. The Hub crawls/imports the catalog, builds tenant RAG inventory, answers product questions, compares items, guides the shopper, and executes supported storefront actions through hosted adapters.

## Current Public Setup

```text
AI-KART website: http://143.198.5.97/
AI Hub CRM:      http://143.198.5.97/aihub/crm/
AI Hub API:      http://143.198.5.97/aihub/
Client Panel:    http://143.198.5.97/client-panel/ai_kart
```

Shared Nginx routing is owned by `Vercel_website/aikart.md`:

```text
/                         -> AI-KART frontend on 127.0.0.1:5175
/api/                     -> AI-KART backend on 127.0.0.1:8000
/aihub/                   -> AI Hub Docker app on 127.0.0.1:5176
/client-panel/<client_id> -> Client Panel on 127.0.0.1:5177
```

The active deployment mode is `public-ip`. AI Hub runs through Docker Compose and shared system Nginx.

## Core Components

1. **Hosted widget and adapters**
   - Location: `plugin/src/*`, built to `plugin/shopbot.js`
   - Purpose: floating Voice Orb, audio capture, UI actions, product overlays, navigation, cart hooks, checkout handoff, platform/site adapters.

2. **FastAPI Hub backend**
   - Location: `api/main.py`, `api/*`
   - Purpose: voice turn APIs, admin APIs, client-panel APIs, widget serving, CRM serving, health checks.

3. **AI orchestration**
   - Location: `agent/orchestrator.py`, `agent/prompt.py`, `agent/stt.py`, `agent/tts.py`
   - Purpose: STT, LLM prompt, RAG context, UI action generation, TTS.

4. **Crawler and catalog ingestion**
   - Location: `agent/ingestion.py`, `agent/product_extractor.py`, `db/database.py`
   - Purpose: API-first crawling, priority URL planning, Crawl4AI fallback, product extraction, variants, vectorization, reports.

5. **CRM**
   - Location: `crm/src/*`
   - Purpose: Hub admin UI for clients, catalog, usage, conversations, analytics, adapters, settings, health, readiness, crawl reports.

6. **Client Panel**
   - Location: `C:/Users/admin/Desktop/client_panel`
   - Purpose: scoped client-facing analytics, usage, conversations, catalog status, and token policy.

7. **AI-KART storefront**
   - Location: `C:/Users/admin/Desktop/Vercel_website`
   - Purpose: demo/client storefront, backend product/admin system, shared public Nginx edge config.

## Active Tenant

```text
site_id: ai_kart
tenant schema: tenant_ai_kart
```

`ai_kart` is the only active AI-KART tenant ID.

## One-Line Script Contract

Current AI-KART script:

```html
<script defer src="http://143.198.5.97/aihub/shopbot.js?site=ai_kart" data-site-id="ai_kart"></script>
```

Generic client script:

```html
<script defer src="https://hub.example.com/shopbot.js?site=client_site_id" data-site-id="client_site_id"></script>
```

The client should not need a second hook block for normal operation. Site-specific behavior belongs in the Hub-hosted adapter layer.

## AI Enablement Levels

### 1. Script Only

Works when we only get one script tag:

- Voice Orb
- Product Q&A from crawled/imported catalog
- Product recommendations
- Comparisons and buying guidance
- Support answers from public content
- Simple page navigation
- AI usage analytics
- Lead/preference capture if approved

Limit: native cart and checkout actions may not work unless the site exposes usable APIs or predictable UI hooks.

### 2. Script + Robots/Crawl Permission + Adapter

Works when the client allows crawling and we add or select a platform/site adapter:

- Better catalog coverage
- Product detail routing
- Add to cart
- Remove from cart
- Cart quantity updates
- Variant selection where IDs/options are discoverable
- Native filter/search calls
- Checkout handoff

This is the practical commerce plan for most clients.

### 3. Full Support

Best result when the client provides platform/API access:

- Product feed or API credentials
- Live stock and price access
- Variant IDs and option maps
- Cart/checkout API or approved browser hooks
- Order/checkout handoff rules
- Brand/support/content sources
- Test account or staging site

This gives the strongest reliability for finding products, comparing variants, adding/removing cart items, checkout handoff, and analytics.

## Crawler Status

Implemented/available:

- Public product endpoints first.
- Sitemap and robots discovery.
- Priority scoring for product/shop/category URLs.
- Skip rules for admin, login, cart, checkout, account, and static assets.
- Crawl4AI fallback for rendered pages.
- Deterministic product extraction from JSON-LD, Shopify/Woo-like JSON, framework payloads, embedded state, and visible text.
- Readiness scanner and capability reports.
- Crawl report storage for CRM inspection.
- Variants ingestion/API support.
- LLM extractor is gated by `LLM_EXTRACTOR_ENABLED=false` by default.

Known reality:

- No crawler works on every website in every condition.
- Login-only inventory, bot-protected pages, private APIs, and checkout/payment flows require client approval, whitelisting, feeds, API keys, or a platform adapter.

## CRM Status

Recent improvements:

- Light/dark theme readability fixed.
- Clients can be removed.
- Settings includes model, temperature, voice, embedding, RAG, crawler, CRM, and Client Panel keys.
- Client detail is tabbed: Overview, Readiness, Catalog, Crawl, Activity, Controls.
- Readiness/crawl reports are readable instead of raw JSON strips.
- Catalog review has images, filters, and pagination.
- Analytics includes KPIs, demand trend, product demand, intent mix, transport/status/latency breakdowns, site mix, peak day, and recent events.

## Admin Boundary

AI Hub `.env` owns AI/CRM/client-panel settings.

AI-KART website admin credentials belong only in:

```text
Vercel_website/backend/.env
```

AI Hub must not store AI-KART admin username/password.

## Deployment Docs

Use these files:

```text
AI Hub:       AI_salesman_plugin/aihub.md
AI-KART:      Vercel_website/aikart.md
Client Panel: client_panel/clientpanel.md
```

Deploy order:

1. AI Hub Docker app.
2. AI-KART backend/frontend and shared Nginx.
3. Client Panel.

## Verification Checklist

- `python -m pytest` passes in AI Hub.
- `npm run lint` and `npm run build` pass in `crm`.
- `docker compose config` passes and shows `127.0.0.1:5176:8585`.
- `http://127.0.0.1:5176/health` returns `200`.
- `http://143.198.5.97/aihub/health` returns `200` after shared Nginx reload.
- CRM uses `ai_kart`.
- The script tag loads from `/aihub/shopbot.js?site=ai_kart`.
- Client disabled means widget removed, but admin crawling can still run.
- Removing a client is a CRM soft delete and does not drop tenant catalog data.
- Public microphone access requires HTTPS; DNS plus HTTPS is the production target.
