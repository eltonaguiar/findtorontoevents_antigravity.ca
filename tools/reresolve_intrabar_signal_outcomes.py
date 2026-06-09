#!/usr/bin/env python3
"""Intrabar re-resolution of at_signal_outcomes DIRECTLY (self-contained, no join).

WHY
---
Per Investigate-3 (2026-06-09): the money_ready_verdict intrabar truth never
reaches the verdict because at_pick_outcomes pick_ids are content-hashes that
JOIN ~0% to trading_picks (a MySQL string->0 coercion artifact). ~65% of
at_pick_outcomes is permanently orphaned from entry/TP/SL.

THE WIN: at_signal_outcomes (125,529 rows) is SELF-CONTAINED — it carries
entry_price + take_profit + stop_loss + direction + opened_at + closed_at +
symbol + asset_class in ONE row, so each pick replays first-touch with NO
key-mapping. 2,239 rows are replayable all-time across all 6 classes, and it is
the ONLY path that reaches FOREX/COMMODITY/EQUITY intrabar truth (those never
arrive via at_pick_outcomes->trading_picks).

This adapter reuses the PROVEN first-touch replay() from
tools/reresolve_intrabar.py verbatim (SL-wins-ties = conservative, ambiguous
flag) but:
  * reads at_signal_outcomes instead of trading_picks
  * branches crypto_ohlcv vs stock_ohlcv on asset_class
  * normalizes CRYPTO symbols (ABC-USD -> ABCUSDT, RNDR -> RENDER)
  * writes ADDITIVE shadow columns on at_signal_outcomes
      (intrabar_status / intrabar_pnl_pct / intrabar_ambiguous /
       intrabar_horizon_bars / intrabar_resolved_at)
NEVER touches canonical outcome / pnl_pct.

SAFETY
------
  * Additive-only: 5 new nullable shadow columns + a backup table in
    ejaguiar1_backups. Canonical outcome/pnl_pct untouched.
  * Idempotent: --apply only processes rows WHERE intrabar_resolved_at IS NULL.
  * Row-capped (--max, default 3000; 90d window default) to bound DB load.
  * First-touch replay, SL wins same-bar ties (conservative); ambiguous flagged.
  * DRY-RUN by default; --apply gated behind --i-understand-this-mutates-production.

USAGE
-----
    python3 tools/reresolve_intrabar_signal_outcomes.py                 # dry-run
    python3 tools/reresolve_intrabar_signal_outcomes.py --all-time      # ignore 90d window
    python3 tools/reresolve_intrabar_signal_outcomes.py --apply --i-understand-this-mutates-production
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
    from tools.db_env import get_stocks_creds, get_backups_creds
    # reuse the PROVEN replay / time / win helpers verbatim
    from tools.reresolve_intrabar import replay, _to_ms, _orig_is_win
except ImportError as exc:  # pragma: no cover
    print(f"missing deps: {exc}", file=sys.stderr)
    raise SystemExit(1)

CRYPTO_CLASSES = {"CRYPTO", "MEMECOIN", "MEME"}
# Ticker aliases where the signal table uses a different code than crypto_ohlcv.
CRYPTO_SYMBOL_ALIASES = {
    "RNDRUSDT": "RENDERUSDT",
}


def _is_long(direction) -> bool:
    return str(direction or "BUY").upper() in ("LONG", "BUY", "STRONG_BUY")


def valid_geometry(entry, tp, sl, direction) -> bool:
    """Reject corrupt TP/SL data BEFORE replay.

    A long must have sl < entry < tp; a short must have tp < entry < sl.
    ~12% of at_signal_outcomes replayable rows store a stop_loss on the WRONG
    side of entry (e.g. GMTUSDT LONG entry=0.01231 sl=0.6953 = 56x above entry),
    which makes first-touch trivially fire SL_HIT and compute a fake
    +5548% pnl. Those rows are unresolvable, not edge — exclude them.
    """
    try:
        e, t, s = float(entry), float(tp), float(sl)
    except (TypeError, ValueError):
        return False
    if e <= 0 or t <= 0 or s <= 0:
        return False
    if _is_long(direction):
        return s < e < t
    return t < e < s


def normalize_symbol(sym: str, asset_class: str) -> str:
    if sym is None:
        return ""
    s = str(sym).upper().strip()
    if str(asset_class or "").upper() in CRYPTO_CLASSES:
        s = s.replace("/", "").replace("-", "")
        if s.endswith("USD") and not s.endswith("USDT"):
            s = s[:-3] + "USDT"
        s = CRYPTO_SYMBOL_ALIASES.get(s, s)
    # non-crypto: stock_ohlcv stores symbols in the same raw form (AAPL, GC=F,
    # EURUSD=X) so no transform.
    return s


def fetch_picks(cur, max_n, window_days, only_unresolved):
    where = [
        "entry_price > 0", "take_profit > 0", "stop_loss > 0",
        "opened_at IS NOT NULL", "closed_at IS NOT NULL",
    ]
    if window_days:
        where.append(f"closed_at >= NOW() - INTERVAL {int(window_days)} DAY")
    if only_unresolved:
        where.append("intrabar_resolved_at IS NULL")
    q = (
        "SELECT id, symbol, direction, strategy, source_system, asset_class, "
        "entry_price, take_profit, stop_loss, outcome, pnl_pct, opened_at, closed_at "
        "FROM at_signal_outcomes WHERE " + " AND ".join(where) +
        " ORDER BY closed_at DESC"
    )
    if max_n:
        q += f" LIMIT {int(max_n)}"
    cur.execute(q)
    return cur.fetchall()


def fetch_ohlcv(cur, symbol, asset_class, start_ms, end_ms):
    table = "crypto_ohlcv" if str(asset_class or "").upper() in CRYPTO_CLASSES else "stock_ohlcv"
    cur.execute(
        f"SELECT timestamp, high, low, close FROM {table} "
        "WHERE symbol=%s AND timeframe='1h' AND timestamp>=%s AND timestamp<=%s "
        "ORDER BY timestamp",
        (symbol, start_ms, end_ms),
    )
    return cur.fetchall()


SHADOW_COLS = {
    "intrabar_status": "VARCHAR(20) NULL",
    "intrabar_pnl_pct": "DECIMAL(12,4) NULL",
    "intrabar_ambiguous": "TINYINT NULL",
    "intrabar_horizon_bars": "INT NULL",
    "intrabar_resolved_at": "DATETIME NULL",
}


def ensure_shadow_columns(cur, conn):
    cur.execute(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='at_signal_outcomes'"
    )
    existing = {r["COLUMN_NAME"] for r in cur.fetchall()}
    for col, typ in SHADOW_COLS.items():
        if col not in existing:
            cur.execute(f"ALTER TABLE at_signal_outcomes ADD COLUMN {col} {typ}")
            print(f"  [ddl] added column {col}")
    conn.commit()


def backup_rows(picks):
    bc = {k: v for k, v in get_backups_creds().items()
          if k in ("host", "user", "password", "database", "port", "connect_timeout")}
    bconn = pymysql.connect(**bc)
    bcur = bconn.cursor()
    bcur.execute("DROP TABLE IF EXISTS at_signal_outcomes_intrabar_backup")
    bcur.execute(
        "CREATE TABLE at_signal_outcomes_intrabar_backup ("
        "id BIGINT, symbol VARCHAR(50), direction VARCHAR(10), "
        "entry_price DECIMAL(18,8), take_profit DECIMAL(18,8), stop_loss DECIMAL(18,8), "
        "outcome VARCHAR(20), pnl_pct DECIMAL(12,4), opened_at DATETIME, "
        "closed_at DATETIME, asset_class VARCHAR(20), backed_up_at DATETIME)"
    )
    BATCH = 500
    rows = [
        (p["id"], p["symbol"], p["direction"], p["entry_price"], p["take_profit"],
         p["stop_loss"], p["outcome"], p["pnl_pct"], p["opened_at"], p["closed_at"],
         p["asset_class"]) for p in picks
    ]
    for i in range(0, len(rows), BATCH):
        bcur.executemany(
            "INSERT INTO at_signal_outcomes_intrabar_backup "
            "(id,symbol,direction,entry_price,take_profit,stop_loss,outcome,pnl_pct,"
            "opened_at,closed_at,asset_class) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            rows[i:i + BATCH])
    bconn.commit()
    bconn.close()
    print(f"  [backup] snapshot {len(rows)} rows -> ejaguiar1_backups.at_signal_outcomes_intrabar_backup")


def wr_pf(pnls, w, n):
    gw = sum(x for x in pnls if x > 0)
    gl = abs(sum(x for x in pnls if x < 0))
    pf = round(gw / gl, 3) if gl > 0 else (float("inf") if gw > 0 else 0.0)
    return (round(w / n * 100, 1) if n else 0.0), pf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=3000)
    ap.add_argument("--max-hold-bars", type=int, default=168,
                    help="Fixed forward horizon in 1h bars (default 168=7d), from opened_at.")
    ap.add_argument("--window-days", type=int, default=90,
                    help="Only rows closed within this many days (default 90).")
    ap.add_argument("--all-time", action="store_true", help="ignore --window-days")
    ap.add_argument("--min-strategy-n", type=int, default=10)
    ap.add_argument("--out", default=str(REPO / "reports" / "reresolve_intrabar_signal_outcomes_latest.json"))
    ap.add_argument("--apply", action="store_true", help="GATED: write intrabar shadow cols")
    ap.add_argument("--i-understand-this-mutates-production", action="store_true")
    args = ap.parse_args()

    if args.apply and not args.i_understand_this_mutates_production:
        print("REFUSING --apply without --i-understand-this-mutates-production", file=sys.stderr)
        return 2

    sc = {k: v for k, v in get_stocks_creds().items()
          if k in ("host", "user", "password", "database", "port", "connect_timeout")}
    conn = pymysql.connect(**sc, cursorclass=pymysql.cursors.DictCursor)
    cur = conn.cursor()

    # In --apply mode we need the shadow columns to exist before we can filter on
    # intrabar_resolved_at. Add them first (idempotent).
    only_unresolved = args.apply
    if args.apply:
        ensure_shadow_columns(cur, conn)

    window_days = None if args.all_time else args.window_days
    picks = fetch_picks(cur, args.max, window_days, only_unresolved)
    print(f"[reresolve-signal] loaded {len(picks)} replayable at_signal_outcomes rows "
          f"(window={'all-time' if args.all_time else str(window_days)+'d'}, "
          f"only_unresolved={only_unresolved})")

    if args.apply and picks:
        backup_rows(picks)

    # accumulators per asset_class and per (asset_class,strategy)
    per_class = defaultdict(lambda: {"n": 0, "orig_w": 0, "true_w": 0, "tp": 0, "sl": 0,
                                     "time_exit": 0, "reclass_tp_to_sl": 0, "no_data": 0,
                                     "bad_geometry": 0, "ambiguous": 0, "true_pnls": []})
    per_strat = defaultdict(lambda: {"n": 0, "orig_w": 0, "true_w": 0, "tp": 0, "sl": 0,
                                     "reclass_tp_to_sl": 0, "true_pnls": []})
    no_data_total = 0
    bad_geometry_total = 0
    horizon_ms = args.max_hold_bars * 3600 * 1000
    updates = []  # (id, status, pnl_pct, ambiguous, horizon)

    for p in picks:
        ac = str(p["asset_class"] or "").upper()
        # Reject corrupt TP/SL geometry BEFORE replay (poisons PF otherwise).
        if not valid_geometry(p["entry_price"], p["take_profit"], p["stop_loss"], p["direction"]):
            bad_geometry_total += 1
            per_class[ac].setdefault("bad_geometry", 0)
            per_class[ac]["bad_geometry"] += 1
            continue
        sym = normalize_symbol(p["symbol"], ac)
        start = _to_ms(p["opened_at"])
        if not start or not sym:
            no_data_total += 1
            per_class[ac]["no_data"] += 1
            continue
        end = start + horizon_ms
        bars = fetch_ohlcv(cur, sym, ac, start, end)
        entry = float(p["entry_price"]); tp = float(p["take_profit"]); sl = float(p["stop_loss"])
        ts, tpnl, used, ambiguous = replay(entry, tp, sl, p["direction"], bars)
        if ts is None:
            no_data_total += 1
            per_class[ac]["no_data"] += 1
            continue
        orig_w = _orig_is_win(p["outcome"], p["pnl_pct"])
        true_w = tpnl is not None and tpnl > 0
        c = per_class[ac]
        c["n"] += 1
        c["orig_w"] += int(orig_w); c["true_w"] += int(true_w)
        c["true_pnls"].append(tpnl)
        if ts == "TP_HIT": c["tp"] += 1
        elif ts == "SL_HIT": c["sl"] += 1
        else: c["time_exit"] += 1
        if ambiguous: c["ambiguous"] += 1
        if orig_w and ts == "SL_HIT": c["reclass_tp_to_sl"] += 1

        strat = (p.get("strategy") or p.get("source_system") or "(none)")
        skey = f"{ac}::{strat}"
        s = per_strat[skey]
        s["n"] += 1
        s["orig_w"] += int(orig_w); s["true_w"] += int(true_w)
        s["true_pnls"].append(tpnl)
        if ts == "TP_HIT": s["tp"] += 1
        elif ts == "SL_HIT": s["sl"] += 1
        if orig_w and ts == "SL_HIT": s["reclass_tp_to_sl"] += 1

        if args.apply:
            updates.append((ts, round((tpnl or 0) * 100, 4),
                            1 if ambiguous else 0, args.max_hold_bars, p["id"]))

    # ---- build report ----
    report = {"generated_at": datetime.now(timezone.utc).isoformat(),
              "source_table": "at_signal_outcomes",
              "picks_loaded": len(picks), "no_data_total": no_data_total,
              "bad_geometry_total": bad_geometry_total,
              "max_hold_bars": args.max_hold_bars,
              "window": "all-time" if args.all_time else f"{window_days}d",
              "per_class": [], "top_strategies": []}

    print("\n=== PER ASSET CLASS (intrabar-true, T2 = WR>=50 & PF>=1.5 & n>=100) ===")
    print(f"  {'class':10} {'n':>5} {'origWR':>7} {'trueWR':>7} {'truePF':>8} "
          f"{'TP':>4} {'SL':>4} {'TIME':>5} {'reclass%':>9} {'ndata':>6} T2")
    for ac, r in sorted(per_class.items(), key=lambda kv: -kv[1]["n"]):
        if r["n"] == 0 and r.get("bad_geometry", 0) == 0 and r["no_data"] == 0:
            continue
        if r["n"] == 0:
            print(f"  {ac[:10]:10} {0:5} {'-':>7} {'-':>7} {'-':>8} "
                  f"{0:4} {0:4} {0:5} {0:9} {r['no_data']:6} -- (bad_geom={r.get('bad_geometry',0)})")
            continue
        wr, pf = wr_pf(r["true_pnls"], r["true_w"], r["n"])
        owr = round(r["orig_w"] / r["n"] * 100, 1)
        recl = round(r["reclass_tp_to_sl"] / r["n"] * 100, 1)
        # intrabar WR = TP/(TP+SL) per the measurement spec
        tpsl = r["tp"] + r["sl"]
        intrabar_wr = round(r["tp"] / tpsl * 100, 1) if tpsl else 0.0
        pf_num = pf if pf != float("inf") else 999.0
        t2 = (intrabar_wr >= 50.0 and pf_num >= 1.5 and r["n"] >= 100)
        report["per_class"].append({
            "asset_class": ac, "n": r["n"], "orig_wr": owr,
            "intrabar_wr_tp_over_tpsl": intrabar_wr, "pnl_sign_wr": wr,
            "intrabar_pf": pf_num, "tp": r["tp"], "sl": r["sl"],
            "time_exit": r["time_exit"], "ambiguous": r["ambiguous"],
            "tp_to_sl_reclass_pct": recl, "no_data": r["no_data"],
            "bad_geometry": r.get("bad_geometry", 0), "t2_pass": t2})
        print(f"  {ac[:10]:10} {r['n']:5} {owr:7} {intrabar_wr:7} {str(pf):>8} "
              f"{r['tp']:4} {r['sl']:4} {r['time_exit']:5} {recl:9} {r['no_data']:6} "
              f"{'PASS' if t2 else '--'}")

    print(f"\n=== TOP STRATEGIES per class (n>={args.min_strategy_n}) ===")
    print(f"  {'class::strategy':44} {'n':>5} {'trueWR':>7} {'truePF':>8} {'reclass%':>9}")
    strat_out = []
    for skey, r in sorted(per_strat.items(), key=lambda kv: -kv[1]["n"]):
        if r["n"] < args.min_strategy_n:
            continue
        wr, pf = wr_pf(r["true_pnls"], r["true_w"], r["n"])
        tpsl = r["tp"] + r["sl"]
        intrabar_wr = round(r["tp"] / tpsl * 100, 1) if tpsl else 0.0
        pf_num = pf if pf != float("inf") else 999.0
        recl = round(r["reclass_tp_to_sl"] / r["n"] * 100, 1)
        strat_out.append({"key": skey, "n": r["n"], "intrabar_wr": intrabar_wr,
                          "intrabar_pf": pf_num, "tp_to_sl_reclass_pct": recl})
        print(f"  {skey[:44]:44} {r['n']:5} {intrabar_wr:7} {str(pf):>8} {recl:9}")
    report["top_strategies"] = strat_out

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2, default=str))
    print(f"\nReport: {args.out}")

    # ---- apply ----
    if args.apply and updates:
        print(f"\n[APPLY] writing {len(updates)} intrabar shadow rows (canonical UNTOUCHED)")
        BATCH = 500
        try:
            n_chunks = (len(updates) + BATCH - 1) // BATCH
            for i in range(0, len(updates), BATCH):
                chunk = updates[i:i + BATCH]
                cur.executemany(
                    "UPDATE at_signal_outcomes SET intrabar_status=%s, intrabar_pnl_pct=%s, "
                    "intrabar_ambiguous=%s, intrabar_horizon_bars=%s, intrabar_resolved_at=NOW() "
                    "WHERE id=%s", chunk)
                conn.commit()
                print(f"[APPLY] committed chunk {i//BATCH + 1}/{n_chunks} ({len(chunk)} rows)")
            print(f"[APPLY] wrote {len(updates)} intrabar_* shadow rows. Canonical outcome/pnl_pct UNCHANGED.")
            print("[APPLY] rollback: UPDATE at_signal_outcomes SET intrabar_status=NULL,"
                  "intrabar_pnl_pct=NULL,intrabar_ambiguous=NULL,intrabar_horizon_bars=NULL,"
                  "intrabar_resolved_at=NULL; snapshot in ejaguiar1_backups.at_signal_outcomes_intrabar_backup")
        except Exception as exc:
            print(f"[APPLY] FAILED (rolled back main conn): {exc}", file=sys.stderr)
            try: conn.rollback()
            except Exception: pass
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
