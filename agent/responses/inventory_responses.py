import re
import time
from typing import Any, Callable

from api.contracts.models import ACTION_SHOW_PRODUCTS, PRODUCT_IDS_PARAM

RecoverableErrors = tuple[type[BaseException], ...]


# Browse/search phrasings ("I'm looking for X", "I want to buy X"). These are a
# product *search* intent, not an inventory *count* question, so the response
# must say "matching products" rather than pluralizing the search term.
_BROWSE_PHRASE_RE = re.compile(
    r"\bi(?:\s*am|'m|\s*m)?\s+(?:interested\s+in|looking\s+for|planning\s+on|shopping\s+for|browsing\s+for|searching\s+for)\b"
    r"|\bi\s+(?:want|would\s+like|need|wanna)\s+to\s+(?:buy|get|purchase|order|find)\b"
    r"|\bi\s+(?:want|need)\s+(?:a|an|some)\b",
    re.IGNORECASE,
)


def is_browse_search_phrase(transcript: str) -> bool:
    """True when the turn is a product-browse phrasing rather than a count question."""
    return bool(_BROWSE_PHRASE_RE.search((transcript or "").lower()))


def _term_matches_a_brand(term: str, products: list[dict[str, Any]]) -> bool:
    """True when the searched term is itself a catalog brand (e.g. "apple").

    A brand must never be pluralized into a product type ("apples"); when the
    term is a brand the count wording falls back to "matching products".
    """
    normalized = (term or "").strip().lower()
    if not normalized:
        return False
    return any(
        normalized == str(product.get("brand") or product.get("vendor") or "").strip().lower()
        for product in products
    )


def is_inventory_stats_query(transcript: str) -> bool:
    text = (transcript or "").lower()
    if re.search(r"\b(review|rating|result|page|cart|order)\s+count\b", text):
        return False
    return bool(
        re.search(r"\bhow many\b.{0,45}\b(products?|items?|stock|inventory|catalog(?:ue)?)\b", text)
        or re.search(r"\b(count|total|number)\s+(?:of\s+)?\b(products?|items?)\b", text)
        or re.search(r"\b(inventory|catalog(?:ue)?)\b.{0,30}\b(count|total|how many)\b", text)
    )


