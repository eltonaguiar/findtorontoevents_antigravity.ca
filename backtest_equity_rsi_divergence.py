#!/usr/bin/env python3
"""
Backtest equity_rsi_divergence_mr strategy according to TESTING_PROTOCOL.MD
"""

import sys
from pathlib import Path
import json
from datetime import datetime, timezone
import math

import numpy as np
import pandas as pd
import yfinance as yf

# Add alpha_engine to path
sys.path.append(str(Path(__file__).parent / "alpha_engine"))

from alpha_engine.equity_rsi_divergence_mr import equity_rsi_divergence_mr
from alpha_engine.indicators import rsi, sma, volume_ratio
from alpha_engine.crypto_strategies import (
    _atr_tp_sl,
    _smart_round,
    _get_category,
    _now_iso,
)


def binomial_p(wins: int, n: int, p_null: float = 0.5) -> float:
    """One-tailed binomial test: P(X >= wins) under null hypothesis p=p_null."""
    if n == 0:
        return 1.0
    p_val = 0.0
    for k in range(wins, n + 1):
        p_val += math.comb(n, k) * (p_null**k) * ((1 - p_null) ** (n - k))
    return p_val


def calc_sharpe(pnls: list, annualize: float = 252.0) -> float:
    """Annualized Sharpe ratio from list of per-trade P&L percentages."""
    if len(pnls) < 2:
        return 0.0
    arr = np.array(pnls)
    mean = np.mean(arr)
    std = np.std(arr, ddof=1)
    if std == 0:
        return 0.0
    return float((mean / std) * np.sqrt(annualize))


def fetch_equity_data(symbol: str, period: str = "10y") -> pd.DataFrame:
    """Download equity OHLCV data via yfinance."""
    df = yf.download(
        symbol, period=period, interval="1d", auto_adjust=True, progress=False
    )
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna()
    return df


def simulate_trades(signals: list, data: dict) -> list:
    """Simulate trades from signals."""
    trades = []

    for signal in signals:
        symbol = signal["symbol"]
        if symbol not in data:
            continue

        df = data[symbol]
        entry_date = pd.to_datetime(signal["timestamp"].split("T")[0])

        # Find entry price
        try:
            entry_row = df.loc[df.index >= entry_date].iloc[0]
            entry_price = entry_row["Close"]
        except:
            continue

        # Simulate hold for hold_days
        hold_days = signal.get("hold_days", 7)
        exit_date = entry_date + pd.Timedelta(days=hold_days)

        try:
            exit_row = df.loc[df.index >= exit_date].iloc[0]
            exit_price = exit_row["Close"]
        except:
            # If no exit date, use last available
            exit_price = df.iloc[-1]["Close"]

        # Calculate P&L
        if signal["signal_type"] == "BUY":
            pnl_pct = (exit_price - entry_price) / entry_price * 100
        else:  # SELL
            pnl_pct = (entry_price - exit_price) / entry_price * 100

        trade = {
            "symbol": symbol,
            "direction": signal["signal_type"],
            "entry_date": entry_date.strftime("%Y-%m-%d"),
            "exit_date": exit_date.strftime("%Y-%m-%d")
            if exit_date <= df.index[-1]
            else df.index[-1].strftime("%Y-%m-%d"),
            "entry_price": round(entry_price, 2),
            "exit_price": round(exit_price, 2),
            "pnl_pct": round(pnl_pct, 4),
            "days": hold_days,
            "won": pnl_pct > 0,
            "strategy": signal["strategy"],
        }
        trades.append(trade)

    return trades


def run_backtest(strategy_name: str, symbols: list, period: str = "5y"):
    """Run backtest with IS/OOS/holdout split."""
    print(f"Running backtest for {strategy_name}")

    # Fetch data
    data = {}
    for sym in symbols:
        df = fetch_equity_data(sym, period)
        data[sym] = df
        print(f"Fetched {len(df)} days for {sym}")

    # Generate signals
    signals = equity_rsi_divergence_mr(data)
    print(f"Generated {len(signals)} signals")
    if len(signals) == 0:
        print("Debug: checking strategy logic...")
        # Quick debug for one symbol
        symbol = "SPY"
        df = data.get(symbol)
        if df is not None:
            from alpha_engine.indicators import rsi, volume_ratio
            from alpha_engine.crypto_strategies import _atr_tp_sl

            close = df["Close"]
            rsi_14 = rsi(close, 14)
            current_rsi = float(rsi_14.iloc[-1])
            print(f"SPY: current RSI = {current_rsi}")
            if current_rsi < 30 or current_rsi > 70:
                print(f"SPY: RSI condition met ({current_rsi})")

    # Simulate trades
    trades = simulate_trades(signals, data)

    # Split into IS (70%), OOS validation (15%), holdout (15%)
    n_trades = len(trades)
    is_end = int(0.7 * n_trades)
    oos_end = int(0.85 * n_trades)

    is_trades = trades[:is_end]
    oos_trades = trades[is_end:oos_end]
    holdout_trades = trades[oos_end:]

    results = {
        "strategy": strategy_name,
        "total_signals": len(signals),
        "total_trades": n_trades,
        "period": period,
        "symbols": symbols,
        "in_sample": analyze_trades(is_trades, "In-Sample"),
        "oos_validation": analyze_trades(oos_trades, "OOS Validation"),
        "holdout": analyze_trades(holdout_trades, "Holdout"),
        "monte_carlo": run_monte_carlo(trades),
    }

    return results


