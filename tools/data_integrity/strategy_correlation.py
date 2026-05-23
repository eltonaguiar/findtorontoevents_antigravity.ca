"""Pairwise correlation matrix of strategy returns.

Diagnoses the diversification problem directly. In a 93%-crypto system,
most strategies are likely to be highly correlated — this quantifies it
so concentration risk is visible rather than implicit.

Method:
  1. Load closed picks, filter ghosts, group by (strategy, date).
  2. Build a daily-return series per strategy (sum of pnl_pct per day).
  3. Compute Pearson correlation across each pair of strategies with
     overlapping days >= MIN_OVERLAP.
  4. Flag pairs with |rho| >= 0.80 as highly correlated (concentration).
  5. Report average pairwise correlation per strategy — the higher the
     average, the less diversified that strategy's return stream.

Stdlib only. Safe-default pass when strategy count < 2 or data sparse.

Usage:
    python tools/data_integrity/strategy_correlation.py
    python tools/data_integrity/strategy_correlation.py --min-trades 30
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
from collections import defaultdict
from typing import Any

try:
    from tools.data_integrity import _common
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from tools.data_integrity import _common  # type: ignore

DEFAULT_MIN_TRADES = 20
DEFAULT_MIN_OVERLAP_DAYS = 5
HIGH_CORR_THRESHOLD = 0.80


def build_daily_returns(rows: list[dict], min_trades: int) -> dict[str, dict[str, float]]:
    """Return {strategy: {date_str: daily_pnl_sum}} for strategies with >= min_trades."""
    per_strategy_trades: dict[str, int] = defaultdict(int)
    per_strategy_daily: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for p in rows:
        if _common.is_ghost_row(p):
            continue
        strat = p.get("strategy") or p.get("source") or p.get("source_system")
        if not strat:
            continue
        strat = str(strat)
        raw_pnl = p.get("pnl_pct")
        if raw_pnl is None:
            raw_pnl = p.get("pnl")
        try:
            pnl = float(raw_pnl) if raw_pnl is not None else None
        except (TypeError, ValueError):
            pnl = None
        if pnl is None:
            continue
        ts = (
            _common.parse_ts(p.get("closed_at"))
            or _common.parse_ts(p.get("close_time"))
            or _common.parse_ts(p.get("resolved_at"))
            or _common.parse_ts(p.get("exit_time"))
            or _common.parse_ts(p.get("timestamp"))
            or _common.parse_ts(p.get("created_at"))
        )
        if ts is None:
            continue
        day_key = ts.strftime("%Y-%m-%d")
        per_strategy_daily[strat][day_key] += pnl
        per_strategy_trades[strat] += 1

    return {
        s: dict(days)
        for s, days in per_strategy_daily.items()
        if per_strategy_trades[s] >= min_trades
    }


def pearson(xs: list[float], ys: list[float]) -> float | None:
    """Plain-stdlib Pearson correlation. Returns None if undefined (zero variance)."""
    n = len(xs)
    if n < 2:
        return None
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    var_x = sum((x - mx) ** 2 for x in xs)
    var_y = sum((y - my) ** 2 for y in ys)
    if var_x == 0 or var_y == 0:
        return None
    return num / math.sqrt(var_x * var_y)


def compute_correlation_matrix(
    strat_daily: dict[str, dict[str, float]],
    min_overlap: int,
) -> dict[tuple[str, str], tuple[float, int]]:
    """Return {(s1,s2): (rho, overlap_n)} for every strategy pair with overlap >= min."""
    strategies = sorted(strat_daily.keys())
    out: dict[tuple[str, str], tuple[float, int]] = {}
    for i, a in enumerate(strategies):
        a_days = strat_daily[a]
        for b in strategies[i + 1 :]:
            b_days = strat_daily[b]
            common = sorted(set(a_days) & set(b_days))
            if len(common) < min_overlap:
                continue
            xs = [a_days[d] for d in common]
            ys = [b_days[d] for d in common]
            rho = pearson(xs, ys)
            if rho is None:
                continue
            out[(a, b)] = (rho, len(common))
    return out


def analyze(min_trades: int, min_overlap: int) -> dict[str, Any]:
    rows = _common.load_json_list(_common.CLOSED_PICKS)
    strat_daily = build_daily_returns(rows, min_trades)
    n_strategies = len(strat_daily)
    if n_strategies < 2:
        return {
            "status": "INSUFFICIENT_STRATEGIES",
            "n_strategies": n_strategies,
            "min_trades": min_trades,
            "message": f"Need >=2 strategies with >={min_trades} trades; got {n_strategies}",
        }

    matrix = compute_correlation_matrix(strat_daily, min_overlap)
    if not matrix:
        return {
            "status": "INSUFFICIENT_OVERLAP",
            "n_strategies": n_strategies,
            "min_overlap": min_overlap,
            "message": (
                f"No strategy pair had >={min_overlap} overlapping days. "
                "Try --min-overlap 3 or a longer lookback."
            ),
        }

    # Average absolute correlation per strategy (how non-diversified it is)
    per_strat_avg: dict[str, list[float]] = defaultdict(list)
    for (a, b), (rho, _) in matrix.items():
        per_strat_avg[a].append(abs(rho))
        per_strat_avg[b].append(abs(rho))
    concentration_scores = {
        s: statistics.fmean(vals) for s, vals in per_strat_avg.items()
    }

    # Highly correlated pairs
    high_corr_pairs = sorted(
        [
            {"pair": [a, b], "rho": round(rho, 3), "overlap_days": n}
            for (a, b), (rho, n) in matrix.items()
            if abs(rho) >= HIGH_CORR_THRESHOLD
        ],
        key=lambda d: abs(d["rho"]),
        reverse=True,
    )

    overall_mean = statistics.fmean(abs(rho) for (_, (rho, _)) in matrix.items())

    sorted_concentration = sorted(
        concentration_scores.items(), key=lambda kv: kv[1], reverse=True
    )

    return {
        "status": "OK",
        "n_strategies": n_strategies,
        "n_pairs": len(matrix),
        "min_trades": min_trades,
        "min_overlap_days": min_overlap,
        "high_corr_threshold": HIGH_CORR_THRESHOLD,
        "mean_abs_correlation": round(overall_mean, 4),
        "high_corr_pairs": high_corr_pairs,
        "concentration_top10": [
            {"strategy": s, "avg_abs_rho": round(v, 3)}
            for s, v in sorted_concentration[:10]
        ],
    }


def format_report(result: dict[str, Any]) -> str:
    lines = ["=== STRATEGY CORRELATION ==="]
    if result.get("status") != "OK":
        lines.append(f"Status: {result.get('status')}")
        lines.append(f"Message: {result.get('message', '')}")
        return "\n".join(lines)
    lines.append(
        f"Strategies: {result['n_strategies']} | Pairs: {result['n_pairs']} | "
        f"min_trades={result['min_trades']} min_overlap={result['min_overlap_days']}"
    )
    lines.append(f"Overall mean |rho|: {result['mean_abs_correlation']:.4f}")
    if result["high_corr_pairs"]:
        lines.append("")
        lines.append(f"Highly correlated pairs (|rho| >= {HIGH_CORR_THRESHOLD}):")
        for entry in result["high_corr_pairs"][:20]:
            a, b = entry["pair"]
            lines.append(
                f"  rho={entry['rho']:+.3f}  n={entry['overlap_days']:3d}  "
                f"{a[:28]:28s}  <->  {b[:28]}"
            )
    else:
        lines.append(f"No pairs above |rho|={HIGH_CORR_THRESHOLD} — good diversification signal.")
    lines.append("")
    lines.append("Top 10 most-correlated strategies (avg |rho| with other strategies):")
    for entry in result["concentration_top10"]:
        lines.append(f"  {entry['avg_abs_rho']:.3f}  {entry['strategy']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--min-trades", type=int, default=DEFAULT_MIN_TRADES)
    parser.add_argument("--min-overlap", type=int, default=DEFAULT_MIN_OVERLAP_DAYS)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = analyze(args.min_trades, args.min_overlap)
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(format_report(result))

    out_dir = _common.ensure_out_dir()
    out_path = os.path.join(out_dir, "strategy_correlation.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)

    if result.get("status") != "OK":
        return 3  # insufficient data, not a failure
    # Flag if mean concentration is dangerously high
    if result["mean_abs_correlation"] >= 0.70:
        return 2  # concentration warning
    return 0


if __name__ == "__main__":
    sys.exit(main())
