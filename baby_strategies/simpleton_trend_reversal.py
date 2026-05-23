"""
Simpleton Trend Reversal Strategy
EMA crossover (21/55) with EMA(200) trend filter, RSI(14) confirmation, ATR volatility gate.
Converted from Pine Script v6: Simpletonv0.01_KIMI.pine (Triple EMA mode).
"""

import pandas as pd
import numpy as np


class SimpletonTrendReversalStrategy:
    """
    Simpleton Trend Reversal — EMA crossover + RSI + ATR confirmation.
    Academic source: Gerald Appel (EMA crossover systems), Wilder (RSI/ATR 1978).
    """
    NAME = "simpleton_trend_reversal"
    DESCRIPTION = "EMA(21)/EMA(55) crossover with EMA(200) trend filter, RSI(14) momentum, ATR volatility gate"
    ENTRY_RULES = (
        "LONG: EMA(21) crosses above EMA(55) AND close > EMA(200) AND RSI(14) > 55 AND true_range > ATR(14); "
        "SHORT: EMA(21) crosses below EMA(55) AND close < EMA(200) AND RSI(14) < 45 AND true_range > ATR(14)"
    )
    EXIT_RULES = "TP = 2.5x ATR(14), SL = 1.5x ATR(14)"
    ACADEMIC_SOURCE = "Appel (EMA systems), Wilder (1978) 'New Concepts in Technical Trading Systems'"
    EXPECTED_WR = "52-58%"
    EXPECTED_TRADES_PER_YEAR = "15-30 per symbol"

    def __init__(self, tp_atr_mult: float = 2.5, sl_atr_mult: float = 1.5, rsi_offset: float = 5):
        self.tp_atr_mult = tp_atr_mult
        self.sl_atr_mult = sl_atr_mult
        self.rsi_offset = rsi_offset  # Long threshold = 50+offset, Short = 50-offset

    def generate_signals(self, df: pd.DataFrame, symbol: str = "UNKNOWN") -> list[dict]:
        """Generate EMA crossover trend reversal signals."""
        if len(df) < 200:
            return []

        df = df.copy()

        # --- EMA (exponential weighted mean, adjust=False matches Pine ta.ema) ---
        ema21 = df['close'].ewm(span=21, adjust=False).mean()
        ema55 = df['close'].ewm(span=55, adjust=False).mean()
        ema200 = df['close'].ewm(span=200, adjust=False).mean()

        # --- RSI(14) with Wilder smoothing ---
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1.0 / 14, min_periods=14, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1.0 / 14, min_periods=14, adjust=False).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        # --- True Range & ATR(14) with EWM (Wilder smoothing) ---
        hl = df['high'] - df['low']
        hc = np.abs(df['high'] - df['close'].shift())
        lc = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        atr = true_range.ewm(alpha=1.0 / 14, min_periods=14, adjust=False).mean()

        # --- Thresholds ---
        rsi_long_threshold = 50 + self.rsi_offset   # default 55
        rsi_short_threshold = 50 - self.rsi_offset   # default 45

        signals = []

        for i in range(200, len(df)):
            if pd.isna(rsi.iloc[i]) or pd.isna(atr.iloc[i]) or pd.isna(ema200.iloc[i]):
                continue

            curr_close = float(df['close'].iloc[i])
            curr_rsi = float(rsi.iloc[i])
            curr_atr = float(atr.iloc[i])
            curr_tr = float(true_range.iloc[i])
            curr_ema200 = float(ema200.iloc[i])

            fast_curr = float(ema21.iloc[i])
            fast_prev = float(ema21.iloc[i - 1])
            slow_curr = float(ema55.iloc[i])
            slow_prev = float(ema55.iloc[i - 1])

            # Volatility gate: current bar's true range must exceed ATR
            if curr_tr <= curr_atr:
                continue

            # --- LONG: EMA(21) crosses above EMA(55) ---
            if fast_curr > slow_curr and fast_prev <= slow_prev:
                if curr_close > curr_ema200 and curr_rsi > rsi_long_threshold:
                    entry_price = curr_close
                    tp = entry_price + self.tp_atr_mult * curr_atr
                    sl = entry_price - self.sl_atr_mult * curr_atr
                    strength = min(100, int((curr_rsi - 50) * 2))

                    signals.append({
                        "symbol": symbol,
                        "side": "LONG",
                        "entry_price": entry_price,
                        "take_profit": float(tp),
                        "stop_loss": float(sl),
                        "strength": strength,
                        "reason": (
                            f"EMA(21) crossed above EMA(55), "
                            f"RSI(14)={curr_rsi:.1f}, "
                            f"TR={curr_tr:.2f} > ATR={curr_atr:.2f}, "
                            f"above EMA(200)"
                        ),
                        "strategy": self.NAME,
                    })

            # --- SHORT: EMA(21) crosses below EMA(55) ---
            if fast_curr < slow_curr and fast_prev >= slow_prev:
                if curr_close < curr_ema200 and curr_rsi < rsi_short_threshold:
                    entry_price = curr_close
                    tp = entry_price - self.tp_atr_mult * curr_atr
                    sl = entry_price + self.sl_atr_mult * curr_atr
                    strength = min(100, int((50 - curr_rsi) * 2))

                    signals.append({
                        "symbol": symbol,
                        "side": "SHORT",
                        "entry_price": entry_price,
                        "take_profit": float(tp),
                        "stop_loss": float(sl),
                        "strength": strength,
                        "reason": (
                            f"EMA(21) crossed below EMA(55), "
                            f"RSI(14)={curr_rsi:.1f}, "
                            f"TR={curr_tr:.2f} > ATR={curr_atr:.2f}, "
                            f"below EMA(200)"
                        ),
                        "strategy": self.NAME,
                    })

        return signals
