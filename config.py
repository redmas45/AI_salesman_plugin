"""Central configuration loaded from the project .env file."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

STT_MODEL: str = os.getenv("STT_MODEL", "gpt-4o-mini-transcribe")
STT_LANGUAGE: str = os.getenv("STT_LANGUAGE", "").strip()
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4.1")
TTS_MODEL: str = os.getenv("TTS_MODEL", "gpt-4o-mini-tts")
TTS_VOICE: str = os.getenv("TTS_VOICE", "alloy")

EMBEDDING_MODEL: str = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "10"))
RAG_TOP_N: int = int(os.getenv("RAG_TOP_N", "3"))

LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.20"))
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "1024"))

HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8001"))
PUBLIC_API_URL: str = os.getenv("PUBLIC_API_URL", f"http://127.0.0.1:{PORT}").strip()
CORS_ORIGINS: list[str] = [item.strip() for item in os.getenv("CORS_ORIGINS", "*").split(",")]

DEFAULT_SITE_ID: str = os.getenv(
    "AI_DEFAULT_SITE_ID",
    os.getenv("DEFAULT_SITE_ID", "site_1"),
).strip().strip("\"'")
CURRENT_SITE_ID: str = os.getenv("CURRENT_SITE_ID", DEFAULT_SITE_ID).strip().strip("\"'")
CURRENT_URL: str = os.getenv("CURRENT_URL", "").strip()
MANUAL_WIDGET_SCRIPT: str = os.getenv("MANUAL_WIDGET_SCRIPT", "").strip()
PUBLIC_WIDGET_SCRIPT_URL: str = os.getenv("PUBLIC_WIDGET_SCRIPT_URL", "").strip()
VOICE_ORB_API_URL: str = os.getenv("VOICE_ORB_API_URL", "").strip()

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://shopbot:shopbot_password@localhost:5433/shopping_db",
)
BASE_DIR = Path(__file__).parent

CRAWL_MAX_PAGES: int = int(os.getenv("CRAWL_MAX_PAGES", "60"))
CRAWL_MAX_DEPTH: int = int(os.getenv("CRAWL_MAX_DEPTH", "3"))

MAX_TRANSCRIPT_CHARS: int = 2000
MAX_RESPONSE_CHARS: int = 3000
MAX_UI_ACTIONS: int = 5

VALID_UI_ACTIONS = {
    "SHOW_PRODUCTS",
    "SHOW_COMPARISON",
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
    "CLEAR_HISTORY",
    "UPDATE_PREFERENCES",
}
