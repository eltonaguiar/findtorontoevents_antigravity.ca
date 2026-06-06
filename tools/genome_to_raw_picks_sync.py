#!/usr/bin/env python3
"""
genome_to_raw_picks_sync.py
===========================
Bridges genome/data/mega_mutation_picks.json → at_raw_picks.

The mega_mutation_live_tracker.py runs its own paper-trade resolver but
writes to a separate file that is invisible to the live active_picks_sync.py
resolver. This script ingests OPEN picks from the genome tracker into
at_raw_picks so they receive live resolution by the production resolver.

Only OPEN picks opened within the last 7 days are synced (avoids back-filling
stale paper trades that were resolved in the genome tracker but missed live).

Usage (manual or GHA):
    python3 tools/genome_to_raw_picks_sync.py
    python3 tools/genome_to_raw_picks_sync.py --dry-run   # print only, no DB write

Wire-up:
    Called automatically by .github/workflows/picks-now-refresh.yml AFTER
    genome/mega_mutation_live_tracker.py generate completes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

GENOME_PICKS = ROOT / "genome" / "data" / "mega_mutation_picks.json"
MAX_AGE_DAYS = 7      # only sync OPEN picks younger than this
SOURCE_SYSTEM = "mega_mutation"
CONFIDENCE_DEFAULT = 0.68    # mega_mutation avg tournament_wr ≈ 68%


def _dedup_hash(symbol: str, direction: str, entry_price: float, opened_at: str) -> str:
    """Stable hash for INSERT IGNORE dedup: (symbol, direction, entry, date)."""
    date_str = str(opened_at)[:10]   # YYYY-MM-DD
    raw = f"{symbol}|{direction}|{entry_price:.8f}|{date_str}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _direction(signal: str) -> str:
    s = str(signal).upper()
    if s in ("BUY", "LONG"):
        return "LONG"
    if s in ("SELL", "SHORT"):
        return "SHORT"
    return "LONG"   # mega_mutation primarily emits LONG (momentum)


def _rr(entry: float, tp: float, sl: float, direction: str) -> float:
    if not (entry and tp and sl):
        return 0.0
    if direction == "LONG":
        denom = entry - sl
        return (tp - entry) / denom if denom > 0 else 0.0
    denom = sl - entry
    return (entry - tp) / denom if denom > 0 else 0.0


def load_open_picks() -> list[dict]:
    if not GENOME_PICKS.exists():
        print(f"[genome_sync] GENOME_PICKS not found: {GENOME_PICKS}")
        return []
    data = json.loads(GENOME_PICKS.read_text())
    if isinstance(data, list):
        return [p for p in data if str(p.get("status", "")).upper() == "OPEN"]
    return data.get("open_picks", [])


def sync(dry_run: bool = False) -> int:
    """Returns number of picks successfully written (or would-write in dry-run)."""
    open_picks = load_open_picks()
    print(f"[genome_sync] {len(open_picks)} OPEN picks in genome tracker")

    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    synced = 0
    skipped_age = 0
    skipped_invalid = 0

    if not open_picks:
        print("[genome_sync] No open picks to sync.")
        return 0

    if not dry_run:
        from audit_trail.mysql_client import mysql_record_raw_pick

    for p in open_picks:
        opened_raw = p.get("opened_at") or p.get("timestamp") or ""
        try:
            opened = datetime.fromisoformat(str(opened_raw).replace("Z", "+00:00"))
            if opened.tzinfo is None:
                opened = opened.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            opened = datetime.now(timezone.utc)

        if opened < cutoff:
            skipped_age += 1
            continue

        symbol = str(p.get("symbol", "")).upper()
        entry = p.get("entry_price")
        tp = p.get("tp_price")
        sl = p.get("sl_price")
        mutation_name = p.get("mutation_name", "mega_mutation_unknown")
        signal = p.get("signal", "BUY")
        direction = _direction(signal)
        conf = float(p.get("tournament_wr") or CONFIDENCE_DEFAULT)

        if not (symbol and entry and tp and sl):
            skipped_invalid += 1
            continue

        entry = float(entry)
        tp = float(tp)
        sl = float(sl)
        rr = _rr(entry, tp, sl, direction)

        strategy = f"mega_mutation::{mutation_name}"
        sig_ts = opened.strftime("%Y-%m-%d %H:%M:%S")
        pick_id = f"genome_mm_{symbol}_{mutation_name}_{opened.strftime('%Y%m%d%H%M')}"
        run_id = f"genome_sync_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}"
        dh = _dedup_hash(symbol, direction, entry, sig_ts)

        if dry_run:
            print(f"  [DRY] {symbol} {direction} entry={entry:.4f} tp={tp:.4f} sl={sl:.4f} "
                  f"strat={strategy} conf={conf:.2f} rr={rr:.2f}")
            synced += 1
            continue

        rows = mysql_record_raw_pick(
            pick_id=pick_id,
            run_id=run_id,
            source_system=SOURCE_SYSTEM,
            symbol=symbol,
            direction=direction,
            entry_price=entry,
            take_profit=tp,
            stop_loss=sl,
            risk_reward=rr,
            confidence=conf,
            strategy=strategy,
            signal_timestamp=sig_ts,
            dedup_hash=dh,
            raw_payload=p,
        )
        if rows:
            print(f"  [SYNC] {symbol} {direction} {strategy} → at_raw_picks")
            synced += 1
        else:
            print(f"  [SKIP-DUP] {symbol} {direction} {strategy} (already in DB)")

    print(f"[genome_sync] done — synced={synced} skipped_age={skipped_age} "
          f"skipped_invalid={skipped_invalid}")
    return synced


def main():
    parser = argparse.ArgumentParser(description="Sync genome mega_mutation picks to at_raw_picks")
    parser.add_argument("--dry-run", action="store_true", help="Print picks without writing to DB")
    args = parser.parse_args()
    count = sync(dry_run=args.dry_run)
    sys.exit(0 if count >= 0 else 1)


if __name__ == "__main__":
    main()
