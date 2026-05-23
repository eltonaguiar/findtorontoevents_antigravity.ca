#!/usr/bin/env python3
"""Donchian 52-week breakout with volume confirmation.

4/4-engine swarm consensus: Donchian 1960s Turtle Trading + volume validation
to reduce fake breakouts (~70% of raw breakouts per literature).

Spec:
  Long entry: close = 252-day high (52w breakout) AND volume > 1.5× 20d avg vol
  Exit: 20-day trailing low (Turtle exit) OR 8% stop-loss from entry

Universe: 30 large-cap US (same as 200MA+ADX run for comparability).

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


def fetch_daily(tickers, start, end):
    return yf.download(tickers, start=start, end=end, interval="1d",
                       progress=False, auto_adjust=True)


def backtest_ticker(df_ticker, lookback_high=252, lookback_low=20,
                     vol_lookback=20, vol_mult=1.5, stop_pct=8.0):
    if "Close" not in df_ticker.columns or len(df_ticker) < lookback_high + 30:
        return None
    close = df_ticker["Close"]; high = df_ticker["High"]; low = df_ticker["Low"]
    vol = df_ticker["Volume"]
    rolling_high = high.rolling(lookback_high).max().shift(1)  # prior 252d high (excl today)
    rolling_low = low.rolling(lookback_low).min().shift(1)
    avg_vol = vol.rolling(vol_lookback).mean().shift(1)
    trades = []
    in_position = False
    entry_idx = None
    entry_price = None
    for i in range(lookback_high, len(close)):
        if not in_position:
            if (close.iloc[i] > rolling_high.iloc[i] and
                vol.iloc[i] > vol_mult * avg_vol.iloc[i] and
                not pd.isna(rolling_high.iloc[i])):
                in_position = True
                entry_idx = i
                entry_price = close.iloc[i]
        else:
            stop_price = entry_price * (1 - stop_pct/100)
            exit_now = (close.iloc[i] < rolling_low.iloc[i]) or (close.iloc[i] < stop_price)
            if exit_now:
                ret = (close.iloc[i]/entry_price - 1) * 100
                trades.append({
                    "entry_idx": entry_idx, "exit_idx": i,
                    "entry_date": close.index[entry_idx].strftime("%Y-%m-%d"),
                    "exit_date": close.index[i].strftime("%Y-%m-%d"),
                    "ret_pct": float(ret),
                    "days_held": i - entry_idx,
                    "exit_reason": "stop" if close.iloc[i] < stop_price else "trailing_low",
                })
                in_position = False
                entry_idx = None
    if in_position:
        ret = (close.iloc[-1]/entry_price - 1) * 100
        trades.append({"entry_idx": entry_idx, "exit_idx": len(close)-1,
                       "entry_date": close.index[entry_idx].strftime("%Y-%m-%d"),
                       "exit_date": close.index[-1].strftime("%Y-%m-%d"),
                       "ret_pct": float(ret), "days_held": len(close)-1-entry_idx,
                       "exit_reason": "open_at_end"})
    return trades


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2010-01-01")
    p.add_argument("--end", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    p.add_argument("--out", default="audit_dashboard/data/donchian_52w_volume_backtest.json")
    args = p.parse_args()

    print(f"# fetching {len(UNIVERSE)} tickers", file=sys.stderr)
    df = fetch_daily(UNIVERSE, args.start, args.end)

    all_trades = []
    per_ticker = {}
    for sym in UNIVERSE:
        try:
            if isinstance(df.columns, pd.MultiIndex):
                df_t = df.xs(sym, axis=1, level=1)
            else: df_t = df
        except KeyError: continue
        trades = backtest_ticker(df_t)
        if not trades: continue
        for t in trades: t["ticker"] = sym
        all_trades.extend(trades)
        pnls = [t["ret_pct"] for t in trades]
        w = sum(1 for p in pnls if p > 0); l = sum(1 for p in pnls if p < 0)
        wr = w/(w+l)*100 if (w+l) else 0
        per_ticker[sym] = {"n": len(pnls), "wr_pct": round(wr,1),
                          "mean_ret": round(float(np.mean(pnls)),2) if pnls else 0}

    n = len(all_trades)
    if n == 0:
        print("# no trades"); return
    pnls = [t["ret_pct"]/100 for t in all_trades]
    w = sum(1 for p in pnls if p > 0); l = sum(1 for p in pnls if p < 0)
    wr = w/(w+l)*100 if (w+l) else 0
    wins = [p for p in pnls if p > 0]
    losses = [abs(p) for p in pnls if p < 0]
    pf = sum(wins)/sum(losses) if losses else 999
    mean_r = float(np.mean(pnls))
    std_r = float(np.std(pnls, ddof=1)) if len(pnls)>1 else 0
    avg_days = float(np.mean([t["days_held"] for t in all_trades]))
    trades_per_year = 252/max(avg_days, 1)
    sharpe = (mean_r/std_r * np.sqrt(trades_per_year)) if std_r>0 else 0
    eq = 1.0; peak = 1.0; max_dd = 0
    for p in pnls:
        eq *= 1 + p
        peak = max(peak, eq); dd = (peak-eq)/peak
        max_dd = max(max_dd, dd)

    print(f"\n## Donchian 52w + Volume breakout (n={n} trades across {len(per_ticker)} tickers)")
    print(f"WR={wr:.1f}%  PF={pf:.2f}  mean={mean_r*100:+.2f}%  std={std_r*100:.2f}%")
    print(f"avg_days={avg_days:.0f}  trades/yr={trades_per_year:.2f}  Sharpe={sharpe:.2f}")
    print(f"MDD={max_dd*100:.1f}%")

    # Exit reason breakdown
    from collections import Counter
    exit_reasons = Counter(t.get("exit_reason","?") for t in all_trades)
    print(f"\nExit reasons: {dict(exit_reasons)}")

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "Donchian 52w high + volume 1.5x avg breakout, Turtle Trading",
        "universe": UNIVERSE,
        "config": {"start": args.start, "end": args.end,
                   "lookback_high_days": 252, "lookback_low_days": 20,
                   "vol_lookback_days": 20, "vol_mult": 1.5, "stop_pct": 8.0},
        "results": {"n_trades": n, "win_rate_pct": round(wr,2),
                    "profit_factor": round(pf,4),
                    "sharpe_annualized": round(float(sharpe),4),
                    "max_drawdown_pct": round(float(max_dd)*100,2),
                    "mean_ret_pct": round(mean_r*100,4),
                    "avg_days_held": round(avg_days,1)},
        "per_ticker": per_ticker,
        "exit_reasons": dict(exit_reasons),
        "expected_per_swarm": {"pf": 2.0, "sharpe": 0.95, "mdd_pct": 22},
        "nfa": "Hindsight backtest.",
    }
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\n# wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
