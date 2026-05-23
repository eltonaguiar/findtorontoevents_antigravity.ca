"""
CommodityRangePositionReversion - Baby Strat
==============================================

Created: 2026-04-18
Asset class: Commodities (also tested across crypto/equity/forex)

Hypothesis:
- After an ATR volatility spike, if price closes in the bottom 20% of its
  daily range, exhaustion selling has occurred and next-day mean-reversion
  is likely.
- Uses intraday footprint (range position) rather than oscillator reading,
  making it fundamentally different from existing RSI/Stochastic-based pool.

Strategy Logic:
- Entry: ATR(14) > 1.5× ATR(50)  (vol expansion)
         AND (Close-Low)/(High-Low) < 0.20  (bottom 20% of range)
         AND Close > SMA(200)  (trend filter)
- Exit: TP = 2.5× ATR, SL = 2.0× ATR, max hold = 10 days

Differentiation:
- Not RSI / Stochastic / Williams %R
- Uses ATR regime (14 vs 50) for adaptive volatility detection
- Uses intraday range position for exhaustion detection
"""

import numpy as np
import pandas as pd


class CommodityRangePositionReversionStrategy:
    NAME = "commodity_range_position_reversion"
    DESCRIPTION = "ATR regime expansion + bottom-20% range close mean reversion"
    ENTRY_RULES = (
        "LONG: ATR(14) > 1.5*ATR(50) AND "
        "(Close-Low)/(High-Low) < 0.20 AND Close > SMA(200)"
    )
    EXIT_RULES = "TP = 2.5x ATR, SL = 2.0x ATR, max hold = 10 bars"

    def __init__(self, atr_fast=14, atr_slow=50, atr_mult=1.5,
                 range_threshold=0.20, sma_period=200,
                 tp_atr_mult=2.5, sl_atr_mult=2.0):
        self.atr_fast = atr_fast
        self.atr_slow = atr_slow
        self.atr_mult = atr_mult
        self.range_threshold = range_threshold
        self.sma_period = sma_period
        self.tp_atr_mult = tp_atr_mult
        self.sl_atr_mult = sl_atr_mult

    def generate_signals(self, df: pd.DataFrame, symbol: str = "UNKNOWN") -> list:
        if len(df) < 200:
            return []

        df = df.copy()
        close = df["close"] if "close" in df.columns else df["Close"]
        high = df["high"] if "high" in df.columns else df["High"]
        low = df["low"] if "low" in df.columns else df["Low"]

        # ATR
        hl = high - low
        hc = np.abs(high - close.shift())
        lc = np.abs(low - close.shift())
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        atr_fast = tr.rolling(window=self.atr_fast).mean()
        atr_slow = tr.rolling(window=self.atr_slow).mean()

        # SMA trend filter
        sma200 = close.rolling(window=self.sma_period).mean()

        signals = []
        for i in range(self.sma_period, len(df)):
            if pd.isna(atr_fast.iloc[i]) or pd.isna(atr_slow.iloc[i]) or pd.isna(sma200.iloc[i]):
                continue

            curr_close = float(close.iloc[i])
            curr_high = float(high.iloc[i])
            curr_low = float(low.iloc[i])
            curr_atr = float(atr_fast.iloc[i])
            curr_atr_slow = float(atr_slow.iloc[i])
            curr_sma = float(sma200.iloc[i])

            if curr_high <= curr_low or curr_atr <= 0 or curr_atr_slow <= 0:
                continue

            # ATR regime: fast > mult * slow
            atr_spike = curr_atr > self.atr_mult * curr_atr_slow

            # Range position: close in bottom N% of day's range
            bar_range = curr_high - curr_low
            range_pos = (curr_close - curr_low) / bar_range
            bottom_of_range = range_pos < self.range_threshold

            # Trend filter
            in_uptrend = curr_close > curr_sma

            if atr_spike and bottom_of_range and in_uptrend:
                entry_price = curr_close
                tp = entry_price + self.tp_atr_mult * curr_atr
                sl = entry_price - self.sl_atr_mult * curr_atr
                strength = min(100, int((self.range_threshold - range_pos) * 500))

                signals.append({
                    "symbol": symbol,
                    "side": "LONG",
                    "entry_price": entry_price,
                    "take_profit": float(tp),
                    "stop_loss": float(sl),
                    "strength": strength,
                    "reason": (
                        f"ATR spike {curr_atr:.2f}>{self.atr_mult}*{curr_atr_slow:.2f}, "
                        f"range pos {range_pos:.1%} < {self.range_threshold}, above SMA200"
                    ),
                    "strategy": self.NAME,
                })

        return signals
