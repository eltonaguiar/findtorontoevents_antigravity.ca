"""Demo driver: LQD-HYG credit-spread mean-reversion signal.

Pulls 2 years of HYG (HY OAS) minus LQD (IG OAS) from FRED, computes the
60-day z-score, and prints the BOND-team's top-1 ship signal:

    z >= +2  -> LONG_IG    (spread rich, IG should outperform HY as it tightens)
    z <= -2  -> LONG_HY    (spread cheap, HY should outperform as it tightens)
    else     -> NEUTRAL

This script is the **proof of feasibility** for the strategy referenced in
``reports/asset_class_team_bond_2026_04_28.md`` — it shows the exact data +
math the strategy needs is reachable on free APIs (FRED) and importable
modules (``alpha_engine.fred_data_fetcher``, ``alpha_engine.bond_pricer``).

Requires ``FRED_API_KEY`` (free; https://fred.stlouisfed.org/docs/api/api_key.html).

Usage::

    python tools/run_bond_signal_demo.py
    python tools/run_bond_signal_demo.py --lookback 90 --threshold 1.5
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Make the repo root importable when invoked as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alpha_engine.bond_pricer import credit_spread_zscore  # noqa: E402
from alpha_engine.fred_data_fetcher import (  # noqa: E402
    MissingFredApiKey,
    get_credit_spread,
)


def classify(z: float, threshold: float) -> str:
    if z != z:  # NaN
        return "INSUFFICIENT_DATA"
    if z >= threshold:
        return "LONG_IG"
    if z <= -threshold:
        return "LONG_HY"
    return "NEUTRAL"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lookback", type=int, default=60,
                   help="rolling window for z-score (days)")
    p.add_argument("--threshold", type=float, default=2.0,
                   help="|z| threshold for LONG_IG / LONG_HY signal")
    p.add_argument("--years", type=int, default=2,
                   help="years of history to pull from FRED")
    p.add_argument("--no-cache", action="store_true",
                   help="skip the local parquet cache")
    args = p.parse_args(argv)

    date_from = (datetime.utcnow().date() - timedelta(days=365 * args.years))
    try:
        spread = get_credit_spread(
            "HYG_LQD",
            date_from=date_from,
            use_cache=not args.no_cache,
        )
    except MissingFredApiKey as e:
        print(f"ERROR: {e}", file=sys.stderr)
        print("Set FRED_API_KEY and re-run.", file=sys.stderr)
        return 2

    if spread is None or len(spread) == 0:
        print("ERROR: empty HYG_LQD spread series from FRED", file=sys.stderr)
        return 3

    z = credit_spread_zscore(spread, lookback=args.lookback)
    signal = classify(z, args.threshold)
    latest = float(spread.iloc[-1])
    latest_date = str(spread.index[-1].date())

    out = {
        "series": "HYG_LQD",
        "latest_date": latest_date,
        "latest_spread_pp": round(latest, 4),
        "lookback_days": args.lookback,
        "zscore": round(z, 3) if z == z else None,
        "threshold": args.threshold,
        "signal": signal,
        "n_observations": int(len(spread)),
    }
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
