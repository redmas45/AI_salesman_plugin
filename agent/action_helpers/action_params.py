"""Natural-language parameter extraction for runtime actions."""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

from agent.products.product_response import (
    normalize_lookup_text,
    phrase_in_text,
)


def action_param_context_text(transcript: str, conversation_history: list) -> str:
    parts: list[str] = []
    for turn in conversation_history or []:
        if not isinstance(turn, dict):
            continue
        content = turn.get("content") or turn.get("text") or turn.get("message")
        if content:
            parts.append(str(content))
    if transcript:
        parts.append(str(transcript))
    return "\n".join(parts)


def action_param_facts_from_text(
    text: str,
    *,
    action_config: dict[str, Any],
) -> dict[str, str]:
    facts: dict[str, str] = {}
    for spec in action_param_specs(action_config):
        param = spec.get("param", "")
        if not param or should_skip_auto_param(param):
            continue
        value = extract_value_for_action_param(text, spec)
        if value:
            facts[param] = value
    return facts


def action_param_specs(action_config: dict[str, Any]) -> list[dict[str, Any]]:
    specs: dict[str, dict[str, Any]] = {}

    field_schema = action_config.get("field_schema")
    if isinstance(field_schema, list):
        for item in field_schema:
            if not isinstance(item, dict):
                continue
            param = str(item.get("param") or "").strip()
            if not param:
                continue
            specs[param] = {
                "param": param,
                "label": str(item.get("label") or param).strip(),
                "type": str(item.get("type") or "").strip().lower(),
                "options": item.get("options") if isinstance(item.get("options"), list) else [],
                "required": bool(item.get("required") is True),
            }

    for param in action_config_param_names(action_config):
        specs.setdefault(
            param,
            {
                "param": param,
                "label": param.replace("_", " ").replace("-", " "),
                "type": "",
                "options": [],
                "required": param in set(clean_string_list(action_config.get("required_fields"))),
            },
        )
    return list(specs.values())


def action_config_param_names(action_config: dict[str, Any]) -> list[str]:
    params: list[str] = [
        *clean_string_list(action_config.get("required_fields")),
        *clean_string_list(action_config.get("fields")),
    ]
    steps = action_config.get("steps")
    if isinstance(steps, list):
        for step in steps:
            if not isinstance(step, dict):
                continue
            param = str(step.get("param") or step.get("parameter") or step.get("name") or "").strip()
            if param:
                params.append(param)
    unique: list[str] = []
    seen: set[str] = set()
    for param in params:
        key = normalized_action_param_key(param)
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(param)
    return unique


def clean_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item or "").strip() for item in value if str(item or "").strip()]


def should_skip_auto_param(param: str) -> bool:
    text = normalize_lookup_text(param)
    blocked_terms = {"otp", "password", "passcode", "card", "cvv", "captcha", "file", "upload", "document"}
    return any(term in text.split() or term in text for term in blocked_terms)


def extract_value_for_action_param(text: str, spec: dict[str, Any]) -> str:
    option_value = extract_option_value(text, spec)
    if option_value:
        return option_value

    param = str(spec.get("param") or "")
    label = str(spec.get("label") or "")
    param_text = normalize_lookup_text(f"{param} {label}")
    aliases = param_aliases(param, label)

    labeled = extract_labeled_param_value(text, aliases)
    if labeled:
        return labeled

    field_type = str(spec.get("type") or "").lower()
    if field_type in {"date", "datetime", "datetime-local", "month", "time"}:
        return extract_date_like_value(text, param_text)
    if field_type in {"email"}:
        return extract_email_like_value(text)
    if field_type in {"tel", "phone"}:
        return extract_phone_like_value(text)
    if field_type in {"number", "range"}:
        if param_has_any(param_text, ("age", "eldest")):
            return extract_age_like_value(text)
        return extract_count_like_value(text, param_text) or extract_money_like_value(text)

    if param_has_any(param_text, ("age", "eldest")):
        return extract_age_like_value(text)
    if param_has_any(param_text, ("date", "day", "check in", "check out", "arrival", "departure", "start", "end", "when")):
        return extract_date_like_value(text, param_text)
    if param_has_any(param_text, ("destination", "target", "to", "drop", "arrival")):
        return extract_location_like_value(text, "target")
    if param_has_any(param_text, ("origin", "source", "from", "departure city", "pickup")):
        return extract_location_like_value(text, "source")
    if param_has_any(param_text, ("city", "location", "area", "jurisdiction", "branch", "service area", "port", "station", "terminal")):
        return extract_location_like_value(text, "location")
    if param_has_any(param_text, ("traveler", "traveller", "guest", "people", "passenger", "ticket", "adult", "child", "children", "family size", "quantity", "rooms", "nights", "party", "count", "size")):
        return extract_count_like_value(text, param_text)
    if param_has_any(param_text, ("budget", "amount", "price", "cost", "premium", "income", "loan", "emi", "salary", "term", "tenure")):
        return extract_money_like_value(text)
    if param_has_any(param_text, ("phone", "mobile")):
        return extract_phone_like_value(text)
    if param_has_any(param_text, ("email",)):
        return extract_email_like_value(text)
    if param_has_any(param_text, ("name", "full name")):
        return extract_name_like_value(text)
    if param_has_any(param_text, ("project", "scope", "service", "role", "skill", "goal", "matter", "category", "type", "cover", "coverage", "specialist", "course", "program", "vehicle")):
        return extract_need_phrase_value(text)
    return ""


