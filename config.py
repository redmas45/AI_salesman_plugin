"""Central configuration loaded from the project .env file."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

OPENAI_API_KEY: str = (os.getenv("OPENAI_API_KEY", "") or os.getenv("\ufeffOPENAI_API_KEY", "")).strip()
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip()

def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


STT_MODEL: str = os.getenv("STT_MODEL", "gpt-4o-mini-transcribe")
GROQ_STT_MODEL: str = os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo")
STT_PROVIDER: str = os.getenv("STT_PROVIDER", "groq" if GROQ_API_KEY else "openai").strip().lower()
STT_LANGUAGE: str = os.getenv("STT_LANGUAGE", "").strip()
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_EXTRACTOR_ENABLED: bool = _env_bool("LLM_EXTRACTOR_ENABLED", False)
FAST_VOICE_MODE: bool = _env_bool("FAST_VOICE_MODE", True)
_RAW_TTS_MODEL: str = os.getenv("TTS_MODEL", "tts-1")
TTS_MODEL: str = os.getenv("FAST_TTS_MODEL", "tts-1") if FAST_VOICE_MODE else _RAW_TTS_MODEL
TTS_VOICE: str = os.getenv("TTS_VOICE", "alloy")
GROQ_TTS_MODEL: str = os.getenv("GROQ_TTS_MODEL", "canopylabs/orpheus-v1-english")
GROQ_TTS_VOICE: str = os.getenv("GROQ_TTS_VOICE", "troy")
GROQ_TTS_RESPONSE_FORMAT: str = os.getenv("GROQ_TTS_RESPONSE_FORMAT", "wav")
TTS_PROVIDER: str = os.getenv("TTS_PROVIDER", "groq" if GROQ_API_KEY else "openai").strip().lower()
GROQ_FALLBACK_TO_OPENAI: bool = _env_bool("GROQ_FALLBACK_TO_OPENAI", True)

EMBEDDING_MODEL: str = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "10"))
RAG_TOP_N: int = int(os.getenv("RAG_TOP_N", "3"))

LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.20"))
LLM_MAX_TOKENS_HARD_CAP: int = int(os.getenv("LLM_MAX_TOKENS_HARD_CAP", "320"))
LLM_MAX_TOKENS: int = min(
    int(os.getenv("LLM_MAX_TOKENS", "320")),
    LLM_MAX_TOKENS_HARD_CAP,
)

HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8001"))
PUBLIC_API_URL: str = os.getenv("PUBLIC_API_URL", f"http://127.0.0.1:{PORT}").strip()
CORS_ORIGINS: list[str] = [item.strip() for item in os.getenv("CORS_ORIGINS", "*").split(",")]
HUB_PUBLIC_URL: str = os.getenv("HUB_PUBLIC_URL", PUBLIC_API_URL).strip()
PUBLIC_STOREFRONT_ORIGIN: str = os.getenv("PUBLIC_STOREFRONT_ORIGIN", "").strip()
CLIENT_STORE_URL: str = os.getenv("CLIENT_STORE_URL", "").strip()
DEPLOYMENT_MODE: str = os.getenv("DEPLOYMENT_MODE", "local").strip().lower()

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
    "postgresql://shopbot:shopbot_password@localhost:5434/shopping_db",
)
BASE_DIR = Path(__file__).parent

CRAWL_MAX_PAGES: int = int(os.getenv("CRAWL_MAX_PAGES", "60"))
CRAWL_MAX_DEPTH: int = int(os.getenv("CRAWL_MAX_DEPTH", "3"))
CRAWL_ON_STARTUP: bool = os.getenv("CRAWL_ON_STARTUP", "true").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}
CRAWL_PERIODIC_ENABLED: bool = _env_bool("CRAWL_PERIODIC_ENABLED", True)

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
    "SHOW_ENTITIES",
    "COMPARE_ENTITIES",
    "FILTER_ENTITIES",
    "SORT_ENTITIES",
    "OPEN_ENTITY_DETAIL",
    "OPEN_POLICY",
    "OPEN_MAP",
    "OPEN_CONTACT",
    "START_QUOTE",
    "START_BOOKING",
    "START_APPLICATION",
    "REQUEST_APPOINTMENT",
    "REQUEST_TEST_DRIVE",
    "REQUEST_VIEWING",
    "CONTACT_AGENT",
    "START_INTAKE",
    "REQUEST_CONSULTATION",
    "START_TICKET_PURCHASE",
    "START_ENROLLMENT",
    "CAPTURE_LEAD",
    "CAPTURE_PATIENT_LEAD",
    "REQUEST_CALLBACK",
    "HANDOFF_TO_HUMAN",
    "HANDOFF_TO_AGENT",
    "HANDOFF_TO_LICENSED_AGENT",
    "HANDOFF_TO_ADVISOR",
    "HANDOFF_TO_CLINIC",
    "HANDOFF_TO_LAWYER",
    "HANDOFF_TO_RECRUITER",
    "RUN_CALCULATOR",
    "RUN_AFFORDABILITY_CALCULATOR",
    "BUILD_ITINERARY",
    "BUILD_LEARNING_PATH",
    "CHECK_AVAILABILITY",
    "SEARCH_AVAILABILITY",
    "CHECK_ELIGIBILITY_SOFT",
    "CHECK_APPOINTMENT_AVAILABILITY",
    "CHECK_PREREQUISITES",
    "SET_LOCATION",
    "SCHEDULE_ORDER",
    "CHECKOUT_HANDOFF",
    "CHECK_DELIVERY_AVAILABILITY",
    "JOIN_WAITLIST",
    "MATCH_JOBS",
    "SAVE_SEARCH",
    "OPEN_CLAIM_FLOW",
    "OPEN_RENEWAL_FLOW",
    "OPEN_DISCLOSURE",
    "OPEN_SYLLABUS",
    "OPEN_LOCATION",
    "OPEN_TELECONSULT",
    "SHOW_EMERGENCY_NOTICE",
    "BOOK_APPOINTMENT_REQUEST",
    "REQUEST_COUNSELOR_CALLBACK",
}
