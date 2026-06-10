# AI Salesman Hub

This project is the backend and AI agent engine for the Voice Orb. It is designed to automatically sync with your cloned Vercel Storefront.

The core workflow:
1. Crawls a public website from `CURRENT_URL` to build the catalog database.
2. Starts the FastAPI backend, which handles chat and voice via an `ngrok` tunnel.
3. Automatically updates the connected Vercel storefront with the new ngrok URL so the Voice Orb stays synced.

Current target example:
```text
https://vercelclonedwebsite.vercel.app/
```

## Flow Diagram

![AI Salesman Plugin Flow](docs/ai_salesman_plugin_flow.svg)

## Startup Workflow (Important)

Because this project uses the free tier of ngrok, your public backend URL changes every time you restart the server. Your live website needs to be updated with this new URL. 

To start working, open **two separate terminal windows**:

**Terminal 1:**
```powershell
python run.py
```
This starts the backend, crawls the catalog, and generates a new `ngrok` URL (saving it to `.env`). **Leave this running.**

**Terminal 2:**
```powershell
python update_vercel.py
```
This script will:
1. Detect your new ngrok URL from `.env`.
2. Connect to your `vercel_cloned_website` project and update the `SHOPBOT_API_URL` environment variable.
3. Automatically redeploy the site to production.

Once Terminal 2 says the deployment is successful, you can close Terminal 2. Your live website is now connected to your active backend!

## Vercel Integration

The Vercel storefront (`Vercel_website`) has been customized with the following integrations:
1. **Auto-Injection:** A custom script (`scripts/inject-shopbot.mjs`) automatically reads the `SHOPBOT_API_URL` environment variable and injects the Voice Orb `<script>` tag into all static HTML files during the Vercel build process.
2. **CSP Fixes:** The backend proxy in Vercel (`api/index.py`) has been modified to allow `script-src` and `media-src` from `https://*.ngrok-free.app`, ensuring that the Voice Orb and its text-to-speech audio are not blocked by the browser.

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
