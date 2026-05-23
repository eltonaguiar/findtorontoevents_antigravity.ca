"""
CommoditySeasonalSilver - Baby Strat
=======================================

Created by: web_ai
Date: 2026-04-01

Strategy Logic:
- Silver (SLV ETF) with seasonal bias
- LONG SLV when month in [Sep-Feb] AND RSI(14) < 50 AND price > SMA(50)
- SHORT SLV when month in [Mar-Aug] AND RSI(14) > 60
- TP = 2.5x ATR, SL = 1.5x ATR

Instrument: SLV ETF (Silver proxy)

Unique Value Proposition:
Silver has well-documented seasonal strength Sep-Feb (industrial demand,
jewellery season, Indian festivals). This strategy combines seasonal timing
with RSI and trend confirmation to trade with the seasonal wind at its back.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class Signal:
    """A trading signal - required return type."""
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class CommoditySeasonalSilverStrategy:
    """
    Silver (SLV) seasonal + RSI + trend strategy.

    Required methods:
    - __init__(self, params): Initialize parameters
    - generate_signals(self, data, symbol): Return List[Signal]
    """

    STRONG_MONTHS = [9, 10, 11, 12, 1, 2]
    WEAK_MONTHS = [3, 4, 5, 6, 7, 8]

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.rsi_period = self.params.get('rsi_period', 14)
        self.sma_period = self.params.get('sma_period', 50)
        self.atr_period = self.params.get('atr_period', 14)
        self.long_rsi_max = self.params.get('long_rsi_max', 50)
        self.short_rsi_min = self.params.get('short_rsi_min', 60)
        self.tp_atr = self.params.get('tp_atr', 2.5)
        self.sl_atr = self.params.get('sl_atr', 1.5)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "SLV",
                         current_date: Optional[pd.Timestamp] = None) -> List[Signal]:
        min_len = max(self.sma_period, self.rsi_period, self.atr_period) + 10
        if len(data) < min_len:
            return []

        rsi = self._calculate_rsi(data['close'], self.rsi_period)
        sma = data['close'].rolling(self.sma_period).mean()
        atr = self._calculate_atr(data)

        current_rsi = rsi.iloc[-1]
        current_price = data['close'].iloc[-1]
        current_sma = sma.iloc[-1]
        current_atr = atr.iloc[-1]

        if pd.isna(current_rsi) or pd.isna(current_sma) or pd.isna(current_atr):
            return []

        # Determine current month
        if current_date is not None:
            month = current_date.month
        elif 'date' in data.columns:
            month = pd.to_datetime(data['date'].iloc[-1]).month
        elif isinstance(data.index[-1], pd.Timestamp):
            month = data.index[-1].month
        else:
            month = pd.Timestamp.now().month

        signals = []

        # LONG: strong season + RSI < 50 + above SMA(50)
        if month in self.STRONG_MONTHS and current_rsi < self.long_rsi_max and current_price > current_sma:
            confidence = min(
                0.4 + (self.long_rsi_max - current_rsi) / self.long_rsi_max * 0.4,
                0.90
            )
            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 2),
                entry_price=round(current_price, 2),
                take_profit=round(current_price + current_atr * self.tp_atr, 2),
                stop_loss=round(current_price - current_atr * self.sl_atr, 2),
                reason=f"SeasonalSilver LONG month={month} RSI={current_rsi:.1f} price>SMA50({current_sma:.2f})"
            ))

        # SHORT: weak season + RSI > 60
        elif month in self.WEAK_MONTHS and current_rsi > self.short_rsi_min:
            confidence = min(
                0.35 + (current_rsi - self.short_rsi_min) / (100 - self.short_rsi_min) * 0.4,
                0.85
            )
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 2),
                entry_price=round(current_price, 2),
                take_profit=round(current_price - current_atr * self.tp_atr, 2),
                stop_loss=round(current_price + current_atr * self.sl_atr, 2),
                reason=f"SeasonalSilver SHORT month={month} RSI={current_rsi:.1f}"
            ))

        return signals

    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_atr(self, data: pd.DataFrame) -> pd.Series:
        high, low, close = data['high'], data['low'], data['close']
        tr = pd.concat([
            high - low,
            abs(high - close.shift()),
            abs(low - close.shift())
        ], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()


# ==============================================================================
# BACKTEST with yfinance
# ==============================================================================

if __name__ == "__main__":
    import yfinance as yf
    from datetime import datetime, timedelta

    symbol = "SLV"
    end = datetime.now()
    start = end - timedelta(days=730)
    print(f"Downloading {symbol} data ({start.date()} to {end.date()})...")
    df = yf.download(symbol, start=start, end=end, progress=False)
    if hasattr(df.columns, 'levels') and df.columns.nlevels > 1:
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    df = df.reset_index()

    strategy = CommoditySeasonalSilverStrategy()

    trades = []
    position = None
    for i in range(60, len(df)):
        window = df.iloc[:i+1].copy()
        current_date = pd.to_datetime(df['date'].iloc[i]) if 'date' in df.columns else None

        if position is not None:
            cp = df['close'].iloc[i]
            if position['direction'] == 'BUY':
                if cp >= position['tp']:
                    trades.append({'direction': 'BUY', 'entry': position['entry'],
                                   'exit': position['tp'], 'pnl_pct': (position['tp'] - position['entry']) / position['entry'] * 100})
                    position = None
                elif cp <= position['sl']:
                    trades.append({'direction': 'BUY', 'entry': position['entry'],
                                   'exit': position['sl'], 'pnl_pct': (position['sl'] - position['entry']) / position['entry'] * 100})
                    position = None
            else:
                if cp <= position['tp']:
                    trades.append({'direction': 'SELL', 'entry': position['entry'],
                                   'exit': position['tp'], 'pnl_pct': (position['entry'] - position['tp']) / position['entry'] * 100})
                    position = None
                elif cp >= position['sl']:
                    trades.append({'direction': 'SELL', 'entry': position['entry'],
                                   'exit': position['sl'], 'pnl_pct': (position['entry'] - position['sl']) / position['entry'] * 100})
                    position = None
            continue

        sigs = strategy.generate_signals(window, symbol, current_date=current_date)
        if sigs:
            s = sigs[0]
            position = {'direction': s.direction, 'entry': s.entry_price,
                        'tp': s.take_profit, 'sl': s.stop_loss}

    print(f"\n=== {symbol} Seasonal Silver Backtest ===")
    print(f"Period: {df['date'].iloc[0].date() if 'date' in df.columns else start.date()} to {df['date'].iloc[-1].date() if 'date' in df.columns else end.date()}")
    print(f"Total bars: {len(df)}")
    print(f"Total trades: {len(trades)}")
    if trades:
        wins = [t for t in trades if t['pnl_pct'] > 0]
        losses = [t for t in trades if t['pnl_pct'] <= 0]
        total_pnl = sum(t['pnl_pct'] for t in trades)
        avg_pnl = total_pnl / len(trades)
        win_rate = len(wins) / len(trades) * 100
        avg_win = np.mean([t['pnl_pct'] for t in wins]) if wins else 0
        avg_loss = np.mean([t['pnl_pct'] for t in losses]) if losses else 0
        print(f"Win rate: {win_rate:.1f}%")
        print(f"Total PnL: {total_pnl:.2f}%")
        print(f"Avg PnL/trade: {avg_pnl:.2f}%")
        print(f"Avg win: {avg_win:.2f}% | Avg loss: {avg_loss:.2f}%")
        if losses:
            print(f"Profit factor: {abs(sum(t['pnl_pct'] for t in wins) / sum(t['pnl_pct'] for t in losses)):.2f}")
        longs = [t for t in trades if t['direction'] == 'BUY']
        shorts = [t for t in trades if t['direction'] == 'SELL']
        print(f"Longs: {len(longs)} | Shorts: {len(shorts)}")
        # Seasonal breakdown
        print("\nNote: Silver strong months = Sep-Feb, weak months = Mar-Aug")
    else:
        print("No trades generated.")
    if position:
        print(f"Open position: {position['direction']} @ {position['entry']:.2f}")
