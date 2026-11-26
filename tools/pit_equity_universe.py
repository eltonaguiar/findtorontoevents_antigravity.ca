#!/usr/bin/env python3
"""Build a point-in-time equity/ETF universe of >= 22 names for the H-201 pod.

WHY THIS EXISTS
    `tools/pod_forward.py` bars itself from ever issuing a PASS because its universe is 10
    mega-caps and the pod spec requires a point-in-time universe of at least
    `universe.minimum_names` (22) names. That bar exists because a universe drawn from
    *today's* tickers cannot contain a name that died, so it is survivorship-flattered.

WHAT THIS TOOL DOES
    Enumerates the equity/ETF series actually on disk, computes each symbol's first and last
    available close, and reports the trading membership of the universe on every monthly
    rebalance date using `tools/pit_universe.py` (first-observation point-in-time). Writes
    `reports/pit_equity_universe_20261122.json` with the membership, per-date counts, and the
    count against the spec's minimum.

WHAT IT DELIBERATELY DOES NOT DO
    It does NOT claim the survivorship problem is solved. Removing left/right censoring is not
    removing delisting bias: every symbol in this cache is a name that still exists, because the
    cache was built from today's list. So this tool can satisfy the *count* bar and cannot
    satisfy the *purpose* of that bar. The output says so in a machine-readable field
    (`survivorship.status = PARTIAL_NON_DELISTING_AWARE`) rather than in a footnote, because a
    PASS issued on the strength of a 44-name count alone would be exactly the laundering the
    programme exists to prevent.

    Recommendation encoded in the artifact: a PASS on this universe is admissible under the
    LETTER of the pod rule and should be labelled `CANDIDATE_SURVIVORSHIP_FLAGGED` rather than
    `PASS` until a delisted-ticker price source exists (see COMS ask A1).

Read-only. No orders. Not investment advice.

Usage:
    python3 tools/pit_equity_universe.py                 # build + write artifact
    python3 tools/pit_equity_universe.py --min-names 22  # override the spec floor
    python3 tools/pit_equity_universe.py --dry-run       # print, write nothing
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import pandas as pd  # noqa: E402

from pit_universe import build_pit_universe, _load_close_series  # noqa: E402

CACHE_DIR = ROOT / "data" / "cache" / "asset_class_review"
OUT_DIR = ROOT / "reports"
DEFAULT_MIN_NAMES = 22

# asset-class suffix conventions used by this cache
CRYPTO_SUFFIX = "-USD"
FX_SUFFIX = "_X"
FUTURES_SUFFIX = "_F"


def classify(sym: str) -> str:
    if sym.endswith(CRYPTO_SUFFIX):
        return "CRYPTO"
    if sym.endswith(FX_SUFFIX):
        return "FOREX"
    if sym.endswith(FUTURES_SUFFIX):
        return "FUTURES"
    return "EQUITY_OR_ETF"


def census(cache_dir: Path) -> dict:
    out = {}
    for p in sorted(glob.glob(str(cache_dir / "*_5y.csv"))):
        sym = os.path.basename(p)[: -len("_5y.csv")]
        try:
            close = _load_close_series(p)
        except Exception as e:  # noqa: BLE001 - recorded, not raised
            out[sym] = {"error": f"{type(e).__name__}: {e}"}
            continue
        if close.empty:
            out[sym] = {"error": "no positive closes"}
            continue
        out[sym] = {
            "first": close.index[0].date().isoformat(),
            "last": close.index[-1].date().isoformat(),
            "n_obs": int(len(close)),
            "asset_class": classify(sym),
        }
    return out


def month_end_sessions(idx: pd.DatetimeIndex) -> list:
    """Last session of each month — the pod's rebalance signal dates."""
    s = pd.Series(idx, index=idx)
    return list(s.groupby([idx.year, idx.month]).last())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-names", type=int, default=DEFAULT_MIN_NAMES)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--cache-dir", default=str(CACHE_DIR))
    a = ap.parse_args()

    cache_dir = Path(a.cache_dir)
    c = census(cache_dir)
    ok = {s: v for s, v in c.items() if "error" not in v}
    eq = {s: v for s, v in ok.items() if v["asset_class"] == "EQUITY_OR_ETF"}

    print(f"cache: {len(c)} series, {len(ok)} parseable, {len(eq)} equity/ETF")
    if not eq:
        print("NO equity/ETF series found — refusing to invent a universe")
        return 2

    # the window the pod backtests over: intersection of all equity firsts / lasts
    start = max(v["first"] for v in eq.values())
    end = min(v["last"] for v in eq.values())
    print(f"equity window: {start} -> {end}")

    # rebalance dates from the union index, then per-date PIT membership
    ref = _load_close_series(str(cache_dir / f"{sorted(eq)[0]}_5y.csv"))
    idx = ref.index[(ref.index >= pd.Timestamp(start)) & (ref.index <= pd.Timestamp(end))]
    dates = month_end_sessions(idx)

    per_date = {}
    for d in dates:
        names = build_pit_universe(d, str(cache_dir), symbols=sorted(eq))
        per_date[d.date().isoformat()] = len(names)

    counts = list(per_date.values())
    min_count, max_count = (min(counts), max(counts)) if counts else (0, 0)
    thin = sorted(k for k, v in per_date.items() if v < a.min_names)

    survived_full_window = sorted(s for s, v in eq.items()
                                  if v["first"] <= start and v["last"] >= end)

    artifact = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "task": "PIT equity/ETF universe for POD-EQUITY-H201-XSMOM-6M",
        "universe_minimum_required": a.min_names,
        "universe": sorted(eq),
        "n_universe": len(eq),
        "n_covering_full_window": len(survived_full_window),
        "window": {"start": start, "end": end},
        "rebalance_dates": len(dates),
        "membership_per_date": per_date,
        "min_membership": min_count,
        "max_membership": max_count,
        "dates_below_minimum": thin,
        "passes_count_bar": bool(counts and not thin and min_count >= a.min_names),
        "survivorship": {
            "status": "PARTIAL_NON_DELISTING_AWARE",
            "what_is_fixed": ("left- and right-censoring: a symbol does not count before its "
                              "first available close or after its last"),
            "what_is_not_fixed": ("delisting bias: every symbol in this cache still exists, so "
                                  "names that died are absent and their returns are not in any "
                                  "distribution computed on this universe"),
            "direction_of_residual_bias": "UPWARD for long-only momentum families",
            "source": "tools/pit_universe.py (first-observation PIT)",
        },
        "verdict_guidance": {
            "count_bar": ("MET - the spec's minimum_names condition is satisfied on every "
                          "rebalance date" if counts and not thin and min_count >= a.min_names
                          else "NOT MET - see dates_below_minimum"),
            "recommended_label": ("CANDIDATE_SURVIVORSHIP_FLAGGED rather than PASS: the letter "
                                   "of the pod rule is satisfied, its purpose is not"),
            "what_would_change_this": ("a delisted-ticker OHLC source (COMS ask A1: Polygon / "
                                       "Tiingo / CRSP / Norgate). None exists in this tree"),
        },
        "per_symbol": {s: eq[s] for s in sorted(eq)},
        "excluded_by_class": {
            k: sorted(s for s, v in ok.items() if v["asset_class"] == k)
            for k in ("CRYPTO", "FOREX", "FUTURES")
        },
    }

    print(f"rebalance dates: {len(dates)} | membership min {min_count} max {max_count}")
    if thin:
        print(f"DATES BELOW MINIMUM ({a.min_names}): {thin}")
    print(f"count bar: {'MET' if artifact['passes_count_bar'] else 'NOT MET'}")
    print("survivorship: PARTIAL - delisting bias remains, direction UPWARD")

    if a.dry_run:
        print("\n--dry-run: artifact not written")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "pit_equity_universe_20261122.json"
    path.write_text(json.dumps(artifact, indent=1))
    print(f"\nwrote {path}")

    return 0 if artifact["passes_count_bar"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
