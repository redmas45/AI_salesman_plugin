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

### What is Pending & Blocked ❌
- **Router Port Forwarding**: External access to the public IP is blocked by the router. To make the service accessible over the public internet, router port forwarding for ports `80` and `443` is required.
- **Self-Signed Certificate Warning**: Intranet/LAN IP HTTPS runs on a self-signed certificate, triggering browser warnings. True production deployment requires a public domain with Caddy/Let's Encrypt certificates.
- **Catalog/Inventory Expansion**: Expand `products.json` inventory to cover wider test cases without disrupting existing IDs or RAG embeddings.
- **UX Fine-tuning**: Improve product card clickable areas and refine category/sorting menu positions.

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

## Verification & QA

### Automation Tests
- Running `pytest` runs contract tests, DB seed checks, and endpoint schema validation.
- Run tests: `pytest`

### Manual Smoke Test Checklist
1. Start stack: `python run.py`
2. Open storefront: `https://192.168.68.71:8484` (verify widget renders).
3. Test greetings: Say "hello" or "hi" (verify conversational greeting response).
4. Search products: Say "show me mugs" (verify recommendation panel filters grid).
5. Cart: Say "add bomber jacket to cart" (verify item added and drawer opens).
6. Admin Panel: Log in, verify RAG status, test "Generate Description with AI" button.

---

## Next Step: Real-time Voice Streaming via WebSockets (Option 1)

### Planned Architecture: Sentence-Buffered Parallel Streaming
We will implement a high-performance streaming pipeline to achieve sub-second voice response latency using our existing standard OpenAI API key and models (without ElevenLabs):
1. **Audio Input Streaming**: Client streams mic audio in small binary chunks (100–200ms WebM/Opus or WAV) via WebSockets to `/ws/chat`.
2. **Text Generation Streaming**: The FastAPI backend invokes OpenAI LLM Chat Completions with `stream=True`.
3. **Sentence Buffering & Parallel TTS**: As response tokens arrive, they are accumulated on the backend. When a sentence boundary (punctuation like `.`, `?`, `!`) is reached:
   - A concurrent background task is spun up to call OpenAI TTS (`tts-1` model) for just that sentence.
   - The resulting audio chunk is immediately streamed back to the client over the WebSocket.
4. **Seamless Playback Queue**: The frontend uses the browser's Web Audio API to queue incoming audio chunks and play them back sequentially without pauses.
5. **Barge-in (Interruption Handling)**: If the user starts speaking during playback, the client sends an `INTERRUPT` frame, prompting the backend to immediately cancel all active LLM/TTS generation tasks, and the client stops audio playback.

### Implementation Checklist
- [ ] Refactor `/ws/chat` in [api/main.py](file:///c:/Users/admin/Desktop/AI_salesman_plugin/api/main.py) to orchestrate sentence-level parallel synthesis and streaming.
- [ ] Implement browser microphone chunk streaming in the frontend widget (source code in `plugin/src/index.js` or separate helper).
- [ ] Build the audio queueing and playing mechanism in the frontend using standard browser Web Audio API.
- [ ] Implement client-side interrupt triggers (e.g. user speaks/clicks) and server-side task cancellation.

