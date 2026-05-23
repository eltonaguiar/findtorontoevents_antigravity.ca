"""
MultiTF_TrendVol_Confluence — Mercury AI (Inception)
====================================================
4h ADX trend strength + 1h breakout with volume surge confirmation.

Entry: 4h ADX > 25 (strong trend) AND 1h close > 4h rolling high (long)
       or close < 4h rolling low (short) AND 1h vol > 1.5x SMA-20.
Exit:  TP = 2.0x ATR-14, SL = 1.5x ATR-14.
Filter: Skip if 4h ATR < 0.5% of price (low volatility).

Why unique: ADX-based strength filter + volume surge, not just EMA direction.
Trades both directions. Avoids false breakouts in choppy markets.

Best regime: Trending, moderately volatile markets.
"""
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Signal:
    symbol: str
    direction: str
    confidence: float
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str


class MultiTF_TrendVolConfluenceStrategy:
    """4h ADX trend + 1h breakout with volume surge."""
    name = "multitf_trendvol_confluence"
    version = "1.0.0"
    agent = "mercury_ai"

    def __init__(self, params: Optional[dict] = None):
        self.p = params or {}
        self.adx_period = self.p.get('adx_period', 14)
        self.adx_thresh = self.p.get('adx_thresh', 25)
        self.atr_period = self.p.get('atr_period', 14)
        self.vol_sma_len = self.p.get('vol_sma_len', 20)
        self.vol_mult = self.p.get('vol_mult', 1.5)
        self.tp_mul = self.p.get('tp_mul', 2.0)
        self.sl_mul = self.p.get('sl_mul', 1.5)
        self.rolling_hl = self.p.get('rolling_hl', 80)  # 20 * 4 bars on 1h = 4h equivalent

    def _atr(self, data, period=14):
        tr = pd.concat([
            data['high'] - data['low'],
            (data['high'] - data['close'].shift()).abs(),
            (data['low'] - data['close'].shift()).abs()
        ], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    def _adx(self, high, low, close, period=14):
        """Compute ADX from OHLC series"""
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs()
        ], axis=1).max(axis=1)

        up = high.diff()
        down = -low.diff()
        plus_dm = np.where((up > down) & (up > 0), up, 0.0)
        minus_dm = np.where((down > up) & (down > 0), down, 0.0)

        tr_s = tr.rolling(period).sum()
        plus_s = pd.Series(plus_dm, index=high.index).rolling(period).sum()
        minus_s = pd.Series(minus_dm, index=high.index).rolling(period).sum()

        plus_di = 100 * (plus_s / tr_s)
        minus_di = 100 * (minus_s / tr_s)
        dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10))
        return dx.rolling(period).mean()

    def generate_signals(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> List[Signal]:
        min_bars = max(self.rolling_hl, self.adx_period * 2, self.atr_period) + 10
        if len(data) < min_bars:
            return []

        # 1h indicators
        atr = self._atr(data, self.atr_period)
        vol_sma = data['volume'].rolling(self.vol_sma_len).mean()

        # 4h proxy: ADX on longer window (4x period on 1h data)
        adx = self._adx(data['high'], data['low'], data['close'], self.adx_period * 4)

        # 4h proxy rolling high/low (80 bars on 1h = 20 bars on 4h)
        rolling_high = data['high'].rolling(self.rolling_hl).max()
        rolling_low = data['low'].rolling(self.rolling_hl).min()

        signals = []
        scan_start = max(min_bars, len(data) - 20)
        for i in range(scan_start, len(data)):
            price = data['close'].iloc[i]
            vol = data['volume'].iloc[i]
            atr_val = atr.iloc[i]
            adx_val = adx.iloc[i]

            if pd.isna(atr_val) or pd.isna(adx_val) or atr_val <= 0:
                continue

            # ADX strength filter
            if adx_val < self.adx_thresh:
                continue

            # Low volatility filter: ATR < 0.5% of price
            if atr_val < price * 0.005:
                continue

            # Volume surge
            vol_sma_val = vol_sma.iloc[i]
            if pd.isna(vol_sma_val) or vol < self.vol_mult * vol_sma_val:
                continue

            # Breakout detection
            rh = rolling_high.iloc[i - 1]  # use previous bar's rolling high (avoid look-ahead)
            rl = rolling_low.iloc[i - 1]

            if pd.isna(rh) or pd.isna(rl):
                continue

            direction = None
            if price > rh:
                direction = "BUY"
            elif price < rl:
                direction = "SELL"

            if not direction:
                continue

            if direction == "BUY":
                tp = price + self.tp_mul * atr_val
                sl = price - self.sl_mul * atr_val
            else:
                tp = price - self.tp_mul * atr_val
                sl = price + self.sl_mul * atr_val

            confidence = min(0.95, 0.40 + (adx_val - self.adx_thresh) / self.adx_thresh * 0.6)
            vol_ratio = vol / vol_sma_val if vol_sma_val > 0 else 0

            signals.append(Signal(
                symbol=symbol,
                direction=direction,
                confidence=round(confidence, 2),
                entry_price=price,
                take_profit=tp,
                stop_loss=sl,
                reason=f"ADX {adx_val:.1f}>{self.adx_thresh}, {direction} breakout, vol {vol_ratio:.1f}x"
            ))

        return signals


if __name__ == "__main__":
    np.random.seed(0)
    n = 300
    close = np.cumsum(np.random.randn(n) * 50) + 50000
    high = close + np.abs(np.random.randn(n) * 80)
    low = close - np.abs(np.random.randn(n) * 80)
    volume = np.abs(np.random.randn(n) * 500) + 2000

    df = pd.DataFrame({
        'open': close + np.random.randn(n) * 10,
        'high': high, 'low': low, 'close': close, 'volume': volume
    })

    strat = MultiTF_TrendVolConfluenceStrategy()
    sigs = strat.generate_signals(df)
    print(f"Generated {len(sigs)} signal(s)")
    for s in sigs[:5]:
        print(f"  {s.direction} @ {s.entry_price:.2f}  TP:{s.take_profit:.2f}  SL:{s.stop_loss:.2f}  {s.reason}")
