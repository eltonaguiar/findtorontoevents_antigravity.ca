"""
M-039: Cross-commodity spread momentum research module.

Tests the crude/natgas pair spread as a trading signal. The spread between
energy commodities (WTI crude CL=F vs natural gas NG=F) historically captures
supply/demand divergences in the energy complex.

Academic basis: Gorton & Rouwenhorst (2006) — commodity term structure and
cross-commodity correlations; Bessembinder (1992) — predictability of commodity
futures prices. Energy spread signals have documented Sharpe ~0.6-0.8 in
academic literature (Casassus & Collin-Dufresne, 2005).

Usage (research only — OPT-IN, no production callers):
    python tools/research/commodity_spread_momentum.py
    python tools/research/commodity_spread_momentum.py --period 90 --min-n 30

Wiring plan: if this passes H-004 acceptance criteria (deflated Sharpe > 0.6),
wire as additional signal into alpha_engine/smart_picks_engine.py as an
opt-in strategy (COMMODITY_SPREAD_MOMENTUM_ENABLED=1 env var).
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CLOSED_PATH = REPO_ROOT / "alpha_engine" / "data" / "closed_picks.json"

SPREAD_PAIRS = [
    {
        "name": "CL_NG_energy_spread",
        "long_symbol": "CL=F",
        "short_symbol": "NG=F",
        "description": "WTI Crude (long) vs Natural Gas (short) — energy complex divergence",
        "economic_prior": "Oil/gas substitution; refinery demand shocks affect crude more than gas short-term",
    },
    {
        "name": "GC_SI_gold_silver_ratio",
        "long_symbol": "GC=F",
        "short_symbol": "SI=F",
        "description": "Gold (long) vs Silver (short) — precious metals ratio reversion",
        "economic_prior": "Gold/silver ratio reverts to historical mean ~70x; ratio >85 signals silver undervalued",
    },
    {
        "name": "CT_KC_soft_spread",
        "long_symbol": "CT=F",
        "short_symbol": "KC=F",
        "description": "Cotton (long) vs Coffee (short) — agricultural soft commodities",
        "economic_prior": "EM currency exposure correlation; both affected by Brazil/India FX but with different lag",
    },
]


def _load_picks(path: Path = CLOSED_PATH) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_dt(s: Any) -> datetime | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(str(s)[:26].strip(), fmt.replace("%z", "").strip())
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def _is_win(pick: dict) -> bool | None:
    status = str(pick.get("status") or "").upper()
    pnl = pick.get("pnl_pct")
    WIN = {"WIN", "TARGET_HIT", "TP_HIT", "CLOSED_WIN"}
    LOSS = {"LOSS", "SL_HIT", "STOPPED", "CLOSED_LOSS", "EXPIRED"}
    if status in WIN:
        return True
    if status in LOSS:
        return False
    if pnl is not None:
        try:
            return float(pnl) > 0
        except (TypeError, ValueError):
            pass
    return None


def analyze_spread_picks(
    picks: list[dict],
    pair: dict,
    lookback_days: int = 90,
    min_n: int = 10,
) -> dict:
    """
    Analyze existing closed picks for a symbol pair to estimate spread viability.

    Since we don't yet run a spread strategy, this analyzes the component
    symbols independently to estimate if a spread-based signal would add value.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=lookback_days)

    long_sym = pair["long_symbol"]
    short_sym = pair["short_symbol"]

    long_picks = []
    short_picks = []

    for p in picks:
        sym = p.get("symbol", "")
        dt = _parse_dt(p.get("closed_at") or p.get("exit_date") or p.get("resolved_at"))
        if dt is None or dt < cutoff:
            continue
        outcome = _is_win(p)
        if outcome is None:
            continue
        pnl = p.get("pnl_pct")
        if pnl is None:
            continue
        try:
            pnl_f = float(pnl)
        except (TypeError, ValueError):
            continue

        if sym == long_sym:
            long_picks.append({"outcome": outcome, "pnl": pnl_f, "direction": p.get("direction")})
        elif sym == short_sym:
            short_picks.append({"outcome": outcome, "pnl": pnl_f, "direction": p.get("direction")})

    def _stats(picks_list: list[dict]) -> dict:
        if not picks_list:
            return {"n": 0, "wr": None, "avg_pnl": None}
        wins = sum(1 for p in picks_list if p["outcome"])
        pnls = [p["pnl"] for p in picks_list]
        return {
            "n": len(picks_list),
            "wr": round(wins / len(picks_list), 4),
            "avg_pnl": round(sum(pnls) / len(pnls), 4),
        }

    long_stats = _stats(long_picks)
    short_stats = _stats(short_picks)

    # Estimate spread PnL: long - short (both taken simultaneously)
    # If both symbols have sufficient data, compute synthetic spread return
    spread_pnl = None
    if long_stats["avg_pnl"] is not None and short_stats["avg_pnl"] is not None:
        spread_pnl = round(long_stats["avg_pnl"] - short_stats["avg_pnl"], 4)

    sufficient_data = (
        long_stats["n"] >= min_n and short_stats["n"] >= min_n
    )

    verdict = "INSUFFICIENT_DATA"
    if sufficient_data:
        if spread_pnl is not None and spread_pnl > 0.005:
            verdict = "PROMISING"
        elif spread_pnl is not None and spread_pnl < -0.005:
            verdict = "NEGATIVE"
        else:
            verdict = "FLAT"

    return {
        "pair": pair["name"],
        "long_symbol": long_sym,
        "short_symbol": short_sym,
        "description": pair["description"],
        "economic_prior": pair["economic_prior"],
        "lookback_days": lookback_days,
        "long": long_stats,
        "short": short_stats,
        "synthetic_spread_pnl": spread_pnl,
        "verdict": verdict,
        "notes": (
            "Synthetic spread: uses independent picks, not co-timed pairs. "
            "For real spread trading, picks must enter/exit simultaneously."
            if sufficient_data else
            "Insufficient closed picks in lookback window for this pair."
        ),
    }