def analyze_trades(trades: list, label: str) -> dict:
    """Analyze a set of trades."""
    if not trades:
        return {
            "label": label,
            "n_trades": 0,
            "win_rate": 0,
            "profit_factor": 0,
            "sharpe": 0,
            "avg_pnl": 0,
            "total_return": 0,
            "binomial_p": 1.0,
            "significant": False,
        }

    pnls = [t["pnl_pct"] for t in trades]
    wins = sum(1 for t in trades if t["won"])
    n = len(trades)

    gross_win = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p <= 0))
    profit_factor = gross_win / gross_loss if gross_loss > 0 else float("inf")

    return {
        "label": label,
        "n_trades": n,
        "win_rate": round(wins / n, 4),
        "profit_factor": round(profit_factor, 4),
        "sharpe": round(calc_sharpe(pnls), 4),
        "avg_pnl": round(np.mean(pnls), 4),
        "total_return": round(sum(pnls), 4),
        "binomial_p": round(binomial_p(wins, n), 6),
        "significant": binomial_p(wins, n) < 0.05,
    }


def run_monte_carlo(trades: list, n_sims: int = 1000) -> dict:
    """Run Monte Carlo robustness tests."""
    if len(trades) < 10:
        return {
            "n_simulations": 0,
            "sharpe_mean": 0,
            "sharpe_std": 0,
            "sharpe_robustness": 0,
            "pf_mean": 0,
            "pf_std": 0,
        }

    pnls = np.array([t["pnl_pct"] for t in trades])
    n = len(pnls)

    sharpes = []
    pfs = []

    for _ in range(n_sims):
        # Bootstrap sample with replacement
        sample = np.random.choice(pnls, size=n, replace=True)
        sharpe = calc_sharpe(sample)
        gross_win = sum(p for p in sample if p > 0)
        gross_loss = abs(sum(p for p in sample if p <= 0))
        pf = gross_win / gross_loss if gross_loss > 0 else float("inf")

        sharpes.append(sharpe)
        pfs.append(pf)

    return {
        "n_simulations": n_sims,
        "sharpe_mean": round(np.mean(sharpes), 4),
        "sharpe_std": round(np.std(sharpes), 4),
        "sharpe_robustness": round(
            np.mean(sharpes) / np.std(sharpes) if np.std(sharpes) > 0 else 0, 4
        ),
        "pf_mean": round(np.mean(pfs), 4),
        "pf_std": round(np.std(pfs), 4),
    }


def check_edge_criteria(results: dict) -> dict:
    """Check against edge criteria: WR ≥50%, PF ≥1.2, Sharpe ≥0.7"""
    is_results = results["in_sample"]

    criteria = {
        "win_rate_50": is_results["win_rate"] >= 0.50,
        "profit_factor_1_2": is_results["profit_factor"] >= 1.2,
        "sharpe_0_7": is_results["sharpe"] >= 0.7,
    }

    criteria["all_pass"] = all(criteria.values())

    return criteria


def report_results(results: dict):
    """Print structured backtest results."""
    print("\n" + "=" * 80)
    print(f"BACKTEST REPORT: {results['strategy']}")
    print("=" * 80)
    print(f"Period: {results['period']}")
    print(f"Symbols: {', '.join(results['symbols'])}")
    print(f"Total Signals: {results['total_signals']}")
    print(f"Total Trades: {results['total_trades']}")

    for phase in ["in_sample", "oos_validation", "holdout"]:
        r = results[phase]
        print(f"\n{r['label']} ({r['n_trades']} trades):")
        print(
            f"  Win Rate: {r['win_rate'] * 100:.1f}% (p={r['binomial_p']:.4f}, sig={r['significant']})"
        )
        print(f"  Profit Factor: {r['profit_factor']:.2f}")
        print(f"  Sharpe Ratio: {r['sharpe']:.2f}")
        print(f"  Avg P&L: {r['avg_pnl']:+.2f}%")
        print(f"  Total Return: {r['total_return']:+.1f}%")

    mc = results["monte_carlo"]
    print(f"\nMonte Carlo ({mc['n_simulations']} sims):")
    print(f"  Sharpe Mean: {mc['sharpe_mean']:.2f} ± {mc['sharpe_std']:.2f}")
    print(f"  PF Mean: {mc['pf_mean']:.2f} ± {mc['pf_std']:.2f}")

    criteria = check_edge_criteria(results)
    print("\nEdge Criteria (In-Sample):")
    print(
        f"  WR >= 50%: {'PASS' if criteria['win_rate_50'] else 'FAIL'} ({results['in_sample']['win_rate'] * 100:.1f}%)"
    )
    print(
        f"  PF >= 1.2: {'PASS' if criteria['profit_factor_1_2'] else 'FAIL'} ({results['in_sample']['profit_factor']:.2f})"
    )
    print(
        f"  Sharpe >= 0.7: {'PASS' if criteria['sharpe_0_7'] else 'FAIL'} ({results['in_sample']['sharpe']:.2f})"
    )
    print(f"  Overall: {'PASS' if criteria['all_pass'] else 'FAIL'}")

    # Save results
    output_file = Path("alpha_engine/data/equity_rsi_divergence_backtest.json")
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    symbols = ["SPY", "QQQ", "IWM", "DIA", "VTI"]
    results = run_backtest("equity_rsi_divergence_mr", symbols, "10y")
    report_results(results)
