import pandas as pd
import numpy as np
import sys, os

SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "SUIUSDT",
    "INJUSDT", "NEARUSDT", "HBARUSDT", "ARBUSDT", "OPUSDT",
    "FETUSDT", "TIAUSDT", "SEIUSDT", "AAVEUSDT", "ETCUSDT",
]

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from market_structure_volume import Signal

class PriceRocTrendAlignedStrategy:
    """Trend-aligned mean-reversion using Price ROC dips within confirmed uptrends.

    DNA Mutation of PriceRocMeanReversionStrategy (13% WR catastrophic failure).
    Key insight: Mean reversion works WITH trend, not against it.

    Entry: ROC(5) < -2.5% AND price > EMA(200) AND price < EMA(20)
           AND EMA(20) > EMA(50) AND volume > 1.5 * median(volume, 50)
    Exit: TP = 2×ATR(14), SL = 1.5×ATR(14), max hold = 10 bars

    Mutation changes from original:
    - Tighter ROC threshold (-2.5% vs -2%)
    - EMA(200) uptrend filter (price must be above)
    - EMA(20) > EMA(50) confirming uptrend structure
    - Tighter TP/SL (2×/1.5× ATR vs 3×/2×)
    - Shorter max hold (10 vs 15 bars)
    """
    NAME = "price_roc_trend_aligned"
    DESCRIPTION = "Trend-aligned ROC mean-reversion: dip-buy in confirmed uptrends only"
    ENTRY_RULES = "ROC(5) < -0.025, price > EMA(200), price < EMA(20), EMA(20) > EMA(50), volume > 1.5 * median(volume)"
    EXIT_RULES = "TP = 2×ATR(14) or SL = 1.5×ATR(14) or max_hold = 10 bars"
    ACADEMIC_SOURCE = "Ehlers 2004 ROC mean-reversion + trend filter (Faber 2007 200-day MA)"
    EXPECTED_WR = "55-65%"
    EXPECTED_TRADES_PER_YEAR = "10-25 per symbol"

    def __init__(self, tp_atr_mult: float = 2.0, sl_atr_mult: float = 1.5, max_hold_days: int = 10):
        self.tp_atr_mult = tp_atr_mult
        self.sl_atr_mult = sl_atr_mult
        self.max_hold_days = max_hold_days

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add ROC(5), EMA(20), EMA(50), EMA(200), ATR(14), and median volume."""
        df = df.copy()
        df['roc_5'] = df['close'].pct_change(periods=5)
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
        # ATR 14 period
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr_14'] = tr.rolling(window=14).mean()
        df['median_vol_50'] = df['volume'].rolling(window=50).median()
        return df

    def generate_signals(self, df: pd.DataFrame, symbol: str = "BTCUSDT") -> list[dict]:
        df = self.compute_indicators(df.copy())
        signals = []
        for i in range(200, len(df)):
            row = df.iloc[i]
            # Skip if any indicator is NaN
            if pd.isna(row['roc_5']) or pd.isna(row['ema_20']) or pd.isna(row['ema_50']) or pd.isna(row['ema_200']) or pd.isna(row['atr_14']) or pd.isna(row['median_vol_50']):
                continue
            # Entry conditions — trend-aligned mean reversion
            if (row['roc_5'] < -0.025                          # ROC dip: 5-bar drop > 2.5%
                and row['close'] > row['ema_200']              # Price above EMA(200) — in uptrend
                and row['close'] < row['ema_20']               # Price below EMA(20) — local dip
                and row['ema_20'] > row['ema_50']              # EMA stack confirms uptrend
                and row['volume'] > 1.5 * row['median_vol_50'] # Volume spike
            ):
                atr = row['atr_14']
                entry_price = row['close']
                signals.append(Signal(
                    symbol=symbol,
                    direction="LONG",
                    confidence=0.8,
                    entry_price=entry_price,
                    take_profit=entry_price + atr * self.tp_atr_mult,
                    stop_loss=entry_price - atr * self.sl_atr_mult,
                    reason=f"TrendAlignedROC: ROC={row['roc_5']:.3%}, above EMA200, below EMA20, EMA20>EMA50, vol spike"
                ))
        return signals
