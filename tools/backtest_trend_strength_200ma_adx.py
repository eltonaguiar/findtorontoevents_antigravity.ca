#!/usr/bin/env python3
"""Trend Strength: 200-day MA + ADX filter.

4/4 engine consensus (xai/deepseek/groq/cerebras) on academic literature:
Faber 2007, Moskowitz-Ooi-Pedersen 2012, Brock-Lakonishok-LeBaron 1992.

Spec:
  Long entry: price > 200-day SMA AND ADX(14) > 25
  Exit: price < 200-day SMA OR ADX(14) < 20

Universe: 30 large-cap US (same as backtest_equity_top_momentum). Equal-weight
across qualifying tickers each month.

Expected (per engines): PF 2.10, Sharpe 0.90-1.05, MDD 18-20%.

NFA — hindsight backtest.
"""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path
try:
    import numpy as np
    import pandas as pd
    import yfinance as yf
except ImportError as exc:
    print(f"ERROR: {exc}", file=sys.stderr); sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent

UNIVERSE = [
    "AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA","AVGO","ORCL",
    "JPM","BAC","WFC","GS","MS","BLK",
    "JNJ","PFE","UNH","ABBV","LLY",
    "WMT","HD","COST","KO","MCD",
    "XOM","CVX","PG","PEP","TMO",
]


def adx(high, low, close, period=14):
    """Wilder's ADX from scratch (avoids pandas-ta dependency)."""
    up = high.diff()
    down = -low.diff()
    plus_dm = ((up > down) & (up > 0)) * up
    minus_dm = ((down > up) & (down > 0)) * down
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1/period, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1/period, adjust=False).mean() / atr)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return dx.ewm(alpha=1/period, adjust=False).mean()


def fetch_daily(tickers, start, end):
    df = yf.download(tickers, start=start, end=end, interval="1d",
                     progress=False, auto_adjust=True)
    return df


