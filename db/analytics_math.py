"""Analytics metrics calculations, conversation logs parsing, and AI summarization."""

from __future__ import annotations

import json
import logging
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

import psycopg

import config
from db.database import get_all_products
from db.schema import _connect, init_admin_schema

logger = logging.getLogger(__name__)

ANALYTICS_DEFAULT_RANGE = "7d"
ANALYTICS_CATALOG_PRODUCT_LIMIT = 1000
PRODUCT_FULL_MATCH_WEIGHT = 3
PRODUCT_TOKEN_MATCH_WEIGHT = 1
PRODUCT_COMMON_TOKEN_RATIO = 0.6
PRODUCT_COMMON_TOKEN_MIN_COUNT = 3
SUMMARY_MAX_BULLETS = 6
PERCENT_SCALE = 100
LATENCY_FAST_MS = 1000
LATENCY_ACCEPTABLE_MS = 3000
DEFAULT_USAGE_LIMIT = 200

RANGE_DAYS = {
    "1d": 1,
    "3d": 3,
    "7d": 7,
    "15d": 15,
    "30d": 30,
    "3m": 90,
    "6m": 180,
    "1y": 365,
}

ANALYTICS_STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "and",
    "are",
    "can",
    "could",
    "for",
    "from",
    "have",
    "how",
    "into",
    "like",
    "me",
    "more",
    "need",
    "please",
    "show",
    "that",
    "the",
    "this",
    "what",
    "with",
    "you",
    "your",
}

PRODUCT_TOKEN_STOPWORDS = ANALYTICS_STOPWORDS | {
    "any",
    "best",
    "buy",
    "choice",
    "get",
    "good",
    "great",
    "help",
    "hello",
    "here",
    "interested",
    "looking",
    "might",
    "one",
    "ready",
    "see",
    "some",
    "want",
    "yaar",
}

PRODUCT_TYPE_TOKENS = {
    "bag",
    "bottom",
    "cap",
    "cup",
    "hoodie",
    "jacket",
    "mug",
    "onesie",
    "pant",
    "shirt",
    "shoe",
    "sticker",
    "top",
}


def conversation_log(range_key: str = ANALYTICS_DEFAULT_RANGE, site_id: str = "") -> dict[str, Any]:
    """Return date-grouped conversation sessions and turns for CRM review."""
    rows = _usage_rows(range_key, site_id, limit=500)
    sessions: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        session_key = (row["site_id"], row["session_id"])
        session = sessions.setdefault(
            session_key,
            {
                "site_id": row["site_id"],
                "session_id": row["session_id"],
                "started_at": row["created_at"],
                "last_seen_at": row["created_at"],
                "turn_count": 0,
                "tokens_used": 0,
                "turns": [],
            },
        )
        session["turn_count"] += 1
        session["tokens_used"] += _row_tokens(row)
        session["last_seen_at"] = row["created_at"]
        session["turns"].append(_conversation_turn(row))

    date_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for session in sessions.values():
        group_date = str(session["last_seen_at"])[:10]
        session["turns"].sort(key=lambda item: item["created_at"], reverse=True)
        date_groups[group_date].append(session)

    groups = [
        {
            "date": date,
            "sessions": sorted(items, key=lambda item: item["last_seen_at"], reverse=True),
        }
        for date, items in sorted(date_groups.items(), reverse=True)
    ]
    return {"range": _clean_range_key(range_key), "site_id": site_id or "all", "groups": groups}


def analytics_snapshot(range_key: str = ANALYTICS_DEFAULT_RANGE, site_id: str = "") -> dict[str, Any]:
    """Return CRM analytics computed from stored conversation turns."""
    rows = _usage_rows(range_key, site_id, limit=2000)
    tokens = sum(_row_tokens(row) for row in rows)
    sessions = {(row["site_id"], row["session_id"]) for row in rows}
    intents = Counter(row["intent"] or "unknown" for row in rows)
    products = _top_product_mentions(rows)
    statuses = Counter(row["status"] or "unknown" for row in rows)
    transports = Counter(row["transport"] or "unknown" for row in rows)
    sites = Counter(row["site_id"] or "unknown" for row in rows)
    action_count = sum(int(row.get("action_count") or 0) for row in rows)
    action_turn_count = sum(1 for row in rows if int(row.get("action_count") or 0) > 0)
    error_count = sum(1 for row in rows if str(row.get("status") or "").lower() not in {"ok", "success"})
    series = _daily_series(rows)
    peak_day = _peak_series_day(series)
    return {
        "range": _clean_range_key(range_key),
        "site_id": site_id or "all",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "turns": len(rows),
            "tokens": tokens,
            "sessions": len(sessions),
            "avg_latency_ms": _average_latency(rows),
            "actions": action_count,
            "action_rate": _percent(action_turn_count, len(rows)),
            "error_rate": _percent(error_count, len(rows)),
            "tokens_per_turn": round(tokens / len(rows), 1) if rows else 0,
        },
        "top_intents": _counter_rows(intents, limit=8),
        "top_products": _counter_rows(products, limit=12),
        "top_terms": _counter_rows(products, limit=12),
        "status_mix": _counter_rows(statuses, limit=8),
        "transport_mix": _counter_rows(transports, limit=8),
        "site_mix": _counter_rows(sites, limit=8),
        "latency_buckets": _latency_bucket_rows(rows),
        "peak_day": peak_day,
        "recent_events": rows[:8],
        "series": series,
        "summary": _heuristic_summary(rows, intents, products),
    }


