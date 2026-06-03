#!/usr/bin/env python3
"""Aggregate bootstrap-approved forward paper pilots (B_flip, inverse_ml BTC)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "reports" / "bootstrap_forward_stats_latest.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PILOT_DIR = ROOT / "verified_strategies" / "paper_pilot"

LAB = {
    "B_flip_PriceRocMeanReversion": {
        "verdict": "BOOTSTRAP_PASS",
        "is_pf": 35.91,
        "is_n": 157,
        "pf_lo_95": 21.21,
        "note": "PR #482 legit — forward virtual only",
    },
    "inverse_ml_enhanced_BTCUSDT_15m_D": {
        "verdict": "BOOTSTRAP_PASS",
        "is_pf": 34.46,
        "is_n": 65,
        "pf_lo_95": 15.97,
        "note": "PR #482 legit — forward virtual only",
    },
}


def _load_state(name: str) -> dict:
    path = PILOT_DIR / name
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def build_report() -> dict:
    b_flip = _load_state("b_flip_price_roc_state.json")
    inv = _load_state("inverse_ml_btc_state.json")
    sleeves = {
        "b_flip_price_roc": {
            "lab_bootstrap": LAB["B_flip_PriceRocMeanReversion"],
            "forward": b_flip.get("forward") or {"error": "no_tick_yet"},
            "open_position": b_flip.get("open_position"),
            "recommend_enable": False,
            "flag": "B_FLIP_PRICEROC_ENABLED",
        },
        "inverse_ml_btc_15m": {
            "lab_bootstrap": LAB["inverse_ml_enhanced_BTCUSDT_15m_D"],
            "forward": inv.get("forward") or {"error": "no_tick_yet"},
            "open_position": inv.get("open_position"),
            "recommend_enable": False,
            "flag": "INVERSE_ML_BTC_15M_ENABLED",
        },
    }
    any_ready = any(
        (s.get("forward") or {}).get("promotion_ready") for s in sleeves.values()
    )
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "forward_n_target": 100,
        "any_promotion_ready": any_ready,
        "sleeves": sleeves,
        "blocked_from_production": [
            "money_ready_verdict freeze_promotions",
            "no scanner env flags until forward n>=100",
        ],
        "refs": ["updates/2026-06-02-suspicious-pass-investigation.md", "PR #482"],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    report = build_report()
    print(json.dumps(report, indent=2))
    if args.write:
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
        audit = ROOT / "audit_dashboard" / "data" / "bootstrap_forward_stats.json"
        audit.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote {OUT_PATH}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())