def param_aliases(param: str, label: str) -> list[str]:
    aliases = [param, label, param.replace("_", " "), param.replace("-", " ")]
    rows: list[str] = []
    seen: set[str] = set()
    for alias in aliases:
        clean = normalize_lookup_text(alias)
        if clean and clean not in seen:
            seen.add(clean)
            rows.append(clean)
    return rows


def param_has_any(param_text: str, terms: tuple[str, ...]) -> bool:
    return any(normalize_lookup_text(term) in param_text for term in terms)


def extract_option_value(text: str, spec: dict[str, Any]) -> str:
    normalized = normalize_lookup_text(text)
    for option in spec.get("options") or []:
        if not isinstance(option, dict):
            continue
        label = str(option.get("label") or "").strip()
        value = str(option.get("value") or "").strip()
        for candidate in (label, value):
            candidate_text = normalize_lookup_text(candidate)
            if candidate_text and phrase_in_text(candidate_text, normalized):
                return value or label
    return ""


def extract_labeled_param_value(text: str, aliases: list[str]) -> str:
    source = str(text or "")
    for alias in aliases:
        pattern_alias = r"\s+".join(re.escape(part) for part in alias.split())
        patterns = (
            rf"\b{pattern_alias}\s*(?:is|=|:|-)\s*([A-Za-z0-9][A-Za-z0-9 .,'/+&-]{{0,80}})",
            rf"\b(?:my|the|use|with|for)\s+{pattern_alias}\s*(?:is|=|:|-)?\s*([A-Za-z0-9][A-Za-z0-9 .,'/+&-]{{0,80}})",
        )
        for pattern in patterns:
            match = re.search(pattern, source, flags=re.IGNORECASE)
            if match:
                return clean_generic_extracted_value(match.group(1))
    return ""


def extract_location_like_value(text: str, kind: str) -> str:
    source = str(text or "")
    if kind == "target":
        patterns = (
            r"\bfrom\s+[A-Za-z][A-Za-z .'-]{1,50}\s+to\s+([A-Za-z][A-Za-z .'-]{1,60})",
            r"\b(?:to|target\s*(?:is|:|-)?|destination\s*(?:is|:|-)?)\s+([A-Za-z][A-Za-z .'-]{1,60})",
        )
    elif kind == "source":
        patterns = (
            r"\b(?:from|source\s*(?:is|:|-)?|origin\s*(?:is|:|-)?|pickup\s*(?:is|:|-)?\s*(?:from)?)\s+([A-Za-z][A-Za-z .'-]{1,60})",
        )
    else:
        patterns = (
            r"\b(?:live|living|based|located|stay|staying|service\s+area\s*(?:is|:|-)?|city\s*(?:is|:|-)?|location\s*(?:is|:|-)?|near)\s+(?:in\s+)?([A-Za-z][A-Za-z .'-]{1,60})",
            r"\bfrom\s+([A-Za-z][A-Za-z .'-]{1,60})",
        )
    for pattern in patterns:
        for match in re.finditer(pattern, source, flags=re.IGNORECASE):
            value = clean_extracted_city(match.group(1))
            if value:
                return value
    return ""


def extract_date_like_value(text: str, param_text: str = "") -> str:
    source = str(text or "")
    today = date.today()
    lowered = source.lower()
    if "tomorrow" in lowered:
        return (today + timedelta(days=1)).isoformat()
    if "today" in lowered:
        return today.isoformat()
    if "next week" in lowered:
        return (today + timedelta(days=7)).isoformat()

    match = re.search(
        r"\b(?:on|date\s*(?:is|:|-)?|depart(?:ing|ure)?\s*(?:on|date)?|check\s*in\s*(?:on)?|check\s*out\s*(?:on)?)\s+"
        r"([A-Za-z]{3,9}\s+\d{1,2}(?:,?\s+\d{4})?|\d{1,2}\s+[A-Za-z]{3,9}(?:\s+\d{4})?|\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)",
        source,
        flags=re.IGNORECASE,
    )
    if match:
        return clean_generic_extracted_value(match.group(1))
    match = re.search(
        r"\b(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}(?:,?\s+\d{4})?)\b",
        source,
        flags=re.IGNORECASE,
    )
    return clean_generic_extracted_value(match.group(1)) if match else ""


