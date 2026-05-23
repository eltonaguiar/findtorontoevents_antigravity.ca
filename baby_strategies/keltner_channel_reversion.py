"""
Keltner Channel Mean Reversion Strategy
Academic source: Chester Keltner (1960), modernized by Linda Raschke (1996)
Price touching outer Keltner Channel band + RSI confirmation = mean reversion entry.
Similar to Bollinger Band touch but uses ATR-based bands (more adaptive to volatility).
"""

import pandas as pd
import numpy as np


SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "SUIUSDT",
    "INJUSDT", "NEARUSDT", "HBARUSDT", "ARBUSDT", "OPUSDT",
    "FETUSDT", "TIAUSDT", "SEIUSDT", "AAVEUSDT", "ETCUSDT",
]

class KeltnerChannelReversionStrategy:
    """
    Keltner Channel Mean Reversion.
    LONG: Close touches/pierces lower Keltner band (EMA20 - 2.5*ATR) AND RSI(14) < 40
          AND Close > 200 SMA.
    SHORT: Close touches/pierces upper Keltner band (EMA20 + 2.5*ATR) AND RSI(14) > 60
           AND Close < 200 SMA.
    """
    NAME = "keltner_channel_reversion"
    DESCRIPTION = "Keltner Channel (EMA20, 2.5*ATR) touch with RSI confirmation"
    ENTRY_RULES = (
        "LONG: Close <= Lower Keltner (EMA20 - 2.5*ATR) AND RSI(14) < 40 AND Close > 200 SMA; "
        "SHORT: Close >= Upper Keltner (EMA20 + 2.5*ATR) AND RSI(14) > 60 AND Close < 200 SMA"
    )
    EXIT_RULES = "TP = 2.0x ATR (back to EMA center), SL = 1.5x ATR"
    ACADEMIC_SOURCE = "Keltner (1960), Raschke & Connors (1996) 'Street Smarts'"
    EXPECTED_WR = "58-65%"
    EXPECTED_TRADES_PER_YEAR = "25-50 per symbol"

    def __init__(self, ema_period: int = 20, atr_mult: float = 2.5,
                 tp_atr_mult: float = 2.0, sl_atr_mult: float = 1.5):
        self.ema_period = ema_period
        self.atr_mult = atr_mult
        self.tp_atr_mult = tp_atr_mult
        self.sl_atr_mult = sl_atr_mult

    def generate_signals(self, df: pd.DataFrame, symbol: str = "UNKNOWN") -> list[dict]:
        """Generate Keltner Channel mean reversion signals."""
        if len(df) < 200:
            return []

        df = df.copy()

        # EMA(20) center line
        ema20 = df['close'].ewm(span=self.ema_period, adjust=False).mean()

        # ATR(14) with Wilder smoothing
        hl = df['high'] - df['low']
        hc = np.abs(df['high'] - df['close'].shift())
        lc = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1.0 / 14, min_periods=14, adjust=False).mean()

        # Keltner bands
        upper_band = ema20 + self.atr_mult * atr
        lower_band = ema20 - self.atr_mult * atr

        # RSI(14)
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1.0 / 14, min_periods=14, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1.0 / 14, min_periods=14, adjust=False).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        # 200 SMA trend filter
        sma200 = df['close'].rolling(window=200).mean()

        signals = []

        for i in range(200, len(df)):
            if pd.isna(upper_band.iloc[i]) or pd.isna(rsi.iloc[i]) or pd.isna(sma200.iloc[i]):
                continue

            curr_close = float(df['close'].iloc[i])
            curr_atr = float(atr.iloc[i])
            curr_rsi = float(rsi.iloc[i])
            curr_upper = float(upper_band.iloc[i])
            curr_lower = float(lower_band.iloc[i])
            curr_sma200 = float(sma200.iloc[i])
            curr_ema = float(ema20.iloc[i])

            if curr_atr <= 0:
                continue

            # LONG: Price touches/pierces lower band, RSI < 40, above 200 SMA
            if curr_close <= curr_lower and curr_rsi < 40 and curr_close > curr_sma200:
                entry_price = curr_close
                tp = entry_price + self.tp_atr_mult * curr_atr
                sl = entry_price - self.sl_atr_mult * curr_atr
                # Measure how far below band (deeper = stronger signal)
                depth = (curr_lower - curr_close) / curr_atr if curr_atr > 0 else 0
                strength = min(100, int(50 + depth * 30 + (40 - curr_rsi)))

                signals.append({
                    "symbol": symbol,
                    "side": "LONG",
                    "entry_price": entry_price,
                    "take_profit": float(tp),
                    "stop_loss": float(sl),
                    "strength": max(10, strength),
                    "reason": (
                        f"Price ${curr_close:.2f} at lower Keltner ${curr_lower:.2f}, "
                        f"RSI(14)={curr_rsi:.1f}, above 200SMA, "
                        f"target EMA20=${curr_ema:.2f}"
                    ),
                    "strategy": self.NAME,
                })

            # SHORT: Price touches/pierces upper band, RSI > 60, below 200 SMA
            elif curr_close >= curr_upper and curr_rsi > 60 and curr_close < curr_sma200:
                entry_price = curr_close
                tp = entry_price - self.tp_atr_mult * curr_atr
                sl = entry_price + self.sl_atr_mult * curr_atr
                depth = (curr_close - curr_upper) / curr_atr if curr_atr > 0 else 0
                strength = min(100, int(50 + depth * 30 + (curr_rsi - 60)))

                signals.append({
                    "symbol": symbol,
                    "side": "SHORT",
                    "entry_price": entry_price,
                    "take_profit": float(tp),
                    "stop_loss": float(sl),
                    "strength": max(10, strength),
                    "reason": (
                        f"Price ${curr_close:.2f} at upper Keltner ${curr_upper:.2f}, "
                        f"RSI(14)={curr_rsi:.1f}, below 200SMA, "
                        f"target EMA20=${curr_ema:.2f}"
                    ),
                    "strategy": self.NAME,
                })

        return signals
