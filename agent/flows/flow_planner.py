"""Universal transaction-flow planner for Maya.

The planner stays domain-neutral: it looks at the user's intent, retrieved
website records, and the site's discovered action contract. It does not encode
client websites or vertical-specific pages.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from agent.actions.registry import get_action
from agent.flows.flow_planner_text import normalize_text, ordinal_index
from agent.products.product_response import ProductCatalogFormatter
from agent.responses.cart_responses import cart_target_product
from db.client_domain.client_facade import get_client_detail


FLOW_STATE_COLLECT_TARGET = "collect_target"
FLOW_STATE_READY = "ready"
FLOW_STATE_HANDOFF = "handoff"

COMMERCE_ITEM_ACTIONS = ("ADD_TO_CART",)
CHECKOUT_ACTIONS = ("CHECKOUT", "CHECKOUT_HANDOFF")
DETAIL_ACTIONS = ("OPEN_ENTITY_DETAIL", "SHOW_PRODUCT_DETAIL")
CONTACT_ACTIONS = (
    "REQUEST_CALLBACK",
    "CONTACT_AGENT",
    "CAPTURE_LEAD",
    "OPEN_CONTACT",
    "HANDOFF_TO_HUMAN",
    "HANDOFF_TO_AGENT",
    "HANDOFF_TO_ADVISOR",
    "HANDOFF_TO_LICENSED_AGENT",
)
QUOTE_ACTIONS = ("START_QUOTE", "REQUEST_ESTIMATE", "RUN_CALCULATOR")
BOOKING_ACTIONS = (
    "START_BOOKING",
    "REQUEST_APPOINTMENT",
    "BOOK_APPOINTMENT_REQUEST",
    "REQUEST_CONSULTATION",
    "REQUEST_SITE_VISIT",
    "REQUEST_VIEWING",
)
APPLICATION_ACTIONS = ("START_APPLICATION", "START_ENROLLMENT", "START_INTAKE")
PURCHASE_FLOW_ACTIONS = ("START_TICKET_PURCHASE", "START_BOOKING", "START_QUOTE", "REQUEST_ESTIMATE")

GENERIC_WORDS = {
    "a",
    "about",
    "add",
    "an",
    "and",
    "apply",
    "book",
    "buy",
    "cart",
    "checkout",
    "compare",
    "contact",
    "for",
    "get",
    "help",
    "i",
    "in",
    "looking",
    "me",
    "my",
    "need",
    "now",
    "open",
    "plan",
    "please",
    "purchase",
    "quote",
    "reserve",
    "show",
    "start",
    "the",
    "this",
    "to",
    "want",
    "with",
}

PRODUCT_FORMATTER = ProductCatalogFormatter()


@dataclass(frozen=True)
class FlowPlan:
    response_text: str
    intent: str
    confidence: float
    ui_actions: list[dict[str, Any]]
    flow_state: str

    def to_response(self) -> dict[str, Any]:
        return {
            "response_text": self.response_text,
            "intent": self.intent,
            "confidence": self.confidence,
            "ui_actions": self.ui_actions,
            "flow_state": self.flow_state,
        }


def plan_universal_flow(
    *,
    site_id: str,
    transcript: str,
    retrieved_items: list[dict[str, Any]],
    ecommerce_runtime: bool,
) -> dict[str, Any] | None:
    """Plan the next safe transactional action, if the turn is transactional."""
    text = _normalize_text(transcript)
    if not text:
        return None

    action_contract = _site_action_contract(site_id)
    allowed_actions = set(action_contract)
    intent = _flow_intent(text, ecommerce_runtime)
    if not intent:
        return None

    target = _resolved_target(text, retrieved_items)
    if intent in {"add_to_cart", "buy"} and ecommerce_runtime:
        target = target or cart_target_product(text, retrieved_items, PRODUCT_FORMATTER)
        return _commerce_plan(intent, text, target, retrieved_items, allowed_actions)

    if intent == "checkout":
        return _first_action_plan(
            intent="checkout",
            action_names=CHECKOUT_ACTIONS,
            allowed_actions=allowed_actions,
            action_contract=action_contract,
            response_text="I'll try to open the checkout step.",
            fallback_text="Checkout is not mapped safely on this website yet.",
        )

    if intent == "contact":
        return _first_action_plan(
            intent="contact",
            action_names=CONTACT_ACTIONS,
            allowed_actions=allowed_actions,
            action_contract=action_contract,
            response_text="I'll try to open the best contact option for this request.",
            fallback_text="I could not find a safe contact action mapped for this website yet.",
        )

    flow_actions = _candidate_actions_for_intent(intent)
    if target and "OPEN_ENTITY_DETAIL" in allowed_actions and intent == "buy":
        flow_actions = (*PURCHASE_FLOW_ACTIONS, "OPEN_ENTITY_DETAIL")

    plan = _best_contract_action_plan(
        intent=intent,
        text=text,
        action_names=flow_actions,
        allowed_actions=allowed_actions,
        action_contract=action_contract,
        target=target,
    )
    if plan:
        return plan.to_response()

    if target and any(action in allowed_actions for action in DETAIL_ACTIONS):
        action = "SHOW_PRODUCT_DETAIL" if ecommerce_runtime and "SHOW_PRODUCT_DETAIL" in allowed_actions else "OPEN_ENTITY_DETAIL"
        id_key = "product_id" if action == "SHOW_PRODUCT_DETAIL" else "entity_id"
        return FlowPlan(
            response_text=f"I'll try to open details for {_item_title(target)}.",
            intent=intent,
            confidence=0.84,
            ui_actions=[{"action": action, "params": {id_key: str(target.get("id"))}}],
            flow_state=FLOW_STATE_READY,
        ).to_response()

    return None


def _commerce_plan(
    intent: str,
    text: str,
    target: dict[str, Any] | None,
    retrieved_items: list[dict[str, Any]],
    allowed_actions: set[str],
) -> dict[str, Any] | None:
    if not any(action in allowed_actions for action in COMMERCE_ITEM_ACTIONS):
        return None
    if not target:
        if intent == "buy":
            return None
        candidates = [_item_title(item) for item in retrieved_items[:3] if item.get("id")]
        if len(candidates) >= 2:
            names = ", ".join(candidates[:3])
            return FlowPlan(
                response_text=f"Which one should I add: {names}?",
                intent=intent,
                confidence=0.88,
                ui_actions=[],
                flow_state=FLOW_STATE_COLLECT_TARGET,
            ).to_response()
        return None
    return FlowPlan(
        response_text=f"I'll try to add {_item_title(target)} to your cart now.",
        intent="add_to_cart",
        confidence=0.92,
        ui_actions=[{"action": "ADD_TO_CART", "params": {"product_id": str(target.get("id"))}}],
        flow_state=FLOW_STATE_READY,
    ).to_response()


def _first_action_plan(
    *,
    intent: str,
    action_names: tuple[str, ...],
    allowed_actions: set[str],
    action_contract: dict[str, dict[str, Any]],
    response_text: str,
    fallback_text: str,
) -> dict[str, Any] | None:
    for action_name in action_names:
        if action_name in allowed_actions:
            return FlowPlan(
                response_text=response_text,
                intent=intent,
                confidence=0.88,
                ui_actions=[{"action": action_name, "params": {}}],
                flow_state=FLOW_STATE_HANDOFF if action_name.startswith("HANDOFF_") else FLOW_STATE_READY,
            ).to_response()
    if any(action_name in action_contract for action_name in action_names):
        return FlowPlan(
            response_text=fallback_text,
            intent=intent,
            confidence=0.72,
            ui_actions=[],
            flow_state=FLOW_STATE_HANDOFF,
        ).to_response()
    return None


def _best_contract_action_plan(
    *,
    intent: str,
    text: str,
    action_names: tuple[str, ...],
    allowed_actions: set[str],
    action_contract: dict[str, dict[str, Any]],
    target: dict[str, Any] | None,
) -> FlowPlan | None:
    scored: list[tuple[int, str]] = []
    for action_name in action_names:
        if action_name not in allowed_actions:
            continue
        score = _contract_score(text, action_name, action_contract.get(action_name) or {})
        if action_name in _preferred_actions_for_intent(intent):
            score += 3
        if score > 0:
            scored.append((score, action_name))
    if not scored:
        return None
    scored.sort(key=lambda row: (-row[0], row[1]))
    action_name = scored[0][1]
    params: dict[str, Any] = {}
    if target and action_name == "OPEN_ENTITY_DETAIL":
        params["entity_id"] = str(target.get("id"))
    return FlowPlan(
        response_text=_planned_action_text(intent, action_name, target),
        intent=intent,
        confidence=0.9,
        ui_actions=[{"action": action_name, "params": params}],
        flow_state=FLOW_STATE_READY,
    )


def _flow_intent(text: str, ecommerce_runtime: bool) -> str:
    if _is_navigation_request(text):
        return ""
    if _is_buying_guidance_question(text):
        return ""
    if re.search(r"\b(add|put|place)\b.{0,40}\b(cart|basket|bag|tray)\b", text):
        return "add_to_cart"
    if re.search(r"\b(checkout|check out|cart|basket|bag)\b", text):
        return "checkout"
    if re.search(r"\b(call me|callback|call back|contact|talk to|agent|advisor|sales)\b", text):
        return "contact"
    if re.search(r"\b(quote|estimate|premium|rate|calculator|calculate)\b", text):
        return "quote"
    if re.search(r"\b(book|booking|reserve|reservation|appointment|schedule|visit|viewing)\b", text):
        return "book"
    if re.search(r"\b(apply|application|enroll|enrol|register|intake)\b", text):
        return "apply"
    if re.search(r"\b(buy|purchase|order|take this|get this|i want this)\b", text):
        return "buy"
    return ""


def _is_navigation_request(text: str) -> bool:
    """Keep page/tab requests out of transactional flow planning."""
    has_navigation_verb = re.search(r"\b(open|go|goto|navigate|visit|take me|show me|see|view|switch)\b", text)
    has_page_target = re.search(
        r"\b(page|tab|section|faq|support|contact|about|policy|policies|terms|privacy|home|plans?|claims?|renewals?)\b",
        text,
    )
    if has_navigation_verb and has_page_target:
        return True
    return bool(re.search(r"\b(i need|i want)\s+to\s+(see|view|open|visit|go to)\b", text))


def _is_buying_guidance_question(text: str) -> bool:
    """Keep advisory product questions out of transaction execution."""
    return bool(
        re.search(r"\b(why|should|which|what|how)\b.{0,40}\b(buy|purchase|choose|pick|select|get)\b", text)
        or re.search(r"\b(buy|purchase|choose|pick|select|get)\b.{0,40}\b(why|should|which|what|how)\b", text)
        or re.search(r"\b(recommend|suggest|advice|advise|options|something)\b", text)
    )


def _candidate_actions_for_intent(intent: str) -> tuple[str, ...]:
    if intent == "quote":
        return QUOTE_ACTIONS
    if intent == "book":
        return BOOKING_ACTIONS
    if intent == "apply":
        return APPLICATION_ACTIONS
    if intent == "buy":
        return PURCHASE_FLOW_ACTIONS
    return ()


def _preferred_actions_for_intent(intent: str) -> set[str]:
    if intent == "quote":
        return {"START_QUOTE", "REQUEST_ESTIMATE"}
    if intent == "book":
        return {"START_BOOKING", "REQUEST_APPOINTMENT", "BOOK_APPOINTMENT_REQUEST"}
    if intent == "apply":
        return {"START_APPLICATION", "START_ENROLLMENT"}
    if intent == "buy":
        return {"START_TICKET_PURCHASE", "START_BOOKING"}
    return set()


def _planned_action_text(intent: str, action_name: str, target: dict[str, Any] | None) -> str:
    if target and action_name in DETAIL_ACTIONS:
        return f"I'll try to open details for {_item_title(target)}."
    labels = {
        "quote": "I'll try to start the quote flow.",
        "book": "I'll try to start the booking or appointment flow.",
        "apply": "I'll try to start the application flow.",
        "buy": "I'll try to start the purchase flow.",
    }
    return labels.get(intent, "I'll try to start that website flow.")


def _site_action_contract(site_id: str) -> dict[str, dict[str, Any]]:
    try:
        from agent.action_helpers.capabilities import get_allowed_actions

        allowed_actions = set(get_allowed_actions(site_id))
    except Exception:
        allowed_actions = set()

    try:
        client = get_client_detail(site_id)
    except Exception:
        return {}
    vertical_config = client.get("vertical_config") if isinstance(client, dict) else {}
    raw_actions = vertical_config.get("actions") if isinstance(vertical_config, dict) else {}
    if not isinstance(raw_actions, dict):
        raw_actions = {}
    contract: dict[str, dict[str, Any]] = {}
    for action_name, config in raw_actions.items():
        clean_name = str(action_name or "").strip().upper()
        if not clean_name or not get_action(clean_name):
            continue
        if allowed_actions and clean_name not in allowed_actions:
            continue
        contract[clean_name] = config if isinstance(config, dict) else {}
    if allowed_actions:
        for action_name in allowed_actions:
            if get_action(action_name):
                contract.setdefault(action_name, {})
    return contract


def _contract_score(text: str, action_name: str, action_config: dict[str, Any]) -> int:
    terms = _contract_terms(action_name, action_config)
    score = 0
    for term in terms:
        if not term:
            continue
        if re.search(rf"\b{re.escape(term)}\b", text):
            score += 2 if " " in term else 1
    return score


def _contract_terms(action_name: str, action_config: dict[str, Any]) -> set[str]:
    raw_values = [action_name.replace("_", " ")]
    for key in ("label", "title", "button_label", "form_label", "path", "page", "page_path", "selector"):
        value = action_config.get(key)
        if value:
            raw_values.append(str(value))
    for field in _field_schema_values(action_config):
        raw_values.append(field)
    terms: set[str] = set()
    for raw_value in raw_values:
        normalized = _normalize_text(raw_value)
        if len(normalized) >= 4:
            terms.add(normalized)
        for word in normalized.split():
            if len(word) >= 4 and word not in GENERIC_WORDS:
                terms.add(word)
    return terms


def _field_schema_values(action_config: dict[str, Any]) -> list[str]:
    values: list[str] = []
    field_schema = action_config.get("field_schema")
    if isinstance(field_schema, list):
        for field in field_schema:
            if not isinstance(field, dict):
                continue
            for key in ("param", "label", "placeholder", "type"):
                value = field.get(key)
                if value:
                    values.append(str(value))
    for key in ("fields", "required_fields"):
        raw_values = action_config.get(key)
        if isinstance(raw_values, list):
            values.extend(str(value) for value in raw_values if value)
    return values


def _resolved_target(text: str, retrieved_items: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [item for item in retrieved_items if item.get("id") is not None]
    if not candidates:
        return None
    ordinal = _ordinal_index(text)
    if ordinal is not None and ordinal < len(candidates):
        return candidates[ordinal]

    scored: list[tuple[int, dict[str, Any]]] = []
    query_terms = {word for word in text.split() if len(word) >= 3 and word not in GENERIC_WORDS}
    for item in candidates:
        title = _normalize_text(_item_title(item))
        if not title:
            continue
        score = 0
        if re.search(rf"\b{re.escape(title)}\b", text):
            score += 10
        title_terms = {word for word in title.split() if len(word) >= 3 and word not in GENERIC_WORDS}
        score += len(query_terms & title_terms) * 2
        score += _attribute_overlap_score(query_terms, item)
        if score:
            scored.append((score, item))
    if not scored:
        return candidates[0] if len(candidates) == 1 else None
    scored.sort(key=lambda row: row[0], reverse=True)
    if len(scored) > 1 and scored[0][0] == scored[1][0] and scored[0][0] < 8:
        return None
    return scored[0][1]


def _attribute_overlap_score(query_terms: set[str], item: dict[str, Any]) -> int:
    values = [
        item.get("brand"),
        item.get("category"),
        item.get("category_name"),
        item.get("entity_type"),
        item.get("subtitle"),
        item.get("summary"),
    ]
    attributes = item.get("attributes") if isinstance(item.get("attributes"), dict) else {}
    values.extend(str(value) for value in attributes.values() if value)
    text = _normalize_text(" ".join(str(value or "") for value in values))
    item_terms = {word for word in text.split() if len(word) >= 3 and word not in GENERIC_WORDS}
    return len(query_terms & item_terms)


def _ordinal_index(text: str) -> int | None:
    return ordinal_index(text)


def _item_title(item: dict[str, Any]) -> str:
    return str(item.get("name") or item.get("title") or item.get("label") or "that option").strip()


def _normalize_text(value: Any) -> str:
    return normalize_text(value)
