"""Stable JSON schemas for the research orchestrator.

These keys are part of the orchestrator contract — renaming breaks
downstream HTML render + dashboard ingest. Bump `SCHEMA_VERSION` on
breaking change.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

SCHEMA_VERSION = "v1"


@dataclass
class Citation:
    url: str
    access_date: str  # ISO date YYYY-MM-DD
    title: str = ""
    author: str = ""
    year: str = ""
    claim: str = ""
    evidence_strength: str = "anec"  # anec | empirical | peer-reviewed
    asset_class: str = ""
    verified: bool = False  # filled by verify_citations.py
    low_trust: bool = False  # filled when domain off the allowlist


@dataclass
class StrategySpec:
    spec_id: str
    asset_class: str
    entry: str
    exit: str
    sizing: str
    universe: list[str]
    regime_filter: str = ""
    source_refs: list[str] = field(default_factory=list)  # URLs from Citation set
    proposed_by_engine: str = ""


@dataclass
class BacktestResult:
    spec_id: str
    pf: float
    wr: float
    mdd: float
    sharpe: float
    n_trades: int
    walk_forward_folds: list[dict[str, Any]] = field(default_factory=list)
    data_window_start: str = ""
    data_window_end: str = ""
    cost_assumption: str = ""
    notes: str = ""


@dataclass
class CrossTestResult:
    spec_id: str
    max_rho: float
    max_rho_strategy: str
    symbol_overlap_pct: float
    verdict: str  # DUPLICATE | OVERLAP_WARNING | INDEPENDENT
    nearest_neighbors: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SynthesisRow:
    spec_id: str
    verdict: str  # GO | NO_EDGE | MIXED
    rationale: str
    wiring_plan: str = ""
    engine_votes: dict[str, str] = field(default_factory=dict)


@dataclass
class RunSummary:
    asset_class: str
    run_ts_utc: str
    schema_version: str = SCHEMA_VERSION
    verdict: str = "PENDING"  # GO | NO_EDGE | MIXED | PENDING | ABORTED
    n_citations_verified: int = 0
    n_citations_hallucinated: int = 0
    n_candidates: int = 0
    n_backtested: int = 0
    n_independent_after_cross_test: int = 0
    n_v3b_validated: int = 0
    n_v3b_rejected: int = 0
    cost_usd: float = 0.0
    wall_time_sec: float = 0.0
    aborted: bool = False
    abort_reason: str = ""


def to_dict(obj) -> dict:
    """Convert dataclass to dict for JSON serialization."""
    return asdict(obj) if hasattr(obj, "__dataclass_fields__") else dict(obj)
