"""
Run Tier 1 Strategy Backtests
==============================
Pulls real market data from Yahoo Finance and Kraken, then runs
all 5 forward-test-validated strategies through the backtest engine.

Usage:
    python run_tier1_backtest.py                  # full run, all strategies
    python run_tier1_backtest.py --strategy bab   # single strategy
    python run_tier1_backtest.py --quick           # shorter data window

Requirements:
    pip install yfinance pandas numpy
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

# Ensure local imports work
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np

from backtest_framework import (
    BacktestEngine,
    BacktestConfig,
    DataLoader,
    BacktestResult,
)
from strategies_tier1 import (
    FundingRateArbitrage,
    PairsTrading,
    BettingAgainstBeta,
    FlashCrashReversal,
    QualityMinusJunk,
    TIER1_STRATEGIES,
)


# -------------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------------

DEFAULT_CONFIG = BacktestConfig(
    initial_capital=100_000.0,
    commission_rate=0.001,      # 0.1% per trade
    slippage=0.0005,            # 0.05% slippage
    max_position_pct=0.95,      # leave 5% cash buffer
    allow_short=False,
    position_sizing="percent_risk",
    risk_per_trade=0.02,        # 2% risk per trade (Kelly/4)
    stop_loss_pct=0.05,         # 5% stop loss
)

CRYPTO_CONFIG = BacktestConfig(
    initial_capital=100_000.0,
    commission_rate=0.002,      # 0.2% (typical crypto exchange)
    slippage=0.001,             # 0.1% (wider spreads)
    max_position_pct=0.90,
    allow_short=False,
    position_sizing="percent_risk",
    risk_per_trade=0.02,
    stop_loss_pct=0.07,         # wider stop for crypto vol
)


# -------------------------------------------------------------------------
# Data helpers
# -------------------------------------------------------------------------

def load_equity_data(
    symbol: str = "SPY",
    start: str = "2020-01-01",
    end: str = "2026-02-15",
) -> pd.DataFrame:
    """Load equity OHLCV from Yahoo Finance."""
    print(f"  Loading {symbol} from Yahoo Finance ({start} to {end})...")
    try:
        data = DataLoader.from_yahoo(symbol, start, end)
        print(f"  -> {len(data)} bars loaded.")
        return data
    except Exception as e:
        print(f"  [WARN] Yahoo Finance failed for {symbol}: {e}")
        print("  -> Generating synthetic proxy data instead.")
        return _synthetic_equity(symbol, start, end)


def load_crypto_data(
    symbol: str = "BTC-USD",
    start: str = "2020-01-01",
    end: str = "2026-02-15",
) -> pd.DataFrame:
    """Load crypto OHLCV. Tries Yahoo first, Kraken as fallback."""
    print(f"  Loading {symbol} from Yahoo Finance ({start} to {end})...")
    try:
        data = DataLoader.from_yahoo(symbol, start, end)
        print(f"  -> {len(data)} bars loaded.")
        return data
    except Exception:
        print(f"  [WARN] Yahoo failed for {symbol}. Trying Kraken...")
        try:
            kraken_pair = symbol.replace("-", "").replace("USD", "USD")
            data = DataLoader.from_kraken(kraken_pair, start, end, interval=1440)
            print(f"  -> {len(data)} bars loaded from Kraken.")
            return data
        except Exception as e2:
            print(f"  [WARN] Kraken also failed: {e2}")
            print("  -> Generating synthetic crypto proxy data.")
            return _synthetic_crypto(symbol, start, end)


def _synthetic_equity(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Generate realistic synthetic equity data when APIs are unavailable."""
    dates = pd.bdate_range(start=start, end=end)
    np.random.seed(42)
    daily_ret = np.random.normal(0.0004, 0.012, len(dates))
    prices = 300 * np.exp(np.cumsum(daily_ret))
    return pd.DataFrame(
        {
            "open": prices * (1 + np.random.normal(0, 0.002, len(dates))),
            "high": prices * (1 + np.abs(np.random.normal(0, 0.008, len(dates)))),
            "low": prices * (1 - np.abs(np.random.normal(0, 0.008, len(dates)))),
            "close": prices,
            "volume": np.random.randint(50_000_000, 200_000_000, len(dates)),
            "symbol": symbol,
        },
        index=dates,
    )


