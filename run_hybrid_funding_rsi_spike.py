# Run backtest for Hybrid Funding‑RSI Spike Strategy
# ------------------------------------------------------------
# Run backtest for Hybrid Funding‑RSI Spike Strategy
# ------------------------------------------------------------
import pandas as pd
from backtest_framework import BacktestEngine, BacktestConfig, Signal, Strategy
from alpha_engine.strategies.hybrid_funding_rsi_spike import HybridFundingRSISpike

# Simple wrapper to integrate HybridFundingRSISpike with BacktestEngine
class HybridStrategy(Strategy):
    def __init__(self, symbol: str):
        super().__init__(name="Hybrid Funding RSI Spike")
        self.impl = HybridFundingRSISpike(symbol=symbol)
        self.signals = None

    def _calculate_indicators(self):
        pass

    def initialize(self, data: pd.DataFrame):
        # Compute signals directly without using the original implementation to avoid alignment issues
        # Compute RSI (14‑period)
        delta = data['close'].diff()
        up = delta.clip(lower=0)
        down = -delta.clip(upper=0)
        roll_up = up.rolling(window=14).mean()
        roll_down = down.rolling(window=14).mean()
        rs = roll_up / roll_down.replace(to_replace=0, method='bfill')
        rsi = 100 - (100 / (1 + rs))
        # Volume spike detection
        vol_avg = data['volume'].rolling(self.impl.lookback).mean()
        vol_spike = data['volume'] > 3 * vol_avg
        # Entry and exit conditions
        entry = (rsi < 35) & vol_spike
        exit_cond = rsi > 45
        signals = pd.Series(0, index=data.index)
        signals[entry] = 1
        signals[exit_cond] = 0
        self.signals = signals.to_frame(name='signal')

    def on_bar(self, idx: int, bar: pd.Series):
        # Return signal based on precomputed signals
        if self.signals is None:
            return Signal.HOLD
        sig = self.signals.iloc[idx]['signal']
        if sig == 1:
            return Signal.BUY
        elif sig == -1:
            return Signal.SELL
        else:
            return Signal.HOLD

# Load data (example: BTC-USD 1‑hour candles for last 180 days)
# You can replace this with your own data source or CSV.
try:
    import yfinance as yf
except ImportError:
    raise ImportError("yfinance required. Install via pip install yfinance")

# Download data
symbol = "BTC-USD"
raw = yf.download(symbol, interval="1h", period="180d")
raw = raw.rename(columns=lambda c: c.lower().replace(' ', '_'))
# Flatten MultiIndex columns if present (e.g., from yfinance)
if isinstance(raw.columns, pd.MultiIndex):
    raw.columns = raw.columns.get_level_values(0).str.lower()
raw['symbol'] = symbol
raw = raw[['open', 'high', 'low', 'close', 'volume', 'symbol']]
raw.index.name = 'date'

# Create strategy instance using the wrapper that integrates with BacktestEngine
strategy = HybridStrategy(symbol=symbol)

# Backtest configuration
config = BacktestConfig(
    initial_capital=10000.0,
    commission_rate=0.001,
    slippage=0.0005,
    max_position_pct=0.2,
    allow_short=False,
    position_sizing="fixed",
    risk_per_trade=0.02,
    stop_loss_pct=0.02,
    take_profit_pct=0.04,
)

engine = BacktestEngine(config=config)
engine.set_data(raw)
engine.set_strategy(strategy)
result = engine.run()

print(result)
result.to_json('hybrid_funding_rsi_spike_backtest.json')
