# AI Salesman Hub — Operational Project Guide

## What this project does

AI Salesman Hub is a voice-powered shopping assistant for Shopify-style stores.

- It ingests a merchant catalog into a PostgreSQL tenant schema.
- It runs a FastAPI backend with an AI pipeline (`STT -> guardrails -> RAG -> LLM -> TTS`).
- A storefront widget (`shopbot.js`) sends voice + interaction events to the backend and executes UI actions (cart updates, product details, filtering).

The project has per-tenant isolation using PostgreSQL schemas and is designed to work with:

- Shopify API sync
- Generic website crawler sync
- Third-party website API sync

## Core runtime path

1. Operator picks a run mode in `run.py`.
2. Ingestion functions in `agent/ingestion.py` normalize product data and call `_persist_catalog`.
3. `_persist_catalog` calls `init_tenant_schema()` in `db/database.py`.
4. `init_tenant_schema()` creates/activates tenant schema and applies `db/schema.sql`.
5. Runtime APIs in `api/main.py` serve chat/audio/cart endpoints and plugin bootstrap.
6. Conversation requests go through `agent/orchestrator.py` and use:
   - `agent/stt.py` for speech input,
   - `agent/rag.py` for retrieval,
   - `agent/llm.py` for response synthesis,
   - `agent/guardrails.py` for safety checks,
   - `agent/tts.py` for speech output.

## Major directories and responsibilities

- `agent/`
  - `orchestrator.py`: Pipeline orchestration and action handling.
  - `ingestion.py`: Product ingestion from Shopify API, crawler, and external product APIs.
  - `llm.py`: LLM calls and response schema orchestration.
  - `rag.py`: Vector generation + product retrieval.
  - `rag.py`: Vector search + fallback SQL retrieval logic.
  - `stt.py`: Speech-to-text.
  - `tts.py`: Text-to-speech.
  - `guardrails.py`: Input/output validation.
  - `prompt.py`: LLM prompt assembly.

- `api/`
  - `main.py`: FastAPI routes for widget, chat/audio/cart, and OAuth install webhooks.
  - `models.py`: Pydantic API models.
  - `middleware.py`: Request-level middleware.

- `db/`
  - `database.py`: DB connection pooling, schema creation, tenant access context managers.
  - `schema.sql`: Tenant schema tables (`products`, `categories`, `cart`, `user_profile`).
  - `seed.py`: Optional seed helper for local test data.

- `plugin/`
  - `shopbot.js`: Storefront widget (recording, SSE/API calls, and UI action execution).
  - `src/api.js`: Frontend API helper.

- `run.py`
  - CLI entrypoint for running ingestion flows and starting the backend server.

- `scripts/`
  - Operational helpers like forced sync, vectorization triggers, and other ad-hoc tasks.

## Tenant identity and schema behavior

Each tenant has a schema named `tenant_<site_id>`.

- `run.py` and ingestion modes accept optional `Target site_id`.
- If omitted, it is inferred from the store/domain URL and sanitized.
- `db/database.py` sets `search_path` per tenant before every tenant-scoped query.
- Ingress and storefront actions pass `site_id` explicitly via request form/body or env config.

Recent fix in this repo:

- URL-like site IDs now sanitize to SQL-safe identifiers (only lowercase letters, digits, underscore).
- Schema creation and `search_path` now use `psycopg.sql.Identifier` to prevent invalid SQL identifier syntax and improve safety.

## Key issue and fix that prompted this update

Observed failure when running crawler mode:

```
CREATE SCHEMA IF NOT EXISTS tenant_https___demo.vercel.store
```

This failed because dots in `site_id` produced invalid unquoted schema names.

Fix summary:

- `agent/ingestion.py`
  - `sanitize_site_id` now strips invalid characters and collapses repeats to underscores.
  - Leading digits are prefixed with `site_` to keep schemas valid.
- `db/database.py`
  - `CREATE SCHEMA` and `SET search_path` now use safe quoted identifiers.

## Environment variables used at runtime

- `GEMINI_API_KEY`
- `SHOPIFY_CLIENT_ID`
- `SHOPIFY_CLIENT_SECRET`
- `SHOPIFY_STORE_DOMAIN`
- `SHOPIFY_ACCESS_TOKEN`
- `DATABASE_URL`
- `AI_DEFAULT_SITE_ID`
- `DEFAULT_SITE_ID`
- `PUBLIC_API_URL`
- `AI_PLUGIN_SCRIPT_URL`
