"""Mega-Permutation Combo: RSI Volume Mean Reversion + EMA Trend Alignment.

Source: Mega-permutation top findings — RSIVolumeMeanReversion combined with
        EMA trend alignment layer. Only triggers BUY when oversold + volume
        spike occurs within a confirmed uptrend (EMA20 > EMA50).

Strategy Logic:
  1. RSI(14) < 30 — oversold condition.
  2. Volume > 1.5x 20-bar average — participation spike.
  3. EMA(20) > EMA(50) — trend alignment (buy dips in uptrend only).
  4. Entry: BUY on next bar open after all conditions met.
  5. Exits from mega-permutation winners:
     - Take Profit = 1.0 * ATR(14)
     - Stop Loss   = 0.75 * ATR(14)
     - Risk:Reward = 1.33:1

Confidence Formula:
  confidence = min(0.95, 0.5 + (30 - rsi14) / 50 + vol_ratio_bonus)
  - Base 0.5
  - RSI depth bonus: deeper oversold = higher confidence
  - Volume ratio bonus: capped at 0.15

Why It Works:
  Buying oversold pullbacks within an established uptrend (EMA alignment)
  catches mean-reversion bounces with trend tailwind. The volume spike
  confirms institutional participation in the dip. Tight ATR stops from
  mega-perm optimization limit losses on failed bounces.

References:
  - Wilder (1978): RSI momentum oscillator
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
    "rsi_period": 14,
    "rsi_threshold": 30,
    "ema_fast": 20,
    "ema_slow": 50,
    "vol_avg_period": 20,
    "vol_mult": 1.5,
    "atr_period": 14,
    "tp_atr_mult": 1.0,
    "sl_atr_mult": 0.75,
}


class MegaRsiVolEmaStrategy:
    """RSI Volume Mean Reversion + EMA Trend Alignment — mega-perm optimized.

    Parameters
    ----------
    params : dict, optional
        Override any default parameter.
    """

    strategy_name = "MegaRsiVolEma_v1"
    min_bars = 60

    def __init__(self, params: Optional[Dict] = None):
        cfg = {**DEFAULT_PARAMS}
        if params:
            cfg.update(params)

        self.rsi_period: int = cfg["rsi_period"]
        self.rsi_threshold: float = cfg["rsi_threshold"]
        self.ema_fast: int = cfg["ema_fast"]
        self.ema_slow: int = cfg["ema_slow"]
        self.vol_avg_period: int = cfg["vol_avg_period"]
        self.vol_mult: float = cfg["vol_mult"]
        self.atr_period: int = cfg["atr_period"]
        self.tp_atr_mult: float = cfg["tp_atr_mult"]
        self.sl_atr_mult: float = cfg["sl_atr_mult"]

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        """Generate BUY signals on RSI oversold + volume spike + EMA trend alignment.

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
        volume = data["volume"].astype(float)

        # === Step 1: RSI(14) < 30 ===
        rsi = self._calculate_rsi(close, self.rsi_period)
        cur_rsi = rsi.iloc[-1]

        if pd.isna(cur_rsi) or cur_rsi >= self.rsi_threshold:
            return []

        # === Step 2: Volume > 1.5x 20-bar average ===
        vol_avg = volume.rolling(window=self.vol_avg_period, min_periods=1).mean()
        current_vol = volume.iloc[-1]
        avg_vol = vol_avg.iloc[-1]

        if current_vol <= avg_vol * self.vol_mult:
            return []

        # === Step 3: EMA(20) > EMA(50) — uptrend ===
        ema_fast = close.ewm(span=self.ema_fast, adjust=False).mean()
        ema_slow = close.ewm(span=self.ema_slow, adjust=False).mean()

        if ema_fast.iloc[-1] <= ema_slow.iloc[-1]:
            return []

        # === Step 4: ATR for TP/SL ===
        atr = self._calculate_atr(data, self.atr_period)
        cur_atr = atr.iloc[-1]

        if cur_atr <= 0 or pd.isna(cur_atr):
            return []

        # === Step 5: Build signal ===
        cur_close = float(close.iloc[-1])
        tp_price = cur_close + cur_atr * self.tp_atr_mult
        sl_price = cur_close - cur_atr * self.sl_atr_mult

        risk = cur_close - sl_price
        reward = tp_price - cur_close
        rr = reward / risk if risk > 0 else 0

        vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1.0
        vol_bonus = min(0.15, (vol_ratio - 1.0) * 0.05)

        confidence = 0.5 + (self.rsi_threshold - cur_rsi) / 50.0 + vol_bonus
        confidence = min(0.95, max(0.10, confidence))

        ema_gap_pct = (ema_fast.iloc[-1] - ema_slow.iloc[-1]) / ema_slow.iloc[-1] * 100

        reason = (
            f"MegaRsiVolEma BUY [mega-perm optimized]: "
            f"RSI(14)={cur_rsi:.1f}<{self.rsi_threshold}, "
            f"vol={vol_ratio:.1f}x avg (>{self.vol_mult}x), "
            f"EMA({self.ema_fast})>EMA({self.ema_slow}) gap={ema_gap_pct:.2f}%, "
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
                "rsi14": round(cur_rsi, 2),
                "vol_ratio": round(vol_ratio, 2),
                "ema_gap_pct": round(ema_gap_pct, 4),
                "atr": round(cur_atr, 2),
                "reason": reason,
            },
        )]

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

    strategy = MegaRsiVolEmaStrategy()
    signals = strategy.generate_signals(data, symbol="BTCUSDT")

    print("=" * 72)
    print(f"MegaRsiVolEma_v1 (Mega-Permutation Optimized)")
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
