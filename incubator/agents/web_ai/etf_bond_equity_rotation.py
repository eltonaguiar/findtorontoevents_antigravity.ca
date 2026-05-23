"""
ETFBondEquityRotation - Baby Strat
=====================================

Created by: web_ai
Date: 2026-04-01

Strategy Logic:
- LONG SPY when SPY RSI(14) > 50 AND TLT RSI(14) < 50 (risk-on)
- LONG TLT when SPY RSI(14) < 50 AND TLT RSI(14) > 50 (risk-off)
- TP = 2.0x ATR, SL = 1.2x ATR

Instruments: SPY (equities), TLT (long-term bonds)

Unique Value Proposition:
Classic risk-on/risk-off rotation using RSI divergence between stocks and bonds.
When equities show relative strength (RSI > 50) and bonds weaken (RSI < 50),
the strategy goes long equities, and vice versa. Captures macro regime shifts.
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


class ETFBondEquityRotationStrategy:
    """
    Bond-equity rotation between TLT and SPY based on RSI divergence.

    Required methods:
    - __init__(self, params): Initialize parameters
    - generate_signals(self, spy_data, tlt_data): Return List[Signal]
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.rsi_period = self.params.get('rsi_period', 14)
        self.atr_period = self.params.get('atr_period', 14)
        self.rsi_threshold = self.params.get('rsi_threshold', 50)
        self.tp_atr = self.params.get('tp_atr', 2.0)
        self.sl_atr = self.params.get('sl_atr', 1.2)

    def generate_signals(self, data_dict: Dict[str, pd.DataFrame], symbol: str = "ROTATION") -> List[Signal]:
        """
        Args:
            data_dict: {'SPY': DataFrame, 'TLT': DataFrame}
        """
        if 'SPY' not in data_dict or 'TLT' not in data_dict:
            return []

        spy_data = data_dict['SPY']
        tlt_data = data_dict['TLT']

        min_len = self.rsi_period + self.atr_period + 10
        if len(spy_data) < min_len or len(tlt_data) < min_len:
            return []

        spy_rsi = self._calculate_rsi(spy_data['close'], self.rsi_period).iloc[-1]
        tlt_rsi = self._calculate_rsi(tlt_data['close'], self.rsi_period).iloc[-1]

        if pd.isna(spy_rsi) or pd.isna(tlt_rsi):
            return []

        signals = []

        # Risk-on: LONG SPY
        if spy_rsi > self.rsi_threshold and tlt_rsi < self.rsi_threshold:
            spy_price = spy_data['close'].iloc[-1]
            spy_atr = self._calculate_atr(spy_data).iloc[-1]
            if pd.isna(spy_atr):
                return []
            rsi_spread = spy_rsi - tlt_rsi
            confidence = min(0.4 + rsi_spread / 100 * 0.5, 0.90)
            signals.append(Signal(
                symbol="SPY",
                direction="BUY",
                confidence=round(confidence, 2),
                entry_price=round(spy_price, 2),
                take_profit=round(spy_price + spy_atr * self.tp_atr, 2),
                stop_loss=round(spy_price - spy_atr * self.sl_atr, 2),
                reason=f"RiskOn SPY_RSI={spy_rsi:.1f}>50 TLT_RSI={tlt_rsi:.1f}<50"
            ))

        # Risk-off: LONG TLT
        elif spy_rsi < self.rsi_threshold and tlt_rsi > self.rsi_threshold:
            tlt_price = tlt_data['close'].iloc[-1]
            tlt_atr = self._calculate_atr(tlt_data).iloc[-1]
            if pd.isna(tlt_atr):
                return []
            rsi_spread = tlt_rsi - spy_rsi
            confidence = min(0.4 + rsi_spread / 100 * 0.5, 0.90)
            signals.append(Signal(
                symbol="TLT",
                direction="BUY",
                confidence=round(confidence, 2),
                entry_price=round(tlt_price, 2),
                take_profit=round(tlt_price + tlt_atr * self.tp_atr, 2),
                stop_loss=round(tlt_price - tlt_atr * self.sl_atr, 2),
                reason=f"RiskOff SPY_RSI={spy_rsi:.1f}<50 TLT_RSI={tlt_rsi:.1f}>50"
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

    end = datetime.now()
    start = end - timedelta(days=730)

    print(f"Downloading SPY and TLT ({start.date()} to {end.date()})...")
    all_data = {}
    for sym in ['SPY', 'TLT']:
        df = yf.download(sym, start=start, end=end, progress=False)
        if hasattr(df.columns, 'levels') and df.columns.nlevels > 1:
            df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]
        df = df.reset_index()
        all_data[sym] = df
        print(f"  {sym}: {len(df)} bars")

    strategy = ETFBondEquityRotationStrategy()

    trades = []
    position = None
    ref_len = min(len(all_data['SPY']), len(all_data['TLT']))

    for i in range(40, ref_len):
        # Check TP/SL on open position
        if position is not None:
            sym = position['symbol']
            cp = all_data[sym]['close'].iloc[i]
            if position['direction'] == 'BUY':
                if cp >= position['tp']:
                    trades.append({'symbol': sym, 'direction': 'BUY', 'entry': position['entry'],
                                   'exit': position['tp'], 'pnl_pct': (position['tp'] - position['entry']) / position['entry'] * 100})
                    position = None
                elif cp <= position['sl']:
                    trades.append({'symbol': sym, 'direction': 'BUY', 'entry': position['entry'],
                                   'exit': position['sl'], 'pnl_pct': (position['sl'] - position['entry']) / position['entry'] * 100})
                    position = None
            if position is not None:
                continue

        # Generate new signals
        window_data = {sym: all_data[sym].iloc[:i+1].copy() for sym in ['SPY', 'TLT']}
        sigs = strategy.generate_signals(window_data)
        if sigs:
            s = sigs[0]
            position = {'symbol': s.symbol, 'direction': s.direction, 'entry': s.entry_price,
                        'tp': s.take_profit, 'sl': s.stop_loss}

    print(f"\n=== Bond-Equity Rotation Backtest ===")
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
        spy_trades = [t for t in trades if t['symbol'] == 'SPY']
        tlt_trades = [t for t in trades if t['symbol'] == 'TLT']
        print(f"SPY trades: {len(spy_trades)} | TLT trades: {len(tlt_trades)}")
        for sym_name, sym_trades in [('SPY', spy_trades), ('TLT', tlt_trades)]:
            if sym_trades:
                sym_pnl = sum(t['pnl_pct'] for t in sym_trades)
                sym_wr = len([t for t in sym_trades if t['pnl_pct'] > 0]) / len(sym_trades) * 100
                print(f"  {sym_name}: total={sym_pnl:.2f}%, WR={sym_wr:.1f}%")
    else:
        print("No trades generated.")
    if position:
        print(f"Open position: {position['direction']} {position['symbol']} @ {position['entry']:.2f}")
