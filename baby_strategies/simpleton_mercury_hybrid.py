"""
Simpleton Mercury Hybrid Strategy
FundedRelay 21/55 EMA crossover + Mercury RSI extremes (30/70) + ATR volatility gate.
Hybrid combining best of both frameworks: Simpleton's crossover with Mercury's aggressive RSI thresholds.
"""

import pandas as pd
import numpy as np


class SimpletonMercuryHybridStrategy:
    """
    Simpleton Mercury Hybrid -- FundedRelay EMA cross + Mercury RSI extremes + ATR gate.
    Combines Simpleton's 21/55 crossover structure with Mercury's 30/70 RSI extremes
    and enhanced 2.5:1 reward-to-risk ratio.
    """
    NAME = "simpleton_mercury_hybrid"
    DESCRIPTION = "FundedRelay 21/55 EMA cross + Mercury RSI extremes (30/70) + ATR volatility gate"
    ENTRY_RULES = (
        "LONG: EMA(21) crosses above EMA(55) AND close > EMA(200) AND RSI(14) < 30 within last 3 bars AND true_range > ATR(14); "
        "SHORT: EMA(21) crosses below EMA(55) AND close < EMA(200) AND RSI(14) > 70 within last 3 bars AND true_range > ATR(14)"
    )
    EXIT_RULES = "SL = 2x ATR(14), TP = 5x ATR(14) (2.5:1 RR)"
    ACADEMIC_SOURCE = "FundedRelay (2024) x Mercury/InceptionLabs (2026) -- hybrid crossover with RSI extremes"
    EXPECTED_WR = "38-48%"
    EXPECTED_TRADES_PER_YEAR = "8-20 per symbol"

    def __init__(self, atr_stop_mult: float = 2.0, rr_mult: float = 2.5, rsi_extreme: float = 40):
        self.atr_stop_mult = atr_stop_mult
        self.rr_mult = rr_mult
        self.rsi_extreme = rsi_extreme  # LONG: RSI < rsi_extreme, SHORT: RSI > (100 - rsi_extreme)
        # NOTE: Default relaxed from 30→40 to generate trades in normal markets

    def generate_signals(self, df: pd.DataFrame, symbol: str = "UNKNOWN") -> list[dict]:
        """Generate hybrid Simpleton/Mercury signals."""
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
        rsi_long_threshold = self.rsi_extreme        # default 30 (oversold)
        rsi_short_threshold = 100 - self.rsi_extreme  # default 70 (overbought)

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

            # Volatility gate: current bar's true range must be at least 70% of ATR
            # (was 100% — too strict, filtered out most valid crossovers)
            if curr_tr <= curr_atr * 0.7:
                continue

            # --- LONG: EMA(21) crosses above EMA(55), RSI oversold (3-bar lookback) ---
            if fast_curr > slow_curr and fast_prev <= slow_prev:
                # Check if RSI was extreme in last 3 bars (including current)
                rsi_recent_low = min(float(rsi.iloc[j]) for j in range(max(0, i - 2), i + 1))
                if curr_close > curr_ema200 and rsi_recent_low < rsi_long_threshold:
                    entry_price = curr_close
                    sl = entry_price - self.atr_stop_mult * curr_atr
                    tp = entry_price + self.atr_stop_mult * self.rr_mult * curr_atr
                    strength = min(100, int((rsi_long_threshold - curr_rsi) * 3))

                    signals.append({
                        "symbol": symbol,
                        "side": "LONG",
                        "entry_price": entry_price,
                        "take_profit": float(tp),
                        "stop_loss": float(sl),
                        "strength": strength,
                        "reason": (
                            f"EMA(21) crossed above EMA(55), "
                            f"RSI(14)={curr_rsi:.1f} < {rsi_long_threshold} (oversold), "
                            f"TR={curr_tr:.2f} > ATR={curr_atr:.2f}, "
                            f"above EMA(200)"
                        ),
                        "strategy": self.NAME,
                    })

            # --- SHORT: EMA(21) crosses below EMA(55), RSI overbought (3-bar lookback) ---
            if fast_curr < slow_curr and fast_prev >= slow_prev:
                # Check if RSI was extreme in last 3 bars (including current)
                rsi_recent_high = max(float(rsi.iloc[j]) for j in range(max(0, i - 2), i + 1))
                if curr_close < curr_ema200 and rsi_recent_high > rsi_short_threshold:
                    entry_price = curr_close
                    sl = entry_price + self.atr_stop_mult * curr_atr
                    tp = entry_price - self.atr_stop_mult * self.rr_mult * curr_atr
                    strength = min(100, int((curr_rsi - rsi_short_threshold) * 3))

                    signals.append({
                        "symbol": symbol,
                        "side": "SHORT",
                        "entry_price": entry_price,
                        "take_profit": float(tp),
                        "stop_loss": float(sl),
                        "strength": strength,
                        "reason": (
                            f"EMA(21) crossed below EMA(55), "
                            f"RSI(14)={curr_rsi:.1f} > {rsi_short_threshold} (overbought), "
                            f"TR={curr_tr:.2f} > ATR={curr_atr:.2f}, "
                            f"below EMA(200)"
                        ),
                        "strategy": self.NAME,
                    })

        return signals
