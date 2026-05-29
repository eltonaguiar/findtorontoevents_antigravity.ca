#!/usr/bin/env python3
"""
backtest_ma_trend_montecarlo.py — independent verification + Monte-Carlo significance
test of the 200-day MA trend strategy (the one on /audit/ai_leaderboard.html), per asset class.

Rule (matches the leaderboard): long when Close > SMA200, flat when Close < SMA200, no TP.
No-lookahead: signal computed on bar t (data ≤ t), applied to bar t+1's return.

The leaderboard reports IS/OOS/holdout point estimates. This adds the two things it lacks:
  (1) BUY-AND-HOLD benchmark — does the MA timing beat just holding? (critical for crypto bull beta)
  (2) MONTE CARLO — is the edge real or luck?
      - random-day-selection null (1000×): hold the same # of days but on RANDOM days; p = P(random ≥ strategy).
        Tests whether the MA filter picks BETTER days than chance (isolates timing skill from exposure).
      - trade-return bootstrap (1000×): resample trades w/ replacement → PF 5/50/95 CI.

Data: yfinance daily, ~6y. Long-only/flat. 10bp round-trip cost per episode.
Run: python3 tools/backtest_ma_trend_montecarlo.py
NFA — research only.
"""
from __future__ import annotations
import math, random, statistics, sys

random.seed(20260529)  # deterministic MC
FEE = 0.0010
N_MC = 1000
UNIVERSE = {
    "CRYPTO":    ["BTC-USD","ETH-USD","BNB-USD","XRP-USD","LTC-USD","ADA-USD"],
    "EQUITY":    ["SPY","AAPL","MSFT","NVDA","JPM","XOM"],
    "ETF":       ["QQQ","DIA","IWM","XLK","XLF","XLE"],
    "FOREX":     ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X"],
    "COMMODITY": ["GLD","SLV","USO","DBC","PPLT"],
    "BOND":      ["TLT","IEF","LQD","HYG","AGG"],
    "FUTURES":   ["ES=F","NQ=F","CL=F","GC=F","ZB=F"],
}

def fetch(sym):
    try:
        import yfinance as yf
        df = yf.Ticker(sym).history(period="6y", interval="1d", auto_adjust=True)
        if df is None or df.empty: return None
        return [float(x) for x in df["Close"].tolist()]
    except Exception as e:
        print(f"    {sym}: {e}", file=sys.stderr); return None

def sma(v, p, i):
    return sum(v[i-p+1:i+1]) / p if i >= p-1 else None

def strat_daily_and_trades(closes):
    """Lagged-signal daily returns + per-episode trade returns. No lookahead."""
    n = len(closes)
    rets = [0.0]*n
    for i in range(1, n):
        rets[i] = closes[i]/closes[i-1] - 1
    sig = [0]*n
    for t in range(n):
        m = sma(closes, 200, t)
        sig[t] = 1 if (m is not None and closes[t] > m) else 0
    # strategy daily return uses YESTERDAY's signal (enter next day)
    strat_daily = [sig[i-1]*rets[i] for i in range(1, n)]
    # trades = contiguous in-market episodes
    trades = []; in_pos = False; entry_i = 0
    for t in range(200, n-1):
        if not in_pos and sig[t] == 1:
            in_pos = True; entry_i = t+1
        elif in_pos and sig[t] == 0:
            ex = t+1
            trades.append(closes[ex]/closes[entry_i] - 1 - 2*FEE); in_pos = False
    if in_pos:
        trades.append(closes[-1]/closes[entry_i] - 1 - 2*FEE)
    return strat_daily, sig[200:], rets[201:], trades

def maxdd(daily):
    eq=1.0; pk=1.0; mdd=0.0
    for r in daily: eq*=1+r; pk=max(pk,eq); mdd=max(mdd,(pk-eq)/pk)
    return mdd, eq-1

def sharpe(daily):
    xs=[r for r in daily]
    if len(xs)<2: return 0.0
    mu=statistics.mean(xs); sd=statistics.pstdev(xs)
    return (mu/sd*math.sqrt(252)) if sd else 0.0

def pf(trades):
    w=sum(t for t in trades if t>0); l=abs(sum(t for t in trades if t<=0))
    return (w/l) if l else float('inf')

