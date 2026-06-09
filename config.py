"""
Central configuration — loads from .env or environment variables.
All modules import from here; never read os.environ directly.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent / ".env")

# OpenAI
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

# Models
STT_MODEL: str = os.getenv("STT_MODEL", "gpt-4o-mini-transcribe")
STT_LANGUAGE: str = os.getenv("STT_LANGUAGE", "").strip()
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4.1")
TTS_MODEL: str = os.getenv("TTS_MODEL", "gpt-4o-mini-tts")
TTS_VOICE: str = os.getenv("TTS_VOICE", "alloy")

# RAG
EMBEDDING_MODEL: str = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "10"))
RAG_TOP_N: int = int(os.getenv("RAG_TOP_N", "3"))

# LLM
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.20"))
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "1024"))

# Server
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8001"))
PUBLIC_API_URL: str = os.getenv("PUBLIC_API_URL", f"http://127.0.0.1:{PORT}")
CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")
DEFAULT_SITE_ID: str = os.getenv("AI_DEFAULT_SITE_ID", os.getenv("DEFAULT_SITE_ID", "site_1"))
VOICE_ORB_SITE_ID: str = os.getenv("VOICE_ORB_SITE_ID", DEFAULT_SITE_ID)
VOICE_ORB_API_URL: str = os.getenv("VOICE_ORB_API_URL", "").strip()

# Database
DATABASE_URL: str = os.getenv(
    "DATABASE_URL", "postgresql://shopbot:shopbot_password@localhost:5433/shopping_db"
)
BASE_DIR = Path(__file__).parent

# Shopify Integration
SHOPIFY_STORE_DOMAIN: str = os.getenv("SHOPIFY_STORE_DOMAIN", "")
SHOPIFY_ACCESS_TOKEN: str = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
SHOPIFY_CLIENT_ID: str = os.getenv("SHOPIFY_CLIENT_ID", "")
SHOPIFY_CLIENT_SECRET: str = os.getenv("SHOPIFY_CLIENT_SECRET", "")
SHOPIFY_SITE_URL: str = os.getenv("SHOPIFY_SITE_URL", "").strip()
SHOPIFY_SITE_ID: str = os.getenv("SHOPIFY_SITE_ID", "").strip()
SHOPIFY_CRAWL_FALLBACK_URL: str = os.getenv("SHOPIFY_CRAWL_FALLBACK_URL", "").strip()

# Third-party website ingestion
WEBSITE_API_URL: str = os.getenv("WEBSITE_API_URL", "").strip()
WEBSITE_API_METHOD: str = os.getenv("WEBSITE_API_METHOD", "GET").upper().strip()
WEBSITE_API_HEADERS_JSON: str = os.getenv("WEBSITE_API_HEADERS_JSON", "").strip()
WEBSITE_CRAWL_URL: str = os.getenv("WEBSITE_CRAWL_URL", "").strip()
WEBSITE_CRAWL_MAX_PAGES: int = int(os.getenv("WEBSITE_CRAWL_MAX_PAGES", "60"))
WEBSITE_CRAWL_MAX_DEPTH: int = int(os.getenv("WEBSITE_CRAWL_MAX_DEPTH", "3"))

# Guardrail Settings
MAX_TRANSCRIPT_CHARS: int = 2000
MAX_RESPONSE_CHARS: int = 3000
MAX_UI_ACTIONS: int = 5

# Valid UI Action Types
VALID_UI_ACTIONS = {
    "SHOW_PRODUCTS",
    "FILTER_PRODUCTS",
    "NAVIGATE_TO",
    "SORT_PRODUCTS",
    "ADD_TO_CART",
    "REMOVE_FROM_CART",
    "SHOW_PRODUCT_DETAIL",
    "CLEAR_FILTERS",
    "CLEAR_CART",
    "CHECKOUT",
    "UPDATE_CART_QUANTITY",
}
