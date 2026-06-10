# AI Salesman Hub

This project now does one thing:

1. crawl a public website from `CURRENT_URL`
2. start the backend
3. print and save the widget `<script>` tag for manual HTML injection

Current target example:

```text
https://vercelclonedwebsite.vercel.app/
```

## Flow Diagram

![AI Salesman Plugin Flow](docs/ai_salesman_plugin_flow.svg)

The diagram above shows the full operator flow from `.env` setup to crawl, backend startup, manual script injection, and live storefront behavior.

## Run

```powershell
python run.py
```

`run.py` will:

- read `CURRENT_URL` and `CURRENT_SITE_ID` from `.env`
- crawl the target site and build the catalog
- start the FastAPI backend
- open an ngrok URL when available
- save the final widget tag into `.env` as `MANUAL_WIDGET_SCRIPT`

## Required `.env`

```env
OPENAI_API_KEY=
DATABASE_URL=postgresql://shopbot:shopbot_password@localhost:5433/shopping_db
HOST=0.0.0.0
PORT=8001

CURRENT_URL=https://vercelclonedwebsite.vercel.app/
CURRENT_SITE_ID=https_demo_vercel_store
CRAWL_MAX_PAGES=1024
CRAWL_MAX_DEPTH=100

MANUAL_WIDGET_SCRIPT=
PUBLIC_WIDGET_SCRIPT_URL=
PUBLIC_API_URL=
```

## Manual Injection

After startup, the saved script looks like:

```html
<script src="https://your-public-backend.ngrok-free.app/shopbot.js?site=https_demo_vercel_store"></script>
```

Paste that directly into the target site HTML.

If the target site has CSP, allow the backend origin in:

- `script-src`
- `connect-src`
- `frame-src`

## Local Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
docker-compose up -d
python run.py
```

## Catalog Storage

Each crawled target uses a tenant schema:

```text
tenant_<site_id>
```

Relevant tables:

```text
products
categories
catalog_source_products
catalog_sync_runs
```

Current crawler source name:

```text
custom_url_crawler
```
