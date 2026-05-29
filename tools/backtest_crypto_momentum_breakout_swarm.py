#!/usr/bin/env python3
"""
backtest_crypto_momentum_breakout_swarm.py

Honest, no-lookahead backtest of the CRYPTO strategy the ParallelSwarm dry-run
generated (deepseek): "Crypto Momentum Breakout with Volume Confirmation".

  entry  : Close>SMA20 AND Close>upperBB(20,2) AND Vol>1.5*SMA20(Vol)
  filters: SMA20 slope>0 AND ADX(14)>25
  exit   : trailing stop 2*ATR(14) below highest-close-since-entry, OR TP 3*ATR(14) above entry

Discipline (matches metric-honesty-tiers): multi-symbol (no single-symbol artifact),
signal on bar t -> ENTER at bar t+1 open (no lookahead), trailing/TP checked intrabar
on each bar's high/low, long-only, fees+slippage applied. PF=sum(+)/|sum(-)|.

Data: Binance daily klines (public, no key), failover api->api1. ~1000d/symbol.
Run:  python3 tools/backtest_crypto_momentum_breakout_swarm.py
"""
from __future__ import annotations
import json, sys, urllib.request, urllib.error

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
INTERVAL, LIMIT = "1d", 1000
FEE_SLIP = 0.0010  # 10 bps per side (taker+slippage), applied on entry and exit

def fetch(sym):
    for host in ("https://api.binance.com", "https://api1.binance.com", "https://api2.binance.com"):
        try:
            url = f"{host}/api/v3/klines?symbol={sym}&interval={INTERVAL}&limit={LIMIT}"
            with urllib.request.urlopen(url, timeout=20) as r:
                k = json.load(r)
            # [openT, open, high, low, close, volume, ...]
            return [(float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])) for x in k]
        except Exception:
            continue
    return None

def sma(v, p, i):
    return sum(v[i-p+1:i+1]) / p if i >= p-1 else None

def std(v, p, i, mean):
    if i < p-1: return None
    seg = v[i-p+1:i+1]; return (sum((x-mean)**2 for x in seg)/p) ** 0.5

def wilder_atr(highs, lows, closes, p):
    n = len(closes); tr = [0.0]*n
    for i in range(1, n):
        tr[i] = max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
    atr = [None]*n
    if n > p:
        atr[p] = sum(tr[1:p+1])/p
        for i in range(p+1, n):
            atr[i] = (atr[i-1]*(p-1) + tr[i]) / p
    return atr

def wilder_adx(highs, lows, closes, p):
    n = len(closes)
    plus_dm = [0.0]*n; minus_dm = [0.0]*n; tr = [0.0]*n
    for i in range(1, n):
        up = highs[i]-highs[i-1]; dn = lows[i-1]-lows[i]
        plus_dm[i] = up if (up > dn and up > 0) else 0.0
        minus_dm[i] = dn if (dn > up and dn > 0) else 0.0
        tr[i] = max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
    adx = [None]*n
    if n < 2*p + 1: return adx
    atr = sum(tr[1:p+1]); apdm = sum(plus_dm[1:p+1]); amdm = sum(minus_dm[1:p+1])
    dx_hist = []
    for i in range(p+1, n):
        atr = atr - atr/p + tr[i]; apdm = apdm - apdm/p + plus_dm[i]; amdm = amdm - amdm/p + minus_dm[i]
        if atr == 0: continue
        pdi = 100*apdm/atr; mdi = 100*amdm/atr
        dx = 100*abs(pdi-mdi)/(pdi+mdi) if (pdi+mdi) else 0.0
        dx_hist.append((i, dx))
        if len(dx_hist) == p:
            adx[i] = sum(d for _, d in dx_hist)/p
        elif len(dx_hist) > p:
            adx[i] = (adx[dx_hist[-2][0]]*(p-1) + dx)/p
    return adx

