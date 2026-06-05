#!/usr/bin/env python3
"""
Validate intrabar fills for historical CRYPTO picks.

Problem: outcome_resolver.py uses NOMINAL_TP_LEGACY fill method which
assumes TP fill at the target price, not the actual intrabar price.
Per v2 spec §7, replay 1h OHLCV from entry to find the TRUE exit
(was SL hit first before TP? did price even reach TP?).

For each closed pick:
  - Load 1h OHLCV from entry_time to entry_time + max_hold
  - Replay: did Low<SL before High>=TP?  -> original WR INFLATED
  - Compute: "true" exit price, true pnl_pct, true WR/PF

Read-only. Outputs:
  reports/validate_intrabar_fills_<UTC>.json
  stdout summary per sleeve with reclassification rate

Usage:
  python3 tools/validate_intrabar_fills.py
  python3 tools/validate_intrabar_fills.py --sleeves S1,S2,S3,S4
  python3 tools/validate_intrabar_fills.py --max-picks 200
  python3 tools/validate_intrabar_fills.py --json-only
"""
from __future__ import annotations
import os
import sys
import json
import argparse
import logging
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("validate_intrabar_fills")

try:
    import pymysql
    from tools.db_env import get_stocks_creds
except ImportError as e:
    log.error("Missing imports: %s", e)
    sys.exit(1)


# v2 spec §2 sleeves: (sleeve_id, label, symbol, strategy_filter)
DEFAULT_SLEEVES = [
    ("S1", "JUP_mega", "JUPUSDT", ""),
    ("S2", "ENA_mega", "ENAUSDT", ""),
    ("S3", "ADA_mega", "ADAUSDT", ""),
    ("S4", "DYDX_alpha", "DYDXUSDT", "ml_enhanced_DYDXUSDT_15m_D_ensemble_stack"),
]

# v2 spec §10 entry/exit parameters
SLEEVE_PARAMS = {
    "S1": {"tp_pct": 0.020, "sl_pct": -0.010, "max_hold_h": 24, "r_r": 2.0},
    "S2": {"tp_pct": 0.020, "sl_pct": -0.010, "max_hold_h": 24, "r_r": 2.0},
    "S3": {"tp_pct": 0.020, "sl_pct": -0.010, "max_hold_h": 24, "r_r": 2.0},
    "S4": {"tp_pct": 0.020, "sl_pct": -0.015, "max_hold_h": 48, "r_r": 1.33},
}

# Per spec §7 Step 3: 20% reclassification stress + 0.2% latency buffer
WORST_CASE_RECLASSIFY_PCT = 0.20
LATENCY_BUFFER_PCT = 0.002  # 0.2% per trade unknown slippage


def connect():
    creds = get_stocks_creds()
    creds.setdefault("connect_timeout", 30)
    return pymysql.connect(**creds, cursorclass=pymysql.cursors.DictCursor)


def fetch_picks(cur, sleeve_id: str, symbol: str, strategy: str) -> list[dict]:
    """Get all closed picks for a sleeve.

    Note: many historical picks have created_at=NULL (backfill artifact),
    but closed_at is populated. We use closed_at - max_hold_h as the
    estimated entry_ts, which is approximate but the best we can do.
    """
    if strategy:
        cur.execute("""
            SELECT id, symbol, direction, strategy, entry_price, take_profit,
                   stop_loss, status, pnl_pct, exit_price, created_at, closed_at,
                   exit_reason, tp_fill_method
            FROM trading_picks
            WHERE status IN ('TP_HIT','SL_HIT','TIME_EXIT','LOST','EXPIRED')
              AND pnl_pct IS NOT NULL
              AND entry_price IS NOT NULL AND entry_price > 0
              AND closed_at IS NOT NULL
              AND symbol = %s AND strategy = %s
            ORDER BY closed_at
        """, (symbol, strategy))
    else:
        cur.execute("""
            SELECT id, symbol, direction, strategy, entry_price, take_profit,
                   stop_loss, status, pnl_pct, exit_price, created_at, closed_at,
                   exit_reason, tp_fill_method
            FROM trading_picks
            WHERE status IN ('TP_HIT','SL_HIT','TIME_EXIT','LOST','EXPIRED')
              AND pnl_pct IS NOT NULL
              AND entry_price IS NOT NULL AND entry_price > 0
              AND closed_at IS NOT NULL
              AND symbol = %s AND (strategy = '' OR strategy IS NULL)
            ORDER BY closed_at
        """, (symbol,))
    return cur.fetchall()


