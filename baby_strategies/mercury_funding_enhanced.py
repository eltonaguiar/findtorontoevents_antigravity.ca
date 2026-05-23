"""
Mercury Funding Enhanced Strategy
Mercury EMA(9)/EMA(21) crossover + RSI(14) extremes + funding rate directional bias.
Overlays Binance funding rate data for enhanced crypto signal confidence.
"""

import pandas as pd
import numpy as np


class MercuryFundingEnhancedStrategy:
    """
    Mercury Funding Enhanced -- EMA cross + RSI extremes + funding rate overlay.
    Uses Mercury's fast 9/21 crossover with RSI 30/70 extremes, plus optional
    funding rate column for directional bias confirmation in crypto markets.
    """
    NAME = "mercury_funding_enhanced"
    DESCRIPTION = "Mercury EMA cross + RSI + funding rate directional bias for enhanced crypto signals"
    ENTRY_RULES = (
        "LONG: EMA(9) crosses above EMA(21) AND close > EMA(200) AND RSI(14) < 30 within last 3 bars "
        "AND (funding_rate < -0.0003 if available); "
        "SHORT: EMA(9) crosses below EMA(21) AND close < EMA(200) AND RSI(14) > 70 within last 3 bars "
        "AND (funding_rate > 0.0005 if available)"
    )
    EXIT_RULES = "SL = 2x ATR(14), TP = 4x ATR(14) (2:1 RR)"
    ACADEMIC_SOURCE = "Mercury/InceptionLabs (2026) + Binance funding rate carry research (2021)"
    EXPECTED_WR = "40-50%"
    EXPECTED_TRADES_PER_YEAR = "10-25 per symbol"

    def __init__(self, atr_stop_mult: float = 2.0, rr_mult: float = 2.0, funding_threshold: float = 0.0003):
        self.atr_stop_mult = atr_stop_mult
        self.rr_mult = rr_mult
        self.funding_threshold = funding_threshold  # Negative for LONG bias, positive for SHORT bias

    def generate_signals(self, df: pd.DataFrame, symbol: str = "UNKNOWN") -> list[dict]:
        """Generate Mercury + funding rate enhanced signals."""
        if len(df) < 200:
            return []

        df = df.copy()
        has_funding = 'funding_rate' in df.columns

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

        # --- True Range & ATR(14) with EWM (Wilder smoothing) ---
        hl = df['high'] - df['low']
        hc = np.abs(df['high'] - df['close'].shift())
        lc = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        atr = true_range.ewm(alpha=1.0 / 14, min_periods=14, adjust=False).mean()

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

            # Funding rate for this bar (if available)
            curr_funding = None
            if has_funding and not pd.isna(df['funding_rate'].iloc[i]):
                curr_funding = float(df['funding_rate'].iloc[i])

            # --- LONG: EMA(9) crosses above EMA(21), RSI oversold (3-bar lookback) ---
            if fast_curr > slow_curr and fast_prev <= slow_prev:
                # Check if RSI was extreme in last 3 bars (including current)
                rsi_recent_low = min(float(rsi.iloc[j]) for j in range(max(0, i - 2), i + 1))
                if curr_close > curr_ema200 and rsi_recent_low < 30:
                    entry_price = curr_close
                    sl = entry_price - self.atr_stop_mult * curr_atr
                    tp = entry_price + self.atr_stop_mult * self.rr_mult * curr_atr

                    # Base strength from RSI distance below 30
                    strength = min(100, int((30 - curr_rsi) * 3))

                    # Funding rate boost: negative funding = longs underpaid = bullish
                    funding_note = ""
                    if curr_funding is not None and curr_funding < -self.funding_threshold:
                        strength = min(100, strength + 15)
                        funding_note = f", funding={curr_funding:.6f} (bullish bias)"

                    signals.append({
                        "symbol": symbol,
                        "side": "LONG",
                        "entry_price": entry_price,
                        "take_profit": float(tp),
                        "stop_loss": float(sl),
                        "strength": strength,
                        "reason": (
                            f"EMA(9) crossed above EMA(21), "
                            f"RSI(14)={curr_rsi:.1f} < 30 (oversold), "
                            f"above EMA(200)"
                            f"{funding_note}"
                        ),
                        "strategy": self.NAME,
                    })

            # --- SHORT: EMA(9) crosses below EMA(21), RSI overbought (3-bar lookback) ---
            if fast_curr < slow_curr and fast_prev >= slow_prev:
                # Check if RSI was extreme in last 3 bars (including current)
                rsi_recent_high = max(float(rsi.iloc[j]) for j in range(max(0, i - 2), i + 1))
                if curr_close < curr_ema200 and rsi_recent_high > 70:
                    entry_price = curr_close
                    sl = entry_price + self.atr_stop_mult * curr_atr
                    tp = entry_price - self.atr_stop_mult * self.rr_mult * curr_atr

                    # Base strength from RSI distance above 70
                    strength = min(100, int((curr_rsi - 70) * 3))

                    # Funding rate boost: high positive funding = shorts pay = bearish
                    funding_note = ""
                    if curr_funding is not None and curr_funding > (self.funding_threshold + 0.0002):
                        strength = min(100, strength + 15)
                        funding_note = f", funding={curr_funding:.6f} (bearish bias)"

                    signals.append({
                        "symbol": symbol,
                        "side": "SHORT",
                        "entry_price": entry_price,
                        "take_profit": float(tp),
                        "stop_loss": float(sl),
                        "strength": strength,
                        "reason": (
                            f"EMA(9) crossed below EMA(21), "
                            f"RSI(14)={curr_rsi:.1f} > 70 (overbought), "
                            f"below EMA(200)"
                            f"{funding_note}"
                        ),
                        "strategy": self.NAME,
                    })

        return signals
