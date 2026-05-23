#!/usr/bin/env python3
"""Donchian 52w breakout + Volume + VIX regime overlay.

Per pattern transfer this session (EQUITY VIX TIER-1 + ETF VIX TIER-1):
Test if VIX-regime gate also lifts Donchian breakout strategy.

Baseline Donchian 52w + Volume (n=491, 2010-2026): WR 48.9%, PF 2.36, Sharpe 0.46
Hypothesis: skip entries when VIX > threshold -> compress MDD without
killing PF (regime-gate pattern).

NFA - hindsight backtest.
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


def backtest_with_vix(df_ticker, vix_close, lookback_high=252, lookback_low=20,
                      vol_lookback=20, vol_mult=1.5, stop_pct=8.0,
                      vix_threshold=None):
    """Donchian + Volume + optional VIX threshold filter."""
    if "Close" not in df_ticker.columns or len(df_ticker) < lookback_high + 30:
        return None
    close = df_ticker["Close"]; high = df_ticker["High"]; low = df_ticker["Low"]
    vol = df_ticker["Volume"]
    rolling_high = high.rolling(lookback_high).max().shift(1)
    rolling_low = low.rolling(lookback_low).min().shift(1)
    avg_vol = vol.rolling(vol_lookback).mean().shift(1)
    trades = []
    in_position = False
    entry_idx = None; entry_price = None
    skipped = 0
    for i in range(lookback_high, len(close)):
        if not in_position:
            # Donchian + volume conditions
            if (close.iloc[i] > rolling_high.iloc[i]
                and vol.iloc[i] > vol_mult * avg_vol.iloc[i]
                and not pd.isna(rolling_high.iloc[i])):
                # VIX gate
                if vix_threshold is not None:
                    date_now = close.index[i]
                    vix_prior = vix_close[vix_close.index <= date_now]
                    if vix_prior.empty:
                        skipped += 1; continue
                    if float(vix_prior.iloc[-1]) > vix_threshold:
                        skipped += 1; continue
                in_position = True
                entry_idx = i; entry_price = close.iloc[i]
        else:
            stop_price = entry_price * (1 - stop_pct/100)
            exit_now = (close.iloc[i] < rolling_low.iloc[i]) or (close.iloc[i] < stop_price)
            if exit_now:
                ret = (close.iloc[i]/entry_price - 1) * 100
                trades.append({
                    "entry_date": close.index[entry_idx].strftime("%Y-%m-%d"),
                    "exit_date": close.index[i].strftime("%Y-%m-%d"),
                    "ret_pct": float(ret),
                    "days_held": i - entry_idx,
                })
                in_position = False
                entry_idx = None
    if in_position:
        ret = (close.iloc[-1]/entry_price - 1) * 100
        trades.append({
            "entry_date": close.index[entry_idx].strftime("%Y-%m-%d"),
            "exit_date": close.index[-1].strftime("%Y-%m-%d"),
            "ret_pct": float(ret), "days_held": len(close)-1-entry_idx,
        })
    return trades, skipped


def aggregate(all_trades):
    if not all_trades: return None
    pnls = [t["ret_pct"]/100 for t in all_trades]
    n = len(pnls)
    w = sum(1 for p in pnls if p > 0); l = sum(1 for p in pnls if p < 0)
    wr = w/(w+l)*100 if (w+l) else 0
    wins = [p for p in pnls if p > 0]
    losses = [abs(p) for p in pnls if p < 0]
    pf = sum(wins)/sum(losses) if losses else 999
    mean_r = float(np.mean(pnls))
    std_r = float(np.std(pnls, ddof=1)) if n > 1 else 0
    avg_days = float(np.mean([t["days_held"] for t in all_trades]))
    trades_per_year = 252/max(avg_days, 1)
    sharpe = (mean_r/std_r * np.sqrt(trades_per_year)) if std_r > 0 else 0
    # Single-asset compounded MDD
    eq = 1.0; peak = 1.0; max_dd = 0
    for p in pnls:
        eq *= 1 + p
        peak = max(peak, eq); max_dd = max(max_dd, (peak-eq)/peak)
    return {
        "n_trades": n, "win_rate_pct": round(wr, 2),
        "profit_factor": round(pf, 4),
        "sharpe_annualized": round(float(sharpe), 4),
        "mean_ret_pct": round(mean_r*100, 4),
        "single_asset_mdd_pct": round(float(max_dd)*100, 2),
        "avg_days_held": round(avg_days, 1),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2010-01-01")
    p.add_argument("--end", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    p.add_argument("--out", default="audit_dashboard/data/donchian_vix_regime_backtest.json")
    args = p.parse_args()

    print(f"# fetching {len(UNIVERSE)} tickers + VIX", file=sys.stderr)
    df = yf.download(UNIVERSE + ["^VIX"], start=args.start, end=args.end,
                     interval="1d", progress=False, auto_adjust=True)
    closes_only = df["Close"] if isinstance(df.columns, pd.MultiIndex) else df
    vix_close = closes_only["^VIX"] if "^VIX" in closes_only.columns else None
    if vix_close is None:
        print("ERROR: VIX missing", file=sys.stderr); sys.exit(1)

    results = {}
    for vt in [None, 18.0, 20.0, 22.0, 25.0, 30.0]:
        all_trades = []
        total_skipped = 0
        for sym in UNIVERSE:
            try:
                if isinstance(df.columns, pd.MultiIndex):
                    df_t = df.xs(sym, axis=1, level=1)
                else:
                    df_t = df
            except KeyError:
                continue
            res = backtest_with_vix(df_t, vix_close, vix_threshold=vt)
            if res is None: continue
            trades, skipped = res
            for t in trades: t["ticker"] = sym
            all_trades.extend(trades)
            total_skipped += skipped
        agg = aggregate(all_trades)
        if agg:
            agg["vix_threshold"] = vt
            agg["entries_skipped_by_vix"] = total_skipped
            label = "baseline" if vt is None else f"VIX<{vt:>5.1f}"
            results[label] = agg
            print(f"  {label}: n={agg['n_trades']:>4} WR={agg['win_rate_pct']:>5.1f}% "
                  f"PF={agg['profit_factor']:>5.2f} Sharpe={agg['sharpe_annualized']:>5.2f} "
                  f"MDD={agg['single_asset_mdd_pct']:>5.1f}% mean={agg['mean_ret_pct']:>+6.2f}% "
                  f"skipped={total_skipped}", file=sys.stderr)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "Donchian 52w + Volume + VIX regime overlay",
        "universe": UNIVERSE,
        "config": {"start": args.start, "end": args.end,
                   "lookback_high": 252, "lookback_low": 20,
                   "vol_mult": 1.5, "stop_pct": 8.0},
        "results_by_threshold": results,
        "nfa": "Hindsight backtest.",
    }
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\n# wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