def generate_analytics_summary(range_key: str = ANALYTICS_DEFAULT_RANGE, site_id: str = "") -> dict[str, Any]:
    """Generate an AI analytics summary when OpenAI is configured."""
    snapshot = analytics_snapshot(range_key, site_id)
    if not config.OPENAI_API_KEY:
        return {**snapshot, "summary_source": "heuristic"}

    try:
        from openai import OpenAI

        client = OpenAI(api_key=config.OPENAI_API_KEY)
        completion = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You summarize ecommerce voice-assistant analytics for a store manager. "
                        "Return 4 to 6 plain bullet points only. Start each line with '- '. "
                        "Focus on what customers are looking for, what to stock, and what operational "
                        "action to take. Mention demand terms only when they are product names from "
                        "top_products. Do not use markdown headings."
                    ),
                },
                {
                    "role": "user",
                    "content": json_ready_analytics(snapshot),
                },
            ],
            temperature=0.2,
            max_tokens=280,
        )
        summary = completion.choices[0].message.content or snapshot["summary"]
        return {**snapshot, "summary": _clean_summary_bullets(summary), "summary_source": "openai"}
    except Exception as exc:
        logger.warning("OpenAI analytics summary failed; using heuristic summary: %s", exc)
        return {**snapshot, "summary_source": "heuristic"}


def _usage_rows(range_key: str, site_id: str = "", limit: int = DEFAULT_USAGE_LIMIT) -> list[dict[str, Any]]:
    from db.clients import _safe_site_id

    init_admin_schema()
    clean_site_id = _safe_site_id(site_id) if site_id else ""
    start_at = _range_start(_clean_range_key(range_key))
    clauses: list[str] = []
    params: list[Any] = []
    if clean_site_id:
        clauses.append("site_id = %s")
        params.append(clean_site_id)
    if start_at:
        clauses.append("created_at >= %s")
        params.append(start_at)
    where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(max(1, int(limit)))
    with _connect() as conn:
        rows = conn.execute(
            f"""
            SELECT
                site_id, session_id, transport, status, intent, action_count,
                input_tokens, output_tokens, latency_ms, transcript, response_text,
                created_at::TEXT AS created_at
            FROM hub_usage_events
            {where_clause}
            ORDER BY created_at DESC
            LIMIT %s
            """,
            tuple(params),
        ).fetchall()
    return [dict(row) for row in rows]


def _conversation_turn(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "created_at": row["created_at"],
        "transport": row["transport"],
        "status": row["status"],
        "intent": row["intent"] or "unknown",
        "tokens": _row_tokens(row),
        "latency_ms": int(float(row["latency_ms"] or 0)),
        "transcript": row["transcript"],
        "response_text": row["response_text"],
        "action_count": int(row["action_count"] or 0),
    }


def _row_tokens(row: dict[str, Any]) -> int:
    return int(row.get("input_tokens") or 0) + int(row.get("output_tokens") or 0)


def _clean_range_key(range_key: str) -> str:
    text = str(range_key or ANALYTICS_DEFAULT_RANGE).strip().lower()
    if text == "all":
        return "all"
    return text if text in RANGE_DAYS else ANALYTICS_DEFAULT_RANGE


def _range_start(range_key: str) -> datetime | None:
    if range_key == "all":
        return None
    return datetime.now(timezone.utc) - timedelta(days=RANGE_DAYS[range_key])


