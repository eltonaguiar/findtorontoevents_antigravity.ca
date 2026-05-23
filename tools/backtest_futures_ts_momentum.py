#!/usr/bin/env python3
"""Backtest FUTURES time-series momentum (Moskowitz-Ooi-Pedersen 2012).

Classic CTA strategy: per-instrument 12-month look-back, go long if
return positive, go short if negative, sized by inverse volatility.
Monthly rebalance.

Universe: liquid yfinance continuous-contract futures.

Skips CL=F per memory (3.8% WR / -29.82% PnL, removed from FUTURES_SYMBOLS).

Hypothesis: TS-momentum is the most academically-robust strategy in
the FUTURES class. If it doesn't work, FUTURES class is genuinely dead
(not just an emitter-coverage gap).

Benchmark vs current /audit FUTURES class: 5.9% WR historical, silent-dead.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import numpy as np
    import pandas as pd
    import yfinance as yf
except ImportError as exc:
    print(f"ERROR: missing dependency: {exc}", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent

# Excludes CL=F per memory; includes liquid commodities + indices + bonds
DEFAULT_UNIVERSE = [
    "CT=F",   # cotton
    "GC=F",   # gold
    "SI=F",   # silver
    "HG=F",   # copper
    "ZC=F",   # corn
    "ZW=F",   # wheat
    "ZS=F",   # soybeans
    "NG=F",   # natgas (volatile)
    "ES=F",   # S&P 500 e-mini
    "NQ=F",   # nasdaq 100 e-mini
    "ZN=F",   # 10y treasury note
    "ZB=F",   # 30y treasury bond
    "6E=F",   # euro fx future
    "6J=F",   # yen fx future
]


def fetch_monthly_returns(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    df = yf.download(tickers, start=start, end=end, interval="1mo",
                     progress=False, auto_adjust=True)
    closes = df["Close"] if isinstance(df.columns, pd.MultiIndex) else df
    if isinstance(closes, pd.Series):
        closes = closes.to_frame()
    return closes.pct_change().dropna(how="all")


def ts_momentum_signals(returns: pd.DataFrame, lookback: int) -> pd.DataFrame:
    """Per-instrument: +1 if 12m return > 0, -1 if < 0, 0 otherwise."""
    rolling = (1 + returns).rolling(lookback).apply(lambda x: x.prod() - 1, raw=False)
    sig = rolling.applymap(lambda r: 0 if pd.isna(r) else (1 if r > 0 else -1))
    return sig


def inv_vol_weights(returns: pd.DataFrame, lookback: int = 36) -> pd.DataFrame:
    """Inverse-volatility per instrument; row-normalized to sum |w|=1."""
    vol = returns.rolling(lookback).std()
    inv = 1.0 / vol.replace(0, np.nan)
    row_sum = inv.abs().sum(axis=1)
    weights = inv.div(row_sum, axis=0)
    return weights


def run_backtest(returns: pd.DataFrame, lookback_signal: int = 12,
                 lookback_vol: int = 36) -> dict:
    sig = ts_momentum_signals(returns, lookback_signal)
    weights = inv_vol_weights(returns, lookback_vol)
    # Position = sign × inverse-vol weight; rebalance at each row
    positions = sig * weights
    # Realized portfolio return = sum(position_t * return_{t+1})
    period_returns = (positions.shift(1) * returns).sum(axis=1).dropna()
    period_returns = period_returns.iloc[max(lookback_signal, lookback_vol):]
    if period_returns.empty:
        return {"n_periods": 0, "error": "insufficient_data"}
    equity = (1 + period_returns).cumprod()
    final_eq = equity.iloc[-1]
    peak = equity.cummax()
    max_dd = ((peak - equity) / peak).max()
    wins = int((period_returns > 0).sum())
    losses = int((period_returns < 0).sum())
    n = wins + losses
    wr = (wins / n * 100) if n else 0
    win_sum = float(period_returns[period_returns > 0].sum())
    loss_sum = float(abs(period_returns[period_returns < 0].sum()))
    pf = (win_sum / loss_sum) if loss_sum > 0 else (
        float("inf") if win_sum > 0 else 0.0
    )
    mean_r = float(period_returns.mean())
    std_r = float(period_returns.std())
    sharpe = (mean_r / std_r * np.sqrt(12)) if std_r > 0 else 0
    return {
        "n_periods": n,
        "win_rate_pct": round(wr, 2),
        "profit_factor": round(pf, 4) if pf != float("inf") else None,
        "sharpe_annualized": round(float(sharpe), 4),
        "max_drawdown_pct": round(float(max_dd) * 100, 2),
        "total_return_pct": round(float(final_eq - 1) * 100, 2),
        "wins": wins, "losses": losses,
        "tail_returns": [
            {"period": str(d.date()), "ret_pct": round(float(r) * 100, 3)}
            for d, r in list(period_returns.items())[-12:]
        ],
    }


def _classify(r):
    pf = r.get("profit_factor") or 0
    wr = r.get("win_rate_pct") or 0
    n = r.get("n_periods") or 0
    mdd = r.get("max_drawdown_pct") or 999
    if pf >= 2 and wr >= 55 and mdd <= 10 and n >= 200: return "TIER_1"
    if pf >= 1.5 and wr >= 50 and mdd <= 20 and n >= 100: return "TIER_2"
    if pf >= 1.2 and wr >= 45 and mdd <= 25 and n >= 100: return "TIER_3"
    return "BELOW_T3"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2010-01-01")
    p.add_argument("--end", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    p.add_argument("--universe", nargs="*", default=DEFAULT_UNIVERSE)
    p.add_argument("--lookback-signal", type=int, default=12)
    p.add_argument("--lookback-vol", type=int, default=36)
    p.add_argument("--out", default="audit_dashboard/data/futures_ts_momentum_backtest.json")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    print(f"# fetching {len(args.universe)} futures contracts", file=sys.stderr)
    returns = fetch_monthly_returns(args.universe, args.start, args.end)
    print(f"# returns shape: {returns.shape}", file=sys.stderr)

    result = run_backtest(
        returns,
        lookback_signal=args.lookback_signal,
        lookback_vol=args.lookback_vol,
    )

    # Long-only variant
    sig_long = ts_momentum_signals(returns, args.lookback_signal).clip(lower=0)
    weights = inv_vol_weights(returns, args.lookback_vol)
    pos_long = sig_long * weights
    period_long = (pos_long.shift(1) * returns).sum(axis=1).dropna()
    period_long = period_long.iloc[max(args.lookback_signal, args.lookback_vol):]
    if not period_long.empty:
        eq_long = (1 + period_long).cumprod()
        peak_long = eq_long.cummax()
        mdd_long = ((peak_long - eq_long) / peak_long).max()
        wins_l = int((period_long > 0).sum())
        n_l = int(((period_long > 0) | (period_long < 0)).sum())
        wr_l = wins_l / n_l * 100 if n_l else 0
        sharpe_l = (period_long.mean() / period_long.std() * np.sqrt(12)
                    if period_long.std() > 0 else 0)
        long_only = {
            "n_periods": n_l,
            "win_rate_pct": round(wr_l, 2),
            "sharpe_annualized": round(float(sharpe_l), 4),
            "max_drawdown_pct": round(float(mdd_long) * 100, 2),
            "total_return_pct": round(float(eq_long.iloc[-1] - 1) * 100, 2),
        }
    else:
        long_only = None

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "FUTURES time-series momentum (Moskowitz-Ooi-Pedersen 2012)",
        "universe": args.universe,
        "config": {
            "start": args.start, "end": args.end,
            "lookback_signal_months": args.lookback_signal,
            "lookback_vol_months": args.lookback_vol,
            "weighting": "inverse-volatility (36m std)",
            "rebalance": "monthly",
        },
        "long_short_results": result,
        "long_only_results": long_only,
        "benchmark_audit_futures": {
            "n": 0, "wr_pct": 5.9, "verdict": "silent-dead per memory project_futures_kill_without_replacement",
        },
        "tier_comparison_long_short": _classify(result),
        "nfa": "Hindsight backtest. No real-money sizing.",
    }

    if args.dry_run:
        print(json.dumps(payload, indent=2, default=str))
        return

    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"# wrote {out_path}", file=sys.stderr)
    print(f"# LONG-SHORT: PF={result.get('profit_factor')} WR={result.get('win_rate_pct')}% "
          f"Sharpe={result.get('sharpe_annualized')} MDD={result.get('max_drawdown_pct')}% "
          f"Total={result.get('total_return_pct')}% (n={result.get('n_periods')})",
          file=sys.stderr)
    if long_only:
        print(f"# LONG-ONLY:  WR={long_only['win_rate_pct']}% "
              f"Sharpe={long_only['sharpe_annualized']} "
              f"MDD={long_only['max_drawdown_pct']}% Total={long_only['total_return_pct']}%",
              file=sys.stderr)


if __name__ == "__main__":
    main()
