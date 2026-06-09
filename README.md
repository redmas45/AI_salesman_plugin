# AI Salesman Hub

Voice shopping assistant for Shopify and normal websites.

The system ingests product catalogs into PostgreSQL, vectorizes product text with pgvector, serves a FastAPI backend, and injects a `shopbot.js` voice orb into storefronts. Customers can speak naturally, search products, compare products side by side, add items to cart, and hear spoken responses.

## Supported Modes

Run the project with:

```powershell
python run.py
```

Menu:

```text
1) Shopify
   a) Shopify API
   b) Shopify crawler
2) Website API
3) Website crawler
4) View data
0) Exit
```

Mode meanings:

- `1a Shopify API`: merchant provides Shopify API access. Products are fetched directly from Shopify Admin API.
- `1b Shopify crawler`: merchant does not provide API/catalog access. The storefront is crawled and scraped.
- `2 Website API`: a normal website provides a product API URL.
- `3 Website crawler`: a normal website provides no API. The crawler builds the catalog from public pages.
- `4 View data`: inspect stored catalog data and source snapshots.

`1a` and `1b` are separate business paths. Selecting `1b` must crawl the storefront even if API data already exists.

## Catalog Storage

Every website has its own tenant schema:

```text
tenant_<site_id>
```

Example:

```text
tenant_pisszq_ay
```

The main runtime catalog lives in:

```text
products
categories
```

Source snapshots live in:

```text
catalog_source_products
catalog_sync_runs
```

Known source names:

```text
shopify_api
shopify_crawler
website_api
website_crawler
```

This lets you compare what came from Shopify API versus what the crawler found.

## Incremental Sync

Catalog sync is incremental.

- New products are inserted.
- Changed products are updated.
- Removed/missing products are marked inactive.
- Unchanged products keep their existing embeddings.
- Only new/changed/deactivated rows are vectorized again.
- Cart and user profile data are not wiped during catalog sync.

This keeps repeat runs fast when the catalog has not changed.

## AI Pipeline

Voice request flow:

```text
Browser audio
-> OpenAI STT
-> input guardrails
-> pgvector RAG retrieval
-> OpenAI LLM
-> output guardrails
-> OpenAI TTS
-> widget UI actions + spoken reply
```

Current model environment:

```env
STT_MODEL=gpt-4o-mini-transcribe
STT_LANGUAGE=en
LLM_MODEL=gpt-4.1
TTS_MODEL=gpt-4o-mini-tts
TTS_VOICE=alloy
```

Embeddings:

```env
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

## Widget Behavior

The injected `shopbot.js` supports:

- microphone recording
- spoken AI response playback
- product cards for `SHOW_PRODUCTS`
- side-by-side comparison table for `SHOW_COMPARISON`
- Shopify cart add/clear actions
- navigation actions
- client diagnostics via `/v1/client-log`

Comparison works for 2, 3, or 4 products across all catalog sources.

## Shopify Setup

Required `.env` keys for Shopify API mode:

```env
SHOPIFY_STORE_DOMAIN=pisszq-ay.myshopify.com
SHOPIFY_ACCESS_TOKEN=
SHOPIFY_CLIENT_ID=
SHOPIFY_CLIENT_SECRET=
SHOPIFY_SITE_URL=https://pisszq-ay.myshopify.com/?pb=0
SHOPIFY_SITE_ID=pisszq_ay
SHOPIFY_CRAWL_FALLBACK_URL=https://pisszq-ay.myshopify.com/?pb=0
```

Required Shopify scopes:

```text
read_products,read_inventory
```

For automatic ScriptTag injection:

```text
read_script_tags,write_script_tags
```

The app auto-updates Shopify ScriptTags on server startup when a Shopify installation exists in the global DB.

## External Website Setup

For Website API mode:

```env
WEBSITE_API_URL=
WEBSITE_API_METHOD=GET
WEBSITE_API_HEADERS_JSON=
VOICE_ORB_SITE_ID=
```

For Website crawler mode:

```env
WEBSITE_CRAWL_URL=
WEBSITE_CRAWL_MAX_PAGES=120
WEBSITE_CRAWL_MAX_DEPTH=10
VOICE_ORB_SITE_ID=
```

Manual one-line widget install:

```html
<script src="https://your-public-api.example.com/shopbot.js" data-site-id="your_site_id" data-api-url="https://your-public-api.example.com"></script>
```

## Local Setup

Install dependencies:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Start Postgres/pgvector:

```powershell
docker-compose up -d
```

Run:

```powershell
python run.py
```

## Data Inspection

Use:

```text
4) View data
```

Then preview:

```text
live_catalog
shopify_api
shopify_crawler
website_api
website_crawler
```

`live_catalog` is the current catalog used by voice/RAG. Source names show snapshots from each ingestion path.
