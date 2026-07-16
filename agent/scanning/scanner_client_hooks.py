"""Capability helpers for verified client hook adapters."""

from __future__ import annotations

import re
from typing import Any

from agent.scanning.scanner_runtime_capabilities import CapabilityFactory


CLIENT_HOOK_ADAPTER_NAMES = (
    "client-hook",
    "client_hook",
    "custom-hook",
    "custom_hook",
    "verified-hook",
    "verified_hook",
)


def is_client_hook_adapter(adapter_name: str) -> bool:
    normalized = re.sub(
        r"[^a-z0-9]+",
        "-",
        f"{adapter_name or ''}".strip().lower(),
    )
    return any(token in normalized for token in CLIENT_HOOK_ADAPTER_NAMES)


def client_hook_capabilities(adapter_name: str, capability: CapabilityFactory) -> list[Any]:
    evidence = f"Client adapter '{adapter_name}' exposes verified first-party hooks"
    return [
        capability("cart", True, 0.95, evidence),
        capability("checkout", True, 0.9, evidence),
    ]


def merge_capability(detected: Any, override: Any | None) -> Any:
    if override is None:
        return detected
    if override.supported and not detected.supported:
        return override
    if override.supported and override.confidence > detected.confidence:
        return override
    return detected