def run_class(cls, syms):
    all_trades=[]; all_strat_daily=[]; days_in=0; days_tot=0
    bh_rets_per_sym=[]; strat_total_per=[]; bh_total_per=[]; strat_sh=[]; bh_sh=[]; strat_mdd=[]; bh_mdd=[]
    mc_better=0; mc_runs=0
    ok=0
    for s in syms:
        c=fetch(s)
        if not c or len(c)<260: print(f"    {s}: no/short data", file=sys.stderr); continue
        ok+=1
        sd, sig_av, ret_av, trades = strat_daily_and_trades(c)
        all_trades+=trades; all_strat_daily+=sd
        # buy-hold daily = market rets over same span (from bar 201)
        bh = [c[i]/c[i-1]-1 for i in range(1,len(c))]
        _,st_tot = maxdd(sd); _,bh_tot = maxdd(bh)
        strat_total_per.append(st_tot); bh_total_per.append(bh_tot)
        sm,_=maxdd(sd); bm,_=maxdd(bh); strat_mdd.append(sm); bh_mdd.append(bm)
        strat_sh.append(sharpe(sd)); bh_sh.append(sharpe(bh))
        # MC random-day-selection null on the aligned window (sig_av/ret_av)
        k=sum(sig_av); pool=ret_av; m=len(pool)
        if k>0 and m>k:
            strat_sum=sum(sig_av[i]*pool[i] for i in range(m))
            for _ in range(N_MC):
                idx=random.sample(range(m),k)
                rnd=sum(pool[i] for i in idx)
                if rnd>=strat_sum: mc_better+=1
                mc_runs+=1
            days_in+=k; days_tot+=m
    if ok==0: return None
    md,tot=maxdd(all_strat_daily)
    p_value = mc_better/mc_runs if mc_runs else 1.0
    # trade bootstrap PF CI
    pfs=[]
    if len(all_trades)>=10:
        for _ in range(N_MC):
            samp=[random.choice(all_trades) for _ in all_trades]
            pfs.append(pf(samp))
        pfs=[x for x in pfs if x!=float('inf')]
    wins=sum(1 for t in all_trades if t>0)
    return dict(
        n_syms=ok, n_trades=len(all_trades),
        wr=100*wins/len(all_trades) if all_trades else 0,
        pf=pf(all_trades),
        pf_ci=(round(statistics.quantiles(pfs,n=20)[0],2), round(statistics.quantiles(pfs,n=20)[18],2)) if len(pfs)>20 else (None,None),
        strat_sharpe=statistics.mean(strat_sh), bh_sharpe=statistics.mean(bh_sh),
        strat_mdd=100*statistics.mean(strat_mdd), bh_mdd=100*statistics.mean(bh_mdd),
        strat_ret=100*statistics.mean(strat_total_per), bh_ret=100*statistics.mean(bh_total_per),
        mc_p=p_value, days_exposure=100*days_in/days_tot if days_tot else 0,
    )

def main():
    print("=== 200-day SMA trend — verification + Monte Carlo per asset class (yfinance 6y, no-lookahead, 20bp) ===")
    print("MC null = random-day-selection (same days-in-market, random days); p<0.05 ⇒ MA timing beats chance.\n")
    rows={}
    for cls,syms in UNIVERSE.items():
        m=run_class(cls,syms)
        if not m: print(f"[{cls}] no data"); continue
        rows[cls]=m
        print(f"[{cls}] {m['n_syms']} syms, {m['n_trades']} trades, {m['days_exposure']:.0f}% time in market")
        print(f"   trade WR={m['wr']:.1f}% PF={m['pf']:.2f} (boot CI {m['pf_ci']})")
        print(f"   STRAT: ret={m['strat_ret']:+.0f}% Sharpe={m['strat_sharpe']:.2f} MaxDD={m['strat_mdd']:.0f}%")
        print(f"   BUYHOLD: ret={m['bh_ret']:+.0f}% Sharpe={m['bh_sharpe']:.2f} MaxDD={m['bh_mdd']:.0f}%")
        print(f"   MC p-value (timing vs random)={m['mc_p']:.3f}")
        # verdict
        beats_random = m['mc_p']<0.05
        better_risk = (m['strat_sharpe']>m['bh_sharpe']) or (m['strat_mdd']<0.6*m['bh_mdd'])
        if beats_random and better_risk: v="WORTHWHILE — timing beats chance AND better risk-adjusted than buy-hold"
        elif better_risk and not beats_random: v="DEFENSIVE ONLY — cuts drawdown vs buy-hold but timing not better than random days"
        elif beats_random: v="TIMING-REAL but doesn't beat buy-hold risk-adjusted"
        else: v="NOT WORTHWHILE — no timing edge over random, no risk-adjusted gain vs buy-hold"
        print(f"   => {v}\n")
    print("=== one-line verdicts ===")
    for cls,m in rows.items():
        print(f"  {cls:10} PF={m['pf']:.2f} Sharpe {m['strat_sharpe']:.2f} vs B&H {m['bh_sharpe']:.2f} | MaxDD {m['strat_mdd']:.0f}% vs {m['bh_mdd']:.0f}% | MC p={m['mc_p']:.3f}")
    print("\nNFA. Every figure computed from fetched yfinance OHLC. MC seed=20260529.")

if __name__ == "__main__":
    main()