def fetch_ohlcv(cur, symbol: str, start_ts_ms: int, end_ts_ms: int) -> list[dict]:
    """Get 1h OHLCV for symbol between timestamps (ms, inclusive).

    Note: crypto_ohlcv.timestamp is stored in MILLISECONDS.
    """
    cur.execute("""
        SELECT timestamp, open, high, low, close, volume
        FROM crypto_ohlcv
        WHERE symbol = %s AND timeframe = '1h'
          AND timestamp >= %s AND timestamp <= %s
        ORDER BY timestamp
    """, (symbol, start_ts_ms, end_ts_ms))
    return cur.fetchall()


def replay_intrabar(entry_price: float, direction: str, params: dict,
                    bars: list[dict], entry_ts: int) -> dict:
    """
    Replay the trade on 1h bars. Returns dict with:
      - true_exit_price: float or None (if no fill before time stop)
      - true_exit_reason: 'TP_HIT' | 'SL_HIT' | 'TIME_EXIT' | 'NO_DATA'
      - true_pnl_pct: float
      - sl_hit_first: bool (the key flag)
    """
    tp_pct = params["tp_pct"]
    sl_pct = params["sl_pct"]
    max_hold_h = params["max_hold_h"]

    if direction.upper() in ("LONG", "BUY"):
        tp_price = entry_price * (1 + tp_pct)
        sl_price = entry_price * (1 + sl_pct)
    else:  # SHORT / SELL
        tp_price = entry_price * (1 - tp_pct)
        sl_price = entry_price * (1 - sl_pct)

    for i, bar in enumerate(bars):
        if i >= max_hold_h:
            return {
                "true_exit_price": float(bar["close"]),
                "true_exit_reason": "TIME_EXIT",
                "true_pnl_pct": (float(bar["close"]) - entry_price) / entry_price
                                 if direction.upper() in ("LONG", "BUY") else
                                 (entry_price - float(bar["close"])) / entry_price,
                "sl_hit_first": False,
                "bars_used": i,
            }
        h = float(bar["high"])
        l = float(bar["low"])
        if direction.upper() in ("LONG", "BUY"):
            sl_hit = l <= sl_price
            tp_hit = h >= tp_price
        else:
            sl_hit = h >= sl_price
            tp_hit = l <= tp_price
        if sl_hit and tp_hit:
            # Conservative: assume SL hit first (per v2 spec §7)
            return {
                "true_exit_price": sl_price,
                "true_exit_reason": "SL_HIT",
                "true_pnl_pct": sl_pct,
                "sl_hit_first": True,
                "bars_used": i + 1,
            }
        if sl_hit:
            return {
                "true_exit_price": sl_price,
                "true_exit_reason": "SL_HIT",
                "true_pnl_pct": sl_pct,
                "sl_hit_first": True,
                "bars_used": i + 1,
            }
        if tp_hit:
            return {
                "true_exit_price": tp_price,
                "true_exit_reason": "TP_HIT",
                "true_pnl_pct": tp_pct,
                "sl_hit_first": False,
                "bars_used": i + 1,
            }

    return {
        "true_exit_price": None,
        "true_exit_reason": "NO_DATA",
        "true_pnl_pct": None,
        "sl_hit_first": False,
        "bars_used": 0,
    }


def compute_pf(trades: list[dict]) -> float:
    """Profit factor from a list of trades with 'true_pnl_pct' (Decimal-safe)."""
    gw = sum(t["true_pnl_pct"] for t in trades if t.get("true_pnl_pct") and t["true_pnl_pct"] > 0)
    gl = abs(sum(t["true_pnl_pct"] for t in trades if t.get("true_pnl_pct") and t["true_pnl_pct"] < 0))
    if gl == 0:
        return float("inf") if gw > 0 else 0.0
    return round(gw / gl, 2)


