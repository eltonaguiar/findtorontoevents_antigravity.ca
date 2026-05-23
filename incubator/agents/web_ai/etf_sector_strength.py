"""
ETFSectorStrength - Baby Strat
================================

Created by: web_ai
Date: 2026-04-01

Strategy Logic:
- Rank sector ETFs (XLK, XLE, XLF, XLV, XLI, XLP, XLU, XLRE, XLB, XLC) by 20-day return
- LONG top 2 sectors when their RSI(14) < 65
- SHORT bottom 2 sectors when their RSI(14) > 35
- TP = 2.0x ATR, SL = 1.5x ATR

Unique Value Proposition:
Sector rotation captures relative strength across the equity market. By going
long the strongest sectors and shorting the weakest, the strategy is roughly
market-neutral and profits from sector dispersion.
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


class ETFSectorStrengthStrategy:
    """
    Sector rotation across SPDR sector ETFs ranked by momentum.

    Required methods:
    - __init__(self, params): Initialize parameters
    - generate_signals(self, data_dict, symbol): Return List[Signal]
    """

    SECTORS = ['XLK', 'XLE', 'XLF', 'XLV', 'XLI', 'XLP', 'XLU', 'XLRE', 'XLB', 'XLC']

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.return_period = self.params.get('return_period', 20)
        self.rsi_period = self.params.get('rsi_period', 14)
        self.atr_period = self.params.get('atr_period', 14)
        self.long_rsi_max = self.params.get('long_rsi_max', 65)
        self.short_rsi_min = self.params.get('short_rsi_min', 35)
        self.top_n = self.params.get('top_n', 2)
        self.bottom_n = self.params.get('bottom_n', 2)
        self.tp_atr = self.params.get('tp_atr', 2.0)
        self.sl_atr = self.params.get('sl_atr', 1.5)

    def generate_signals(self, data_dict: Dict[str, pd.DataFrame], symbol: str = "SECTOR") -> List[Signal]:
        """
        Args:
            data_dict: {symbol: DataFrame} for each sector ETF
        """
        min_len = self.return_period + self.rsi_period + 10
        returns_map = {}
        for sym, df in data_dict.items():
            if len(df) < min_len:
                continue
            ret_20d = (df['close'].iloc[-1] / df['close'].iloc[-self.return_period - 1] - 1) * 100
            returns_map[sym] = ret_20d

        if len(returns_map) < 4:
            return []

        ranked = sorted(returns_map.items(), key=lambda x: x[1], reverse=True)
        top = ranked[:self.top_n]
        bottom = ranked[-self.bottom_n:]

        signals = []

        for sym, ret in top:
            df = data_dict[sym]
            rsi = self._calculate_rsi(df['close'], self.rsi_period).iloc[-1]
            atr = self._calculate_atr(df).iloc[-1]
            price = df['close'].iloc[-1]
            if pd.isna(rsi) or pd.isna(atr):
                continue
            if rsi < self.long_rsi_max:
                confidence = min(0.4 + ret / 20 * 0.4, 0.90)
                signals.append(Signal(
                    symbol=sym,
                    direction="BUY",
                    confidence=round(max(confidence, 0.3), 2),
                    entry_price=round(price, 2),
                    take_profit=round(price + atr * self.tp_atr, 2),
                    stop_loss=round(price - atr * self.sl_atr, 2),
                    reason=f"SectorTop ret20d={ret:.1f}% RSI={rsi:.1f} rank=top{self.top_n}"
                ))

        for sym, ret in bottom:
            df = data_dict[sym]
            rsi = self._calculate_rsi(df['close'], self.rsi_period).iloc[-1]
            atr = self._calculate_atr(df).iloc[-1]
            price = df['close'].iloc[-1]
            if pd.isna(rsi) or pd.isna(atr):
                continue
            if rsi > self.short_rsi_min:
                confidence = min(0.4 + abs(ret) / 20 * 0.4, 0.90)
                signals.append(Signal(
                    symbol=sym,
                    direction="SELL",
                    confidence=round(max(confidence, 0.3), 2),
                    entry_price=round(price, 2),
                    take_profit=round(price - atr * self.tp_atr, 2),
                    stop_loss=round(price + atr * self.sl_atr, 2),
                    reason=f"SectorBot ret20d={ret:.1f}% RSI={rsi:.1f} rank=bot{self.bottom_n}"
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

    sectors = ETFSectorStrengthStrategy.SECTORS
    end = datetime.now()
    start = end - timedelta(days=730)

    print(f"Downloading {len(sectors)} sector ETFs ({start.date()} to {end.date()})...")
    all_data = {}
    for sym in sectors:
        df = yf.download(sym, start=start, end=end, progress=False)
        if hasattr(df.columns, 'levels') and df.columns.nlevels > 1:
            df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]
        df = df.reset_index()
        if len(df) > 50:
            all_data[sym] = df
            print(f"  {sym}: {len(df)} bars")

    strategy = ETFSectorStrengthStrategy()

    # Walk-forward: generate signals every 5 bars (weekly rebalance)
    trades = []
    open_positions = {}
    ref_len = len(list(all_data.values())[0])

    for i in range(50, ref_len):
        # Check open positions for TP/SL
        closed = []
        for sym, pos in open_positions.items():
            if sym not in all_data or i >= len(all_data[sym]):
                continue
            cp = all_data[sym]['close'].iloc[i]
            if pos['direction'] == 'BUY':
                if cp >= pos['tp']:
                    trades.append({'symbol': sym, 'direction': 'BUY', 'entry': pos['entry'],
                                   'exit': pos['tp'], 'pnl_pct': (pos['tp'] - pos['entry']) / pos['entry'] * 100})
                    closed.append(sym)
                elif cp <= pos['sl']:
                    trades.append({'symbol': sym, 'direction': 'BUY', 'entry': pos['entry'],
                                   'exit': pos['sl'], 'pnl_pct': (pos['sl'] - pos['entry']) / pos['entry'] * 100})
                    closed.append(sym)
            else:
                if cp <= pos['tp']:
                    trades.append({'symbol': sym, 'direction': 'SELL', 'entry': pos['entry'],
                                   'exit': pos['tp'], 'pnl_pct': (pos['entry'] - pos['tp']) / pos['entry'] * 100})
                    closed.append(sym)
                elif cp >= pos['sl']:
                    trades.append({'symbol': sym, 'direction': 'SELL', 'entry': pos['entry'],
                                   'exit': pos['sl'], 'pnl_pct': (pos['entry'] - pos['sl']) / pos['entry'] * 100})
                    closed.append(sym)
        for sym in closed:
            del open_positions[sym]

        # Generate new signals every 5 bars
        if i % 5 == 0:
            window_data = {}
            for sym, df in all_data.items():
                if i < len(df):
                    window_data[sym] = df.iloc[:i+1].copy()
            sigs = strategy.generate_signals(window_data)
            for s in sigs:
                if s.symbol not in open_positions:
                    open_positions[s.symbol] = {'direction': s.direction, 'entry': s.entry_price,
                                                 'tp': s.take_profit, 'sl': s.stop_loss}

    print(f"\n=== Sector Rotation Backtest ===")
    print(f"Sectors: {', '.join(sectors)}")
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
        # Per-sector breakdown
        by_sector = {}
        for t in trades:
            by_sector.setdefault(t['symbol'], []).append(t['pnl_pct'])
        print("\nPer-sector PnL:")
        for sym in sorted(by_sector.keys()):
            pnls = by_sector[sym]
            print(f"  {sym}: {len(pnls)} trades, total={sum(pnls):.2f}%, avg={np.mean(pnls):.2f}%")
    else:
        print("No trades generated.")
    print(f"Open positions: {len(open_positions)}")