def backtest_per_ticker(df_ticker):
    close = df_ticker["Close"]; high = df_ticker["High"]; low = df_ticker["Low"]
    if len(close) < 250: return None
    sma200 = close.rolling(200).mean()
    adx14 = adx(high, low, close, period=14)
    # Entry: close > sma200 AND adx > 25
    long_signal = (close > sma200) & (adx14 > 25)
    # Exit when close < sma200 OR adx < 20
    exit_signal = (close < sma200) | (adx14 < 20)
    # Build positions
    in_position = False
    trades = []
    entry_idx = None
    for i in range(200, len(close)):
        if not in_position and long_signal.iloc[i]:
            in_position = True
            entry_idx = i
        elif in_position and exit_signal.iloc[i]:
            exit_price = close.iloc[i]
            entry_price = close.iloc[entry_idx]
            ret = (exit_price / entry_price) - 1
            trades.append({"entry_idx": entry_idx, "exit_idx": i,
                           "entry_date": close.index[entry_idx].strftime("%Y-%m-%d"),
                           "exit_date": close.index[i].strftime("%Y-%m-%d"),
                           "ret_pct": float(ret * 100)})
            in_position = False
            entry_idx = None
    # Close open at end
    if in_position:
        ret = (close.iloc[-1] / close.iloc[entry_idx]) - 1
        trades.append({"entry_idx": entry_idx, "exit_idx": len(close)-1,
                       "entry_date": close.index[entry_idx].strftime("%Y-%m-%d"),
                       "exit_date": close.index[-1].strftime("%Y-%m-%d"),
                       "ret_pct": float(ret * 100), "open_at_end": True})
    return trades


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2010-01-01")
    p.add_argument("--end", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    p.add_argument("--out", default="audit_dashboard/data/trend_strength_200ma_adx_backtest.json")
    args = p.parse_args()

    print(f"# fetching {len(UNIVERSE)} tickers", file=sys.stderr)
    df = fetch_daily(UNIVERSE, args.start, args.end)

    all_trades = []
    per_ticker_stats = {}
    for sym in UNIVERSE:
        try:
            if isinstance(df.columns, pd.MultiIndex):
                df_t = df.xs(sym, axis=1, level=1)
            else:
                df_t = df
        except KeyError:
            continue
        trades = backtest_per_ticker(df_t)
        if not trades: continue
        for t in trades:
            t["ticker"] = sym
        all_trades.extend(trades)
        # per-ticker stats
        pnls = [t["ret_pct"] for t in trades]
        w = sum(1 for p in pnls if p > 0); l = sum(1 for p in pnls if p < 0)
        wr = w/(w+l)*100 if (w+l) else 0
        per_ticker_stats[sym] = {"n": len(pnls), "wr_pct": round(wr,1),
                                 "mean_ret": round(np.mean(pnls),2) if pnls else 0}

    # Aggregate
    n = len(all_trades)
    if n == 0:
        print("# no trades"); return
    pnls = [t["ret_pct"]/100 for t in all_trades]
    w = sum(1 for p in pnls if p > 0); l = sum(1 for p in pnls if p < 0)
    wr = w/(w+l)*100 if (w+l) else 0
    wins = [p for p in pnls if p > 0]
    losses = [abs(p) for p in pnls if p < 0]
    pf = sum(wins)/sum(losses) if losses else 999
    mean_r = np.mean(pnls)
    std_r = np.std(pnls, ddof=1) if len(pnls)>1 else 0
    # Average trade days (rough)
    avg_days = np.mean([(all_trades[i]["exit_idx"] - all_trades[i]["entry_idx"]) for i in range(len(all_trades))])
    # Sharpe annualized (assume avg trade ~50 days = ~5 trades/yr)
    trades_per_year = 252 / max(avg_days, 1)
    sharpe = (mean_r/std_r * np.sqrt(trades_per_year)) if std_r > 0 else 0

    # Cumulative equity assuming sequential same-capital across all-trades
    eq = 1.0; peak = 1.0; max_dd = 0
    for p in pnls:
        eq *= 1 + p
        peak = max(peak, eq)
        dd = (peak - eq)/peak
        max_dd = max(max_dd, dd)

    print(f"\n## Trend Strength 200MA+ADX backtest (n={n} trades across {len(per_ticker_stats)} tickers)")
    print(f"WR={wr:.1f}%  PF={pf:.2f}  mean={mean_r*100:+.2f}%  std={std_r*100:.2f}%")
    print(f"avg_trade_days={avg_days:.0f}  trades/yr={trades_per_year:.1f}  Sharpe={sharpe:.2f}")
    print(f"MDD={max_dd*100:.1f}%  final_eq_naive={(eq-1)*100:+.1f}%")
    print()
    print("Per-ticker:")
    for sym, s in sorted(per_ticker_stats.items(), key=lambda x: -x[1]["mean_ret"]):
        print(f"  {sym:6} n={s['n']:>3} WR={s['wr_pct']:>5.1f}%  mean={s['mean_ret']:>+6.2f}%")

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "Trend Strength 200MA+ADX(14) — Faber 2007 / Moskowitz-Ooi-Pedersen 2012",
        "universe": UNIVERSE,
        "config": {"start": args.start, "end": args.end,
                   "entry": "close > SMA(200) AND ADX(14) > 25",
                   "exit": "close < SMA(200) OR ADX(14) < 20"},
        "results": {
            "n_trades": n, "win_rate_pct": round(wr, 2),
            "profit_factor": round(pf, 4),
            "sharpe_annualized": round(float(sharpe), 4),
            "max_drawdown_pct": round(float(max_dd)*100, 2),
            "mean_ret_pct": round(float(mean_r)*100, 4),
            "avg_trade_days": round(float(avg_days), 1),
            "trades_per_year": round(float(trades_per_year), 2),
            "final_equity_naive": round(float(eq), 4),
        },
        "per_ticker": per_ticker_stats,
        "expected_per_swarm": {"pf": 2.10, "sharpe": 0.95, "mdd_pct": 19},
        "nfa": "Hindsight backtest. No real-money sizing.",
    }
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\n# wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