def extract_count_like_value(text: str, param_text: str = "") -> str:
    patterns = (
        r"\b(\d{1,3})\s*(?:travell?ers?|guests?|people|passengers?|tickets?|adults?|children|kids|rooms?|nights?)\b",
        r"\b(?:for|party\s+of|group\s+of)\s+(\d{1,3})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, str(text or ""), flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return ""


def extract_money_like_value(text: str) -> str:
    match = re.search(
        r"(?:\u20b9|rs\.?|inr|\$|usd)?\s*(\d[\d,]*(?:\.\d+)?)\s*(?:k|lakh|lakhs|crore|cr)?\b",
        str(text or ""),
        flags=re.IGNORECASE,
    )
    return match.group(0).strip() if match else ""


def extract_phone_like_value(text: str) -> str:
    match = re.search(r"\b(?:\+?\d[\d -]{7,}\d|\[PHONE\])\b", str(text or ""), flags=re.IGNORECASE)
    return match.group(0).strip() if match else ""


def extract_email_like_value(text: str) -> str:
    match = re.search(r"\b(?:[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|\[EMAIL\])\b", str(text or ""), flags=re.IGNORECASE)
    return match.group(0).strip() if match else ""


def extract_name_like_value(text: str) -> str:
    match = re.search(r"\b(?:my\s+name\s+is|i\s+am|i'm)\s+([A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){0,3})\b", str(text or ""))
    return clean_generic_extracted_value(match.group(1)) if match else ""


def extract_need_phrase_value(text: str) -> str:
    match = re.search(
        r"\b(?:looking\s+for|need|want|help\s+with|interested\s+in|show\s+me|find)\s+(?:a|an|the|some)?\s*([A-Za-z0-9][A-Za-z0-9 .,'/+&-]{2,80})",
        str(text or ""),
        flags=re.IGNORECASE,
    )
    return clean_generic_extracted_value(match.group(1)) if match else ""


def clean_generic_extracted_value(raw_value: str) -> str:
    text = str(raw_value or "").strip()
    text = re.split(r"[;\n]", text, maxsplit=1)[0]
    text = re.split(
        r"\b(?:and|but|because|please|thanks|thank you|then|after that|with my|with the|for my)\b",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    return re.sub(r"\s+", " ", text).strip(" .,;:-")


def extract_age_like_value(text: str) -> str:
    candidates: list[int] = []
    patterns = (
        r"\b(\d{1,3})\s*(?:yo|y/o|yrs?|years?\s*old|year\s*old)\b",
        r"\b(?:i\s*(?:am|'m)|im|my\s+age\s+is|age(?:d)?|male|female)\s*(?:is|:)?\s*(\d{1,3})\b",
        r"\b(\d{1,3})\s*(?:male|female)\b",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, str(text or ""), flags=re.IGNORECASE):
            try:
                age = int(match.group(1))
            except (TypeError, ValueError):
                continue
            if 1 <= age <= 120:
                candidates.append(age)
    return str(candidates[-1]) if candidates else ""


def clean_extracted_city(raw_city: str) -> str:
    text = str(raw_city or "").strip()
    text = re.split(
        r"\b(?:and|but|because|for|with|who|myself|self|age|aged|years?|year|yo|male|female|looking|need|want|get|buy|quote|quotes|policy|policies|plan|plans|cover|coverage|premium|please|thanks|on|date|when|from|to)\b",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    text = re.sub(r"[^A-Za-z .'-]", " ", text)
    words = [word.strip(" .'-") for word in re.sub(r"\s+", " ", text).split()]
    while words and words[0].lower() in {"a", "an", "the", "city", "location"}:
        words.pop(0)
    words = [word for word in words[:4] if word]
    city = " ".join(words).strip()
    if not city or city.lower() in {"insurance", "policy", "plan", "quote", "home"}:
        return ""
    return " ".join(title_case_city_word(word) for word in city.split())


def title_case_city_word(word: str) -> str:
    if any(char.isupper() for char in word[1:]):
        return word
    return word[:1].upper() + word[1:].lower()


def action_param_has_value(params: dict[str, Any], wanted_key: str) -> bool:
    wanted = normalized_action_param_key(wanted_key)
    for raw_key, value in params.items():
        if normalized_action_param_key(raw_key) != wanted:
            continue
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, tuple, set, dict)):
            return bool(value)
        return True
    return False


def normalized_action_param_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())
