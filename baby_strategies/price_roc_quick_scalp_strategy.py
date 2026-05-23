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


class PriceRocQuickScalpStrategy:
    """Quick scalp mutation of PriceRocMeanReversion.

    DNA Mutation: "Quick Scalp ROC"
    - ROC(3) < -1.5% (faster 3-bar ROC, smaller threshold)
    - Price below EMA(10) (very short-term filter)
    - Volume > 1.3x median over 20 bars (fast volume check)
    - Previous bar must be red (close < open) — momentum confirmation
    - TP = 1.0×ATR, SL = 0.8×ATR (R:R = 1.25:1)
    - Max hold: 3 bars — scalp mentality, exit fast

    Parent: price_roc_mean_reversion (ROC(5)<-2%, EMA(20), vol>1.5x, TP=3xATR, SL=2xATR)
    Hypothesis: Faster entry + tighter exits may capture quick bounces better than
    the parent's wider parameters which suffered 13% WR and Sharpe -15.
    """
    NAME = "price_roc_quick_scalp"
    DESCRIPTION = "Quick scalp ROC: 3-bar ROC + EMA(10) + tight TP/SL"
    ENTRY_RULES = "ROC(3) < -0.015, price < EMA(10), volume > 1.3 * median(volume, 20), prev bar red"
    EXIT_RULES = "TP = 1.0×ATR or SL = 0.8×ATR or max hold 3 bars"
    ACADEMIC_SOURCE = "Mutation of Ehlers ROC mean-reversion with scalp parameters"
    EXPECTED_WR = "50-60%"
    EXPECTED_TRADES_PER_YEAR = "40-80 per symbol"

    def __init__(self, tp_atr_mult: float = 1.0, sl_atr_mult: float = 0.8, max_hold_days: int = 3):
        self.tp_atr_mult = tp_atr_mult
        self.sl_atr_mult = sl_atr_mult
        self.max_hold_days = max_hold_days

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add ROC(3), EMA(10), ATR(14), and median volume(20) to dataframe."""
        df = df.copy()
        # ROC 3 period
        df['roc_3'] = df['close'].pct_change(periods=3)
        # EMA 10 period
        df['ema_10'] = df['close'].ewm(span=10, adjust=False).mean()
        # ATR 14 period
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr_14'] = tr.rolling(window=14).mean()
        # Median volume for rolling window of 20 bars (fast)
        df['median_vol_20'] = df['volume'].rolling(window=20).median()
        return df

    def generate_signals(self, df: pd.DataFrame, symbol: str = "BTCUSDT") -> list:
        df = self.compute_indicators(df.copy())
        signals = []
        for i in range(50, len(df)):
            row = df.iloc[i]
            prev = df.iloc[i - 1]
            # Ensure required indicators are not NaN
            if pd.isna(row['roc_3']) or pd.isna(row['ema_10']) or pd.isna(row['atr_14']) or pd.isna(row['median_vol_20']):
                continue
            # Entry conditions:
            # 1. ROC(3) < -1.5%
            # 2. Price below EMA(10)
            # 3. Volume > 1.3x median over 20 bars
            # 4. Previous bar is red (close < open) — momentum confirmation
            if (row['roc_3'] < -0.015
                    and row['close'] < row['ema_10']
                    and row['volume'] > 1.3 * row['median_vol_20']
                    and prev['close'] < prev['open']):
                atr = row['atr_14']
                entry_price = row['close']
                signals.append(Signal(
                    symbol=symbol,
                    direction="LONG",
                    confidence=0.7,
                    entry_price=entry_price,
                    take_profit=entry_price + atr * self.tp_atr_mult,
                    stop_loss=entry_price - atr * self.sl_atr_mult,
                    reason=f"ROC3={row['roc_3']:.3%}, <EMA10, vol spike, prev red bar"
                ))
        return signals
