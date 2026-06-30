"""Prompt profile persistence and publication helpers."""

from __future__ import annotations

import json
import uuid
from typing import Any

from agent.actions.registry import is_supported_action
from agent.verticals.registry import DEFAULT_VERTICAL_KEY, get_vertical
from db.clients import _client_row, _safe_site_id
from db.schema import _connect, init_admin_schema

PROMPT_STATUS_DRAFT = "draft"
PROMPT_STATUS_PUBLISHED = "published"
PROMPT_STATUS_ARCHIVED = "archived"
DEFAULT_CREATED_BY = "crm"
PROMPT_BASE_ACTIONS: frozenset[str] = frozenset({
    "SHOW_ENTITIES",
    "COMPARE_ENTITIES",
    "FILTER_ENTITIES",
    "OPEN_ENTITY_DETAIL",
    "SORT_ENTITIES",
    "NAVIGATE_TO",
    "OPEN_CONTACT",
    "OPEN_POLICY",
    "CLEAR_HISTORY",
    "UPDATE_PREFERENCES",
})
ECOMMERCE_PROMPT_ACTIONS: frozenset[str] = frozenset({
    "SHOW_PRODUCTS",
    "SHOW_COMPARISON",
    "FILTER_PRODUCTS",
    "SORT_PRODUCTS",
    "SHOW_PRODUCT_DETAIL",
    "CLEAR_FILTERS",
    "ADD_TO_CART",
    "REMOVE_FROM_CART",
    "UPDATE_CART_QUANTITY",
    "CLEAR_CART",
    "CHECKOUT",
})


def get_client_prompt_profile(site_id: str) -> dict[str, Any]:
    """Return a client's prompt profile, creating a draft profile if needed."""
    clean_site_id = _safe_site_id(site_id)
    profile = ensure_client_prompt_profile(clean_site_id)
    versions = _profile_versions(profile["id"])
    return {
        "profile": profile,
        "versions": versions,
        "draft_version": _first_version(versions, PROMPT_STATUS_DRAFT),
        "published_version": _first_version(versions, PROMPT_STATUS_PUBLISHED),
        "active_version": _first_version(versions, PROMPT_STATUS_PUBLISHED)
        or _first_version(versions, PROMPT_STATUS_DRAFT),
    }


def ensure_client_prompt_profile(site_id: str) -> dict[str, Any]:
    """Ensure the client has one prompt profile linked from hub_clients."""
    init_admin_schema()
    client = _client_row(site_id)
    if not client:
        raise LookupError(f"Client {site_id} was not found.")

    profile_id = str(client.get("prompt_profile_id") or "").strip()
    profile = _profile_by_id(profile_id) if profile_id else None
    if profile:
        return profile

    vertical_key = str(client.get("vertical_key") or DEFAULT_VERTICAL_KEY)
    profile = _create_prompt_profile(
        site_id=site_id,
        name=f"{client.get('name') or site_id} prompt",
        vertical_key=vertical_key,
    )
    _create_prompt_version(
        profile_id=profile["id"],
        version=1,
        status=PROMPT_STATUS_DRAFT,
        system_prompt=_default_system_prompt(client, vertical_key),
        developer_rules=_default_developer_rules(vertical_key),
        allowed_actions=_allowed_prompt_actions(vertical_key),
    )
    _link_profile_to_client(site_id, profile["id"])
    return profile


def save_client_prompt_profile(
    site_id: str,
    *,
    name: str,
    system_prompt: str,
    developer_rules: str = "",
    publish: bool = False,
    changelog: str = "",
) -> dict[str, Any]:
    """Create a new prompt version as draft or published."""
    clean_site_id = _safe_site_id(site_id)
    profile = ensure_client_prompt_profile(clean_site_id)
    vertical_key = str(profile.get("vertical_key") or _client_vertical_key(clean_site_id))
    clean_name = _required_text(name, "Prompt profile name is required.")
    clean_prompt = _required_text(system_prompt, "System prompt is required.")
    status = PROMPT_STATUS_PUBLISHED if publish else PROMPT_STATUS_DRAFT

    with _connect() as conn:
        conn.execute(
            """
            UPDATE hub_prompt_profiles
            SET name = %s,
                status = %s,
                updated_at = now()
            WHERE id = %s
            """,
            (clean_name, status, profile["id"]),
        )
        if publish:
            _archive_published_versions(conn, profile["id"])
        version = _next_profile_version(conn, profile["id"])
        conn.execute(
            """
            INSERT INTO hub_prompt_versions
                (
                    id, profile_id, version, status, system_prompt,
                    developer_rules, allowed_actions_json, changelog,
                    created_by, published_at
                )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CASE WHEN %s THEN now() ELSE NULL END)
            """,
            (
                _new_id("prompt_version"),
                profile["id"],
                version,
                status,
                clean_prompt,
                str(developer_rules or ""),
                _json_text(_allowed_prompt_actions(vertical_key)),
                str(changelog or ""),
                DEFAULT_CREATED_BY,
                publish,
            ),
        )
        conn.commit()
    return get_client_prompt_profile(clean_site_id)


