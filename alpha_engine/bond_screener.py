#!/usr/bin/env python3
"""Bond / fixed-income screener — duration + credit + real yield.

Passive core allocation tool (daily resolution, no intraday TP/SL).
Screens investment-grade bond ETFs against hard gates.

Hard gates (ALL must pass):
  - Expense ratio ≤ 0.10%
  - AUM ≥ $1B
  - Tracking error ≤ 0.25%
  - Track record ≥ 10 years
  - Duration within target range for current rate regime

Signal logic:
  - Real yield (TIPS) > 1% → attractive → LONG duration
  - Real yield < 0% → avoid → SHORT duration (or cash)
  - Credit spread (IG vs Treasury) > historical median → buy credit
  - Yield curve slope (2s10s) < 0 → recession risk → overweight long bonds

Universe: AGG, BND, LQD, TLT, IEF, SHY, TIP, VGIT, VGLT
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)

HARD_GATES = {
    "expense_ratio": 0.0010,       # 0.10%
    "min_aum": 1_000_000_000,     # $1B
    "max_tracking_error": 0.0025,  # 0.25%
    "min_track_record_years": 10,
    "max_duration_deviation": 2.0,  # ±2 years from target
}

STARTER_UNIVERSE = ["AGG", "BND", "LQD", "TLT", "IEF", "SHY", "TIP", "VGIT", "VGLT"]

# Duration targets by rate regime
DURATION_TARGETS = {
    "rising_rates": 3.0,   # short duration
    "falling_rates": 8.0,   # long duration
    "neutral": 5.0,         # intermediate
}


def screen_bond(fund: dict) -> dict:
    """Screen a single bond fund/ETF against hard gates."""
    gates = {}
    er = fund.get("expense_ratio", 999)
    gates["expense_ratio"] = {
        "pass": er <= HARD_GATES["expense_ratio"],
        "threshold": f"≤ {HARD_GATES['expense_ratio']:.4f}",
        "actual": er,
    }
    aum = fund.get("aum", 0)
    gates["aum"] = {
        "pass": aum >= HARD_GATES["min_aum"],
        "threshold": f"≥ ${HARD_GATES['min_aum']:,}",
        "actual": aum,
    }
    te = fund.get("tracking_error", 999)
    gates["tracking_error"] = {
        "pass": te <= HARD_GATES["max_tracking_error"],
        "threshold": f"≤ {HARD_GATES['max_tracking_error']:.4f}",
        "actual": te,
    }
    tr = fund.get("track_record_years", 0)
    gates["track_record"] = {
        "pass": tr >= HARD_GATES["min_track_record_years"],
        "threshold": f"≥ {HARD_GATES['min_track_record_years']} years",
        "actual": tr,
    }
    dur = fund.get("duration", 0)
    target = fund.get("duration_target", DURATION_TARGETS["neutral"])
    gates["duration"] = {
        "pass": abs(dur - target) <= HARD_GATES["max_duration_deviation"],
        "threshold": f"within ±{HARD_GATES['max_duration_deviation']} of {target}",
        "actual": dur,
    }

    passed = all(g.get("pass", False) for g in gates.values())
    failed = [k for k, v in gates.items() if not v.get("pass", False)]

    return {
        "symbol": fund.get("symbol", "?"),
        "passed": passed,
        "status": "pass" if passed else "fail",
        "failed_gates": failed,
        "gates": gates,
    }


def generate_signal(market_data: dict) -> dict:
    """Generate bond allocation signal based on macro conditions.

    Returns: {"regime": str, "duration_target": float, "credit_overweight": bool}
    """
    real_yield = market_data.get("real_yield_tips", 0.0)
    credit_spread = market_data.get("ig_credit_spread", 0.0)
    spread_median = market_data.get("ig_spread_median", 0.0)
    yield_curve_slope = market_data.get("yield_curve_2s10s", 0.0)

    if real_yield > 0.01:
        regime = "rising_rates"
        duration_target = DURATION_TARGETS["rising_rates"]
    elif real_yield < 0.0:
        regime = "falling_rates"
        duration_target = DURATION_TARGETS["falling_rates"]
    else:
        regime = "neutral"
        duration_target = DURATION_TARGETS["neutral"]

    credit_overweight = credit_spread > spread_median

    # Recession risk: inverted yield curve → overweight long bonds
    if yield_curve_slope < 0:
        duration_target = max(duration_target, 7.0)
        regime = "recession_risk"

    return {
        "regime": regime,
        "duration_target": duration_target,
        "credit_overweight": credit_overweight,
        "real_yield": real_yield,
        "credit_spread": credit_spread,
        "yield_curve_slope": yield_curve_slope,
    }


def run_screener(market_data: dict | None = None) -> dict:
    """Run the bond screener on the starter universe."""
    market_data = market_data or {}
    signal = generate_signal(market_data)

    funds = []
    for sym in STARTER_UNIVERSE:
        fund = {
            "symbol": sym,
            "expense_ratio": 0.0003,  # placeholder
            "aum": 5_000_000_000,
            "tracking_error": 0.001,
            "track_record_years": 15,
            "duration": 5.0,  # placeholder
            "duration_target": signal["duration_target"],
        }
        funds.append(fund)

    results = []
    for fund in funds:
        screen = screen_bond(fund)
        results.append({"fund": fund["symbol"], "screen": screen})

    passing = [r for r in results if r["screen"].get("passed", False)]
    failing = [r for r in results if not r["screen"].get("passed", False)]

    print(json.dumps({
        "n_universe": len(funds),
        "n_passing": len(passing),
        "n_failing": len(failing),
        "passing_funds": [r["fund"] for r in passing],
        "signal": signal,
    }, indent=2))
    return {"passing": passing, "failing": failing, "signal": signal}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_screener()