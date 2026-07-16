"""Lexical ranking helpers for generic knowledge retrieval."""

from __future__ import annotations

import re
from typing import Any

from agent.retrieval.generic_items import json_or_text, knowledge_item_to_text, optional_number

LEXICAL_SCORE_FLOOR = 4
LEXICAL_STOPWORDS = {
    "a",
    "am",
    "and",
    "are",
    "between",
    "for",
    "from",
    "i",
    "is",
    "me",
    "my",
    "of",
    "old",
    "please",
    "show",
    "the",
    "to",
    "with",
    "year",
    "years",
    "yrs",
}
LEXICAL_ALIASES = {
    "compare": {"compare", "comparison", "premium", "coverage", "features", "rating"},
    "health": {"health", "medical", "hospital", "hospitalization", "cashless", "illness", "opd"},
    "insurance": {"insurance", "policy", "policies", "plan", "plans", "premium", "coverage", "cover", "claim"},
    "policy": {"insurance", "policy", "policies", "plan", "plans", "coverage", "premium"},
    "plan": {"plan", "plans", "policy", "coverage", "premium"},
}


def rank_lexical_items(query: str, rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    terms = query_terms(query)
    if not terms:
        return []
    age = age_from_query(query)
    scored: list[tuple[int, str, dict[str, Any]]] = []
    for row in rows:
        text = normalize_text(knowledge_item_to_text(row))
        score = lexical_score(text, terms)
        if age is not None and age_matches_item(age, row):
            score += 5
        if score < LEXICAL_SCORE_FLOOR:
            continue
        item = dict(row)
        item["_semantic_score"] = max(float(item.get("_semantic_score") or 0.0), min(score / 30, 0.95))
        scored.append((score, str(item.get("title") or ""), item))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [item for _score, _title, item in scored[:limit]]


def query_terms(query: str) -> set[str]:
    tokens = {
        singularize(token)
        for token in normalize_text(query).split()
        if len(token) > 1 and token not in LEXICAL_STOPWORDS
    }
    expanded = set(tokens)
    for token in tokens:
        expanded.update(LEXICAL_ALIASES.get(token, set()))
    if "20" in tokens or "age" in tokens:
        expanded.update({"age", "eligible", "adult"})
    return {term for term in expanded if term}


def lexical_score(text: str, terms: set[str]) -> int:
    score = 0
    for term in terms:
        if not term:
            continue
        if phrase_in_text(term, text):
            score += 3 if len(term) > 3 else 2
    if phrase_in_text("health", text) and {"health", "medical", "hospital"} & terms:
        score += 6
    if phrase_in_text("insurance", text) and {"insurance", "policy", "plan"} & terms:
        score += 6
    if phrase_in_text("insurance plan", text) or phrase_in_text("health insurance", text):
        score += 4
    return score


def age_from_query(query: str) -> int | None:
    match = re.search(r"\b(?:age\s*)?(\d{1,3})(?:\s*(?:year|years|yr|yrs)\s*old)?\b", str(query or "").lower())
    if not match:
        return None
    try:
        age = int(match.group(1))
    except (TypeError, ValueError):
        return None
    return age if 0 < age < 120 else None


def age_matches_item(age: int, row: dict[str, Any]) -> bool:
    candidates = [
        json_or_text(row.get("policy_json")),
        json_or_text(row.get("attributes_json")),
    ]
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        age_min = optional_number(candidate.get("age_min") or candidate.get("min_age"))
        age_max = optional_number(candidate.get("age_max") or candidate.get("max_age"))
        if age_min is not None and age < age_min:
            continue
        if age_max is not None and age > age_max:
            continue
        if age_min is not None or age_max is not None:
            return True
    return False


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(value or "").lower())).strip()


def phrase_in_text(phrase: str, text: str) -> bool:
    return f" {phrase} " in f" {text} "


def singularize(token: str) -> str:
    if token.endswith("ies") and len(token) > 4:
        return f"{token[:-3]}y"
    if token.endswith("s") and len(token) > 3:
        return token[:-1]
    return token
