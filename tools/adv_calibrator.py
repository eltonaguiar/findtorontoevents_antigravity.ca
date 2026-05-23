"""Per-asset-class ADV calibrator from realised pick sizes.

Why this exists
---------------
`tools/capacity_estimator.py` uses hard-coded `FALLBACK_ADV_USD` constants
when yfinance lookup fails. Those numbers are conservative guesses
(documented in the capacity_estimator caveats). This module computes the
per-class **empirical** ADV proxy from actual closed-pick sizes —
useful both as a sanity check on the constants and as a more honest
fallback for symbols / classes where yfinance has poor coverage.

What it computes
----------------
For each asset class, treats `entry_price * 1` as the per-pick notional
proxy (assumes 1-unit position size since dashboard picks don't carry
explicit position size). Then reports per-class:

  - `median_pick_usd`    50th percentile of pick notionals
  - `p25_pick_usd`       25th percentile
  - `p75_pick_usd`       75th percentile
  - `min_pick_usd`       0th percentile
  - `max_pick_usd`       100th percentile
  - `n_picks_observed`   sample size
  - `last_calibrated_at` UTC ISO timestamp

This is NOT an ADV estimate (we don't know the actual market volume) —
it's a *trade-size distribution* proxy. The capacity_estimator can use
this to estimate "ADV at retail-pick-size scale" rather than the
exchange-wide ADV, which is a more honest input for capacity math when
the strategy operates at retail size.

Output: `tools/data/adv_calibration.json`. Future capacity_estimator
revision can read this artifact to override its FALLBACK_ADV_USD when
yfinance lookup fails.

Wiring status: OPT-IN SIDECAR. No production caller. No env flag.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PICKS_PATH = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_JSON = REPO_ROOT / "tools" / "data" / "adv_calibration.json"
DEFAULT_MIN_N = 5  # below this per class, skip — too noisy


def _safe_float(x: Any) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    return v


def _percentile(values: list[float], pct: float) -> float:
    """Linear-interpolation percentile (matches numpy default).

    pct in [0, 100]. Pure-python so we don't pull numpy as a hard dep.
    """
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    sv = sorted(values)
    rank = (pct / 100.0) * (len(sv) - 1)
    lo = int(math.floor(rank))
    hi = int(math.ceil(rank))
    if lo == hi:
        return float(sv[lo])
    frac = rank - lo
    return float(sv[lo] + (sv[hi] - sv[lo]) * frac)


def _extract_notionals(picks: list[dict]) -> dict[str, list[float]]:
    """Group `entry_price` notionals by asset_class.

    Skips picks with missing or non-numeric entry_price.
    """
    by_class: dict[str, list[float]] = defaultdict(list)
    for p in picks:
        ep = _safe_float(p.get("entry_price"))
        if ep is None or ep <= 0:
            continue
        klass = (p.get("asset_class") or "UNKNOWN").upper()
        by_class[klass].append(ep)
    return by_class


def calibrate(picks: list[dict],
              min_n: int = DEFAULT_MIN_N) -> dict[str, Any]:
    """Pure function: closed picks -> calibration artifact dict."""
    by_class = _extract_notionals(picks)
    now = datetime.now(timezone.utc).isoformat()
    out: dict[str, Any] = {
        "schema_version": 1,
        "last_calibrated_at": now,
        "min_n": min_n,
        "by_asset_class": {},
        "skipped_classes": {},
    }
    for klass, vals in by_class.items():
        if len(vals) < min_n:
            out["skipped_classes"][klass] = {
                "n_picks_observed": len(vals),
                "reason": f"n<min_n({min_n})",
            }
            continue
        out["by_asset_class"][klass] = {
            "n_picks_observed": len(vals),
            "min_pick_usd": round(_percentile(vals, 0), 6),
            "p25_pick_usd": round(_percentile(vals, 25), 6),
            "median_pick_usd": round(_percentile(vals, 50), 6),
            "p75_pick_usd": round(_percentile(vals, 75), 6),
            "max_pick_usd": round(_percentile(vals, 100), 6),
        }
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--min-n", type=int, default=DEFAULT_MIN_N)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    with PICKS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    picks_block = data.get("picks", {}) or {}
    picks = list(picks_block.get("recent_closed") or []) + list(
        picks_block.get("active") or [])

    summary = calibrate(picks, args.min_n)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    if not args.quiet:
        print(f"calibrated classes: {len(summary['by_asset_class'])}")
        for klass, c in sorted(summary["by_asset_class"].items()):
            print(f"  {klass:<10} n={c['n_picks_observed']:>5} "
                  f"median=${c['median_pick_usd']:,.2f} "
                  f"[p25=${c['p25_pick_usd']:,.2f}, "
                  f"p75=${c['p75_pick_usd']:,.2f}]")
        if summary["skipped_classes"]:
            print(f"skipped (n<{args.min_n}):")
            for klass, info in summary["skipped_classes"].items():
                print(f"  {klass}: n={info['n_picks_observed']}")
        print(f"JSON: {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
