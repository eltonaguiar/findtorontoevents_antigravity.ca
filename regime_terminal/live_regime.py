"""
Live Regime Scanner — Main entry point for GitHub Actions.

Fetches latest market data, trains HMM on each ticker, classifies current regime,
generates signals, and outputs JSON + dashboard data.

Usage:
    python -m regime_terminal.live_regime [--backtest] [--category crypto]
"""

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timezone


def clean_nan(obj):
    """Recursively replace NaN/Inf floats with None so json.dump produces valid JSON."""
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_nan(v) for v in obj]
    return obj

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from regime_terminal import config
from regime_terminal.hmm_engine import RegimeDetector
from regime_terminal.data_loader import MarketDataLoader
from regime_terminal.backtester import RegimeBacktester


def scan_all_markets(categories=None, run_backtest=False):
    """
    Run the full regime detection pipeline.

    1. Fetch data for all markets
    2. Train HMM per ticker
    3. Classify current regime
    4. Optionally run walk-forward backtest
    5. Output results to JSON
    """
    start_time = time.time()

    print("=" * 70)
    print("  REGIME TERMINAL v1.0.0 — Hidden Markov Model Regime Detection")
    print(f"  Scan started: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  Regimes: {config.HMM_N_REGIMES} | Gaussian distributions | Walk-forward validation")
    print("=" * 70)

    # ── 1. Load Data ────────────────────────────────────────────────────────
    loader = MarketDataLoader()

    if categories:
        market_data = {}
        for cat in categories:
            market_data[cat] = loader.fetch_category(cat)
    else:
        market_data = loader.fetch_all()

    # ── 2. Run HMM on Each Ticker ──────────────────────────────────────────
    regime_results = {}
    market_overview = {
        "bull_count": 0,
        "bear_count": 0,
        "neutral_count": 0,
        "total_scanned": 0,
    }

    for category, tickers in market_data.items():
        regime_results[category] = {}
        cat_label = config.MARKETS[category]["label"]
        print(f"\n{'─'*60}")
        print(f"  REGIME DETECTION: {cat_label}")
        print(f"{'─'*60}")

        for ticker, df in tickers.items():
            try:
                # Train HMM
                detector = RegimeDetector()
                detector.fit(df)

                # Get current regime
                current = detector.current_regime(df)
                if current is None:
                    continue

                # Get technical confirmations
                confirmations = detector.get_confirmations(df)

                # Get regime history summary
                history = detector.regime_history(df)

                # Market summary
                summary = loader.get_market_summary(df)

                # Combine results
                result = {
                    "ticker": ticker,
                    "category": category,
                    "price": summary.get("current_price", 0),
                    "regime": current["regime"],
                    "confidence": current["confidence"],
                    "signal": current["signal"],
                    "signal_reason": current["signal_reason"],
                    "leverage": current["leverage"],
                    "regime_stable": current["regime_stable"],
                    "most_likely_next": current["most_likely_next"],
                    "confirmations": confirmations["count"],
                    "confirmations_met": confirmations["met_threshold"],
                    "confirmation_details": confirmations["details"],
                    "rsi": confirmations["rsi_value"],
                    "transition_probs": current["transition_probs"],
                    "all_probabilities": current["all_probabilities"],
                    "regime_stats": current["regime_stats"],
                    "training_points": current["training_points"],
                    "returns": {
                        "1d": summary.get("return_1d"),
                        "7d": summary.get("return_7d"),
                        "30d": summary.get("return_30d"),
                        "90d": summary.get("return_90d"),
                    },
                    "volatility_30d": summary.get("volatility_30d"),
                    "history": {
                        "distribution": history.get("distribution", {}),
                        "avg_duration": history.get("avg_regime_duration", {}),
                    },
                }

                regime_results[category][ticker] = result
                market_overview["total_scanned"] += 1

                # Classify for overview
                if current["regime"] in ["Strong Bull", "Mild Bull"]:
                    market_overview["bull_count"] += 1
                elif current["regime"] in ["Strong Bear", "Mild Bear", "Crash"]:
                    market_overview["bear_count"] += 1
                else:
                    market_overview["neutral_count"] += 1

                # Color code output
                regime = current["regime"]
                conf = current["confidence"]
                signal = current["signal"]
                confirms = confirmations["count"]

                regime_icon = {
                    "Strong Bull": "▲▲", "Mild Bull": "▲ ",
                    "Accumulation": "◆ ", "Chop/Neutral": "── ",
                    "Mild Bear": "▼ ", "Strong Bear": "▼▼", "Crash": "☠ ",
                }.get(regime, "? ")

                print(f"  {regime_icon} {ticker:15s} | {regime:15s} | "
                      f"Conf: {conf:.0%} | Signal: {signal:5s} | "
                      f"Confirms: {confirms}/8 | ${summary.get('current_price', 0):,.2f}")

            except Exception as e:
                print(f"  ✗  {ticker:15s} | ERROR: {e}")
                continue

    # ── 3. Generate Actionable Signals ──────────────────────────────────────
    signals = []
    for category, tickers in regime_results.items():
        for ticker, result in tickers.items():
            if result["signal"] in ["LONG", "SHORT"] and result["confirmations_met"]:
                signals.append({
                    "ticker": result["ticker"],
                    "category": result["category"],
                    "signal": result["signal"],
                    "regime": result["regime"],
                    "confidence": result["confidence"],
                    "leverage": result["leverage"],
                    "confirmations": result["confirmations"],
                    "price": result["price"],
                    "rsi": result["rsi"],
                })

    # Sort by confidence
    signals.sort(key=lambda x: x["confidence"], reverse=True)

    # ── 4. Optional Backtest ────────────────────────────────────────────────
    backtest_results = None
    if run_backtest:
        print(f"\n{'='*70}")
        print("  WALK-FORWARD BACKTEST (out-of-sample validation)")
        print(f"  Train: {config.TRAIN_WINDOW_DAYS}d | Test: {config.TEST_WINDOW_DAYS}d | "
              f"Costs: {config.TRANSACTION_COST_BPS}bps + {config.SLIPPAGE_BPS}bps slippage")
        print(f"{'='*70}")

        backtester = RegimeBacktester()
        backtest_results = backtester.run_all_markets(market_data)

    # ── 5. Build Output ─────────────────────────────────────────────────────
    elapsed = round(time.time() - start_time, 1)

    output = {
        "version": "1.0.0",
        "engine": "Gaussian HMM (hmmlearn)",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "elapsed_seconds": elapsed,
        "config": {
            "n_regimes": config.HMM_N_REGIMES,
            "covariance_type": config.HMM_COVARIANCE_TYPE,
            "lookback_days": config.LOOKBACK_DAYS,
            "interval": config.DATA_INTERVAL,
            "min_confirmations": config.MIN_CONFIRMATIONS,
            "hysteresis_bars": config.MIN_REGIME_BARS,
        },
        "market_overview": market_overview,
        "signals": signals,
        "regimes": regime_results,
    }

    if backtest_results:
        output["backtest"] = backtest_results

    # ── 6. Write Output Files ───────────────────────────────────────────────
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(data_dir, exist_ok=True)

    # Main regime state
    regime_path = os.path.join(data_dir, "regime_state.json")
    with open(regime_path, "w") as f:
        json.dump(clean_nan(output), f, indent=2, default=str)
    print(f"\n  → Regime state saved to {regime_path}")

    # Active signals (lightweight file for other systems to consume)
    signals_path = os.path.join(data_dir, "active_signals.json")
    signals_output = {
        "generated_at": output["generated_at"],
        "signals": signals,
        "market_overview": market_overview,
    }
    with open(signals_path, "w") as f:
        json.dump(clean_nan(signals_output), f, indent=2)
    print(f"  → Active signals saved to {signals_path}")

    # Backtest results
    if backtest_results:
        bt_path = os.path.join(data_dir, "backtest_results.json")
        with open(bt_path, "w") as f:
            json.dump(clean_nan(backtest_results), f, indent=2, default=str)
        print(f"  → Backtest results saved to {bt_path}")

    # ── 7. Print Summary ────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  REGIME TERMINAL SCAN COMPLETE")
    print(f"{'='*70}")
    print(f"  Markets scanned:  {market_overview['total_scanned']}")
    print(f"  Bullish regimes:  {market_overview['bull_count']}")
    print(f"  Bearish regimes:  {market_overview['bear_count']}")
    print(f"  Neutral regimes:  {market_overview['neutral_count']}")
    print(f"  Active signals:   {len(signals)}")
    print(f"  Elapsed:          {elapsed}s")

    if signals:
        print(f"\n  TOP SIGNALS:")
        for s in signals[:5]:
            print(f"    {s['signal']:5s} {s['ticker']:12s} | "
                  f"{s['regime']:15s} | Conf: {s['confidence']:.0%} | "
                  f"Leverage: {s['leverage']}x | {s['confirmations']}/8 confirms")

    if backtest_results:
        sm = backtest_results.get("summary", {})
        print(f"\n  BACKTEST SUMMARY:")
        print(f"    Tickers tested:    {sm.get('total_tickers', 0)}")
        print(f"    Profitable:        {sm.get('profitable', 0)}")
        print(f"    Alpha-positive:    {sm.get('alpha_positive', 0)}")
        print(f"    Avg Sharpe:        {sm.get('avg_sharpe', 0):.3f}")
        print(f"    Avg Alpha:         {sm.get('avg_alpha', 0):+.2f}%")
        print(f"    Best:              {sm.get('best_ticker', 'N/A')} ({sm.get('best_alpha', 0):+.2f}%)")
        print(f"    Worst:             {sm.get('worst_ticker', 'N/A')} ({sm.get('worst_alpha', 0):+.2f}%)")

    print(f"\n{'='*70}\n")

    return output


def main():
    parser = argparse.ArgumentParser(description="Regime Terminal — HMM Market Regime Detection")
    parser.add_argument("--backtest", action="store_true", help="Run walk-forward backtest")
    parser.add_argument("--category", nargs="+", choices=list(config.MARKETS.keys()),
                        help="Only scan specific categories")
    args = parser.parse_args()

    return scan_all_markets(
        categories=args.category,
        run_backtest=args.backtest,
    )


if __name__ == "__main__":
    main()
