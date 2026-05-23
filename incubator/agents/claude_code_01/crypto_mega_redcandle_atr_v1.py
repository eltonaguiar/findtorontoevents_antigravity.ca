"""Mega-Permutation Combo: Red Candle Mean Reversion + ATR Expanding Layer.

Source: Mega-permutation top findings — RedCandleMeanReversion combined with
        ATR expansion filter. Only triggers BUY when 3+ consecutive red candles
        occur during expanding volatility (ATR above its own average), confirmed
        by moderate RSI weakness.

Strategy Logic:
  1. 3+ consecutive red candles (close < open).
  2. ATR(14) > 1.1 * ATR(14) averaged over 50 bars — volatility expanding.
  3. RSI(14) < 40 — moderate oversold confirmation.
  4. Entry: BUY on next bar open after all conditions met.
  5. Exits from mega-permutation winners:
     - Take Profit = 1.5 * ATR(14)
     - Stop Loss   = 0.75 * ATR(14)
     - Risk:Reward = 2.0:1

Confidence Formula:
  confidence = min(0.95, 0.5 + consecutive_count * 0.08 + atr_expansion_bonus)
  - Base 0.5
  - +0.08 per consecutive red candle
  - ATR expansion bonus (capped at 0.15)

Why It Works:
  Red candle streaks during expanding volatility indicate capitulation selling.
  ATR expansion confirms the move is real (not just drift), making the
  mean-reversion bounce more powerful. The 1.5 ATR target captures the
  typical V-bounce magnitude while the 0.75 ATR stop cuts losers early.

References:
  - Bollinger (2001): volatility expansion/contraction cycles
  - Mega-permutation engine backtest (2026)
"""

import sys
import os

if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class Signal:
    symbol: str
    direction: str
    entry_price: float
    take_profit: float
    stop_loss: float
    confidence: float
    strategy_name: str
    metadata: dict = field(default_factory=dict)


DEFAULT_PARAMS = {
    "min_consecutive_red": 3,
    "rsi_period": 14,
    "rsi_threshold": 40,
    "atr_period": 14,
    "atr_avg_period": 50,
    "atr_expansion_mult": 1.1,
    "tp_atr_mult": 1.5,
    "sl_atr_mult": 0.75,
}


