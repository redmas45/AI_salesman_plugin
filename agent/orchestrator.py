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
from typing import Any, Generator, Optional

from agent import guardrails, llm, rag, stt, tts
from agent.guardrails import InputGuardrailError, OutputGuardrailError
from agent.prompt import format_cart_for_prompt
from db.database import (
    get_all_products,
    get_cart_items,
    get_user_profile,
    tenant_inventory_summary,
    update_user_preferences,
    get_db,
)

logger = logging.getLogger(__name__)


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
    audio_filename: str = "audio.wav",
    skip_tts: bool = False,
    conversation_history: Optional[list] = None,
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

    # Stage 1: Speech-to-Text
    if text_input:
        transcript = text_input
        timings["stt_ms"] = 0
    elif audio_bytes:
        t = time.perf_counter()
        try:
            transcript = stt.transcribe(audio_bytes, audio_filename)
        except RuntimeError as exc:
            return _error_response(str(exc), timings)
        timings["stt_ms"] = _ms(t)
    else:
        return _error_response("No audio or text input provided.", timings)

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

    if _is_inventory_stats_query(safe_transcript):
        return _inventory_stats_response(site_id, transcript, skip_tts, timings, t0)

    inventory_type = _extract_inventory_type_query(safe_transcript)
    if inventory_type:
        return _inventory_type_count_response(
            site_id, transcript, inventory_type, skip_tts, timings, t0
        )

    # Stage 3: RAG Retrieval
    t = time.perf_counter()
    profile = {}
    try:
        profile = get_user_profile(site_id)
        prefs = profile.get("preferences")
        rag_query = safe_transcript
        if prefs:
            rag_query = f"{safe_transcript} (User preferences: {prefs})"
            
        # Extract price constraints once, reuse for RAG filter + LLM prompt
        price_constraints = rag.extract_price_constraints(rag_query)
        retrieved_products = rag.retrieve(
            rag_query, site_id=site_id, price_constraints=price_constraints
        )
        
        # Dialogue context: fetch previously discussed products
        history_products = _extract_products_from_history(conversation_history or [], site_id)
        if history_products:
            # Merge lists, avoiding duplicates by product ID
            existing_ids = {str(p["id"]) for p in retrieved_products}
            for hp in history_products:
                if str(hp["id"]) not in existing_ids:
                    retrieved_products.append(hp)
                    existing_ids.add(str(hp["id"]))
        retrieved_products = _merge_products(
            retrieved_products,
            _exact_products_from_query(safe_transcript, site_id),
        )
    except Exception as exc:
        logger.error("PIPELINE | RAG failed: %s", exc)
        retrieved_products = []  # Degrade gracefully — LLM can still respond
        price_constraints = {}
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
    cart_context = format_cart_for_prompt(get_cart_items(site_id))

    if not profile:
        try:
            profile = get_user_profile(site_id)
        except Exception:
            profile = {}
    profile_context = f"Address: {profile.get('address') or 'None'} | Payment Method: {profile.get('payment_method') or 'None'} | Preferences: {profile.get('preferences') or 'None'}"

    llm_response = llm.generate_response(
        site_id,
        safe_transcript,
        retrieved_products,
        conversation_history=conversation_history or [],
        price_constraints=price_constraints,
        cart_context=cart_context,
        profile_context=profile_context,
    )

    if not retrieved_products and llm_response.get("intent") == "product_search":
        llm_response["ui_actions"] = []
        llm_response["intent"] = "out_of_stock"

    if llm_response.get("intent") == "out_of_stock":
        llm_response["ui_actions"] = []

    if llm_response.get("intent") == "error" and retrieved_products:
        logger.info(
            "PIPELINE | LLM failed, falling back to local FAISS search results."
        )
        llm_response = {
            "response_text": f"I had trouble processing that, but I found {len(retrieved_products)} products matching your search.",
            "intent": "search_fallback",
            "confidence": 1.0,
            "ui_actions": [
                {
                    "action": "SHOW_PRODUCTS",
                    "params": {"product_ids": [str(p["id"]) for p in retrieved_products]},
                }
            ],
        }
    
    for action in llm_response.get("ui_actions", []):
        if action.get("action") == "UPDATE_PREFERENCES":
            prefs = action.get("params", {}).get("preferences")
            if prefs:
                update_user_preferences(site_id, prefs)

    timings["llm_ms"] = _ms(t)

    # Stage 5: Output Guardrails
    t = time.perf_counter()
    try:
        allowed_product_ids = [p["id"] for p in retrieved_products]
        
        orig_actions = [
            a.get("action")
            for a in llm_response.get("ui_actions", [])
            if isinstance(a, dict)
        ]
        
        validated = guardrails.validate_output(llm_response, site_id, allowed_product_ids)

        # Check if the LLM hallucinated fake product IDs and they were all blocked
        val_actions = [a.get("action") for a in validated.get("ui_actions", [])]
        if "SHOW_PRODUCTS" in orig_actions and "SHOW_PRODUCTS" not in val_actions:
            logger.warning(
                "PIPELINE | Detected LLM hallucination: SHOW_PRODUCTS was completely blocked. Overriding response."
            )
            validated["intent"] = "out_of_stock"
            validated["ui_actions"] = []
            validated["response_text"] = (
                "I'm sorry, I couldn't find any products matching your request in our current inventory."
            )

    except OutputGuardrailError as exc:
        logger.error("PIPELINE | Output guardrail blocked response: %s", exc)
        validated = {
            "response_text": "Whoops! Looks like I got my shopping bags in a twist. How can I help you find what you need?",
            "intent": "blocked",
            "confidence": 1.0,
            "ui_actions": [],
        }
    _promote_comparison_action(validated, safe_transcript)
    _ensure_named_comparison_response(validated, safe_transcript, retrieved_products)
    _prevent_false_empty_inventory_claim(validated, safe_transcript, site_id)
    timings["guardrail_output_ms"] = _ms(t)

    print(f'🧠 LLM RESPONSE: "{validated["response_text"][:150]}"')
    print(
        f"   Intent: {validated.get('intent', '?')} | Confidence: {validated.get('confidence', '?')}"
    )
    print(f"   UI Actions: {validated.get('ui_actions', [])}")

    # Stage 6: Text-to-Speech
    audio_b64 = ""
    if not skip_tts:
        t = time.perf_counter()
        try:
            audio_b64 = tts.synthesize_b64(validated["response_text"])
        except RuntimeError as exc:
            logger.error("PIPELINE | TTS failed: %s — continuing without audio.", exc)
        timings["tts_ms"] = _ms(t)

    timings["total_ms"] = _ms(t0)
    logger.info("PIPELINE | Done in %.0fms", timings["total_ms"])
    print(
        f"🔊 TTS: {'Generated audio' if audio_b64 else 'No audio (failed or skipped)'}"
    )
    print(f"⏱️  Total: {timings['total_ms']:.0f}ms")
    print(f"{'=' * 60}\n")

    final_actions = validated.get("ui_actions", [])
    _ai_log("assistant", validated["response_text"])
    _ai_log("actions", final_actions)
    for a in final_actions:
        if a.get("action") == "ADD_TO_CART":
            pid = a.get("params", {}).get("product_id")
            if pid:
                with get_db(site_id) as conn:
                    res = conn.execute("SELECT variant_id FROM products WHERE id = %s", (pid,)).fetchone()
                    if res and res["variant_id"]:
                        a["params"]["variant_id"] = str(res["variant_id"])

    return {
        "transcript": transcript,
        "response_text": validated["response_text"],
        "intent": validated.get("intent", "unknown"),
        "confidence": validated.get("confidence", 0.0),
        "ui_actions": final_actions,
        "audio_b64": audio_b64,
        "latency_ms": timings,
    }


