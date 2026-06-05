#!/usr/bin/env python3
"""
prediction_market_consensus_pilot.py

Tracks every new `prediction_market_consensus` pick in a forward-test pilot.
- Ingests new picks from `at_raw_picks`
- Resolves open picks via `at_pick_outcomes` and `at_raw_picks.status`
- Maintains running stats: total_picks, wins, losses, wr, pf, avg_pnl, max_drawdown
- Sets promotion_ready only when forward n>=50 AND WR>=60% AND PF>=1.5

Usage:
    python tools/prediction_market_consensus_pilot.py --dry-run
    python tools/prediction_market_consensus_pilot.py --execute
    python tools/prediction_market_consensus_pilot.py --snapshot
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pymysql

REPO_ROOT = Path(__file__).resolve().parent.parent
PILOT_PATH = REPO_ROOT / "verified_strategies" / "paper_pilot" / "prediction_market_consensus_pilot.json"

DB_CONFIG = {
    "host": "mysql.50webs.com",
    "user": "ejaguiar1_stocks",
    "password": "stocks1234560",
    "database": "ejaguiar1_stocks",
    "cursorclass": pymysql.cursors.DictCursor,
}

PROMOTION_CRITERIA = {
    "min_forward_n": 50,
    "min_wr_pct": 60.0,
    "min_pf": 1.5,
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_pilot() -> dict:
    if PILOT_PATH.exists():
        with open(PILOT_PATH, "r") as f:
            return json.load(f)
    return {
        "strategy": "prediction_market_consensus",
        "pilot_started_at": now_iso(),
        "promotion_ready": False,
        "promotion_criteria": PROMOTION_CRITERIA,
        "stats": {
            "total_picks": 0,
            "resolved": 0,
            "wins": 0,
            "losses": 0,
            "flats": 0,
            "wr": 0.0,
            "pf": 0.0,
            "avg_pnl": 0.0,
            "max_drawdown": 0.0,
        },
        "picks": [],
    }


def save_pilot(pilot: dict) -> None:
    PILOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PILOT_PATH, "w") as f:
        json.dump(pilot, f, indent=2)


def recalculate_stats(picks: list) -> dict:
    resolved = [p for p in picks if p["status"] in ("WON", "LOST", "EXPIRED", "CLOSED", "FLAT")]
    wins = [p for p in resolved if p["status"] == "WON"]
    losses = [p for p in resolved if p["status"] == "LOST"]
    flats = [p for p in resolved if p["status"] in ("EXPIRED", "CLOSED", "FLAT") and p not in wins and p not in losses]

    pnls = [p["pnl_pct"] for p in resolved if p["pnl_pct"] is not None]
    wr = (len(wins) / len(resolved) * 100) if resolved else 0.0
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    pf = gross_profit / gross_loss if gross_loss > 0 else 0.0
    avg_pnl = sum(pnls) / len(pnls) if pnls else 0.0

    equity = 100.0
    peak = 100.0
    mdd = 0.0
    for pnl in pnls:
        equity *= (1.0 + pnl / 100.0)
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak * 100.0
        if dd > mdd:
            mdd = dd

    return {
        "total_picks": len(picks),
        "resolved": len(resolved),
        "wins": len(wins),
        "losses": len(losses),
        "flats": len(flats),
        "wr": round(wr, 2),
        "pf": round(pf, 4),
        "avg_pnl": round(avg_pnl, 4),
        "max_drawdown": round(mdd, 2),
    }


def fetch_new_picks(conn, existing_ids: set) -> list:
    sql = """
        SELECT
            p.id, p.symbol, p.asset_class, p.direction,
            CAST(p.entry_price AS FLOAT) AS entry_price,
            CAST(p.take_profit AS FLOAT) AS take_profit,
            CAST(p.stop_loss AS FLOAT) AS stop_loss,
            CAST(p.confidence AS FLOAT) AS confidence,
            p.signal_timestamp, p.status,
            CAST(p.exit_price AS FLOAT) AS exit_price,
            p.exit_reason,
            CAST(p.pnl_pct AS FLOAT) AS pnl_pct,
            p.closed_at
        FROM at_raw_picks p
        WHERE p.strategy = 'prediction_market_consensus'
          AND p.id NOT IN (%s)
        ORDER BY p.signal_timestamp ASC
    """ % ",".join("%s" for _ in existing_ids)

    with conn.cursor() as cur:
        if not existing_ids:
            cur.execute("""
                SELECT
                    p.id, p.symbol, p.asset_class, p.direction,
                    CAST(p.entry_price AS FLOAT) AS entry_price,
                    CAST(p.take_profit AS FLOAT) AS take_profit,
                    CAST(p.stop_loss AS FLOAT) AS stop_loss,
                    CAST(p.confidence AS FLOAT) AS confidence,
                    p.signal_timestamp, p.status,
                    CAST(p.exit_price AS FLOAT) AS exit_price,
                    p.exit_reason,
                    CAST(p.pnl_pct AS FLOAT) AS pnl_pct,
                    p.closed_at
                FROM at_raw_picks p
                WHERE p.strategy = 'prediction_market_consensus'
                ORDER BY p.signal_timestamp ASC
            """)
        else:
            cur.execute(sql, tuple(existing_ids))
        rows = cur.fetchall()

    new_picks = []
    for r in rows:
        new_picks.append({
            "pick_id": r["id"],
            "symbol": r["symbol"],
            "asset_class": r["asset_class"],
            "direction": r["direction"],
            "entry_price": r["entry_price"],
            "signal_timestamp": r["signal_timestamp"].isoformat() if r["signal_timestamp"] else None,
            "tp": r["take_profit"],
            "sl": r["stop_loss"],
            "confidence": r["confidence"],
            "status": r["status"] or "OPEN",
            "exit_price": r["exit_price"],
            "pnl_pct": r["pnl_pct"],
            "resolution_method": r["exit_reason"],
            "resolved_at": r["closed_at"].isoformat() if r["closed_at"] else None,
            "added_to_pilot_at": now_iso(),
        })
    return new_picks


def fetch_outcomes(conn, open_ids: list) -> dict:
    if not open_ids:
        return {}

    sql = """
        SELECT
            pick_id, status, resolution_method,
            CAST(pnl_pct AS FLOAT) AS pnl_pct,
            resolved_at
        FROM at_pick_outcomes
        WHERE pick_id IN (%s)
    """ % ",".join("%s" for _ in open_ids)

    outcomes = {}
    with conn.cursor() as cur:
        cur.execute(sql, tuple(open_ids))
        for r in cur.fetchall():
            outcomes[r["pick_id"]] = r
    return outcomes


def update_pilot(pilot: dict, dry_run: bool = False) -> dict:
    conn = pymysql.connect(**DB_CONFIG)
    try:
        existing_ids = {p["pick_id"] for p in pilot["picks"]}

        # 1. Ingest new picks
        new_picks = fetch_new_picks(conn, existing_ids)
        if new_picks:
            print(f"[INFO] Found {len(new_picks)} new pick(s) to ingest.")
            pilot["picks"].extend(new_picks)
        else:
            print("[INFO] No new picks found.")

        # 2. Resolve open picks
        open_picks = [p for p in pilot["picks"] if p["status"] == "OPEN"]
        open_ids = [p["pick_id"] for p in open_picks]
        outcomes = fetch_outcomes(conn, open_ids)

        resolved_count = 0
        for pick in open_picks:
            pick_id = pick["pick_id"]
            if pick_id in outcomes:
                o = outcomes[pick_id]
                pick["status"] = o["status"] or pick["status"]
                pick["pnl_pct"] = o["pnl_pct"] if o["pnl_pct"] is not None else pick["pnl_pct"]
                pick["resolution_method"] = o["resolution_method"] or pick["resolution_method"]
                pick["resolved_at"] = o["resolved_at"].isoformat() if o["resolved_at"] else pick["resolved_at"]
                resolved_count += 1
            else:
                # Fallback: check at_raw_picks itself for exit fields
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT status, CAST(exit_price AS FLOAT) AS exit_price,
                               exit_reason, CAST(pnl_pct AS FLOAT) AS pnl_pct, closed_at
                        FROM at_raw_picks WHERE id = %s
                        """,
                        (pick_id,),
                    )
                    row = cur.fetchone()
                    if row and row["status"] in ("WON", "LOST", "EXPIRED", "CLOSED"):
                        pick["status"] = row["status"]
                        pick["exit_price"] = row["exit_price"] if row["exit_price"] is not None else pick["exit_price"]
                        pick["pnl_pct"] = row["pnl_pct"] if row["pnl_pct"] is not None else pick["pnl_pct"]
                        pick["resolution_method"] = row["exit_reason"] or pick["resolution_method"]
                        pick["resolved_at"] = row["closed_at"].isoformat() if row["closed_at"] else pick["resolved_at"]
                        resolved_count += 1

        if resolved_count:
            print(f"[INFO] Resolved {resolved_count} pick(s).")
        else:
            print("[INFO] No newly resolved picks.")

        # 3. Recalculate stats
        pilot["stats"] = recalculate_stats(pilot["picks"])

        # 4. Promotion gate
        s = pilot["stats"]
        pilot["promotion_ready"] = (
            s["resolved"] >= PROMOTION_CRITERIA["min_forward_n"]
            and s["wr"] >= PROMOTION_CRITERIA["min_wr_pct"]
            and s["pf"] >= PROMOTION_CRITERIA["min_pf"]
        )

        # 5. Persist or preview
        if dry_run:
            print("\n--- DRY-RUN SUMMARY (no files written) ---")
        else:
            save_pilot(pilot)
            print(f"\n[INFO] Pilot saved to {PILOT_PATH}")

        print(json.dumps(pilot["stats"], indent=2))
        print(f"promotion_ready: {pilot['promotion_ready']}")

    finally:
        conn.close()

    return pilot