def _top_product_mentions(rows: list[dict[str, Any]]) -> Counter[str]:
    products: Counter[str] = Counter()
    matchers_by_site = _product_matchers_by_site({row["site_id"] for row in rows})
    for row in rows:
        matchers = matchers_by_site.get(row["site_id"], [])
        exact_matches = _exact_product_matches(row, matchers)
        if exact_matches:
            products.update(exact_matches)
            continue
        products.update(_fallback_product_matches(row, matchers))
    return products


def _exact_product_matches(row: dict[str, Any], matchers: list[dict[str, Any]]) -> Counter[str]:
    matches: Counter[str] = Counter()
    normalized_text = _normalized_product_text(_conversation_product_text(row))
    for matcher in matchers:
        if matcher["full_text"] and matcher["full_text"] in normalized_text:
            matches[matcher["name"]] += PRODUCT_FULL_MATCH_WEIGHT
    return matches


def _fallback_product_matches(row: dict[str, Any], matchers: list[dict[str, Any]]) -> Counter[str]:
    matches: Counter[str] = Counter()
    text_tokens = set(_normalized_product_tokens(_customer_demand_text(row)))
    for matcher in matchers:
        if matcher["tokens"] & text_tokens:
            matches[matcher["name"]] += PRODUCT_TOKEN_MATCH_WEIGHT
    return matches


def _product_matchers_by_site(site_ids: set[str]) -> dict[str, list[dict[str, Any]]]:
    products_by_site = _catalog_product_names(site_ids)
    return {
        site_id: _product_matchers(product_names)
        for site_id, product_names in products_by_site.items()
    }


def _catalog_product_names(site_ids: set[str]) -> dict[str, list[str]]:
    product_names: dict[str, list[str]] = {}
    for site_id in site_ids:
        try:
            products = get_all_products(site_id, limit=ANALYTICS_CATALOG_PRODUCT_LIMIT)
        except psycopg.Error:
            product_names[site_id] = []
            continue
        product_names[site_id] = _unique_product_names(products)
    return product_names


def _unique_product_names(products: list[dict[str, Any]]) -> list[str]:
    names = {
        str(product.get("name") or "").strip()
        for product in products
        if str(product.get("name") or "").strip()
    }
    return sorted(names)


def _product_matchers(product_names: list[str]) -> list[dict[str, Any]]:
    common_tokens = _common_product_tokens(product_names)
    return [
        {
            "name": product_name,
            "full_text": _normalized_product_text(product_name),
            "tokens": _significant_product_tokens(product_name, common_tokens),
        }
        for product_name in product_names
    ]


def _common_product_tokens(product_names: list[str]) -> set[str]:
    token_counts: Counter[str] = Counter()
    for product_name in product_names:
        token_counts.update(set(_normalized_product_tokens(product_name)))
    threshold = max(PRODUCT_COMMON_TOKEN_MIN_COUNT, int(len(product_names) * PRODUCT_COMMON_TOKEN_RATIO))
    return {
        token
        for token, count in token_counts.items()
        if count >= threshold and token not in PRODUCT_TYPE_TOKENS
    }


def _significant_product_tokens(product_name: str, common_tokens: set[str]) -> set[str]:
    tokens = {
        token
        for token in _normalized_product_tokens(product_name)
        if _is_product_signal_token(token, common_tokens)
    }
    if tokens:
        return tokens
    return set(_normalized_product_tokens(product_name)) - common_tokens


def _is_product_signal_token(token: str, common_tokens: set[str]) -> bool:
    if len(token) < 3:
        return False
    if token in PRODUCT_TOKEN_STOPWORDS or token in common_tokens:
        return False
    return True


def _customer_demand_text(row: dict[str, Any]) -> str:
    return str(row.get("transcript") or "")


def _conversation_product_text(row: dict[str, Any]) -> str:
    return f"{row.get('transcript', '')} {row.get('response_text', '')}"


def _normalized_product_text(value: str) -> str:
    return " ".join(_normalized_product_tokens(value))


def _normalized_product_tokens(value: str) -> list[str]:
    text = str(value or "").lower()
    text = re.sub(r"\bt[\s-]?shirts?\b", " t shirt ", text)
    text = re.sub(r"\btees?\b", " t shirt ", text)
    return [_singular_token(token) for token in re.findall(r"[a-z0-9]+", text)]


