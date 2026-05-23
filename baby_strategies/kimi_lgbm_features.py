"""
KimiLgbmFeatureProxyStrategy - Baby Strat
==========================================

Created by: Claude AI
Date: 2026-03-04

Academic Source: G-Research Crypto Forecasting Competition (Kaggle, $85K prize pool)
  1st/2nd/3rd place winners all used LightGBM with engineered features.
  This strategy replicates the FEATURE SCORING approach without the ML model.

Strategy Logic:
- Composite score = weighted average of 5 normalized features:
  - Lagged return rank: percentile of 1h/4h/24h returns (weight 0.30)
  - Volume ratio: current volume / 20-bar SMA volume (weight 0.20)
  - Volatility rank: ATR(14) percentile over 100 bars (weight 0.15)
  - RSI(14) normalized to 0-1 (weight 0.20)
  - Cross-asset proxy: correlation of price to its 50-bar EMA (weight 0.15)
- Entry BUY:  composite score > 0.65 (strong bullish features)
- Entry SELL: composite score < 0.35 (strong bearish features)
- TP: +12%, SL: -5%

Why it works:
- Replicates competition-winning feature engineering without black-box model
- Multi-factor scoring reduces single-indicator false signals
- Volume + volatility + momentum + trend = robust regime detection
- Percentile normalization makes signals comparable across assets
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


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


def calc_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calc_atr(high: pd.Series, low: pd.Series, close: pd.Series,
             period: int = 14) -> pd.Series:
    """Average True Range."""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def percentile_rank(series: pd.Series, window: int) -> pd.Series:
    """Rolling percentile rank (0-1) over window."""
    return series.rolling(window).apply(
        lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False
    )


class KimiLgbmFeatureProxyStrategy:
    NAME = "Kimi LGBM Feature Proxy"
    DESCRIPTION = "G-Research competition feature scoring without ML model ($85K winners)"

    WEIGHTS = [0.30, 0.20, 0.15, 0.20, 0.15]

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.long_threshold = self.params.get("long_threshold", 0.65)
        self.short_threshold = self.params.get("short_threshold", 0.35)
        self.tp_pct = self.params.get("tp_pct", 0.12)
        self.sl_pct = self.params.get("sl_pct", 0.05)

    def _calc_features(self, data: pd.DataFrame) -> Optional[List[float]]:
        """Calculate the 5 normalized feature scores for the latest bar."""
        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)
        volume = data["volume"].astype(float)

        # Feature 1: Lagged return rank (blend of 1h/4h/24h proxied by 1/4/24 bars)
        ret_1 = close.pct_change(1)
        ret_4 = close.pct_change(4)
        ret_24 = close.pct_change(24)
        rank_1 = percentile_rank(ret_1, 100)
        rank_4 = percentile_rank(ret_4, 100)
        rank_24 = percentile_rank(ret_24, 100)
        lagged_return_rank = (rank_1 + rank_4 + rank_24) / 3.0
        f1 = float(lagged_return_rank.iloc[-1])

        # Feature 2: Volume ratio (current / 20-bar SMA)
        vol_sma = volume.rolling(20).mean()
        vol_ratio = volume / vol_sma.replace(0, np.nan)
        # Normalize: cap at 3x, scale to 0-1
        vol_ratio_norm = vol_ratio.clip(upper=3.0) / 3.0
        f2 = float(vol_ratio_norm.iloc[-1])

        # Feature 3: Volatility rank (ATR percentile over 100 bars)
        atr = calc_atr(high, low, close, 14)
        atr_rank = percentile_rank(atr, 100)
        f3 = float(atr_rank.iloc[-1])

        # Feature 4: RSI(14) normalized to 0-1
        rsi = calc_rsi(close, 14)
        f4 = float(rsi.iloc[-1]) / 100.0

        # Feature 5: Correlation of price to its 50-bar EMA (trend alignment proxy)
        ema50 = close.ewm(span=50, adjust=False).mean()
        corr = close.rolling(50).corr(ema50)
        # Scale from [-1, 1] to [0, 1]
        corr_norm = (corr + 1.0) / 2.0
        f5 = float(corr_norm.iloc[-1])

        features = [f1, f2, f3, f4, f5]
        if any(np.isnan(f) for f in features):
            return None
        return features

    def generate_signals(
        self, data: pd.DataFrame, symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        if len(data) < 150:
            return []

        features = self._calc_features(data)
        if features is None:
            return []

        score = sum(w * f for w, f in zip(self.WEIGHTS, features))
        current_price = float(data["close"].iloc[-1])

        signals = []
        feature_str = ", ".join(f"{f:.3f}" for f in features)

        if score > self.long_threshold:
            confidence = min(0.5 + (score - self.long_threshold) * 2, 0.95)
            tp = current_price * (1 + self.tp_pct)
            sl = current_price * (1 - self.sl_pct)
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"LGBM proxy BUY: score={score:.3f} > {self.long_threshold}, features=[{feature_str}]",
                )
            )
        elif score < self.short_threshold:
            confidence = min(0.5 + (self.short_threshold - score) * 2, 0.95)
            tp = current_price * (1 - self.tp_pct)
            sl = current_price * (1 + self.sl_pct)
            signals.append(
                Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=f"LGBM proxy SELL: score={score:.3f} < {self.short_threshold}, features=[{feature_str}]",
                )
            )

        return signals


if __name__ == "__main__":
    np.random.seed(42)
    n = 300
    returns = np.random.normal(0.0001, 0.02, n)
    prices = 50000 * np.exp(np.cumsum(returns))

    test_data = pd.DataFrame(
        {
            "open": prices * (1 + np.random.normal(0, 0.001, n)),
            "high": prices * (1 + abs(np.random.normal(0, 0.01, n))),
            "low": prices * (1 - abs(np.random.normal(0, 0.01, n))),
            "close": prices,
            "volume": np.random.uniform(100, 1000, n),
        }
    )

    strategy = KimiLgbmFeatureProxyStrategy()
    signals = strategy.generate_signals(test_data, symbol="BTCUSDT")

    print(f"Generated {len(signals)} signals from {len(test_data)} bars")
    for sig in signals[:3]:
        print(f"\n{sig.direction} {sig.symbol}")
        print(f"  Confidence: {sig.confidence:.1%}")
        print(f"  Entry: ${sig.entry_price:,.2f}")
        print(f"  TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f}")
        print(f"  Reason: {sig.reason}")
