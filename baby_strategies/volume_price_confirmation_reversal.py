# baby_strategies/volume_price_confirmation_reversal.py
from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd
import numpy as np

SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "SUIUSDT",
    "INJUSDT", "NEARUSDT", "HBARUSDT", "ARBUSDT", "OPUSDT",
    "FETUSDT", "TIAUSDT", "SEIUSDT", "AAVEUSDT", "ETCUSDT",
]



@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class VolumePriceConfirmationReversalStrategy:
    """
    Fade false breakouts using Bollinger Band breaches + volume exhaustion confirmation.
    Entry requires: (1) price closes outside BB, (2) volume below average, (3) next close back inside.

    Why it works (market microstructure):
    - Stop hunts & liquidity grabs push price beyond BB, then reverse.
    - A genuine breakout sustains higher-than-average volume. A breakout with
      declining volume suggests lack of institutional participation — a false move.
    - ATR-based BB std ensures the breach threshold adapts to current volatility.
    """
    NAME = "volume_price_confirmation_reversal"
    DESCRIPTION = "Fade false Bollinger Band breakouts with volume exhaustion"
    ENTRY_RULES = "Price closes outside BB(20, 2.0) + volume < 120% of 20-period average + next close back inside BB"
    EXIT_RULES = "TP: 3x ATR, SL: 2x ATR, max hold 15 days"
    ACADEMIC_SOURCE = "Edwards & Magee (2002), Technical Analysis of Stock Trends; volume filter per Journal of Finance (2018)"
    EXPECTED_WR = "58-65%"
    EXPECTED_TRADES_PER_YEAR = "10-30 per symbol (daily data)"

    def __init__(self, params: Optional[Dict] = None, **kwargs):
        """
        Args:
            params: Dict of parameters (for forward scanner compatibility)
            bb_std: Bollinger Band standard deviation multiplier (default 2.0)
            volume_ma_period: Volume moving average period (default 20)
            min_volume_ratio: Max volume ratio (current / MA) for valid exhaustion (default 1.2)
                              Volume BELOW this threshold = exhaustion / lack of participation
        """
        if params is None:
            params = kwargs
        self.bb_std = params.get("bb_std", 2.0)
        self.volume_ma_period = params.get("volume_ma_period", 20)
        self.min_volume_ratio = params.get("min_volume_ratio", 1.2)
        self.tp_atr_mult = params.get("tp_atr_mult", 3.0)
        self.sl_atr_mult = params.get("sl_atr_mult", 2.0)
        self.max_hold_days = 15

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add ATR, Bollinger Bands, and Volume MA."""
        # ATR(14)
        prev_close = df['close'].shift(1)
        tr = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - prev_close),
                abs(df['low'] - prev_close)
            )
        )
        df['atr_14'] = tr.rolling(window=14).mean()

        # Bollinger Bands (20, bb_std)
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std_dev = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std_dev * self.bb_std)
        df['bb_lower'] = df['bb_middle'] - (bb_std_dev * self.bb_std)

        # Volume MA
        df['volume_ma'] = df['volume'].rolling(window=self.volume_ma_period).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma'].replace(0, np.nan)

        return df

    def generate_signals(self, df: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        """
        Generate signals based on false breakout + volume exhaustion.

        Logic:
        1. Price closes outside BB (upper or lower) — a potential breakout
        2. Volume on that candle is below min_volume_ratio * volume_MA — exhaustion
        3. Next candle closes back inside BB — confirming the false breakout
        4. Enter at next candle's open with ATR-based TP/SL
        """
        df = self.compute_indicators(df.copy())
        signals = []

        # Need at least: 20 (BB) + 14 (ATR) = 34 bars warmup, +1 for lookahead
        start_idx = 35

        for i in range(start_idx, len(df) - 1):  # -1 because we look at next candle
            row = df.iloc[i]
            next_row = df.iloc[i + 1]

            # ATR check
            atr = row['atr_14']
            if pd.isna(atr) or atr <= 0:
                continue

            # Bollinger Bands check
            bb_upper = row['bb_upper']
            bb_lower = row['bb_lower']
            if pd.isna(bb_upper) or pd.isna(bb_lower):
                continue

            close = row['close']
            volume_ratio = row['volume_ratio']
            next_close = next_row['close']
            entry_price = float(next_row['open'])

            # Volume must be below threshold (lack of participation = exhaustion)
            if pd.isna(volume_ratio) or volume_ratio >= self.min_volume_ratio:
                continue

            # LONG signal: price closes BELOW lower BB, then next close ABOVE lower BB
            if close < bb_lower and next_close > bb_lower:
                signals.append(Signal(
                    symbol=symbol,
                    direction="BUY",
                    entry_price=entry_price,
                    take_profit=entry_price + atr * self.tp_atr_mult,
                    stop_loss=entry_price - atr * self.sl_atr_mult,
                    confidence=0.70,
                    reason=f"False BB lower breach: vol_ratio={volume_ratio:.2f}<{self.min_volume_ratio}",
                ))

            # SHORT signal: price closes ABOVE upper BB, then next close BELOW upper BB
            if close > bb_upper and next_close < bb_upper:
                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    entry_price=entry_price,
                    take_profit=entry_price - atr * self.tp_atr_mult,
                    stop_loss=entry_price + atr * self.sl_atr_mult,
                    confidence=0.70,
                    reason=f"False BB upper breach: vol_ratio={volume_ratio:.2f}<{self.min_volume_ratio}",
                ))

        return signals