def print_snapshot(pilot: dict):
    print("\n========== prediction_market_consensus PILOT SNAPSHOT ==========\n")
    print(f"Strategy: {pilot['strategy']}")
    print(f"Pilot started: {pilot['pilot_started_at']}")
    print(f"Promotion ready: {pilot['promotion_ready']}")
    print()
    stats = pilot["stats"]
    print(f"  Total picks : {stats['total_picks']}")
    print(f"  Resolved    : {stats['resolved']}")
    print(f"  Wins        : {stats['wins']}")
    print(f"  Losses      : {stats['losses']}")
    print(f"  Flats       : {stats['flats']}")
    print(f"  Win Rate    : {stats['wr']:.2f}%")
    print(f"  Profit Fact : {stats['pf']:.4f}")
    print(f"  Avg PnL     : {stats['avg_pnl']:.4f}%")
    print(f"  Max DD      : {stats['max_drawdown']:.2f}%")
    print()

    # Recent 20 picks
    recent = sorted(pilot["picks"], key=lambda x: x["signal_timestamp"] or "", reverse=True)[:20]
    print("--- Last 20 picks ---")
    for p in recent:
        ts = (p["signal_timestamp"] or "N/A")[:19]
        print(
            f"  {ts} | {p['symbol']:12s} | {p['direction']:5s} | "
            f"entry={p['entry_price']} | tp={p['tp']} | sl={p['sl']} | "
            f"status={p['status']} | pnl={p['pnl_pct']}"
        )
    print()


def main():
    parser = argparse.ArgumentParser(description="prediction_market_consensus paper trading pilot")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--execute", action="store_true", help="Apply changes and write JSON")
    parser.add_argument("--snapshot", action="store_true", help="Print current snapshot and exit")
    args = parser.parse_args()

    pilot = load_pilot()

    if args.snapshot:
        print_snapshot(pilot)
        return

    if not args.dry_run and not args.execute:
        parser.print_help()
        sys.exit(1)

    pilot = update_pilot(pilot, dry_run=args.dry_run)
    print_snapshot(pilot)


if __name__ == "__main__":
    main()
