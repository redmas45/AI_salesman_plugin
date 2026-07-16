"""Data models for AI readiness scanner reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SiteCapability:
    """One capability detection result."""

    name: str
    supported: bool
    confidence: float
    evidence: str
    blocking: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReadinessReport:
    """Full readiness scan output for one client site."""

    site_id: str
    site_url: str
    platform: str
    platform_confidence: float
    capabilities: list[SiteCapability] = field(default_factory=list)
    scanned_at: str = ""
    scan_duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "site_id": self.site_id,
            "site_url": self.site_url,
            "platform": self.platform,
            "platform_confidence": round(self.platform_confidence, 2),
            "capabilities": [cap.to_dict() for cap in self.capabilities],
            "scanned_at": self.scanned_at,
            "scan_duration_ms": round(self.scan_duration_ms, 1),
        }

    def capability(self, name: str) -> SiteCapability | None:
        """Lookup a capability by name."""
        for cap in self.capabilities:
            if cap.name == name:
                return cap
        return None
