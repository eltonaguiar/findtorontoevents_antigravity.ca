import pandas as pd
import numpy as np
from collections import deque

class GridTrader:
    def __init__(self, initial_cash=100000, grid_size=0.005, num_levels=10):
        self.initial_cash = initial_cash
        self.grid_size = grid_size
        self.num_levels = num_levels
        self.reset()

    def reset(self):
        self.cash = self.initial_cash
        self.realized_pnl = 0.0
        self.open_longs = deque()
        self.open_shorts = deque()
        self.num_fills_buy = 0
        self.num_fills_sell = 0
        self.grid_center = None

    def set_center(self, price):
        if self.grid_center is None:
            self.grid_center = price

    def on_bar(self, high, low, close):
        self.set_center(close)
        center = self.grid_center
        if center is None:
            return

        # Simulate buy fills at grid levels
        for i in range(1, self.num_levels + 1):
            buy_price = center * (1 - i * self.grid_size)
            if low <= buy_price:
                self.fill_buy(buy_price)

        # Simulate sell fills at grid levels
        for i in range(1, self.num_levels + 1):
            sell_price = center * (1 + i * self.grid_size)
            if high >= sell_price:
                self.fill_sell(sell_price)

    def fill_buy(self, fill_price):
        self.num_fills_buy += 1
        if self.open_shorts:
            short_entry = self.open_shorts.popleft()
            self.realized_pnl += short_entry - fill_price
        else:
            self.open_longs.append(fill_price)
        self.cash -= fill_price

    def fill_sell(self, fill_price):
        self.num_fills_sell += 1
        if self.open_longs:
            long_entry = self.open_longs.popleft()
            self.realized_pnl += fill_price - long_entry
        else:
            self.open_shorts.append(fill_price)
        self.cash += fill_price

    def current_equity(self, close):
        long_unreal = sum(close - e for e in self.open_longs)
        short_unreal = sum(e - close for e in self.open_shorts)
        return self.cash + long_unreal + short_unreal

def generate_synthetic_data(n_bars=1000, start_price=100, volatility=0.01):
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

def test_grid():
    df = generate_synthetic_data(1000)
    trader = GridTrader()
    equities = []
    for _, row in df.iterrows():
        trader.on_bar(row['high'], row['low'], row['close'])
        equities.append(trader.current_equity(row['close']))
    total_return = (equities[-1] / trader.initial_cash - 1) * 100
    returns = pd.Series(equities).pct_change().dropna()
    sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if len(returns) > 0 and returns.std() != 0 else 0
    print("Grid Trading Incubator Test on Synthetic Data (1000 bars, seed=42):")
    print(f"Total Return: {total_return:.2f}%")
    print(f"Sharpe Ratio (annualized assuming daily bars): {sharpe:.2f}")
    print(f"Final Equity: {equities[-1]:.2f}")
    print(f"Realized PnL: {trader.realized_pnl:.2f}")
    print(f"Buy Fills: {trader.num_fills_buy}, Sell Fills: {trader.num_fills_sell}")
    print(f"Final Open Longs: {len(trader.open_longs)}, Open Shorts: {len(trader.open_shorts)}")

if __name__ == "__main__":
    test_grid()