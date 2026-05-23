import pandas as pd
import numpy as np
import ta
from ta.volatility import BollingerBands, AverageTrueRange

class BBMeanRevTrader:
    def __init__(self, initial_cash=100000, risk_per_trade=0.01):
        self.initial_cash = initial_cash
        self.risk_per_trade = risk_per_trade
        self.reset()

    def reset(self):
        self.cash = self.initial_cash
        self.position = 0.0
        self.entry_price = 0.0
        self.sl_price = 0.0
        self.realized_pnl = 0.0
        self.trades = 0

    def on_bar(self, high, low, close, upper, lower, mid, atr_val):
        unreal_pnl = self.position * (close - self.entry_price) if abs(self.position) > 1e-8 else 0.0
        current_equity = self.cash + unreal_pnl

        if abs(self.position) < 1e-8:  # flat
            if pd.isna(lower) or pd.isna(upper) or pd.isna(atr_val) or atr_val <= 0:
                return
            if close < lower:
                sl_dist = 2 * atr_val
                size = (self.risk_per_trade * current_equity) / sl_dist
                self.position = size
                self.entry_price = close
                self.sl_price = close - sl_dist
                self.trades += 1
            elif close > upper:
                sl_dist = 2 * atr_val
                size = (self.risk_per_trade * current_equity) / sl_dist
                self.position = -size
                self.entry_price = close
                self.sl_price = close + sl_dist
                self.trades += 1
        else:
            sl_hit_long = self.position > 0 and low <= self.sl_price
            sl_hit_short = self.position < 0 and high >= self.sl_price
            sl_hit = sl_hit_long or sl_hit_short
            exit_meanrev_long = self.position > 0 and close > mid
            exit_meanrev_short = self.position < 0 and close < mid
            exit_meanrev = exit_meanrev_long or exit_meanrev_short
            if sl_hit or exit_meanrev:
                exit_price = self.sl_price if sl_hit else close
                trade_pnl = self.position * (exit_price - self.entry_price)
                self.realized_pnl += trade_pnl
                self.cash += self.position * exit_price
                self.position = 0.0
                self.entry_price = 0.0
                self.sl_price = 0.0

    def current_equity(self, close):
        unreal = self.position * (close - self.entry_price) if abs(self.position) > 1e-8 else 0.0
        return self.cash + unreal

def generate_synthetic_data(n_bars=2000, start_price=100, volatility=0.01):
    np.random.seed(42)
    returns = np.random.normal(0, volatility, n_bars)
    close = start_price * np.exp(np.cumsum(returns))
    noise = np.random.normal(0, volatility * 2, n_bars)
    high = np.maximum(close * (1 + np.abs(noise)), close)
    low = np.minimum(close * (1 - np.abs(noise)), close)
    open_prices = np.roll(close, 1)
    open_prices[0] = start_price
    df = pd.DataFrame({
        'open': open_prices,
        'high': high,
        'low': low,
        'close': close,
        'volume': np.random.randint(1000, 10000, n_bars)
    })
    return df

def test_bb():
    df = generate_synthetic_data(2000)
    bbands = BollingerBands(close=df['close'], window=20, window_dev=2)
    df['bb_lower'] = bbands.bollinger_lband()
    df['bb_mid'] = bbands.bollinger_mavg()
    df['bb_upper'] = bbands.bollinger_hband()
    atr_ind = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14)
    df['atr'] = atr_ind.average_true_range()
    trader = BBMeanRevTrader()
    equities = []
    for _, row in df.iterrows():
        if pd.isna(row['bb_lower']) or pd.isna(row['atr']):
            equities.append(trader.current_equity(row['close']))
            continue
        trader.on_bar(row['high'], row['low'], row['close'], row['bb_upper'], row['bb_lower'], row['bb_mid'], row['atr'])
        equities.append(trader.current_equity(row['close']))
    total_return = (equities[-1] / trader.initial_cash - 1) * 100
    returns = pd.Series(equities).pct_change().dropna()
    sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if len(returns) > 0 and returns.std() != 0 else 0
    print("Bollinger Bands Mean Reversion Incubator Test on Synthetic Data (2000 bars, seed=42):")
    print(f"Total Return: {total_return:.2f}%")
    print(f"Sharpe Ratio (annualized assuming daily bars): {sharpe:.2f}")
    print(f"Final Equity: {equities[-1]:.2f}")
    print(f"Realized PnL: {trader.realized_pnl:.2f}")
    print(f"Number of Trades: {trader.trades}")

if __name__ == "__main__":
    test_bb()