def extract_inventory_type_query(transcript: str) -> str | None:
    text = re.sub(r"[^a-z0-9\s-]", " ", (transcript or "").lower())
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return None
    if re.search(r"\b(which of|those|these|them|compared|shortlisted)\b", text):
        return None

    patterns = [
        r"\bhow many (?:types|kinds|options|varieties) of ([a-z0-9\s-]+?)(?: do you have| are available| available| in stock| right now|$)",
        r"\bhow many ([a-z0-9\s-]+?)(?: do you have| are available| available| in stock| right now|$)",
        r"\bdo you have (?:any )?([a-z0-9\s-]+?)(?: available| in stock| right now|$)",
        r"\b(?:are there|have you got|do you (?:sell|carry|stock)) (?:any |a |an |some )?([a-z0-9\s-]+?)(?: available| in stock| right now|$)",
        r"\bis (?:a |an |the )?([a-z0-9\s-]+?) (?:available|in stock)(?: right now)?$",
        r"\bi(?: am| m)? (?:interested in|looking for|planning on) (?:buying |getting |purchasing )?(?:a |an |some )?([a-z0-9\s-]+?)(?: for | with | under | below | around |$)",
        r"\bi (?:want|would like|need) to (?:buy|get|purchase|order) (?:a |an |some )?([a-z0-9\s-]+?)(?: for | with | under | below | around |$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        term = clean_inventory_type_term(match.group(1))
        if term:
            return term
    return None


def clean_inventory_type_term(raw: str) -> str:
    term = re.sub(
        r"\b(a|an|some|additional|another|different|else|more|other|products?|items?|types?|kinds?|options?|varieties|stock|inventory|catalog|catalogue)\b",
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
        elif word.endswith(("ches", "shes", "sses", "xes", "zes")) and len(word) > 5:
            # "smartwatches" -> "smartwatch", "watches" -> "watch", "boxes" -> "box".
            normalized_words.append(word[:-2])
        elif word.endswith("s") and not word.endswith("ss") and len(word) > 3:
            normalized_words.append(word[:-1])
        else:
            normalized_words.append(word)
    return " ".join(normalized_words)


def greeting_response(
    transcript: str,
    skip_tts: bool,
    timings: dict[str, float],
    start_time: float,
    *,
    synthesize_b64: Callable[[str], str],
    ai_log: Callable[[str, Any], None],
    elapsed_ms: Callable[[float], float],
    logger: Any,
) -> dict[str, Any]:
    response_text = "Hi, I am ready to help. Tell me what you want to find today."
    ai_log("assistant", response_text)
    ai_log("actions", [])

    audio_b64 = ""
    if not skip_tts:
        started_at = time.perf_counter()
        try:
            audio_b64 = synthesize_b64(response_text)
        except RuntimeError as exc:
            logger.error("PIPELINE | TTS failed for greeting: %s", exc)
        timings["tts_ms"] = elapsed_ms(started_at)

    timings["total_ms"] = elapsed_ms(start_time)
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


def inventory_type_count_response(
    site_id: str,
    transcript: str,
    item_type: str,
    skip_tts: bool,
    timings: dict[str, float],
    start_time: float,
    *,
    load_products: Callable[[str, int], list[dict[str, Any]]],
    matching_products: Callable[[list[dict[str, Any]], str], list[dict[str, Any]]],
    available_categories: Callable[[list[dict[str, Any]]], list[str]],
    synthesize_b64: Callable[[str], str],
    ai_log: Callable[[str, Any], None],
    elapsed_ms: Callable[[float], float],
    recoverable_errors: RecoverableErrors,
    logger: Any,
) -> dict[str, Any]:
    started_at = time.perf_counter()
    try:
        products = load_products(site_id, 1000)
    except recoverable_errors as exc:
        logger.error("Inventory type lookup failed: %s", exc)
        products = []
    timings["inventory_lookup_ms"] = elapsed_ms(started_at)

    matches = matching_products(products, item_type)
    # A browse phrasing ("looking for X") is a product search; a "how many / do
    # you have" phrasing is an inventory count. A term that is itself a brand is
    # never pluralized into a product type. Both cases render "matching products".
    is_browse = is_browse_search_phrase(transcript)
    term_is_brand = _term_matches_a_brand(item_type, matches or products)
    use_product_wording = is_browse or term_is_brand
    intent = "product_search" if is_browse else "inventory_status"
    final_actions: list[dict[str, Any]] = []

    if matches:
        count = len(matches)
        names = [str(product.get("name") or product.get("title") or "").strip() for product in matches[:3]]
        shown_names = ", ".join(name for name in names if name)
        if use_product_wording:
            product_noun = "product" if count == 1 else "products"
            response_text = f"I found {count} matching {product_noun}"
        else:
            response_text = f"I found {count} {pluralize(item_type, count)} in stock"
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
        missing_text = (
            f"I don't have any {item_type} products right now."
            if use_product_wording
            else f"I don't have {item_type}s right now."
        )
        categories = available_categories(products)
        if categories:
            response_text = f"{missing_text} I do have categories like {', '.join(categories[:5])}."
        else:
            response_text = missing_text

    ai_log("assistant", response_text)
    ai_log("actions", final_actions)

    audio_b64 = ""
    if not skip_tts:
        started_at = time.perf_counter()
        try:
            audio_b64 = synthesize_b64(response_text)
        except RuntimeError as exc:
            logger.error("PIPELINE | TTS failed for inventory type count: %s", exc)
        timings["tts_ms"] = elapsed_ms(started_at)

    timings["total_ms"] = elapsed_ms(start_time)
    return {
        "transcript": transcript,
        "response_text": response_text,
        "intent": intent,
        "confidence": 1.0,
        "ui_actions": final_actions,
        "audio_b64": audio_b64,
        "latency_ms": timings,
    }


def pluralize(term: str, count: int) -> str:
    if count == 1:
        return term
    if term.endswith("y"):
        return f"{term[:-1]}ies"
    if term.endswith("s"):
        return term
    return f"{term}s"


def inventory_stats_response(
    site_id: str,
    transcript: str,
    skip_tts: bool,
    timings: dict[str, float],
    start_time: float,
    *,
    inventory_summary: Callable[[str], dict[str, Any]],
    synthesize_b64: Callable[[str], str],
    elapsed_ms: Callable[[float], float],
    recoverable_errors: RecoverableErrors,
    logger: Any,
) -> dict[str, Any]:
    try:
        stats = inventory_summary(site_id)
        logger.info("Inventory stats requested; internal counts hidden from customer: %s", stats)
    except recoverable_errors as exc:
        logger.error("Inventory stats lookup failed: %s", exc)
    response_text = (
        "I have plenty of products available to browse. "
        "Tell me what you are looking for, and I will find the best options for you."
    )

    audio_b64 = ""
    if not skip_tts:
        started_at = time.perf_counter()
        try:
            audio_b64 = synthesize_b64(response_text)
        except RuntimeError as exc:
            logger.error("PIPELINE | TTS failed for inventory stats: %s", exc)
        timings["tts_ms"] = elapsed_ms(started_at)

    timings["total_ms"] = elapsed_ms(start_time)
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
