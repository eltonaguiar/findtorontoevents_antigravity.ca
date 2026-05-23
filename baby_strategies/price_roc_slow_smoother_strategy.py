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


class PriceRocSlowSmootherStrategy:
    """Slow ROC Smoother — DNA mutation of PriceRocMeanReversion.
    Uses longer lookback periods to filter noise and capture real moves.
    Entry: ROC(14) < -3% AND price below EMA(50) AND volume > 1.8× median(100).
    Exit: TP/SL hit (ATR-21 based, asymmetric 2:1.2 reward:risk).
    """
    NAME = "price_roc_slow_smoother"
    DESCRIPTION = "Slow ROC + EMA(50) + volume spike mean-reversion (noise-filtered)"
    ENTRY_RULES = "ROC(14) < -0.03, price < EMA(50), volume > 1.8 * median(volume, 100)"
    EXIT_RULES = "TP = 2×ATR(21), SL = 1.2×ATR(21), max hold 12 bars"
    ACADEMIC_SOURCE = "John Ehlers, 2004, 'Rocket Science for Traders', ROC mean-reversion (slow variant)"
    EXPECTED_WR = "50-60%"
    EXPECTED_TRADES_PER_YEAR = "15-30 per symbol"
    MUTATION_OF = "price_roc_mean_reversion"
    MUTATION_TYPE = "parameter_shift"
    MUTATION_NOTES = "ROC 5→14, EMA 20→50, ATR 14→21, threshold -2%→-3%, vol window 50→100, vol mult 1.5→1.8, TP 3→2 ATR, SL 2→1.2 ATR, hold 15→12"

    def __init__(self, tp_atr_mult: float = 2.0, sl_atr_mult: float = 1.2, max_hold_days: int = 12):
        self.tp_atr_mult = tp_atr_mult
        self.sl_atr_mult = sl_atr_mult
        self.max_hold_days = max_hold_days

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add ROC(14), EMA(50), ATR(21), and median volume(100) to dataframe."""
        df = df.copy()
        # ROC 14 period — captures real price moves, not noise
        df['roc_14'] = df['close'].pct_change(periods=14)
        # EMA 50 period — stronger trend filter
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        # ATR 21 period — smoother volatility measure
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr_21'] = tr.rolling(window=21).mean()
        # Median volume for rolling window of 100 bars
        df['median_vol_100'] = df['volume'].rolling(window=100).median()
        return df

    def generate_signals(self, df: pd.DataFrame, symbol: str = "BTCUSDT") -> list[dict]:
        df = self.compute_indicators(df.copy())
        signals = []
        for i in range(200, len(df)):
            row = df.iloc[i]
            # Ensure required indicators are not NaN
            if pd.isna(row['roc_14']) or pd.isna(row['ema_50']) or pd.isna(row['atr_21']) or pd.isna(row['median_vol_100']):
                continue
            # Entry condition: deeper dip + stronger trend filter + higher volume bar
            if (row['roc_14'] < -0.03) and (row['close'] < row['ema_50']) and (row['volume'] > 1.8 * row['median_vol_100']):
                atr = row['atr_21']
                entry_price = row['close']
                signals.append(Signal(
                    symbol=symbol,
                    direction="LONG",
                    confidence=0.75,
                    entry_price=entry_price,
                    take_profit=entry_price + atr * self.tp_atr_mult,
                    stop_loss=entry_price - atr * self.sl_atr_mult,
                    reason=f"SlowROC={row['roc_14']:.3%}, EMA50 gap, vol spike {row['volume']/row['median_vol_100']:.1f}x"
                ))
        return signals