def run_spread_analysis(
    picks: list[dict] | None = None,
    lookback_days: int = 90,
    min_n: int = 10,
) -> dict:
    if picks is None:
        picks = _load_picks()

    results = []
    for pair in SPREAD_PAIRS:
        result = analyze_spread_picks(picks, pair, lookback_days, min_n)
        results.append(result)

    promising = [r["pair"] for r in results if r["verdict"] == "PROMISING"]
    negative = [r["pair"] for r in results if r["verdict"] == "NEGATIVE"]
    flat = [r["pair"] for r in results if r["verdict"] == "FLAT"]
    insufficient = [r["pair"] for r in results if r["verdict"] == "INSUFFICIENT_DATA"]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": {"lookback_days": lookback_days, "min_n_per_symbol": min_n},
        "pairs": results,
        "summary": {
            "promising": promising,
            "negative": negative,
            "flat": flat,
            "insufficient_data": insufficient,
        },
        "next_steps": (
            "Register promising pairs in reports/hypothesis_registry.json (M-107) "
            "before running any formal backtest. Use deflated Sharpe as acceptance criterion."
        ),
    }


def print_report(result: dict) -> None:
    print(f"\n{'='*60}")
    print(f"Cross-Commodity Spread Analysis (M-039)")
    print(f"Generated: {result['generated_at']}")
    print(f"Config: {result['config']['lookback_days']}d lookback, "
          f"min_n={result['config']['min_n_per_symbol']}")
    print(f"{'='*60}\n")

    verdicts = {"PROMISING": "✅", "FLAT": "—", "NEGATIVE": "❌", "INSUFFICIENT_DATA": "🔵"}
    for r in result["pairs"]:
        icon = verdicts.get(r["verdict"], "?")
        long_n = r["long"]["n"]
        short_n = r["short"]["n"]
        spread = r["synthetic_spread_pnl"]
        spread_str = f"spread_pnl={spread:+.4f}" if spread is not None else "spread_pnl=N/A"
        print(f"{icon} {r['pair']:<35} {r['verdict']:<18} "
              f"n={long_n}/{short_n} {spread_str}")
        print(f"   {r['description']}")

    print(f"\n{'─'*60}")
    s = result["summary"]
    print(f"PROMISING ({len(s['promising'])}): {', '.join(s['promising']) or 'none'}")
    print(f"NEGATIVE  ({len(s['negative'])}):  {', '.join(s['negative']) or 'none'}")
    print(f"FLAT      ({len(s['flat'])}):  {', '.join(s['flat']) or 'none'}")
    print(f"NO DATA   ({len(s['insufficient_data'])}): "
          f"{', '.join(s['insufficient_data']) or 'none'}")
    print(f"\nNext steps: {result['next_steps']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="M-039: Cross-commodity spread momentum")
    parser.add_argument("--period", type=int, default=90, help="Lookback in days")
    parser.add_argument("--min-n", type=int, default=10, help="Min picks per symbol")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    picks = _load_picks()
    result = run_spread_analysis(picks, args.period, args.min_n)

    out = REPO_ROOT / "reports" / "commodity_spread_analysis.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_report(result)
        print(f"\nJSON written: {out}")


if __name__ == "__main__":
    main()
