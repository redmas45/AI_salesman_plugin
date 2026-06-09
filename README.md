# 🛍️ AI Salesman Hub — Shopify B2B SaaS App

A production-ready, fully-integrated Voice AI Shopping Assistant designed for Shopify merchants.  
Any Shopify merchant can install this app via OAuth. Once installed, it automatically syncs their entire product catalog into a high-performance Vector Database (RAG) and embeds a voice-enabled shopping widget directly into their storefront.

Customers speak naturally → the system understands intent → retrieves real products using vector search → controls the website in real-time → responds with voice.

---

## 🎯 The Vision & Goal

This project has evolved from a simple scraping bot into a **true B2B SaaS Shopify App**.
1. **The Merchant** installs our app from their Shopify admin dashboard.
2. **Our Backend** (the Hub Server) automatically syncs their entire store catalog into our AI's "brain" (Vector Database / RAG).
3. **The Shopper** visits the merchant's website, clicks our injected microphone widget, and talks to the AI to find products, check inventory, or get recommendations based on the actual catalog data.

---

## 🏗️ Architecture

Our robust architecture leverages a **modular, multi-model approach** to ensure a highly resilient, fail-safe scenario. We integrate natively with the Shopify API for seamless catalog ingestion.

```
Shopify Storefront & Admin
        │
        ▼
┌─────────────────────┐
│  1. Shopify OAuth   │  Secure installation & API token generation
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  2. Background Sync │  REST API pulling products, variants, & inventory
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  3. RAG Vector DB   │  PostgreSQL (pgvector) + sentence-transformers
│                     │  Computes embeddings for fast semantic search
└─────────────────────┘
```

When a customer talks to the injected `shopbot.js` widget on the storefront, the audio goes through this pipeline:

```
Customer Audio (WAV/WebM/MP3)
        │
        ▼
┌─────────────────────┐
│  1. Whisper STT     │  OpenAI Whisper (whisper-1)
└──────────┬──────────┘
           │ transcript
           ▼
┌─────────────────────┐
│  2. RAG Retrieval   │  Fetches relevant synced Shopify products
└──────────┬──────────┘
           │ product_context
           ▼
┌─────────────────────┐
│  3. LLM Agent       │  OpenAI Chat Completions (gpt-4o-mini)
│                     │  → {response_text, intent, ui_actions}
└──────────┬──────────┘
           │ structured_output
           ▼
┌─────────────────────┐
│  4. TTS             │  OpenAI TTS (tts-1)
└──────────┬──────────┘
           │ audio_bytes
           ▼
┌─────────────────────┐
│  5. Widget Response │  {ui_actions, audio_b64, transcript, response_text}
└─────────────────────┘
```

---

## 🚀 Key Features & Highlights

- **Native Shopify OAuth**: Merchants can install the AI Salesman with a single click. The system securely handles the OAuth redirect flow and stores permanent access tokens.
- **Automated Catalog Sync**: The moment a merchant installs the app, a background task automatically pulls their active products, variants, prices, and inventory using the Shopify API.
- **Multi-Model Fail-Safe Design**: By separating concerns into highly specialized models (STT, LLM, Embedding, TTS), the pipeline ensures rapid execution and fail-safe redundancy.
- **PostgreSQL Vector Database**: Uses an enterprise-grade `pgvector` integration. This enables executing advanced cosine similarity (`<=>`) semantic searches intertwined with standard SQL WHERE clauses (like price caps) in a single, lightning-fast database transaction.
- **Real-Time UI Orchestration**: The AI dynamically generates structured JSON `ui_actions` (like `FILTER_PRODUCTS` or `ADD_TO_CART`) which command the merchant's storefront UI state without requiring page reloads.

---

## 🛠️ Tech Stack

| Layer       | Technology                              | Description                               |
|-------------|------------------------------------------|-------------------------------------------|
| **Platform**| FastAPI + Uvicorn                        | High-performance asynchronous API         |
| **OAuth**   | Shopify Partner API                      | Secure B2B installation flow              |
| **STT**     | `whisper-1` via OpenAI        | Ultra-fast speech-to-text                 |
| **LLM**     | `gpt-4o-mini` via OpenAI      | Reasoning, entity extraction, and JSON    |
| **TTS**     | `tts-1` via OpenAI             | Low-latency voice synthesis               |
| **Embeddings** | `all-MiniLM-L6-v2` (384-dim)         | Semantic vector generation                |
| **Vector DB** | PostgreSQL + `pgvector`                | Advanced hybrid search (semantic + SQL)   |
| **Widget**  | Vanilla JS (`shopbot.js`)                | Injected UI bubble for the storefront     |