def run_stream(
    site_id: str,
    audio_bytes: Optional[bytes] = None,
    text_input: Optional[str] = None,
    audio_filename: str = "audio.wav",
    skip_tts: bool = False,
    conversation_history: Optional[list] = None,
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

    # Stage 1: STT
    t = time.perf_counter()
    if text_input:
        transcript = text_input
        timings["stt_ms"] = 0
    elif audio_bytes:
        try:
            transcript = stt.transcribe(audio_bytes, audio_filename)
        except RuntimeError as exc:
            yield {"event": "error", "data": {"error": str(exc)}}
            return
        timings["stt_ms"] = _ms(t)
    else:
        yield {"event": "error", "data": {"error": "No audio or text input provided."}}
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

        audio_b64 = ""
        if not skip_tts:
            tts_t = time.perf_counter()
            try:
                audio_b64 = tts.synthesize_b64(msg)
            except Exception:
                pass
            timings["tts_ms"] = _ms(tts_t)
        timings["total_ms"] = _ms(t0)
        yield {"event": "audio", "data": {"response_text": msg, "audio_b64": audio_b64}}
        yield {"event": "metrics", "data": {"latency_ms": timings}}
        return
    timings["guardrail_input_ms"] = _ms(t)

    if _is_simple_greeting(safe_transcript):
        result = _greeting_response(transcript, skip_tts, timings, t0)
        yield from _stream_final_result(result)
        return

    if _is_inventory_stats_query(safe_transcript):
        result = _inventory_stats_response(site_id, transcript, skip_tts, timings, t0)
        yield from _stream_final_result(result)
        return

    inventory_type = _extract_inventory_type_query(safe_transcript)
    if inventory_type:
        result = _inventory_type_count_response(
            site_id, transcript, inventory_type, skip_tts, timings, t0
        )
        yield from _stream_final_result(result)
        return

    # Stage 3: RAG
    t = time.perf_counter()
    try:
        profile = get_user_profile(site_id)
        prefs = profile.get("preferences")
        rag_query = safe_transcript
        if prefs:
            rag_query = f"{safe_transcript} (User preferences: {prefs})"
            
        price_constraints = rag.extract_price_constraints(rag_query)
        retrieved_products = rag.retrieve(
            rag_query, site_id=site_id, price_constraints=price_constraints
        )
        
        # Dialogue context: fetch previously discussed products
        history_products = _extract_products_from_history(conversation_history or [], site_id)
        if history_products:
            # Merge lists, avoiding duplicates by product ID
            existing_ids = {str(p["id"]) for p in retrieved_products}
            for hp in history_products:
                if str(hp["id"]) not in existing_ids:
                    retrieved_products.append(hp)
                    existing_ids.add(str(hp["id"]))
        retrieved_products = _merge_products(
            retrieved_products,
            _exact_products_from_query(safe_transcript, site_id),
        )
    except Exception as exc:
        logger.error("PIPELINE | RAG failed: %s", exc)
        retrieved_products = []
        price_constraints = {}
        profile = {}
    timings["rag_ms"] = _ms(t)

    # Stage 4: LLM
    t = time.perf_counter()
    if not profile:
        profile = get_user_profile(site_id)
    profile_context = f"Address: {profile.get('address') or 'None'} | Payment Method: {profile.get('payment_method') or 'None'} | Preferences: {profile.get('preferences') or 'None'}"
    
    cart_context = format_cart_for_prompt(get_cart_items(site_id))
    llm_response = llm.generate_response(
        site_id,
        safe_transcript,
        retrieved_products,
        conversation_history=conversation_history or [],
        price_constraints=price_constraints,
        cart_context=cart_context,
        profile_context=profile_context,
    )
    timings["llm_ms"] = _ms(t)

    # If the LLM tried to search for products but we found none, it shouldn't filter the UI
    # This prevents the 8B model from randomly filtering to "Groceries" when asked for "Snacks" (which we don't have)
    if not retrieved_products and llm_response.get("intent") == "product_search":
        llm_response["ui_actions"] = []
        llm_response["intent"] = "out_of_stock"

    if llm_response.get("intent") == "out_of_stock":
        llm_response["ui_actions"] = []

    if llm_response.get("intent") == "error" and retrieved_products:
        logger.info(
            "PIPELINE | LLM failed, falling back to local FAISS search results."
        )
        llm_response = {
            "response_text": f"I had trouble processing that, but I found {len(retrieved_products)} products matching your search.",
            "intent": "search_fallback",
            "confidence": 1.0,
            "ui_actions": [
                {
                    "action": "SHOW_PRODUCTS",
                    "params": {"product_ids": [str(p["id"]) for p in retrieved_products]},
                }
            ],
        }

    for action in llm_response.get("ui_actions", []):
        if action.get("action") == "UPDATE_PREFERENCES":
            prefs = action.get("params", {}).get("preferences")
            if prefs:
                update_user_preferences(site_id, prefs)

    # Stage 5: Output Guardrails
    t = time.perf_counter()
    try:
        allowed_product_ids = [p["id"] for p in retrieved_products]
        
        orig_actions = [
            a.get("action")
            for a in llm_response.get("ui_actions", [])
            if isinstance(a, dict)
        ]
        
        validated = guardrails.validate_output(llm_response, site_id, allowed_product_ids)

        # Check if the LLM hallucinated fake product IDs and they were all blocked
        val_actions = [a.get("action") for a in validated.get("ui_actions", [])]
        if "SHOW_PRODUCTS" in orig_actions and "SHOW_PRODUCTS" not in val_actions:
            logger.warning(
                "PIPELINE | Detected LLM hallucination: SHOW_PRODUCTS was completely blocked. Overriding response."
            )
            validated["intent"] = "out_of_stock"
            validated["ui_actions"] = []
            validated["response_text"] = (
                "I'm sorry, I couldn't find any products matching your request in our current inventory."
            )

    except OutputGuardrailError as exc:
        logger.error("PIPELINE | Output guardrail blocked response: %s", exc)
        validated = {
            "response_text": "I'm sorry, I can't respond to that. How can I help you shop?",
            "intent": "blocked",
            "confidence": 1.0,
            "ui_actions": [],
        }
    _promote_comparison_action(validated, safe_transcript)
    _ensure_named_comparison_response(validated, safe_transcript, retrieved_products)
    _prevent_false_empty_inventory_claim(validated, safe_transcript, site_id)
    timings["guardrail_output_ms"] = _ms(t)

    # Inject variant_id for ADD_TO_CART actions so the frontend can hit Shopify's native Cart API
    final_actions = validated.get("ui_actions", [])
    _ai_log("assistant", validated["response_text"])
    _ai_log("actions", final_actions)
    for a in final_actions:
        if a.get("action") == "ADD_TO_CART":
            pid = a.get("params", {}).get("product_id")
            if pid:
                with get_db(site_id) as conn:
                    res = conn.execute("SELECT variant_id FROM products WHERE id = %s", (pid,)).fetchone()
                    if res and res["variant_id"]:
                        a["params"]["variant_id"] = str(res["variant_id"])

    # Yield actions so UI can update immediately
    yield {"event": "actions", "data": {"ui_actions": final_actions}}
    yield {"event": "response", "data": {"response_text": validated["response_text"]}}

    # Stage 6: TTS
    audio_b64 = ""
    if not skip_tts:
        t = time.perf_counter()
        try:
            audio_b64 = tts.synthesize_b64(validated["response_text"])
        except RuntimeError as exc:
            logger.error("PIPELINE | TTS failed: %s — continuing without audio.", exc)

        timings["tts_ms"] = _ms(t)
    timings["total_ms"] = _ms(t0)

    # Yield audio
    yield {
        "event": "audio",
        "data": {
            "response_text": validated["response_text"],
            "audio_b64": audio_b64,
            "latency_ms": timings,
        },
    }
    yield {"event": "metrics", "data": {"latency_ms": timings}}


# Helpers


def _stream_final_result(result: dict[str, Any]) -> Generator[dict[str, Any], None, None]:
    ui_actions = result.get("ui_actions", [])
    response_text = result.get("response_text", "")
    latency_ms = result.get("latency_ms", {})
    yield {"event": "actions", "data": {"ui_actions": ui_actions}}
    yield {"event": "response", "data": {"response_text": response_text}}
    yield {
        "event": "audio",
        "data": {
            "response_text": response_text,
            "audio_b64": result.get("audio_b64", ""),
            "latency_ms": latency_ms,
        },
    }
    yield {"event": "metrics", "data": {"latency_ms": latency_ms}}


def _ms(since: float) -> float:
    return round((time.perf_counter() - since) * 1000, 1)


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
    except Exception as exc:
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
    if result:
        logger.info(
            "PIPELINE | Exact product name lookup added %d products: %s",
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
        if action.get("action") == "SHOW_PRODUCTS":
            product_ids = action.get("params", {}).get("product_ids", [])
            if isinstance(product_ids, list) and len(product_ids) >= 2:
                action["action"] = "SHOW_COMPARISON"
                action["params"] = {"product_ids": product_ids[:4]}
                response["intent"] = "product_compare"
                return


def _ensure_named_comparison_response(
    response: dict[str, Any],
    transcript: str,
    retrieved_products: list[dict],
) -> None:
    if not _wants_comparison(transcript):
        return
    if any(action.get("action") == "SHOW_COMPARISON" for action in response.get("ui_actions", [])):
        return

    exact_products = [p for p in retrieved_products if p.get("_exact_name_match")]
    if len(exact_products) < 2:
        return

    selected = exact_products[:4]
    product_ids = [str(product["id"]) for product in selected]
    response["intent"] = "product_compare"
    response["confidence"] = max(float(response.get("confidence") or 0.0), 0.9)
    response["ui_actions"] = [{"action": "SHOW_COMPARISON", "params": {"product_ids": product_ids}}]
    response["response_text"] = _comparison_fallback_text(selected)


def _prevent_false_empty_inventory_claim(response: dict[str, Any], transcript: str, site_id: str) -> None:
    text = str(response.get("response_text") or "")
    if not _claims_store_inventory_empty(text):
        return

    try:
        stats = tenant_inventory_summary(site_id)
        in_stock = int(stats.get("in_stock_products") or 0)
    except Exception:
        in_stock = 0

    if in_stock <= 0:
        return

    categories: list[str] = []
    try:
        categories = _available_category_names(get_all_products(site_id, limit=1000))
    except Exception:
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
    except Exception as exc:
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
                "action": "SHOW_PRODUCTS",
                "params": {
                    "product_ids": [str(product.get("id")) for product in matches[:8] if product.get("id")],
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
    except Exception as exc:
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
    audio_b64 = ""
    if not skip_tts:
        try:
            audio_b64 = tts.synthesize_b64(message)
        except Exception:
            pass
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
        except Exception as exc:
            logger.warning("PIPELINE | History tag product bulk lookup failed: %s", exc)

    # Then: name-match remaining products not already found via tag
    if not mentioned:
        try:
            products = get_all_products(site_id, limit=100)
        except Exception as exc:
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
