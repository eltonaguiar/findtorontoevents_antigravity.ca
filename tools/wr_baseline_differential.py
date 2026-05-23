"""Per-asset-class WR baseline + per-strategy differential.

Why this exists
---------------
A 65% WR sounds great. But "great" depends on the class baseline:

  - CRYPTO baseline ~38%  -> 65% strategy WR = +27pp REAL edge
  - FOREX baseline  ~55%  -> 65% strategy WR = +10pp marginal edge
  - EQUITY baseline ~52%  -> 65% strategy WR = +13pp meaningful

The audit page reports raw WR. Allocators have to know each class's
baseline to interpret it. This module precomputes the baseline AND
the per-strategy differential, plus a Wilson 95% one-sided LB on the
differential so significance is read directly.

`flag_above_baseline` fires when the Wilson LB on the differential
exceeds 5 percentage points (strong evidence of class-relative edge).

Output per strategy with n>=20
------------------------------
- n, strategy_wr_pct, asset_class
- class_baseline_wr_pct, class_baseline_n
- differential_pp                 strategy_wr_pct - class_baseline_wr_pct
- differential_wilson_lb_95_pp    one-sided 95% lower bound (pp)
- flag_above_baseline             True iff wilson LB > 5pp

Wiring status: OPT-IN SIDECAR. Future PR adds a "vs class" column
to `audit_dashboard/template.html` strategy table sourcing
`tools/data/wr_baseline_differential_results.json`.

Caveats
-------
1. Wilson LB is computed on the strategy's own WR with sample-size T;
   the class baseline is treated as a known constant rather than a
   noisy estimate. For very-small-class samples this slightly
   overstates significance — at the 100-pick class minimum it's
   negligible.
2. Like every closed-pick supplement, fits on labels from
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
OUT_JSON = REPO_ROOT / "tools" / "data" / "wr_baseline_differential_results.json"

DEFAULT_MIN_N_STRATEGY = 20
DEFAULT_MIN_N_CLASS = 100
DEFAULT_FLAG_LB_PP = 5.0


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


def _wilson_lb_pct(wins: int, n: int) -> float:
    """Wilson 95% one-sided lower bound on win-rate (percent)."""
    if n == 0:
        return 0.0
    p = wins / n
    z = 1.645  # 95% one-sided
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = p + z2 / (2 * n)
    half = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    return (centre - half) / denom * 100.0


def compute_class_baselines(picks: list[dict],
                             min_n_class: int = DEFAULT_MIN_N_CLASS
                             ) -> dict[str, dict[str, float]]:
    """Per-class baseline {asset_class: {wr_pct, n}}.

    Classes with n < min_n_class are excluded from the baseline (and
    strategies in those classes will get differential=None).
    """
    by_class: dict[str, list[float]] = defaultdict(list)
    for p in picks:
        pnl = _safe_pnl(p)
        if pnl is None:
            continue
        klass = (p.get("asset_class") or "UNKNOWN").upper()
        by_class[klass].append(pnl)
    out: dict[str, dict[str, float]] = {}
    for klass, vals in by_class.items():
        n = len(vals)
        if n < min_n_class:
            continue
        wins = sum(1 for v in vals if v > 0)
        out[klass] = {
            "wr_pct": round(wins / n * 100.0, 4),
            "n": int(n),
        }
    return out


def analyze_strategy(picks: list[dict],
                      class_baselines: dict[str, dict[str, float]],
                      min_n: int = DEFAULT_MIN_N_STRATEGY,
                      flag_lb_pp: float = DEFAULT_FLAG_LB_PP) -> dict | None:
    pnls: list[float] = []
    klass = "UNKNOWN"
    for p in picks:
        pnl = _safe_pnl(p)
        if pnl is None:
            continue
        pnls.append(pnl)
        klass = (p.get("asset_class") or klass).upper()
    if len(pnls) < min_n:
        return None

    n = len(pnls)
    wins = sum(1 for v in pnls if v > 0)
    strategy_wr = wins / n * 100.0
    strategy_lb = _wilson_lb_pct(wins, n)

    baseline = class_baselines.get(klass)
    if baseline is None:
        return {
            "n": int(n), "asset_class": klass,
            "strategy_wr_pct": round(strategy_wr, 4),
            "strategy_wilson_lb_95_pct": round(strategy_lb, 4),
            "class_baseline_wr_pct": None,
            "class_baseline_n": None,
            "differential_pp": None,
            "differential_wilson_lb_95_pp": None,
            "flag_above_baseline": False,
            "skipped_reason": f"insufficient class {klass} sample",
        }

    differential = strategy_wr - baseline["wr_pct"]
    diff_lb = strategy_lb - baseline["wr_pct"]
    flag = diff_lb > flag_lb_pp
    return {
        "n": int(n),
        "asset_class": klass,
        "strategy_wr_pct": round(strategy_wr, 4),
        "strategy_wilson_lb_95_pct": round(strategy_lb, 4),
        "class_baseline_wr_pct": baseline["wr_pct"],
        "class_baseline_n": int(baseline["n"]),
        "differential_pp": round(differential, 4),
        "differential_wilson_lb_95_pp": round(diff_lb, 4),
        "flag_above_baseline": flag,
    }


def analyze_all(picks: list[dict],
                min_n_strategy: int = DEFAULT_MIN_N_STRATEGY,
                min_n_class: int = DEFAULT_MIN_N_CLASS,
                flag_lb_pp: float = DEFAULT_FLAG_LB_PP) -> dict:
    baselines = compute_class_baselines(picks, min_n_class)
    by_strategy: dict[str, list[dict]] = defaultdict(list)
    for p in picks:
        by_strategy[p.get("strategy") or "unknown"].append(p)

    out: list[dict] = []
    for strat, sub in by_strategy.items():
        r = analyze_strategy(sub, baselines, min_n_strategy, flag_lb_pp)
        if r is None:
            continue
        r["strategy"] = strat
        out.append(r)
    out.sort(key=lambda r: -(r["differential_wilson_lb_95_pp"] or -999))
    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "config": {"min_n_strategy": min_n_strategy,
                   "min_n_class": min_n_class,
                   "flag_lb_pp": flag_lb_pp},
        "class_baselines": baselines,
        "n_strategies": len(out),
        "n_above_baseline": sum(
            1 for r in out if r["flag_above_baseline"]),
        "strategies": out,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--min-n-strategy", type=int, default=DEFAULT_MIN_N_STRATEGY)
    ap.add_argument("--min-n-class", type=int, default=DEFAULT_MIN_N_CLASS)
    ap.add_argument("--flag-lb-pp", type=float, default=DEFAULT_FLAG_LB_PP)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    with PICKS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    picks = data.get("picks", {}).get("recent_closed", [])

    summary = analyze_all(picks, args.min_n_strategy, args.min_n_class,
                          args.flag_lb_pp)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    if not args.quiet:
        print(f"class baselines: {summary['class_baselines']}")
        print(f"strategies analysed: {summary['n_strategies']}")
        print(f"above-baseline (LB > {args.flag_lb_pp}pp): "
              f"{summary['n_above_baseline']}")
        for r in summary["strategies"][:10]:
            flag = "ABV" if r["flag_above_baseline"] else " - "
            diff = r["differential_pp"]
            lb = r["differential_wilson_lb_95_pp"]
            print(f"  [{flag}] {r['strategy'][:30]:<30} {r['asset_class']:<10} "
                  f"WR={r['strategy_wr_pct']:>5.1f}% "
                  f"diff={diff if diff is not None else '-':>+6} "
                  f"LB={lb if lb is not None else '-':>+6} n={r['n']}")
        print(f"JSON: {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
