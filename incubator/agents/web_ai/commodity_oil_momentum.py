"""
CommodityOilMomentum - Baby Strat
===================================

Created by: web_ai
Date: 2026-04-01

Strategy Logic:
- LONG when EMA(9) crosses above EMA(21) AND ADX > 20 AND volume > 1.5x avg
- SHORT when EMA(9) crosses below EMA(21) AND ADX > 20 AND volume > 1.5x avg
- TP = 2.5x ATR, SL = 1.5x ATR

Instrument: USO ETF (Oil proxy)

Unique Value Proposition:
Triple-confirmation momentum on oil: EMA crossover for direction, ADX for
trend strength, volume surge for institutional participation. Filters out
low-conviction crossovers in choppy oil markets.
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


class CommodityOilMomentumStrategy:
    """
    Oil (USO) momentum using EMA crossover + ADX + volume confirmation.

    Required methods:
    - __init__(self, params): Initialize parameters
    - generate_signals(self, data, symbol): Return List[Signal]
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.ema_fast = self.params.get('ema_fast', 9)
        self.ema_slow = self.params.get('ema_slow', 21)
        self.adx_period = self.params.get('adx_period', 14)
        self.adx_threshold = self.params.get('adx_threshold', 20)
        self.vol_multiplier = self.params.get('vol_multiplier', 1.5)
        self.vol_lookback = self.params.get('vol_lookback', 20)
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_atr = self.params.get('tp_atr', 2.5)
        self.sl_atr = self.params.get('sl_atr', 1.5)

    def generate_signals(self, data: pd.DataFrame, symbol: str = "USO") -> List[Signal]:
        min_len = max(self.ema_slow, self.adx_period * 2, self.vol_lookback) + 10
        if len(data) < min_len:
            return []

        ema_fast = data['close'].ewm(span=self.ema_fast, adjust=False).mean()
        ema_slow = data['close'].ewm(span=self.ema_slow, adjust=False).mean()
        adx = self._calculate_adx(data, self.adx_period)
        atr = self._calculate_atr(data)
        vol_avg = data['volume'].rolling(self.vol_lookback).mean()

        current_price = data['close'].iloc[-1]
        current_atr = atr.iloc[-1]
        current_adx = adx.iloc[-1]
        current_vol = data['volume'].iloc[-1]
        current_vol_avg = vol_avg.iloc[-1]

        # EMA crossover detection (current bar vs previous)
        ema_fast_now = ema_fast.iloc[-1]
        ema_slow_now = ema_slow.iloc[-1]
        ema_fast_prev = ema_fast.iloc[-2]
        ema_slow_prev = ema_slow.iloc[-2]

        bullish_cross = ema_fast_prev <= ema_slow_prev and ema_fast_now > ema_slow_now
        bearish_cross = ema_fast_prev >= ema_slow_prev and ema_fast_now < ema_slow_now

        if pd.isna(current_adx) or pd.isna(current_atr) or pd.isna(current_vol_avg):
            return []

        vol_confirmed = current_vol > self.vol_multiplier * current_vol_avg
        adx_confirmed = current_adx > self.adx_threshold

        signals = []

        if bullish_cross and adx_confirmed and vol_confirmed:
            confidence = min(
                (current_adx - self.adx_threshold) / 30 * 0.5 + 0.4,
                0.95
            )
            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 2),
                entry_price=round(current_price, 2),
                take_profit=round(current_price + current_atr * self.tp_atr, 2),
                stop_loss=round(current_price - current_atr * self.sl_atr, 2),
                reason=f"OilMom LONG EMA9x21 ADX={current_adx:.1f} vol={current_vol/current_vol_avg:.1f}x"
            ))

        elif bearish_cross and adx_confirmed and vol_confirmed:
            confidence = min(
                (current_adx - self.adx_threshold) / 30 * 0.5 + 0.4,
                0.95
            )
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 2),
                entry_price=round(current_price, 2),
                take_profit=round(current_price - current_atr * self.tp_atr, 2),
                stop_loss=round(current_price + current_atr * self.sl_atr, 2),
                reason=f"OilMom SHORT EMA9x21 ADX={current_adx:.1f} vol={current_vol/current_vol_avg:.1f}x"
            ))

        return signals

    def _calculate_adx(self, data: pd.DataFrame, period: int) -> pd.Series:
        high, low, close = data['high'], data['low'], data['close']
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

        tr = pd.concat([
            high - low,
            abs(high - close.shift()),
            abs(low - close.shift())
        ], axis=1).max(axis=1)

        atr = tr.rolling(period).mean()
        plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(period).mean()
        return adx

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

    symbol = "USO"
    end = datetime.now()
    start = end - timedelta(days=730)
    print(f"Downloading {symbol} data ({start.date()} to {end.date()})...")
    df = yf.download(symbol, start=start, end=end, progress=False)
    if hasattr(df.columns, 'levels') and df.columns.nlevels > 1:
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    df = df.reset_index()

    strategy = CommodityOilMomentumStrategy()
    atr = strategy._calculate_atr(df)

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

    print(f"\n=== {symbol} Oil Momentum Backtest ===")
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
