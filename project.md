# AI Salesman Plugin - Project Overview & Status

Date: 2026-06-10

## About the Project
This project is an AI-powered voice shopping assistant ("Voice Orb") that can be injected into any storefront (currently integrated with a Vercel-based demo website). The assistant uses a combination of natural language processing (LLM), Text-To-Speech (TTS), Speech-To-Text (STT), and Retrieval-Augmented Generation (RAG) to understand user intent, answer questions, provide product recommendations, and perform storefront navigation actions like adding items to the cart or checking out. 

## Core Components

### 1. **Voice Orb Widget (Frontend / Injected Script)**
- **Location**: `plugin/shopbot.js`
- **Purpose**: A responsive, glassmorphic UI element injected onto the storefront. It listens to user voice input using the browser's MediaRecorder API, streams the audio to the backend, and processes returning JSON to execute UI actions (e.g. `SHOW_PRODUCTS`, `NAVIGATE_TO`, `ADD_TO_CART`).

### 2. **FastAPI Backend (`api/main.py`)**
- **Location**: `api/main.py`, `run.py`
- **Purpose**: Exposes the `/v1/shop` and WebSocket endpoints. It accepts the audio blob from the widget, passes it to the orchestrator, and returns the LLM response alongside actionable UI commands. 
- **Networking**: `run.py` automates starting the server and setting up an `ngrok` tunnel for HTTPS traffic so the browser can connect to it securely.

### 3. **AI Orchestrator & Agents (`agent/`)**
- **Location**: `agent/orchestrator.py`, `agent/prompt.py`
- **Purpose**: Connects the STT parser, LLM, and TTS engine. The system prompt (`agent/prompt.py`) rigorously instructs the LLM on how to behave as a cheerful AI assistant. It outputs JSON commands embedded within normal responses.

### 4. **RAG Vector Database & Ingestion (`db/` & `agent/ingestion.py`)**
- **Location**: `db/database.py` (PostgreSQL / pgvector), `agent/ingestion.py`
- **Purpose**: Automatically crawls the target store to fetch product details (Name, Brand, Price, Image, description) and loads them into the DB. It uses `pgvector` to build searchable embeddings so the LLM can lookup items semantically without needing the full catalog loaded in its context.

### 5. **Vercel Storefront Clone (External)**
- **Location**: `C:/Users/admin/Desktop/Vercel_website`
- **Purpose**: The demo e-commerce website where the `voice-orb` is embedded. We use a python script (`scripts/update_vercel.py`) to inject the active backend ngrok URL into the Vercel clone.

---

## Current Status

### What We Did Till Now
- **Fixed Voice Orb Visibility**: The orb wasn't showing because the frontend was using a stale `127.0.0.1` script URL instead of the ngrok HTTPS URL. We corrected the `.env` settings to properly use the ngrok URL.
- **Enabled Crawler Exclusion**: We excluded `/admin` paths from the catalog crawler to avoid hitting HTTP 401 errors.
- **Vercel Admin UI**: The Vercel clone has an Admin Panel `/admin` route which allows replenishing stock. A hardcoded Admin Panel link is currently injected via `api/index.py` at the bottom left of the storefront.

### What is Working ✅
- **Server Startup & Ngrok Tunneling**: `run.py` correctly provisions a tunnel and exposes the API.
- **Widget Injection**: The build script successfully injects `shopbot.js` into the Vercel site.
- **Audio Recording**: The `shopbot.js` successfully records user voice via the browser Media API and transmits it to the backend.
- **Database Search**: Postgres + pgvector indexing is functional, allowing product retrieval.
- **Navigation Commands**: General LLM navigation tasks (`NAVIGATE_TO` cart, etc.) are working.
- **LLM Product Identification (Precision Loss)**: Fixed the 64-bit ID corruption issue. The LLM is instructed to output IDs as strings, and the entire pipeline (frontend parser, guardrails, models, database) safely handles string-based IDs.
- **Admin Panel UI Placement**: The Admin Panel link on the Vercel site is now an aesthetic glassmorphic SVG gear icon with hover effects, matching the Voice Orb.
- **Debugging Auditability**: The backend now writes timestamped logs to the `logs/` directory alongside standard output.

### Edge Cases Resolved
- Fixed `run_stream` crash bugs in `orchestrator.py` by adding missing `site_id` arguments.
- Added `CLEAR_HISTORY` and `UPDATE_PREFERENCES` to allowed action whitelists so they are no longer silently dropped.
- Fixed duplicated prompt example numbering in `prompt.py`.

### What is Not Working / Broken ❌
- **None** - All known critical issues are resolved including resilient Vercel updater.

---

## Future Addons / Planned Changes
1. **Resilient Vercel Updater (COMPLETED)**: The build/deployment pipeline now fails gracefully if ngrok isn't available. Three scenarios are handled:
   - **Placeholder mode**: When no ngrok URL is found, deploys site with warning stub script
   - **Localhost mode**: When localhost URL is cached, deploys with local-only warning
   - **Valid ngrok mode**: When valid HTTPS ngrok URL is available, full widget injection proceeds
   
   Changes made:
   - `scripts/update_vercel.py`: Added graceful fallback to placeholder URL instead of exiting
   - `run.py`: Modified to use localhost URLs when ngrok unavailable instead of raising errors
   - `Vercel_website/scripts/inject-shopbot.mjs`: Added stub script injection for non-functional cases
   - Added proper warning messages and user guidance for each scenario