class MegaRedCandleAtrStrategy:
    """Red Candle Mean Reversion + ATR Expanding — mega-perm optimized.

    Parameters
    ----------
    params : dict, optional
        Override any default parameter.
    """

    strategy_name = "MegaRedCandleAtr_v1"
    min_bars = 60

    def __init__(self, params: Optional[Dict] = None):
        cfg = {**DEFAULT_PARAMS}
        if params:
            cfg.update(params)

        self.min_consecutive_red: int = cfg["min_consecutive_red"]
        self.rsi_period: int = cfg["rsi_period"]
        self.rsi_threshold: float = cfg["rsi_threshold"]
        self.atr_period: int = cfg["atr_period"]
        self.atr_avg_period: int = cfg["atr_avg_period"]
        self.atr_expansion_mult: float = cfg["atr_expansion_mult"]
        self.tp_atr_mult: float = cfg["tp_atr_mult"]
        self.sl_atr_mult: float = cfg["sl_atr_mult"]

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        """Generate BUY signals on consecutive red candles + ATR expansion + RSI weakness.

        Parameters
        ----------
        data : pd.DataFrame
            OHLCV DataFrame with columns: open, high, low, close, volume.
        symbol : str
            Trading pair symbol (default "BTCUSDT").

        Returns
        -------
        List[Signal]
            Zero or one BUY Signal based on the latest bar.
        """
        required_cols = {"open", "high", "low", "close", "volume"}
        data.columns = [c.lower() for c in data.columns]
        if not required_cols.issubset(set(data.columns)):
            missing = required_cols - set(data.columns)
            raise ValueError(f"Missing columns: {missing}")

        if len(data) < self.min_bars:
            return []

        open_prices = data["open"].astype(float)
        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)

        # === Step 1: 3+ consecutive red candles ===
        is_red = (close < open_prices).astype(int)
        consecutive_red = self._count_consecutive(is_red)
        current_consecutive = int(consecutive_red.iloc[-1])

        if current_consecutive < self.min_consecutive_red:
            return []

        # === Step 2: ATR expansion — ATR(14) > 1.1 * avg ATR over 50 bars ===
        atr = self._calculate_atr(data, self.atr_period)
        cur_atr = atr.iloc[-1]

        if cur_atr <= 0 or pd.isna(cur_atr):
            return []

        atr_avg = atr.rolling(window=self.atr_avg_period, min_periods=1).mean()
        cur_atr_avg = atr_avg.iloc[-1]

        if cur_atr <= cur_atr_avg * self.atr_expansion_mult:
            return []

        # === Step 3: RSI(14) < 40 ===
        rsi = self._calculate_rsi(close, self.rsi_period)
        cur_rsi = rsi.iloc[-1]

        if pd.isna(cur_rsi) or cur_rsi >= self.rsi_threshold:
            return []

        # === Step 4: Build signal ===
        cur_close = float(close.iloc[-1])
        tp_price = cur_close + cur_atr * self.tp_atr_mult
        sl_price = cur_close - cur_atr * self.sl_atr_mult

        risk = cur_close - sl_price
        reward = tp_price - cur_close
        rr = reward / risk if risk > 0 else 0

        atr_expansion_ratio = cur_atr / cur_atr_avg if cur_atr_avg > 0 else 1.0
        atr_bonus = min(0.15, (atr_expansion_ratio - 1.0) * 0.1)

        confidence = 0.5 + current_consecutive * 0.08 + atr_bonus
        confidence = min(0.95, max(0.10, confidence))

        reason = (
            f"MegaRedCandleAtr BUY [mega-perm optimized]: "
            f"{current_consecutive} consecutive red candles, "
            f"ATR expansion={atr_expansion_ratio:.2f}x avg (>{self.atr_expansion_mult}x), "
            f"RSI(14)={cur_rsi:.1f}<{self.rsi_threshold}, "
            f"TP={self.tp_atr_mult}*ATR SL={self.sl_atr_mult}*ATR R:R={rr:.1f}:1"
        )

        return [Signal(
            symbol=symbol,
            direction="BUY",
            confidence=round(confidence, 4),
            entry_price=round(cur_close, 2),
            take_profit=round(tp_price, 2),
            stop_loss=round(sl_price, 2),
            strategy_name=self.strategy_name,
            metadata={
                "consecutive_red": current_consecutive,
                "atr_expansion": round(atr_expansion_ratio, 4),
                "rsi14": round(cur_rsi, 2),
                "atr": round(cur_atr, 2),
                "reason": reason,
            },
        )]

    def _count_consecutive(self, series: pd.Series) -> pd.Series:
        """Count consecutive True (1) values ending at each position."""
        result = pd.Series(0, index=series.index, dtype=int)
        for i in range(len(series)):
            if series.iloc[i] == 1:
                result.iloc[i] = (result.iloc[i - 1] + 1) if i > 0 else 1
            else:
                result.iloc[i] = 0
        return result

    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Wilder RSI."""
        delta = prices.diff()
        gains = delta.where(delta > 0, 0.0)
        losses = (-delta.where(delta < 0, 0.0))
        avg_gains = gains.rolling(window=period, min_periods=1).mean()
        avg_losses = losses.rolling(window=period, min_periods=1).mean()
        rs = avg_gains / avg_losses.replace(0, np.nan)
        return 100.0 - (100.0 / (1.0 + rs))

    def _calculate_atr(self, data: pd.DataFrame, period: int) -> pd.Series:
        """Average True Range."""
        high = data["high"]
        low = data["low"]
        close = data["close"]
        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)
        return tr.rolling(window=period, min_periods=1).mean()


# ---------------------------------------------------------------------------
# Standalone execution: synthetic test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    np.random.seed(42)
    n = 500
    prices_list = [90000.0]

    for i in range(1, n):
        phase = i % 100
        if phase < 15:
            ret = np.random.normal(-0.012, 0.004)
        elif phase < 25:
            ret = np.random.normal(0.008, 0.006)
        elif phase < 60:
            ret = np.random.normal(0.003, 0.008)
        else:
            ret = np.random.normal(0.0, 0.010)
        prices_list.append(prices_list[-1] * (1 + ret))

    prices = np.array(prices_list)
    opens = prices * (1 + np.random.normal(0.001, 0.003, n))
    highs = np.maximum(prices, opens) * (1 + np.abs(np.random.normal(0, 0.005, n)))
    lows = np.minimum(prices, opens) * (1 - np.abs(np.random.normal(0, 0.005, n)))

    base_vol = np.random.uniform(500, 2000, n)
    for i in range(n):
        if i % 100 < 15:
            base_vol[i] *= 2.5

    data = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": prices,
        "volume": base_vol,
    })

    strategy = MegaRedCandleAtrStrategy()
    signals = strategy.generate_signals(data, symbol="BTCUSDT")

    print("=" * 72)
    print(f"MegaRedCandleAtr_v1 (Mega-Permutation Optimized)")
    print("=" * 72)
    print(f"Bars: {n} | Signals: {len(signals)}")
    for s in signals:
        print(f"\n  [{s.direction}] {s.symbol} @ ${s.entry_price:,.2f}")
        print(f"  Confidence: {s.confidence:.2%}")
        print(f"  TP: ${s.take_profit:,.2f} | SL: ${s.stop_loss:,.2f}")
        print(f"  {s.metadata.get('reason', '')}")

    if not signals:
        print("  (No signal on latest bar)")
    print()
