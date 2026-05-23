"""Per-strategy win/loss streak analyzer.

Why this exists
---------------
Mean-PnL metrics hide tail-of-tail risk: a strategy with 60% WR can
still suffer a 6-trade losing streak that wipes a quarter of equity
under fixed-fractional sizing. Rolling-Sharpe drawdown
(`rolling_sharpe_drawdown.py`) captures it after the fact in
percentage-equity terms; this module surfaces the underlying
*combinatorial* pattern in a more interpretable way: max consecutive
wins, max consecutive losses, and the streak-length distribution.

Output per strategy with n>=20 picks (chronological by closed_at)
-----------------------------------------------------------------
- max_win_streak           longest run of consecutive wins
- max_loss_streak          longest run of consecutive losses
- current_streak           signed: +N for current win run, -N for loss run
- n_streaks                total number of streaks
- p25_streak_length        25th percentile of all streak lengths
- median_streak_length     50th percentile
- p75_streak_length        75th percentile
- mean_streak_length       arithmetic mean
- win_streak_count         number of winning streaks
- loss_streak_count        number of losing streaks

Wiring status: OPT-IN SIDECAR. Future PR adds a "max-loss-streak"
column to `audit_dashboard/template.html` strategy table sourcing
`tools/data/win_loss_streak_results.json`.

Caveats
-------
1. Treats `pnl_pct == 0` as a loss (consistent with wr_posterior
   convention: `pnl_pct > 0` = win, else loss).
2. Sorts picks chronologically by closed_at when present; falls back
   to input order when the field is missing or malformed.
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
OUT_JSON = REPO_ROOT / "tools" / "data" / "win_loss_streak_results.json"

DEFAULT_MIN_N = 20


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


def compute_streaks(outcomes: list[int]) -> list[tuple[int, int]]:
    """Return list of (sign, length) tuples. sign=+1 for wins, -1 losses.

    e.g. [1, 1, 0, 1, 0, 0] -> [(+1, 2), (-1, 1), (+1, 1), (-1, 2)].
    """
    out: list[tuple[int, int]] = []
    if not outcomes:
        return out
    cur_sign = 1 if outcomes[0] else -1
    run = 1
    for o in outcomes[1:]:
        sign = 1 if o else -1
        if sign == cur_sign:
            run += 1
        else:
            out.append((cur_sign, run))
            cur_sign = sign
            run = 1
    out.append((cur_sign, run))
    return out


def analyze_strategy(picks: list[dict],
                      min_n: int = DEFAULT_MIN_N) -> dict | None:
    cleaned: list[tuple[datetime | None, int]] = []
    for p in picks:
        pnl = _safe_pnl(p)
        if pnl is None:
            continue
        outcome = 1 if pnl > 0 else 0
        ts = _parse_iso(p.get("closed_at") or p.get("opened_at"))
        cleaned.append((ts, outcome))

    if len(cleaned) < min_n:
        return None

    cleaned.sort(key=lambda x: (x[0] is None,
                                x[0] or datetime.min.replace(tzinfo=timezone.utc)))
    outcomes = [o for _, o in cleaned]
    streaks = compute_streaks(outcomes)
    win_lengths = [length for sign, length in streaks if sign > 0]
    loss_lengths = [length for sign, length in streaks if sign < 0]
    all_lengths = [length for _, length in streaks]
    max_win = max(win_lengths) if win_lengths else 0
    max_loss = max(loss_lengths) if loss_lengths else 0
    last_sign, last_len = streaks[-1]
    current_streak = last_len if last_sign > 0 else -last_len
    return {
        "n": int(len(outcomes)),
        "max_win_streak": int(max_win),
        "max_loss_streak": int(max_loss),
        "current_streak": int(current_streak),
        "n_streaks": int(len(streaks)),
        "win_streak_count": int(len(win_lengths)),
        "loss_streak_count": int(len(loss_lengths)),
        "p25_streak_length": round(_percentile(all_lengths, 25), 4),
        "median_streak_length": round(_percentile(all_lengths, 50), 4),
        "p75_streak_length": round(_percentile(all_lengths, 75), 4),
        "mean_streak_length": round(
            sum(all_lengths) / len(all_lengths) if all_lengths else 0.0, 4),
    }


def analyze_all(picks: list[dict],
                min_n: int = DEFAULT_MIN_N) -> dict:
    by_strategy: dict[str, list[dict]] = defaultdict(list)
    for p in picks:
        by_strategy[p.get("strategy") or "unknown"].append(p)

    out: list[dict] = []
    for strat, sub in by_strategy.items():
        r = analyze_strategy(sub, min_n)
        if r is None:
            continue
        r["strategy"] = strat
        out.append(r)
    out.sort(key=lambda r: -r["max_loss_streak"])
    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "config": {"min_n": min_n},
        "n_strategies": len(out),
        "strategies": out,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--min-n", type=int, default=DEFAULT_MIN_N)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    with PICKS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    picks = data.get("picks", {}).get("recent_closed", [])

    summary = analyze_all(picks, args.min_n)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    if not args.quiet:
        print(f"strategies analysed: {summary['n_strategies']}")
        print("top 10 by max-loss-streak:")
        for r in summary["strategies"][:10]:
            print(f"  {r['strategy'][:30]:<30} max_W={r['max_win_streak']:>3} "
                  f"max_L={r['max_loss_streak']:>3} cur={r['current_streak']:>+4} "
                  f"n_streaks={r['n_streaks']:>3} n={r['n']}")
        print(f"JSON: {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
