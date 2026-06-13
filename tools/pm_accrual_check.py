#!/usr/bin/env python3
"""pm_accrual_check.py — loud, NON-BLOCKING freshness gate for the PM lead/lag lane.

Context (2026-06-13): PRs #567 (pm_odds_history) + #575 (pm_macro_overlay fetcher
schema fix) merged. Risk review found the overlay no-op is RE-ARMED unless its
output persists — so this checker exists to make a future silent failure LOUD
(`::error` annotation) instead of another 6-day dead lane. It NEVER blocks pick
emission (enrichment must not gate the scanner); it only surfaces.

Three assertions (M-107 + quant-desk spec):
  A. ACCRUAL   pm_odds_history.jsonl: last-line date within 36h AND line count
               grew vs the prior committed state (passed via --prev-lines).
  B. OVERLAY   pm_macro_overlay_signals.json exists AND has a non-empty payload
               (picks/signals) — the pre-#575 no-op produced empty/absent output.
  C. READINESS distinct dates in the history; <14 => INSUFFICIENT_HISTORY (no
               lead/lag claim is statistically valid yet — quant's gate).

Exit 0 always in --soft mode (default): prints PASS/WARN/FAIL lines + a single
`::error`/`::warning` annotation. Use --strict to exit non-zero (for a dedicated
monitor job, never inside the emission path).

For the first 48h after merge, assertion A is WARN-only (one date seeded in the
PR) — hardens automatically once n_dates>=2.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HIST = REPO / "prediction_market_agents" / "data" / "pm_odds_history.jsonl"
OVERLAY = REPO / "prediction_market_agents" / "data" / "pm_macro_overlay_signals.json"
LEADLAG = REPO / "prediction_market_agents" / "data" / "pm_leadlag_report.json"
READINESS_MIN_DATES = 14


def _dates_from_history():
    if not HIST.exists():
        return [], 0
    lines = [ln for ln in HIST.read_text().splitlines() if ln.strip()]
    dates = set()
    for ln in lines:
        try:
            rec = json.loads(ln)
        except Exception:
            continue
        d = rec.get("date") or (rec.get("ts") or rec.get("timestamp") or "")[:10]
        if d:
            dates.add(str(d)[:10])
    return sorted(dates), len(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prev-lines", type=int, default=-1,
                    help="line count from the prior commit (for growth check)")
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero on FAIL (monitor job only; never in emit path)")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    dates, n_lines = _dates_from_history()
    n_dates = len(dates)
    problems, warns = [], []

    # A. accrual
    if not dates:
        problems.append("A/ACCRUAL: pm_odds_history.jsonl empty or missing")
    else:
        try:
            last = datetime.fromisoformat(dates[-1] + "T00:00:00+00:00")
            age_h = (now - last).total_seconds() / 3600
        except Exception:
            age_h = 1e9
        if age_h > 36:
            (warns if n_dates < 2 else problems).append(
                f"A/ACCRUAL: newest history date {dates[-1]} is {age_h:.0f}h old (>36h)")
        if args.prev_lines >= 0 and n_lines <= args.prev_lines and n_dates >= 2:
            problems.append(
                f"A/ACCRUAL: line count did not grow ({n_lines} <= prev {args.prev_lines})")

    # B. overlay non-empty
    if not OVERLAY.exists():
        problems.append("B/OVERLAY: pm_macro_overlay_signals.json absent "
                        "(gitignored-not-persisted, or fetcher no-op)")
    else:
        try:
            ov = json.loads(OVERLAY.read_text())
            payload = ov.get("picks") or ov.get("signals") or ov.get("series") or []
            if not payload:
                problems.append("B/OVERLAY: snapshot present but payload EMPTY "
                                "(fetcher returned nothing — the pre-#575 no-op signature)")
        except Exception as exc:
            problems.append(f"B/OVERLAY: unreadable ({exc})")

    # C. readiness
    if n_dates < READINESS_MIN_DATES:
        warns.append(f"C/READINESS: {n_dates}/{READINESS_MIN_DATES} distinct dates "
                     "— lead/lag verdict is INSUFFICIENT_HISTORY (no claim valid yet)")

    print(f"[pm-accrual] dates={n_dates} lines={n_lines} overlay={'ok' if OVERLAY.exists() else 'MISSING'} "
          f"leadlag={'ok' if LEADLAG.exists() else 'absent'}")
    for w in warns:
        print(f"::warning title=pm-accrual::{w}")
    for p in problems:
        print(f"::error title=pm-accrual::{p}")
    if problems:
        print(f"[pm-accrual] FAIL ({len(problems)} hard problem(s))")
        return 1 if args.strict else 0
    print("[pm-accrual] PASS" + (" (with readiness warnings)" if warns else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
