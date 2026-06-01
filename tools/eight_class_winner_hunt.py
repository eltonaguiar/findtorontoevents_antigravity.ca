#!/usr/bin/env python3
"""Run backtests + live emitters; report per-class winners (TESTING_PROTOCOL tiers).

Usage:
  python3 tools/eight_class_winner_hunt.py
  python3 tools/eight_class_winner_hunt.py --emit
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TIER2 = {"min_pf": 1.5, "min_wr": 50.0}
TIER3 = {"min_pf": 1.2, "min_wr": 45.0}

BACKTEST_CMDS = [
    ("BOND", ["python3", "tools/backtest_bond_credit_spread_overlay.py"],
     "audit_dashboard/data/bond_credit_spread_overlay_backtest.json", "baseline_no_overlay"),
    ("FUTURES", ["python3", "tools/backtest_futures_ts_momentum.py"],
     "audit_dashboard/data/futures_ts_momentum_backtest.json", "long_short"),
    ("EQUITY", ["python3", "tools/equity_baby_strategies_backtest.py"],
     "audit_dashboard/data/equity_baby_strategies_backtest.json", "equity_sector_rotation_momentum"),
    ("ETF", ["python3", "tools/backtest_etf_rotation_vix_regime.py"],
     "audit_dashboard/data/etf_rotation_vix_regime_backtest.json", "baseline_no_filter"),
]


def _load_json(rel: str) -> dict:
    p = ROOT / rel
    if not p.exists():
        return {}
    with p.open() as f:
        return json.load(f)


def _tier(pf: float, wr: float) -> str:
    if pf >= TIER2["min_pf"] and wr >= TIER2["min_wr"]:
        return "TIER_2"
    if pf >= TIER3["min_pf"] and wr >= TIER3["min_wr"]:
        return "TIER_3"
    if pf >= 1.0:
        return "REHAB"
    return "FAIL"


def main() -> None:
    emit = "--emit" in sys.argv
    print("# Eight-class winner hunt", file=sys.stderr)

    for _cls, cmd, _, _key in BACKTEST_CMDS:
        print(f"# backtest {_cls}...", file=sys.stderr)
        subprocess.run(cmd, cwd=ROOT, check=False)

    print("# backtest CHEAP_STOCKS...", file=sys.stderr)
    subprocess.run(["python3", "tools/backtest_cheap_stock_momentum.py"], cwd=ROOT, check=False)
    print("# backtest IPO (post-listing long)...", file=sys.stderr)
    subprocess.run(["python3", "tools/backtest_ipo_post_listing_long.py"], cwd=ROOT, check=False)

    # Parse backtest JSONs
    bond = _load_json("audit_dashboard/data/bond_credit_spread_overlay_backtest.json")
    futures = _load_json("audit_dashboard/data/futures_ts_momentum_backtest.json")
    equity = _load_json("audit_dashboard/data/equity_baby_strategies_backtest.json")
    etf = _load_json("audit_dashboard/data/etf_rotation_vix_regime_backtest.json")

    winners = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "classes": {},
    }

    b = bond.get("baseline_no_overlay") or bond.get("baseline") or {}
    winners["classes"]["BOND"] = {
        "strategy": "bond_hyg_lqd_momentum_winner",
        "pf": b.get("profit_factor"),
        "wr": b.get("win_rate_pct"),
        "tier": _tier(float(b.get("profit_factor") or 0), float(b.get("win_rate_pct") or 0)),
        "evidence": "bond_credit_spread_overlay_backtest.json",
    }

    f = futures.get("long_short_results") or futures.get("long_short") or futures
    winners["classes"]["FUTURES"] = {
        "strategy": "futures_tsmom_winner",
        "pf": f.get("profit_factor"),
        "wr": f.get("win_rate_pct"),
        "tier": _tier(float(f.get("profit_factor") or 0), float(f.get("win_rate_pct") or 0)),
        "evidence": "futures_ts_momentum_backtest.json",
    }

    eq = equity.get("equity_sector_rotation_momentum") or {}
    eq_r = eq.get("results") or eq
    winners["classes"]["EQUITY"] = {
        "strategy": "equity_sector_rotation",
        "pf": eq_r.get("profit_factor"),
        "wr": eq_r.get("win_rate_pct"),
        "tier": _tier(float(eq_r.get("profit_factor") or 0), float(eq_r.get("win_rate_pct") or 0)),
        "evidence": "equity_baby_strategies_backtest.json",
    }

    e = etf.get("baseline_no_filter") or etf.get("baseline") or {}
    winners["classes"]["ETF"] = {
        "strategy": "etf_sector_momentum_rotation",
        "pf": e.get("profit_factor"),
        "wr": e.get("win_rate_pct"),
        "tier": _tier(float(e.get("profit_factor") or 0), float(e.get("win_rate_pct") or 0)),
        "evidence": "etf_rotation_vix_regime_backtest.json",
    }

    winners["classes"]["CRYPTO"] = {
        "strategy": "st_fear_greed_contrarian_winner",
        "pf": 2.50,
        "wr": 58.1,
        "tier": "TIER_2",
        "evidence": "walkforward_results.json (n=344)",
        "note": "walk-forward validated, not re-run here",
    }

    winners["classes"]["COMMODITY"] = {
        "strategy": "commodity_seasonal_planting_harvest",
        "pf": 1.365,
        "wr": 50.34,
        "tier": "TIER_3",
        "evidence": "backtest_commodity_seasonal_2026_05_31_2358Z.md",
    }

    winners["classes"]["FOREX"] = {
        "strategy": "fx_carry_vix_regime",
        "pf": None,
        "wr": None,
        "tier": "REHAB",
        "evidence": "VIX-gated carry (live); backtest COT synthetic PF 1.04 only",
        "next_rehab": "harness fx_carry on 5y resolved before production size",
    }

    winners["classes"]["PREDICTION_MARKETS"] = {
        "strategy": "polymarket_bts_consensus",
        "tier": "PAPER_PILOT",
        "evidence": "live API when markets available",
    }

    cheap = _load_json("audit_dashboard/data/cheap_stock_momentum_backtest.json")
    winners["classes"]["CHEAP_STOCKS"] = {
        "strategy": "cheap_stock_cross_momentum_winner",
        "pf": cheap.get("profit_factor"),
        "wr": cheap.get("win_rate_pct"),
        "tier": _tier(float(cheap.get("profit_factor") or 0), float(cheap.get("win_rate_pct") or 0)),
        "evidence": "cheap_stock_momentum_backtest.json",
        "n": cheap.get("n_trades"),
    }

    ipo = _load_json("audit_dashboard/data/ipo_post_listing_long_backtest.json")
    winners["classes"]["IPO"] = {
        "strategy": "ipo_post_listing_momentum_long",
        "pf": ipo.get("profit_factor"),
        "wr": ipo.get("win_rate_pct"),
        "tier": _tier(float(ipo.get("profit_factor") or 0), float(ipo.get("win_rate_pct") or 0)),
        "evidence": "ipo_post_listing_long_backtest.json",
        "n": ipo.get("n_trades"),
        "note": "lockup-expiry SHORT FAILED — do not use ipo_lockup_strategy for production",
    }

    out = ROOT / "reports" / f"eight_class_winners_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
    out.write_text(json.dumps(winners, indent=2), encoding="utf-8")
    print(json.dumps(winners, indent=2))

    if emit:
        from alpha_engine.eight_class_flagship_strategies import generate_all_flagship_picks
        picks = generate_all_flagship_picks()
        batch = {
            "batch_id": f"winners_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}",
            "num_picks": len(picks),
            "classes": sorted({p["asset_class"] for p in picks}),
            "picks": picks,
        }
        dest = ROOT / "alpha_engine" / "data" / f"winning_picks_{batch['batch_id']}.json"
        dest.write_text(json.dumps(batch, indent=2), encoding="utf-8")
        print(f"# emitted {len(picks)} picks -> {dest}", file=sys.stderr)


if __name__ == "__main__":
    main()
