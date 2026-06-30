"""
Orchestrator — wires all pipeline stages together.

Pipeline:
  audio bytes
    → STT (Whisper via OpenAI)
    → Input Guardrails
    → RAG Retrieval (PostgreSQL + pgvector)
    → LLM Agent (OpenAI Chat Completions)
    → Output Guardrails
    → TTS (OpenAI tts-1)
    → structured response dict
"""

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Generator, Optional

import psycopg

from agent import guardrails, llm, rag, stt, tts
from agent.guardrails import InputGuardrailError, OutputGuardrailError
from agent.prompt import format_cart_for_prompt
from api.models import (
    ACTION_ADD_TO_CART,
    ACTION_COMPARE_ENTITIES,
    ACTION_NAVIGATE_TO,
    ACTION_SHOW_COMPARISON,
    ACTION_SHOW_ENTITIES,
    ACTION_SHOW_PRODUCTS,
    ACTION_SORT_ENTITIES,
    ACTION_SORT_PRODUCTS,
    ACTION_UPDATE_PREFERENCES,
    ENTITY_IDS_PARAM,
    PRODUCT_ID_PARAM,
    PRODUCT_IDS_PARAM,
    QUANTITY_PARAM,
)
from db.database import (
    get_all_products,
    get_cart_items,
    get_user_profile,
    tenant_inventory_summary,
    update_user_preferences,
    get_db,
)
from db.clients import get_client_detail, get_client_vertical_key

logger = logging.getLogger(__name__)

DEFAULT_AUDIO_FILENAME = "audio.wav"
GENERIC_BLOCKED_RESPONSE = "I'm sorry, I can't respond to that safely. Tell me what you need and I will help from this website's information."
ECOMMERCE_BLOCKED_RESPONSE = "I had trouble with that shopping request. Tell me what you need and I will help you find it."
NON_ECOMMERCE_CART_CONTEXT = "No ecommerce cart context applies to this client."
CAPABILITY_FILTER_SKIPPED = "skipped"
PIPELINE_RECOVERABLE_ERRORS = (
    KeyError,
    LookupError,
    RuntimeError,
    TypeError,
    ValueError,
    psycopg.Error,
)
LEAD_FLOW_INTENT_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("REQUEST_TEST_DRIVE", (r"\btest drive\b",)),
    ("REQUEST_SITE_VISIT", (r"\bsite visit\b", r"\bvisit\b.{0,30}\bsite\b")),
    ("REQUEST_VIEWING", (r"\bviewing\b", r"\bproperty tour\b", r"\bhome tour\b", r"\bsee\b.{0,30}\b(property|home|flat|apartment)\b")),
    ("BOOK_APPOINTMENT_REQUEST", (r"\bbook\b.{0,25}\bappointment\b", r"\bappointment\b.{0,25}\bbook\b")),
    ("REQUEST_APPOINTMENT", (r"\bappointment\b", r"\bbook\b.{0,25}\b(doctor|clinic|consult)\b")),
    ("REQUEST_COUNSELOR_CALLBACK", (r"\bcounsell?or\b", r"\badvisor\b.{0,30}\b(call|callback|contact)\b")),
    ("REQUEST_CONSULTATION", (r"\bconsultation\b", r"\bconsult\b.{0,30}\b(expert|lawyer|advisor|doctor|specialist)\b")),
    ("START_TICKET_PURCHASE", (r"\bticket(s)?\b", r"\bbuy\b.{0,30}\bpass(es)?\b")),
    ("START_ENROLLMENT", (r"\benroll\b", r"\benrolment\b", r"\benrollment\b", r"\badmission\b", r"\bregister\b.{0,30}\b(course|program|class)\b")),
    ("START_APPLICATION", (r"\bapply\b", r"\bapplication\b", r"\bstart\b.{0,30}\bapplication\b")),
    ("START_QUOTE", (r"\bquote(s)?\b", r"\bget\b.{0,30}\brate(s)?\b", r"\bpremium\b", r"\bshow\b.{0,30}\bquote(s)?\b")),
    ("REQUEST_ESTIMATE", (r"\bestimate\b", r"\bquote\b", r"\bproject cost\b", r"\brenovation cost\b")),
    ("START_BOOKING", (r"\bbook\b", r"\bbooking\b", r"\breserve\b", r"\breservation\b")),
    ("REQUEST_CALLBACK", (r"\bcall me\b", r"\bcallback\b", r"\bcall back\b", r"\bphone call\b")),
    ("CONTACT_AGENT", (r"\bagent\b", r"\brealtor\b", r"\bsales person\b", r"\bsalesperson\b")),
    ("CAPTURE_LEAD", (r"\bcontact me\b", r"\bsend my details\b", r"\bleave my details\b")),
)


@dataclass(frozen=True)
class RetrievalContext:
    profile: dict[str, Any]
    price_constraints: dict[str, Any]
    products: list[dict[str, Any]]


def print(*args, **kwargs):
    """Safely print to stdout, handling encoding issues on Windows."""
    import sys
    import builtins
    try:
        builtins.print(*args, **kwargs)
    except UnicodeEncodeError:
        sep = kwargs.get('sep', ' ')
        end = kwargs.get('end', '\n')
        file = kwargs.get('file', sys.stdout)
        
        text = sep.join(str(arg) for arg in args)
        encoding = getattr(file, 'encoding', 'utf-8') or 'utf-8'
        safe_text = text.encode(encoding, errors='replace').decode(encoding)
        
        file.write(safe_text + end)
        file.flush()


def _ai_log(label: str, value: Any) -> None:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    text = " ".join(str(text).split())
    line = f"AI_CONVO | {label}: {text[:2000]}"
    logger.info(line)
    print(line, flush=True)


