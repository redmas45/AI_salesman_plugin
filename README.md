# AI Salesman Hub

This project is the backend and AI agent engine for the Voice Orb. It is designed to sync with the AI-KART storefront and can run on localhost, the local Wi-Fi/LAN, a public static IP, a DNS domain, or a tunnel.

## Current Milestone

**L3.5** is the current fallback point.

- GitHub sync comment: `L 3.5`
- Date: 2026-06-12
- Meaning: if later changes break the hub/spoke setup, roll back to this synced state before debugging forward.

The core workflow:
1. Crawls a public website from `CURRENT_URL` to build the catalog database.
2. Starts the FastAPI backend, which handles chat, voice, cart, checkout, and RAG status.
3. Serves the Voice Orb script and `/v1/*` APIs through the HTTPS entrypoint used by the client/spoke test site.

Current target example:
```text
https://192.168.68.71:8484/
```

## Flow Diagram

![AI Salesman Plugin Flow](docs/ai_salesman_plugin_flow.svg)

## Modular Startup Workflow

Use `run.py` to start the HTTPS proxy, local spoke storefront simulator, and backend:

```powershell
python run.py
```

Stop both processes:

```powershell
Ctrl+C
```

Default intranet topology:
```text
Caddy HTTPS:       https://<this-pc-lan-ip>:8484
Spoke storefront:  http://0.0.0.0:8584
AI HUB backend:    http://127.0.0.1:8585
Browser routes:    /shopbot.js and /v1/* proxy to the HUB
```

For intranet mode, open the printed `Wi-Fi/LAN URL` from other devices on the same Wi-Fi. Caddy uses a local self-signed certificate for the LAN IP, so browsers may show a warning. Accepting the warning is enough for internal testing; a real customer URL should use a domain with trusted HTTPS.

Deployment mode is controlled by `.env`:

```env
DEPLOYMENT_MODE=intranet
```

Supported modes:
- `intranet`: same Wi-Fi/LAN, no router port forwarding.
- `public-ip`: direct public IP hosting after router/firewall forwarding is configured.
- `domain`: DNS hostname with Caddy-managed HTTPS.
- `custom`: tunnel or external HTTPS origin, such as Cloudflare Tunnel/ngrok.

Switch modes with:

```powershell
.\scripts\set_deployment_mode.ps1 -Mode intranet
.\scripts\set_deployment_mode.ps1 -Mode public-ip -Origin https://103.97.243.133
.\scripts\set_deployment_mode.ps1 -Mode domain -Domain shop.example.com
.\scripts\set_deployment_mode.ps1 -Mode custom -Origin https://example.trycloudflare.com
```

After switching, restart:

```powershell
python run.py
```

## Client Admin Boundary

This repo is the AI HUB. It does not own or inject a client admin page.

For the local AI-KART spoke simulator, admin/product editing lives in the separate `Vercel_website` project. The HUB only exposes neutral catalog APIs such as `/v1/catalog/status` and `/v1/catalog/crawler/run`.

The backend crawler treats `/api/products.json` as the authoritative storefront catalog when present, so client-side catalog edits are picked up by periodic RAG sync.

## Local Spoke Simulator

`C:\Users\admin\Desktop\Vercel_website` is treated as a customer/spoke website.

Standalone spoke mode:

```powershell
cd C:\Users\admin\Desktop\Vercel_website
python run.py
```

This starts the storefront/admin without the Voice Orb. Its search bar reads `out/api/products.json`.

AI-enabled spoke simulation:

```powershell
cd C:\Users\admin\Desktop\Vercel_website
$env:ENABLE_AI_WIDGET="true"
$env:SHOPBOT_HUB_ORIGIN="http://127.0.0.1:8585"
python run.py
```

That injects one client-style script at request time. The static `out/*.html` files stay clean by default.

The AI HUB `python run.py` still starts the full intranet stack and injects/proxies the one-script widget through Caddy.

## Terminal Turn Logs

Every completed turn now prints readable terminal diagnostics:

```text
AI_CONVO | user: show me caps
AI_CONVO | ai_reply: Here are two cap options.
AI_CONVO | method_used: websocket | status: ok | time_taken: 1842ms | pipeline: 1750ms | actions: 1
[SHOPBOT TURN] transport=websocket status=ok site=ai_kart_main elapsed=1842ms pipeline=1750ms actions=1 transcript="show me caps" response="Here are two cap options."
```

`method_used` / `transport` shows whether the turn used `websocket`, `legacy-http`, `legacy-sse`, or `legacy-ws`.

## Crawler Architecture (100% Accuracy)

The AI Salesman backend features a highly specialized crawler capable of achieving 100% precision and recall against Next.js storefronts. 
Rather than relying on fragile HTML text scraping or heuristic regex rules, the crawler intercepts the underlying frontend framework state. 

When crawling a Next.js site, it dynamically extracts:
- `__NEXT_DATA__` JSON payloads embedded in the initial HTML
- React Server Components (RSC) Flight data payloads pushed by Next.js
- `application/ld+json` semantic SEO tags

This allows the crawler to directly reconstruct the exact JSON data structures that power the storefront, resulting in perfectly accurate product titles, prices, descriptions, and IDs, with zero hallucination.

## Required `.env`

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
HOST=0.0.0.0
PORT=8001

CURRENT_URL=http://127.0.0.1:8584/
DEPLOYMENT_MODE=intranet
STOREFRONT_PORT=8584
BACKEND_PORT=8585
HTTPS_PORT=8484
HTTP_REDIRECT_PORT=0
CURRENT_SITE_ID=ai_kart_main
CRAWL_MAX_PAGES=1024
CRAWL_MAX_DEPTH=100
CRAWL_ON_STARTUP=true

MANUAL_WIDGET_SCRIPT=
PUBLIC_WIDGET_SCRIPT_URL=
PUBLIC_API_URL=
PUBLIC_STOREFRONT_ORIGIN=
PUBLIC_HTTPS_ORIGIN=
```

`CURRENT_SITE_ID` is a tenant/catalog namespace used by the backend database and RAG sync. The current value `ai_kart_main` is not a live URL and does not mean the old storefront owner is still connected. If you rename it later, update `CURRENT_SITE_ID`, `AI_DEFAULT_SITE_ID`, `DEFAULT_SITE_ID`, and the `site=` query parameter together so the crawler, widget, and RAG schema stay aligned.

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
