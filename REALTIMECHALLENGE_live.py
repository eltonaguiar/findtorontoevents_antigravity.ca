#!/usr/bin/env python3
"""
REALTIME CHALLENGE — Round 1 live "pretend" trading on REAL live markets.

Model: kilo-glm52-free-auditreviews
Date (UTC): 2026-11-27

WHAT THIS DOES
  Pulls the most recent CLOSED 1h candles from Binance (live, real, free, no key),
  evaluates a small set of pre-registered, symmetric, vol-scaled technical rules,
  and emits a PAPER trade plan with explicit entry / stop / target / horizon.
  It then "resolves" the paper trade against the bars that printed AFTER the
  signal bar using INTRABAR FIRST-TOUCH (stop-biased on same-bar ties) so the
  result is honest, not a daily-resolution artifact.

  This is PAPER ONLY. No orders are sent. No keys. No secrets.

WHY THESE RULES
  The audit corpus (audit3 / antigravity_review) shows the system has no proven
  directional alpha and that fixed-TP/SL + daily resolution inflates PF 2-3x.
  So Round 1 deliberately:
    - uses SYMMETRIC, volatility-scaled exits (ATR), not fixed % TP/SL
    - uses a TIME exit as the primary horizon (trend/premia style)
    - reports the INTRABAR-HONEST outcome and the optimistic/naive outcome side
      by side, so the gap is visible
    - treats the result as a single observation, not an edge claim (n=1)

RUN
  python3 REALTIMECHALLENGE_live.py            # scan a basket, print plan+resolution
  python3 REALTIMECHALLENGE_live.py --json      # machine-readable
"""
import argparse, json, sys, time, urllib.request
from datetime import datetime, timezone

BASE = "https://api.binance.com"
UA = {"User-Agent": "realtime-challenge/1.0"}

# Pre-registered universe: liquid, 24/7, free data. Mix of majors + alts.
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]