def backtest_symbol(bars):
    o = [b[0] for b in bars]; h = [b[1] for b in bars]; l = [b[2] for b in bars]
    c = [b[3] for b in bars]; v = [b[4] for b in bars]
    n = len(c)
    atr = wilder_atr(h, l, c, 14); adx = wilder_adx(h, l, c, 14)
    trades = []; in_pos = False; entry=hi_close=stop=tp=0.0
    for t in range(21, n-1):  # need 20-bar windows; enter at t+1
        if in_pos:
            # update trailing on close, then check stop/tp on NEXT handling — manage on current bar t
            hi_close = max(hi_close, c[t])
            atr_e = atr[t] if atr[t] else 0
            stop = hi_close - 2*atr_e
            # intrabar: did low hit trailing stop or high hit TP this bar?
            exit_px = None
            if l[t] <= stop: exit_px = stop
            elif h[t] >= tp: exit_px = tp
            if exit_px is not None:
                ret = (exit_px/entry) - 1 - 2*FEE_SLIP
                trades.append(ret); in_pos = False
            continue
        # signal on bar t (data <= t), enter at t+1 open
        m = sma(c, 20, t); sd = std(c, 20, t, m) if m else None
        vm = sma(v, 20, t)
        if None in (m, sd, vm) or atr[t] is None or adx[t] is None: continue
        upper_bb = m + 2*sd
        slope_ok = (sma(c,20,t) or 0) > (sma(c,20,t-1) or 1e9)
        if c[t] > m and c[t] > upper_bb and v[t] > 1.5*vm and slope_ok and adx[t] > 25:
            entry = o[t+1] * (1 + 0*FEE_SLIP)  # fee applied at exit net (2*FEE_SLIP) to avoid double count
            hi_close = c[t]; tp = entry + 3*atr[t]; in_pos = True
    return trades

def metrics(rets):
    n = len(rets)
    if not n: return dict(n=0)
    wins = [r for r in rets if r > 0]; losses = [r for r in rets if r <= 0]
    gp = sum(wins); gl = abs(sum(losses))
    pf = gp/gl if gl else float('inf')
    # equity curve MDD (compounded)
    eq = 1.0; peak = 1.0; mdd = 0.0
    for r in rets:
        eq *= (1+r); peak = max(peak, eq); mdd = max(mdd, (peak-eq)/peak)
    return dict(n=n, wr=len(wins)/n, pf=pf, avg=sum(rets)/n, mdd=mdd,
                total_ret=eq-1)

def main():
    all_rets = []; per = {}
    for s in SYMBOLS:
        bars = fetch(s)
        if not bars or len(bars) < 60:
            print(f"  {s}: fetch failed/short", file=sys.stderr); continue
        r = backtest_symbol(bars); per[s] = metrics(r); all_rets += r
        m = per[s]
        print(f"  {s:9} n={m.get('n',0):3}  WR={m.get('wr',0)*100:5.1f}%  PF={m.get('pf',0):6.2f}  "
              f"avg={m.get('avg',0)*100:+5.2f}%  MDD={m.get('mdd',0)*100:4.1f}%  "
              f"({len(bars)}d {('%s..%s'%('',''))})")
    pooled = metrics(all_rets)
    print("\nPOOLED (all symbols, no-lookahead, net of "
          f"{FEE_SLIP*2*100:.0f}bp round-trip):")
    print(f"  n={pooled.get('n',0)}  WR={pooled.get('wr',0)*100:.1f}%  PF={pooled.get('pf',0):.2f}  "
          f"avg={pooled.get('avg',0)*100:+.2f}%/trade  MDD={pooled.get('mdd',0)*100:.1f}%  "
          f"cumRet={pooled.get('total_ret',0)*100:+.1f}%")
    print("\nBars vs targets:")
    print("  Tier-2 bar:        PF>=1.5  WR>=50%  n>=100")
    print("  CRYPTO incumbent:  PF 3.23  WR 17%   n=30  (pf_registry policy-clean)")
    print("  Swarm spec claim:  PF 1.6   WR 45%")
    return pooled

if __name__ == "__main__":
    main()
