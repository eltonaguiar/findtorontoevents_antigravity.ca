"""Per-group Wilson score confidence interval for win rate.

Loads closed_picks.json, filters MATICUSDT/-0.15 ghost rows, groups by
asset_class (or strategy when asset_class is missing), and prints a table
sorted by n descending. Flags groups where CI_hi < --kill-threshold (default
0.50) as kill candidates.

Exit non-zero when any group with n >= --min-n has CI_hi < kill_threshold.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from tools.data_integrity._common import (  # noqa: E402
    CLOSED_PICKS,
    classify_asset,
    is_ghost_row,
    load_json_list,
)


def wilson_ci(wins: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """Return (point_wr, ci_lo, ci_hi) using Wilson score interval."""
    if n == 0:
        return 0.0, 0.0, 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)) / denom
    return p, max(0.0, centre - half), min(1.0, centre + half)


def pick_is_win(p: dict) -> bool | None:
    pnl = p.get("pnl_pct")
    if pnl is None:
        er = str(p.get("exit_reason", "")).upper()
        if "TP" in er or "TAKE" in er:
            return True
        if "SL" in er or "STOP" in er:
            return False
        return None
    try:
        return float(pnl) > 0
    except Exception:
        return None


def group_key(p: dict) -> str:
    ac = classify_asset(p)
    if ac != "UNKNOWN":
        return f"asset:{ac}"
    strat = p.get("strategy") or "unknown_strategy"
    return f"strat:{strat}"


def build_stats(rows: list[dict]) -> list[dict]:
    groups: dict[str, list[bool]] = defaultdict(list)
    for p in rows:
        if is_ghost_row(p):
            continue
        res = pick_is_win(p)
        if res is None:
            continue
        groups[group_key(p)].append(res)

    out = []
    for g, results in groups.items():
        n = len(results)
        wins = sum(1 for r in results if r)
        wr, lo, hi = wilson_ci(wins, n)
        out.append(
            {"group": g, "n": n, "wins": wins, "wr": wr, "ci_lo": lo, "ci_hi": hi}
        )
    out.sort(key=lambda r: -r["n"])
    return out


def print_table(stats: list[dict], min_n: int, kill_threshold: float) -> None:
    print(f"{'GROUP':40s} {'n':>6s} {'wr':>7s} {'ci_lo':>7s} {'ci_hi':>7s}  flag")
    print("-" * 80)
    for s in stats:
        flag = ""
        if s["n"] >= min_n and s["ci_hi"] < kill_threshold:
            flag = "KILL_CANDIDATE"
        elif s["n"] < min_n:
            flag = "under_sampled"
        print(
            f"{s['group'][:40]:40s} {s['n']:6d} {s['wr']*100:6.2f}% "
            f"{s['ci_lo']*100:6.2f}% {s['ci_hi']*100:6.2f}%  {flag}"
        )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--closed", default=CLOSED_PICKS)
    ap.add_argument("--min-n", type=int, default=10)
    ap.add_argument("--kill-threshold", type=float, default=0.50)
    args = ap.parse_args(argv)

    rows = load_json_list(args.closed)
    stats = build_stats(rows)

    print("=" * 80)
    print("WIN RATE / WILSON 95% CI REPORT")
    print("=" * 80)
    print_table(stats, args.min_n, args.kill_threshold)

    kills = [s for s in stats if s["n"] >= args.min_n and s["ci_hi"] < args.kill_threshold]
    print(f"\nkill candidates (n >= {args.min_n}, CI_hi < {args.kill_threshold*100:.0f}%): {len(kills)}")
    for k in kills:
        print(f"  - {k['group']}: n={k['n']}, wr={k['wr']*100:.2f}%, ci_hi={k['ci_hi']*100:.2f}%")

    if kills:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
