#!/usr/bin/env python3
"""One-shot backfill for INCIDENT_OVERALL #94 — TIME_EXIT pnl=0 bug.

Iterates 33,172 trading_picks rows where status='TIME_EXIT' and pnl_pct=0,
fetches the close-time market price via yfinance (equity/etf/forex) or
Binance fallback chain (crypto), recomputes pnl_pct, writes back.

USAGE (operator):
    python3 tools/backfill_time_exit_pnl.py --dry-run    # preview, no writes
    python3 tools/backfill_time_exit_pnl.py              # apply

Idempotent — re-runs only update rows where pnl_pct is still NULL or 0.
Safe — skips rows where fetched price is None (data unavailable).

After running, sanity check:
    SELECT COUNT(*) FROM trading_picks WHERE status='TIME_EXIT' AND pnl_pct=0;
should drop from ~33172 toward the no-data residual.
"""
import os, sys, time, argparse, json, urllib.request
from datetime import datetime, timezone, timedelta
import pymysql

DRIFT_BY_CLASS_ABS = {"crypto":0.5, "etf":0.05, "equity":0.10, "forex":0.03, "bond":0.05}

def connect():
    from tools.db_env import get_stocks_creds
    return pymysql.connect(**get_stocks_creds())

def fetch_close_yfinance(symbol, ts):
    try:
        import yfinance as yf
        clean = symbol.lstrip("$")
        if not symbol.endswith("=X") and (symbol.startswith("EUR") or symbol.startswith("GBP")
                                          or symbol.startswith("USD") or symbol.startswith("AUD")
                                          or symbol.startswith("NZD")):
            clean = clean + "=X"
        df = yf.download(clean, start=(ts - timedelta(days=2)).strftime("%Y-%m-%d"),
                         end=(ts + timedelta(days=2)).strftime("%Y-%m-%d"),
                         auto_adjust=False, progress=False, threads=False)
        if hasattr(df.columns, "get_level_values"):
            df.columns = df.columns.get_level_values(0)
        if df.empty: return None
        bd = [d.date() for d in df.index]
        idx = min(range(len(bd)), key=lambda i: abs((bd[i] - ts.date()).days))
        return float(df.iloc[idx]["Close"])
    except Exception:
        return None

def fetch_close_binance(symbol, ts_ms):
    s = symbol.upper().strip("$")
    if not s.endswith("USDT"): s = s + "USDT"
    for host in ("api","api1","api2","api3"):
        try:
            url=f"https://{host}.binance.com/api/v3/klines?symbol={s}&interval=1h&startTime={ts_ms}&endTime={ts_ms+3600000}&limit=2"
            req=urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                d = json.loads(r.read())
                if d: return float(d[0][4])  # close price
        except Exception:
            continue
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="stop after N successful backfills (0=all)")
    args = ap.parse_args()
    c = connect()
    with c.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute("""
            SELECT id, symbol, direction, category, entry_price, created_at, closed_at, exit_reason
            FROM trading_picks
            WHERE status='TIME_EXIT' AND (pnl_pct=0 OR pnl_pct IS NULL)
              AND symbol IS NOT NULL AND entry_price > 0
            ORDER BY closed_at DESC
        """)
        rows = cur.fetchall()
    c.close()
    print(f"candidate rows: {len(rows)}")
    if args.dry_run: print("(dry-run: no writes)")
    fixed = 0; nodata = 0; skipped = 0
    for i, r in enumerate(rows):
        if args.limit and fixed >= args.limit: break
        if i % 250 == 0 and i:
            print(f"  {i}/{len(rows)} fixed={fixed} nodata={nodata}", flush=True)
        ca = r.get("closed_at") or r.get("created_at")
        if not ca: skipped += 1; continue
        if isinstance(ca, str):
            ts = datetime.fromisoformat(ca.replace("Z","+00:00"))
        else:
            ts = ca.replace(tzinfo=timezone.utc) if ca.tzinfo is None else ca
        cat = (r.get("category") or "").lower()
        sym = r["symbol"]
        close = None
        if cat in ("crypto","meme","memecoin"):
            close = fetch_close_binance(sym, int(ts.timestamp()*1000)//3600000*3600000)
        else:
            close = fetch_close_yfinance(sym, ts)
        if close is None or close <= 0:
            nodata += 1; continue
        entry = float(r["entry_price"])
        direction = (r.get("direction") or "LONG").upper()
        mult = 1 if direction in ("LONG","BUY") else -1
        pnl_pct = (close - entry) / entry * mult * 100
        # Sanity: cap absurd values (likely stale-data)
        if abs(pnl_pct) > 200:
            skipped += 1; continue
        if args.dry_run:
            fixed += 1
            if fixed <= 5:
                print(f"  would update id={r['id']} {sym} entry={entry} close={close} pnl={pnl_pct:.3f}%")
            continue
        try:
            c2 = connect()
            with c2.cursor() as cur2:
                cur2.execute("""UPDATE trading_picks SET exit_price=%s, pnl_pct=%s,
                                exit_reason=COALESCE(NULLIF(exit_reason,''),'TIME_EXIT_BACKFILLED_2026_06_04')
                                WHERE id=%s AND status='TIME_EXIT' AND (pnl_pct=0 OR pnl_pct IS NULL)""",
                             (close, pnl_pct, r["id"]))
                c2.commit()
                fixed += cur2.rowcount
            c2.close()
        except Exception as e:
            print(f"  WARN id={r['id']}: {e}")
            skipped += 1
    print(f"\nFINAL: candidate={len(rows)} fixed={fixed} nodata={nodata} skipped={skipped}")

if __name__ == "__main__":
    main()
