# AI Salesman Hub - Agent Guide

This file describes the current project behavior and operating assumptions.

## Goal

Build a voice shopping assistant that works across four catalog acquisition paths:

- `1a` Shopify API: merchant shares Shopify API access.
- `1b` Shopify crawler: merchant does not share API/catalog access; we crawl the storefront.
- `2` Website API: a normal website provides product API access.
- `3` Website crawler: a normal website provides no API; we crawl public pages.

These are separate use cases. Do not silently replace one path with another.

## Runtime Entry

Use:

```powershell
python run.py
```

Current menu:

```text
1) Shopify
   a) Shopify API
   b) Shopify crawler
2) Website API
3) Website crawler
4) View data
0) Exit
```

Selecting `1 -> a` must run Shopify API ingestion.

Selecting `1 -> b` must run Shopify storefront crawler ingestion.

Selecting `4` shows source snapshots and live catalog data.

## Data Model

Each website gets its own PostgreSQL tenant schema:

```text
tenant_<site_id>
```

The active catalog used by RAG is:

```text
products
categories
```

Source snapshots are:

```text
catalog_source_products
catalog_sync_runs
```

Source names:

```text
shopify_api
shopify_crawler
website_api
website_crawler
```

Use these snapshots to compare API ingestion quality against crawler ingestion quality.

## Incremental Catalog Sync

Do not wipe catalogs on every run.

Expected behavior:

- Insert new products.
- Update changed products.
- Mark missing products inactive.
- Preserve embeddings for unchanged products.
- Re-vectorize only rows whose content changed or became inactive.
- Preserve cart/profile data.

`embedding IS NULL` means the product needs vectorization.

## AI Pipeline

Main endpoint:

```text
POST /v1/shop
```

Pipeline:

```text
STT -> guardrails -> RAG -> LLM -> guardrails -> TTS -> widget response
```

Model config:

```env
STT_MODEL=gpt-4o-mini-transcribe
STT_LANGUAGE=en
LLM_MODEL=gpt-4.1
TTS_MODEL=gpt-4o-mini-tts
TTS_VOICE=alloy
```

Provider:

```text
OpenAI only for STT, LLM, and TTS.
```

Do not reintroduce Groq/Gemini keys or provider paths.

## UI Actions

Supported important actions:

```text
SHOW_PRODUCTS
SHOW_COMPARISON
FILTER_PRODUCTS
NAVIGATE_TO
ADD_TO_CART
REMOVE_FROM_CART
UPDATE_CART_QUANTITY
SHOW_PRODUCT_DETAIL
CLEAR_CART
CHECKOUT
```

`SHOW_PRODUCTS` renders product cards in the injected widget.

`SHOW_COMPARISON` renders a side-by-side comparison for 2 to 4 products.

The widget implementation is:

```text
plugin/shopbot.js
```

## Shopify ScriptTag

On startup, the backend can update Shopify ScriptTags for installed shops.

The injected script should use the tenant site id:

```text
/shopbot.js?site=<site_id>
```

For current test Shopify site:

```text
/shopbot.js?site=pisszq_ay
```

## Important Files

- `run.py`: CLI entrypoint and source selection.
- `agent/ingestion.py`: Shopify API, website API, and crawler ingestion.
- `db/schema.sql`: tenant tables.
- `db/database.py`: tenant DB helpers and catalog inspection helpers.
- `api/main.py`: FastAPI routes, `/shopbot.js`, `/v1/shop`, `/v1/client-log`.
- `plugin/shopbot.js`: voice orb, product cards, comparison UI, cart actions.
- `agent/orchestrator.py`: AI pipeline.
- `agent/prompt.py`: LLM rules and examples.
- `agent/guardrails.py`: input/output validation.

## Debugging Notes

If the browser only loads `/shopbot.js` and does not call `/v1/shop`, the issue is client-side recording or permissions.

If logs show `/v1/client-log`, inspect the `CLIENT | ...` lines.

If `/v1/shop` runs and STT succeeds, failures after that are in RAG/LLM/TTS.

If products are found but UI does not move, inspect returned `ui_actions` and `plugin/shopbot.js` action handling.
