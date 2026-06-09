#!/usr/bin/env python3
"""Intrabar re-resolution of CRYPTO picks using each pick's ACTUAL TP/SL.

WHY
---
The per-asset-class edge audit (reports/2026-06-06-per-asset-class-edge-*) and
tools/validate_intrabar_fills.py proved the production resolver inflates WR by
labeling a pick TP_HIT without checking whether SL was touched FIRST inside the
holding window. ~63% of sampled CRYPTO TP_HITs actually hit SL first on intrabar
replay. This tool re-resolves every replayable CRYPTO pick by replaying 1h OHLC
between the pick's own created_at and closed_at, using the pick's OWN
take_profit / stop_loss prices (not sleeve defaults), and reports the corrected
WR/PF per strategy + reclassification rate.

SAFETY
------
DRY-RUN BY DEFAULT — read-only, writes only a JSON report. The --apply path
(write corrected status/pnl back) is implemented but REFUSES to run without both
--apply AND --i-understand-this-mutates-production, and it backs up every
affected row to ejaguiar1_backups first. Do NOT --apply without operator
greenlight after reviewing the dry-run diff.

USAGE
-----
    python3 tools/reresolve_intrabar.py                 # dry-run, all CRYPTO
    python3 tools/reresolve_intrabar.py --max 2000      # sample
    python3 tools/reresolve_intrabar.py --min-strategy-n 30   # report filter
    # (gated) python3 tools/reresolve_intrabar.py --apply --i-understand-this-mutates-production
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

try:
    import pymysql
    from tools.db_env import get_stocks_creds
except ImportError as exc:  # pragma: no cover
    print(f"missing deps: {exc}", file=sys.stderr)
    raise SystemExit(1)

# De-biased horizon. The ACTIVE default is the --max-hold-bars arg (168 = 7d):
# replaying far beyond a pick's intended hold is look-ahead bias (peer review
# 2026-06-09, deepseek+ofox unanimous). 4320 (=OHLCV backfill depth) is NOT a
# valid hold and must never be the default — data depth != intended trade life.
MAX_HOLD_BARS_DEFAULT = 168  # ~7d of 1h bars (defensible intended-hold proxy)


def _to_ms(dt) -> int | None:
    if dt is None:
        return None
    if isinstance(dt, (int, float)):
        return int(dt)
    try:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except Exception:
        return None


def fetch_picks(cur, max_n: int | None):
    q = """
        SELECT id, symbol, direction, strategy, category, entry_price,
               take_profit, stop_loss, status, pnl_pct, created_at, closed_at
        FROM trading_picks
        WHERE status IN ('TP_HIT','SL_HIT','TIME_EXIT','LOST','EXPIRED','WON')
          AND entry_price > 0 AND take_profit > 0 AND stop_loss > 0
          AND closed_at IS NOT NULL AND created_at IS NOT NULL
          AND (category = 'crypto' OR symbol LIKE '%USDT')
        ORDER BY closed_at DESC
    """
    if max_n:
        q += f" LIMIT {int(max_n)}"
    cur.execute(q)
    return cur.fetchall()


def fetch_ohlcv(cur, symbol: str, start_ms: int, end_ms: int):
    cur.execute(
        """SELECT timestamp, high, low, close FROM crypto_ohlcv
           WHERE symbol=%s AND timeframe='1h' AND timestamp>=%s AND timestamp<=%s
           ORDER BY timestamp""",
        (symbol, start_ms, end_ms),
    )
    return cur.fetchall()


def replay(entry, tp, sl, direction, bars):
    """First-touch replay using the pick's actual TP/SL prices.
    Returns (true_status, true_pnl_frac, bars_used) or (None, None, 0) if no data."""
    if not bars:
        return None, None, 0, False
    is_long = str(direction or "BUY").upper() in ("LONG", "BUY", "STRONG_BUY")
    for i, b in enumerate(bars):
        h, l = float(b["high"]), float(b["low"])
        if is_long:
            sl_hit, tp_hit = l <= sl, h >= tp
        else:
            sl_hit, tp_hit = h >= sl, l <= tp
        # AMBIGUOUS: both TP and SL touched within the same 1h bar — intrabar
        # order is unknown at this timeframe. We resolve conservatively to SL
        # (v2 spec §7) but FLAG it (ambiguous=True) so downstream isn't silently
        # over-penalized (peer review 2026-06-09 flagged the tie-break as biased).
        if sl_hit and tp_hit:
            pnl = (sl - entry) / entry if is_long else (entry - sl) / entry
            return "SL_HIT", pnl, i + 1, True
        if sl_hit:
            pnl = (sl - entry) / entry if is_long else (entry - sl) / entry
            return "SL_HIT", pnl, i + 1, False
        if tp_hit:
            pnl = (tp - entry) / entry if is_long else (entry - tp) / entry
            return "TP_HIT", pnl, i + 1, False
    last = float(bars[-1]["close"])
    pnl = (last - entry) / entry if is_long else (entry - last) / entry
    return "TIME_EXIT", pnl, len(bars), False


def _orig_is_win(status, pnl):
    s = str(status or "").upper()
    if s in ("TP_HIT", "WON", "WIN"):
        return True
    if s in ("SL_HIT", "LOST", "LOSS"):
        return False
    # TIME_EXIT/EXPIRED: by pnl sign
    try:
        return float(pnl or 0) > 0
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=None)
    ap.add_argument("--max-hold-bars", type=int, default=168,
                    help="Fixed forward horizon in 1h bars (default 168=7d). "
                         "Replay runs from created_at for this many bars, "
                         "INDEPENDENT of the original (buggy) closed_at, so the "
                         "re-resolution is not conditioned on the thing it corrects.")
    ap.add_argument("--min-strategy-n", type=int, default=30)
    ap.add_argument("--out", default=str(REPO / "reports" / "reresolve_intrabar_latest.json"))
    ap.add_argument("--apply", action="store_true", help="GATED: write corrected resolutions")
    ap.add_argument("--i-understand-this-mutates-production", action="store_true")
    args = ap.parse_args()

    if args.apply and not args.i_understand_this_mutates_production:
        print("REFUSING --apply without --i-understand-this-mutates-production", file=sys.stderr)
        return 2

    conn = pymysql.connect(**get_stocks_creds(), cursorclass=pymysql.cursors.DictCursor)
    cur = conn.cursor()
    picks = fetch_picks(cur, args.max)
    print(f"[reresolve] loaded {len(picks)} replayable CRYPTO picks")

    per_strat = defaultdict(lambda: {"n": 0, "orig_w": 0, "true_w": 0,
                                     "reclass_tp_to_sl": 0, "no_data": 0,
                                     "true_pnls": []})
    overall = {"n": 0, "orig_w": 0, "true_w": 0, "reclass_tp_to_sl": 0, "no_data": 0,
               "true_pnls": []}
    corrections = []  # for --apply

    horizon_ms = args.max_hold_bars * 3600 * 1000
    for p in picks:
        sym = p["symbol"]
        start = _to_ms(p["created_at"])
        if not start:
            continue
        # FIXED forward horizon from entry — NOT bounded by the original
        # closed_at (which the buggy resolver set). This de-biases the replay.
        end = start + horizon_ms
        bars = fetch_ohlcv(cur, sym, start, end)
        entry = float(p["entry_price"]); tp = float(p["take_profit"]); sl = float(p["stop_loss"])
        ts, tpnl, used, ambiguous = replay(entry, tp, sl, p["direction"], bars)
        strat = p.get("strategy") or "(none)"
        rec = per_strat[strat]
        if ts is None:
            rec["no_data"] += 1; overall["no_data"] += 1
            continue
        rec["n"] += 1; overall["n"] += 1
        orig_w = _orig_is_win(p["status"], p["pnl_pct"])
        true_w = tpnl is not None and tpnl > 0
        rec["orig_w"] += int(orig_w); overall["orig_w"] += int(orig_w)
        rec["true_w"] += int(true_w); overall["true_w"] += int(true_w)
        if orig_w and ts == "SL_HIT":
            rec["reclass_tp_to_sl"] += 1; overall["reclass_tp_to_sl"] += 1
        rec["true_pnls"].append(tpnl); overall["true_pnls"].append(tpnl)
        if args.apply:
            # Write EVERY replayed pick's intrabar verdict (not only changes) to
            # parallel columns so the corrected layer is complete + queryable.
            corrections.append({"id": p["id"], "old_status": p["status"],
                                "new_status": ts, "true_pnl_pct": round((tpnl or 0) * 100, 4),
                                "ambiguous": 1 if ambiguous else 0,
                                "horizon_bars": args.max_hold_bars})

    def wr_pf(pnls, w, n):
        gw = sum(x for x in pnls if x > 0); gl = abs(sum(x for x in pnls if x < 0))
        pf = round(gw / gl, 3) if gl > 0 else (float("inf") if gw > 0 else 0.0)
        return round(w / n * 100, 1) if n else 0.0, pf

    report = {"generated_at": datetime.now(timezone.utc).isoformat(),
              "picks_loaded": len(picks), "replayed": overall["n"],
              "no_data": overall["no_data"], "strategies": []}
    o_wr, o_pf = wr_pf(overall["true_pnls"], overall["true_w"], overall["n"])
    orig_wr = round(overall["orig_w"] / overall["n"] * 100, 1) if overall["n"] else 0
    report["overall"] = {"n": overall["n"], "orig_wr": orig_wr, "true_wr": o_wr,
                         "true_pf": o_pf,
                         "tp_to_sl_reclass_pct": round(overall["reclass_tp_to_sl"] / overall["n"] * 100, 1) if overall["n"] else 0}
    for strat, r in sorted(per_strat.items(), key=lambda kv: -kv[1]["n"]):
        if r["n"] < args.min_strategy_n:
            continue
        wr, pf = wr_pf(r["true_pnls"], r["true_w"], r["n"])
        report["strategies"].append({
            "strategy": strat, "n": r["n"],
            "orig_wr": round(r["orig_w"] / r["n"] * 100, 1),
            "true_wr": wr, "true_pf": pf,
            "tp_to_sl_reclass_pct": round(r["reclass_tp_to_sl"] / r["n"] * 100, 1),
        })

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2))

    print(f"\n=== OVERALL (n={overall['n']}) ===")
    print(f"  orig WR {orig_wr}%  ->  intrabar-true WR {o_wr}%   true PF {o_pf}")
    print(f"  TP->SL reclassification: {report['overall']['tp_to_sl_reclass_pct']}%")
    print(f"\n=== PER STRATEGY (n>={args.min_strategy_n}) ===")
    print(f"  {'strategy':32} {'n':>5} {'origWR':>7} {'trueWR':>7} {'truePF':>7} {'TP->SL%':>8}")
    for s in report["strategies"]:
        print(f"  {s['strategy'][:32]:32} {s['n']:5} {s['orig_wr']:7} {s['true_wr']:7} {str(s['true_pf']):>7} {s['tp_to_sl_reclass_pct']:8}")
    print(f"\nReport: {args.out}")

    if args.apply:
        # NON-DESTRUCTIVE per peer review (2026-06-09, deepseek+ofox unanimous):
        # write corrected verdicts to PARALLEL columns; NEVER overwrite the
        # canonical trading_picks.status/pnl_pct (that was the previous design and
        # the review rejected it). The untouched original IS the backup
        # (rollback = NULL the intrabar_* cols); a full original snapshot also goes
        # to ejaguiar1_backups. Ambiguous (TP&SL same bar) rows are flagged, not
        # silently penalized.
        print(f"\n[APPLY] writing {len(corrections)} intrabar verdicts to PARALLEL columns (canonical row UNTOUCHED)")
        BATCH = 500
        try:
            for ddl in (
                "ALTER TABLE trading_picks ADD COLUMN IF NOT EXISTS intrabar_status VARCHAR(20) NULL",
                "ALTER TABLE trading_picks ADD COLUMN IF NOT EXISTS intrabar_pnl_pct DECIMAL(12,4) NULL",
                "ALTER TABLE trading_picks ADD COLUMN IF NOT EXISTS intrabar_ambiguous TINYINT NULL",
                "ALTER TABLE trading_picks ADD COLUMN IF NOT EXISTS intrabar_horizon_bars INT NULL",
                "ALTER TABLE trading_picks ADD COLUMN IF NOT EXISTS intrabar_resolved_at DATETIME NULL",
            ):
                try: cur.execute(ddl)
                except Exception as e: print(f"  [ddl] {e}")
            conn.commit()

            # Full original snapshot (status+pnl) to ejaguiar1_backups for audit.
            from tools.db_env import get_backups_creds
            ids = [c["id"] for c in corrections]
            orig = {}
            for i in range(0, len(ids), BATCH):
                chunk = ids[i:i + BATCH]
                cur.execute(f"SELECT id, status, pnl_pct FROM trading_picks WHERE id IN ({','.join(['%s']*len(chunk))})", chunk)
                for r in cur.fetchall(): orig[r["id"]] = (r["status"], r["pnl_pct"])
            bconn = pymysql.connect(**get_backups_creds()); bcur = bconn.cursor()
            bcur.execute("""CREATE TABLE IF NOT EXISTS reresolve_intrabar_backup
                (id BIGINT, orig_status VARCHAR(20), orig_pnl_pct DECIMAL(12,4),
                 new_intrabar_status VARCHAR(20), new_intrabar_pnl_pct DECIMAL(12,4),
                 ambiguous TINYINT, horizon_bars INT, backed_up_at DATETIME)""")
            bcur.execute("DELETE FROM reresolve_intrabar_backup")  # idempotent re-runs
            backup_rows = [(c["id"], orig.get(c["id"], (None, None))[0], orig.get(c["id"], (None, None))[1],
                            c["new_status"], c["true_pnl_pct"], c["ambiguous"], c["horizon_bars"]) for c in corrections]
            for i in range(0, len(backup_rows), BATCH):
                bcur.executemany(
                    "INSERT INTO reresolve_intrabar_backup (id,orig_status,orig_pnl_pct,new_intrabar_status,new_intrabar_pnl_pct,ambiguous,horizon_bars) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    backup_rows[i:i + BATCH])
            bconn.commit(); bconn.close()

            n_chunks = (len(corrections) + BATCH - 1) // BATCH
            for i in range(0, len(corrections), BATCH):
                chunk = corrections[i:i + BATCH]
                for c in chunk:
                    cur.execute(
                        "UPDATE trading_picks SET intrabar_status=%s, intrabar_pnl_pct=%s, "
                        "intrabar_ambiguous=%s, intrabar_horizon_bars=%s, intrabar_resolved_at=NOW() "
                        "WHERE id=%s",
                        (c["new_status"], c["true_pnl_pct"], c["ambiguous"], c["horizon_bars"], c["id"]))
                conn.commit()
                print(f"[APPLY] committed chunk {i//BATCH + 1}/{n_chunks} ({len(chunk)} rows)")
            print(f"[APPLY] wrote {len(corrections)} intrabar_* parallel rows. Canonical status/pnl_pct UNCHANGED.")
            print("[APPLY] rollback: UPDATE trading_picks SET intrabar_status=NULL,intrabar_pnl_pct=NULL,intrabar_ambiguous=NULL,intrabar_horizon_bars=NULL,intrabar_resolved_at=NULL; snapshot in ejaguiar1_backups.reresolve_intrabar_backup")
        except Exception as exc:
            print(f"[APPLY] FAILED (rolled back main conn): {exc}", file=sys.stderr)
            try: conn.rollback()
            except Exception: pass
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