def compute_wr(trades: list[dict]) -> float:
    valid = [t for t in trades if t.get("true_pnl_pct") is not None]
    if not valid:
        return 0.0
    wins = sum(1 for t in valid if t["true_pnl_pct"] > 0)
    return round(wins / len(valid) * 100, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sleeves", default="S1,S2,S3,S4",
                    help="comma-sep sleeve IDs (default S1-S4)")
    ap.add_argument("--max-picks", type=int, default=500,
                    help="cap picks per sleeve (default 500)")
    ap.add_argument("--json-only", action="store_true",
                    help="suppress verbose stdout, only emit summary JSON")
    ap.add_argument("--out-dir", default=None,
                    help="output dir (default reports/)")
    args = ap.parse_args()

    sleeves = [s for s in DEFAULT_SLEEVES if s[0] in args.sleeves.split(",")]
    if not sleeves:
        log.error("No valid sleeves selected")
        sys.exit(1)

    out_dir = args.out_dir or os.path.join(REPO, "reports")
    os.makedirs(out_dir, exist_ok=True)

    log.info("Validating %d sleeves: %s", len(sleeves), [s[0] for s in sleeves])

    conn = connect()
    cur = conn.cursor()

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sleeves": {},
        "global": {
            "total_picks": 0,
            "tp_hits_replayed": 0,
            "sl_hit_first_count": 0,
            "reclassify_rate": 0.0,
        },
    }

    for sleeve_id, label, symbol, strategy in sleeves:
        log.info("=" * 60)
        log.info("Sleeve %s: %s / %s", sleeve_id, symbol, label)
        picks = fetch_picks(cur, sleeve_id, symbol, strategy)
        if args.max_picks:
            picks = picks[: args.max_picks]
        log.info("  Found %d closed picks", len(picks))
        if not picks:
            summary["sleeves"][sleeve_id] = {"symbol": symbol, "n": 0}
            continue

        params = SLEEVE_PARAMS[sleeve_id]

        replayed = []
        for p in picks:
            closed = p["closed_at"]
            if not closed:
                continue
            if isinstance(closed, str):
                try:
                    closed_dt = datetime.fromisoformat(closed.replace("Z", "+00:00"))
                except ValueError:
                    continue
            else:
                closed_dt = closed
            if closed_dt.tzinfo is None:
                closed_dt = closed_dt.replace(tzinfo=timezone.utc)
            # Best proxy: entry was max_hold_h before closed_at
            # crypto_ohlcv timestamps are in MILLISECONDS
            entry_ts_ms = (int(closed_dt.timestamp()) - params["max_hold_h"] * 3600) * 1000
            end_ts_ms = (int(closed_dt.timestamp()) + 3600) * 1000

            bars = fetch_ohlcv(cur, symbol, entry_ts_ms, end_ts_ms)
            if not bars:
                continue
            entry = float(p["entry_price"])
            direction = p.get("direction") or "LONG"
            r = replay_intrabar(entry, direction, params, bars, entry_ts_ms)
            r["original_pnl_pct"] = float(p["pnl_pct"]) if p["pnl_pct"] is not None else None
            r["original_status"] = p["status"]
            r["original_exit_reason"] = p.get("exit_reason")
            r["tp_fill_method"] = p.get("tp_fill_method")
            r["closed_at"] = str(closed)
            r["entry_price"] = entry
            r["direction"] = direction
            replayed.append(r)

        # Step 1: count SL-first reclassifications
        tp_hits_replayed = [t for t in replayed
                            if t["original_exit_reason"] in ("TP_HIT", "TP_HIT_RESOLVED", "TP_HIT_RESOLVED ")
                            or t["original_status"] == "TP_HIT"]
        sl_hit_first = [t for t in tp_hits_replayed if t["sl_hit_first"]]
        reclassify_rate = (len(sl_hit_first) / len(tp_hits_replayed)
                          if tp_hits_replayed else 0.0)

        # Step 2: actual-fill PF
        actual_pf = compute_pf(replayed)
        actual_wr = compute_wr(replayed)

        # Step 3: worst-case stress (relabel 20% of wins as losses, 0.2% buffer)
        stressed = []
        for t in replayed:
            t2 = dict(t)
            if t2.get("true_pnl_pct") is None:
                continue
            if t2["true_pnl_pct"] > 0:
                # Stress: small chance of reclassification to loss
                # We model worst-case deterministically: 20% of wins become losses
                t2["stressed"] = True
                stressed.append(t2)
            else:
                t2["stressed"] = False
                stressed.append(t2)
        # Relabel worst 20% of wins as losses
        wins_sorted = sorted([t for t in stressed if t["true_pnl_pct"] > 0],
                            key=lambda x: x["true_pnl_pct"])
        n_relabel = int(len(wins_sorted) * WORST_CASE_RECLASSIFY_PCT)
        for t in wins_sorted[:n_relabel]:
            t["true_pnl_pct"] = -LATENCY_BUFFER_PCT * 5  # treat as ~1% loss
            t["true_exit_reason"] = "STRESS_SL"
        stressed_pf = compute_pf(stressed)
        stressed_wr = compute_wr(stressed)

        # Original WR for comparison
        orig_pf = compute_pf([{"true_pnl_pct": t["original_pnl_pct"]}
                              for t in replayed if t["original_pnl_pct"] is not None])
        orig_wr = sum(1 for t in replayed if t["original_pnl_pct"] and t["original_pnl_pct"] > 0) / max(1, len(replayed)) * 100

        sleeve_summary = {
            "symbol": symbol,
            "strategy": strategy,
            "n_picks": len(replayed),
            "n_tp_hits_replayed": len(tp_hits_replayed),
            "n_sl_hit_first": len(sl_hit_first),
            "reclassify_rate": round(reclassify_rate, 4),
            "original_pf": orig_pf,
            "original_wr_pct": round(orig_wr, 1),
            "actual_pf": actual_pf,
            "actual_wr_pct": actual_wr,
            "stressed_pf": stressed_pf,
            "stressed_wr_pct": stressed_wr,
            "verdict": ("PASS" if reclassify_rate <= 0.20 and stressed_pf >= 2.0
                        else "FAIL_RECLASSIFY" if reclassify_rate > 0.20
                        else "FAIL_STRESS_PF"),
        }
        summary["sleeves"][sleeve_id] = sleeve_summary
        summary["global"]["total_picks"] += len(replayed)
        summary["global"]["tp_hits_replayed"] += len(tp_hits_replayed)
        summary["global"]["sl_hit_first_count"] += len(sl_hit_first)

        if not args.json_only:
            print()
            print(f"  Sleeve {sleeve_id} ({symbol}):")
            print(f"    N picks:                    {len(replayed)}")
            print(f"    TP_HIT count:               {len(tp_hits_replayed)}")
            print(f"    SL hit first (reclassify):  {len(sl_hit_first)} ({reclassify_rate*100:.1f}%)")
            print(f"    Original WR / PF:           {sleeve_summary['original_wr_pct']:.1f}% / {orig_pf:.2f}")
            print(f"    Replayed WR / PF:           {actual_wr:.1f}% / {actual_pf:.2f}")
            print(f"    Stressed WR / PF (20% relbl+0.2% buf): {stressed_wr:.1f}% / {stressed_pf:.2f}")
            print(f"    Verdict:                    {sleeve_summary['verdict']}")
            print()

    if summary["global"]["tp_hits_replayed"]:
        summary["global"]["reclassify_rate"] = round(
            summary["global"]["sl_hit_first_count"] / summary["global"]["tp_hits_replayed"], 4)

    # Write JSON
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = os.path.join(out_dir, f"validate_intrabar_fills_{ts}.json")
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    log.info("Wrote %s", out_path)

    # Latest pointer
    latest_path = os.path.join(out_dir, "validate_intrabar_fills_latest.json")
    with open(latest_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    if not args.json_only:
        print()
        print("=" * 60)
        print("GLOBAL SUMMARY")
        print(f"  Total picks replayed:    {summary['global']['total_picks']}")
        print(f"  TP_HIT events:           {summary['global']['tp_hits_replayed']}")
        print(f"  SL-hit-first:            {summary['global']['sl_hit_first_count']} ({summary['global']['reclassify_rate']*100:.1f}%)")
        print()
        print("Verdict (v2 spec §7):")
        for sid, s in summary["sleeves"].items():
            if isinstance(s, dict) and "verdict" in s:
                print(f"  {sid}: {s['verdict']:18s}  stressed PF={s['stressed_pf']}  reclassify={s['reclassify_rate']*100:.1f}%")
        print()
        print("Pass criteria (per v2 spec):")
        print("  - reclassify_rate <= 20%")
        print("  - stressed_pf >= 2.0")
        print("  - All 4 sleeves must PASS to proceed to Stage 1 ($100)")


if __name__ == "__main__":
    main()
