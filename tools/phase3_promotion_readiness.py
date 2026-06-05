#!/usr/bin/env python3
"""Phase 3 promotion readiness — unified gate check for first PROMOTED_STRATEGIES entry.

Reads pilot state files + forward stats + tournament shadow. Does NOT mutate
promotion_gate.PROMOTED_STRATEGIES (operator-only when criteria pass).

Usage:
  python3 tools/phase3_promotion_readiness.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT_REPORT = ROOT / "reports/phase3_promotion_readiness.json"
OUT_AUDIT = ROOT / "audit_dashboard/data/phase3_promotion_readiness.json"


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _check_sleeve(
    sleeve_id: str,
    *,
    forward_n: int,
    pf: float | None,
    wr_pct: float | None,
    day_count: int | None = None,
    min_n: int = 100,
    min_pf: float = 1.5,
    min_wr: float = 50.0,
    min_days: int | None = None,
    extra_blockers: list[str] | None = None,
) -> dict:
    blockers = list(extra_blockers or [])
    if min_days is not None and (day_count or 0) < min_days:
        blockers.append(f"day_count {day_count or 0} < {min_days}")
    if forward_n < min_n:
        blockers.append(f"n {forward_n} < {min_n}")
    if pf is None:
        blockers.append("pf unavailable")
    elif pf < min_pf:
        blockers.append(f"pf {pf} < {min_pf}")
    if wr_pct is None:
        blockers.append("wr unavailable")
    elif wr_pct < min_wr:
        blockers.append(f"wr {wr_pct}% < {min_wr}%")
    return {
        "sleeve": sleeve_id,
        "forward_n": forward_n,
        "pf": pf,
        "win_rate_pct": wr_pct,
        "day_count": day_count,
        "blockers": blockers,
        "phase3_ready": len(blockers) == 0,
    }


def build_report() -> dict:
    etf_stats = _load(ROOT / "reports/etf_forward_stats_latest.json")
    etf_fwd = etf_stats.get("paper_pilot_forward") or {}
    pilot = _load(ROOT / "audit_dashboard/data/pilot_forward_dashboard.json")
    lux = _load(ROOT / "verified_strategies/paper_pilot/luxalgo_confluence_state.json")
    ada = _load(ROOT / "verified_strategies/paper_pilot/inverse_ml_ada_state.json")
    macd = _load(ROOT / "verified_strategies/paper_pilot/macd_rsi_m048_state.json")
    tournament = _load(ROOT / "reports/tournament_shadow_book.json")
    ada_db = ada.get("forward_db") or {}
    bootstrap_ada = (
        (pilot.get("bootstrap_forward") or {})
        .get("sleeves", {})
        .get("inverse_ml_ada_15m", {})
        .get("forward")
        or {}
    )
    ada_n = max(
        int(ada_db.get("n_closed") or 0),
        int(bootstrap_ada.get("n_closed") or 0),
    )
    ada_pf = ada_db.get("pf") or bootstrap_ada.get("pf")
    ada_wr = ada_db.get("wr") if ada_db.get("wr") is not None else bootstrap_ada.get("wr")
    t_combined = tournament.get("combined") or {}

    candidates = [
        _check_sleeve(
            "etf_verified_dual_momentum",
            forward_n=int(etf_fwd.get("n_closed") or 0),
            pf=float(etf_fwd.get("pf") or 0) or None,
            wr_pct=float(etf_fwd.get("wr") or 0) * 100 if etf_fwd.get("wr") is not None else None,
            extra_blockers=list(etf_fwd.get("gates") or []),
        ),
        _check_sleeve(
            "luxalgo_confluence",
            forward_n=int(lux.get("rolling_30d_n_closed") or 0),
            pf=lux.get("rolling_30d_pf"),
            wr_pct=(lux.get("rolling_30d_wr") or 0) * 100 if lux.get("rolling_30d_wr") is not None else None,
            day_count=int(lux.get("day_count") or 0),
            min_n=50,
            min_days=30,
        ),
        _check_sleeve(
            "inverse_ml_ada_15m",
            forward_n=ada_n,
            pf=float(ada_pf) if ada_pf is not None else None,
            wr_pct=float(ada_wr) * 100 if ada_wr is not None else None,
            extra_blockers=(
                ["bootstrap n=36 vs mysql dedupe n=2 — reconcile strategy_id filter"]
                if ada_n >= 30 and int(ada_db.get("n_closed") or 0) < 10
                else []
            ),
        ),
        _check_sleeve(
            "macd_rsi_m048",
            forward_n=int(macd.get("rolling_30d_n_closed") or 0),
            pf=macd.get("rolling_30d_pf"),
            wr_pct=(macd.get("rolling_30d_wr") or 0) * 100 if macd.get("rolling_30d_wr") is not None else None,
            day_count=int(macd.get("day_count") or 0),
            min_n=30,
            min_days=30,
        ),
        _check_sleeve(
            "tournament_grok3_shadow",
            forward_n=int(t_combined.get("n") or 0),
            pf=t_combined.get("profit_factor"),
            wr_pct=t_combined.get("win_rate_pct"),
            extra_blockers=["shadow_only — never production merge"],
        ),
    ]

    ready = [c for c in candidates if c["phase3_ready"]]

    tier2_lux = {}
    try:
        from audit_trail.promotion_gate import evaluate_forward_tier2
        pnls = [float(x) for x in (lux.get("rolling_30d_pnls") or []) if x is not None]
        if pnls:
            tier2_lux = evaluate_forward_tier2(pnls)
    except Exception as exc:
        tier2_lux = {"error": str(exc)}

    try:
        from audit_trail.promotion_gate import PROMOTED_STRATEGIES
        promoted = sorted(PROMOTED_STRATEGIES)
    except ImportError:
        promoted = []

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": 3,
        "promoted_strategies": promoted,
        "promoted_count": len(promoted),
        "money_ready_target": "1 strategy in PROMOTED_STRATEGIES, 1 class at Tier-2",
        "candidates": candidates,
        "phase3_ready_count": len(ready),
        "phase3_ready_sleeves": [c["sleeve"] for c in ready],
        "first_real_money_candidate": (
            ready[0]["sleeve"]
            if ready
            else (
                "inverse_ml_ada_15m"
                if ada_n >= int(bootstrap_ada.get("n_closed") or 0)
                and int(bootstrap_ada.get("n_closed") or 0) >= 30
                else "etf_verified_dual_momentum (forward clock running)"
            )
        ),
        "inverse_ml_ada_bootstrap_n": int(bootstrap_ada.get("n_closed") or 0),
        "tier2_luxalgo_confluence": tier2_lux,
        "operator_note": (
            "Empty PROMOTED_STRATEGIES is intentional until forward gates pass. "
            "Do not size real money on aggregate /audit class WR."
        ),
    }


def main() -> int:
    report = build_report()
    payload = json.dumps(report, indent=2)
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_AUDIT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(payload, encoding="utf-8")
    OUT_AUDIT.write_text(payload, encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
