"""
CommodityGoldMeanReversion - Baby Strat
========================================

Created by: web_ai
Date: 2026-04-01

Strategy Logic:
- LONG when RSI(14) < 30 AND price < lower Bollinger Band(20, 2)
- SHORT when RSI(14) > 70 AND price > upper Bollinger Band(20, 2)
- TP = 2.0x ATR, SL = 1.5x ATR

Instrument: GLD ETF (Gold proxy)

Unique Value Proposition:
Mean-reversion on gold using dual-confirmation (RSI extremes + Bollinger Band
breach). Gold tends to mean-revert in ranging regimes; the dual filter reduces
false signals compared to single-indicator approaches.
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


class CommodityGoldMeanReversionStrategy:
    """
    Gold (GLD) mean reversion using RSI + Bollinger Bands.

    Required methods:
    - __init__(self, params): Initialize parameters
    - generate_signals(self, data, symbol): Return List[Signal]
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.rsi_period = self.params.get('rsi_period', 14)
        self.bb_period = self.params.get('bb_period', 20)
        self.bb_std = self.params.get('bb_std', 2.0)
        self.atr_period = self.params.get('atr_period', 14)
        self.rsi_oversold = self.params.get('rsi_oversold', 30)
        self.rsi_overbought = self.params.get('rsi_overbought', 70)
        self.tp_atr = self.params.get('tp_atr', 2.0)
        self.sl_atr = self.params.get('sl_atr', 1.5)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "GLD") -> List[Signal]:
        min_len = max(self.bb_period, self.rsi_period, self.atr_period) + 10
        if len(data) < min_len:
            return []

        rsi = self._calculate_rsi(data['close'], self.rsi_period)
        atr = self._calculate_atr(data)
        bb_mid = data['close'].rolling(self.bb_period).mean()
        bb_std = data['close'].rolling(self.bb_period).std()
        bb_upper = bb_mid + self.bb_std * bb_std
        bb_lower = bb_mid - self.bb_std * bb_std

        current_rsi = rsi.iloc[-1]
        current_price = data['close'].iloc[-1]
        current_atr = atr.iloc[-1]
        current_bb_upper = bb_upper.iloc[-1]
        current_bb_lower = bb_lower.iloc[-1]

        if pd.isna(current_rsi) or pd.isna(current_atr) or pd.isna(current_bb_upper):
            return []

        signals = []

        # LONG: RSI < 30 AND price < lower BB
        if current_rsi < self.rsi_oversold and current_price < current_bb_lower:
            confidence = min(
                (self.rsi_oversold - current_rsi) / self.rsi_oversold * 0.7 + 0.3,
                0.95
            )
            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 2),
                entry_price=round(current_price, 2),
                take_profit=round(current_price + current_atr * self.tp_atr, 2),
                stop_loss=round(current_price - current_atr * self.sl_atr, 2),
                reason=f"GoldMR LONG RSI={current_rsi:.1f} price<lowerBB({current_bb_lower:.2f})"
            ))

        # SHORT: RSI > 70 AND price > upper BB
        elif current_rsi > self.rsi_overbought and current_price > current_bb_upper:
            confidence = min(
                (current_rsi - self.rsi_overbought) / (100 - self.rsi_overbought) * 0.7 + 0.3,
                0.95
            )
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 2),
                entry_price=round(current_price, 2),
                take_profit=round(current_price - current_atr * self.tp_atr, 2),
                stop_loss=round(current_price + current_atr * self.sl_atr, 2),
                reason=f"GoldMR SHORT RSI={current_rsi:.1f} price>upperBB({current_bb_upper:.2f})"
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

    symbol = "GLD"
    end = datetime.now()
    start = end - timedelta(days=730)
    print(f"Downloading {symbol} data ({start.date()} to {end.date()})...")
    df = yf.download(symbol, start=start, end=end, progress=False)
    if hasattr(df.columns, 'levels') and df.columns.nlevels > 1:
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    df = df.reset_index()

    strategy = CommodityGoldMeanReversionStrategy()
    atr = strategy._calculate_atr(df)

    # Walk-forward backtest
    trades = []
    position = None
    for i in range(50, len(df)):
        window = df.iloc[:i+1].copy()
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

        sigs = strategy.generate_signals(window, symbol)
        if sigs:
            s = sigs[0]
            position = {'direction': s.direction, 'entry': s.entry_price,
                        'tp': s.take_profit, 'sl': s.stop_loss}

    print(f"\n=== {symbol} Gold Mean Reversion Backtest ===")
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
        print(f"Profit factor: {abs(sum(t['pnl_pct'] for t in wins) / sum(t['pnl_pct'] for t in losses)):.2f}" if losses else "Profit factor: inf")
        longs = [t for t in trades if t['direction'] == 'BUY']
        shorts = [t for t in trades if t['direction'] == 'SELL']
        print(f"Longs: {len(longs)} | Shorts: {len(shorts)}")
    else:
        print("No trades generated.")
    if position:
        print(f"Open position: {position['direction']} @ {position['entry']:.2f}")
