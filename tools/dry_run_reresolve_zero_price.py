#!/usr/bin/env python3
"""Dry-run re-resolve of the stale ``exit_price=0.0`` rows — ON A COPY ONLY.

Context (issue #748): 38 rows in ``picks.recent_closed`` carry
``exit_price=0.0 / pnl_pct=0.0`` (all TIME_EXIT). They were resolved BEFORE the
2026-10-18 ``_priceless_close`` guard landed; the resolver skips already-resolved
picks (``if pick_id in resolved_ids: continue``), so the guard never re-healed
them. Production already runs the fixed code (verified: last successful deploy
sha 620565856f contains f3cc4433dd6) — the remedy is a RE-RESOLVE, not a redeploy.

This tool simulates that re-resolve on an in-memory COPY using the REAL
``_priceless_close`` function imported from ``audit_trail.universal_pick_resolver``
(the exact production guard — not a reimplementation). For each 0.0 row it applies
the same decision the fixed TIME_EXIT branch makes:

    if _priceless_close(exit_price, entry): status=UNRESOLVED_NO_PRICE, pnl=None

Read-only: never writes to the payload, DB, or production. Reports before/after:
  * rows at exit_price==0.0  (expect 38 -> 0)
  * rows at UNRESOLVED_NO_PRICE (expect 0 -> 38)
  * rows still contributing to PF/WR (expect 0 after — None pnl is excluded)

Exit 1 (CONTINGENCY) if any row remains at 0.0 after the dry-run re-resolve.
"""
from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, ".")
from audit_trail.universal_pick_resolver import _priceless_close  # the REAL guard


def _is_zero(v) -> bool:
    try:
        return v is not None and float(v) == 0.0
    except (TypeError, ValueError):
        return False


def _rows(payload) -> list[dict]:
    # Accept a bare list (a saved zero-rows copy) or a full payload dict.
    if isinstance(payload, list):
        return payload
    if isinstance(payload.get("rows"), list):
        return payload["rows"]
    return (payload.get("picks", {}) or {}).get("recent_closed", []) or []


def dry_run(payload: dict) -> int:
    rows = _rows(payload)
    zero_rows = [
        r for r in rows
        if _is_zero(r.get("exit_price"))
        and str(r.get("status", "")).upper() != "UNRESOLVED_NO_PRICE"
    ]

    before_zero = len(zero_rows)
    before_unresolved = sum(
        1 for r in rows if str(r.get("status", "")).upper() == "UNRESOLVED_NO_PRICE"
    )

    # Re-resolve the COPY with the REAL guard (mirrors the fixed TIME_EXIT branch).
    after = []
    still_zero = 0
    for r in zero_rows:
        entry = r.get("entry_price")
        exit_price = r.get("exit_price")
        if _priceless_close(exit_price, entry):
            r = dict(r)  # COPY, never mutate the source row
            r["exit_price"] = None
            r["pnl_pct"] = None
            r["status"] = "UNRESOLVED_NO_PRICE"
            r["_mtm"] = "unresolved"
            r["exit_time_estimated"] = True
            after.append(r)
        else:
            # Guard did NOT catch it — a real 0.0 slipped through: contingency.
            still_zero += 1
            after.append(dict(r))

    after_zero = sum(1 for r in after if _is_zero(r.get("exit_price")))
    after_unresolved = sum(
        1 for r in after if str(r.get("status", "")).upper() == "UNRESOLVED_NO_PRICE"
    )
    # A row contributes to PF/WR only if it has a numeric pnl and a resolved
    # CLOSED/WON/LOST status. UNRESOLVED_NO_PRICE + pnl=None => excluded.
    contributing_after = sum(
        1 for r in after
        if r.get("pnl_pct") is not None
        and str(r.get("status", "")).upper() in ("CLOSED", "WON", "LOST")
    )

    print("=== DRY-RUN RE-RESOLVE (copy only; production untouched) ===")
    print(f"scanned rows:                 {len(rows)}")
    print(f"exit_price==0.0 BEFORE:       {before_zero}")
    print(f"UNRESOLVED_NO_PRICE BEFORE:   {before_unresolved}")
    print("-" * 46)
    print(f"exit_price==0.0 AFTER:        {after_zero}   (expect 0)")
    print(f"UNRESOLVED_NO_PRICE AFTER:    {after_unresolved}   (expect {before_unresolved + before_zero})")
    print(f"contributing to PF/WR AFTER:  {contributing_after}   (expect 0 — None pnl excluded)")
    print("-" * 46)

    if after_zero != 0 or still_zero != 0:
        print(
            f"CONTINGENCY TRIGGERED: {still_zero} row(s) remained at 0.0 after the "
            "real _priceless_close guard — STOP, report the code path (no patch-around)."
        )
        return 1
    print("PASS: 0 rows at 0.0; all re-resolved to UNRESOLVED_NO_PRICE; excluded from PF/WR.")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--payload", required=True, help="dashboard_data.json or a zero-rows copy")
    args = ap.parse_args()
    with open(args.payload, encoding="utf-8") as f:
        payload = json.load(f)
    sys.exit(dry_run(payload))


if __name__ == "__main__":
    main()
