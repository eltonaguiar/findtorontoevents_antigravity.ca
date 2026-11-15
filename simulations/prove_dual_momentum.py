#!/usr/bin/env python3
"""
Simulation 3: Prove Dual Momentum (Faber-Style Tactical Asset Allocation)
=========================================================================
Tests Gary Antonacci's Dual Momentum strategy — one of the most documented
simple tactical approaches. Combines absolute momentum (is the asset above
its 10-month SMA?) with relative momentum (which asset has the best 12-month
return?).

This is a lower-frequency, higher-probability approach than daily trading.
It is designed to avoid bear markets while capturing bull market upside.

Universe: SPY (US equity), VTI (total US), VXUS (international), BND (bonds), SHY (T-bills)
Rules:
  1. Compute 12-month return for each asset
  2. Compute 10-month SMA for each asset
  3. Filter: only assets with price > 10-month SMA (absolute momentum)
  4. Select the asset with the highest 12-month return (relative momentum)
  5. If no asset passes absolute momentum, hold SHY (T-bills)
  6. Rebalance monthly
  7. Cost: 0.10% per rebalance
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

# ── Configuration ──────────────────────────────────────────────────────────
START_DATE = "2010-01-01"
END_DATE = "2026-11-14"
TICKERS = ["SPY", "VTI", "VXUS", "BND", "SHY"]
SMA_MONTHS = 10
MOMENTUM_MONTHS = 12
REBALANCE_FREQ = "M"  # Monthly
COST_PER_REBALANCE = 0.001  # 0.10%

OUT_PATH = Path(__file__).parent / "results_dual_momentum.json"


def fetch_data(tickers: list[str]) -> pd.DataFrame:
    """Download monthly adjusted close prices."""
    print(f"[DUAL MOMENTUM] Fetching {tickers} monthly data from {START_DATE} to {END_DATE}...")
    data = yf.download(tickers, start=START_DATE, end=END_DATE, interval="1mo", progress=False, auto_adjust=True)["Close"]
    if isinstance(data, pd.Series):
        data = data.to_frame()
    data = data.dropna()
    print(f"[DUAL MOMENTUM] Loaded {len(data)} months.")
    return data


def backtest_dual_momentum(prices: pd.DataFrame) -> pd.Series:
    """
    Backtest dual momentum strategy.
    Returns monthly portfolio value series.
    """
    # Compute 10-month SMA and 12-month momentum
    sma = prices.rolling(window=SMA_MONTHS, min_periods=SMA_MONTHS).mean()
    momentum = prices.pct_change(MOMENTUM_MONTHS)

    # Align: we trade at the END of each month based on THAT month's close
    portfolio_value = [1.0]
    current_ticker = None

    for i in range(SMA_MONTHS + MOMENTUM_MONTHS, len(prices)):
        date = prices.index[i]
        prev_date = prices.index[i - 1]

        # Signals available at end of previous month
        price_prev = prices.iloc[i - 1]
        sma_prev = sma.iloc[i - 1]
        mom_prev = momentum.iloc[i - 1]

        # Absolute momentum filter: price > 10-month SMA
        abs_pass = mom_prev[mom_prev.index].dropna()
        # Actually use price > SMA
        pass_mask = price_prev > sma_prev
        pass_tickers = pass_mask[pass_mask].index.tolist()

        # Relative momentum: highest 12-month return among those that pass absolute
        selected = None
        if pass_tickers:
            mom_candidates = mom_prev[pass_tickers].dropna()
            if len(mom_candidates) > 0:
                selected = mom_candidates.idxmax()

        # Fallback to SHY if nothing passes
        if selected is None:
            selected = "SHY"

        # Compute return for this month (from prev close to this close)
        if current_ticker != selected:
            # Rebalance cost
            portfolio_value.append(portfolio_value[-1] * (1 - COST_PER_REBALANCE))
            current_ticker = selected
        else:
            portfolio_value.append(portfolio_value[-1])

        # Apply the selected asset's monthly return
        monthly_ret = prices.iloc[i][selected] / prices.iloc[i - 1][selected] - 1
        portfolio_value[-1] *= (1 + monthly_ret)

    return pd.Series(portfolio_value[1:], index=prices.index[SMA_MONTHS + MOMENTUM_MONTHS:])


def compute_metrics(values: pd.Series, annual_rf: float = 0.045) -> dict:
    """Compute risk-adjusted metrics from monthly values."""
    monthly_ret = values.pct_change().dropna()
    ann_ret = monthly_ret.mean() * 12
    ann_vol = monthly_ret.std() * np.sqrt(12)
    sharpe = (ann_ret - annual_rf) / ann_vol if ann_vol > 0 else 0

    cummax = values.cummax()
    dd = (values - cummax) / cummax
    max_dd = dd.min()
    calmar = ann_ret / abs(max_dd) if max_dd != 0 else 0

    wr = (monthly_ret > 0).mean()

    return {
        "total_return": round(values.iloc[-1] / values.iloc[0] - 1, 4),
        "annualized_return": round(ann_ret, 4),
        "annualized_volatility": round(ann_vol, 4),
        "sharpe_ratio": round(sharpe, 4),
        "max_drawdown": round(max_dd, 4),
        "calmar_ratio": round(calmar, 4),
        "win_rate_monthly": round(wr, 4),
        "n_months": len(monthly_ret),
    }


def main() -> int:
    prices = fetch_data(TICKERS)

    # Dual momentum backtest
    dm_values = backtest_dual_momentum(prices)

    # Benchmark: SPY buy-and-hold over same period
    bench_prices = prices["SPY"].loc[dm_values.index]
    bench_values = bench_prices / bench_prices.iloc[0]

    # Metrics
    dm_metrics = compute_metrics(dm_values)
    bench_metrics = compute_metrics(bench_values)

    excess_return = dm_metrics["annualized_return"] - bench_metrics["annualized_return"]
    tracking_error = (dm_values.pct_change().dropna() - bench_values.pct_change().dropna()).std() * np.sqrt(12)
    information_ratio = excess_return / tracking_error if tracking_error > 0 else 0

    # Drawdown comparison
    dm_dd = (dm_values - dm_values.cummax()) / dm_values.cummax()
    bench_dd = (bench_values - bench_values.cummax()) / bench_values.cummax()
    dd_benefit = dm_dd.min() - bench_dd.min()  # Less negative = better

    # Verdict
    deployable = False
    if dm_metrics["sharpe_ratio"] > bench_metrics["sharpe_ratio"] and dm_metrics["max_drawdown"] > bench_metrics["max_drawdown"] * 0.7:
        verdict = "PROMISING — higher Sharpe and controlled drawdown vs SPY"
        deployable = True
    elif dm_metrics["sharpe_ratio"] > bench_metrics["sharpe_ratio"]:
        verdict = "MARGINAL — better risk-adjusted return but not dramatically"
    else:
        verdict = "FAIL — does not improve on SPY buy-and-hold"

    results = {
        "simulation": "dual_momentum_tactical_allocation",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "parameters": {
            "start_date": START_DATE,
            "end_date": END_DATE,
            "universe": TICKERS,
            "sma_months": SMA_MONTHS,
            "momentum_months": MOMENTUM_MONTHS,
            "rebalance_frequency": REBALANCE_FREQ,
            "cost_per_rebalance": COST_PER_REBALANCE,
        },
        "portfolio_metrics": dm_metrics,
        "benchmark_metrics": bench_metrics,
        "excess_return_annual": round(excess_return, 4),
        "tracking_error": round(tracking_error, 4),
        "information_ratio": round(information_ratio, 4),
        "drawdown_benefit": round(dd_benefit, 4),
        "verdict": verdict,
        "deployable": deployable,
        "rationale": "Dual momentum is one of the few tactical approaches with multi-decade academic and practitioner support. If it fails here, tactical timing is not viable for this system.",
    }

    with open(OUT_PATH, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n[DUAL MOMENTUM] Results saved to {OUT_PATH}")
    print(f"  Dual Momentum:   AnnRet={dm_metrics['annualized_return']:.1%}, Sharpe={dm_metrics['sharpe_ratio']:.2f}, MaxDD={dm_metrics['max_drawdown']:.1%}")
    print(f"  Benchmark (SPY): AnnRet={bench_metrics['annualized_return']:.1%}, Sharpe={bench_metrics['sharpe_ratio']:.2f}, MaxDD={bench_metrics['max_drawdown']:.1%}")
    print(f"  Excess Return:   {excess_return:.2%}")
    print(f"  Information Ratio: {information_ratio:.2f}")
    print(f"  Drawdown Benefit: {dd_benefit:.1%} (less negative = better)")
    print(f"  Verdict:         {verdict}")
    print(f"  Deployable:      {deployable}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
