"""Detect hard automation barriers in discovered website flows."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

MAX_BARRIER_FINDINGS = 80
HIGH_SEVERITY = "high"
MEDIUM_SEVERITY = "medium"
LOW_SEVERITY = "low"


@dataclass(frozen=True)
class FlowBarrierFinding:
    """One obstacle that affects universal website control."""

    key: str
    label: str
    severity: str
    page_url: str
    evidence: str
    handling: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FlowBarrierReport:
    """Hard-flow obstacles detected during website discovery."""

    site_id: str
    site_url: str
    summary: dict[str, Any] = field(default_factory=dict)
    findings: tuple[FlowBarrierFinding, ...] = ()
    detected_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "site_id": self.site_id,
            "site_url": self.site_url,
            "summary": self.summary,
            "findings": [finding.to_dict() for finding in self.findings],
            "detected_at": self.detected_at,
        }


def build_flow_barrier_report(
    snapshots: list[dict[str, Any]],
    *,
    site_id: str,
    site_url: str,
) -> FlowBarrierReport:
    """Build barrier evidence from flow discovery snapshots."""
    findings = _unique_findings(_snapshot_findings(snapshot) for snapshot in snapshots)
    return FlowBarrierReport(
        site_id=site_id,
        site_url=site_url,
        summary=_summary(findings),
        findings=tuple(findings),
        detected_at=datetime.now(timezone.utc).isoformat(),
    )


def _snapshot_findings(snapshot: dict[str, Any]) -> list[FlowBarrierFinding]:
    page_url = str(snapshot.get("url") or "")
    text = str(snapshot.get("text_sample") or "").lower()
    hints = snapshot.get("barrier_hints") if isinstance(snapshot.get("barrier_hints"), dict) else {}
    findings: list[FlowBarrierFinding] = []
    findings.extend(_auth_findings(text, hints, page_url))
    findings.extend(_captcha_findings(text, hints, page_url))
    findings.extend(_iframe_findings(hints, page_url))
    findings.extend(_payment_findings(text, hints, page_url))
    findings.extend(_calendar_findings(text, hints, page_url))
    findings.extend(_map_findings(text, hints, page_url))
    findings.extend(_file_upload_findings(text, hints, page_url))
    findings.extend(_external_handoff_findings(hints, page_url))
    return findings


def _auth_findings(text: str, hints: dict[str, Any], page_url: str) -> list[FlowBarrierFinding]:
    password_count = int(hints.get("password_inputs") or 0)
    if password_count > 0 or _has_any(text, ("sign in to continue", "login required", "log in to continue", "account required")):
        return [_finding("auth_required", HIGH_SEVERITY, page_url, "Login/account gate detected.", "Require user login or authenticated integration before autonomous actions.")]
    return []


def _captcha_findings(text: str, hints: dict[str, Any], page_url: str) -> list[FlowBarrierFinding]:
    providers = _string_list(hints.get("captcha_providers"))
    if providers or bool(hints.get("captcha")) or "captcha" in text or "not a robot" in text:
        evidence = f"CAPTCHA provider(s): {', '.join(providers)}" if providers else "CAPTCHA or bot challenge detected."
        return [_finding("captcha", HIGH_SEVERITY, page_url, evidence, "Use human handoff; do not attempt automated CAPTCHA solving.")]
    return []


def _iframe_findings(hints: dict[str, Any], page_url: str) -> list[FlowBarrierFinding]:
    iframe_count = int(hints.get("iframe_count") or 0)
    sources = _string_list(hints.get("iframe_sources"))
    if iframe_count <= 0:
        return []
    evidence = f"{iframe_count} iframe(s) detected"
    if sources:
        evidence = f"{evidence}: {', '.join(sources[:3])}"
    return [_finding("embedded_iframe", MEDIUM_SEVERITY, page_url, evidence, "Inspect iframe origin; cross-origin widgets need provider-specific integration or handoff.")]


def _payment_findings(text: str, hints: dict[str, Any], page_url: str) -> list[FlowBarrierFinding]:
    providers = _string_list(hints.get("payment_providers"))
    if providers or _has_any(text, ("payment", "card details", "pay now", "secure checkout")):
        evidence = f"Payment provider(s): {', '.join(providers)}" if providers else "Payment/checkout wording detected."
        return [_finding("payment_handoff", HIGH_SEVERITY, page_url, evidence, "Never complete payment automatically; navigate or hand off after user confirmation.")]
    return []


def _calendar_findings(text: str, hints: dict[str, Any], page_url: str) -> list[FlowBarrierFinding]:
    providers = _string_list(hints.get("calendar_providers"))
    date_inputs = int(hints.get("date_inputs") or 0)
    if providers or date_inputs > 0 or _has_any(text, ("select a date", "choose a time", "calendar", "appointment slot")):
        evidence = f"Calendar provider(s): {', '.join(providers)}" if providers else "Calendar/date selection detected."
        return [_finding("calendar_widget", MEDIUM_SEVERITY, page_url, evidence, "Use explicit slot-selection policy or provider-specific integration before booking.")]
    return []


def _map_findings(text: str, hints: dict[str, Any], page_url: str) -> list[FlowBarrierFinding]:
    providers = _string_list(hints.get("map_providers"))
    if providers or _has_any(text, ("view map", "directions", "service area map")):
        evidence = f"Map provider(s): {', '.join(providers)}" if providers else "Map/location wording detected."
        return [_finding("map_widget", LOW_SEVERITY, page_url, evidence, "Treat map interaction as informational unless a route/location action is explicitly configured.")]
    return []


def _file_upload_findings(text: str, hints: dict[str, Any], page_url: str) -> list[FlowBarrierFinding]:
    upload_count = int(hints.get("file_uploads") or 0)
    if upload_count > 0 or _has_any(text, ("upload resume", "upload document", "attach file", "upload file")):
        return [_finding("file_upload", MEDIUM_SEVERITY, page_url, "File upload field or upload wording detected.", "Require user-provided file and explicit confirmation before continuing.")]
    return []


def _external_handoff_findings(hints: dict[str, Any], page_url: str) -> list[FlowBarrierFinding]:
    hosts = _string_list(hints.get("external_action_hosts"))
    if not hosts:
        return []
    return [_finding("external_handoff", MEDIUM_SEVERITY, page_url, f"Action links leave site: {', '.join(hosts[:5])}", "Confirm cross-origin navigation and hand off where the widget cannot control the target page.")]


def _finding(key: str, severity: str, page_url: str, evidence: str, handling: str) -> FlowBarrierFinding:
    return FlowBarrierFinding(
        key=key,
        label=key.replace("_", " ").title(),
        severity=severity,
        page_url=page_url,
        evidence=evidence,
        handling=handling,
    )


def _unique_findings(finding_groups: Any) -> list[FlowBarrierFinding]:
    unique: dict[tuple[str, str], FlowBarrierFinding] = {}
    for group in finding_groups:
        for finding in group:
            unique.setdefault((finding.key, finding.page_url), finding)
    return sorted(unique.values(), key=lambda item: (_severity_rank(item.severity), item.key, item.page_url))[:MAX_BARRIER_FINDINGS]


def _summary(findings: list[FlowBarrierFinding]) -> dict[str, Any]:
    return {
        "total": len(findings),
        "high": _severity_count(findings, HIGH_SEVERITY),
        "medium": _severity_count(findings, MEDIUM_SEVERITY),
        "low": _severity_count(findings, LOW_SEVERITY),
        "keys": sorted({finding.key for finding in findings}),
    }


def _severity_count(findings: list[FlowBarrierFinding], severity: str) -> int:
    return sum(1 for finding in findings if finding.severity == severity)


def _severity_rank(severity: str) -> int:
    return {HIGH_SEVERITY: 0, MEDIUM_SEVERITY: 1, LOW_SEVERITY: 2}.get(severity, 3)


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item or "").strip() for item in value[:20] if str(item or "").strip()]
