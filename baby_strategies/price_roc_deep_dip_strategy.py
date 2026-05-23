"""
PriceRocDeepDipStrategy - DNA Mutation of PriceRocMeanReversion
================================================================

Mutation: "Deep Dip RSI Filter"
Parent: price_roc_mean_reversion (banned: 13% WR, Sharpe -15 on BTC)

Changes from parent:
- ROC(5) threshold: < -5% (was -2%) -- only enter on deep dips
- Added RSI(14) < 30 oversold filter
- Volume spike: > 2.0x median (was 1.5x)
- TP = 2.5x ATR (was 3x), SL = 1.5x ATR (was 2x) -- tighter risk
- Max hold: 10 bars (was 15)

Hypothesis: The parent failed because -2% ROC is noise, not a real dip.
By requiring -5% ROC + RSI<30, we only enter genuine capitulation events
where mean-reversion has a statistical edge.
"""

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



class PriceRocDeepDipStrategy:
    """Deep dip mean-reversion: ROC(5) < -5% + RSI(14) < 30 + volume spike."""

    NAME = "price_roc_deep_dip"
    DESCRIPTION = "Deep dip ROC + RSI oversold + volume spike mean-reversion"
    ENTRY_RULES = "ROC(5) < -0.05, RSI(14) < 30, price < EMA(20), volume > 2.0 * median(volume)"
    EXIT_RULES = "TP/SL hit or max hold 10 bars"
    ACADEMIC_SOURCE = "Ehlers 2004 ROC + Wilder 1978 RSI oversold confluence"
    EXPECTED_WR = "55-65%"
    EXPECTED_TRADES_PER_YEAR = "5-15 per symbol (selective)"
    MUTATION_OF = "price_roc_mean_reversion"

    def __init__(self, tp_atr_mult: float = 2.5, sl_atr_mult: float = 1.5, max_hold_days: int = 10):
        self.tp_atr_mult = tp_atr_mult
        self.sl_atr_mult = sl_atr_mult
        self.max_hold_days = max_hold_days

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add ROC(5), RSI(14), EMA(20), ATR(14), and median volume."""
        df = df.copy()
        # ROC 5 period
        df['roc_5'] = df['close'].pct_change(periods=5)
        # RSI 14 period
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(com=13, adjust=False).mean()
        avg_loss = loss.ewm(com=13, adjust=False).mean()
        rs = avg_gain / avg_loss
        df['rsi_14'] = 100 - (100 / (1 + rs))
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

    def generate_signals(self, df: pd.DataFrame, symbol: str = "BTCUSDT") -> list:
        df = self.compute_indicators(df.copy())
        signals = []
        for i in range(200, len(df)):
            row = df.iloc[i]
            # Ensure required indicators are not NaN
            if pd.isna(row['roc_5']) or pd.isna(row['rsi_14']) or pd.isna(row['ema_20']) \
               or pd.isna(row['atr_14']) or pd.isna(row['median_vol_50']):
                continue
            # Entry conditions: deep dip + oversold + below EMA + volume spike
            if (row['roc_5'] < -0.05
                    and row['rsi_14'] < 30
                    and row['close'] < row['ema_20']
                    and row['volume'] > 2.0 * row['median_vol_50']):
                atr = row['atr_14']
                entry_price = row['close']
                signals.append(Signal(
                    symbol=symbol,
                    direction="LONG",
                    confidence=0.85,
                    entry_price=entry_price,
                    take_profit=entry_price + atr * self.tp_atr_mult,
                    stop_loss=entry_price - atr * self.sl_atr_mult,
                    reason=f"DeepDip ROC={row['roc_5']:.3%}, RSI={row['rsi_14']:.1f}, vol spike"
                ))
        return signals
