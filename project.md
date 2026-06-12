# AI Salesman Plugin - Project Overview & Status

Date: 2026-06-11

## About the Project
An AI-powered voice shopping assistant ("Voice Orb") injected into the storefront (`AI-KART`). It uses natural language processing (LLM), Text-To-Speech (TTS), Speech-To-Text (STT), and Retrieval-Augmented Generation (RAG) to recommend products, answer customer queries, and execute storefront actions (e.g., adding to cart, navigating, checkout).

---

## Core Components

1. **Voice Orb Widget (Frontend / Injected Script)**
   - **Location**: `plugin/shopbot.js`
   - **Purpose**: Glassmorphic UI element injected onto the storefront. Streams recorded user voice via browser Media API to the backend and handles returning UI action events.
2. **FastAPI Backend (`api/main.py`)**
   - **Location**: `api/main.py`, `run.py`
   - **Purpose**: Runs private API on `127.0.0.1:8585` (proxied same-origin by storefront on `:8484` or `:8584`).
3. **AI Orchestrator & Agents (`agent/`)**
   - **Location**: `agent/orchestrator.py`, `agent/prompt.py`
   - **Purpose**: Connects STT, LLM (with system prompt in `prompt.py`), and TTS.
4. **RAG Database & Ingestion (`db/` & `agent/ingestion.py`)**
   - **Location**: `db/database.py`, `agent/ingestion.py`
   - **Purpose**: Crawls the catalog, calculates embeddings, and runs semantic search in PostgreSQL (pgvector).
5. **Storefront Clone (`Vercel_website/`)**
   - **Location**: `C:/Users/admin/Desktop/Vercel_website`
   - **Purpose**: E-commerce storefront with premium branding (AI-KART) and custom cart integrations.

---

## Current Status Overview

### What is Fixed & Working ✅
- **BOM in `.env` (STT Pipeline Heart)**: Resolved a critical pipeline blocker where `OPENAI_API_KEY` was not loaded due to a Byte Order Mark (`\ufeff`) in the `.env` file, causing transcription failures. Stripped the BOM from `.env` and added a robust fallback in `config.py`.
- **Microphone Z-Index Layering**: Changed `#shopbot-widget` z-index to `2147483647` (the absolute maximum possible CSS z-index) to guarantee the Voice Orb and mic button always float above storefront overlays, drawers, and panels.
- **Side-by-Side Product Comparison ("Stat Card")**: Added a premium comparative layout for `SHOW_COMPARISON` intent, displaying compared items side-by-side with matched attributes (Price, Brand, Category, Description) and direct "Add to Cart" actions.
- **Detail-Page Product Auto-Inclusion**: Automatically detects if the customer is on a product details view and prepends the currently viewed product to the comparison grid.
- **Comparison UI Squeezing Fix**: Refactored the results overlay element to use a direct flex-row flow during comparisons to prevent nested containers from adding horizontal or vertical scrollbars to compared product cards.
- **Single-Command Startup**: `python run.py` launches Caddy, the storefront, and backend in a unified supervisor loop.
- **Modular Deployment Modes**: Persistence and setup scripts for `intranet` (LAN Wi-Fi testing) and `public-ip` modes.
- **Voice-Cart Integrations**:
  - Storefront resolves both catalog handles and numeric backend IDs.
  - Large product IDs are serialized as JSON strings to prevent JS precision loss.
  - Interactive actions handled: `ADD_TO_CART`, `NAVIGATE_TO`, `CLEAR_CART`, `CHECKOUT`, `SHOW_PRODUCTS`, `FILTER_PRODUCTS`, `SHOW_PRODUCT_DETAIL`, `SORT_PRODUCTS`.
- **Admin Panel UI & Functions**: Labeled `Admin` page with live product management (Add/Update/Delete) and AI-generated product descriptions.
- **Voice Widget UI**: Clear/reset of conversation history, displaying `Listening...` and `Analyzing...` state indicators.
- **Checkout Process**: Invoice PDF generation verified using `reportlab`.
- **Security Hardening**: Basic login rate limiting, same-origin restrictions, security headers (CSP, HSTS, Frame Options), and dynamic admin password generation.
- **Multi-tenant isolation**: Sites schema separation backed by `tenant_ai_kart_main`.
- **Crawler Stabilization**: Incremental vectorization of new catalog items only, with startup crawler sync.


---

## Deployment Architecture

### Mode Configuration
Controlled via `DEPLOYMENT_MODE` in `.env`:
- `intranet` (Current): LAN testing at `https://192.168.68.71:8484`.
- `public-ip`: Binds storefront and API endpoints directly to a global static IP.
- `domain`: Maps standard domain name (e.g., `example.com`) to public IP.

### Port Mappings (Intranet Mode)
- **Caddy HTTPS Entry**: `8484` (Proxies all traffic to storefront)
- **Storefront/Admin Private**: `8584`
- **FastAPI Backend Private**: `8585`
- **Postgres Database**: `5434`

---

### Manual Smoke Test Checklist
1. Start stack: `python run.py`
2. Open storefront: `https://192.168.68.71:8484` (verify widget renders).
3. Test greetings: Say "hello" or "hi" (verify conversational greeting response).
4. Search products: Say "show me mugs" (verify recommendation panel filters grid).
5. Cart: Say "add bomber jacket to cart" (verify item added and drawer opens).
6. Admin Panel: Log in, verify RAG status, test "Generate Description with AI" button.

---

## Voice Transport Status

The active widget voice path is the legacy turn-based HTTP flow:
1. Browser records one `audio.webm` blob with `MediaRecorder`.
2. Widget posts the blob to `POST /v1/shop` with `site_id` and conversation history.
3. Backend returns transcript, response text, optional `audio_b64`, and `ui_actions`.
4. Widget plays the returned audio and executes storefront actions.