def _singular_token(token: str) -> str:
    if len(token) > 4 and token.endswith("ies"):
        return f"{token[:-3]}y"
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _daily_series(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    daily: dict[str, dict[str, int]] = defaultdict(lambda: {"turns": 0, "tokens": 0})
    for row in rows:
        day = str(row["created_at"])[:10]
        daily[day]["turns"] += 1
        daily[day]["tokens"] += _row_tokens(row)
    return [
        {"date": day, "turns": values["turns"], "tokens": values["tokens"]}
        for day, values in sorted(daily.items())
    ]


def _average_latency(rows: list[dict[str, Any]]) -> int:
    values = [float(row["latency_ms"] or 0) for row in rows if float(row["latency_ms"] or 0) > 0]
    if not values:
        return 0
    return int(round(sum(values) / len(values)))


def _counter_rows(counter: Counter[str], limit: int) -> list[dict[str, Any]]:
    return [{"label": label, "count": count} for label, count in counter.most_common(limit)]


def _latency_bucket_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: Counter[str] = Counter()
    for row in rows:
        latency_ms = float(row.get("latency_ms") or 0)
        if latency_ms <= 0:
            buckets["No timing"] += 1
        elif latency_ms < LATENCY_FAST_MS:
            buckets["Under 1s"] += 1
        elif latency_ms <= LATENCY_ACCEPTABLE_MS:
            buckets["1s to 3s"] += 1
        else:
            buckets["Over 3s"] += 1
    ordered_labels = ["Under 1s", "1s to 3s", "Over 3s", "No timing"]
    return [{"label": label, "count": buckets[label]} for label in ordered_labels if buckets[label]]


def _peak_series_day(series: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not series:
        return None
    return max(series, key=lambda row: int(row.get("turns") or 0))


def _percent(value: int, total: int) -> int:
    if total <= 0:
        return 0
    return int(round((value / total) * PERCENT_SCALE))


def _heuristic_summary(
    rows: list[dict[str, Any]],
    intents: Counter[str],
    products: Counter[str],
) -> str:
    if not rows:
        return "\n".join(
            [
                "- No customer conversations are logged for this range yet.",
                "- Keep collecting voice turns before making stock or merchandising decisions.",
            ]
        )
    top_intent = intents.most_common(1)[0][0] if intents else "unknown"
    top_products = [label for label, _count in products.most_common(5)]
    bullets = [
        f"- Customers completed {len(rows)} voice turns in this range; the main intent is {top_intent}.",
        _demand_summary_bullet(top_products),
        _stock_summary_bullet(intents, top_products),
        _latency_summary_bullet(rows),
    ]
    return "\n".join(bullets)


def _demand_summary_bullet(top_products: list[str]) -> str:
    if not top_products:
        return "- No clear product demand signal is visible yet; collect more conversations before changing stock."
    return f"- Customers are showing interest in {', '.join(top_products[:3])}."


def _stock_summary_bullet(intents: Counter[str], top_products: list[str]) -> str:
    out_of_stock_count = intents.get("out_of_stock", 0)
    if out_of_stock_count and top_products:
        return f"- Stock check: review availability for {', '.join(top_products[:3])}; out-of-stock came up {out_of_stock_count} time(s)."
    if top_products:
        return f"- Merchandising action: keep {top_products[0]} visible in search, recommendations, and featured sections."
    return "- Stock action: wait for stronger product-level demand before increasing inventory."


def _latency_summary_bullet(rows: list[dict[str, Any]]) -> str:
    latency_ms = _average_latency(rows)
    if latency_ms <= 0:
        return "- Operations action: no latency trend is available yet."
    if latency_ms > 3000:
        return f"- Operations action: average latency is {latency_ms} ms, so response speed should be improved."
    return f"- Operations action: average latency is {latency_ms} ms, which is acceptable for this range."


def json_ready_analytics(snapshot: dict[str, Any]) -> str:
    payload = {
        "range": snapshot["range"],
        "metrics": snapshot["metrics"],
        "top_intents": snapshot["top_intents"],
        "top_products": snapshot["top_products"],
        "series": snapshot["series"][-14:],
    }
    return json.dumps(payload, ensure_ascii=True)


def _clean_summary_bullets(summary: str) -> str:
    lines = [_clean_summary_line(line) for line in str(summary or "").splitlines()]
    bullets = [line for line in lines if line]
    if not bullets:
        return "- No actionable analytics summary was generated."
    return "\n".join(f"- {line}" for line in bullets[:SUMMARY_MAX_BULLETS])


def _clean_summary_line(line: str) -> str:
    text = re.sub(r"^#{1,6}\s*", "", str(line or "").strip())
    text = text.replace("**", "").strip()
    text = re.sub(r"^[-*]\s+", "", text)
    text = re.sub(r"^\d+[\.)]\s+", "", text)
    if not text or text.lower().startswith("key metrics"):
        return ""
    return text
