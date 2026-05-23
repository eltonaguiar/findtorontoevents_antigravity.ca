# Hybrid Funding‑RSI Spike Strategy
# ------------------------------------------------------------
# This strategy combines extreme negative funding rates with an oversold
# RSI condition and a volume surge to capture short‑term crypto spikes.
# ------------------------------------------------------------
import pandas as pd
from alpha_engine.backtest.engine import BacktestEngine

class HybridFundingRSISpike:
    """Long when funding < -0.01% AND RSI(14) < 35 AND volume > 3× avg.
    Exit when funding > 0.01% OR RSI(14) > 45 or profit target hit.
    """
    def __init__(self, symbol: str, lookback: int = 24):
        self.name = "Hybrid Funding RSI Spike"
        self.symbol = symbol
        self.lookback = lookback  # hours to look back for avg volume
        self.position = None
        self.entry_price = None
        self.take_profit_mult = 2.0
        self.stop_loss_mult = 1.5

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Return a DataFrame with a 'signal' column (1=LONG, -1=SHORT, 0=FLAT)."""
        # Compute RSI (14‑period) manually
        delta = data['close'].diff()
        up = delta.clip(lower=0)
        down = -delta.clip(upper=0)
        roll_up = up.rolling(window=14).mean()
        roll_down = down.rolling(window=14).mean()
        rs = roll_up / roll_down.replace(to_replace=0, method='bfill')
        data['rsi'] = 100 - (100 / (1 + rs))
        # Volume spike detection
        data['vol_avg'] = data['volume'].rolling(self.lookback).mean()
        # Use numpy arrays to avoid pandas alignment issues when comparing
        # Compute volume spike using row-wise comparison to avoid shape issues
        data['vol_spike'] = data.apply(lambda row: row['volume'] > 3 * row['vol_avg'], axis=1)

        # Entry condition: RSI < 35 and volume spike
        entry = (data['rsi'] < 35) & data['vol_spike']
        # Exit condition: RSI > 45
        exit_cond = data['rsi'] > 45

        signals = pd.Series(0, index=data.index)
        signals[entry] = 1
        signals[exit_cond] = 0
        return signals.to_frame(name='signal')

    def backtest(self, data: pd.DataFrame):
        signals = self.generate_signals(data)
        engine = BacktestEngine(symbol=self.symbol, data=data, signals=signals)
        engine.run(take_profit_mult=self.take_profit_mult, stop_loss_mult=self.stop_loss_mult)
        return engine.results

# Example usage (run via backtest_framework):
# if __name__ == "__main__":
#     import yfinance as yf
#     df = yf.download("BTC-USD", interval="1h", period="180d")
#     strat = HybridFundingRSISpike(symbol="BTC-USD")
#     res = strat.backtest(df)
#     print(res.summary())
