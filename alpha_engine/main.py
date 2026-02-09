"""
Alpha Engine - Main Runner

The master orchestrator that runs the full research pipeline:
Phase 1: Data loading + feature computation
Phase 2: Strategy signal generation
Phase 3: Ensemble / Meta-Learner picks
Phase 4: Backtesting + validation
Phase 5: Report generation

Usage:
    python -m alpha_engine.main --mode picks        # Generate today's picks
    python -m alpha_engine.main --mode backtest      # Run full backtest
    python -m alpha_engine.main --mode validate      # Walk-forward validation
    python -m alpha_engine.main --mode full          # Everything
    python -m alpha_engine.main --mode quick         # Quick picks (fewer tickers)
"""
import argparse
import logging
import sys
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("alpha_engine")


def run_picks(universe_size: str = "default", top_k: int = 20):
    """
    Generate today's picks using the full pipeline.
    
    This is the main daily/weekly workflow.
    """
    from .data import PriceLoader, FundamentalsLoader, MacroLoader, SentimentLoader, InsiderLoader, EarningsLoader, UniverseManager
    from .features import FeatureFactory
    from .strategies import StrategyGenerator
    from .ensemble import MetaLearner
    from .reporting import ReportGenerator, PickListGenerator
    from . import config

    print("=" * 70)
    print("  ALPHA ENGINE v1.0 - Multi-Strategy Quantitative Research Platform")
    print("=" * 70)
    print()

    # ── Phase 1: Data Loading ─────────────────────────────────────────────
    print("Phase 1: Loading data...")
    universe_mgr = UniverseManager()
    tickers = universe_mgr.get_universe(source=universe_size)
    print(f"  Universe: {len(tickers)} tickers")

    price_loader = PriceLoader()
    prices_data = price_loader.load(tickers, start=config.BACKTEST_START)
    close_prices = price_loader.get_close_prices(tickers, start=config.BACKTEST_START)
    volume = price_loader.get_volume(tickers, start=config.BACKTEST_START)

    # Get OHLCV panel
    panel = price_loader.get_ohlcv_panel(tickers, start=config.BACKTEST_START)
    high = panel.get("High", None)
    low = panel.get("Low", None)

    print(f"  Price data: {close_prices.shape[0]} days x {close_prices.shape[1]} tickers")

    # Apply liquidity filter
    dollar_volume = price_loader.get_dollar_volume(tickers, start=config.BACKTEST_START)
    liquid_tickers = universe_mgr.apply_liquidity_filter(tickers, dollar_volume)
    print(f"  After liquidity filter: {len(liquid_tickers)} tickers")

    # Macro data
    print("  Loading macro data...")
    macro_loader = MacroLoader()
    macro_df = macro_loader.load(start=config.BACKTEST_START)
    regimes = macro_loader.compute_regimes(macro_df)
    current_regime = macro_loader.get_current_regime()
    print(f"  Current regime: {current_regime.get('composite_regime', 'unknown')}")

    # Fundamentals
    print("  Loading fundamentals...")
    fund_loader = FundamentalsLoader()
    fundamentals = fund_loader.get_key_ratios(liquid_tickers[:50])  # Limit for speed
    print(f"  Fundamentals loaded for {len(fundamentals)} tickers")

    # Earnings
    print("  Loading earnings data...")
    earn_loader = EarningsLoader()
    earnings_beats = earn_loader.detect_consecutive_beats(liquid_tickers[:50])
    pead_signals = earn_loader.compute_pead_signal(liquid_tickers[:50], close_prices)
    revision_momentum = earn_loader.compute_revision_momentum(liquid_tickers[:50])
    safe_bets = earnings_beats[earnings_beats["is_safe_bet"] == True]
    print(f"  Safe Bet candidates: {len(safe_bets)} tickers")

    # Insider data
    print("  Loading insider data...")
    insider_loader = InsiderLoader()
    insider_clusters = insider_loader.detect_cluster_buys(liquid_tickers[:30])
    cluster_buys = insider_clusters[insider_clusters["is_cluster_buy"] == True]
    print(f"  Insider cluster buys: {len(cluster_buys)} tickers")

    # Sentiment
    print("  Computing sentiment...")
    sent_loader = SentimentLoader()
    sentiment_proxy = sent_loader.compute_sentiment_from_price_volume(close_prices, volume)

    # ── Phase 2: Feature Computation ──────────────────────────────────────
    print("\nPhase 2: Computing features...")
    feature_factory = FeatureFactory()

    earnings_data = {
        "beats": earnings_beats,
        "pead": pead_signals,
        "revision": revision_momentum,
    }

    # Use stacked momentum features for efficiency
    from .features.momentum import compute_momentum_features_stacked
    mom_features = compute_momentum_features_stacked(close_prices)
    print(f"  Momentum features: {mom_features.shape}")

    # ── Phase 3: Strategy Signal Generation ───────────────────────────────
    print("\nPhase 3: Generating strategy signals...")
    generator = StrategyGenerator()
    all_strategies = generator.get_all()
    print(f"  Registered strategies: {len(all_strategies)}")

    latest_date = close_prices.index[-1]
    strategy_signals = {}

    for name, strategy in all_strategies.items():
        try:
            signals = strategy.generate_signals(mom_features, latest_date, liquid_tickers)
            if signals:
                signals_df = pd.DataFrame([{
                    "ticker": s.ticker, "score": s.score, "direction": s.direction,
                    "confidence": s.confidence, "holding_period": s.holding_period,
                    "category": s.category, "strategy": name,
                    "date": latest_date,
                } for s in signals])
                strategy_signals[name] = signals_df
                print(f"    {name}: {len(signals)} signals")
        except Exception as e:
            logger.debug(f"Strategy {name} failed: {e}")

    # ── Phase 4: Meta-Learner Ensemble ────────────────────────────────────
    print("\nPhase 4: Running Meta-Learner ensemble...")
    meta = MetaLearner()
    picks = meta.generate_picks(
        strategy_signals=strategy_signals,
        macro_data=current_regime,
        insider_data=insider_clusters,
        sentiment_data=None,  # Would use real sentiment if available
        earnings_data=earnings_beats,
        top_k=top_k,
    )

    watchlist = meta.generate_watchlist(picks, top_k=10)
    upcoming_earnings = earn_loader.get_upcoming_earnings(liquid_tickers[:50])
    avoid_list = meta.generate_avoid_list(picks, upcoming_earnings)

    # ── Phase 5: Report Generation ────────────────────────────────────────
    print("\nPhase 5: Generating reports...")

    # Get current prices for pick list
    latest_prices = close_prices.iloc[-1].to_dict()

    # Strategy weights from regime allocator
    regime_scores = meta.regime_allocator.classify_regime(current_regime)
    strategy_weights = meta.regime_allocator.compute_blended_weights(regime_scores)

    # Generate reports
    report_gen = ReportGenerator()
    report = report_gen.generate_daily_report(
        picks=picks,
        watchlist=watchlist,
        avoid_list=avoid_list,
        regime_info=current_regime,
        strategy_weights=strategy_weights,
    )

    # Generate actionable pick list
    pick_gen = PickListGenerator()
    pick_list = pick_gen.generate(picks, latest_prices, regime=current_regime.get("composite_regime", "neutral"))
    pick_text = pick_gen.format_as_text(pick_list)

    # Print results
    print("\n" + pick_text)
    print(f"\n  Report saved to: {report_gen.output_dir}")

    # Save picks as JSON for PHP API
    if not pick_list.empty:
        json_path = Path(config.OUTPUT_DIR) / "latest_picks.json"
        pick_list.to_json(json_path, orient="records", indent=2)
        print(f"  Picks JSON saved to: {json_path}")

    print("\n  Meta-Learner Allocation:")
    print(meta.get_allocation_report())

    return picks, pick_list, report


