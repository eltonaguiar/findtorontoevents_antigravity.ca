#!/usr/bin/env python3
"""R3 FILL-CONVENTION AUDIT (REALTIMECHALLENGE kilo, Phase 0).

Question (pre-registered): How much of the gross edge is a fill-convention
artefact? Compare SAME-BAR-CLOSE (optimistic/look-ahead-ish) vs NEXT-BAR-OPEN
(honest) vs VWAP(typical) on the identical Donchian(20)+RSI rule.

Reproducible: `python3 reports/realtime_challenge/kilo/r3_fill_convention.py`
Read-only, public ccxt OHLCV. Gross only (fees handled in R1). Intrabar-pessimistic
(SL wins ties). Reports gross bp/trade per convention + n.
"""
import datetime, hashlib, json
import numpy as np

PAIRS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]
TF = "5m"; LIMIT = 500
TP_ATR = 2.0; SL_ATR = 1.0; MAX_HOLD = 24; ATR_N = 14; DON_N = 20; RSI_N = 14

def rsi(closes, n):
    d = np.diff(closes[-(n+1):]); up = d[d > 0].sum(); dn = -d[d < 0].sum()
    return 100 - 100/(1 + (up/dn if dn > 0 else 999))

def atr(highs, lows, closes, n):
    highs = np.asarray(highs, float); lows = np.asarray(lows, float); closes = np.asarray(closes, float)
    tr = np.maximum(highs[-n:] - lows[-n:],
                    np.maximum(abs(highs[-n:] - closes[-n-1:-1]),
                               abs(lows[-n:] - closes[-n-1:-1])))
    return tr.mean()

def run_convention(o, mode):
    """Return list of gross-return-per-trade (fraction) under a fill mode."""
    highs = [c[2] for c in o]; lows = [c[3] for c in o]; closes = [c[4] for c in o]
    trades = []
    i = DON_N + 1
    while i < len(o) - 1:
        prior_high = max(highs[i-DON_N:i])
        r = rsi(closes[:i+1], RSI_N)
        a = atr(highs[:i+1], lows[:i+1], closes[:i+1], ATR_N)
        long_setup = closes[i] > prior_high or r < 30
        if not long_setup or a <= 0:
            i += 1; continue
        # entry price by convention
        if mode == "same_bar_close":
            entry = closes[i]; j = i + 1
        elif mode == "next_bar_open":
            entry = o[i+1][1]; j = i + 2
        elif mode == "vwap":
            entry = (highs[i] + lows[i] + closes[i]) / 3.0; j = i + 1
        tp = entry + TP_ATR * a; sl = entry - SL_ATR * a
        exit_px = None
        for k in range(j, min(j + MAX_HOLD, len(o))):
            if lows[k] <= sl:            # SL first on tie (pessimistic)
                exit_px = sl; break
            if highs[k] >= tp:
                exit_px = tp; break
        if exit_px is None:
            exit_px = closes[min(j + MAX_HOLD - 1, len(o) - 1)]
        trades.append((exit_px - entry) / entry)
        i = j
    return trades

def main():
    import ccxt
    ex = ccxt.binance({"enableRateLimit": True})
    agg = {m: [] for m in ("same_bar_close", "next_bar_open", "vwap")}
    per = {}
    for p in PAIRS:
        o = ex.fetch_ohlcv(p, TF, limit=LIMIT)
        per[p] = {}
        for m in agg:
            t = run_convention(o, m)
            agg[m].extend(t); per[p][m] = (len(t), round(np.mean(t)*1e4, 2) if t else None)
    out = {"round": "R3", "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "pairs": PAIRS, "tf": TF, "limit": LIMIT,
           "rules": {"tp_atr": TP_ATR, "sl_atr": SL_ATR, "max_hold": MAX_HOLD},
           "per_pair": per, "aggregate": {}}
    for m, t in agg.items():
        out["aggregate"][m] = {"n": len(t), "gross_bp_per_trade": round(float(np.mean(t))*1e4, 3) if t else None}
    with open(__file__, "rb") as fh:
        out["artifact_sha"] = hashlib.sha256(fh.read()).hexdigest()[:16]
    print(json.dumps(out["aggregate"], indent=2))
    print("per_pair:", json.dumps(per))
    with open(__file__.replace(".py", ".json"), "w") as fh:
        json.dump(out, fh, indent=2)
    a = out["aggregate"]
    if a["same_bar_close"]["gross_bp_per_trade"] is not None and a["next_bar_open"]["gross_bp_per_trade"] is not None:
        s = a["same_bar_close"]["gross_bp_per_trade"]; n = a["next_bar_open"]["gross_bp_per_trade"]
        print(f"\nLEAST-SURVIVABLE NUMBER: same-bar-close {s}bp vs honest next-bar-open {n}bp "
              f"-> look-ahead inflation = {round(s-n,2)}bp/trade "
              f"({'HONEST' if n>0 else 'FLIPS NEGATIVE'})")

if __name__ == "__main__":
    main()