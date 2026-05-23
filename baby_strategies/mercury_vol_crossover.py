"""
Mercury Vol Crossover Strategy
EMA(9)/EMA(21) crossover with RSI extremes, EMA(200) trend filter, ATR-based risk management.
Based on Mercury/InceptionLabs Vol-Adjusted EMA Crossover framework.
"""

import pandas as pd
import numpy as np


class MercuryVolCrossoverStrategy:
    """
    Mercury Vol Crossover -- EMA 9/21 cross + RSI extremes + 200 EMA trend + ATR risk.
    Academic source: Mercury/InceptionLabs (2026), Wilder (RSI/ATR 1978).
    """
    NAME = "mercury_vol_crossover"
    DESCRIPTION = "Mercury InceptionLabs: EMA 9/21 cross + RSI extremes + 200 EMA trend + ATR risk"
    ENTRY_RULES = (
        "LONG: EMA(9) crosses above EMA(21) AND RSI(14) < 30 within last 3 bars AND close > EMA(200); "
        "SHORT: EMA(9) crosses below EMA(21) AND RSI(14) > 70 within last 3 bars AND close < EMA(200)"
    )
    EXIT_RULES = "SL = 2x ATR(14), TP = 2:1 RR (4x ATR)"
    ACADEMIC_SOURCE = "Mercury/InceptionLabs (2026) — Vol-Adjusted EMA Crossover framework for TradingView Leap"
    EXPECTED_WR = "35-45%"
    EXPECTED_TRADES_PER_YEAR = "10-25 per symbol"

    def __init__(self, tp_rr_mult: float = 2.0, atr_stop_mult: float = 2.0, rsi_extreme: float = 30):
        self.tp_rr_mult = tp_rr_mult        # RR ratio (TP = rr_mult * stop distance)
        self.atr_stop_mult = atr_stop_mult  # Stop loss in ATR multiples
        self.rsi_extreme = rsi_extreme      # RSI threshold (LONG < extreme, SHORT > 100-extreme)

    def generate_signals(self, df: pd.DataFrame, symbol: str = "UNKNOWN") -> list[dict]:
        """Generate Mercury vol crossover signals."""
        if len(df) < 200:
            return []

        df = df.copy()

        # --- EMA (exponential weighted mean, adjust=False matches Pine ta.ema) ---
        ema9 = df['close'].ewm(span=9, adjust=False).mean()
        ema21 = df['close'].ewm(span=21, adjust=False).mean()
        ema200 = df['close'].ewm(span=200, adjust=False).mean()

        # --- RSI(14) with Wilder smoothing ---
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1.0 / 14, min_periods=14, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1.0 / 14, min_periods=14, adjust=False).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        # --- True Range & ATR(14) with Wilder smoothing ---
        hl = df['high'] - df['low']
        hc = np.abs(df['high'] - df['close'].shift())
        lc = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        atr = true_range.ewm(alpha=1.0 / 14, min_periods=14, adjust=False).mean()

        # --- Thresholds ---
        rsi_long_threshold = self.rsi_extreme         # default 30
        rsi_short_threshold = 100 - self.rsi_extreme  # default 70

        signals = []

        for i in range(200, len(df)):
            if pd.isna(rsi.iloc[i]) or pd.isna(atr.iloc[i]) or pd.isna(ema200.iloc[i]):
                continue

            curr_close = float(df['close'].iloc[i])
            curr_rsi = float(rsi.iloc[i])
            curr_atr = float(atr.iloc[i])
            curr_ema200 = float(ema200.iloc[i])

            fast_curr = float(ema9.iloc[i])
            fast_prev = float(ema9.iloc[i - 1])
            slow_curr = float(ema21.iloc[i])
            slow_prev = float(ema21.iloc[i - 1])

            stop_dist = self.atr_stop_mult * curr_atr
            tp_dist = self.tp_rr_mult * stop_dist

            # --- LONG: EMA(9) crosses above EMA(21) + RSI oversold (3-bar lookback) + uptrend ---
            if fast_curr > slow_curr and fast_prev <= slow_prev:
                # Check if RSI was extreme in last 3 bars (including current)
                rsi_recent_low = min(float(rsi.iloc[j]) for j in range(max(0, i - 2), i + 1))
                if rsi_recent_low < rsi_long_threshold and curr_close > curr_ema200:
                    entry_price = curr_close
                    tp = entry_price + tp_dist
                    sl = entry_price - stop_dist
                    strength = min(100, int((rsi_long_threshold - curr_rsi) * 3))

                    signals.append({
                        "symbol": symbol,
                        "side": "LONG",
                        "entry_price": entry_price,
                        "take_profit": float(tp),
                        "stop_loss": float(sl),
                        "strength": strength,
                        "reason": (
                            f"EMA(9) crossed above EMA(21), "
                            f"RSI(14)={curr_rsi:.1f} < {rsi_long_threshold}, "
                            f"above EMA(200), "
                            f"SL={stop_dist:.2f} TP={tp_dist:.2f} ({self.tp_rr_mult}:1 RR)"
                        ),
                        "strategy": self.NAME,
                    })

            # --- SHORT: EMA(9) crosses below EMA(21) + RSI overbought (3-bar lookback) + downtrend ---
            if fast_curr < slow_curr and fast_prev >= slow_prev:
                # Check if RSI was extreme in last 3 bars (including current)
                rsi_recent_high = max(float(rsi.iloc[j]) for j in range(max(0, i - 2), i + 1))
                if rsi_recent_high > rsi_short_threshold and curr_close < curr_ema200:
                    entry_price = curr_close
                    tp = entry_price - tp_dist
                    sl = entry_price + stop_dist
                    strength = min(100, int((curr_rsi - rsi_short_threshold) * 3))

                    signals.append({
                        "symbol": symbol,
                        "side": "SHORT",
                        "entry_price": entry_price,
                        "take_profit": float(tp),
                        "stop_loss": float(sl),
                        "strength": strength,
                        "reason": (
                            f"EMA(9) crossed below EMA(21), "
                            f"RSI(14)={curr_rsi:.1f} > {rsi_short_threshold}, "
                            f"below EMA(200), "
                            f"SL={stop_dist:.2f} TP={tp_dist:.2f} ({self.tp_rr_mult}:1 RR)"
                        ),
                        "strategy": self.NAME,
                    })

        return signals