---

## ⚡ Quick Start & Setup Guide

### 1. Clone & Install

```bash
cd AI_salesman_plugin

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
You must create a `.env` file in the root directory. Copy the `.env.example` template:
```bash
cp .env.example .env
```
Open the `.env` file and configure the following keys:
- `OPENAI_API_KEY`: Get this from OpenAI Console.
- `SHOPIFY_CLIENT_ID` & `SHOPIFY_CLIENT_SECRET`: Create an App in your Shopify Partner Dashboard to get these.
- `SHOPIFY_STORE_DOMAIN`: Your store's URL (e.g., `pisszq-ay.myshopify.com`).

### 3. Boot Up PostgreSQL Vector Database
Ensure you have Docker Desktop installed and running. Then spin up the database container:
```bash
docker-compose up -d
```
*Note: The first time you run this, it will download the PostgreSQL pgvector image.*

### 4. Start the Hub Server
To start the backend server and automatically set up the public Ngrok tunnel, run:
```bash
python run.py
```
**Important:** When the server starts, it will print a huge block of text in the terminal saying **"ACTION REQUIRED"**. It will give you your unique Ngrok public URL.

### 5. Configure Shopify Partner Dashboard
1. Go to your Shopify Partner Dashboard.
2. Select your App.
3. Update the **App URL** to match the install link printed in the terminal (e.g., `https://<random>.ngrok-free.app/install?shop=your-store.myshopify.com`).
4. Update the **Allowed redirection URL** to the callback link printed in the terminal (e.g., `https://<random>.ngrok-free.app/v1/shopify/callback`).
5. Click **Release** or Save.

### 6. Install the App
Open a new browser tab and navigate to the **App URL** you just configured. This will trigger the OAuth installation flow on your Shopify store, and automatically sync your catalog into the Vector Database!

## Widget script for external websites (One-line install)

For Shopify installs, the app can still auto-add the ScriptTag.

For any custom/non-Shopify website (including crawler mode), paste this single line once before `</body>`:

```html
<script src="https://vercelclonedwebsite.vercel.app/shopbot.js" data-site-id="your_site_id" data-api-url="https://vercelclonedwebsite.vercel.app"></script>
```

If you want, you can also omit `data-site-id` and use:

```html
<script src="https://vercelclonedwebsite.vercel.app/shopbot.js?shop=your_site_id&api=https://vercelclonedwebsite.vercel.app"></script>
```

`data-site-id` can be a fixed tenant id such as `https_demo_vercel_store`.
If `WEBSITE_API_URL` is empty in `.env`, option **2** (website API) will fallback to crawler mode.
If `WEBSITE_API_URL` is empty, option **2** will use crawler mode with `WEBSITE_CRAWL_URL`, `WEBSITE_CRAWL_MAX_PAGES`, and `WEBSITE_CRAWL_MAX_DEPTH` automatically.

---

## 💻 Daily Usage (Restarting your PC)

If you turn off your PC and need to boot the AI Server back up the next day, it is incredibly simple. `run.py` acts as your **single point of entry**.

1. **Start Docker Desktop** (if it doesn't open automatically on boot).
2. Open your terminal in the `AI_salesman_plugin` folder.
3. Activate the virtual environment: `.venv\Scripts\activate`
4. Run the server:
```bash
python run.py
```
*That's it! This single command safely restarts Uvicorn and Ngrok automatically.*

*(Note: Because Ngrok generates a new random URL every time it restarts on the free tier, you will need to quickly update your Shopify Partner Dashboard with the new URL printed in the terminal).*

---

## 🔄 The Road Ahead (Next Steps)
1. Injecting `shopbot.js` directly into the merchant's active Shopify Theme using ScriptTags or Theme App Extensions.
2. Deploying the Hub Server to the cloud (Render, AWS) to make the OAuth flow accessible to the public internet.
3. Enhancing the UI/UX of the floating voice widget to give a premium, polished feel to any storefront it is installed on.


