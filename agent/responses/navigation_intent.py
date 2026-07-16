import re
import time
from typing import Any, Callable
from agent.responses import navigation_routes
from agent.responses.sales_relevance import SCOPE_WEBSITE_ACTION
from api.contracts.models import ACTION_NAVIGATE_TO, ACTION_SORT_ENTITIES, ACTION_SORT_PRODUCTS

RecoverableErrors = tuple[type[BaseException], ...]

GENERIC_NAVIGATION_TERMS = navigation_routes.GENERIC_NAVIGATION_TERMS


def navigation_intent_response(
    site_id: str,
    transcript: str,
    safe_transcript: str,
    skip_tts: bool,
    timings: dict[str, float],
    start_time: float,
    page_context: dict[str, Any] | None,
    *,
    page_from_transcript: Callable[[str, str, dict[str, Any] | None], str],
    synthesize_b64: Callable[[str], str],
    ai_log: Callable[[str, Any], None],
    elapsed_ms: Callable[[float], float],
    logger: Any,
) -> dict[str, Any] | None:
    page = page_from_transcript(site_id, safe_transcript, page_context)
    if not page:
        return None

    label = navigation_response_label(page, safe_transcript)
    response_text = f"I'll try to open {label}."
    final_actions = [{"action": ACTION_NAVIGATE_TO, "params": {"page": page}}]
    ai_log("assistant", response_text)
    ai_log("actions", final_actions)

    audio_b64 = ""
    if not skip_tts:
        started_at = time.perf_counter()
        try:
            audio_b64 = synthesize_b64(response_text)
        except RuntimeError as exc:
            logger.error("PIPELINE | TTS failed for navigation: %s", exc)
        timings["tts_ms"] = elapsed_ms(started_at)

    timings["total_ms"] = elapsed_ms(start_time)
    return {
        "transcript": transcript,
        "response_text": response_text,
        "intent": "navigate",
        "confidence": 1.0,
        "answer_scope": SCOPE_WEBSITE_ACTION,
        "ui_actions": final_actions,
        "audio_b64": audio_b64,
        "latency_ms": timings,
    }


def sort_intent_response(
    site_id: str,
    transcript: str,
    safe_transcript: str,
    ecommerce_runtime: bool,
    skip_tts: bool,
    timings: dict[str, float],
    start_time: float,
    *,
    vertical_entity_plural: Callable[[str], str],
    synthesize_b64: Callable[[str], str],
    ai_log: Callable[[str, Any], None],
    elapsed_ms: Callable[[float], float],
    logger: Any,
) -> dict[str, Any] | None:
    sort_by = sort_key_from_transcript(safe_transcript)
    if not sort_by:
        return None

    action = ACTION_SORT_PRODUCTS if ecommerce_runtime else ACTION_SORT_ENTITIES
    subject = "products" if ecommerce_runtime else vertical_entity_plural(site_id)
    response_text = sort_response_text(subject, sort_by)
    final_actions = [{"action": action, "params": {"sort_by": sort_by}}]
    ai_log("assistant", response_text)
    ai_log("actions", final_actions)

    audio_b64 = ""
    if not skip_tts:
        started_at = time.perf_counter()
        try:
            audio_b64 = synthesize_b64(response_text)
        except RuntimeError as exc:
            logger.error("PIPELINE | TTS failed for sort action: %s", exc)
        timings["tts_ms"] = elapsed_ms(started_at)

    timings["total_ms"] = elapsed_ms(start_time)
    return {
        "transcript": transcript,
        "response_text": response_text,
        "intent": "sort",
        "confidence": 1.0,
        "ui_actions": final_actions,
        "audio_b64": audio_b64,
        "latency_ms": timings,
    }


def navigation_unavailable_text(
    site_id: str,
    transcript: str,
    page_context: dict[str, Any] | None = None,
    *,
    route_map: Callable[[str, dict[str, Any] | None], dict[str, str]],
) -> str:
    target = navigation_target_phrase(transcript)
    options = available_navigation_labels(site_id, page_context, route_map=route_map)
    if options:
        option_text = human_join(options[:6])
        return f"I could not find a {target} page or tab on this site. I can open {option_text}."
    return f"I could not find a {target} page or tab on this site from the controls I can see right now."