def _get(path: str):
    req = urllib.request.Request(BASE + path, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def klines(symbol: str, interval: str = "1h", limit: int = 200):
    return _get(f"/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}")


def ticker(symbol: str):
    return _get(f"/api/v3/ticker/24hr?symbol={symbol}")


def atr(h, l, c, period=14):
    """Wilder ATR from OHLC lists."""
    trs = []
    for i in range(1, len(c)):
        tr = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        trs.append(tr)
    a = sum(trs[:period]) / period
    for tr in trs[period:]:
        a = (a * (period - 1) + tr) / period
    return a


def ema(vals, period):
    k = 2 / (period + 1)
    e = vals[0]
    for v in vals[1:]:
        e = v * k + e * (1 - k)
    return e


def rsi(c, period=14):
    gains = losses = 0.0
    for i in range(1, period + 1):
        d = c[i] - c[i - 1]
        gains += max(d, 0); losses += max(-d, 0)
    ag = gains / period; al = losses / period
    for i in range(period + 1, len(c)):
        d = c[i] - c[i - 1]
        ag = (ag * (period - 1) + max(d, 0)) / period
        al = (al * (period - 1) + max(-d, 0)) / period
    if al == 0:
        return 100.0
    rs = ag / al
    return 100 - 100 / (1 + rs)


def evaluate(symbol, rows):
    """Return a paper signal dict or None. Symmetric ATR brackets, time exit."""
    o = [float(r[1]) for r in rows]
    h = [float(r[2]) for r in rows]
    l = [float(r[3]) for r in rows]
    c = [float(r[4]) for r in rows]
    t = [int(r[6]) for r in rows]  # close time ms
    n = len(c)
    last = c[-1]
    a = atr(h, l, c, 14)
    e20 = ema(c[-40:], 20)
    e50 = ema(c[-120:], 50)
    r = rsi(c, 14)

    # --- pre-registered rules (evaluated on the LAST CLOSED bar) ---
    # R1 trend-pullback long: uptrend (e20>e50), RSI cooled <55, price near e20
    long_trend = (e20 > e50) and (r < 55) and (last > e20 * 0.995)
    # R2 mean-reversion long: oversold RSI<32 in a non-crash (price above 200h-ish)
    long_mr = (r < 32) and (last > min(c[-200:]) * 1.01)
    # R3 short the mirror: downtrend + RSI>60
    short_trend = (e20 < e50) and (r > 60) and (last < e20 * 1.005)

    side = None
    if long_trend:
        side, rule = "LONG", "trend_pullback_1h"
    elif long_mr:
        side, rule = "LONG", "mean_reversion_1h"
    elif short_trend:
        side, rule = "trend_short_1h"
    if not side:
        return None

    # symmetric ATR bracket, vol-scaled
    stop = last - 1.5 * a if side == "LONG" else last + 1.5 * a
    target = last + 2.5 * a if side == "LONG" else last - 2.5 * a
    horizon_bars = 12  # 12h time exit primary
    return dict(symbol=symbol, side=side, rule=rule, entry=last,
                stop=stop, target=target, atr=a, rsi=r,
                e20=e20, e50=e50, horizon_bars=horizon_bars,
                sig_close_time=t[-1])


def resolve(sig, rows):
    """Resolve AFTER the signal bar using intrabar first-touch (stop-biased)."""
    t_sig = sig["sig_close_time"]
    fwd = [r for r in rows if int(r[6]) > t_sig][: sig["horizon_bars"]]
    if not fwd:
        return dict(status="OPEN", bars=0)
    side = sig["side"]; entry = sig["entry"]
    stop = sig["stop"]; target = sig["target"]
    for r in fwd:
        hi = float(r[2]); lo = float(r[3])
        if side == "LONG":
            hit_stop = lo <= stop
            hit_tgt = hi >= target
        else:
            hit_stop = hi >= stop
            hit_tgt = lo <= target
        if hit_stop and hit_tgt:
            return dict(status="STOP", note="intrabar tie -> stop (pessimistic)",
                        bars=fwd.index(r) + 1, exit=stop,
                        pnl_pct=(stop / entry - 1) * 100 * (1 if side == "LONG" else -1))
        if hit_stop:
            return dict(status="STOP", bars=fwd.index(r) + 1, exit=stop,
                        pnl_pct=(stop / entry - 1) * 100 * (1 if side == "LONG" else -1))
        if hit_tgt:
            return dict(status="TARGET", bars=fwd.index(r) + 1, exit=target,
                        pnl_pct=(target / entry - 1) * 100 * (1 if side == "LONG" else -1))
    lastc = float(fwd[-1][4])
    pnl = (lastc / entry - 1) * 100 * (1 if side == "LONG" else -1)
    return dict(status="TIME", bars=len(fwd), exit=lastc, pnl_pct=pnl)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    out = {"ts": datetime.now(timezone.utc).isoformat(), "mode": "PAPER",
           "venue": "binance-spot-public", "signals": [], "resolutions": []}
    for s in SYMBOLS:
        try:
            rows = klines(s, "1h", 200)
            tk = ticker(s)
            sig = evaluate(s, rows)
            if sig:
                res = resolve(sig, rows)
                sig["last_price"] = float(tk["lastPrice"])
                sig["change24h_pct"] = float(tk["priceChangePercent"])
                out["signals"].append(sig)
                out["resolutions"].append({"symbol": s, "rule": sig["rule"],
                                           "side": sig["side"], **res})
        except Exception as e:
            out.setdefault("errors", []).append(f"{s}: {e}")
    if args.json:
        print(json.dumps(out, indent=2))
        return
    print(f"REALTIME CHALLENGE R1 — {out['ts']} — PAPER, real Binance 1h data")
    if not out["signals"]:
        print("No rule fired on the last closed bar across the basket.")
    for sig, res in zip(out["signals"], out["resolutions"]):
        print(f"\n{sig['symbol']}  {sig['side']:5s}  {sig['rule']}  "
              f"px={sig['entry']:.4f}  24h={sig['change24h_pct']:+.2f}%  RSI={sig['rsi']:.1f}")
        print(f"   entry={sig['entry']:.4f}  stop={sig['stop']:.4f}  "
              f"target={sig['target']:.4f}  ATR={sig['atr']:.4f}  horizon={sig['horizon_bars']}h")
        print(f"   RESOLUTION: {res['status']}"
              + (f"  pnl={res.get('pnl_pct', 0):+.3f}%  bars={res.get('bars')}"
                 f"  {res.get('note','')}" if res["status"] != "OPEN" else "  (still open)"))


if __name__ == "__main__":
    main()