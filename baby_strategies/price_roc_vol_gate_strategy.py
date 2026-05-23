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


class PriceRocVolGateStrategy:
    """Volatility-gated ROC mean-reversion strategy.
    DNA mutation of PriceRocMeanReversion with ATR volatility gate, tighter thresholds,
    and aggressive 2:1 R:R ratio for quick mean-reversion trades in high-vol regimes.

    Entry: ATR(14) > 1.5 * SMA(ATR,50) AND ROC(5) < -3% AND price < EMA(20) AND volume > 2x median(vol,50).
    Exit: TP = 2*ATR, SL = 1*ATR, max hold = 8 bars.
    """
    NAME = "price_roc_vol_gate"
    DESCRIPTION = "ATR vol-gated ROC mean-reversion with 2:1 R:R"
    ENTRY_RULES = "ATR(14) > 1.5*SMA(ATR,50), ROC(5) < -0.03, price < EMA(20), volume > 2*median(vol)"
    EXIT_RULES = "TP = 2*ATR, SL = 1*ATR, max hold 8 bars"
    ACADEMIC_SOURCE = "Ehlers 2004 ROC mean-reversion + ATR regime filter (DNA mutation)"
    EXPECTED_WR = "45-55%"
    EXPECTED_TRADES_PER_YEAR = "10-25 per symbol"

    def __init__(self, tp_atr_mult: float = 2.0, sl_atr_mult: float = 1.0, max_hold_days: int = 8):
        self.tp_atr_mult = tp_atr_mult
        self.sl_atr_mult = sl_atr_mult
        self.max_hold_days = max_hold_days

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add ROC(5), EMA(20), ATR(14), SMA(ATR,50), and median volume."""
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
        # SMA of ATR for volatility gate
        df['atr_sma_50'] = df['atr_14'].rolling(window=50).mean()
        # Median volume for rolling window of 50 bars
        df['median_vol_50'] = df['volume'].rolling(window=50).median()
        return df

    def generate_signals(self, df: pd.DataFrame, symbol: str = "BTCUSDT") -> list:
        df = self.compute_indicators(df.copy())
        signals = []
        for i in range(200, len(df)):
            row = df.iloc[i]
            # Ensure required indicators are not NaN
            if pd.isna(row['roc_5']) or pd.isna(row['ema_20']) or pd.isna(row['atr_14']) or pd.isna(row['atr_sma_50']) or pd.isna(row['median_vol_50']):
                continue
            # Volatility gate: ATR must be elevated (high vol regime)
            if row['atr_14'] <= 1.5 * row['atr_sma_50']:
                continue
            # Entry conditions: deep ROC dip + below EMA + volume spike
            if (row['roc_5'] < -0.03) and (row['close'] < row['ema_20']) and (row['volume'] > 2.0 * row['median_vol_50']):
                atr = row['atr_14']
                entry_price = row['close']
                signals.append(Signal(
                    symbol=symbol,
                    direction="LONG",
                    confidence=0.75,
                    entry_price=entry_price,
                    take_profit=entry_price + atr * self.tp_atr_mult,
                    stop_loss=entry_price - atr * self.sl_atr_mult,
                    reason=f"VolGate ROC={row['roc_5']:.3%}, ATR ratio={row['atr_14']/row['atr_sma_50']:.2f}x, vol spike"
                ))
        return signals