def navigation_response_label(page: str, transcript: str) -> str:
    target = navigation_target_phrase(transcript)
    if target != "matching" and len(target.split()) <= 4:
        return target
    label = str(page or "").split("?", 1)[0].split("#", 1)[0].strip("/")
    label = label.split("/")[-1] if label else ""
    return label.replace("-", " ").replace("_", " ").strip() or "that page"


def navigation_target_phrase(transcript: str) -> str:
    text = normalize_navigation_text(transcript)
    text = re.sub(r"\binsurances\b", "insurance", text)
    text = re.sub(
        r"\b(can|could|would|you|please|go|going|open|opening|navigate|navigating|take|taking|send|move|switch|switching|visit|show|showing|me|my|to|the|a|an|page|tab|section|screen|i|im|m|am|interested|interest|in|buying|buy|purchase|purchasing|want|wanted|wants|like|looking|trying|planning|for|get|see|view|explore|check)\b",
        " ",
        text,
    )
    text = re.sub(r"\s+", " ", text).strip()
    return text[:60] or "matching"


def available_navigation_labels(
    site_id: str,
    page_context: dict[str, Any] | None = None,
    *,
    route_map: Callable[[str, dict[str, Any] | None], dict[str, str]],
) -> list[str]:
    labels: list[str] = []
    for key, _path in route_map(site_id, page_context).items():
        if not key or "/" in key or key in {"nav", "navigate", "open", "show-entities", "capture-lead"}:
            continue
        label = key.replace("-", " ").strip().title()
        if label and label not in labels:
            labels.append(label)
    return labels


def human_join(items: list[str]) -> str:
    clean_items = [item for item in items if item]
    if not clean_items:
        return ""
    if len(clean_items) == 1:
        return clean_items[0]
    return f"{', '.join(clean_items[:-1])}, or {clean_items[-1]}"


def sort_key_from_transcript(transcript: str) -> str:
    text = normalize_navigation_text(transcript)
    if not looks_like_sort_request(text):
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


def looks_like_sort_request(text: str) -> bool:
    return bool(
        re.search(r"\b(sort|arrange|order|rank)\b", text)
        or re.search(r"\b(low to high|high to low|lowest first|highest first|cheapest|expensive|newest|latest|best rated)\b", text)
    )


def sort_response_text(subject: str, sort_by: str) -> str:
    labels = {
        "price_asc": "low to high",
        "price_desc": "high to low",
        "rating": "by rating",
        "newest": "newest first",
    }
    label = labels.get(sort_by, "low to high")
    return f"I'll try to sort visible {subject} {label}."


def navigation_page_from_transcript(
    site_id: str,
    transcript: str,
    page_context: dict[str, Any] | None = None,
    *,
    require_specific_match: bool = False,
    route_map: Callable[[str, dict[str, Any] | None], dict[str, str]],
    is_ecommerce_site: Callable[[str], bool],
    lead_flow_action_from_transcript: Callable[[str, str], str],
) -> str:
    text = normalize_navigation_text(transcript)
    route_terms = navigation_route_terms(site_id, page_context, route_map=route_map)
    if (
        not looks_like_navigation_request(text)
        and not looks_like_discovered_navigation_request(text, route_terms)
        and not looks_like_route_interest_request(text, route_terms)
    ):
        return ""
    if lead_flow_should_own_navigation_text(text, site_id, lead_flow_action_from_transcript=lead_flow_action_from_transcript):
        return ""
    if product_discovery_should_own_navigation_text(text, route_terms):
        return ""

    matches = [(term, page) for term, page in route_terms if navigation_term_matches(text, term)]
    if require_specific_match:
        matches = [match for match in matches if navigation_match_rank(match[0])[0] > 0]
    if not matches:
        return ""
    matches.sort(key=lambda item: navigation_match_rank(item[0]), reverse=True)
    return matches[0][1]