def _synthetic_crypto(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Generate realistic synthetic crypto data when APIs are unavailable."""
    dates = pd.date_range(start=start, end=end, freq="D")
    np.random.seed(99)
    daily_ret = np.random.normal(0.001, 0.035, len(dates))
    prices = 30000 * np.exp(np.cumsum(daily_ret))
    return pd.DataFrame(
        {
            "open": prices * (1 + np.random.normal(0, 0.005, len(dates))),
            "high": prices * (1 + np.abs(np.random.normal(0, 0.02, len(dates)))),
            "low": prices * (1 - np.abs(np.random.normal(0, 0.02, len(dates)))),
            "close": prices,
            "volume": np.random.randint(10_000, 500_000, len(dates)).astype(float),
            "symbol": symbol,
        },
        index=dates,
    )


# -------------------------------------------------------------------------
# Run individual strategies
# -------------------------------------------------------------------------

def run_funding_rate(crypto_data: pd.DataFrame) -> BacktestResult:
    """Run Funding Rate Arbitrage on crypto data."""
    strategy = FundingRateArbitrage(
        vwma_period=20,
        zscore_lookback=60,
        entry_z=2.0,
        exit_z=0.5,
    )
    engine = BacktestEngine(CRYPTO_CONFIG)
    engine.set_data(crypto_data)
    engine.set_strategy(strategy)
    return engine.run()


def run_pairs_trading(
    equity_data_1: pd.DataFrame,
    equity_data_2: pd.DataFrame,
) -> BacktestResult:
    """Run Pairs Trading on two correlated equities."""
    # Align the two series on common dates
    common_idx = equity_data_1.index.intersection(equity_data_2.index)
    if len(common_idx) < 200:
        print("  [WARN] Fewer than 200 common dates for pairs trading.")

    data = equity_data_1.loc[common_idx].copy()
    data["pair_close"] = equity_data_2.loc[common_idx, "close"].values

    strategy = PairsTrading(lookback=60, entry_z=2.0, exit_z=0.5)
    engine = BacktestEngine(DEFAULT_CONFIG)
    engine.set_data(data)
    engine.set_strategy(strategy)
    return engine.run()


def run_bab(equity_data: pd.DataFrame, bench_data: pd.DataFrame = None) -> BacktestResult:
    """Run Betting Against Beta."""
    data = equity_data.copy()
    if bench_data is not None:
        common_idx = data.index.intersection(bench_data.index)
        data = data.loc[common_idx]
        data["benchmark_close"] = bench_data.loc[common_idx, "close"].values

    strategy = BettingAgainstBeta(
        beta_lookback=120,
        low_beta=0.8,
        high_beta=1.2,
        trend_filter_period=200,
    )
    engine = BacktestEngine(DEFAULT_CONFIG)
    engine.set_data(data)
    engine.set_strategy(strategy)
    return engine.run()


def run_flash_crash(crypto_data: pd.DataFrame) -> BacktestResult:
    """Run Flash Crash Reversal on crypto (high vol = more crashes)."""
    strategy = FlashCrashReversal(
        crash_threshold=0.05,
        rsi_period=6,
        rsi_oversold=25.0,
        volume_spike_mult=2.0,
        recovery_pct=0.5,
        max_hold_bars=10,
        lookback_high=20,
    )
    engine = BacktestEngine(CRYPTO_CONFIG)
    engine.set_data(crypto_data)
    engine.set_strategy(strategy)
    return engine.run()


def run_qmj(equity_data: pd.DataFrame) -> BacktestResult:
    """Run Quality Minus Junk on equity data."""
    strategy = QualityMinusJunk(
        vol_lookback=20,
        quality_lookback=60,
        trend_period=200,
        entry_z=0.5,
        exit_z=-0.5,
    )
    engine = BacktestEngine(DEFAULT_CONFIG)
    engine.set_data(equity_data)
    engine.set_strategy(strategy)
    return engine.run()


# -------------------------------------------------------------------------
# Main
# -------------------------------------------------------------------------

def print_result(name: str, result: BacktestResult):
    """Pretty-print a single backtest result."""
    print(f"\n{'=' * 60}")
    print(f"  {name}")
    print(f"{'=' * 60}")
    print(f"  Total Return:       {result.total_return:>10.2%}")
    print(f"  Annualized Return:  {result.annualized_return:>10.2%}")
    print(f"  Sharpe Ratio:       {result.sharpe_ratio:>10.2f}")
    print(f"  Sortino Ratio:      {result.sortino_ratio:>10.2f}")
    print(f"  Max Drawdown:       {result.max_drawdown:>10.2%}")
    print(f"  Calmar Ratio:       {result.calmar_ratio:>10.2f}")
    print(f"  Win Rate:           {result.win_rate:>10.2%}")
    print(f"  Profit Factor:      {result.profit_factor:>10.2f}")
    print(f"  Trades:             {result.num_trades:>10d}")
    print(f"  Avg Trade Return:   {result.avg_trade_return:>10.2%}")
    if result.avg_win:
        print(f"  Avg Win:            {result.avg_win:>10.2%}")
    if result.avg_loss:
        print(f"  Avg Loss:           {result.avg_loss:>10.2%}")
    print(f"  Volatility:         {result.volatility:>10.2%}")


def main():
    parser = argparse.ArgumentParser(description="Run Tier 1 strategy backtests")
    parser.add_argument(
        "--strategy",
        choices=list(TIER1_STRATEGIES.keys()) + ["all"],
        default="all",
        help="Which strategy to run (default: all)",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Use shorter data window (2023-present) for faster results",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to save JSON results (default: ./backtest_results/)",
    )
    args = parser.parse_args()

    start_date = "2023-01-01" if args.quick else "2020-01-01"
    end_date = "2026-02-15"
    output_dir = Path(args.output) if args.output else Path(__file__).parent / "backtest_results"

    print("=" * 60)
    print("  TIER 1 STRATEGY BACKTESTS")
    print(f"  Period: {start_date} to {end_date}")
    print(f"  Capital: $100,000")
    print("=" * 60)

    results = {}
    run_all = args.strategy == "all"

    # ---- Load data (shared across strategies) ----
    print("\n[1/6] Loading market data...\n")

    spy_data = None
    btc_data = None
    qqq_data = None

    if run_all or args.strategy in ("bab", "qmj", "pairs_trading"):
        spy_data = load_equity_data("SPY", start_date, end_date)

    if run_all or args.strategy in ("funding_rate_arb", "flash_crash"):
        btc_data = load_crypto_data("BTC-USD", start_date, end_date)

    if run_all or args.strategy == "pairs_trading":
        qqq_data = load_equity_data("QQQ", start_date, end_date)

    # ---- Run strategies ----

    if run_all or args.strategy == "funding_rate_arb":
        print("\n[2/6] Running Funding Rate Arbitrage (BTC-USD)...")
        result = run_funding_rate(btc_data)
        print_result("Funding Rate Arbitrage (BTC-USD)", result)
        results["funding_rate_arb"] = result

    if run_all or args.strategy == "pairs_trading":
        print("\n[3/6] Running Pairs Trading (SPY / QQQ)...")
        result = run_pairs_trading(spy_data, qqq_data)
        print_result("Pairs Trading (SPY / QQQ)", result)
        results["pairs_trading"] = result

    if run_all or args.strategy == "bab":
        print("\n[4/6] Running Betting Against Beta (SPY)...")
        result = run_bab(spy_data)
        print_result("Betting Against Beta (SPY)", result)
        results["bab"] = result

    if run_all or args.strategy == "flash_crash":
        print("\n[5/6] Running Flash Crash Reversal (BTC-USD)...")
        result = run_flash_crash(btc_data)
        print_result("Flash Crash Reversal (BTC-USD)", result)
        results["flash_crash"] = result

    if run_all or args.strategy == "qmj":
        print("\n[6/6] Running Quality Minus Junk (SPY)...")
        result = run_qmj(spy_data)
        print_result("Quality Minus Junk (SPY)", result)
        results["qmj"] = result

    # ---- Summary ----
    if len(results) > 1:
        print("\n" + "=" * 60)
        print("  SUMMARY: ALL TIER 1 STRATEGIES")
        print("=" * 60)
        print(f"  {'Strategy':<35} {'Return':>8} {'Sharpe':>8} {'MaxDD':>8} {'Trades':>7}")
        print(f"  {'-'*35} {'-'*8} {'-'*8} {'-'*8} {'-'*7}")
        for name, res in results.items():
            label = name.replace("_", " ").title()
            print(
                f"  {label:<35} "
                f"{res.total_return:>7.1%} "
                f"{res.sharpe_ratio:>8.2f} "
                f"{res.max_drawdown:>7.1%} "
                f"{res.num_trades:>7d}"
            )

    # ---- Save results ----
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {}
    for name, res in results.items():
        res_dict = res.to_dict()
        summary[name] = res_dict
        result_path = output_dir / f"{name}.json"
        with open(result_path, "w") as f:
            json.dump(res_dict, f, indent=2, default=str)

    summary_path = output_dir / "tier1_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"\n  Results saved to: {output_dir}/")
    print(f"  Summary: {summary_path}")
    print("\nDone.")


if __name__ == "__main__":
    main()
