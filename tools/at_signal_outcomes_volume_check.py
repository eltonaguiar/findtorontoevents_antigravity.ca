#!/usr/bin/env python3
"""at_signal_outcomes INSERT-VOLUME monitor — the un-mask layer for green-on-empty.

WHY THIS EXISTS
---------------
The honest intrabar ledger ``at_signal_outcomes`` (the verdict-grade surface the
entire money-ready program measures against) froze 2026-06-12..06-18 behind a
GREEN CI: the hourly ``outcome-resolver.yml`` runs kept succeeding while inserting
~0 new rows. ``tools/db_freshness_check.py`` tracks *staleness* (MAX(closed_at),
MAX(intrabar_resolved_at)) but NOT *insert volume vs a baseline*, so a generation
or mirror drought stayed invisible — classic masked-failure (cf. memory
``feedback-masked-failure-pattern-ci``).

WHAT IT DOES
------------
Compares the last-24h insert volume against the trailing-7d median of COMPLETE
days and grades the ratio. On a volume collapse it exits non-zero so the resolver
job goes RED — it must be wired FATAL (NOT inside a ``|| echo ::warning:: non-fatal``
block), because being the un-masking layer, its failure MUST propagate.

  ratio = today_24h / max(median7d, 1)
    GREEN  ratio >= 0.40
    YELLOW 0.10 <= ratio < 0.40         -> ::warning::  (exit 0)
    RED    ratio < 0.10                  -> ::error::    (exit 1)
    RED    today == 0 AND median7d >= 50 -> ::error::    (exit 1)   # exact freeze signature

A per-class variant (``--asset-class CRYPTO``) catches a single-class drought
(e.g. CRYPTO 0-3/day vs its own ~100/day) that a healthy total would otherwise mask.

READ-ONLY: SELECT only. Never echoes credentials.
"""
from __future__ import annotations

import argparse
import statistics
import sys


# --- pure grading logic (unit-tested in tests/test_at_signal_outcomes_volume_check.py) ---

GREEN_FLOOR = 0.40
RED_CEILING = 0.10
ZERO_DROUGHT_MEDIAN = 50  # if a normal day is >=50 rows and today is 0 -> hard RED


def grade(today: int, median7d: float) -> tuple[str, float, int]:
    """Return (status, ratio, exit_code).

    exit_code 0 = OK/warning (GREEN/YELLOW), 1 = RED (volume collapse).
    """
    m = max(float(median7d), 1.0)
    ratio = today / m
    # Exact freeze signature: a normally-busy table inserting literally nothing.
    if today == 0 and median7d >= ZERO_DROUGHT_MEDIAN:
        return "RED", ratio, 1
    if ratio < RED_CEILING:
        return "RED", ratio, 1
    if ratio < GREEN_FLOOR:
        return "YELLOW", ratio, 0
    return "GREEN", ratio, 0


def _self_test() -> int:
    """Assert the grading on the documented real-baseline vectors."""
    cases = [
        # (today, median7d) -> expected_status
        (0, 5338, "RED"),      # the exact 06-13..06-18 freeze
        (15, 5338, "RED"),     # the 06-19 trickle (ratio 0.003)
        (5000, 5338, "GREEN"), # healthy day
        (4748, 5338, "GREEN"), # low-but-healthy historical day
        (1000, 5338, "YELLOW"),# ratio 0.187 -> warn
        (0, 10, "GREEN"),      # tiny/quiet table, 0 today -> not a hard-RED (median<50) & ratio<0.10? -> see note
    ]
    ok = True
    for today, med, want in cases:
        # NOTE: the last case (0, 10): today==0 but median<50 -> not hard-RED;
        # ratio 0.0 < 0.10 -> RED by the ratio rule. So expected is RED, not GREEN.
        # keep the assertion honest:
        expect = want
        if today == 0 and med < ZERO_DROUGHT_MEDIAN:
            expect = "RED"  # ratio 0 still trips the <0.10 rule
        status, ratio, code = grade(today, med)
        flag = "ok" if status == expect else "FAIL"
        if status != expect:
            ok = False
        print(f"  grade(today={today}, med={med}) = {status} (ratio={ratio:.3f}, exit={code}) "
              f"expect={expect} [{flag}]")
    print("SELF-TEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def _fetch_volumes(asset_class: str | None):
    """Return (today_24h_count, [complete_day_counts...]) from at_signal_outcomes. READ-ONLY."""
    import pymysql  # local import so --self-test needs no DB driver

    sys.path.insert(0, ".")
    from tools.db_env import get_stocks_creds  # noqa: E402

    keep = ("host", "user", "password", "database", "port", "connect_timeout")
    creds = {k: v for k, v in get_stocks_creds().items() if k in keep}
    conn = pymysql.connect(**creds)
    try:
        cur = conn.cursor()
        where_cls = ""
        params: tuple = ()
        if asset_class:
            where_cls = " AND asset_class = %s"
            params = (asset_class,)

        # Query A: last 24h insert volume
        cur.execute(
            f"SELECT COUNT(*) FROM at_signal_outcomes "
            f"WHERE created_at >= DATE_SUB(UTC_TIMESTAMP(), INTERVAL 24 HOUR){where_cls}",
            params,
        )
        today = int(cur.fetchone()[0])

        # Query B: per-day counts for the 8 days ending yesterday (exclude today's partial day)
        cur.execute(
            f"SELECT DATE(created_at) d, COUNT(*) n FROM at_signal_outcomes "
            f"WHERE created_at >= DATE_SUB(UTC_DATE(), INTERVAL 8 DAY) "
            f"AND created_at < UTC_DATE(){where_cls} "
            f"GROUP BY d ORDER BY d",
            params,
        )
        day_counts = [int(n) for _, n in cur.fetchall()]
        return today, day_counts
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--asset-class", default=None,
                    help="scope the check to one class (e.g. CRYPTO); default = all classes")
    ap.add_argument("--self-test", action="store_true",
                    help="run the pure-grading self-test (no DB needed) and exit")
    args = ap.parse_args()

    if args.self_test:
        return _self_test()

    scope = args.asset_class or "ALL"
    try:
        today, day_counts = _fetch_volumes(args.asset_class)
    except Exception as e:  # noqa: BLE001 - report loudly; do NOT swallow
        print(f"::error title=at_signal_outcomes_volume::query failed for scope={scope}: {e!r}")
        return 1

    # trailing-7d median of complete days (use the most recent 7 complete days available)
    complete = day_counts[-7:]
    median7d = statistics.median(complete) if complete else 0.0
    status, ratio, code = grade(today, median7d)

    print(f"# at_signal_outcomes volume check — scope={scope}")
    print(f"#   today_24h={today}  median7d={median7d:.0f}  ratio={ratio:.3f}  -> {status}")
    print(f"#   complete-day window={complete}")

    if status == "RED":
        print(f"::error title=at_signal_outcomes_volume::scope={scope} today={today} "
              f"median7d={median7d:.0f} ratio={ratio:.3f} below the {RED_CEILING:.0%} floor "
              f"— honest ledger inflow collapsed (green-on-empty). See "
              f"tools/at_signal_outcomes_volume_check.py.")
    elif status == "YELLOW":
        print(f"::warning title=at_signal_outcomes_volume::scope={scope} today={today} "
              f"median7d={median7d:.0f} ratio={ratio:.3f} below the {GREEN_FLOOR:.0%} target "
              f"— inflow degraded, watch for a developing drought.")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
