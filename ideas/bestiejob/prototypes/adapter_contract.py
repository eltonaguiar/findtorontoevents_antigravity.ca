#!/usr/bin/env python3
"""Adapter interface contract + stubs for BESTIEJOB lead discovery.

Design goals (per ADAPTER_COVERAGE_PLAN.md / runbook):
- `plan(config)` -> endpoints/notes with NO network access.
- `scan(config, limits)` -> bounded lead records (permissioned, rate-limited) with
  provenance fields compatible with normalize_lead.py.
- Adapters emit leads only (`status=lead_only`); verification/dedupe/publish are downstream.
- No secrets in code; config supplied at runtime from approved sources.

This module defines lightweight dataclasses/protocol-like base classes and no-op stubs.
Extend per adapter (Workday CXS, civic boards, etc.) behind explicit config and rights checks.

No deps, no network.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class AdapterLimits:
    max_pages: int = 3
    max_details: int = 15
    delay_seconds: float = 2.0
    timeout_seconds: int = 12
    max_payload_bytes: int = 20_000_000

    def bounded(self) -> "AdapterLimits":
        return AdapterLimits(
            max_pages=min(max(int(self.max_pages), 1), 20),
            max_details=min(max(int(self.max_details), 1), 100),
            delay_seconds=min(max(float(self.delay_seconds), 1.0), 60.0),
            timeout_seconds=min(max(int(self.timeout_seconds), 1), 60),
            max_payload_bytes=min(max(int(self.max_payload_bytes), 1), 50_000_000),
        )


@dataclass
class SourceConfig:
    source_id: str
    adapter: str
    organization: Optional[str] = None
    board_token: Optional[str] = None
    tenant: Optional[str] = None
    base_url: Optional[str] = None
    country: Optional[str] = None
    regions: List[str] = field(default_factory=list)
    rights: str = "unknown"  # manual_discovery|permitted_api_private|own_site_attributed|redistribution_approved|unknown
    enabled: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Lead:
    source: str
    publisher: Optional[str]
    ats: str
    posting_id: str
    title: str
    posting_url: str
    apply_url: Optional[str] = None
    location_as_listed: str = ""
    mode_as_listed: str = ""
    description: str = ""
    time_field: str = ""
    time_value: str = ""
    candidate_tracks: List[str] = field(default_factory=list)
    status: str = "lead_only"
    observed_at_utc: Optional[str] = None
    req_id: Optional[str] = None
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> Dict[str, Any]:
        d = asdict(self)
        # normalize_lead accepts candidate_tracks as list or ';' string
        return d


class BaseAdapter:
    name: str = "base"

    def validate_config(self, config: SourceConfig) -> List[str]:
        errors = []
        if not config.source_id:
            errors.append("missing source_id")
        if not config.adapter:
            errors.append("missing adapter")
        if config.rights == "unknown":
            errors.append("rights unknown (do not publish; discovery/plan only)")
        return errors

    def plan(self, config: SourceConfig) -> Dict[str, Any]:
        """Return planned endpoints/actions without performing network IO."""
        return {
            "adapter": self.name,
            "source_id": config.source_id,
            "enabled": config.enabled,
            "rights": config.rights,
            "network": "none",
            "actions": [],
            "notes": ["stub adapter: implement plan() with documented endpoints only"],
        }

    def scan(self, config: SourceConfig, limits: Optional[AdapterLimits] = None) -> Iterable[Lead]:
        """Yield lead records. Stub: returns no leads. Implement with bounded, permissioned IO."""
        if not config.enabled:
            return []
        return []


class WorkdayCxsAdapterStub(BaseAdapter):
    name = "workday_cxs_stub"

    def plan(self, config: SourceConfig) -> Dict[str, Any]:
        tenant = config.tenant or config.extra.get("tenant") or "<tenant>"
        site = config.board_token or config.extra.get("site") or "<site>"
        endpoint = f"https://{tenant}.wdX.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs" if tenant != "<tenant>" else None
        return {
            "adapter": self.name,
            "source_id": config.source_id,
            "enabled": config.enabled,
            "rights": config.rights,
            "network": "none (stub)",
            "endpoints": [endpoint] if endpoint else [],
            "actions": [
                "POST search with bounded pagination/limit (when implemented, permissioned)",
                "GET/derive posting URLs per job; capture postedOn/timeType/locations",
            ],
            "notes": [
                "Tenant/site and request shape vary; require verified config per employer.",
                "Must emit lead_only records with observed_at_utc and time_field semantics.",
            ],
        }


def example_lead() -> Lead:
    return Lead(
        source="example_source",
        publisher="Example Org",
        ats="example_adapter",
        posting_id="REQ-123",
        req_id="REQ-123",
        title="ServiceNow Developer",
        posting_url="https://careers.example.org/jobs/REQ-123",
        location_as_listed="Toronto, ON",
        mode_as_listed="Hybrid",
        description="Build ITSM workflows, GlideRecord integrations. CSA preferred.",
        candidate_tracks=["ServiceNow"],
        status="lead_only",
        provenance={"adapter_contract": "v0"},
    )
