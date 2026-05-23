#!/usr/bin/env python3
"""
Live Trading Strategies for KIMI Rise of the Claw.

Adapts 5 validated Tier-1 strategies for real-time execution and adds 3 custom strategies.

10 Strategy Instances:
1. ETF Masters (stock) - QualityMinusJunk
2. Crypto Winners (crypto) - FundingRateArbitrage
3. Meme Coin Scanner (meme) - HighVolatilityScanner (custom)
4. Penny Stock Tracker (penny) - BreakoutScanner (custom)
5. Forex Scanner (forex) - MomentumFX (custom)
6. RSI Momentum 5 (crypto) - RSIStrategy (custom)
7. Alpha Hunter (crypto) - FlashCrashReversal
8. Pump Watch (crypto) - VolumeSpikeDetector (custom)
9. Blue Chip Growth (stock) - BettingAgainstBeta
10. Technical Momentum (stock) - PairsTrading

Author: Claude Sonnet 4.5
Date: 2026-02-16
"""

import logging
import sys
from pathlib import Path
from typing import Optional
import pandas as pd
import numpy as np

# Add parent directory to path
WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

from backtest_framework import Strategy, Signal

# Import Tier-1 validated strategies
try:
    from KIMI_CLAW_RESEARCH_FEB162026.strategies_tier1 import (
        FundingRateArbitrage,
        PairsTrading,
        BettingAgainstBeta,
        FlashCrashReversal,
        QualityMinusJunk
    )
    TIER1_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"Could not import Tier-1 strategies: {e}")
    TIER1_AVAILABLE = False

logger = logging.getLogger(__name__)


class LiveStrategyAdapter:
    """Adapts backtest strategies for real-time execution."""

    def __init__(self, strategy: Strategy, lookback_days: int = 90):
        """
        Initialize adapter.

        Args:
            strategy: Backtest strategy to wrap
            lookback_days: Days of historical data to fetch for indicators
        """
        self.strategy = strategy
        self.lookback_days = lookback_days
        self.data_cache = {}  # symbol -> DataFrame

    def fetch_historical_data(self, symbol: str, asset_type: str) -> pd.DataFrame:
        """
        Fetch historical data for strategy initialization.

        Args:
            symbol: Ticker symbol
            asset_type: Asset category

        Returns:
            DataFrame with OHLCV data
        """
        from datetime import datetime, timedelta
        import yfinance as yf

        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.lookback_days + 30)

        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date, interval='1d')

            if df.empty:
                raise ValueError(f"No data returned for {symbol}")

            # Standardize columns
            df.columns = [c.lower() for c in df.columns]
            df['symbol'] = symbol

            return df

        except Exception as e:
            logger.error(f"Failed to fetch historical data for {symbol}: {e}")
            return pd.DataFrame()

    def generate_signal(self, symbol: str, asset_type: str, current_price: float) -> Signal:
        """
        Generate live trading signal.

        Args:
            symbol: Ticker symbol
            asset_type: Asset category
            current_price: Real-time price

        Returns:
            Signal.BUY, Signal.SELL, or Signal.HOLD
        """
        # Fetch historical data if not cached
        if symbol not in self.data_cache:
            df = self.fetch_historical_data(symbol, asset_type)
            if df.empty:
                return Signal.HOLD
            self.data_cache[symbol] = df

        df = self.data_cache[symbol]

        # Append current price as latest bar
        from datetime import datetime
        current_bar = pd.DataFrame({
            'open': [current_price],
            'high': [current_price],
            'low': [current_price],
            'close': [current_price],
            'volume': [0],
            'symbol': [symbol]
        }, index=[datetime.now()])

        df_live = pd.concat([df, current_bar])

        try:
            # Initialize strategy with data
            self.strategy.initialize(df_live)

            # Get signal for latest bar
            latest_idx = len(df_live) - 1
            latest_bar = df_live.iloc[latest_idx]

            signal = self.strategy.on_bar(latest_idx, latest_bar)

            return signal if signal else Signal.HOLD

        except Exception as e:
            logger.error(f"Signal generation error for {symbol}: {e}")
            return Signal.HOLD


# ============================================================================
# CUSTOM STRATEGIES (3 new strategies for meme/penny/forex)
# ============================================================================

