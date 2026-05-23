#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Re-resolve historical non-crypto picks under outcome_resolver v2.

Status: SKELETON / DRY-RUN ONLY by default.
This script does NOT modify any historical pick files when run with --dry-run.
A separate, explicitly-approved follow-up PR is required to apply the rewrite.

What it does
------------
For every closed non-crypto pick (FOREX/COMMODITY/EQUITY/ETF/BOND/FUTURES) in
the upstream source files:

  1. Pull entry_price, take_profit, stop_loss, entry_date.
  2. Fetch the daily OHLC window from yfinance for that holding period.
  3. Run alpha_engine.outcome_resolver._scan_ohlc_for_touch() for a
     TP_HIT_REPLAY or SL_HIT_REPLAY label.
  4. If neither was touched: record TIME_EXIT_REPLAY at the last close.
  5. Apply the v2 asset-class-gated WIN threshold (5bp non-crypto / 0.1bp crypto)
     via classify_outcome().
  6. Stamp resolver_version="v2", preserve _legacy_pnl_pct + _legacy_exit_reason.
  7. Emit a delta CSV summarizing label flips per pick.

Why the script is separate from the resolver PR
-----------------------------------------------
The resolver code change (this PR: fix/non-crypto-resolver-bar-replay-2026-04-28)
is the foundation. Re-resolving ~1,860 historical non-crypto picks is a separate
operation with its own risks (yfinance rate limits, label inversion shock to
ML retraining, race with the cron resolver). Run order per
``reports/action_B_resolver_2026_04_27.md`` §9.2:

    Day 0: PR-B1 (resolver code) — THIS PR
    Day 0: PR-B2 (this script + dry-run report)
    Day 1: PR-B3 (pause cron, run for real, commit corrected files)

Verification commands
---------------------
After running this script (when authorized):

    # 1. Rebuild dashboard payload (will pick up corrected closed picks)
    #    NOTE: per CLAUDE.md, don't run dashboard generators locally — let the
    #    hourly workflow do it. Only manual rebuild on a maintainer's box.
    #
    # 2. Re-run the noise-share check (taken verbatim from the design doc):
    python -c "
    import json
    with open('audit_trail/data/dashboard_payload.json') as f:
        rc = json.load(f)['picks']['recent_closed']
    for cls in ['FOREX','COMMODITY','EQUITY','ETF','BOND']:
        n=wins=noise=0
        for p in rc:
            if (p.get('asset_class') or '').upper()!=cls: continue
            n+=1
            try: v=float(p.get('pnl_pct') or 0)
            except: v=0
            if v>0:
                wins+=1
                if abs(v)<0.05: noise+=1
        pct = (noise/wins*100) if wins else 0.0
        print(f'{cls:10s} n={n:4d} wins={wins:4d} noise={noise:4d} ({pct:5.2f}%)')
    "

Expected post-fix output: every non-crypto class shows noise share <30%.

Source files re-resolved (per design doc §5.1)
----------------------------------------------
Top sources for the 1,897 non-crypto historical rows:
  * copy_trader_intel/data/multi_asset_picks.json
  * copy_trader_intel/data/forex_copytrader_picks.json
  * copy_trader_intel/data/stocks_copytrader_picks.json
  * copy_trader_intel/data/commodity_copytrader_picks.json
  * copy_trader_intel/data/cta_picks.json
  * copy_trader_intel/data/non_crypto_consensus_picks.json
  * genome/data/revival_kimi_riseoftheclaw_picks.json
  * alpha_engine/data/closed_picks.json
  * alpha_engine/data/closed_picks_fast.json

USAGE
=====
    python tools/re_resolve_historical_v2.py --dry-run            # safe (default)
    python tools/re_resolve_historical_v2.py --dry-run --report   # write delta CSV only
    python tools/re_resolve_historical_v2.py --apply              # REAL writes, requires
                                                                  # outcome-resolver.yml
                                                                  # cron paused first
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from alpha_engine import outcome_resolver as orv  # noqa: E402

