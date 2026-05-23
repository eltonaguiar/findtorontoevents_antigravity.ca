"""
================================================================================
PAIRS TRADING - PRACTICAL EXAMPLES FOR CRYPTO AND ETF PAIRS
================================================================================
This file provides practical examples for the pairs mentioned in the context:
- Crypto pairs: BTC/DOT, BTC/DOGE, ETH/SOL
- ETF pairs: XLB/XLP (sector ETFs)
- Integration with existing infrastructure

Author: Quantitative Research Team
================================================================================
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging

# Import the pairs trading system
from pairs_trading_system import (
    PairsTradingStrategy, PairsBacktester, ParameterOptimizer,
    PairConfig, SignalType, ExitReason, CointegrationResult
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ================================================================================
# EXAMPLE 1: BTC/DOT PAIR (Long BTC / Short DOT)
# ================================================================================

def btc_dot_example():
    """
    Example implementation for BTC/DOT pair.
    
    Rationale: Both are Layer 1 blockchain tokens with similar market exposure
    but different risk profiles. BTC is the market leader, DOT is a mid-cap alt.
    """
    print("=" * 80)
    print("EXAMPLE 1: BTC/DOT PAIR TRADING")
    print("=" * 80)
    
    # Generate synthetic data (replace with real data in production)
    np.random.seed(42)
    dates = pd.date_range(start='2022-01-01', periods=500, freq='D')
    
    # BTC prices (more stable, lower volatility)
    btc_returns = np.random.randn(500) * 0.035
    btc_prices = 40000 * np.exp(np.cumsum(btc_returns))
    
    # DOT prices (higher beta to BTC)
    dot_beta = 1.3
    dot_noise = np.random.randn(500) * 0.025
    dot_returns = dot_beta * btc_returns + dot_noise
    dot_prices = 25 * np.exp(np.cumsum(dot_returns))
    
    btc_series = pd.Series(btc_prices, index=dates, name='BTC')
    dot_series = pd.Series(dot_prices, index=dates, name='DOT')
    
    # Test for cointegration
    print("\n[1] Testing BTC/DOT for cointegration...")
    coint_result = PairsTradingStrategy.engle_granger_test(btc_series, dot_series)
    print(f"    Cointegrated: {coint_result.is_cointegrated}")
    print(f"    P-value: {coint_result.p_value:.4f}")
    print(f"    Hedge Ratio: {coint_result.hedge_ratio:.4f}")
    print(f"    Half-Life: {coint_result.half_life:.1f} days")
    
    # Configure strategy
    config = PairConfig(
        asset1="BTC",
        asset2="DOT",
        lookback_period=60,           # 60 days for crypto
        entry_zscore=2.0,             # Enter at ±2σ
        exit_zscore=0.5,              # Exit at ±0.5σ
        stop_loss_zscore=3.5,         # Stop at ±3.5σ
        max_holding_periods=20,       # Max 20 days
        position_size_method="dollar_neutral"
    )
    
    print("\n[2] Strategy Configuration:")
    print(f"    Lookback: {config.lookback_period} days")
    print(f"    Entry: ±{config.entry_zscore}σ")
    print(f"    Exit: ±{config.exit_zscore}σ")
    print(f"    Stop Loss: ±{config.stop_loss_zscore}σ")
    
    # Run backtest
    strategy = PairsTradingStrategy(config, use_log_prices=True)
    backtester = PairsBacktester(strategy, initial_capital=100000)
    
    print("\n[3] Running backtest...")
    results = backtester.run_backtest(btc_series, dot_series)
    
    # Performance metrics
    metrics = backtester.get_performance_metrics()
    print("\n[4] Performance Metrics:")
    print(f"    Total Return: {metrics['total_return']:.2%}")
    print(f"    Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"    Win Rate: {metrics['win_rate']:.2%}")
    print(f"    Max Drawdown: {metrics['max_drawdown']:.2%}")
    print(f"    Total Trades: {metrics['total_trades']}")
    print(f"    Profit Factor: {metrics['profit_factor']:.2f}")
    
    return results, metrics


# ================================================================================
# EXAMPLE 2: BTC/DOGE PAIR
# ================================================================================

def btc_doge_example():
    """
    Example implementation for BTC/DOGE pair.
    
    Rationale: DOGE has higher volatility and meme-driven price action,
    creating divergence opportunities from BTC's more fundamental movements.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 2: BTC/DOGE PAIR TRADING")
    print("=" * 80)
    
    # Generate synthetic data
    np.random.seed(43)
    dates = pd.date_range(start='2022-01-01', periods=500, freq='D')
    
    # BTC prices
    btc_returns = np.random.randn(500) * 0.035
    btc_prices = 40000 * np.exp(np.cumsum(btc_returns))
    
    # DOGE prices (higher volatility, meme effects)
    doge_beta = 1.5
    doge_meme_effect = np.random.randn(500) * 0.05  # Extra noise
    doge_returns = doge_beta * btc_returns + doge_meme_effect
    doge_prices = 0.15 * np.exp(np.cumsum(doge_returns))
    
    btc_series = pd.Series(btc_prices, index=dates, name='BTC')
    doge_series = pd.Series(doge_prices, index=dates, name='DOGE')
    
    # Test for cointegration
    print("\n[1] Testing BTC/DOGE for cointegration...")
    coint_result = PairsTradingStrategy.engle_granger_test(btc_series, doge_series)
    print(f"    Cointegrated: {coint_result.is_cointegrated}")
    print(f"    P-value: {coint_result.p_value:.4f}")
    print(f"    Half-Life: {coint_result.half_life:.1f} days")
    
    # Configure strategy with wider thresholds for higher volatility
    config = PairConfig(
        asset1="BTC",
        asset2="DOGE",
        lookback_period=60,
        entry_zscore=2.5,             # Wider entry for higher vol
        exit_zscore=0.5,
        stop_loss_zscore=4.0,         # Wider stop for DOGE volatility
        max_holding_periods=15,       # Shorter holding for meme risk
        position_size_method="dollar_neutral"
    )
    
    print("\n[2] Strategy Configuration (adjusted for DOGE volatility):")
    print(f"    Entry: ±{config.entry_zscore}σ (wider for high vol)")
    print(f"    Stop Loss: ±{config.stop_loss_zscore}σ")
    print(f"    Max Holding: {config.max_holding_periods} days")
    
    # Run backtest
    strategy = PairsTradingStrategy(config, use_log_prices=True)
    backtester = PairsBacktester(strategy, initial_capital=100000)
    
    print("\n[3] Running backtest...")
    results = backtester.run_backtest(btc_series, doge_series)
    
    metrics = backtester.get_performance_metrics()
    print("\n[4] Performance Metrics:")
    print(f"    Total Return: {metrics['total_return']:.2%}")
    print(f"    Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"    Win Rate: {metrics['win_rate']:.2%}")
    print(f"    Max Drawdown: {metrics['max_drawdown']:.2%}")
    
    return results, metrics


# ================================================================================
# EXAMPLE 3: ETH/SOL PAIR
# ================================================================================

def eth_sol_example():
    """
    Example implementation for ETH/SOL pair.
    
    Rationale: Both are smart contract platforms with similar narratives.
    SOL is often viewed as an "ETH killer" creating correlated but divergent moves.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 3: ETH/SOL PAIR TRADING")
    print("=" * 80)
    
    # Generate synthetic data
    np.random.seed(44)
    dates = pd.date_range(start='2022-01-01', periods=500, freq='D')
    
    # ETH prices
    eth_returns = np.random.randn(500) * 0.045
    eth_prices = 3000 * np.exp(np.cumsum(eth_returns))
    
    # SOL prices (higher beta, more volatile)
    sol_beta = 1.4
    sol_noise = np.random.randn(500) * 0.035
    sol_returns = sol_beta * eth_returns + sol_noise
    sol_prices = 100 * np.exp(np.cumsum(sol_returns))
    
    eth_series = pd.Series(eth_prices, index=dates, name='ETH')
    sol_series = pd.Series(sol_prices, index=dates, name='SOL')
    
    # Test for cointegration
    print("\n[1] Testing ETH/SOL for cointegration...")
    coint_result = PairsTradingStrategy.engle_granger_test(eth_series, sol_series)
    print(f"    Cointegrated: {coint_result.is_cointegrated}")
    print(f"    P-value: {coint_result.p_value:.4f}")
    print(f"    Hedge Ratio: {coint_result.hedge_ratio:.4f}")
    print(f"    Half-Life: {coint_result.half_life:.1f} days")
    
    # Configure strategy
    config = PairConfig(
        asset1="ETH",
        asset2="SOL",
        lookback_period=60,
        entry_zscore=2.0,
        exit_zscore=0.5,
        stop_loss_zscore=3.5,
        max_holding_periods=20,
        position_size_method="dollar_neutral"
    )
    
    # Run backtest
    strategy = PairsTradingStrategy(config, use_log_prices=True)
    backtester = PairsBacktester(strategy, initial_capital=100000)
    
    print("\n[2] Running backtest...")
    results = backtester.run_backtest(eth_series, sol_series)
    
    metrics = backtester.get_performance_metrics()
    print("\n[3] Performance Metrics:")
    print(f"    Total Return: {metrics['total_return']:.2%}")
    print(f"    Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"    Win Rate: {metrics['win_rate']:.2%}")
    print(f"    Max Drawdown: {metrics['max_drawdown']:.2%}")
    
    return results, metrics


# ================================================================================
# EXAMPLE 4: SECTOR ETF PAIR (XLB/XLP)
# ================================================================================

def xlb_xlp_example():
    """
    Example implementation for XLB/XLP sector ETF pair.
    
    Rationale: Materials (XLB) vs Consumer Staples (XLP) represents a
    cyclical vs defensive trade. Good for regime-based pair trading.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 4: XLB/XLP SECTOR ETF PAIR TRADING")
    print("=" * 80)
    
    # Generate synthetic data
    np.random.seed(45)
    dates = pd.date_range(start='2022-01-01', periods=500, freq='D')
    
    # Market factor
    market_returns = np.random.randn(500) * 0.012
    
    # XLB (Materials) - higher beta, more cyclical
    xlb_beta = 1.2
    xlb_specific = np.random.randn(500) * 0.008
    xlb_returns = xlb_beta * market_returns + xlb_specific
    xlb_prices = 80 * np.exp(np.cumsum(xlb_returns))
    
    # XLP (Consumer Staples) - lower beta, defensive
    xlp_beta = 0.7
    xlp_specific = np.random.randn(500) * 0.006
    xlp_returns = xlp_beta * market_returns + xlp_specific
    xlp_prices = 70 * np.exp(np.cumsum(xlp_returns))
    
    xlb_series = pd.Series(xlb_prices, index=dates, name='XLB')
    xlp_series = pd.Series(xlp_prices, index=dates, name='XLP')
    
    # Test for cointegration
    print("\n[1] Testing XLB/XLP for cointegration...")
    coint_result = PairsTradingStrategy.engle_granger_test(xlb_series, xlp_series)
    print(f"    Cointegrated: {coint_result.is_cointegrated}")
    print(f"    P-value: {coint_result.p_value:.4f}")
    print(f"    Hedge Ratio: {coint_result.hedge_ratio:.4f}")
    print(f"    Half-Life: {coint_result.half_life:.1f} days")
    
    # Configure strategy for ETFs (longer lookback, tighter thresholds)
    config = PairConfig(
        asset1="XLB",
        asset2="XLP",
        lookback_period=90,           # Longer for ETFs
        entry_zscore=2.0,
        exit_zscore=0.0,              # Exit at mean for ETFs
        stop_loss_zscore=3.0,
        max_holding_periods=30,       # Longer holding for slower mean reversion
        position_size_method="beta_neutral"  # Beta-neutral for sector pairs
    )
    
    print("\n[2] Strategy Configuration (ETF-specific):")
    print(f"    Lookback: {config.lookback_period} days (longer for ETFs)")
    print(f"    Exit: {config.exit_zscore}σ (exit at mean)")
    print(f"    Position Sizing: {config.position_size_method}")
    
    # Run backtest
    strategy = PairsTradingStrategy(config, use_log_prices=False)
    backtester = PairsBacktester(strategy, initial_capital=100000)
    
    print("\n[3] Running backtest...")
    results = backtester.run_backtest(xlb_series, xlp_series)
    
    metrics = backtester.get_performance_metrics()
    print("\n[4] Performance Metrics:")
    print(f"    Total Return: {metrics['total_return']:.2%}")
    print(f"    Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"    Win Rate: {metrics['win_rate']:.2%}")
    print(f"    Max Drawdown: {metrics['max_drawdown']:.2%}")
    print(f"    Total Trades: {metrics['total_trades']}")
    
    return results, metrics


# ================================================================================
# EXAMPLE 5: FINDING COINTEGRATED PAIRS IN UNIVERSE
# ================================================================================

def find_pairs_example():
    """
    Example of finding cointegrated pairs from a universe of assets.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 5: FINDING COINTEGRATED PAIRS")
    print("=" * 80)
    
    np.random.seed(46)
    dates = pd.date_range(start='2022-01-01', periods=365, freq='D')
    
    # Generate correlated price series
    n_assets = 6
    market_factor = np.cumsum(np.random.randn(365) * 0.02)
    
    prices_dict = {}
    assets = ['BTC', 'ETH', 'SOL', 'DOT', 'SPY', 'QQQ']
    betas = [1.0, 1.1, 1.3, 1.2, 0.9, 1.0]
    starting_prices = [40000, 3000, 100, 25, 450, 380]
    
    for asset, beta, start_price in zip(assets, betas, starting_prices):
        specific = np.random.randn(365) * 0.02
        returns = beta * np.diff(market_factor, prepend=0) + specific
        prices = start_price * np.exp(np.cumsum(returns))
        prices_dict[asset] = pd.Series(prices, index=dates, name=asset)
    
    # Create DataFrame
    price_df = pd.DataFrame(prices_dict)
    
    print("\n[1] Price Data Summary:")
    print(price_df.head())
    
    # Find cointegrated pairs
    print("\n[2] Searching for cointegrated pairs...")
    coint_pairs = PairsTradingStrategy.find_cointegrated_pairs(
        price_df,
        significance=0.05,
        min_half_life=5,
        max_half_life=100
    )
    
    if not coint_pairs.empty:
        print(f"\n    Found {len(coint_pairs)} cointegrated pairs:")
        print(coint_pairs.to_string())
        
        # Show top pair
        top_pair = coint_pairs.iloc[0]
        print(f"\n[3] Top Pair: {top_pair['asset1']}/{top_pair['asset2']}")
        print(f"    P-value: {top_pair['p_value']:.4f}")
        print(f"    Half-life: {top_pair['half_life']:.1f} days")
        print(f"    Hedge ratio: {top_pair['hedge_ratio']:.4f}")
    else:
        print("\n    No cointegrated pairs found")
    
    return coint_pairs


# ================================================================================
# EXAMPLE 6: PARAMETER OPTIMIZATION
# ================================================================================

def optimization_example():
    """
    Example of parameter optimization for a pair.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 6: PARAMETER OPTIMIZATION")
    print("=" * 80)
    
    # Generate data
    np.random.seed(47)
    dates = pd.date_range(start='2022-01-01', periods=400, freq='D')
    
    btc_returns = np.random.randn(400) * 0.035
    btc_prices = 40000 * np.exp(np.cumsum(btc_returns))
    
    eth_beta = 1.1
    eth_noise = np.random.randn(400) * 0.025
    eth_returns = eth_beta * btc_returns + eth_noise
    eth_prices = 3000 * np.exp(np.cumsum(eth_returns))
    
    btc_series = pd.Series(btc_prices, index=dates, name='BTC')
    eth_series = pd.Series(eth_prices, index=dates, name='ETH')
    
    print("\n[1] Running grid search optimization...")
    print("    Testing entry: [1.5, 2.0, 2.5]")
    print("    Testing exit: [0.0, 0.5, 1.0]")
    print("    Testing lookback: [30, 60]")
    
    # Grid search
    opt_results = ParameterOptimizer.optimize_zscore_thresholds(
        btc_series.iloc[:300],  # Use first 300 for optimization
        eth_series.iloc[:300],
        entry_range=np.arange(1.5, 3.0, 0.5),
        exit_range=np.arange(0.0, 1.0, 0.5),
        lookback_range=[30, 60],
        metric="sharpe"
    )
    
    if not opt_results.empty:
        print("\n[2] Top 5 Parameter Combinations:")
        print(opt_results.head().to_string())
        
        best = opt_results.iloc[0]
        print(f"\n[3] Best Parameters:")
        print(f"    Entry: {best['entry']}")
        print(f"    Exit: {best['exit']}")
        print(f"    Lookback: {best['lookback']}")
        print(f"    Sharpe: {best['sharpe']:.2f}")
        
        # Test on out-of-sample data
        print("\n[4] Testing on out-of-sample data...")
        config = PairConfig(
            asset1="BTC",
            asset2="ETH",
            lookback_period=int(best['lookback']),
            entry_zscore=best['entry'],
            exit_zscore=best['exit'],
            stop_loss_zscore=3.5,
            max_holding_periods=20
        )
        
        strategy = PairsTradingStrategy(config)
        backtester = PairsBacktester(strategy, initial_capital=100000)
        
        # Test on last 100 days (out-of-sample)
        oos_results = backtester.run_backtest(
            btc_series.iloc[300:],
            eth_series.iloc[300:]
        )
        
        oos_metrics = backtester.get_performance_metrics()
        print(f"\n    Out-of-sample Sharpe: {oos_metrics['sharpe_ratio']:.2f}")
        print(f"    Out-of-sample Return: {oos_metrics['total_return']:.2%}")
    
    return opt_results


# ================================================================================
# EXAMPLE 7: INTEGRATION WITH EXISTING INFRASTRUCTURE
# ================================================================================

def integration_example():
    """
    Example of integrating with existing `pairs_divergence` infrastructure.
    
    The existing infrastructure uses log-ratio z-score. This example shows
    how to bridge between the two approaches.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 7: INTEGRATION WITH EXISTING INFRASTRUCTURE")
    print("=" * 80)
    
    print("""
    Existing Infrastructure: `pairs_divergence` in institutional_picks_engine.py
    
    The existing system uses log-ratio z-score:
        z_score = (log_ratio - mean) / std
        where log_ratio = log(price1 / price2)
    
    This is equivalent to our spread calculation with hedge_ratio = 1:
        spread = log(price1) - log(price2) = log(price1 / price2)
    
    Integration approach:
    1. Use existing log-ratio calculation
    2. Apply our signal generation and risk management
    3. Use our position sizing methods
    """)
    
    # Generate data
    np.random.seed(48)
    dates = pd.date_range(start='2022-01-01', periods=200, freq='D')
    
    btc_returns = np.random.randn(200) * 0.035
    btc_prices = 40000 * np.exp(np.cumsum(btc_returns))
    
    eth_returns = 1.1 * btc_returns + np.random.randn(200) * 0.025
    eth_prices = 3000 * np.exp(np.cumsum(eth_returns))
    
    btc_series = pd.Series(btc_prices, index=dates, name='BTC')
    eth_series = pd.Series(eth_prices, index=dates, name='ETH')
    
    # Existing approach: log-ratio z-score
    print("\n[1] Existing approach (log-ratio z-score):")
    log_ratio = np.log(btc_series / eth_series)
    log_ratio_mean = log_ratio.rolling(60).mean()
    log_ratio_std = log_ratio.rolling(60).std()
    existing_zscore = (log_ratio - log_ratio_mean) / log_ratio_std
    
    print(f"    Current z-score: {existing_zscore.iloc[-1]:.2f}")
    
    # Our approach with hedge_ratio = 1
    print("\n[2] Our approach (equivalent with hedge_ratio=1):")
    config = PairConfig(
        asset1="BTC",
        asset2="ETH",
        lookback_period=60,
        entry_zscore=2.0,
        exit_zscore=0.5,
        stop_loss_zscore=3.5
    )
    
    strategy = PairsTradingStrategy(config, use_log_prices=True)
    
    # Manually set hedge_ratio to 1 for compatibility
    spread = np.log(btc_series) - 1.0 * np.log(eth_series)
    zscore = strategy.calculate_zscore(spread)
    
    print(f"    Current z-score: {zscore.iloc[-1]:.2f}")
    
    # Generate signals using our framework
    signals = strategy.generate_signals(zscore)
    
    current_position = signals['position'].iloc[-1]
    print(f"\n[3] Current Signal:")
    if current_position == 1:
        print("    LONG SPREAD: Long BTC, Short ETH")
    elif current_position == -1:
        print("    SHORT SPREAD: Short BTC, Long ETH")
    else:
        print("    NO POSITION")
    
    # Position sizing
    print("\n[4] Position Sizing:")
    position_sizes = strategy.calculate_position_sizes(
        btc_series.iloc[-1],
        eth_series.iloc[-1],
        hedge_ratio=1.0,
        capital=100000,
        method="dollar_neutral"
    )
    
    btc_qty = position_sizes['BTC']
    eth_qty = position_sizes['ETH']
    btc_value = btc_qty * btc_series.iloc[-1]
    eth_value = eth_qty * eth_series.iloc[-1]
    
    print(f"    BTC: {btc_qty:.4f} (${btc_value:,.2f})")
    print(f"    ETH: {eth_qty:.4f} (${eth_value:,.2f})")
    
    print("""
    
    Integration Code for institutional_picks_engine.py:
    
    ```python
    from pairs_trading_system import PairsTradingStrategy, PairConfig
    
    def enhanced_pairs_divergence(price1, price2, lookback=60):
        # Existing log-ratio calculation
        log_ratio = np.log(price1 / price2)
        
        # Use our framework for signals and sizing
        config = PairConfig(
            asset1="Asset1",
            asset2="Asset2",
            lookback_period=lookback,
            entry_zscore=2.0,
            exit_zscore=0.5
        )
        
        strategy = PairsTradingStrategy(config, use_log_prices=True)
        spread = np.log(price1) - np.log(price2)  # hedge_ratio = 1
        zscore = strategy.calculate_zscore(spread)
        signals = strategy.generate_signals(zscore)
        
        # Add position sizing
        if signals['position'].iloc[-1] != 0:
            sizes = strategy.calculate_position_sizes(
                price1.iloc[-1], price2.iloc[-1],
                hedge_ratio=1.0, capital=allocated_capital
            )
            return {
                'zscore': zscore.iloc[-1],
                'signal': signals['position'].iloc[-1],
                'position_sizes': sizes
            }
    ```
    """)
    
    return signals


# ================================================================================
# EXAMPLE 8: BEAR MARKET SURVIVAL STRATEGIES
# ================================================================================

def bear_market_example():
    """
    Example of pairs trading adjustments for bear market survival.
    
    Key adjustments:
    1. Tighter stop losses
    2. Faster exits (exit at mean, not profit target)
    3. Reduced position sizes
    4. Higher entry thresholds to avoid false signals
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 8: BEAR MARKET SURVIVAL STRATEGIES")
    print("=" * 80)
    
    # Generate bear market data (strong downtrend with volatility)
    np.random.seed(49)
    dates = pd.date_range(start='2022-01-01', periods=365, freq='D')
    
    # Bear market trend
    trend = -0.001  # Daily downtrend
    
    # BTC in bear market
    btc_returns = trend + np.random.randn(365) * 0.045
    btc_prices = 50000 * np.exp(np.cumsum(btc_returns))
    
    # ETH (higher beta, falls more)
    eth_returns = 1.2 * trend + np.random.randn(365) * 0.055
    eth_prices = 4000 * np.exp(np.cumsum(eth_returns))
    
    btc_series = pd.Series(btc_prices, index=dates, name='BTC')
    eth_series = pd.Series(eth_prices, index=dates, name='ETH')
    
    print("\n[1] Market Regime: BEAR MARKET")
    print(f"    BTC Return: {(btc_series.iloc[-1]/btc_series.iloc[0] - 1):.2%}")
    print(f"    ETH Return: {(eth_series.iloc[-1]/eth_series.iloc[0] - 1):.2%}")
    
    # Normal strategy
    print("\n[2] Normal Strategy Performance:")
    normal_config = PairConfig(
        asset1="BTC",
        asset2="ETH",
        lookback_period=60,
        entry_zscore=2.0,
        exit_zscore=0.5,
        stop_loss_zscore=3.5,
        max_holding_periods=20
    )
    
    normal_strategy = PairsTradingStrategy(normal_config)
    normal_backtester = PairsBacktester(normal_strategy, initial_capital=100000)
    normal_results = normal_backtester.run_backtest(btc_series, eth_series)
    normal_metrics = normal_backtester.get_performance_metrics()
    
    print(f"    Return: {normal_metrics['total_return']:.2%}")
    print(f"    Sharpe: {normal_metrics['sharpe_ratio']:.2f}")
    print(f"    Max DD: {normal_metrics['max_drawdown']:.2%}")
    
    # Bear market adjusted strategy
    print("\n[3] Bear Market Adjusted Strategy:")
    bear_config = PairConfig(
        asset1="BTC",
        asset2="ETH",
        lookback_period=60,
        entry_zscore=2.5,         # Higher entry threshold
        exit_zscore=0.0,          # Exit at mean (no profit target)
        stop_loss_zscore=3.0,     # Tighter stop
        max_holding_periods=10    # Shorter holding
    )
    
    print(f"    Entry: ±{bear_config.entry_zscore}σ (higher)")
    print(f"    Exit: {bear_config.exit_zscore}σ (at mean)")
    print(f"    Stop: ±{bear_config.stop_loss_zscore}σ (tighter)")
    print(f"    Max Hold: {bear_config.max_holding_periods} days (shorter)")
    
    bear_strategy = PairsTradingStrategy(bear_config)
    bear_backtester = PairsBacktester(bear_strategy, initial_capital=100000)
    bear_results = bear_backtester.run_backtest(btc_series, eth_series)
    bear_metrics = bear_backtester.get_performance_metrics()
    
    print(f"\n    Return: {bear_metrics['total_return']:.2%}")
    print(f"    Sharpe: {bear_metrics['sharpe_ratio']:.2f}")
    print(f"    Max DD: {bear_metrics['max_drawdown']:.2%}")
    print(f"    Win Rate: {bear_metrics['win_rate']:.2%}")
    
    # Comparison
    print("\n[4] Comparison:")
    print(f"    Return Improvement: {(bear_metrics['total_return'] - normal_metrics['total_return']):.2%}")
    print(f"    Sharpe Improvement: {(bear_metrics['sharpe_ratio'] - normal_metrics['sharpe_ratio']):.2f}")
    print(f"    Drawdown Reduction: {(bear_metrics['max_drawdown'] - normal_metrics['max_drawdown']):.2%}")
    
    return normal_metrics, bear_metrics


# ================================================================================
# MAIN EXECUTION
# ================================================================================

def run_all_examples():
    """Run all examples."""
    
    print("\n" + "=" * 80)
    print("PAIRS TRADING - PRACTICAL EXAMPLES")
    print("=" * 80)
    
    # Run each example
    btc_dot_example()
    btc_doge_example()
    eth_sol_example()
    xlb_xlp_example()
    find_pairs_example()
    optimization_example()
    integration_example()
    bear_market_example()
    
    print("\n" + "=" * 80)
    print("ALL EXAMPLES COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    run_all_examples()
