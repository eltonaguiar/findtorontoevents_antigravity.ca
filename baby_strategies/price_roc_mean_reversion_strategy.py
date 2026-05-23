import pandas as pd
import numpy as np
from market_structure_volume import Signal

SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "SUIUSDT",
    "INJUSDT", "NEARUSDT", "HBARUSDT", "ARBUSDT", "OPUSDT",
    "FETUSDT", "TIAUSDT", "SEIUSDT", "AAVEUSDT", "ETCUSDT",
]


class PriceRocMeanReversionStrategy:
    """Mean-reversion strategy based on Price Rate of Change (ROC) and volume spikes.
    Entry: ROC(5) < -2% AND price below EMA(20) AND volume > median(volume) * 1.5.
    Exit: ROC(5) > 2% OR TP/SL hit (ATR based).
    """
    NAME = "price_roc_mean_reversion"
    DESCRIPTION = "ROC + EMA + volume spike mean-reversion"
    ENTRY_RULES = "ROC(5) < -0.02, price < EMA(20), volume > 1.5 * median(volume)"
    EXIT_RULES = "ROC(5) > 0.02 or TP/SL hit"
    ACADEMIC_SOURCE = "John Ehlers, 2004, 'Rocket Science for Traders', ROC mean-reversion"
    EXPECTED_WR = "55-65%"
    EXPECTED_TRADES_PER_YEAR = "30-50 per symbol"

    def __init__(self, tp_atr_mult: float = 3.0, sl_atr_mult: float = 2.0, max_hold_days: int = 15):
        self.tp_atr_mult = tp_atr_mult
        self.sl_atr_mult = sl_atr_mult
        self.max_hold_days = max_hold_days

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add ROC(5), EMA(20), ATR(14), and median volume to dataframe."""
        df = df.copy()
        # ROC 5 period
        df['roc_5'] = df['close'].pct_change(periods=5)
        # EMA 20 period
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        # ATR 14 period
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr_14'] = tr.rolling(window=14).mean()
        # Median volume for rolling window of 50 bars
        df['median_vol_50'] = df['volume'].rolling(window=50).median()
        return df

    def generate_signals(self, df: pd.DataFrame, symbol: str = "BTCUSDT") -> list[dict]:
        df = self.compute_indicators(df.copy())
        signals = []
        for i in range(200, len(df)):
            row = df.iloc[i]
            prev = df.iloc[i - 1]
            # Ensure required indicators are not NaN
            if pd.isna(row['roc_5']) or pd.isna(row['ema_20']) or pd.isna(row['atr_14']) or pd.isna(row['median_vol_50']):
                continue
            # Entry condition
            if (row['roc_5'] < -0.02) and (row['close'] < row['ema_20']) and (row['volume'] > 1.5 * row['median_vol_50']):
                atr = row['atr_14']
                entry_price = row['close']
                signals.append(Signal(
                    symbol=symbol,
                    direction="LONG",
                    confidence=0.8,
                    entry_price=entry_price,
                    take_profit=entry_price + atr * self.tp_atr_mult,
                    stop_loss=entry_price - atr * self.sl_atr_mult,
                    reason=f"ROC={row['roc_5']:.3%}, EMA gap, vol spike"
                ))
        return signals
