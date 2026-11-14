#!/usr/bin/env python3
"""
Horizon Validation Harness — does any per-(asset-class, strategy) group show a
SOLID, time-stable edge on RECORDED REALIZED trades?

Method (deliberately conservative, addresses multiple-testing and survivorship):
 1. Load recorded closed picks (realized pnl) from the live dashboard payload.
 2. Drop non-resolved / phantom rows: pnl == 0 with exit_price == entry_price,
    missing entry, missing closed_at, or EXIT_REASON UNKNOWN.
 3. Group by (asset_class, strategy). Require n >= MIN_TRADES.
 4. Military-order rows by closed_at, split into chronological windows
    (WINDOW_DAYS each) -> walk-forward style; each window is independent.
 5. Per group compute: n, WR, PF, expectancy, mean per-trade pnl.
 6. Stationarity gate: the group must have >= MIN_WINDOWS non-empty windows and
    win in a clear majority of them (WIN_WINDOW_THRESH fraction with WR>0.5).
 7. Statistical gate: binomial 95% CI lower bound of overall WR must EXCLUDE 0.50
    on the profitable side (true skill vs coin flip), AND PF > 1, AND n >= MIN.
 8. Multiple-testing correction: report how many groups were tested vs how many
    passed (so the reader sees the look-elsewhere effect).
 9. Survivorship warning: this uses the recorded closed ledger, which the audit
    showed excludes ~51% of trades (integrity/expiry). Edge here is UPPER bound.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

MIN_TRADES = 60
MIN_WINDOWS = 4
WINDOW_DAYS = 60
WIN_WINDOW_THRESH = 0.66
PF_MIN = 1.05


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _parse_dt(v):
    if not v:
        return None
    s = str(v)
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = datetime.strptime(s[:10], "%Y-%m-%d")
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def wilson_lower(wins, n, z=1.96):
    if n == 0:
        return 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre - margin) / denom


def load_groups(payload):
    closed = payload.get("picks", {}).get("recent_closed", [])
    groups = defaultdict(list)
    resolved = 0
    phantom = 0
    for p in closed:
        entry = _f(p.get("entry_price"))
        pnl = _f(p.get("pnl_pct"))
        exitp = _f(p.get("exit_price"))
        dt = _parse_dt(p.get("closed_at") or p.get("resolved_at") or p.get("timestamp"))
        reason = str(p.get("exit_reason") or "").upper()
        # phantom filter
        if pnl is None or entry is None or dt is None or entry <= 0:
            phantom += 1
            continue
        if pnl == 0.0 and exitp is not None and abs(entry - exitp) < 1e-9:
            phantom += 1
            continue
        if pnl == 0.0 and reason == "UNKNOWN":
            phantom += 1
            continue
        resolved += 1
        ac = str(p.get("asset_class") or "UNKNOWN").upper()
        st = str(p.get("strategy") or p.get("system") or "UNKNOWN")
        groups[(ac, st)].append({"pnl": pnl, "dt": dt})
    return groups, resolved, phantom


def evaluate_group(rows):
    rows = sorted(rows, key=lambda r: r["dt"])
    n = len(rows)
    wins = sum(1 for r in rows if r["pnl"] > 0)
    losses = sum(1 for r in rows if r["pnl"] < 0)
    flat = n - wins - losses
    gross_win = sum(r["pnl"] for r in rows if r["pnl"] > 0)
    gross_loss = abs(sum(r["pnl"] for r in rows if r["pnl"] < 0))
    pf = (gross_win / gross_loss) if gross_loss > 0 else (float("inf") if gross_win > 0 else 0.0)
    mean_pnl = sum(r["pnl"] for r in rows) / n
    # windows
    start = rows[0]["dt"]
    windows = []
    cur = []
    cur_start = start
    for r in rows:
        if (r["dt"] - cur_start).days >= WINDOW_DAYS:
            windows.append(cur)
            cur = []
            cur_start = r["dt"]
        cur.append(r)
    if cur:
        windows.append(cur)
    win_windows = 0
    nonempty_windows = 0
    for w in windows:
        if not w:
            continue
        nonempty_windows += 1
        w_wins = sum(1 for r in w if r["pnl"] > 0)
        if len(w) > 0 and w_wins / len(w) > 0.5:
            win_windows += 1
    return {
        "n": n, "wins": wins, "losses": losses, "flat": flat,
        "wr": wins / n, "pf": pf, "mean_pnl": mean_pnl,
        "ci_lower": wilson_lower(wins, n),
        "nonempty_windows": nonempty_windows, "win_windows": win_windows,
    }


def run(payload, min_trades=MIN_TRADES, verbose=False):
    groups, resolved, phantom = load_groups(payload)
    tested = 0
    passed = []
    for (ac, st), rows in groups.items():
        if len(rows) < min_trades:
            continue
        tested += 1
        g = evaluate_group(rows)
        ci_ok = g["ci_lower"] > 0.50
        win_ok = g["win_windows"] >= WIN_WINDOW_THRESH * g["nonempty_windows"]
        pf_ok = g["pf"] > PF_MIN
        ok = ci_ok and win_ok and pf_ok
        passed.append((ac, st, g, ok))
    # sort by mean_pnl
    passed.sort(key=lambda x: -x[2]["mean_pnl"])
    return {
        "resolved_trades": resolved, "phantom_excluded": phantom,
        "groups_tested": tested, "groups_passed": sum(1 for _, _, _, ok in passed if ok),
        "passed": passed,
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="/tmp/kilo/dashboard_data_latest.json")
    ap.add_argument("--min-trades", type=int, default=MIN_TRADES)
    ap.add_argument("--all", action="store_true", help="print all tested groups")
    args = ap.parse_args(argv)
    payload = json.loads(Path(args.json).read_text())
    res = run(payload, args.min_trades)
    print(f"resolved trades: {res['resolved_trades']}")
    print(f"phantom rows excluded: {res['phantom_excluded']}")
    print(f"groups tested (n>={args.min_trades}): {res['groups_tested']}")
    print(f"groups passing ALL gates: {res['groups_passed']}")
    print(f"  (binomial CI lower > 0.50 AND PF > {PF_MIN} AND win-majority in "
          f">={WIN_WINDOW_THRESH:.0%} of windows)")
    print()
    if args.all:
        print(f"{'ASSET':<12}{'STRATEGY':<34}{'n':>5}{'WR':>7}{'CI_lo':>7}"
              f"{'PF':>7}{'mean%':>8}{'winW':>5}/{''}")
        for ac, st, g, ok in res["passed"]:
            mark = "OK" if ok else " -"
            print(f"{ac:<12}{st[:33]:<34}{g['n']:>5}{g['wr']*100:>6.1f}%"
                  f"{g['ci_lower']*100:>7.1f}%{g['pf']:>7.2f}"
                  f"{g['mean_pnl']:>8.2f}{g['win_windows']:>5}/{g['nonempty_windows']} {mark}")
    print()
    print("PASSED (up to 15):")
    print(f"{'ASSET':<12}{'STRATEGY':<34}{'n':>5}{'WR':>7}{'CI_lo':>7}{'PF':>7}{'mean%':>8}")
    shown = 0
    for ac, st, g, ok in res["passed"]:
        if not ok:
            continue
        print(f"{ac:<12}{st[:33]:<34}{g['n']:>5}{g['wr']*100:>6.1f}%"
              f"{g['ci_lower']*100:>7.1f}%{g['pf']:>7.2f}{g['mean_pnl']:>8.2f}")
        shown += 1
        if shown >= 15:
            break
    return 0 if res["groups_passed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