def publish_prompt_version(version_id: str) -> dict[str, Any]:
    """Publish a prompt version and archive the previous published version."""
    clean_id = _required_text(version_id, "Prompt version ID is required.")
    init_admin_schema()
    with _connect() as conn:
        row = conn.execute(
            "SELECT profile_id FROM hub_prompt_versions WHERE id = %s",
            (clean_id,),
        ).fetchone()
        if not row:
            raise LookupError(f"Prompt version {clean_id} was not found.")
        profile_id = row["profile_id"]
        _archive_published_versions(conn, profile_id)
        conn.execute(
            """
            UPDATE hub_prompt_versions
            SET status = %s,
                published_at = now()
            WHERE id = %s
            """,
            (PROMPT_STATUS_PUBLISHED, clean_id),
        )
        conn.execute(
            """
            UPDATE hub_prompt_profiles
            SET status = %s,
                updated_at = now()
            WHERE id = %s
            """,
            (PROMPT_STATUS_PUBLISHED, profile_id),
        )
        conn.commit()
    return {"version_id": clean_id, "status": PROMPT_STATUS_PUBLISHED}


def list_prompt_profiles() -> list[dict[str, Any]]:
    """Return all prompt profiles for CRM management."""
    init_admin_schema()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM hub_prompt_profiles
            ORDER BY updated_at DESC, name ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def prompt_profile_context(site_id: str) -> str:
    """Return the published client prompt block used at runtime."""
    try:
        profile = get_client_prompt_profile(site_id)
    except LookupError:
        return ""
    published = profile.get("published_version")
    if not published:
        return ""
    rules = str(published.get("developer_rules") or "").strip()
    prompt = str(published.get("system_prompt") or "").strip()
    if not prompt and not rules:
        return ""
    parts = [f"Client custom prompt:\n{prompt}"] if prompt else []
    if rules:
        parts.append(f"Client developer rules:\n{rules}")
    return "\n\n".join(parts)


def _create_prompt_profile(site_id: str, name: str, vertical_key: str) -> dict[str, Any]:
    profile_id = _new_id("prompt_profile")
    vertical = get_vertical(vertical_key)
    with _connect() as conn:
        row = conn.execute(
            """
            INSERT INTO hub_prompt_profiles
                (id, site_id, name, vertical_key, status, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (profile_id, site_id, name, vertical.key, PROMPT_STATUS_DRAFT, DEFAULT_CREATED_BY),
        ).fetchone()
        conn.commit()
    return dict(row)


def _create_prompt_version(
    *,
    profile_id: str,
    version: int,
    status: str,
    system_prompt: str,
    developer_rules: str,
    allowed_actions: list[str],
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO hub_prompt_versions
                (
                    id, profile_id, version, status, system_prompt,
                    developer_rules, allowed_actions_json, created_by
                )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                _new_id("prompt_version"),
                profile_id,
                version,
                status,
                system_prompt,
                developer_rules,
                _json_text(allowed_actions),
                DEFAULT_CREATED_BY,
            ),
        )
        conn.commit()


def _allowed_prompt_actions(vertical_key: str) -> list[str]:
    vertical = get_vertical(vertical_key)
    allowed = set(vertical.action_types) | set(PROMPT_BASE_ACTIONS)
    if vertical.key == "ecommerce":
        allowed |= set(ECOMMERCE_PROMPT_ACTIONS)
    return sorted(action for action in allowed if is_supported_action(action))


def _client_vertical_key(site_id: str) -> str:
    client = _client_row(site_id)
    return str((client or {}).get("vertical_key") or DEFAULT_VERTICAL_KEY)


def _profile_by_id(profile_id: str) -> dict[str, Any] | None:
    if not profile_id:
        return None
    init_admin_schema()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM hub_prompt_profiles WHERE id = %s",
            (profile_id,),
        ).fetchone()
    return dict(row) if row else None


def _profile_versions(profile_id: str) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT
                id, profile_id, version, status, system_prompt,
                developer_rules, response_schema_json, variables_json,
                allowed_actions_json, changelog, created_by,
                created_at::TEXT AS created_at,
                published_at::TEXT AS published_at
            FROM hub_prompt_versions
            WHERE profile_id = %s
            ORDER BY version DESC
            """,
            (profile_id,),
        ).fetchall()
    return [_decode_version(row) for row in rows]


