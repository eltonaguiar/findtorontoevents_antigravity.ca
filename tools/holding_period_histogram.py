"""Per-strategy holding-period distribution + picks/day + edge/minute.

Why this exists
---------------
The supplement suite covers mean edge, risk, concentration, overfit,
and capacity — but not TIMING. A strategy that emits 50 picks/day with
median holding 5 minutes is structurally different from one that emits
2 picks/day with median holding 4 hours, even if they have identical
mean PnL. The high-frequency strategy's after-cost edge is constantly
under attack from round-trip transaction costs; the low-frequency
strategy is not.

This module computes per-strategy:
  - p25 / median / p75 / mean holding period in minutes
  - picks_per_day
  - bucket counts at standard horizons (1m, 5m, 30m, 1h, 4h, 1d, 1w, 1mo+)
  - edge_per_minute = mean_pnl_pct / median_minutes
  - flag_high_freq_low_conviction when picks/day > 50 AND median < 30m

The flag fires the "scalper paying fees away" pattern: a strategy whose
small per-trade edge gets eaten by its round-trip TC. Combined with the
already-shipped capacity_estimator, allocators have full timing-aware
view of execution feasibility.

Wiring status: OPT-IN SIDECAR. Future PR adds a `holding median` and
`picks/day` column to audit_dashboard/template.html strategy table
sourcing tools/data/holding_period_results.json.

Caveats
-------
1. Many picks lack `opened_at` (it's frequently None in the dashboard
   payload). Those go into a `duration_unavailable` count rather than
   skewing the distribution. Strategies with mostly-unavailable
   durations are flagged in the output.
2. picks_per_day uses calendar-day spread, not active-trading-hour
   spread. A strategy that only trades during US market hours but
   spreads its picks across 5 picks/day will read as "5/day" even
   though intraday density is 5/6.5 = 0.77/hour.
3. Like every closed-pick supplement, fits on labels from
   outcome_resolver.py.
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
OUT_JSON = REPO_ROOT / "tools" / "data" / "holding_period_results.json"

DEFAULT_MIN_N = 20
DEFAULT_FREQ_FLAG_PER_DAY = 50.0
DEFAULT_FREQ_FLAG_MEDIAN_MIN = 30.0

BUCKETS_MINUTES: list[tuple[str, float]] = [
    ("1m_or_less", 1.0),
    ("1m_to_5m", 5.0),
    ("5m_to_30m", 30.0),
    ("30m_to_1h", 60.0),
    ("1h_to_4h", 240.0),
    ("4h_to_1d", 1440.0),
    ("1d_to_1w", 1440.0 * 7),
    ("1w_to_1mo", 1440.0 * 30),
    ("over_1mo", float("inf")),
]


def _safe_pnl(pick: dict) -> float | None:
    pnl = pick.get("pnl_pct")
    if pnl is None:
        return None
    try:
        v = float(pnl)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    return v


def _parse_iso(s: Any) -> datetime | None:
    if not isinstance(s, str):
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _percentile(values: list[float], pct: float) -> float:
    """Linear-interpolation percentile (matches numpy default)."""
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


def _bucket_label(minutes: float) -> str:
    for label, upper in BUCKETS_MINUTES:
        if minutes <= upper:
            return label
    return "over_1mo"


def analyze_strategy(picks: list[dict],
                      min_n: int = DEFAULT_MIN_N,
                      freq_flag_per_day: float = DEFAULT_FREQ_FLAG_PER_DAY,
                      freq_flag_median_min: float = DEFAULT_FREQ_FLAG_MEDIAN_MIN
                      ) -> dict | None:
    """Per-strategy holding-period stats. Returns None when n < min_n."""
    durations: list[float] = []
    pnls: list[float] = []
    closed_times: list[datetime] = []
    duration_unavailable = 0
    bucket_counts: dict[str, int] = {label: 0 for label, _ in BUCKETS_MINUTES}

    for p in picks:
        pnl = _safe_pnl(p)
        if pnl is None:
            continue
        pnls.append(pnl)
        opened = _parse_iso(p.get("opened_at"))
        closed = _parse_iso(p.get("closed_at"))
        if closed is not None:
            closed_times.append(closed)
        if opened is None or closed is None or closed <= opened:
            duration_unavailable += 1
            continue
        minutes = (closed - opened).total_seconds() / 60.0
        durations.append(minutes)
        bucket_counts[_bucket_label(minutes)] += 1

    n_total = len(pnls)
    if n_total < min_n:
        return None

    median_minutes = _percentile(durations, 50) if durations else 0.0
    mean_minutes = (sum(durations) / len(durations)) if durations else 0.0
    avg_pnl_pct = (sum(pnls) / n_total) if pnls else 0.0
    edge_per_minute = (avg_pnl_pct / median_minutes) if median_minutes > 0 else 0.0

    if len(closed_times) >= 2:
        span_days = max(
            (max(closed_times) - min(closed_times)).total_seconds() / 86400.0,
            1.0,
        )
        picks_per_day = n_total / span_days
    else:
        picks_per_day = 0.0

    flag_high_freq = (picks_per_day > freq_flag_per_day
                      and median_minutes > 0
                      and median_minutes < freq_flag_median_min)

    return {
        "n": int(n_total),
        "n_with_duration": int(len(durations)),
        "duration_unavailable": int(duration_unavailable),
        "p25_minutes": round(_percentile(durations, 25), 4),
        "median_minutes": round(median_minutes, 4),
        "p75_minutes": round(_percentile(durations, 75), 4),
        "mean_minutes": round(mean_minutes, 4),
        "picks_per_day": round(picks_per_day, 4),
        "avg_pnl_pct": round(avg_pnl_pct, 6),
        "edge_per_minute": round(edge_per_minute, 9),
        "bucket_counts": bucket_counts,
        "flag_high_freq_low_conviction": flag_high_freq,
    }


def analyze_all(picks: list[dict],
                min_n: int = DEFAULT_MIN_N,
                freq_flag_per_day: float = DEFAULT_FREQ_FLAG_PER_DAY,
                freq_flag_median_min: float = DEFAULT_FREQ_FLAG_MEDIAN_MIN
                ) -> dict:
    by_strategy: dict[str, list[dict]] = defaultdict(list)
    for p in picks:
        by_strategy[p.get("strategy") or "unknown"].append(p)

    out: list[dict] = []
    for strat, sub in by_strategy.items():
        r = analyze_strategy(sub, min_n, freq_flag_per_day, freq_flag_median_min)
        if r is None:
            continue
        r["strategy"] = strat
        out.append(r)
    out.sort(key=lambda r: r["median_minutes"])

    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "config": {"min_n": min_n,
                   "freq_flag_per_day": freq_flag_per_day,
                   "freq_flag_median_min": freq_flag_median_min},
        "n_strategies": len(out),
        "n_high_freq_flagged": sum(
            1 for r in out if r["flag_high_freq_low_conviction"]),
        "strategies": out,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--min-n", type=int, default=DEFAULT_MIN_N)
    ap.add_argument("--freq-flag-per-day", type=float,
                    default=DEFAULT_FREQ_FLAG_PER_DAY)
    ap.add_argument("--freq-flag-median-min", type=float,
                    default=DEFAULT_FREQ_FLAG_MEDIAN_MIN)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    with PICKS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    picks = data.get("picks", {}).get("recent_closed", [])

    summary = analyze_all(picks, args.min_n, args.freq_flag_per_day,
                          args.freq_flag_median_min)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    if not args.quiet:
        print(f"strategies analysed: {summary['n_strategies']}")
        print(f"high-frequency low-conviction flagged: "
              f"{summary['n_high_freq_flagged']}")
        print("top 10 by median holding (shortest first):")
        for r in summary["strategies"][:10]:
            flag = "HFREQ" if r["flag_high_freq_low_conviction"] else "  ok "
            print(f"  [{flag}] {r['strategy'][:30]:<30} "
                  f"med={r['median_minutes']:>8.2f}m "
                  f"picks/day={r['picks_per_day']:>6.2f} "
                  f"edge/min={r['edge_per_minute']:>+8.6f} "
                  f"n={r['n']}")
        print(f"JSON: {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
