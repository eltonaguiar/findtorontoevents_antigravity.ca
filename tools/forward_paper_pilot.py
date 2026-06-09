#!/usr/bin/env python3
"""4-week forward paper-pilot: replay each pick of a strategy on intrabar OHLCV
from its created_at forward up to --max-hold-bars (default 168=7d). Restricted
to picks created within the last --lookback-days (default 28=4w). READ-ONLY.
Outputs reports/forward_paper_pilot_<UTC>.json + a per-strategy summary.
"""
from __future__ import annotations
import argparse, json, sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
import pymysql
from tools.db_env import get_stocks_creds


def _to_ms(dt):
    if dt is None: return None
    if isinstance(dt, (int, float)): return int(dt)
    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def replay(entry, tp, sl, direction, bars):
    if not bars: return None, None, 0
    is_long = str(direction or "BUY").upper() in ("LONG", "BUY", "STRONG_BUY")
    for i, b in enumerate(bars):
        h, l = float(b["high"]), float(b["low"])
        if is_long:
            sl_hit, tp_hit = (l <= sl), (h >= tp)
        else:
            sl_hit, tp_hit = (h >= sl), (l <= tp)
        if sl_hit:
            pnl = (sl - entry) / entry if is_long else (entry - sl) / entry
            return "SL_HIT", pnl, i + 1
        if tp_hit:
            pnl = (tp - entry) / entry if is_long else (entry - tp) / entry
            return "TP_HIT", pnl, i + 1
    last = float(bars[-1]["close"])
    pnl = (last - entry) / entry if is_long else (entry - last) / entry
    return "TIME_EXIT", pnl, len(bars)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", required=True)
    ap.add_argument("--lookback-days", type=int, default=28, help="window of created_at")
    ap.add_argument("--max-hold-bars", type=int, default=168, help="forward horizon in 1h bars")
    ap.add_argument("--asset-class", default="CRYPTO")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    horizon_ms = args.max_hold_bars * 3600 * 1000
    since = datetime.now(timezone.utc) - timedelta(days=args.lookback_days)

    conn = pymysql.connect(**get_stocks_creds(), cursorclass=pymysql.cursors.DictCursor)
    cur = conn.cursor()
    if args.asset_class.upper() == "CRYPTO":
        cur.execute("""SELECT id, symbol, direction, entry_price, take_profit, stop_loss,
                              created_at, status, pnl_pct
                         FROM trading_picks
                        WHERE strategy=%s
                          AND entry_price>0 AND take_profit>0 AND stop_loss>0
                          AND created_at IS NOT NULL AND created_at>=%s
                          AND (category='crypto' OR symbol LIKE '%%USDT')
                        ORDER BY created_at DESC""", (args.strategy, since))
    else:
        cur.execute("""SELECT id, symbol, direction, entry_price, take_profit, stop_loss,
                              created_at, status, pnl_pct
                         FROM trading_picks
                        WHERE strategy=%s AND asset_class=%s
                          AND entry_price>0 AND take_profit>0 AND stop_loss>0
                          AND created_at IS NOT NULL AND created_at>=%s
                        ORDER BY created_at DESC""", (args.strategy, args.asset_class, since))
    picks = cur.fetchall()
    print(f"[pilot] {args.strategy}: loaded {len(picks)} picks in last {args.lookback_days}d "
          f"(since {since.strftime('%Y-%m-%d %H:%M')} UTC)")

    n = 0; w = 0; reclass = 0; no_data = 0
    pnls = []; details = []
    for p in picks:
        start = _to_ms(p["created_at"])
        if not start: continue
        end = start + horizon_ms
        cur.execute("""SELECT high, low, close FROM crypto_ohlcv
                        WHERE symbol=%s AND timeframe='1h' AND timestamp>=%s AND timestamp<=%s
                        ORDER BY timestamp""",
                    (p["symbol"], start, end))
        bars = cur.fetchall()
        ts, tpnl, used = replay(float(p["entry_price"]), float(p["take_profit"]),
                                float(p["stop_loss"]), p["direction"], bars)
        if ts is None:
            no_data += 1
            continue
        n += 1
        is_w = tpnl > 0
        if is_w: w += 1
        pnls.append(tpnl)
        if str(p.get("status") or "").upper() in ("TP_HIT","WON","WIN") and ts == "SL_HIT":
            reclass += 1
        details.append({"id": p["id"], "symbol": p["symbol"], "true_status": ts,
                        "true_pnl": round(tpnl * 100, 4),
                        "orig_status": p.get("status"), "bars_used": used})

    gw = sum(x for x in pnls if x > 0)
    gl = abs(sum(x for x in pnls if x < 0))
    pf = round(gw / gl, 3) if gl > 0 else (float("inf") if gw > 0 else 0.0)
    wr = round(w / n * 100, 1) if n else 0.0

    summary = {"strategy": args.strategy, "asset_class": args.asset_class,
               "lookback_days": args.lookback_days, "since_utc": since.isoformat(),
               "picks_loaded": len(picks), "replayed": n, "no_data": no_data,
               "true_wins": w, "true_wr_pct": wr, "true_pf": pf,
               "tp_to_sl_reclass": reclass,
               "forward_verdict": ("HOLDS" if (n >= 20 and wr >= 50 and pf > 1.5)
                                   else ("INSUFFICIENT" if n < 20 else "REFUTED")),
               "details": details[:200]}
    out = args.out or str(REPO / "reports" / f"forward_paper_pilot_{args.strategy}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(summary, indent=2))
    print(f"\n=== {args.strategy} forward ({args.lookback_days}d, {n} replayed) ===")
    print(f"  true WR {wr}%  true PF {pf}  reclass {reclass}  no_data {no_data}")
    print(f"  FORWARD VERDICT: {summary['forward_verdict']}")
    print(f"  report: {out}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
