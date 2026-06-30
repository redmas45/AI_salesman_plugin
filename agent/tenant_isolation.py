"""Tenant isolation audit helpers for CRM readiness checks."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlparse


def build_tenant_isolation_audit(
    *,
    site_id: str,
    client: dict[str, Any],
    runtime_config: dict[str, Any],
    prompt_profile: dict[str, Any],
    knowledge: dict[str, Any],
) -> dict[str, Any]:
    """Return explicit isolation checks for one client runtime."""
    checks = [
        _check("client_site_id", _text(client.get("site_id")) == site_id, "Client detail belongs to requested site."),
        _check("runtime_site_id", _text(runtime_config.get("site_id")) == site_id, "Runtime config belongs to requested site."),
        _check("install_script_scope", _install_scoped(runtime_config, site_id), "Install assets are scoped with the requested site id."),
        _check("prompt_profile_scope", _prompt_scoped(prompt_profile, site_id), "Prompt profile belongs to requested site."),
        _check("prompt_versions_scope", _prompt_versions_scoped(prompt_profile), "Prompt versions belong to the active profile."),
        _check("knowledge_tenant_schema", isinstance(knowledge.get("stats"), dict), "Knowledge stats loaded from tenant schema."),
        _check("knowledge_items_shape", _knowledge_items_scoped(knowledge), "Knowledge preview is tenant-local and contains no site override field."),
    ]
    failed = [row for row in checks if row["status"] == "failed"]
    return {
        "site_id": site_id,
        "status": "failed" if failed else "passed",
        "summary": {
            "checks": len(checks),
            "failed": len(failed),
            "passed": len(checks) - len(failed),
        },
        "checks": checks,
    }


def _check(key: str, passed: bool, evidence: str) -> dict[str, str]:
    return {
        "key": key,
        "status": "passed" if passed else "failed",
        "evidence": evidence,
    }


def _install_scoped(runtime_config: dict[str, Any], site_id: str) -> bool:
    install = runtime_config.get("install") if isinstance(runtime_config.get("install"), dict) else {}
    urls = [str(value or "") for value in install.values()]
    return bool(urls) and all(_url_site_id(url) == site_id for url in urls)


def _prompt_scoped(prompt_profile: dict[str, Any], site_id: str) -> bool:
    profile = prompt_profile.get("profile") if isinstance(prompt_profile.get("profile"), dict) else {}
    return _text(profile.get("site_id")) == site_id


def _prompt_versions_scoped(prompt_profile: dict[str, Any]) -> bool:
    profile = prompt_profile.get("profile") if isinstance(prompt_profile.get("profile"), dict) else {}
    profile_id = _text(profile.get("id"))
    versions = prompt_profile.get("versions") if isinstance(prompt_profile.get("versions"), list) else []
    if not profile_id:
        return False
    return all(not isinstance(row, dict) or _text(row.get("profile_id")) in {"", profile_id} for row in versions)


def _knowledge_items_scoped(knowledge: dict[str, Any]) -> bool:
    items = knowledge.get("items") if isinstance(knowledge.get("items"), list) else []
    return all(isinstance(item, dict) and "site_id" not in item for item in items[:50])


def _url_site_id(url: str) -> str:
    try:
        parsed = urlparse(url)
    except ValueError:
        return ""
    query = parse_qs(parsed.query)
    return _text((query.get("site") or query.get("site_id") or [""])[0])


def _text(value: Any) -> str:
    return str(value or "").strip()