def run(
    site_id: str,
    audio_bytes: Optional[bytes] = None,
    text_input: Optional[str] = None,
    audio_filename: str = DEFAULT_AUDIO_FILENAME,
    skip_tts: bool = False,
    conversation_history: Optional[list] = None,
    page_context: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Run the full voice shopping pipeline.

    Args:
        audio_bytes:            Raw audio bytes (mutually exclusive with text_input).
        text_input:             Plain text transcript (for testing without audio).
        audio_filename:         Filename hint for MIME type detection.
        skip_tts:               If True, skip TTS synthesis (returns empty audio_b64).
        conversation_history:   List of prior turns for multi-turn conversation context.

    Returns:
        Dict with keys:
            transcript    (str)  — what the customer said
            response_text (str)  — what the assistant says back
            intent        (str)  — detected intent
            confidence    (float)
            ui_actions    (list) — website control commands
            audio_b64     (str)  — base64-encoded WAV (empty if skip_tts=True)
            latency_ms    (dict) — per-stage timing for observability
    """
    timings: dict[str, float] = {}
    t0 = time.perf_counter()

    transcript, transcript_error = _resolve_transcript(
        audio_bytes=audio_bytes,
        text_input=text_input,
        audio_filename=audio_filename,
        timings=timings,
    )
    if transcript_error:
        return _error_response(transcript_error, timings)

    logger.info("PIPELINE | transcript: %r", transcript[:120])
    _ai_log("user", transcript)
    print(f"\n{'=' * 60}")
    print(f'🎤 STT HEARD: "{transcript}"')
    print(f"{'=' * 60}")

    # Stage 2: Input Guardrails
    t = time.perf_counter()
    try:
        safe_transcript = guardrails.validate_input(transcript)
    except InputGuardrailError as exc:
        return _guardrail_response(str(exc), transcript, skip_tts, timings)
    timings["guardrail_input_ms"] = _ms(t)

    if _is_simple_greeting(safe_transcript):
        return _greeting_response(transcript, skip_tts, timings, t0)

    ecommerce_runtime = _is_ecommerce_site(site_id)
    sort_response = _sort_intent_response(
        site_id,
        transcript,
        safe_transcript,
        ecommerce_runtime,
        skip_tts,
        timings,
        t0,
    )
    if sort_response:
        return sort_response

    navigation_response = _navigation_intent_response(site_id, transcript, safe_transcript, skip_tts, timings, t0)
    if navigation_response:
        return navigation_response

    if ecommerce_runtime and _is_inventory_stats_query(safe_transcript):
        return _inventory_stats_response(site_id, transcript, skip_tts, timings, t0)

    inventory_type = _extract_inventory_type_query(safe_transcript) if ecommerce_runtime else None
    if inventory_type:
        return _inventory_type_count_response(
            site_id, transcript, inventory_type, skip_tts, timings, t0
        )

    # Stage 3: RAG Retrieval
    t = time.perf_counter()
    retrieval_context = _retrieve_context(site_id, safe_transcript, conversation_history)
    profile = retrieval_context.profile
    price_constraints = retrieval_context.price_constraints
    retrieved_products = retrieval_context.products
    timings["rag_ms"] = _ms(t)

    logger.info(
        "PIPELINE | RAG returned %d products (price_filter=%s)",
        len(retrieved_products),
        price_constraints or "none",
    )
    print(f"🔍 RAG FOUND: {len(retrieved_products)} products")
    if price_constraints:
        print(f"   💰 Price filter active: {price_constraints}")
    for i, p in enumerate(retrieved_products[:5]):
        print(
            f"   [{i + 1}] id={p.get('id')} | {p.get('name', '?')[:50]} | ₹{p.get('price', '?')}"
        )

    # Stage 4: LLM Agent
    t = time.perf_counter()
    cart_context = _cart_context_for_site(site_id, ecommerce_runtime)
    profile_context = _profile_context(profile)

    llm_response = llm.generate_response(
        site_id,
        safe_transcript,
        retrieved_products,
        conversation_history=conversation_history or [],
        price_constraints=price_constraints,
        cart_context=cart_context,
        profile_context=profile_context,
        page_context=page_context,
    )

    llm_response = _normalize_llm_response(llm_response, retrieved_products)
    _persist_preference_actions(site_id, llm_response.get("ui_actions", []))

    timings["llm_ms"] = _ms(t)

    # Stage 5: Output Guardrails
    t = time.perf_counter()
    validated = _validate_agent_response(
        llm_response,
        site_id=site_id,
        safe_transcript=safe_transcript,
        retrieved_products=retrieved_products,
        blocked_text=_blocked_text_for_site(ecommerce_runtime),
    )
    timings["guardrail_output_ms"] = _ms(t)

    final_actions = _add_variant_ids_to_cart_actions(site_id, validated.get("ui_actions", []))
    filter_report = _apply_capability_filter_result(site_id, final_actions)
    final_actions = filter_report["actions"]
    validated["response_text"] = _align_response_with_action_filter(validated["response_text"], filter_report)
    validated["ui_actions"] = final_actions
    retrieval_evidence = _retrieval_evidence(
        site_id,
        ecommerce_runtime,
        retrieved_products,
        price_constraints,
    )

    print(f'🧠 LLM RESPONSE: "{validated["response_text"][:150]}"')
    print(
        f"   Intent: {validated.get('intent', '?')} | Confidence: {validated.get('confidence', '?')}"
    )
    print(f"   UI Actions: {validated.get('ui_actions', [])}")

    audio_b64, tts_ms = _synthesize_audio_b64(validated["response_text"], skip_tts)
    if tts_ms is not None:
        timings["tts_ms"] = tts_ms

    timings["total_ms"] = _ms(t0)
    logger.info("PIPELINE | Done in %.0fms", timings["total_ms"])
    print(
        f"🔊 TTS: {'Generated audio' if audio_b64 else 'No audio (failed or skipped)'}"
    )
    print(f"⏱️  Total: {timings['total_ms']:.0f}ms")
    print(f"{'=' * 60}\n")

    _ai_log("assistant", validated["response_text"])
    _ai_log("actions", final_actions)

    return {
        "transcript": transcript,
        "response_text": validated["response_text"],
        "intent": validated.get("intent", "unknown"),
        "confidence": validated.get("confidence", 0.0),
        "ui_actions": final_actions,
        "audio_b64": audio_b64,
        "latency_ms": timings,
        "retrieval": retrieval_evidence,
    }


def run_stream(
    site_id: str,
    audio_bytes: Optional[bytes] = None,
    text_input: Optional[str] = None,
    audio_filename: str = DEFAULT_AUDIO_FILENAME,
    skip_tts: bool = False,
    conversation_history: Optional[list] = None,
    page_context: Optional[dict[str, Any]] = None,
) -> Generator[str, None, None]:
    """
    Generator that yields JSON strings for Server-Sent Events.
    Events:
      - transcript: { "transcript": str }
      - response: { "response_text": str }
      - actions: { "ui_actions": list }
      - audio: { "audio_b64": str, "response_text": str }
      - metrics: { "latency_ms": dict }
      - error: { "error": str }
    """
    timings: dict[str, float] = {}
    t0 = time.perf_counter()

    transcript, transcript_error = _resolve_transcript(
        audio_bytes=audio_bytes,
        text_input=text_input,
        audio_filename=audio_filename,
        timings=timings,
    )
    if transcript_error:
        yield {"event": "error", "data": {"error": transcript_error}}
        return

    _ai_log("user", transcript)
    yield {"event": "transcript", "data": {"transcript": transcript}}

    # Stage 2: Input Guardrails
    t = time.perf_counter()
    try:
        safe_transcript = guardrails.validate_input(transcript)
    except InputGuardrailError as exc:
        msg = str(exc)
        yield {"event": "actions", "data": {"ui_actions": []}}
        yield {"event": "response", "data": {"response_text": msg}}

        audio_b64, tts_ms = _synthesize_audio_b64(msg, skip_tts)
        if tts_ms is not None:
            timings["tts_ms"] = tts_ms
        timings["total_ms"] = _ms(t0)
        yield {"event": "audio", "data": {"response_text": msg, "audio_b64": audio_b64}}
        yield {"event": "metrics", "data": {"latency_ms": timings}}
        return
    timings["guardrail_input_ms"] = _ms(t)

    if _is_simple_greeting(safe_transcript):
        result = _greeting_response(transcript, skip_tts, timings, t0)
        yield from _stream_final_result(result)
        return

    ecommerce_runtime = _is_ecommerce_site(site_id)
    sort_response = _sort_intent_response(
        site_id,
        transcript,
        safe_transcript,
        ecommerce_runtime,
        skip_tts,
        timings,
        t0,
    )
    if sort_response:
        yield from _stream_final_result(sort_response)
        return

    navigation_response = _navigation_intent_response(site_id, transcript, safe_transcript, skip_tts, timings, t0)
    if navigation_response:
        yield from _stream_final_result(navigation_response)
        return

    if ecommerce_runtime and _is_inventory_stats_query(safe_transcript):
        result = _inventory_stats_response(site_id, transcript, skip_tts, timings, t0)
        yield from _stream_final_result(result)
        return

    inventory_type = _extract_inventory_type_query(safe_transcript) if ecommerce_runtime else None
    if inventory_type:
        result = _inventory_type_count_response(
            site_id, transcript, inventory_type, skip_tts, timings, t0
        )
        yield from _stream_final_result(result)
        return

    # Stage 3: RAG
    t = time.perf_counter()
    retrieval_context = _retrieve_context(site_id, safe_transcript, conversation_history)
    profile = retrieval_context.profile
    price_constraints = retrieval_context.price_constraints
    retrieved_products = retrieval_context.products
    timings["rag_ms"] = _ms(t)

    # Stage 4: LLM
    t = time.perf_counter()
    profile_context = _profile_context(profile)
    cart_context = _cart_context_for_site(site_id, ecommerce_runtime)
    llm_response = llm.generate_response(
        site_id,
        safe_transcript,
        retrieved_products,
        conversation_history=conversation_history or [],
        price_constraints=price_constraints,
        cart_context=cart_context,
        profile_context=profile_context,
        page_context=page_context,
    )
    llm_response = _normalize_llm_response(llm_response, retrieved_products)
    _persist_preference_actions(site_id, llm_response.get("ui_actions", []))
    timings["llm_ms"] = _ms(t)

    # Stage 5: Output Guardrails
    t = time.perf_counter()
    validated = _validate_agent_response(
        llm_response,
        site_id=site_id,
        safe_transcript=safe_transcript,
        retrieved_products=retrieved_products,
        blocked_text=_blocked_text_for_site(ecommerce_runtime),
    )
    timings["guardrail_output_ms"] = _ms(t)

    final_actions = _add_variant_ids_to_cart_actions(site_id, validated.get("ui_actions", []))
    filter_report = _apply_capability_filter_result(site_id, final_actions)
    final_actions = filter_report["actions"]
    validated["response_text"] = _align_response_with_action_filter(validated["response_text"], filter_report)
    validated["ui_actions"] = final_actions
    retrieval_evidence = _retrieval_evidence(
        site_id,
        ecommerce_runtime,
        retrieved_products,
        price_constraints,
    )
    _ai_log("assistant", validated["response_text"])
    _ai_log("actions", final_actions)

    # Yield actions so UI can update immediately
    yield {"event": "actions", "data": {"ui_actions": final_actions}}
    yield {"event": "response", "data": {"response_text": validated["response_text"]}}

    audio_b64, tts_ms = _synthesize_audio_b64(validated["response_text"], skip_tts)
    if tts_ms is not None:
        timings["tts_ms"] = tts_ms
    timings["total_ms"] = _ms(t0)

    # Yield audio
    yield {
        "event": "audio",
        "data": {
            "response_text": validated["response_text"],
            "audio_b64": audio_b64,
            "latency_ms": timings,
            "retrieval": retrieval_evidence,
        },
    }
    yield {"event": "metrics", "data": {"latency_ms": timings, "retrieval": retrieval_evidence}}


# Helpers


def _stream_final_result(result: dict[str, Any]) -> Generator[dict[str, Any], None, None]:
    ui_actions = result.get("ui_actions", [])
    response_text = result.get("response_text", "")
    latency_ms = result.get("latency_ms", {})
    retrieval_evidence = result.get("retrieval") if isinstance(result.get("retrieval"), dict) else {}
    yield {"event": "actions", "data": {"ui_actions": ui_actions}}
    yield {"event": "response", "data": {"response_text": response_text}}
    yield {
        "event": "audio",
        "data": {
            "response_text": response_text,
            "audio_b64": result.get("audio_b64", ""),
            "latency_ms": latency_ms,
            "retrieval": retrieval_evidence,
        },
    }
    yield {"event": "metrics", "data": {"latency_ms": latency_ms, "retrieval": retrieval_evidence}}


def _ms(since: float) -> float:
    return round((time.perf_counter() - since) * 1000, 1)


def _retrieval_evidence(
    site_id: str,
    ecommerce_runtime: bool,
    retrieved_items: list[dict[str, Any]],
    price_constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return compact retrieval diagnostics for CRM prompt smoke tests and runtime debugging."""
    evidence: dict[str, Any] = {
        "source": "products" if ecommerce_runtime else "knowledge_items",
        "retrieved_count": len(retrieved_items),
        "retrieved_ids": [
            str(item.get("id"))
            for item in retrieved_items[:8]
            if item.get("id") is not None
        ],
        "retrieved_titles": [
            title
            for title in (_retrieval_item_title(item) for item in retrieved_items[:5])
            if title
        ],
    }
    if price_constraints:
        evidence["price_constraints"] = dict(price_constraints)

    try:
        if ecommerce_runtime:
            stats = tenant_inventory_summary(site_id)
            evidence.update(
                {
                    "total_records": _safe_int(stats.get("total_products")),
                    "active_records": _safe_int(stats.get("active_products")),
                    "in_stock_records": _safe_int(stats.get("in_stock_products")),
                    "missing_embeddings": _safe_int(stats.get("missing_embeddings")),
                    "groups": _safe_int(stats.get("total_categories")),
                }
            )
        else:
            from db.knowledge import knowledge_stats

            stats = knowledge_stats(site_id)
            evidence.update(
                {
                    "total_records": _safe_int(stats.get("total_items")),
                    "active_records": _safe_int(stats.get("active_items")),
                    "missing_embeddings": _safe_int(stats.get("missing_embeddings")),
                    "groups": _safe_int(stats.get("entity_types")),
                }
            )
    except PIPELINE_RECOVERABLE_ERRORS as exc:
        evidence["stats_error"] = str(exc)

    evidence["issue"] = _retrieval_issue(evidence)
    return evidence


def _retrieval_item_title(item: dict[str, Any]) -> str:
    return str(item.get("name") or item.get("title") or item.get("summary") or "").strip()[:120]


def _retrieval_issue(evidence: dict[str, Any]) -> str:
    active = _safe_int(evidence.get("active_records"))
    retrieved = _safe_int(evidence.get("retrieved_count"))
    missing = _safe_int(evidence.get("missing_embeddings"))
    if active <= 0:
        return "no_active_records"
    if retrieved <= 0:
        return "retrieval_returned_zero"
    if missing >= active:
        return "all_vectors_missing"
    if missing > 0:
        return "some_vectors_missing"
    return "ok"


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _resolve_transcript(
    *,
    audio_bytes: bytes | None,
    text_input: str | None,
    audio_filename: str,
    timings: dict[str, float],
) -> tuple[str | None, str | None]:
    if text_input:
        timings["stt_ms"] = 0
        return text_input, None
    if not audio_bytes:
        return None, "No audio or text input provided."

    started_at = time.perf_counter()
    try:
        transcript = stt.transcribe(audio_bytes, audio_filename)
    except RuntimeError as exc:
        return None, str(exc)
    timings["stt_ms"] = _ms(started_at)
    return transcript, None


def _safe_user_profile(site_id: str) -> dict[str, Any]:
    try:
        return get_user_profile(site_id)
    except PIPELINE_RECOVERABLE_ERRORS as exc:
        logger.warning("PIPELINE | user profile unavailable for %s: %s", site_id, exc)
        return {}


def _profile_context(profile: dict[str, Any]) -> str:
    return (
        f"Address: {profile.get('address') or 'None'} | "
        f"Payment Method: {profile.get('payment_method') or 'None'} | "
        f"Preferences: {profile.get('preferences') or 'None'}"
    )


def _retrieve_context(
    site_id: str,
    safe_transcript: str,
    conversation_history: list | None,
) -> RetrievalContext:
    profile = _safe_user_profile(site_id)
    rag_query = safe_transcript
    if profile.get("preferences"):
        rag_query = f"{safe_transcript} (User preferences: {profile['preferences']})"

    if not _is_ecommerce_site(site_id):
        return _retrieve_generic_context(site_id, rag_query, profile)

    try:
        price_constraints = rag.extract_price_constraints(rag_query)
        retrieved_products = rag.retrieve(
            rag_query,
            site_id=site_id,
            price_constraints=price_constraints,
        )
        products = _merge_products(
            _merge_history_products(retrieved_products, conversation_history or [], site_id),
            _exact_products_from_query(safe_transcript, site_id),
        )
        return RetrievalContext(profile, price_constraints, products)
    except PIPELINE_RECOVERABLE_ERRORS as exc:
        logger.error("PIPELINE | RAG failed: %s", exc)
        return RetrievalContext(profile, {}, [])


def _retrieve_generic_context(
    site_id: str,
    rag_query: str,
    profile: dict[str, Any],
) -> RetrievalContext:
    try:
        from agent.retrieval.generic_rag import retrieve_knowledge

        items = retrieve_knowledge(rag_query, site_id=site_id)
        return RetrievalContext(profile, {}, items)
    except PIPELINE_RECOVERABLE_ERRORS as exc:
        logger.error("PIPELINE | Generic RAG failed: %s", exc)
        return RetrievalContext(profile, {}, [])


def _is_ecommerce_site(site_id: str) -> bool:
    try:
        return get_client_vertical_key(site_id) == "ecommerce"
    except PIPELINE_RECOVERABLE_ERRORS as exc:
        logger.warning("PIPELINE | vertical lookup failed for %s: %s", site_id, exc)
        return False


def _cart_context_for_site(site_id: str, ecommerce_runtime: bool) -> str:
    if not ecommerce_runtime:
        return NON_ECOMMERCE_CART_CONTEXT
    try:
        return format_cart_for_prompt(get_cart_items(site_id))
    except PIPELINE_RECOVERABLE_ERRORS as exc:
        logger.warning("PIPELINE | cart context unavailable for %s: %s", site_id, exc)
        return "The cart is unavailable."


def _blocked_text_for_site(ecommerce_runtime: bool) -> str:
    return ECOMMERCE_BLOCKED_RESPONSE if ecommerce_runtime else GENERIC_BLOCKED_RESPONSE


def _merge_history_products(
    retrieved_products: list[dict[str, Any]],
    conversation_history: list,
    site_id: str,
) -> list[dict[str, Any]]:
    history_products = _extract_products_from_history(conversation_history, site_id)
    return _merge_products(history_products, retrieved_products)


def _fallback_search_response(retrieved_products: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "response_text": f"I had trouble processing that, but I found {len(retrieved_products)} products matching your search.",
        "intent": "search_fallback",
        "confidence": 1.0,
        "ui_actions": [
            {
                "action": ACTION_SHOW_PRODUCTS,
                "params": {
                    PRODUCT_IDS_PARAM: [str(product["id"]) for product in retrieved_products]
                },
            }
        ],
    }


def _normalize_llm_response(
    llm_response: dict[str, Any],
    retrieved_products: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized = dict(llm_response)
    normalized["ui_actions"] = _fill_missing_entity_list_ids(
        normalized.get("ui_actions"),
        retrieved_products,
    )
    if not retrieved_products and normalized.get("intent") == "product_search":
        normalized["ui_actions"] = []
        normalized["intent"] = "out_of_stock"
    if normalized.get("intent") == "out_of_stock":
        normalized["ui_actions"] = []
    if normalized.get("intent") == "error" and retrieved_products:
        logger.info("PIPELINE | LLM failed, falling back to local FAISS search results.")
        return _fallback_search_response(retrieved_products)
    return normalized


def _fill_missing_entity_list_ids(
    actions: Any,
    retrieved_products: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not isinstance(actions, list):
        return []

    entity_ids = [str(item.get("id")) for item in retrieved_products if item.get("id") is not None]
    if not entity_ids:
        clean_actions: list[dict[str, Any]] = []
        for action in actions:
            if not isinstance(action, dict):
                continue
            action_name = str(action.get("action") or "").upper()
            params = action.get("params") if isinstance(action.get("params"), dict) else {}
            if action_name in {ACTION_SHOW_ENTITIES, ACTION_COMPARE_ENTITIES} and not isinstance(
                params.get(ENTITY_IDS_PARAM),
                list,
            ):
                continue
            clean_actions.append(action)
        return clean_actions

    filled_actions: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        next_action = dict(action)
        action_name = str(next_action.get("action") or "").upper()
        params = next_action.get("params")
        next_params = dict(params) if isinstance(params, dict) else {}
        if action_name in {ACTION_SHOW_ENTITIES, ACTION_COMPARE_ENTITIES} and not isinstance(
            next_params.get(ENTITY_IDS_PARAM),
            list,
        ):
            next_params[ENTITY_IDS_PARAM] = entity_ids
            next_action["params"] = next_params
        filled_actions.append(next_action)
    return filled_actions


def _persist_preference_actions(site_id: str, actions: list[dict[str, Any]]) -> None:
    for action in actions:
        if action.get("action") != ACTION_UPDATE_PREFERENCES:
            continue
        preferences = action.get("params", {}).get("preferences")
        if not preferences:
            continue
        try:
            update_user_preferences(site_id, preferences)
        except PIPELINE_RECOVERABLE_ERRORS as exc:
            logger.warning("PIPELINE | failed to update preferences: %s", exc)


def _validate_agent_response(
    response: dict[str, Any],
    *,
    site_id: str,
    safe_transcript: str,
    retrieved_products: list[dict[str, Any]],
    blocked_text: str,
) -> dict[str, Any]:
    try:
        original_actions = [
            action.get("action")
            for action in response.get("ui_actions", [])
            if isinstance(action, dict)
        ]
        validated = guardrails.validate_output(
            response,
            site_id,
            [product["id"] for product in retrieved_products],
        )
        if _is_ecommerce_site(site_id):
            _override_hallucinated_product_search(validated, original_actions)
    except OutputGuardrailError as exc:
        logger.error("PIPELINE | Output guardrail blocked response: %s", exc)
        validated = _blocked_response(blocked_text)

    if _is_ecommerce_site(site_id):
        _promote_comparison_action(validated, safe_transcript)
        _ensure_named_comparison_response(validated, safe_transcript, retrieved_products)
        _ensure_product_answer_response(validated, safe_transcript, retrieved_products)
        _ensure_cart_request_response(validated, safe_transcript, retrieved_products)
        _prevent_false_empty_inventory_claim(validated, safe_transcript, site_id)
    else:
        _ensure_generic_comparison_response(validated, safe_transcript, retrieved_products)
        _ensure_entity_answer_response(validated, safe_transcript, retrieved_products)
        _ensure_lead_flow_response(validated, safe_transcript, site_id)
    return validated


def _override_hallucinated_product_search(
    validated: dict[str, Any],
    original_actions: list[str],
) -> None:
    validated_actions = [action.get("action") for action in validated.get("ui_actions", [])]
    if ACTION_SHOW_PRODUCTS not in original_actions or ACTION_SHOW_PRODUCTS in validated_actions:
        return
    logger.warning(
        "PIPELINE | Detected LLM hallucination: SHOW_PRODUCTS was completely blocked. Overriding response."
    )
    validated["intent"] = "out_of_stock"
    validated["ui_actions"] = []
    validated["response_text"] = (
        "I'm sorry, I couldn't find any products matching your request in our current inventory."
    )


def _blocked_response(response_text: str) -> dict[str, Any]:
    return {
        "response_text": response_text,
        "intent": "blocked",
        "confidence": 1.0,
        "ui_actions": [],
    }


def _synthesize_audio_b64(response_text: str, skip_tts: bool) -> tuple[str, float | None]:
    if skip_tts:
        return "", None
    started_at = time.perf_counter()
    try:
        return tts.synthesize_b64(response_text), _ms(started_at)
    except RuntimeError as exc:
        logger.error("PIPELINE | TTS failed: %s - continuing without audio.", exc)
        return "", _ms(started_at)


def _add_variant_ids_to_cart_actions(
    site_id: str,
    actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    for action in actions:
        if action.get("action") != ACTION_ADD_TO_CART:
            continue
        product_id = action.get("params", {}).get(PRODUCT_ID_PARAM)
        if not product_id:
            continue
        try:
            with get_db(site_id) as conn:
                row = conn.execute(
                    "SELECT variant_id FROM products WHERE id = %s",
                    (product_id,),
                ).fetchone()
        except psycopg.Error as exc:
            logger.warning("PIPELINE | variant lookup failed for %s: %s", product_id, exc)
            continue
        if row and row["variant_id"]:
            action["params"]["variant_id"] = str(row["variant_id"])
    return actions


def _apply_capability_filter(
    site_id: str,
    actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Apply runtime capability engine to filter unsupported actions."""
    return _apply_capability_filter_result(site_id, actions)["actions"]


def _apply_capability_filter_result(
    site_id: str,
    actions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Apply runtime capability filtering and keep removal diagnostics."""
    try:
        from agent.capabilities import filter_actions_with_diagnostics
        return filter_actions_with_diagnostics(site_id, actions)
    except PIPELINE_RECOVERABLE_ERRORS as exc:
        logger.warning("PIPELINE | capability filter skipped: %s", exc)
        return {"status": CAPABILITY_FILTER_SKIPPED, "actions": actions, "removed_actions": []}


def _align_response_with_action_filter(response_text: str, filter_report: dict[str, Any]) -> str:
    try:
        from agent.capabilities import action_filter_response_note

        note = action_filter_response_note(filter_report)
    except PIPELINE_RECOVERABLE_ERRORS as exc:
        logger.warning("PIPELINE | action filter response note skipped: %s", exc)
        note = ""
    if not note:
        return response_text
    return _merged_action_filter_response(response_text, note, filter_report)


def _merged_action_filter_response(response_text: str, note: str, filter_report: dict[str, Any]) -> str:
    actions = filter_report.get("actions") if isinstance(filter_report, dict) else []
    if not actions:
        return note
    clean_response = str(response_text or "").strip()
    return f"{clean_response} {note}".strip() if clean_response else note


def _guardrail_audio_b64(message: str, skip_tts: bool) -> str:
    audio_b64, _duration_ms = _synthesize_audio_b64(message, skip_tts)
    return audio_b64


def _merge_products(primary: list[dict], supplemental: list[dict], limit: int | None = None) -> list[dict]:
    merged: list[dict] = []
    seen: set[str] = set()
    for product in [*(supplemental or []), *(primary or [])]:
        product_id = str(product.get("id", ""))
        if not product_id or product_id in seen:
            continue
        seen.add(product_id)
        merged.append(product)
    return merged[:limit] if limit else merged


def _exact_products_from_query(query: str, site_id: str, limit: int = 6) -> list[dict]:
    text = _normalize_lookup_text(query)
    if not text:
        return []

    try:
        from db.database import get_all_products

        products = get_all_products(site_id, limit=1000)
    except PIPELINE_RECOVERABLE_ERRORS as exc:
        logger.warning("PIPELINE | Exact product lookup failed: %s", exc)
        return []

    matches: list[tuple[int, dict]] = []
    for product in products:
        score = _product_name_match_score(product, text)
        if score <= 0:
            continue
        product_copy = dict(product)
        product_copy["_semantic_score"] = max(float(product_copy.get("_semantic_score") or 0.0), 0.98)
        product_copy["_exact_name_match"] = True
        matches.append((score, product_copy))

    matches.sort(
        key=lambda item: (
            -item[0],
            len(_normalize_lookup_text(item[1].get("name", ""))),
            str(item[1].get("name", "")),
        )
    )
    result = [product for _, product in matches[:limit]]
    if len(result) < 2:
        result = _dedupe_products(
            [
                *result,
                *_brand_type_products_from_query(text, products, limit=limit),
                *_lexical_products_from_query(text, products, limit=limit),
            ],
            limit=limit,
        )
    if result:
        logger.info(
            "PIPELINE | Exact product lookup added %d products: %s",
            len(result),
            [p.get("name") for p in result],
        )
    return result


def _product_name_match_score(product: dict, normalized_query: str) -> int:
    name = _normalize_lookup_text(product.get("name", ""))
    if not name:
        return 0

    if _phrase_in_text(name, normalized_query):
        return 100

    aliases = _product_aliases(name)
    best = 0
    for alias in aliases:
        if not alias or not _phrase_in_text(alias, normalized_query):
            continue
        token_count = len(alias.split())
        score = 80 if token_count >= 2 else 35
        best = max(best, score)
    return best


def _product_aliases(normalized_name: str) -> list[str]:
    tokens = normalized_name.split()
    aliases = {normalized_name}
    brand_tokens = {"nova", "acme", "ai", "kart"}
    while tokens and tokens[0] in brand_tokens:
        tokens = tokens[1:]
        if tokens:
            aliases.add(" ".join(tokens))
    if len(tokens) >= 2:
        aliases.add(" ".join(tokens[-2:]))
    elif len(tokens) == 1 and len(tokens[0]) >= 4:
        aliases.add(tokens[0])
    return sorted(aliases, key=lambda item: (-len(item.split()), item))


def _brand_type_products_from_query(normalized_query: str, products: list[dict], limit: int = 6) -> list[dict]:
    requested_types = _requested_product_type_aliases(normalized_query)
    if not requested_types:
        return []
    requested_brands = _requested_catalog_brands(normalized_query, products)
    if len(requested_brands) < 2:
        return []

    by_brand: dict[str, list[tuple[int, dict]]] = {brand: [] for brand in requested_brands}
    for product in products:
        brand_key = _matching_requested_brand(product, requested_brands)
        if not brand_key:
            continue
        search_text = _product_search_text(product)
        type_score = _product_type_match_score(search_text, requested_types)
        if type_score <= 0:
            continue
        product_copy = dict(product)
        product_copy["_semantic_score"] = max(float(product_copy.get("_semantic_score") or 0.0), 0.96)
        product_copy["_exact_name_match"] = True
        score = type_score + _brand_match_score(product, brand_key)
        by_brand[brand_key].append((score, product_copy))

    selected: list[dict] = []
    for brand in requested_brands:
        candidates = by_brand.get(brand) or []
        if not candidates:
            continue
        candidates.sort(
            key=lambda item: (
                -item[0],
                len(_normalize_lookup_text(item[1].get("name", ""))),
                str(item[1].get("name", "")),
            )
        )
        selected.append(candidates[0][1])

    if len(selected) < 2:
        return []
    return selected[:limit]


def _lexical_products_from_query(normalized_query: str, products: list[dict], limit: int = 6) -> list[dict]:
    query_tokens = _significant_lookup_tokens(normalized_query)
    requested_types = _requested_product_type_aliases(normalized_query)
    if not query_tokens and not requested_types:
        return []

    scored: list[tuple[int, str, dict]] = []
    for product in products:
        search_text = _product_search_text(product)
        score = _lexical_product_score(search_text, query_tokens, requested_types)
        if score <= 0:
            continue
        product_copy = dict(product)
        product_copy["_semantic_score"] = max(float(product_copy.get("_semantic_score") or 0.0), min(0.9, 0.45 + (score / 100)))
        product_copy["_lexical_query_match"] = True
        scored.append((score + _stock_score(product), str(product.get("name") or product.get("title") or ""), product_copy))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [product for _score, _name, product in scored[:limit]]


_LOOKUP_STOPWORDS = frozenset(
    {
        "a",
        "about",
        "and",
        "any",
        "best",
        "buy",
        "can",
        "for",
        "from",
        "give",
        "have",
        "help",
        "i",
        "me",
        "need",
        "please",
        "recommend",
        "show",
        "should",
        "tell",
        "the",
        "to",
        "want",
        "what",
        "with",
        "you",
    }
)


def _significant_lookup_tokens(normalized_query: str) -> set[str]:
    tokens = {
        token
        for token in normalized_query.split()
        if len(token) >= 3 and token not in _LOOKUP_STOPWORDS
    }
    if "phones" in tokens:
        tokens.add("phone")
    if "mobiles" in tokens:
        tokens.add("mobile")
    return tokens


def _lexical_product_score(search_text: str, query_tokens: set[str], requested_types: set[str]) -> int:
    score = 0
    for alias in requested_types:
        if _phrase_in_text(alias, search_text):
            score += 35 if alias in {"android", "ios", "iphone", "galaxy"} else 55
    for token in query_tokens:
        if _phrase_in_text(token, search_text):
            score += 18
    return score


def _stock_score(product: dict) -> int:
    try:
        stock = float(product.get("stock") or 0)
    except (TypeError, ValueError):
        stock = 0
    return 5 if bool(product.get("in_stock")) or stock > 0 else 0


def _requested_product_type_aliases(normalized_query: str) -> set[str]:
    phone_aliases = {"phone", "phones", "smartphone", "smartphones", "mobile", "mobiles", "iphone", "galaxy"}
    if any(_phrase_in_text(alias, normalized_query) for alias in phone_aliases):
        return phone_aliases | {"android", "ios"}
    return set()


def _requested_catalog_brands(normalized_query: str, products: list[dict]) -> list[str]:
    alias_to_brand: dict[str, str] = {}
    for product in products:
        brand = _normalize_lookup_text(product.get("brand") or product.get("vendor") or "")
        if not brand or len(brand) < 2:
            continue
        alias_to_brand[brand] = brand
        if brand == "apple":
            alias_to_brand["iphone"] = brand
            alias_to_brand["ios"] = brand
        elif brand == "samsung":
            alias_to_brand["galaxy"] = brand

    matches: list[tuple[int, str]] = []
    for alias, brand in alias_to_brand.items():
        match = re.search(rf"(?:^|\s){re.escape(alias)}(?:\s|$)", normalized_query)
        if match:
            matches.append((match.start(), brand))

    ordered: list[str] = []
    seen: set[str] = set()
    for _position, brand in sorted(matches, key=lambda item: (item[0], item[1])):
        if brand in seen:
            continue
        seen.add(brand)
        ordered.append(brand)
    return ordered


def _matching_requested_brand(product: dict, requested_brands: list[str]) -> str:
    requested = set(requested_brands)
    brand = _normalize_lookup_text(product.get("brand") or product.get("vendor") or "")
    if brand in requested:
        return brand
    search_text = _product_search_text(product)
    for requested_brand in requested_brands:
        if _phrase_in_text(requested_brand, search_text):
            return requested_brand
    return ""


def _product_type_match_score(search_text: str, requested_types: set[str]) -> int:
    best = 0
    for alias in requested_types:
        if _phrase_in_text(alias, search_text):
            if alias in {"phone", "phones", "smartphone", "smartphones", "mobile", "mobiles"}:
                best = max(best, 50)
            else:
                best = max(best, 35)
    return best


def _brand_match_score(product: dict, requested_brand: str) -> int:
    score = 40
    brand = _normalize_lookup_text(product.get("brand") or product.get("vendor") or "")
    if brand == requested_brand:
        score += 25
    try:
        stock = float(product.get("stock") or 0)
    except (TypeError, ValueError):
        stock = 0
    if bool(product.get("in_stock")) or stock > 0:
        score += 5
    return score


def _dedupe_products(products: list[dict], limit: int | None = None) -> list[dict]:
    deduped: list[dict] = []
    seen: set[str] = set()
    for product in products:
        product_id = str(product.get("id", ""))
        if not product_id or product_id in seen:
            continue
        seen.add(product_id)
        deduped.append(product)
        if limit and len(deduped) >= limit:
            break
    return deduped


def _phrase_in_text(phrase: str, text: str) -> bool:
    return f" {phrase} " in f" {text} "


def _normalize_lookup_text(value: Any) -> str:
    text = str(value or "").lower()
    text = text.replace("t-shirt", "t shirt").replace("tee-shirt", "tee shirt")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _promote_comparison_action(response: dict[str, Any], transcript: str) -> None:
    if not _wants_comparison(transcript):
        return

    for action in response.get("ui_actions", []):
        if action.get("action") == ACTION_SHOW_PRODUCTS:
            product_ids = action.get("params", {}).get(PRODUCT_IDS_PARAM, [])
            if isinstance(product_ids, list) and len(product_ids) >= 2:
                action["action"] = ACTION_SHOW_COMPARISON
                action["params"] = {PRODUCT_IDS_PARAM: product_ids[:4]}
                response["intent"] = "product_compare"
                return


def _ensure_named_comparison_response(
    response: dict[str, Any],
    transcript: str,
    retrieved_products: list[dict],
) -> None:
    if not _wants_comparison(transcript):
        return
    if any(action.get("action") == ACTION_SHOW_COMPARISON for action in response.get("ui_actions", [])):
        return

    exact_products = [p for p in retrieved_products if p.get("_exact_name_match")]
    if len(exact_products) < 2:
        return

    selected = exact_products[:4]
    product_ids = [str(product["id"]) for product in selected]
    response["intent"] = "product_compare"
    response["confidence"] = max(float(response.get("confidence") or 0.0), 0.9)
    response["ui_actions"] = [
        {"action": ACTION_SHOW_COMPARISON, "params": {PRODUCT_IDS_PARAM: product_ids}}
    ]
    response["response_text"] = _comparison_fallback_text(selected)


def _ensure_generic_comparison_response(
    response: dict[str, Any],
    transcript: str,
    retrieved_items: list[dict],
) -> None:
    if not _wants_comparison(transcript):
        return
    if any(action.get("action") == ACTION_COMPARE_ENTITIES for action in response.get("ui_actions", [])):
        return

    comparable_items = [item for item in retrieved_items if item.get("id") is not None]
    if len(comparable_items) < 2:
        return

    selected = comparable_items[:4]
    entity_ids = [str(item["id"]) for item in selected]
    response["intent"] = "compare"
    response["confidence"] = max(float(response.get("confidence") or 0.0), 0.88)
    response["ui_actions"] = [
        {"action": ACTION_COMPARE_ENTITIES, "params": {ENTITY_IDS_PARAM: entity_ids}}
    ]
    response["response_text"] = _generic_comparison_fallback_text(selected)


def _ensure_product_answer_response(
    response: dict[str, Any],
    transcript: str,
    retrieved_products: list[dict],
) -> None:
    if not _wants_source_answer(transcript) or _wants_comparison(transcript) or _wants_cart_add(transcript):
        return
    if any(action.get("action") in {ACTION_SHOW_PRODUCTS, ACTION_SHOW_COMPARISON} for action in response.get("ui_actions", [])):
        return

    selected = _answer_target_products(transcript, retrieved_products)
    if not selected:
        return

    product_ids = [str(product["id"]) for product in selected if product.get("id")]
    if not product_ids:
        return

    response["intent"] = "product_detail" if len(selected) == 1 else "product_search"
    response["confidence"] = max(float(response.get("confidence") or 0.0), 0.86)
    response["ui_actions"] = [
        {"action": ACTION_SHOW_PRODUCTS, "params": {PRODUCT_IDS_PARAM: product_ids[:6]}}
    ]
    response["response_text"] = _product_answer_fallback_text(selected)


def _ensure_entity_answer_response(
    response: dict[str, Any],
    transcript: str,
    retrieved_items: list[dict],
) -> None:
    if not _wants_source_answer(transcript) or _wants_comparison(transcript):
        return
    if any(
        action.get("action") in {ACTION_SHOW_ENTITIES, ACTION_COMPARE_ENTITIES, "OPEN_ENTITY_DETAIL"}
        for action in response.get("ui_actions", [])
    ):
        return

    selected = [item for item in retrieved_items if item.get("id") is not None][:4]
    if not selected:
        return

    response["intent"] = "discovery"
    response["confidence"] = max(float(response.get("confidence") or 0.0), 0.86)
    response["ui_actions"] = [
        {"action": ACTION_SHOW_ENTITIES, "params": {ENTITY_IDS_PARAM: [str(item["id"]) for item in selected]}}
    ]
    response["response_text"] = _entity_answer_fallback_text(selected)


def _ensure_lead_flow_response(response: dict[str, Any], transcript: str, site_id: str) -> None:
    """Recover obvious quote/booking/application intents when the LLM omits a UI action."""
    if response.get("ui_actions"):
        return
    action_name = _lead_flow_action_from_transcript(transcript, site_id)
    if not action_name:
        return

    response["intent"] = "lead_flow"
    response["confidence"] = max(float(response.get("confidence") or 0.0), 0.86)
    response["ui_actions"] = [{"action": action_name, "params": {}}]
    response["response_text"] = _lead_flow_fallback_text(action_name)


def _lead_flow_action_from_transcript(transcript: str, site_id: str) -> str:
    normalized = _normalize_lookup_text(transcript)
    if not normalized:
        return ""

    allowed_actions = _lead_flow_actions_for_site(site_id)
    if not allowed_actions:
        return ""

    for action_name, patterns in LEAD_FLOW_INTENT_PATTERNS:
        if action_name not in allowed_actions:
            continue
        if any(re.search(pattern, normalized) for pattern in patterns):
            return action_name
    return ""


def _lead_flow_actions_for_site(site_id: str) -> set[str]:
    candidates: set[str] = set()
    try:
        from agent.capabilities import get_allowed_actions

        candidates.update(get_allowed_actions(site_id))
    except PIPELINE_RECOVERABLE_ERRORS as exc:
        logger.warning("PIPELINE | lead fallback capability lookup skipped: %s", exc)

    try:
        from agent.actions.registry import get_action
    except ImportError as exc:
        logger.warning("PIPELINE | lead fallback action registry skipped: %s", exc)
        return set()

    try:
        from agent.verticals.registry import get_vertical
        vertical = get_vertical(get_client_vertical_key(site_id))
        candidates.update(vertical.action_types)
    except PIPELINE_RECOVERABLE_ERRORS as exc:
        logger.warning("PIPELINE | lead fallback vertical lookup skipped: %s", exc)
    return {
        action_name
        for action_name in candidates
        if (definition := get_action(action_name)) and definition.family == "lead"
    }


def _lead_flow_fallback_text(action_name: str) -> str:
    labels = {
        "START_QUOTE": "I can start the quote flow now.",
        "START_BOOKING": "I can start the booking flow now.",
        "START_APPLICATION": "I can start the application flow now.",
        "REQUEST_APPOINTMENT": "I can start the appointment request now.",
        "BOOK_APPOINTMENT_REQUEST": "I can start the appointment request now.",
        "REQUEST_TEST_DRIVE": "I can start the test-drive request now.",
        "REQUEST_VIEWING": "I can start the viewing request now.",
        "REQUEST_CONSULTATION": "I can start the consultation request now.",
        "REQUEST_ESTIMATE": "I can start the estimate request now.",
        "REQUEST_SITE_VISIT": "I can start the site-visit request now.",
        "START_TICKET_PURCHASE": "I can start the ticket flow now.",
        "START_ENROLLMENT": "I can start the enrollment flow now.",
        "REQUEST_COUNSELOR_CALLBACK": "I can request a counselor callback now.",
        "REQUEST_CALLBACK": "I can request a callback now.",
        "CONTACT_AGENT": "I can connect you with an agent now.",
        "CAPTURE_LEAD": "I can open the contact flow now.",
    }
    return labels.get(action_name, "I can start that website flow now.")


def _wants_source_answer(text: str) -> bool:
    normalized = _normalize_lookup_text(text)
    if not normalized:
        return False
    patterns = (
        r"\bwhy\b",
        r"\bshould i\b",
        r"\brecommend\b",
        r"\btell me about\b",
        r"\bdetails?\b",
        r"\bfacts?\b",
        r"\bfeatures?\b",
        r"\bspecs?\b",
        r"\bspecifications?\b",
        r"\bprice\b",
        r"\bcost\b",
        r"\bpremium\b",
        r"\bcoverage\b",
        r"\bin stock\b",
        r"\bavailable\b",
    )
    return any(re.search(pattern, normalized) for pattern in patterns)


def _answer_target_products(transcript: str, products: list[dict]) -> list[dict]:
    candidates = [product for product in products if product.get("id")]
    if not candidates:
        return []

    targeted = _cart_target_product(transcript, candidates)
    if targeted:
        return [targeted]

    normalized = _normalize_lookup_text(transcript)
    for product in candidates:
        name = _normalize_lookup_text(product.get("name") or product.get("title") or "")
        if name and _phrase_in_text(name, normalized):
            return [product]

    if len(candidates) == 1:
        return candidates
    return candidates[:3]


def _product_answer_fallback_text(products: list[dict]) -> str:
    if len(products) == 1:
        product = products[0]
        details = _product_fact_parts(product)
        detail_text = " ".join(details) if details else "I found it in the catalog."
        return f"Based on the catalog, {_product_display_name(product)} is worth considering. {detail_text}"

    bullets = [f"- {_product_display_name(product)}: {' '.join(_product_fact_parts(product)) or 'catalog item'}" for product in products[:3]]
    return "Here are source-backed options to consider:\n" + "\n".join(bullets)


def _product_fact_parts(product: dict) -> list[str]:
    parts: list[str] = []
    brand = str(product.get("brand") or product.get("vendor") or "").strip()
    category = str(product.get("category_name") or product.get("category") or product.get("subcategory") or "").strip()
    description = str(product.get("description") or product.get("summary") or "").strip()
    price = _product_price(product)
    stock = _product_stock(product)
    if brand:
        parts.append(f"Brand: {brand}.")
    if category:
        parts.append(f"Category: {category}.")
    if price is not None and price > 0:
        parts.append(f"Price: {price:g}.")
    if stock is not None:
        parts.append("In stock." if stock > 0 else "Currently sold out.")
    if description:
        parts.append(description[:180])
    return parts


def _entity_answer_fallback_text(items: list[dict]) -> str:
    if len(items) == 1:
        title = _entity_display_name(items[0])
        detail = _entity_fact_text(items[0])
        return f"Based on the website data, {title}: {detail}"

    bullets = [f"- {_entity_display_name(item)}: {_entity_fact_text(item)}" for item in items[:4]]
    return "Based on the website data, these records are relevant:\n" + "\n".join(bullets)


def _entity_display_name(item: dict) -> str:
    return str(item.get("title") or item.get("name") or "This record")


def _entity_fact_text(item: dict) -> str:
    summary = str(item.get("summary") or item.get("body") or "").strip()
    price = _product_price(item)
    parts: list[str] = []
    if price is not None and price > 0:
        parts.append(f"published price or premium {price:g}")
    if summary:
        parts.append(summary[:220])
    if not parts:
        parts.append("source-backed record; confirm final fit with the website or provider")
    return "; ".join(parts)


def _ensure_cart_request_response(
    response: dict[str, Any],
    transcript: str,
    retrieved_products: list[dict],
) -> None:
    """Recover an explicit add-to-cart request when the LLM omits the action."""
    if not _wants_cart_add(transcript):
        return
    if any(action.get("action") == ACTION_ADD_TO_CART for action in response.get("ui_actions", [])):
        return

    product = _cart_target_product(transcript, retrieved_products)
    if not product:
        return

    product_id = str(product.get("id") or "")
    if not product_id:
        return

    stock = _product_stock(product)
    if stock is not None and stock <= 0:
        response["intent"] = "out_of_stock"
        response["ui_actions"] = []
        response["response_text"] = f"{_product_display_name(product)} is sold out right now, so I cannot add it to your cart."
        return

    quantity = _cart_quantity(transcript)
    if stock is not None:
        quantity = min(quantity, stock)

    action = {"action": ACTION_ADD_TO_CART, "params": {PRODUCT_ID_PARAM: product_id}}
    if quantity > 1:
        action["params"][QUANTITY_PARAM] = quantity

    response["intent"] = "add_to_cart"
    response["confidence"] = max(float(response.get("confidence") or 0.0), 0.9)
    response.setdefault("ui_actions", []).append(action)
    response["response_text"] = _cart_confirmation_text(product, quantity)


def _wants_cart_add(text: str) -> bool:
    normalized = _normalize_lookup_text(text)
    if not normalized:
        return False
    cart_words = {"cart", "basket", "bag", "tray"}
    if not any(_phrase_in_text(word, normalized) for word in cart_words):
        return False
    return bool(
        re.search(r"\b(add|put|place|drop|send)\b.{0,45}\b(cart|basket|bag|tray)\b", normalized)
        or re.search(r"\b(cart|basket|bag|tray)\b.{0,45}\b(add|put|place|drop|send)\b", normalized)
        or re.search(r"\b(i will take|i ll take|i want|buy|get me)\b", normalized)
    )


def _cart_target_product(transcript: str, products: list[dict]) -> dict | None:
    candidates = [product for product in products if product.get("id")]
    if not candidates:
        return None

    normalized = _normalize_lookup_text(transcript)
    ordinal_index = _ordinal_index(normalized)
    if ordinal_index is not None and ordinal_index < len(candidates):
        return candidates[ordinal_index]

    if any(_phrase_in_text(token, normalized) for token in ("cheaper", "cheapest", "lowest price", "least expensive")):
        return min(candidates, key=lambda product: _product_price(product) or float("inf"))
    if any(_phrase_in_text(token, normalized) for token in ("expensive", "costliest", "premium")):
        return max(candidates, key=lambda product: _product_price(product) or 0)

    for product in candidates:
        name = _normalize_lookup_text(product.get("name") or product.get("title") or "")
        if name and _phrase_in_text(name, normalized):
            return product

    if len(candidates) == 1:
        return candidates[0]
    return None


def _ordinal_index(text: str) -> int | None:
    ordinals = {
        "first": 0,
        "1st": 0,
        "one": 0,
        "option 1": 0,
        "second": 1,
        "2nd": 1,
        "two": 1,
        "option 2": 1,
        "third": 2,
        "3rd": 2,
        "three": 2,
        "option 3": 2,
        "fourth": 3,
        "4th": 3,
        "four": 3,
        "option 4": 3,
    }
    for token, index in ordinals.items():
        if _phrase_in_text(token, text):
            return index
    return None


def _cart_quantity(text: str) -> int:
    normalized = _normalize_lookup_text(text)
    quantity_text = re.sub(r"\b(option|item|product|choice)\s+[1-9][0-9]?\b", " ", normalized)
    quantity_text = re.sub(
        r"\b(first|second|third|fourth|1st|2nd|3rd|4th)\b",
        " ",
        quantity_text,
    )
    word_numbers = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
    }
    for word, number in word_numbers.items():
        if _phrase_in_text(word, quantity_text):
            return number
    match = re.search(r"\b([1-9][0-9]?)\b", quantity_text)
    if not match:
        return 1
    return max(1, min(99, int(match.group(1))))


def _product_stock(product: dict) -> int | None:
    raw_stock = product.get("stock")
    if raw_stock is None:
        return None
    try:
        return max(0, int(float(raw_stock)))
    except (TypeError, ValueError):
        return None


def _product_price(product: dict) -> float | None:
    try:
        return float(product.get("price"))
    except (TypeError, ValueError):
        return None


def _product_display_name(product: dict) -> str:
    return str(product.get("name") or product.get("title") or "That item")


def _cart_confirmation_text(product: dict, quantity: int) -> str:
    name = _product_display_name(product)
    if quantity > 1:
        return f"Added {quantity} x {name} to your cart."
    return f"Added {name} to your cart."


def _prevent_false_empty_inventory_claim(response: dict[str, Any], transcript: str, site_id: str) -> None:
    text = str(response.get("response_text") or "")
    if not _claims_store_inventory_empty(text):
        return

    try:
        stats = tenant_inventory_summary(site_id)
        in_stock = int(stats.get("in_stock_products") or 0)
    except PIPELINE_RECOVERABLE_ERRORS as exc:
        logger.warning("PIPELINE | inventory summary unavailable: %s", exc)
        in_stock = 0

    if in_stock <= 0:
        return

    categories: list[str] = []
    try:
        categories = _available_category_names(get_all_products(site_id, limit=1000))
    except PIPELINE_RECOVERABLE_ERRORS as exc:
        logger.warning("PIPELINE | category lookup unavailable: %s", exc)
        categories = []

    category_text = f" We have categories like {', '.join(categories[:5])}." if categories else ""
    if _mentions_cart_or_tray(transcript):
        response["response_text"] = (
            "Your cart or tray looks empty right now, but we do have plenty of products in stock."
            f"{category_text} Tell me what you need and I'll help you find it."
        )
    else:
        response["response_text"] = (
            "We do have plenty of products in stock. I just couldn't find an exact match for that request."
            f"{category_text} Tell me what you need and I'll help you shop."
        )
    response["intent"] = "chitchat"
    response["confidence"] = max(float(response.get("confidence") or 0.0), 0.9)
    response["ui_actions"] = []


def _claims_store_inventory_empty(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", (text or "").lower()).strip()
    patterns = [
        r"\b(no|not|don't|do not|doesn't|does not|couldn't|could not)\b.{0,40}\b(items?|products?)\b.{0,40}\b(inventory|catalog|store)\b",
        r"\b(inventory|catalog|store)\b.{0,30}\b(empty|no items|no products|nothing available)\b",
        r"\b(no items|no products|nothing)\b.{0,30}\bavailable\b.{0,30}\b(inventory|catalog|store)\b",
    ]
    return any(re.search(pattern, normalized) for pattern in patterns)


def _mentions_cart_or_tray(text: str) -> bool:
    normalized = re.sub(r"[^a-z\s]", " ", (text or "").lower())
    words = set(normalized.split())
    return bool(words & {"cart", "tray", "basket", "bag"})


def _comparison_fallback_text(products: list[dict]) -> str:
    names = " and ".join(str(product.get("name", "this product")) for product in products[:2])
    bullets = []
    for product in products[:4]:
        bullets.append(
            f"- {product.get('name')}: {product.get('category_name') or product.get('category') or 'Product'}, "
            f"priced at ${float(product.get('price') or 0):.2f}. "
            f"{str(product.get('description') or '').strip()[:120]}"
        )
    return f"I found {names}. Here's a quick comparison:\n" + "\n".join(bullets)


def _generic_comparison_fallback_text(items: list[dict]) -> str:
    bullets = []
    for item in items[:4]:
        title = item.get("title") or item.get("name") or "Option"
        summary = str(item.get("summary") or item.get("body") or item.get("category_name") or "").strip()
        price = float(item.get("price") or 0)
        detail_parts = []
        if price > 0:
            detail_parts.append(f"price or premium {price:g}")
        if summary:
            detail_parts.append(summary[:140])
        detail = "; ".join(detail_parts) if detail_parts else "source-backed record"
        bullets.append(f"- {title}: {detail}")
    return "I found matching records to compare:\n" + "\n".join(bullets)


def _wants_comparison(transcript: str) -> bool:
    text = (transcript or "").lower()
    return any(
        token in text
        for token in ("compare", "comparison", "difference", "better", "versus", " vs ")
    )


def _is_simple_greeting(transcript: str) -> bool:
    text = re.sub(r"[^a-z\s]", " ", (transcript or "").lower())
    words = [word for word in text.split() if word]
    if not words or len(words) > 5:
        return False
    greeting_words = {"hello", "hi", "hey", "namaste", "yo"}
    return any(word in greeting_words for word in words)


def _navigation_intent_response(
    site_id: str,
    transcript: str,
    safe_transcript: str,
    skip_tts: bool,
    timings: dict[str, float],
    start_time: float,
) -> dict[str, Any] | None:
    page = _navigation_page_from_transcript(site_id, safe_transcript)
    if not page:
        return None

    label = page.replace("-", " ").replace("_", " ").strip() or "that page"
    response_text = f"Opening {label}."
    final_actions = [{"action": ACTION_NAVIGATE_TO, "params": {"page": page}}]
    _ai_log("assistant", response_text)
    _ai_log("actions", final_actions)

    audio_b64 = ""
    if not skip_tts:
        t = time.perf_counter()
        try:
            audio_b64 = tts.synthesize_b64(response_text)
        except RuntimeError as exc:
            logger.error("PIPELINE | TTS failed for navigation: %s", exc)
        timings["tts_ms"] = _ms(t)

    timings["total_ms"] = _ms(start_time)
    return {
        "transcript": transcript,
        "response_text": response_text,
        "intent": "navigate",
        "confidence": 1.0,
        "ui_actions": final_actions,
        "audio_b64": audio_b64,
        "latency_ms": timings,
    }


def _sort_intent_response(
    site_id: str,
    transcript: str,
    safe_transcript: str,
    ecommerce_runtime: bool,
    skip_tts: bool,
    timings: dict[str, float],
    start_time: float,
) -> dict[str, Any] | None:
    sort_by = _sort_key_from_transcript(safe_transcript)
    if not sort_by:
        return None

    action = ACTION_SORT_PRODUCTS if ecommerce_runtime else ACTION_SORT_ENTITIES
    subject = "products" if ecommerce_runtime else _vertical_entity_plural(site_id)
    response_text = _sort_response_text(subject, sort_by)
    final_actions = [{"action": action, "params": {"sort_by": sort_by}}]
    _ai_log("assistant", response_text)
    _ai_log("actions", final_actions)

    audio_b64 = ""
    if not skip_tts:
        t = time.perf_counter()
        try:
            audio_b64 = tts.synthesize_b64(response_text)
        except RuntimeError as exc:
            logger.error("PIPELINE | TTS failed for sort action: %s", exc)
        timings["tts_ms"] = _ms(t)

    timings["total_ms"] = _ms(start_time)
    return {
        "transcript": transcript,
        "response_text": response_text,
        "intent": "sort",
        "confidence": 1.0,
        "ui_actions": final_actions,
        "audio_b64": audio_b64,
        "latency_ms": timings,
    }


def _sort_key_from_transcript(transcript: str) -> str:
    text = _normalize_navigation_text(transcript)
    if not _looks_like_sort_request(text):
        return ""
    if re.search(r"\b(high to low|highest first|expensive|costliest|premium high|price high|descending)\b", text):
        return "price_desc"
    if re.search(r"\b(rating|rated|review|best rated)\b", text):
        return "rating"
    if re.search(r"\b(newest|latest|recent)\b", text):
        return "newest"
    if re.search(r"\b(low to high|lowest first|cheapest|affordable|budget|premium low|price low|ascending)\b", text):
        return "price_asc"
    return "price_asc"


def _looks_like_sort_request(text: str) -> bool:
    return bool(
        re.search(r"\b(sort|arrange|order|rank)\b", text)
        or re.search(r"\b(low to high|high to low|lowest first|highest first|cheapest|expensive|newest|latest|best rated)\b", text)
    )


def _sort_response_text(subject: str, sort_by: str) -> str:
    labels = {
        "price_asc": "low to high",
        "price_desc": "high to low",
        "rating": "by rating",
        "newest": "newest first",
    }
    label = labels.get(sort_by, "low to high")
    return f"Sorting visible {subject} {label}."


def _vertical_entity_plural(site_id: str) -> str:
    try:
        from agent.verticals.registry import get_vertical

        vertical = get_vertical(get_client_vertical_key(site_id))
        return vertical.entity_label_plural
    except PIPELINE_RECOVERABLE_ERRORS as exc:
        logger.warning("PIPELINE | vertical entity label unavailable for %s: %s", site_id, exc)
        return "options"


def _navigation_page_from_transcript(site_id: str, transcript: str) -> str:
    text = _normalize_navigation_text(transcript)
    if not _looks_like_navigation_request(text):
        return ""

    route_terms = _navigation_route_terms(site_id)
    for term, page in route_terms:
        if _navigation_term_matches(text, term):
            return page
    return ""


def _looks_like_navigation_request(text: str) -> bool:
    return bool(
        re.search(
            r"\b("
            r"go|open|navigate|take|send|move|switch|visit|show"
            r")\b.{0,24}\b("
            r"page|tab|section|screen|home|plans?|claims?|polic(?:y|ies)|renewal|quote|contact|about|cart|checkout|shop"
            r")\b",
            text,
        )
        or re.search(r"\b(back|return)\b.{0,16}\b(home|main|start)\b", text)
    )


def _navigation_route_terms(site_id: str) -> list[tuple[str, str]]:
    routes = _client_route_map(site_id)
    terms: dict[str, str] = {
        "home": "home",
        "main": "home",
        "start": "home",
        "shop": "shop",
        "store": "shop",
        "cart": "cart",
        "basket": "cart",
        "checkout": "checkout",
        "support": "support",
        "help": "support",
        "contact": "contact",
        "about": "about",
        "plans": "plans",
        "plan": "plans",
        "policies": "policies",
        "policy": "policies",
        "claims": "claims",
        "claim": "claims",
        "renewal": "renewal",
        "renew": "renewal",
        "quote": "quote",
        "quotes": "quote",
    }
    for key, path in routes.items():
        page = _route_page_key(key, path)
        if not page:
            continue
        terms[_normalize_navigation_text(key)] = page
        terms[_normalize_navigation_text(page)] = page
        last_segment = _route_last_segment(path)
        if last_segment:
            terms[_normalize_navigation_text(last_segment)] = page
    return sorted(terms.items(), key=lambda item: len(item[0]), reverse=True)


def _client_route_map(site_id: str) -> dict[str, str]:
    try:
        client = get_client_detail(site_id)
    except PIPELINE_RECOVERABLE_ERRORS as exc:
        logger.info("PIPELINE | navigation routes unavailable for %s: %s", site_id, exc)
        return {}
    vertical_config = client.get("vertical_config") if isinstance(client, dict) else {}
    routes = vertical_config.get("routes") if isinstance(vertical_config, dict) else {}
    return {str(key): str(value) for key, value in routes.items() if key and value} if isinstance(routes, dict) else {}


def _route_page_key(key: str, path: str) -> str:
    clean_key = _safe_page_key(key)
    if clean_key:
        return clean_key
    return _safe_page_key(_route_last_segment(path))


def _route_last_segment(path: str) -> str:
    text = str(path or "").split("?", 1)[0].split("#", 1)[0].strip("/")
    if not text:
        return "home"
    return text.split("/")[-1]


def _safe_page_key(value: str) -> str:
    text = re.sub(r"[^a-z0-9/_-]+", "-", str(value or "").strip().lower()).strip("-/")
    if not text:
        return ""
    return text[:80]


def _navigation_term_matches(text: str, term: str) -> bool:
    clean_term = _normalize_navigation_text(term)
    if not clean_term:
        return False
    return bool(re.search(rf"\b{re.escape(clean_term)}\b", text))


def _normalize_navigation_text(value: str) -> str:
    text = re.sub(r"[^a-z0-9\s_-]+", " ", str(value or "").lower())
    text = text.replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", text).strip()


def _is_inventory_stats_query(transcript: str) -> bool:
    text = (transcript or "").lower()
    has_inventory_word = any(
        token in text
        for token in ("inventory", "catalog", "catalogue", "data", "products", "items", "stock")
    )
    has_count_word = any(
        token in text
        for token in ("how many", "count", "total", "number", "available", "right now")
    )
    return has_inventory_word and has_count_word


def _extract_inventory_type_query(transcript: str) -> str | None:
    text = re.sub(r"[^a-z0-9\s-]", " ", (transcript or "").lower())
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return None

    patterns = [
        r"\bhow many (?:types|kinds|options|varieties) of ([a-z0-9\s-]+?)(?: do you have| are available| available| in stock| right now|$)",
        r"\bhow many ([a-z0-9\s-]+?)(?: do you have| are available| available| in stock| right now|$)",
        r"\bdo you have (?:any )?([a-z0-9\s-]+?)(?: available| in stock| right now|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        term = _clean_inventory_type_term(match.group(1))
        if term:
            return term
    return None


def _clean_inventory_type_term(raw: str) -> str:
    term = re.sub(
        r"\b(products?|items?|types?|kinds?|options?|varieties|stock|inventory|catalog|catalogue)\b",
        " ",
        raw or "",
    )
    term = re.sub(r"\s+", " ", term).strip(" -")
    if not term:
        return ""
    words = term.split()
    if len(words) > 4:
        return ""
    normalized_words = []
    for word in words:
        if word.endswith("ies") and len(word) > 4:
            normalized_words.append(f"{word[:-3]}y")
        elif word.endswith("s") and len(word) > 3:
            normalized_words.append(word[:-1])
        else:
            normalized_words.append(word)
    return " ".join(normalized_words)


def _greeting_response(
    transcript: str,
    skip_tts: bool,
    timings: dict[str, float],
    start_time: float,
) -> dict[str, Any]:
    response_text = "Hi, I am ready to help. Tell me what you want to find today."
    _ai_log("assistant", response_text)
    _ai_log("actions", [])

    audio_b64 = ""
    if not skip_tts:
        t = time.perf_counter()
        try:
            audio_b64 = tts.synthesize_b64(response_text)
        except RuntimeError as exc:
            logger.error("PIPELINE | TTS failed for greeting: %s", exc)
        timings["tts_ms"] = _ms(t)

    timings["total_ms"] = _ms(start_time)
    logger.info("PIPELINE | Greeting answered in %.0fms", timings["total_ms"])
    return {
        "transcript": transcript,
        "response_text": response_text,
        "intent": "greeting",
        "confidence": 1.0,
        "ui_actions": [],
        "audio_b64": audio_b64,
        "latency_ms": timings,
    }


def _inventory_type_count_response(
    site_id: str,
    transcript: str,
    item_type: str,
    skip_tts: bool,
    timings: dict[str, float],
    start_time: float,
) -> dict[str, Any]:
    t = time.perf_counter()
    try:
        products = get_all_products(site_id, limit=1000)
    except PIPELINE_RECOVERABLE_ERRORS as exc:
        logger.error("Inventory type lookup failed: %s", exc)
        products = []
    timings["inventory_lookup_ms"] = _ms(t)

    matches = _matching_inventory_products(products, item_type)
    plural = _pluralize(item_type, len(matches))
    final_actions: list[dict[str, Any]] = []

    if matches:
        names = [str(product.get("name") or product.get("title") or "").strip() for product in matches[:3]]
        shown_names = ", ".join(name for name in names if name)
        response_text = f"I found {len(matches)} {plural} in stock"
        if shown_names:
            response_text += f": {shown_names}"
        response_text += "."
        final_actions = [
            {
                "action": ACTION_SHOW_PRODUCTS,
                "params": {
                    PRODUCT_IDS_PARAM: [str(product.get("id")) for product in matches[:8] if product.get("id")],
                    "search_query": item_type,
                },
            }
        ]
    else:
        categories = _available_category_names(products)
        if categories:
            response_text = (
                f"I don't have {item_type}s right now. "
                f"I do have categories like {', '.join(categories[:5])}."
            )
        else:
            response_text = f"I don't have {item_type}s right now."

    _ai_log("assistant", response_text)
    _ai_log("actions", final_actions)

    audio_b64 = ""
    if not skip_tts:
        t = time.perf_counter()
        try:
            audio_b64 = tts.synthesize_b64(response_text)
        except RuntimeError as exc:
            logger.error("PIPELINE | TTS failed for inventory type count: %s", exc)
        timings["tts_ms"] = _ms(t)

    timings["total_ms"] = _ms(start_time)
    return {
        "transcript": transcript,
        "response_text": response_text,
        "intent": "inventory_status",
        "confidence": 1.0,
        "ui_actions": final_actions,
        "audio_b64": audio_b64,
        "latency_ms": timings,
    }


def _matching_inventory_products(products: list[dict], item_type: str) -> list[dict]:
    normalized_type = _normalize_lookup_text(item_type)
    matches = []
    for product in products:
        search_text = _product_search_text(product)
        if normalized_type and normalized_type in search_text:
            matches.append(product)
    return matches


def _product_search_text(product: dict) -> str:
    values = [
        product.get("name"),
        product.get("title"),
        product.get("brand"),
        product.get("vendor"),
        product.get("category"),
        product.get("category_name"),
        product.get("category_slug"),
        product.get("description"),
        product.get("tags"),
    ]
    return _normalize_lookup_text(" ".join(str(value or "") for value in values))


def _available_category_names(products: list[dict]) -> list[str]:
    seen: set[str] = set()
    names: list[str] = []
    for product in products:
        category = str(product.get("category_name") or product.get("category") or "").strip()
        if not category:
            continue
        key = category.lower()
        if key in {"product", "products"}:
            continue
        if key in seen:
            continue
        seen.add(key)
        names.append(category.replace("-", " ").title())
    return names


def _pluralize(term: str, count: int) -> str:
    if count == 1:
        return term
    if term.endswith("y"):
        return f"{term[:-1]}ies"
    if term.endswith("s"):
        return term
    return f"{term}s"


def _inventory_stats_response(
    site_id: str,
    transcript: str,
    skip_tts: bool,
    timings: dict[str, float],
    start_time: float,
) -> dict[str, Any]:
    try:
        stats = tenant_inventory_summary(site_id)
        logger.info("Inventory stats requested; internal counts hidden from customer: %s", stats)
    except PIPELINE_RECOVERABLE_ERRORS as exc:
        logger.error("Inventory stats lookup failed: %s", exc)
    response_text = (
        "I have plenty of products available to browse. "
        "Tell me what you are looking for, and I will find the best options for you."
    )

    audio_b64 = ""
    if not skip_tts:
        t = time.perf_counter()
        try:
            audio_b64 = tts.synthesize_b64(response_text)
        except RuntimeError as exc:
            logger.error("PIPELINE | TTS failed for inventory stats: %s", exc)
        timings["tts_ms"] = _ms(t)

    timings["total_ms"] = _ms(start_time)
    logger.info("PIPELINE | Inventory stats answered in %.0fms", timings["total_ms"])
    return {
        "transcript": transcript,
        "response_text": response_text,
        "intent": "inventory_status",
        "confidence": 1.0,
        "ui_actions": [],
        "audio_b64": audio_b64,
        "latency_ms": timings,
    }


def _error_response(message: str, timings: dict) -> dict[str, Any]:
    return {
        "transcript": "",
        "response_text": message,
        "intent": "error",
        "confidence": 0.0,
        "ui_actions": [],
        "audio_b64": "",
        "latency_ms": timings,
    }


def _guardrail_response(
    message: str,
    transcript: str,
    skip_tts: bool,
    timings: dict,
) -> dict[str, Any]:
    """Return a guardrail rejection response with TTS if requested."""
    audio_b64 = _guardrail_audio_b64(message, skip_tts)
    return {
        "transcript": transcript,
        "response_text": message,
        "intent": "blocked",
        "confidence": 1.0,
        "ui_actions": [],
        "audio_b64": audio_b64,
        "latency_ms": timings,
    }


def _extract_products_from_history(history: list[dict], site_id: str) -> list[dict]:
    """
    Check the previous assistant response text for product names or IDs
    and retrieve them from the database to retain multi-turn RAG context.

    The frontend embeds a `[PRODUCT_IDS: id1,id2,...]` tag in assistant messages
    so that even ordinal references like "add the first one" can be resolved.
    """
    if not history:
        return []

    # Get the last assistant message
    last_assistant_msg = ""
    for msg in reversed(history):
        if msg.get("role") == "assistant" and msg.get("content"):
            last_assistant_msg = msg["content"]
            break

    if not last_assistant_msg:
        return []

    # --- Strategy 1: Parse [PRODUCT_IDS: ...] tag inserted by frontend ---
    import re as _re
    id_tag_match = _re.search(r'\[PRODUCT_IDS:\s*([\d,\s]+)\]', last_assistant_msg)
    tagged_ids: list[int] = []
    if id_tag_match:
        raw_ids = id_tag_match.group(1)
        for pid_str in raw_ids.split(','):
            pid_str = pid_str.strip()
            if pid_str.isdigit():
                tagged_ids.append(int(pid_str))
        logger.info("PIPELINE | Found %d product IDs from history tag: %s", len(tagged_ids), tagged_ids)

    # --- Strategy 2: Name-matching fallback ---
    from db.database import get_all_products, get_products_by_ids
    mentioned = []

    # First: fetch tagged products directly by ID (fast, reliable)
    if tagged_ids:
        try:
            tagged_products = get_products_by_ids(site_id, tagged_ids)
            for product in tagged_products:
                p_copy = dict(product)
                p_copy["_semantic_score"] = 0.95
                mentioned.append(p_copy)
        except PIPELINE_RECOVERABLE_ERRORS as exc:
            logger.warning("PIPELINE | History tag product bulk lookup failed: %s", exc)

    # Then: name-match remaining products not already found via tag
    if not mentioned:
        try:
            products = get_all_products(site_id, limit=100)
        except PIPELINE_RECOVERABLE_ERRORS as exc:
            logger.error("PIPELINE | History product check failed to get all products: %s", exc)
            products = []

        for p in products:
            name = p.get("name") or p.get("title") or ""
            p_id = str(p.get("id", ""))
            # Check if the product name or exact ID is mentioned in the assistant's previous message text
            if (name and name.lower() in last_assistant_msg.lower()) or (p_id and p_id in last_assistant_msg):
                # Skip if already added via tag
                if any(str(m.get("id")) == p_id for m in mentioned):
                    continue
                p_copy = dict(p)
                p_copy["_semantic_score"] = 0.95  # Give it a high score since it was just discussed
                mentioned.append(p_copy)

    if mentioned:
        logger.info("PIPELINE | Extracted %d previously discussed products from history context", len(mentioned))
    return mentioned
