#!/usr/bin/env python3
"""Interior-gap audit for the FX cache written by tools/fx_spot_backfill.py.

Gap definition: BUSINESS days (Mon-Fri), with documented FX market closures
(New Year, Good Friday, Easter Monday, Christmas, Boxing Day) excluded. A gap
is the count of expected-but-missing business days strictly between two
consecutive observations. Weekends and those holidays are never counted.

Writes reports/block1_r02_fx_gap_audit.json.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = REPO_ROOT / "data" / "forex_rate_cache"
OUT = REPO_ROOT / "reports" / "block1_r02_fx_gap_audit.json"
GAP_THRESHOLD_BD = 5


def easter(year: int) -> date:
    """Anonymous Gregorian algorithm."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def market_holidays(years: range) -> set[date]:
    out: set[date] = set()
    for y in years:
        e = easter(y)
        out |= {
            date(y, 1, 1),                     # New Year's Day
            e - timedelta(days=2),             # Good Friday
            e + timedelta(days=1),             # Easter Monday
            date(y, 12, 25),                   # Christmas
            date(y, 12, 26),                   # Boxing Day
        }
        # Observed-shift: a holiday on a weekend is typically taken on the
        # neighbouring weekday for New Year / Christmas.
        for h in (date(y, 1, 1), date(y, 12, 25), date(y, 12, 26)):
            if h.weekday() == 5:
                out.add(h + timedelta(days=2))
            elif h.weekday() == 6:
                out.add(h + timedelta(days=1))
    return out


def expected_business_days(start: date, end: date, holidays: set[date]) -> int:
    n, d = 0, start
    while d < end:  # strictly interior
        d += timedelta(days=1)
        if d >= end:
            break
        if d.weekday() < 5 and d not in holidays:
            n += 1
    return n


def audit_pair(path: Path, holidays: set[date]) -> dict:
    dates: list[date] = []
    for line in path.read_text().splitlines()[1:]:
        if not line.strip():
            continue
        dates.append(date.fromisoformat(line.split(",")[0]))
    dates.sort()
    uniq = sorted(set(dates))
    dups = len(dates) - len(uniq)
    gaps = []
    for a, b in zip(uniq, uniq[1:]):
        missing = expected_business_days(a, b, holidays)
        if missing > GAP_THRESHOLD_BD:
            gaps.append({"from": a.isoformat(), "to": b.isoformat(),
                         "missing_business_days": missing})
    return {
        "pair": path.stem,
        "observations": len(dates),
        "first_date": uniq[0].isoformat(),
        "last_date": uniq[-1].isoformat(),
        "duplicate_dates": dups,
        "interior_gaps_gt_5bd": gaps,
    }


def main() -> int:
    files = sorted(CACHE_DIR.glob("*.csv"))
    years = range(2018, date.today().year + 2)
    holidays = market_holidays(years)
    pairs = [audit_pair(f, holidays) for f in files]
    gapped = [p["pair"] for p in pairs if p["interior_gaps_gt_5bd"]]
    frac = len(gapped) / len(pairs) if pairs else 0.0
    summary = {
        "generated": date.today().isoformat(),
        "gap_definition": ("business days (Mon-Fri) minus documented FX market "
                           "closures (New Year, Good Friday, Easter Monday, "
                           "Christmas, Boxing Day); weekends never counted"),
        "threshold_business_days": GAP_THRESHOLD_BD,
        "pairs_audited": len(pairs),
        "pairs_with_gaps": len(gapped),
        "gapped_fraction": round(frac, 4),
        "downgrade_to_blocked_data": frac > 0.20,
        "gate": ("PASS" if not gapped and frac <= 0.20 else
                 ("STOP_DOWNGRADE" if frac > 0.20 else "FAIL")),
        "pairs": pairs,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"pairs audited: {len(pairs)}")
    print(f"pairs with >5bd interior gaps: {len(gapped)} ({frac:.2%})")
    print(f"gate: {summary['gate']}  downgrade: {summary['downgrade_to_blocked_data']}")
    print(f"wrote {OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
