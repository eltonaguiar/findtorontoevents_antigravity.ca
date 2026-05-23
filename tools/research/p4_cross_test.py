"""P4 cross-test runner — overlap between candidate specs and shipped strategies.

v1 STUB: deterministic ρ from spec_id × shipped-strategy-name hash, plus a
symbol-universe Jaccard overlap from `audit_dashboard/data/dashboard_data.json`
when available. Real signal-series Pearson lands in PR 2 alongside the
BacktestEngine wire-in.

Verdict thresholds:
  ρ > 0.7 AND overlap > 60% → DUPLICATE     (reject)
  ρ > 0.5 AND overlap > 40% → OVERLAP_WARNING (allow, flag)
  else                       → INDEPENDENT
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .schemas import CrossTestResult, StrategySpec

_DASHBOARD_DATA = (
    Path(__file__).resolve().parents[2]
    / "audit_dashboard"
    / "data"
    / "dashboard_data.json"
)


def _stable_rho(spec_id: str, strat_name: str) -> float:
    """Deterministic pseudo-ρ in [-0.95, 0.95]."""
    h = hashlib.md5(f"{spec_id}::{strat_name}".encode()).digest()
    return round(((h[0] / 255) * 1.9 - 0.95), 2)


def _load_shipped_strategies() -> list[dict]:
    """Pull strategy names + symbols from the live dashboard payload.

    Falls back to empty list if file missing — harness still runs but
    every candidate looks INDEPENDENT (acceptable v1 behavior).
    """
    if not _DASHBOARD_DATA.exists():
        return []
    try:
        data = json.loads(_DASHBOARD_DATA.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    systems = data.get("systems") or []
    out = []
    for s in systems:
        if not isinstance(s, dict):
            continue
        out.append(
            {
                "name": s.get("name") or s.get("id") or "unknown",
                "symbols": set(s.get("symbols") or []),
            }
        )
    return out


def _symbol_overlap(spec_syms: list[str], shipped_syms: set) -> float:
    if not spec_syms or not shipped_syms:
        return 0.0
    a = {str(x).upper() for x in spec_syms}
    b = {str(x).upper() for x in shipped_syms}
    inter = a & b
    union = a | b
    return round(100.0 * len(inter) / len(union), 1) if union else 0.0


def cross_test(spec: StrategySpec) -> CrossTestResult:
    shipped = _load_shipped_strategies()
    neighbors: list[dict] = []
    max_rho = 0.0
    max_rho_strat = ""
    max_overlap = 0.0
    for s in shipped:
        rho = _stable_rho(spec.spec_id, s["name"])
        overlap = _symbol_overlap(spec.universe, s["symbols"])
        neighbors.append(
            {
                "strategy": s["name"],
                "rho": rho,
                "symbol_overlap_pct": overlap,
            }
        )
        if abs(rho) > abs(max_rho):
            max_rho = rho
            max_rho_strat = s["name"]
            max_overlap = overlap
    # Top 3 by |rho|
    neighbors.sort(key=lambda r: abs(r["rho"]), reverse=True)
    neighbors = neighbors[:3]

    if abs(max_rho) > 0.7 and max_overlap > 60:
        verdict = "DUPLICATE"
    elif abs(max_rho) > 0.5 and max_overlap > 40:
        verdict = "OVERLAP_WARNING"
    else:
        verdict = "INDEPENDENT"

    return CrossTestResult(
        spec_id=spec.spec_id,
        max_rho=max_rho,
        max_rho_strategy=max_rho_strat or "(no shipped strategies found)",
        symbol_overlap_pct=max_overlap,
        verdict=verdict,
        nearest_neighbors=neighbors,
    )


def cross_test_all(specs: list[StrategySpec]) -> list[CrossTestResult]:
    return [cross_test(s) for s in specs]
