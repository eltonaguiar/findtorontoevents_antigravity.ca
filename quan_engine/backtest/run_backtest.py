"""
QuanEngine Backtest Runner CLI
================================
Usage:
  python -m quan_engine.backtest.run_backtest --symbols BTCUSDT,ETHUSDT --mode SWING
  python -m quan_engine.backtest.run_backtest --all
"""
import os
import sys
import json
import logging
import argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from quan_engine import config
from quan_engine.backtest.walk_forward import (
    fetch_ohlcv, run_walk_forward, save_results, compute_atr
)
from quan_engine.backtest.anti_overfit import check_all
from quan_engine.regime_router import RegimeRouter
from quan_engine.strategy_pool import StrategyPool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("QuanEngine.BacktestRunner")


def make_strategy_func(pool: StrategyPool, router: RegimeRouter, pool_type: str):
    """Create a callable that generates signals from a strategy pool on a DataFrame slice."""

    def strategy_func(df_slice, symbol):
        """Run pool strategies on a DataFrame slice, returning signal dicts."""
        if len(df_slice) < 100:
            return []

        # Check regime
        close = df_slice["close"].values
        regime = router.classify(close)

        # Only run if regime matches pool
        if pool_type == "TRENDING" and regime != "TRENDING":
            return []
        if pool_type == "MEAN_REVERSION" and regime != "MEAN_REVERSION":
            return []

        votes = pool.get_votes(df_slice, symbol)

        # Count consensus
        active_votes = [v for v in votes if v["direction"] != "ABSTAIN"]
        if not active_votes:
            return []

        from collections import Counter
        dir_counts = Counter(v["direction"] for v in active_votes)
        majority_dir, majority_count = dir_counts.most_common(1)[0]
        consensus_pct = majority_count / len(active_votes)

        if consensus_pct < config.CONSENSUS_THRESHOLD:
            return []

        avg_conf = sum(v["confidence"] for v in active_votes if v["direction"] == majority_dir) / majority_count
        if avg_conf < config.MIN_AVG_CONFIDENCE:
            return []

        # Find best vote for TP/SL
        best_vote = max(
            [v for v in active_votes if v["direction"] == majority_dir],
            key=lambda v: v.get("confidence", 0)
        )

        entry_price = best_vote.get("entry_price") or float(close[-1])
        tp = best_vote.get("take_profit") or entry_price * (1.03 if majority_dir == "BUY" else 0.97)
        sl = best_vote.get("stop_loss") or entry_price * (0.98 if majority_dir == "BUY" else 1.02)

        return [{
            "symbol": symbol,
            "direction": majority_dir,
            "entry_price": entry_price,
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": avg_conf,
            "consensus_pct": consensus_pct,
            "entry_idx": len(df_slice) - 1,
        }]

    return strategy_func


def run_backtest(symbols: list, mode: str = "SWING", start_date: str = "2023-01-01",
                 end_date: str = "2026-03-01"):
    """Run walk-forward backtest for all strategy pools on given symbols."""
    router = RegimeRouter()

    pools = {
        "TRENDING": StrategyPool("TRENDING"),
        "MEAN_REVERSION": StrategyPool("MEAN_REVERSION"),
    }

    all_results = {}
    overall_pass = True

    for pool_type, pool in pools.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"BACKTESTING {pool_type} POOL")
        logger.info(f"Available: {pool.available_strategies()}")
        logger.info(f"Missing: {pool.missing_strategies()}")
        logger.info(f"{'='*60}")

        strategy_func = make_strategy_func(pool, router, pool_type)

        for symbol in symbols:
            logger.info(f"\n--- {pool_type} / {symbol} ---")

            # Fetch data
            df = fetch_ohlcv(symbol, "1h", start_date, end_date)
            if df.empty:
                logger.warning(f"No data for {symbol}")
                continue

            logger.info(f"Data: {len(df)} bars from {df.index[0]} to {df.index[-1]}")

            # Run walk-forward
            windows = run_walk_forward(
                strategy_func=strategy_func,
                df=df,
                symbol=symbol,
                strategy_name=f"{pool_type}_{symbol}",
                mode=mode,
            )

            if not windows:
                logger.warning(f"No windows generated for {pool_type}/{symbol}")
                continue

            # Save results
            save_results(windows, f"{pool_type}", symbol)

            # Run anti-overfit checks
            passed, details = check_all(windows, f"{pool_type}_{symbol}")

            key = f"{pool_type}_{symbol}"
            all_results[key] = {
                "pool": pool_type,
                "symbol": symbol,
                "windows": len(windows),
                "passed": passed,
                "checks": details,
                "summary": {
                    "avg_oos_wr": sum(w.oos_win_rate for w in windows) / len(windows),
                    "avg_oos_sharpe": sum(w.oos_sharpe for w in windows) / len(windows),
                    "avg_oos_pf": sum(w.oos_profit_factor for w in windows) / len(windows),
                    "max_oos_dd": max(w.oos_max_drawdown for w in windows),
                    "profitable_windows": sum(1 for w in windows if w.oos_profitable),
                    "total_windows": len(windows),
                },
            }

            status = "PASS" if passed else "FAIL"
            logger.info(f"{key}: {status}")
            logger.info(f"  Avg OOS WR: {all_results[key]['summary']['avg_oos_wr']:.1%}")
            logger.info(f"  Avg OOS Sharpe: {all_results[key]['summary']['avg_oos_sharpe']:.2f}")
            logger.info(f"  Avg OOS PF: {all_results[key]['summary']['avg_oos_pf']:.2f}")
            logger.info(f"  Max OOS DD: {all_results[key]['summary']['max_oos_dd']:.1f}%")

            if not passed:
                overall_pass = False
                for check_name, check_result in details.items():
                    if not check_result["passed"]:
                        logger.warning(f"  FAILED: {check_name} — {check_result['detail']}")

    # Save overall results
    output_dir = os.path.join(config.DATA_DIR, "backtest_results")
    os.makedirs(output_dir, exist_ok=True)
    summary_path = os.path.join(output_dir, "backtest_summary.json")

    with open(summary_path, "w") as f:
        json.dump({
            "generated_at": datetime.utcnow().isoformat(),
            "mode": mode,
            "symbols": symbols,
            "overall_pass": overall_pass,
            "results": all_results,
        }, f, indent=2, default=str)

    logger.info(f"\n{'='*60}")
    logger.info(f"OVERALL: {'PASS' if overall_pass else 'FAIL'}")
    logger.info(f"Results saved to {summary_path}")
    logger.info(f"{'='*60}")

    return overall_pass, all_results


def main():
    parser = argparse.ArgumentParser(description="QuanEngine Walk-Forward Backtest")
    parser.add_argument("--symbols", type=str, default=None,
                        help="Comma-separated symbols (e.g., BTCUSDT,ETHUSDT)")
    parser.add_argument("--all", action="store_true",
                        help="Run all configured symbols")
    parser.add_argument("--mode", type=str, default="SWING",
                        choices=["SCALP", "SWING", "POSITION"])
    parser.add_argument("--start", type=str, default="2023-01-01")
    parser.add_argument("--end", type=str, default="2026-03-01")

    args = parser.parse_args()

    if args.all:
        symbols = config.SYMBOLS
    elif args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",")]
    else:
        symbols = config.SYMBOLS[:5]  # Default top 5

    run_backtest(symbols, args.mode, args.start, args.end)


if __name__ == "__main__":
    main()
