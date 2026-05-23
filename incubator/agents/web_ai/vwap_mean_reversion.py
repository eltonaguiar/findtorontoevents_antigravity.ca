"""
VWAPMeanReversion - Baby Strat
===============================

Created by: web_ai
Date: 2026-03-28

Strategy Logic:
- Compute VWAP over rolling 20-bar window
- Compute RSI(14) and ATR(14)
- BUY when: price < VWAP * 0.97 (3% below) AND RSI < 35
- SELL when: price > VWAP * 1.03 (3% above) AND RSI > 65
- TP = 2.0x ATR, SL = 1.2x ATR
- Confidence: 0.55-0.85 scaled by deviation magnitude

Unique Value Proposition:
VWAP anchors price to volume-weighted fair value. When price deviates
significantly from VWAP with RSI confirmation, mean-reversion trades
capture the snap-back to fair value. Bi-directional (BUY + SELL).

Expected Regime: Ranging/mean-reverting markets where price oscillates
around VWAP. Avoids strong trending regimes.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class Signal:
    """A trading signal - required return type."""
    symbol: str           # e.g., "BTCUSDT"
    direction: str        # "BUY" or "SELL"
    confidence: float     # 0.0 to 1.0
    entry_price: float    # Suggested entry
    take_profit: float    # Target price
    stop_loss: float      # Stop price
    reason: str           # Why this signal


SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "DOTUSDT", "AVAXUSDT", "LINKUSDT", "NEARUSDT",
]


class VWAPMeanReversionStrategy:
    """
    VWAP mean-reversion with RSI confirmation.

    Computes a rolling VWAP over 20 bars, then triggers BUY when price
    is 3%+ below VWAP with RSI < 35, or SELL when price is 3%+ above
    VWAP with RSI > 65.

    Required methods:
    - __init__(self, params): Initialize parameters
    - generate_signals(self, data, symbol): Return List[Signal]
    """

    def __init__(self, params: Optional[Dict] = None):
        """
        Define all tunable parameters here.

        Args:
            params: Dictionary of parameters
        """
        self.params = params or {}
        self.vwap_window = self.params.get('vwap_window', 20)
        self.rsi_period = self.params.get('rsi_period', 14)
        self.atr_period = self.params.get('atr_period', 14)
        self.buy_deviation = self.params.get('buy_deviation', 0.97)
        self.sell_deviation = self.params.get('sell_deviation', 1.03)
        self.rsi_oversold = self.params.get('rsi_oversold', 35)
        self.rsi_overbought = self.params.get('rsi_overbought', 65)
        self.tp_atr = self.params.get('tp_atr', 2.0)
        self.sl_atr = self.params.get('sl_atr', 1.2)
        self.conf_min = 0.55
        self.conf_max = 0.85

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        """
        Main signal generation method.

        Args:
            data: DataFrame with columns [open, high, low, close, volume]
            symbol: Trading pair being analyzed

        Returns:
            List of Signal objects (empty if no signal)
        """
        min_len = self.vwap_window + self.rsi_period + 10
        if len(data) < min_len:
            return []

        # Calculate indicators
        vwap = self._calculate_vwap(data)
        rsi = self._calculate_rsi(data['close'], self.rsi_period)
        atr = self._calculate_atr(data)

        # Current values
        current_price = data['close'].iloc[-1]
        current_vwap = vwap.iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_atr = atr.iloc[-1]

        if pd.isna(current_vwap) or pd.isna(current_rsi) or pd.isna(current_atr):
            return []
        if current_vwap <= 0 or current_atr <= 0:
            return []

        deviation = (current_price - current_vwap) / current_vwap
        signals = []

        # BUY: price 3%+ below VWAP and RSI oversold
        if current_price < current_vwap * self.buy_deviation and current_rsi < self.rsi_oversold:
            abs_dev = abs(deviation)
            confidence = self._scale_confidence(abs_dev)
            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 2),
                entry_price=round(current_price, 2),
                take_profit=round(current_price + current_atr * self.tp_atr, 2),
                stop_loss=round(current_price - current_atr * self.sl_atr, 2),
                reason=f"VWAP MeanRev BUY dev={deviation:+.2%} RSI={current_rsi:.1f} VWAP={current_vwap:.2f}"
            ))

        # SELL: price 3%+ above VWAP and RSI overbought
        if current_price > current_vwap * self.sell_deviation and current_rsi > self.rsi_overbought:
            abs_dev = abs(deviation)
            confidence = self._scale_confidence(abs_dev)
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 2),
                entry_price=round(current_price, 2),
                take_profit=round(current_price - current_atr * self.tp_atr, 2),
                stop_loss=round(current_price + current_atr * self.sl_atr, 2),
                reason=f"VWAP MeanRev SELL dev={deviation:+.2%} RSI={current_rsi:.1f} VWAP={current_vwap:.2f}"
            ))

        return signals

    def _calculate_vwap(self, data: pd.DataFrame) -> pd.Series:
        """Calculate rolling VWAP over window bars."""
        typical_price = data['close']
        pv = typical_price * data['volume']
        vwap = pv.rolling(self.vwap_window).sum() / data['volume'].rolling(self.vwap_window).sum()
        return vwap

    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_atr(self, data: pd.DataFrame) -> pd.Series:
        """Calculate Average True Range."""
        high, low, close = data['high'], data['low'], data['close']
        tr = pd.concat([
            high - low,
            abs(high - close.shift()),
            abs(low - close.shift())
        ], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def _scale_confidence(self, abs_deviation: float) -> float:
        """Scale confidence 0.55-0.85 based on deviation magnitude."""
        # 3% deviation = 0.55, 8%+ deviation = 0.85
        ratio = min(max((abs_deviation - 0.03) / 0.05, 0.0), 1.0)
        return self.conf_min + ratio * (self.conf_max - self.conf_min)


# ==============================================================================
# BACKTEST - Fetch real data and walk-forward test
# ==============================================================================

if __name__ == "__main__":
    import requests
    import time

    BACKTEST_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
    BINANCE_MIRRORS = [
        "https://api.binance.com",
        "https://api1.binance.com",
        "https://api2.binance.com",
        "https://api3.binance.com",
    ]
    LOOKAHEAD_BARS = 12

    def fetch_klines(symbol: str, interval: str = "4h", limit: int = 540) -> pd.DataFrame:
        """Fetch klines from Binance with mirror failover."""
        for base_url in BINANCE_MIRRORS:
            try:
                url = f"{base_url}/api/v3/klines"
                params = {"symbol": symbol, "interval": interval, "limit": limit}
                resp = requests.get(url, params=params, timeout=15)
                resp.raise_for_status()
                raw = resp.json()
                df = pd.DataFrame(raw, columns=[
                    'open_time', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                    'taker_buy_quote', 'ignore'
                ])
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = df[col].astype(float)
                return df[['open', 'high', 'low', 'close', 'volume']]
            except Exception as e:
                print(f"  Mirror {base_url} failed for {symbol}: {e}")
                continue
        print(f"  ALL mirrors failed for {symbol}, skipping.")
        return pd.DataFrame()

    strategy = VWAPMeanReversionStrategy()
    all_trades = []

    for sym in BACKTEST_SYMBOLS:
        print(f"\n--- Fetching {sym} 4h data (90 days ~ 540 bars) ---")
        df = fetch_klines(sym, "4h", 540)
        if df.empty or len(df) < 100:
            print(f"  Insufficient data for {sym}, skipping.")
            continue

        print(f"  Got {len(df)} bars for {sym}")
        min_start = strategy.vwap_window + strategy.rsi_period + 10

        for i in range(min_start, len(df) - LOOKAHEAD_BARS):
            window = df.iloc[:i + 1].copy().reset_index(drop=True)
            signals = strategy.generate_signals(window, symbol=sym)

            for sig in signals:
                # Walk forward up to LOOKAHEAD_BARS to check TP/SL
                entry = sig.entry_price
                tp = sig.take_profit
                sl = sig.stop_loss
                outcome = "OPEN"
                exit_price = entry

                for j in range(1, LOOKAHEAD_BARS + 1):
                    future_idx = i + j
                    if future_idx >= len(df):
                        break
                    bar_high = df['high'].iloc[future_idx]
                    bar_low = df['low'].iloc[future_idx]

                    if sig.direction == "BUY":
                        if bar_low <= sl:
                            outcome = "LOSS"
                            exit_price = sl
                            break
                        if bar_high >= tp:
                            outcome = "WIN"
                            exit_price = tp
                            break
                    else:  # SELL
                        if bar_high >= sl:
                            outcome = "LOSS"
                            exit_price = sl
                            break
                        if bar_low <= tp:
                            outcome = "WIN"
                            exit_price = tp
                            break

                if outcome == "OPEN":
                    # Close at last available bar
                    last_idx = min(i + LOOKAHEAD_BARS, len(df) - 1)
                    exit_price = df['close'].iloc[last_idx]
                    if sig.direction == "BUY":
                        outcome = "WIN" if exit_price > entry else "LOSS"
                    else:
                        outcome = "WIN" if exit_price < entry else "LOSS"

                if sig.direction == "BUY":
                    pnl_pct = (exit_price - entry) / entry * 100
                else:
                    pnl_pct = (entry - exit_price) / entry * 100

                all_trades.append({
                    'symbol': sym,
                    'direction': sig.direction,
                    'confidence': sig.confidence,
                    'entry': entry,
                    'exit': exit_price,
                    'outcome': outcome,
                    'pnl_pct': pnl_pct,
                    'reason': sig.reason,
                })

        time.sleep(0.5)  # Rate limit courtesy

    # ---- Results Summary ----
    print("\n" + "=" * 60)
    print("VWAP MEAN REVERSION BACKTEST RESULTS")
    print("=" * 60)

    if not all_trades:
        print("No trades generated.")
    else:
        total = len(all_trades)
        wins = sum(1 for t in all_trades if t['outcome'] == 'WIN')
        losses = total - wins
        win_rate = wins / total * 100 if total > 0 else 0

        gross_profit = sum(t['pnl_pct'] for t in all_trades if t['pnl_pct'] > 0)
        gross_loss = abs(sum(t['pnl_pct'] for t in all_trades if t['pnl_pct'] < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        avg_pnl = sum(t['pnl_pct'] for t in all_trades) / total

        print(f"Total trades:   {total}")
        print(f"Wins:           {wins}  |  Losses: {losses}")
        print(f"Win rate:       {win_rate:.1f}%")
        print(f"Profit factor:  {profit_factor:.2f}")
        print(f"Avg PnL/trade:  {avg_pnl:+.3f}%")
        print(f"Gross profit:   {gross_profit:.2f}%  |  Gross loss: {gross_loss:.2f}%")

        # Per-symbol breakdown
        print(f"\n{'Symbol':<10} {'Trades':>6} {'WR':>7} {'AvgPnL':>9}")
        print("-" * 35)
        for sym in BACKTEST_SYMBOLS:
            sym_trades = [t for t in all_trades if t['symbol'] == sym]
            if sym_trades:
                st = len(sym_trades)
                sw = sum(1 for t in sym_trades if t['outcome'] == 'WIN')
                sa = sum(t['pnl_pct'] for t in sym_trades) / st
                print(f"{sym:<10} {st:>6} {sw/st*100:>6.1f}% {sa:>+8.3f}%")

        # Sample trades
        print(f"\nSample trades (first 5):")
        for t in all_trades[:5]:
            print(f"  {t['symbol']} {t['direction']} entry={t['entry']:.2f} "
                  f"exit={t['exit']:.2f} {t['outcome']} pnl={t['pnl_pct']:+.2f}% "
                  f"conf={t['confidence']:.2f}")