def _decode_version(row: dict[str, Any]) -> dict[str, Any]:
    version = dict(row)
    for key in ("response_schema_json", "variables_json", "allowed_actions_json"):
        version[key.replace("_json", "")] = _json_or_default(version.pop(key, ""), [] if key == "allowed_actions_json" else {})
    return version


def _first_version(versions: list[dict[str, Any]], status: str) -> dict[str, Any] | None:
    return next((version for version in versions if version.get("status") == status), None)


def _link_profile_to_client(site_id: str, profile_id: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            UPDATE hub_clients
            SET prompt_profile_id = %s,
                updated_at = now()
            WHERE site_id = %s
            """,
            (profile_id, site_id),
        )
        conn.commit()


def _next_profile_version(conn, profile_id: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(version), 0) + 1 AS next_version FROM hub_prompt_versions WHERE profile_id = %s",
        (profile_id,),
    ).fetchone()
    return int(row["next_version"] if row else 1)


def _archive_published_versions(conn, profile_id: str) -> None:
    conn.execute(
        """
        UPDATE hub_prompt_versions
        SET status = %s
        WHERE profile_id = %s AND status = %s
        """,
        (PROMPT_STATUS_ARCHIVED, profile_id, PROMPT_STATUS_PUBLISHED),
    )


def _default_system_prompt(client: dict[str, Any], vertical_key: str) -> str:
    vertical = get_vertical(vertical_key)
    return (
        f"You are Maya, the expert AI sales and support associate for {client.get('name') or client.get('site_id')}. "
        f"You must strictly use a warm, empathetic, and professional female persona. Introduce yourself briefly as Maya when appropriate. "
        f"Do NOT use generic AI disclaimers (e.g., 'As an AI...', 'I am an AI...'). Speak naturally like a top-tier human consultant. "
        f"The client vertical is {vertical.label}. Your sole source of truth is the website's retrieved context for "
        f"{vertical.entity_label_plural}, pages, policies, forms, and live browser data. "
        "CRITICAL GUARDRAILS:\n"
        "1. Never invent, guess, or estimate prices, premiums, inventory, eligibility, dates, or legal/medical/financial outcomes.\n"
        "2. If information is missing from the context, honestly state that you don't have that specific data and offer the next best website action (like contacting support or checking a related category).\n"
        "3. Keep responses extremely concise and conversational. Do not output massive walls of text.\n"
        "4. Guide the user fluidly through the website by triggering supported UI actions (comparing, sorting, adding to cart, opening details) rather than just describing how to do it."
    )


def _default_developer_rules(vertical_key: str) -> str:
    vertical = get_vertical(vertical_key)
    if vertical.risk_level == "high":
        return (
            "High-risk vertical: do not make regulated decisions, diagnoses, legal conclusions, approval promises, "
            "claim guarantees, underwriting decisions, or financial suitability recommendations. Use source-backed "
            "explanations and website-supported handoff/action flows only. NEVER hallucinate terms."
        )
    return "Do not invent unavailable data, prices, stock, dates, terms, policy details, or completion states. Be concise and human-like."


def _required_text(value: str, message: str) -> str:
    clean_value = str(value or "").strip()
    if not clean_value:
        raise ValueError(message)
    return clean_value


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _json_or_default(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (json.JSONDecodeError, TypeError):
        return fallback