class HighVolatilityScanner(Strategy):
    """Custom strategy for meme coins - trades high volatility + oversold."""

    def __init__(self, volatility_threshold: float = 0.15):
        super().__init__("High Volatility Scanner")
        self.volatility_threshold = volatility_threshold

    def _calculate_indicators(self):
        """Calculate 5-day volatility and RSI."""
        # Volatility (annualized)
        returns = self.data['close'].pct_change()
        self.indicators['volatility'] = returns.rolling(5).std() * np.sqrt(365)

        # RSI for entry timing
        delta = self.data['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        self.indicators['rsi'] = 100 - (100 / (1 + rs))

    def on_bar(self, idx: int, bar: pd.Series) -> Optional[Signal]:
        """Buy high vol + oversold, sell on overbought."""
        if idx < 20:
            return None

        vol = self.get_indicator('volatility', idx)
        rsi = self.get_indicator('rsi', idx)

        if np.isnan(vol) or np.isnan(rsi):
            return None

        # High vol + oversold = buy the meme
        if vol > self.volatility_threshold and rsi < 30:
            return Signal.BUY

        # Overbought = take profits
        if rsi > 70:
            return Signal.SELL

        return Signal.HOLD


class BreakoutScanner(Strategy):
    """Custom strategy for penny stocks - 52-week high breakouts with volume."""

    def __init__(self, volume_threshold: float = 2.0):
        super().__init__("Breakout Scanner")
        self.volume_threshold = volume_threshold

    def _calculate_indicators(self):
        """Calculate 52-week high and volume ratio."""
        # 52-week high (252 trading days)
        self.indicators['high_52w'] = self.data['high'].rolling(252, min_periods=60).max()

        # Volume ratio (current vs 20-day average)
        self.indicators['vol_avg'] = self.data['volume'].rolling(20).mean()
        self.indicators['vol_ratio'] = self.data['volume'] / self.indicators['vol_avg']

    def on_bar(self, idx: int, bar: pd.Series) -> Optional[Signal]:
        """Buy on breakout, sell on -5% or when volume fades."""
        if idx < 60:
            return None

        high_52w = self.get_indicator('high_52w', idx)
        vol_ratio = self.get_indicator('vol_ratio', idx)

        if np.isnan(high_52w) or np.isnan(vol_ratio):
            return None

        price = bar['close']

        # Breakout: new 52-week high with volume surge
        if price >= high_52w * 0.998 and vol_ratio > self.volume_threshold:
            return Signal.BUY

        # Exit on volume fade (risk of false breakout)
        if vol_ratio < 0.5:
            return Signal.SELL

        return Signal.HOLD


class MomentumFX(Strategy):
    """Custom strategy for forex - 20/50 MA crossover momentum."""

    def __init__(self):
        super().__init__("Momentum FX")

    def _calculate_indicators(self):
        """Calculate 20 and 50-day moving averages."""
        self.indicators['ma20'] = self.data['close'].rolling(20).mean()
        self.indicators['ma50'] = self.data['close'].rolling(50).mean()

        # Momentum indicator
        self.indicators['momentum'] = self.data['close'].pct_change(10) * 100

    def on_bar(self, idx: int, bar: pd.Series) -> Optional[Signal]:
        """Buy on bullish crossover, sell on bearish crossover."""
        if idx < 60:
            return None

        ma20_curr = self.get_indicator('ma20', idx)
        ma50_curr = self.get_indicator('ma50', idx)
        ma20_prev = self.get_indicator('ma20', idx - 1)
        ma50_prev = self.get_indicator('ma50', idx - 1)

        if any(np.isnan([ma20_curr, ma50_curr, ma20_prev, ma50_prev])):
            return None

        # Bullish crossover: MA20 crosses above MA50
        if ma20_prev <= ma50_prev and ma20_curr > ma50_curr:
            return Signal.BUY

        # Bearish crossover: MA20 crosses below MA50
        if ma20_prev >= ma50_prev and ma20_curr < ma50_curr:
            return Signal.SELL

        return Signal.HOLD


class RSIStrategy(Strategy):
    """Custom RSI mean-reversion strategy for crypto."""

    def __init__(self, oversold: float = 30, overbought: float = 70):
        super().__init__("RSI Momentum")
        self.oversold = oversold
        self.overbought = overbought

    def _calculate_indicators(self):
        """Calculate RSI."""
        delta = self.data['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        self.indicators['rsi'] = 100 - (100 / (1 + rs))

    def on_bar(self, idx: int, bar: pd.Series) -> Optional[Signal]:
        """Buy oversold, sell overbought."""
        if idx < 20:
            return None

        rsi = self.get_indicator('rsi', idx)

        if np.isnan(rsi):
            return None

        if rsi < self.oversold:
            return Signal.BUY

        if rsi > self.overbought:
            return Signal.SELL

        return Signal.HOLD


class VolumeSpikeDetector(Strategy):
    """Custom strategy for detecting volume spikes (pump detection)."""

    def __init__(self, spike_threshold: float = 5.0):
        super().__init__("Volume Spike Detector")
        self.spike_threshold = spike_threshold

    def _calculate_indicators(self):
        """Calculate volume spike ratio."""
        self.indicators['vol_avg'] = self.data['volume'].rolling(20).mean()
        self.indicators['vol_spike'] = self.data['volume'] / self.indicators['vol_avg']

        # Price momentum
        self.indicators['momentum'] = self.data['close'].pct_change(5) * 100

    def on_bar(self, idx: int, bar: pd.Series) -> Optional[Signal]:
        """Buy on volume spike + positive momentum, sell quickly."""
        if idx < 25:
            return None

        vol_spike = self.get_indicator('vol_spike', idx)
        momentum = self.get_indicator('momentum', idx)

        if np.isnan(vol_spike) or np.isnan(momentum):
            return None

        # Volume spike + rising price = potential pump
        if vol_spike > self.spike_threshold and momentum > 2:
            return Signal.BUY

        # Exit quickly (pumps dump fast)
        if momentum < -3:
            return Signal.SELL

        return Signal.HOLD


# ============================================================================
# STRATEGY CONFIGURATION - 10 Pre-configured Instances
# ============================================================================

def create_live_strategies() -> dict:
    """
    Create 10 live strategy instances mapped to dashboard categories.

    Returns:
        Dict mapping algorithm_id to strategy configuration
    """
    strategies = {}

    # Use Tier-1 strategies if available, otherwise use custom
    if TIER1_AVAILABLE:
        strategies.update({
            'etf-masters-live': {
                'name': 'ETF Masters',
                'strategy': LiveStrategyAdapter(QualityMinusJunk()),
                'universe': ['SPY', 'QQQ', 'VTI', 'IWM'],
                'asset_type': 'stock'
            },
            'crypto-winners-live': {
                'name': 'Crypto Winners Scanner',
                'strategy': LiveStrategyAdapter(FundingRateArbitrage()),
                'universe': ['BTC-USD', 'ETH-USD', 'SOL-USD'],
                'asset_type': 'crypto'
            },
            'blue-chip-live': {
                'name': 'Blue Chip Growth',
                'strategy': LiveStrategyAdapter(BettingAgainstBeta()),
                'universe': ['AAPL', 'MSFT', 'NVDA', 'GOOG'],
                'asset_type': 'stock'
            },
            'alpha-hunter-live': {
                'name': 'Alpha Hunter',
                'strategy': LiveStrategyAdapter(FlashCrashReversal()),
                'universe': ['BTC-USD', 'ETH-USD'],
                'asset_type': 'crypto'
            },
            'technical-momentum-live': {
                'name': 'Technical Momentum',
                'strategy': LiveStrategyAdapter(PairsTrading()),
                'universe': ['SPY', 'QQQ'],
                'asset_type': 'stock'
            }
        })
    else:
        # Fallback to custom strategies only
        logger.warning("Using custom strategies only (Tier-1 not available)")

    # Custom strategies (always added)
    strategies.update({
        'meme-scanner-live': {
            'name': 'Meme Coin Scanner',
            'strategy': LiveStrategyAdapter(HighVolatilityScanner()),
            'universe': ['DOGE-USD', 'SHIB-USD'],
            'asset_type': 'meme'
        },
        'penny-tracker-live': {
            'name': 'Penny Stock Tracker',
            'strategy': LiveStrategyAdapter(BreakoutScanner()),
            'universe': ['SNDL', 'GEVO'],  # Example penny stocks
            'asset_type': 'penny'
        },
        'forex-scanner-live': {
            'name': 'Forex Scanner',
            'strategy': LiveStrategyAdapter(MomentumFX()),
            'universe': ['EURUSD=X', 'GBPUSD=X'],
            'asset_type': 'forex'
        },
        'rsi-momentum-live': {
            'name': 'RSI Momentum 5',
            'strategy': LiveStrategyAdapter(RSIStrategy()),
            'universe': ['BTC-USD', 'ETH-USD', 'BNB-USD'],
            'asset_type': 'crypto'
        },
        'pump-watch-live': {
            'name': 'Pump Watch',
            'strategy': LiveStrategyAdapter(VolumeSpikeDetector()),
            'universe': ['DOGE-USD', 'SHIB-USD'],
            'asset_type': 'crypto'
        }
    })

    return strategies


# Module-level singleton
LIVE_STRATEGIES = create_live_strategies()


if __name__ == '__main__':
    # Test strategy initialization
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    print("Testing Live Strategies")
    print("=" * 60)

    strategies = LIVE_STRATEGIES

    print(f"\n[Strategies Loaded]")
    print(f"  Total: {len(strategies)}")
    for algo_id, config in strategies.items():
        print(f"  {algo_id}:")
        print(f"    Name: {config['name']}")
        print(f"    Universe: {config['universe']}")
        print(f"    Asset Type: {config['asset_type']}")

    # Test signal generation
    print(f"\n[Test Signal Generation]")
    test_algo = 'rsi-momentum-live'
    test_symbol = 'BTC-USD'
    test_price = 68000.0

    config = strategies[test_algo]
    strategy_adapter = config['strategy']

    print(f"  Algorithm: {config['name']}")
    print(f"  Symbol: {test_symbol}")
    print(f"  Price: ${test_price:.2f}")

    signal = strategy_adapter.generate_signal(test_symbol, 'crypto', test_price)
    print(f"  Signal: {signal.name}")

    print("\n" + "=" * 60)
    print("Test complete!")