SOURCE_FILES = [
    REPO_ROOT / "alpha_engine" / "data" / "closed_picks.json",
    REPO_ROOT / "alpha_engine" / "data" / "closed_picks_fast.json",
    REPO_ROOT / "copy_trader_intel" / "data" / "multi_asset_picks.json",
    REPO_ROOT / "copy_trader_intel" / "data" / "forex_copytrader_picks.json",
    REPO_ROOT / "copy_trader_intel" / "data" / "stocks_copytrader_picks.json",
    REPO_ROOT / "copy_trader_intel" / "data" / "commodity_copytrader_picks.json",
    REPO_ROOT / "copy_trader_intel" / "data" / "cta_picks.json",
    REPO_ROOT / "copy_trader_intel" / "data" / "non_crypto_consensus_picks.json",
    REPO_ROOT / "genome" / "data" / "revival_kimi_riseoftheclaw_picks.json",
]

DELTA_CSV = REPO_ROOT / "reports" / "re_resolve_delta_2026_04_28.csv"


def iter_picks(obj):
    """Yield (parent_list, index, pick) for every dict that looks like a pick."""
    if isinstance(obj, list):
        if obj and isinstance(obj[0], dict) and "entry_price" in obj[0]:
            for i, p in enumerate(obj):
                yield obj, i, p
        return
    if isinstance(obj, dict):
        for key in ("picks", "closed_picks", "trades_list", "closed", "items", "history"):
            v = obj.get(key)
            if isinstance(v, list) and v and isinstance(v[0], dict) and "entry_price" in v[0]:
                for i, p in enumerate(v):
                    yield v, i, p
        for v in obj.values():
            if isinstance(v, (dict, list)):
                yield from iter_picks(v)


