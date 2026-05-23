"""Mega-Permutation Combo: Consecutive Down RSI + Very Tight Stop Loss.

Source: Mega-permutation top findings — ConsecutiveDownRsi with optimal
        tight stop loss (0.3 ATR). Uses Bollinger Band lower band as an
        additional oversold confirmation layer on top of RSI(2) extremes.

Strategy Logic:
  1. 3+ consecutive down closes (close[i] < close[i-1]).
  2. RSI(2) < 10 — extreme short-term oversold.
  3. Close < Bollinger Band lower band (20-period, 2 std dev).
  4. Entry: BUY on next bar open after all conditions met.
  5. Exits from mega-permutation optimal tight stop:
     - Take Profit = 1.0 * ATR(14)
     - Stop Loss   = 0.3 * ATR(14)   (very tight — mega-perm optimal)
     - Risk:Reward = 3.33:1

Confidence Formula:
  confidence = min(0.95, 0.5 + consecutive_count * 0.1 + bb_depth_bonus)
  - Base 0.5
  - +0.1 per consecutive down close
  - BB depth bonus: how far below lower band (capped at 0.15)

Why It Works:
  Triple confirmation (consecutive down + RSI(2) extreme + below BB lower)
  identifies statistically rare oversold extremes. The very tight 0.3 ATR
  stop is viable because these setups have a high base win rate — failed
  signals reverse quickly, so a tight stop captures that. The 1.0 ATR
  target captures the snap-back bounce.

References:
  - Connors (2003): RSI(2) mean reversion
  - Bollinger (2001): Bollinger Bands as volatility envelope
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
    "min_consecutive_down": 3,
    "rsi2_period": 2,
    "rsi2_threshold": 10,
    "bb_period": 20,
    "bb_std": 2.0,
    "atr_period": 14,
    "tp_atr_mult": 1.0,
    "sl_atr_mult": 0.3,
}


class MegaConsdownTightStrategy:
    """Consecutive Down + RSI(2) + BB Lower Band — mega-perm tight stop optimized.

    Parameters
    ----------
    params : dict, optional
        Override any default parameter.
    """

    strategy_name = "MegaConsdownTight_v1"
    min_bars = 30

    def __init__(self, params: Optional[Dict] = None):
        cfg = {**DEFAULT_PARAMS}
        if params:
            cfg.update(params)

        self.min_consecutive_down: int = cfg["min_consecutive_down"]
        self.rsi2_period: int = cfg["rsi2_period"]
        self.rsi2_threshold: float = cfg["rsi2_threshold"]
        self.bb_period: int = cfg["bb_period"]
        self.bb_std: float = cfg["bb_std"]
        self.atr_period: int = cfg["atr_period"]
        self.tp_atr_mult: float = cfg["tp_atr_mult"]
        self.sl_atr_mult: float = cfg["sl_atr_mult"]

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        """Generate BUY signals on consecutive down closes + RSI(2) extreme + below BB lower.

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

        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)

        # === Step 1: 3+ consecutive down closes ===
        is_down = (close < close.shift(1)).astype(int)
        consecutive_down = self._count_consecutive(is_down)
        current_consecutive = int(consecutive_down.iloc[-1])

        if current_consecutive < self.min_consecutive_down:
            return []

        # === Step 2: RSI(2) < 10 ===
        rsi2 = self._calculate_rsi(close, self.rsi2_period)
        cur_rsi2 = rsi2.iloc[-1]

        if pd.isna(cur_rsi2) or cur_rsi2 >= self.rsi2_threshold:
            return []

        # === Step 3: Close < BB lower band ===
        bb_mid = close.rolling(window=self.bb_period, min_periods=1).mean()
        bb_std = close.rolling(window=self.bb_period, min_periods=1).std()
        bb_lower = bb_mid - self.bb_std * bb_std

        cur_close = float(close.iloc[-1])
        cur_bb_lower = float(bb_lower.iloc[-1])

        if cur_close >= cur_bb_lower:
            return []

        # === Step 4: ATR for TP/SL ===
        atr = self._calculate_atr(data, self.atr_period)
        cur_atr = atr.iloc[-1]

        if cur_atr <= 0 or pd.isna(cur_atr):
            return []

        # === Step 5: Build signal ===
        tp_price = cur_close + cur_atr * self.tp_atr_mult
        sl_price = cur_close - cur_atr * self.sl_atr_mult

        risk = cur_close - sl_price
        reward = tp_price - cur_close
        rr = reward / risk if risk > 0 else 0

        bb_depth = (cur_bb_lower - cur_close) / cur_atr if cur_atr > 0 else 0
        bb_bonus = min(0.15, abs(bb_depth) * 0.1)

        confidence = 0.5 + current_consecutive * 0.1 + bb_bonus
        confidence = min(0.95, max(0.10, confidence))

        reason = (
            f"MegaConsdownTight BUY [mega-perm tight stop]: "
            f"{current_consecutive} consecutive down closes, "
            f"RSI(2)={cur_rsi2:.1f}<{self.rsi2_threshold}, "
            f"close ${cur_close:,.2f} < BB lower ${cur_bb_lower:,.2f}, "
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
                "consecutive_down": current_consecutive,
                "rsi2": round(cur_rsi2, 2),
                "bb_lower": round(cur_bb_lower, 2),
                "bb_depth_atr": round(bb_depth, 4),
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

    strategy = MegaConsdownTightStrategy()
    signals = strategy.generate_signals(data, symbol="BTCUSDT")

    print("=" * 72)
    print(f"MegaConsdownTight_v1 (Mega-Permutation Tight Stop)")
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
