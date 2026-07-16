"""Report models for catalog ingestion runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class CrawlReport:
    site_id: str
    site_url: str
    source_type: str
    pages_visited: int
    pages_failed: int
    pages_blocked: int
    product_count: int
    variant_count: int
    category_count: int
    failed_urls: list[str] = field(default_factory=list)
    blocked_urls: list[str] = field(default_factory=list)
    coverage_score: float = 0.0
    duration_ms: float = 0.0
    stopped_by_limit: bool = False
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["coverage_score"] = round(float(self.coverage_score), 2)
        data["duration_ms"] = round(float(self.duration_ms), 1)
        return data