def run_backtest(strategy_name: str = None):
    """Run backtest for one or all strategies."""
    from .data import PriceLoader, UniverseManager
    from .backtest import BacktestEngine, CostModel
    from .reporting import ReportGenerator
    from . import config

    print("Running backtest...")

    universe_mgr = UniverseManager()
    tickers = universe_mgr.get_universe()

    price_loader = PriceLoader()
    close = price_loader.get_close_prices(tickers, start=config.BACKTEST_START)
    benchmark = close.get("SPY", pd.Series(dtype=float))

    engine = BacktestEngine(
        initial_capital=100000,
        cost_model=CostModel.interactive_brokers(),
    )

    # TODO: Generate signals for historical dates and run backtest
    print("  Backtest engine ready. Use run_picks() to generate signals first.")


def run_validate():
    """Run walk-forward validation."""
    from .validation import WalkForwardValidator, MonteCarloSimulator, StressTester
    print("Validation engine ready.")
    print("  Use after generating backtest results to validate strategies.")


def main():
    parser = argparse.ArgumentParser(description="Alpha Engine - Quant Research Platform")
    parser.add_argument("--mode", choices=["picks", "backtest", "validate", "full", "quick"],
                       default="picks", help="Execution mode")
    parser.add_argument("--top-k", type=int, default=20, help="Number of picks to generate")
    parser.add_argument("--universe", choices=["default", "sp500", "dividend_aristocrats", "all"],
                       default="default", help="Stock universe")

    args = parser.parse_args()

    if args.mode == "picks":
        run_picks(universe_size=args.universe, top_k=args.top_k)
    elif args.mode == "quick":
        run_picks(universe_size="default", top_k=10)
    elif args.mode == "backtest":
        run_backtest()
    elif args.mode == "validate":
        run_validate()
    elif args.mode == "full":
        run_picks(universe_size=args.universe, top_k=args.top_k)
        run_backtest()
        run_validate()


if __name__ == "__main__":
    main()
