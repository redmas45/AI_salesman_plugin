"""Central configuration loaded from the project .env file."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
AZURE_OPENAI_BASE_URL: str = os.getenv("AZURE_OPENAI_BASE_URL", "").strip()
AZURE_OPENAI_CHAT_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-5.4-mini").strip()
AZURE_OPENAI_STT_DEPLOYMENT: str = os.getenv(
    "AZURE_OPENAI_STT_DEPLOYMENT",
    "gpt-4o-mini-transcribe",
).strip()
AZURE_OPENAI_TTS_DEPLOYMENT: str = os.getenv(
    "AZURE_OPENAI_TTS_DEPLOYMENT",
    "gpt-4o-mini-tts",
).strip()
AZURE_OPENAI_REASONING_EFFORT: str = os.getenv("AZURE_OPENAI_REASONING_EFFORT", "none").strip().lower()
AZURE_OPENAI_TTS_VOICE: str = os.getenv("AZURE_OPENAI_TTS_VOICE", "coral").strip()
AZURE_OPENAI_TIMEOUT_SECONDS: float = float(os.getenv("AZURE_OPENAI_TIMEOUT_SECONDS", "30") or 30)

def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


STT_LANGUAGE: str = os.getenv("STT_LANGUAGE", "").strip()
LLM_EXTRACTOR_ENABLED: bool = _env_bool("LLM_EXTRACTOR_ENABLED", False)
TTS_CHUNK_CHARS: int = int(os.getenv("TTS_CHUNK_CHARS", "1200") or 1200)
TTS_MAX_INPUT_CHARS: int = int(os.getenv("TTS_MAX_INPUT_CHARS", "12000") or 12000)

EMBEDDING_MODEL: str = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "10"))
RAG_TOP_N: int = int(os.getenv("RAG_TOP_N", "50"))
ACTION_AUTO_APPROVE_CONFIDENCE: float = float(os.getenv("ACTION_AUTO_APPROVE_CONFIDENCE", "0.75") or 0.75)

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
CLIENT_TLS_VERIFY: bool = _env_bool("CLIENT_TLS_VERIFY", True)
LOG_CONVERSATION_CONTENT: bool = _env_bool("LOG_CONVERSATION_CONTENT", False)
TRUSTED_PROXY_IPS: set[str] = {
    item.strip() for item in os.getenv("TRUSTED_PROXY_IPS", "").split(",") if item.strip()
}

DEFAULT_SITE_ID: str = os.getenv(
    "AI_DEFAULT_SITE_ID",
    os.getenv("DEFAULT_SITE_ID", "site_1"),
).strip().strip("\"'")
CURRENT_SITE_ID: str = os.getenv("CURRENT_SITE_ID", DEFAULT_SITE_ID).strip().strip("\"'")
CURRENT_URL: str = os.getenv("CURRENT_URL", "").strip()
MANUAL_WIDGET_SCRIPT: str = os.getenv("MANUAL_WIDGET_SCRIPT", "").strip()
PUBLIC_WIDGET_SCRIPT_URL: str = os.getenv("PUBLIC_WIDGET_SCRIPT_URL", "").strip()
VOICE_ORB_API_URL: str = os.getenv("VOICE_ORB_API_URL", "").strip()
CLIENT_PANEL_TOKEN_SECRET: str = os.getenv("CLIENT_PANEL_TOKEN_SECRET", "").strip()

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://shopbot:shopbot_password@localhost:5434/shopping_db",
)
BASE_DIR = Path(__file__).parent

CRAWL_MAX_PAGES: int = int(os.getenv("CRAWL_MAX_PAGES", "60"))
CRAWL_MAX_DEPTH: int = int(os.getenv("CRAWL_MAX_DEPTH", "3"))
SETUP_RUN_TIMEOUT_SECONDS: int = int(os.getenv("SETUP_RUN_TIMEOUT_SECONDS", "7200"))
CRAWL_ON_STARTUP: bool = os.getenv("CRAWL_ON_STARTUP", "false").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}
CRAWL_PERIODIC_ENABLED: bool = _env_bool("CRAWL_PERIODIC_ENABLED", False)
ENSURE_DEFAULT_CLIENT_ON_STARTUP: bool = _env_bool("ENSURE_DEFAULT_CLIENT_ON_STARTUP", False)
CLEAN_SYNTHETIC_DEMO_CLIENTS_ON_STARTUP: bool = _env_bool("CLEAN_SYNTHETIC_DEMO_CLIENTS_ON_STARTUP", True)

MAX_TRANSCRIPT_CHARS: int = 2000
MAX_RESPONSE_CHARS: int = 3000
MAX_UI_ACTIONS: int = 5
MAX_AUDIO_UPLOAD_BYTES: int = int(os.getenv("MAX_AUDIO_UPLOAD_BYTES", str(10 * 1024 * 1024)))

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
    "RUN_DOM_SEQUENCE",
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
