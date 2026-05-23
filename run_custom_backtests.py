import pandas as pd
import logging
import sys
from backtest_framework import BacktestEngine, BacktestConfig, Strategy, Signal, PositionSide
from backtest_framework import DataLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleIchimokuStrategy(Strategy):
    def __init__(self, name="Simple Ichimoku"):
        super().__init__(name)
        # Indicators will be stored in self.indicators dict

    def _calculate_indicators(self):
        # Standard Ichimoku periods: 9, 26, 52
        high = self.data['high']
        low = self.data['low']
        close = self.data['close']
        # Tenkan-sen (9)
        self.indicators['tenkan'] = (high.rolling(9).max() + low.rolling(9).min()) / 2
        # Kijun-sen (26)
        self.indicators['kijun'] = (high.rolling(26).max() + low.rolling(26).min()) / 2
        # Senkou Span A (average of Tenkan and Kijun shifted forward 26 periods)
        self.indicators['senkou_a'] = ((self.indicators['tenkan'] + self.indicators['kijun']) / 2).shift(26)
        # Senkou Span B (52) shifted forward 26 periods
        self.indicators['senkou_b'] = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
        # Chikou Span (close shifted back 26 periods)
        self.indicators['chikou'] = close.shift(-26)

    def on_bar(self, idx, bar):
        # Simple entry/exit logic based on cloud and Tenkan/Kijun cross
        price = bar['close']
        # Ensure we have values for this index
        if pd.isna(self.indicators['senkou_a'].iloc[idx]) or pd.isna(self.indicators['senkou_b'].iloc[idx]):
            return Signal.HOLD
        cloud_top = max(self.indicators['senkou_a'].iloc[idx], self.indicators['senkou_b'].iloc[idx])
        cloud_bottom = min(self.indicators['senkou_a'].iloc[idx], self.indicators['senkou_b'].iloc[idx])
        tenkan = self.indicators['tenkan'].iloc[idx]
        kijun = self.indicators['kijun'].iloc[idx]
        # Buy when price above cloud and Tenkan > Kijun
        if price > cloud_top and tenkan > kijun:
            return Signal.BUY
        # Sell when price below cloud and Tenkan < Kijun
        if price < cloud_bottom and tenkan < kijun:
            return Signal.SELL
        return Signal.HOLD


def run_backtest(symbol: str, start: str, end: str, interval: str):
    # Choose data source based on interval granularity
    if interval in ["15m", "1h", "4h"]:
        # Kraken provides intraday OHLCV for crypto
        df = DataLoader.from_kraken(symbol.replace("-", ""), start, end, interval=15 if interval == "15m" else 60 if interval == "1h" else 240)
    else:
        df = DataLoader.from_yahoo(symbol, start, end, interval)
    # Verify required columns
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col not in df.columns:
            raise ValueError(f"Missing column {col}")
    strat = SimpleIchimokuStrategy()
    strat.initialize(df)
    cfg = BacktestConfig(initial_capital=100000, commission_rate=0.001, slippage=0.0005)
    engine = BacktestEngine(cfg)
    engine.set_data(df)
    engine.set_strategy(strat)
    result = engine.run()
    return result

if __name__ == "__main__":
    # Define test horizons
    horizons = {
        "short": "15m",
        "medium": "1h",
        "long": "4h",
        "daily": "1d",
        "weekly": "1w"
    }
    symbol = "BTC-USD"
    for name, tf in horizons.items():
        logger.info(f"Running backtest for {name} horizon ({tf})")
        # Determine date range based on timeframe
        if tf in ["15m", "1h", "4h"]:
            end_date = pd.Timestamp.utcnow()
            start_date = end_date - pd.Timedelta(days=60)
        else:
            start_date = pd.Timestamp("2024-01-01")
            end_date = pd.Timestamp("2025-12-31")
        start = start_date.strftime("%Y-%m-%d")
        end = end_date.strftime("%Y-%m-%d")
        result = run_backtest(symbol, start, end, tf)
        logger.info(str(result))
        json_path = f"custom_backtest_{name}.json"
        result.to_json(json_path)
        logger.info(f"Saved results to {json_path}")