def lead_flow_should_own_navigation_text(
    text: str,
    site_id: str,
    *,
    lead_flow_action_from_transcript: Callable[[str, str], str],
) -> bool:
    if not lead_flow_action_from_transcript(text, site_id):
        return False
    if re.search(r"\b(page|tab|section|screen)\b", text):
        return False
    return not re.search(r"\b(go|going|open|opening|navigate|navigating|take|taking|send|move|switch|switching|visit)\b", text)


def looks_like_navigation_request(text: str) -> bool:
    return bool(
        re.search(
            r"\b("
            r"go|going|open|opening|navigate|navigating|take|taking|send|move|switch|switching|visit|show|showing"
            r")\b.{0,24}\b("
            r"page|tab|section|screen|home|plans?|claims?|polic(?:y|ies)|renewal|quote|contact|about|cart|checkout|shop"
            r")\b",
            text,
        )
        or re.search(r"\b(back|return)\b.{0,16}\b(home|main|start)\b", text)
    )


def product_discovery_should_own_navigation_text(
    text: str,
    route_terms: list[tuple[str, str]] | None = None,
) -> bool:
    """Keep product discovery/detail language in the sales pipeline."""
    mentions_navigation_container = bool(re.search(r"\b(page|tab|section|screen)\b", text))
    rejects_navigation_container = bool(
        re.search(r"\b(?:rather than|not)\b.{0,20}\b(page|tab|section|screen)\b", text)
    )
    if mentions_navigation_container and not rejects_navigation_container:
        return False
    if re.search(r"\bbrowse\b.{0,20}\b(myself|catalog|shop|store)\b", text):
        return False
    if re.search(r"\b(add|choose|pick|buy|purchase)\b", text):
        return True
    asks_for_results = bool(re.search(r"\b(show|find|recommend|suggest|compare)\b", text))
    navigation_only_subject = bool(
        re.search(
            r"\b(returns?|shipping|delivery|contact|about|home|cart|checkout|orders?|"
            r"information|policy|help|support)\b",
            text,
        )
    )
    if asks_for_results and not navigation_only_subject:
        return True
    has_specific_route = any(
        navigation_term_matches(text, term) and navigation_match_rank(term)[0] > 0
        for term, _page in route_terms or []
    )
    if asks_for_results and not has_specific_route:
        return True
    return bool(
        re.search(
            r"\b(show|find|recommend|suggest|compare|open|view|see)\b.{0,90}"
            r"\b(products?|items?|options?|details?|shortlisted|cheaper|cheapest|rated|reviews?|something)\b",
            text,
        )
    )


def looks_like_discovered_navigation_request(text: str, route_terms: list[tuple[str, str]]) -> bool:
    if not re.search(r"\b(go|going|open|opening|navigate|navigating|take|taking|send|move|switch|switching|visit|show|showing)\b", text):
        return False
    return any(navigation_term_matches(text, term) for term, _page in route_terms)


def looks_like_route_interest_request(text: str, route_terms: list[tuple[str, str]]) -> bool:
    if not any(navigation_term_matches(text, term) for term, _page in route_terms):
        return False
    return bool(
        re.search(
            r"\b(interested|interest|want|wanted|wants|would like|looking to|planning to|trying to)\b"
            r".{0,50}\b(buy|buying|purchase|purchasing|get|see|view|open|explore|check)\b",
            text,
        )
        or re.search(
            r"\b(buy|buying|purchase|purchasing|explore|view|check out)\b.{0,50}\b(plans?|polic(?:y|ies)|packages?|services?|products?|options?)\b",
            text,
        )
    )


navigation_route_terms = navigation_routes.navigation_route_terms
navigation_match_rank = navigation_routes.navigation_match_rank
client_navigation_route_map = navigation_routes.client_navigation_route_map
navigation_route_map_from_config = navigation_routes.navigation_route_map_from_config
add_navigation_route = navigation_routes.add_navigation_route
observed_navigation_path = navigation_routes.observed_navigation_path
same_origin_path = navigation_routes.same_origin_path
safe_config_list = navigation_routes.safe_config_list
route_page_key = navigation_routes.route_page_key
route_last_segment = navigation_routes.route_last_segment
safe_page_key = navigation_routes.safe_page_key
navigation_term_matches = navigation_routes.navigation_term_matches
normalize_navigation_text = navigation_routes.normalize_navigation_text