def re_resolve_pick(pick: dict, dry_run: bool) -> Optional[dict]:
    """Re-resolve a single historical pick. Returns delta-row dict or None."""
    if not isinstance(pick, dict):
        return None
    if not orv._is_non_crypto(pick):
        return None
    status = str(pick.get("status", "")).upper()
    if status not in ("WON", "LOST", "CLOSED", "EXPIRED", "FLAT"):
        return None
    # Skip picks already at v2 — idempotent.
    if pick.get("resolver_version") == "v2":
        return None

    entry = orv._safe_float(pick.get("entry_price"))
    tp = orv._safe_float(pick.get("take_profit", pick.get("targetPrice", 0)))
    sl = orv._safe_float(pick.get("stop_loss", pick.get("stopPrice", 0)))
    direction = orv._infer_direction(pick)
    asset_class = orv._resolve_asset_class(pick)
    if entry <= 0 or (tp <= 0 and sl <= 0):
        return None

    raw_dt = (pick.get("entry_date") or pick.get("entry_time")
              or pick.get("created_at") or pick.get("timestamp") or "")
    entry_dt = orv._parse_utc_timestamp(str(raw_dt)) if raw_dt else None
    symbol = str(pick.get("symbol", ""))

    bars = orv._fetch_yfinance_ohlc_window(symbol, entry_dt) if symbol else []
    hit = orv._scan_ohlc_for_touch(bars, direction, tp, sl) if bars else None

    old_pnl = pick.get("pnl_pct")
    old_status = pick.get("status")
    old_reason = pick.get("exit_reason")

    if hit:
        new_exit = float(hit["price"])
        new_reason = hit["reason"]
    elif bars:
        # No touch in window — close at last close, label TIME_EXIT_REPLAY.
        new_exit = float(bars[-1]["close"])
        new_reason = "TIME_EXIT_REPLAY"
    else:
        # No OHLC data available — leave alone, flag for retry.
        return {
            "symbol": symbol, "asset_class": asset_class,
            "old_pnl": old_pnl, "old_status": old_status, "old_reason": old_reason,
            "new_pnl": None, "new_status": "UNRESOLVED", "new_reason": "NO_OHLC",
            "applied": False,
        }

    new_pnl = orv.compute_pnl(entry, new_exit, direction)
    new_status = orv.classify_outcome(new_pnl, asset_class=asset_class or None)

    delta = {
        "symbol": symbol, "asset_class": asset_class,
        "old_pnl": old_pnl, "old_status": old_status, "old_reason": old_reason,
        "new_pnl": round(new_pnl, 6), "new_status": new_status, "new_reason": new_reason,
        "applied": False,
    }

    if not dry_run:
        if old_pnl not in (None, 0, 0.0):
            pick["_legacy_pnl_pct"] = old_pnl
        if old_reason:
            pick["_legacy_exit_reason"] = old_reason
        pick["pnl_pct"] = round(new_pnl, 6)
        pick["status"] = new_status
        pick["exit_reason"] = new_reason
        pick["exit_price"] = new_exit
        pick["resolver_version"] = "v2"
        pick["resolved_by"] = "re_resolve_historical_v2"
        delta["applied"] = True

    return delta


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true",
                    help="ACTUALLY WRITE corrected picks back to source files. "
                         "Default is dry-run. Pause outcome-resolver.yml cron first.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Force dry-run (default behavior).")
    ap.add_argument("--report", action="store_true",
                    help="Write the delta CSV to reports/re_resolve_delta_2026_04_28.csv")
    ap.add_argument("--limit", type=int, default=0,
                    help="Stop after N picks (debug aid).")
    args = ap.parse_args()

    dry_run = not args.apply  # explicit safe default

    print(f"[re-resolve v2] dry_run={dry_run} apply={args.apply}")
    print(f"[re-resolve v2] {len(SOURCE_FILES)} source files configured")

    deltas: list[dict] = []
    files_modified: list[Path] = []

    for src in SOURCE_FILES:
        if not src.exists():
            print(f"  SKIP {src} (not present)")
            continue
        try:
            with open(src, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"  ERROR reading {src}: {e}")
            continue

        file_count = 0
        for parent_list, idx, pick in iter_picks(data):
            d = re_resolve_pick(pick, dry_run=dry_run)
            if d is not None:
                d["source_file"] = str(src.relative_to(REPO_ROOT))
                deltas.append(d)
                file_count += 1
                if args.limit and len(deltas) >= args.limit:
                    break

        if file_count and not dry_run:
            try:
                with open(src, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, default=str)
                files_modified.append(src)
                print(f"  WROTE {src} ({file_count} picks updated)")
            except Exception as e:
                print(f"  ERROR writing {src}: {e}")
        else:
            print(f"  SCAN {src} ({file_count} candidate picks)")

        if args.limit and len(deltas) >= args.limit:
            break

    print(f"\n[re-resolve v2] total candidate picks: {len(deltas)}")
    flips_won_to_other = sum(1 for d in deltas
                             if str(d["old_status"]).upper() == "WON"
                             and d["new_status"] != "WON")
    flips_lost_to_other = sum(1 for d in deltas
                              if str(d["old_status"]).upper() == "LOST"
                              and d["new_status"] != "LOST")
    no_ohlc = sum(1 for d in deltas if d["new_reason"] == "NO_OHLC")
    print(f"[re-resolve v2] WON->other label flips: {flips_won_to_other}")
    print(f"[re-resolve v2] LOST->other label flips: {flips_lost_to_other}")
    print(f"[re-resolve v2] no OHLC available:       {no_ohlc}")

    if args.report or dry_run:
        DELTA_CSV.parent.mkdir(parents=True, exist_ok=True)
        with open(DELTA_CSV, "w", newline="", encoding="utf-8") as f:
            cols = ["source_file", "symbol", "asset_class",
                    "old_pnl", "old_status", "old_reason",
                    "new_pnl", "new_status", "new_reason", "applied"]
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for d in deltas:
                w.writerow({k: d.get(k, "") for k in cols})
        print(f"[re-resolve v2] delta CSV written: {DELTA_CSV.relative_to(REPO_ROOT)}")

    if dry_run:
        print("\n[DRY RUN] No source files modified. Re-run with --apply to commit.")
    elif files_modified:
        print(f"\n[APPLIED] {len(files_modified)} files modified.")


if __name__ == "__main__":
    main()
