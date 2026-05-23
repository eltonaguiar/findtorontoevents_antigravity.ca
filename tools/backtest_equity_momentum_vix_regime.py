#!/usr/bin/env python3
"""EQUITY top-5 momentum with VIX regime overlay.

Per EQUITY swarm consensus 2026-05-13 (4/4 engines): add VIX-based regime
filter to existing top-5 12-1m momentum strategy.

Baseline (tools/backtest_equity_top_momentum.py): PF 2.82 / Sharpe 1.34 /
MDD 24.18% / +1516% 11y vs SPY +347%. TIER-2 confirmed; fails TIER-1 only
on MDD (24% > 10% target).

Swarm proposal: skip months where VIX is elevated (VIX > 25) or VIX term
structure is inverted (^VIX > ^VIX3M, signaling stress).

Expected per swarm: PF ~2.5-3.1, Sharpe 1.4-1.6, MDD 8-10% (TIER-1 plausible).

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


def fetch_monthly_returns(tickers, start, end):
    df = yf.download(tickers, start=start, end=end, interval="1mo",
                     progress=False, auto_adjust=True)
    closes = df["Close"] if isinstance(df.columns, pd.MultiIndex) else df
    if isinstance(closes, pd.Series): closes = closes.to_frame()
    return closes.pct_change().dropna(how="all")


def fetch_monthly_close(ticker, start, end):
    df = yf.download(ticker, start=start, end=end, interval="1mo",
                     progress=False, auto_adjust=True)
    if df.empty: return None
    close = df["Close"] if "Close" in df.columns else df.iloc[:, 0]
    if isinstance(close, pd.DataFrame): close = close.iloc[:, 0]
    return close


def momentum_score(returns, lookback, skip):
    if len(returns) < lookback + skip + 1:
        return pd.Series(dtype=float)
    window = returns.iloc[-(lookback + skip):-skip] if skip > 0 else returns.iloc[-lookback:]
    return (1 + window).prod() - 1


def run_with_vix_regime(returns, vix, n_long=5, lookback=12, skip=1,
                        vix_threshold=25.0):
    """Top-N momentum gated on prior-month VIX close < threshold."""
    trades = []
    eq = 1.0; peak = 1.0; max_dd = 0
    win_count = loss_count = 0
    win_pnl = loss_pnl = 0.0
    history = []
    skipped_months = 0
    active_months = 0
    for i in range(lookback + skip, len(returns)):
        sub = returns.iloc[:i]
        scores = momentum_score(sub, lookback=lookback, skip=skip).dropna()
        if scores.empty: continue
        # VIX check: look at the most recent VIX close <= current month-end
        signal_date = returns.index[i]
        vix_prior = vix[vix.index <= signal_date]
        if vix_prior.empty:
            skipped_months += 1
            continue
        vix_now = float(vix_prior.iloc[-1])
        if vix_now > vix_threshold:
            skipped_months += 1
            continue
        active_months += 1
        ranked = scores.sort_values(ascending=False)
        longs = ranked.head(n_long).index.tolist()
        nxt = returns.iloc[i]
        period_ret = nxt[longs].mean()
        if pd.isna(period_ret): continue
        eq *= 1 + period_ret
        if period_ret > 0: win_count += 1; win_pnl += period_ret
        elif period_ret < 0: loss_count += 1; loss_pnl += abs(period_ret)
        peak = max(peak, eq)
        dd = (peak - eq)/peak
        max_dd = max(max_dd, dd)
        trades.append(period_ret)
        history.append({"period": signal_date.strftime("%Y-%m-%d"),
                        "vix": round(vix_now, 2),
                        "longs": longs[:3],
                        "period_ret_pct": round(float(period_ret)*100, 3)})
    n = len(trades)
    if n == 0: return None
    wr = win_count/(win_count+loss_count)*100 if (win_count+loss_count) else 0
    pf = win_pnl/loss_pnl if loss_pnl > 0 else 999
    mean = float(np.mean(trades))
    std = float(np.std(trades, ddof=1)) if len(trades) > 1 else 0
    sharpe = (mean/std*np.sqrt(12)) if std > 0 else 0
    return {
        "n_periods": n,
        "win_rate_pct": round(wr, 2),
        "profit_factor": round(pf, 4),
        "sharpe_annualized": round(float(sharpe), 4),
        "max_drawdown_pct": round(float(max_dd)*100, 2),
        "total_return_pct": round(float(eq-1)*100, 2),
        "skipped_months": skipped_months,
        "active_months": active_months,
        "skipped_ratio_pct": round(skipped_months / (skipped_months + active_months) * 100, 2)
                              if (skipped_months + active_months) > 0 else 0,
        "history_tail": history[-12:],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2015-01-01")
    p.add_argument("--end", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    p.add_argument("--vix-thresholds", nargs="*", type=float,
                   default=[20.0, 22.0, 25.0, 28.0, 30.0])
    p.add_argument("--out", default="audit_dashboard/data/equity_momentum_vix_regime_backtest.json")
    args = p.parse_args()

    print(f"# fetching {len(UNIVERSE)} stocks + VIX", file=sys.stderr)
    returns = fetch_monthly_returns(UNIVERSE, args.start, args.end)
    vix_close = fetch_monthly_close("^VIX", args.start, args.end)
    if vix_close is None:
        print("ERROR: VIX fetch failed", file=sys.stderr); sys.exit(1)
    print(f"# returns shape: {returns.shape}", file=sys.stderr)
    print(f"# VIX bars: {len(vix_close)}", file=sys.stderr)

    # Baseline (no VIX filter)
    print(f"\n## Baseline (no VIX filter)", file=sys.stderr)
    eq = 1.0; peak = 1.0; max_dd = 0
    win = lo = 0; win_pnl = lo_pnl = 0
    trades_baseline = []
    for i in range(13, len(returns)):
        sub = returns.iloc[:i]
        scores = momentum_score(sub, lookback=12, skip=1).dropna()
        if scores.empty: continue
        longs = scores.sort_values(ascending=False).head(5).index.tolist()
        nxt = returns.iloc[i]
        pr = nxt[longs].mean()
        if pd.isna(pr): continue
        eq *= 1 + pr
        if pr > 0: win += 1; win_pnl += pr
        elif pr < 0: lo += 1; lo_pnl += abs(pr)
        peak = max(peak, eq)
        max_dd = max(max_dd, (peak-eq)/peak)
        trades_baseline.append(pr)
    n_b = len(trades_baseline)
    wr_b = win/(win+lo)*100 if (win+lo) else 0
    pf_b = win_pnl/lo_pnl if lo_pnl > 0 else 999
    mean_b = float(np.mean(trades_baseline))
    std_b = float(np.std(trades_baseline, ddof=1)) if len(trades_baseline) > 1 else 0
    sharpe_b = (mean_b/std_b*np.sqrt(12)) if std_b > 0 else 0
    baseline = {
        "n_periods": n_b, "win_rate_pct": round(wr_b, 2),
        "profit_factor": round(pf_b, 4),
        "sharpe_annualized": round(float(sharpe_b), 4),
        "max_drawdown_pct": round(float(max_dd)*100, 2),
        "total_return_pct": round(float(eq-1)*100, 2),
    }
    print(f"  PF={baseline['profit_factor']} Sharpe={baseline['sharpe_annualized']} "
          f"MDD={baseline['max_drawdown_pct']}% Total={baseline['total_return_pct']}%",
          file=sys.stderr)

    # Variants
    variants = []
    for vt in args.vix_thresholds:
        result = run_with_vix_regime(returns, vix_close, vix_threshold=vt)
        if not result: continue
        result["vix_threshold"] = vt
        variants.append(result)
        print(f"  VIX<{vt:>5.1f}: PF={result['profit_factor']:>5.2f} "
              f"Sharpe={result['sharpe_annualized']:>5.2f} "
              f"MDD={result['max_drawdown_pct']:>5.1f}% "
              f"Total={result['total_return_pct']:>+7.1f}% "
              f"skipped={result['skipped_ratio_pct']:>5.1f}% "
              f"(n={result['n_periods']})", file=sys.stderr)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "EQUITY top-5 12-1m momentum + VIX regime filter (skip when VIX > threshold)",
        "universe": UNIVERSE,
        "config": {"start": args.start, "end": args.end,
                   "n_long": 5, "lookback_months": 12, "skip_months": 1,
                   "vix_thresholds_tested": args.vix_thresholds},
        "baseline_no_vix_filter": baseline,
        "vix_threshold_variants": variants,
        "expected_per_swarm": {"pf": 2.5, "sharpe": 1.45, "mdd_pct": 8.5},
        "nfa": "Hindsight backtest.",
    }
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\n# wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
