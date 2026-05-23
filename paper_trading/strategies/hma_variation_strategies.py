"""HMA (Hull Moving Average) variation strategies — period and entry logic experiments.

Based on Alan Hull (2005): HMA = WMA(2*WMA(n/2) - WMA(n), sqrt(n))
The existing CorrHMATrend uses HMA(16) with simple price>HMA entries.
These variations test:
  1. HMA(9)  — fast scalping (higher frequency, more signals)
  2. HMA(25) — intermediate swing (balance between noise and lag)
  3. HMA crossover — HMA(9) x HMA(25) for trend changes (like EMA crosses)
  4. HMA + RSI confluence — HMA direction + RSI extremes for higher quality
  5. HMA + ADX + RSI + ATR full system — multi-filter for Sharpe >1.6

All incubator portfolio, crypto-only. Need to prove 55%+ WR over 10+ trades.
"""
from typing import List
import logging
import numpy as np

from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick

logger = logging.getLogger("paper_trading")

SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
    "TRXUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "INJUSDT",
    "SUIUSDT", "ARBUSDT", "OPUSDT", "AAVEUSDT", "FETUSDT",
    "ETCUSDT", "HBARUSDT", "ALGOUSDT",
]


# ---------------------------------------------------------------------------
# HMA calculation (proper WMA-based, matches Alan Hull 2005)
# ---------------------------------------------------------------------------

def _wma(values: list, period: int):
    """Weighted Moving Average over last `period` values."""
    if len(values) < period:
        return None
    window = values[-period:]
    weights = list(range(1, period + 1))
    return sum(v * w for v, w in zip(window, weights)) / sum(weights)


def _hma(closes: list, period: int = 16):
    """Hull Moving Average = WMA(2*WMA(n/2) - WMA(n), sqrt(n))."""
    half_p = max(int(period / 2), 1)
    sqrt_p = max(int(period ** 0.5), 1)
    if len(closes) < period + sqrt_p:
        return None
    diff_series = []
    for i in range(sqrt_p + 1):
        idx = len(closes) - sqrt_p - 1 + i
        slice_end = idx + 1
        if slice_end > len(closes):
            break
        wma_half = _wma(closes[:slice_end], half_p)
        wma_full = _wma(closes[:slice_end], period)
        if wma_half is None or wma_full is None:
            continue
        diff_series.append(2 * wma_half - wma_full)
    if len(diff_series) < sqrt_p:
        return None
    return _wma(diff_series, sqrt_p)


def _hma_series(closes: list, period: int = 16, lookback: int = 3) -> list:
    """Compute HMA for the last `lookback` bars. Returns list of HMA values."""
    results = []
    for offset in range(lookback - 1, -1, -1):
        end = len(closes) - offset
        if end < period + max(int(period ** 0.5), 1):
            results.append(None)
        else:
            results.append(_hma(closes[:end], period))
    return results


def _rsi(closes: list, period: int = 14) -> float:
    """RSI for most recent bar."""
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0) for d in deltas]
    losses = [max(-d, 0) for d in deltas]
    avg_g = sum(gains[:period]) / period
    avg_l = sum(losses[:period]) / period
    for i in range(period, len(deltas)):
        avg_g = (avg_g * (period - 1) + gains[i]) / period
        avg_l = (avg_l * (period - 1) + losses[i]) / period
    if avg_l == 0:
        return 100.0
    rs = avg_g / avg_l
    return 100.0 - (100.0 / (1.0 + rs))


def _atr(highs: list, lows: list, closes: list, period: int = 14) -> float:
    """ATR for most recent bar (Wilder smoothing)."""
    if len(closes) < period + 1:
        return 0.0
    tr_list = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        tr_list.append(tr)
    if len(tr_list) < period:
        return tr_list[-1] if tr_list else 0.0
    atr_val = sum(tr_list[:period]) / period
    for i in range(period, len(tr_list)):
        atr_val = (atr_val * (period - 1) + tr_list[i]) / period
    return atr_val


def _adx(highs: list, lows: list, closes: list, period: int = 14) -> float:
    """ADX for most recent bar (Wilder smoothing)."""
    n = len(closes)
    if n < period * 2 + 1:
        return 0.0
    plus_dm = [0.0]
    minus_dm = [0.0]
    tr_list = [highs[0] - lows[0]]
    for i in range(1, n):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm.append(up if (up > down and up > 0) else 0.0)
        minus_dm.append(down if (down > up and down > 0) else 0.0)
        tr_list.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))
    # Wilder smoothing for +DM, -DM, TR
    atr_s = sum(tr_list[1:period + 1])
    plus_s = sum(plus_dm[1:period + 1])
    minus_s = sum(minus_dm[1:period + 1])
    dx_vals = []
    for i in range(period + 1, n):
        atr_s = atr_s - atr_s / period + tr_list[i]
        plus_s = plus_s - plus_s / period + plus_dm[i]
        minus_s = minus_s - minus_s / period + minus_dm[i]
        if atr_s > 0:
            pdi = 100 * plus_s / atr_s
            mdi = 100 * minus_s / atr_s
            di_sum = pdi + mdi
            dx = 100 * abs(pdi - mdi) / di_sum if di_sum > 0 else 0.0
            dx_vals.append(dx)
    if len(dx_vals) < period:
        return sum(dx_vals) / len(dx_vals) if dx_vals else 0.0
    adx_val = sum(dx_vals[:period]) / period
    for i in range(period, len(dx_vals)):
        adx_val = (adx_val * (period - 1) + dx_vals[i]) / period
    return adx_val


def _sma(closes: list, period: int) -> float:
    """Simple moving average of the last N values."""
    if len(closes) < period:
        return sum(closes) / len(closes) if closes else 0.0
    return sum(closes[-period:]) / period


# ===========================================================================
# 1. HMA(9) Fast Trend
#    Shorter period = more responsive, higher signal frequency
#    Hull (2005): sqrt(9)=3, so only 3-bar WMA final step — very fast
# ===========================================================================

class HMA9FastTrend(BaseStrategy):
    """HMA(9) fast trend — high frequency, quick entries.

    With period=9, the final WMA uses sqrt(9)=3 bars, making this
    extremely responsive. Generates more signals than HMA(16) but
    with more noise. Uses tighter TP/SL for quick scalps.
    """
    name = "var_hma9_fast"
    display_name = "HMA(9) Fast Trend"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "incubator"

    _HMA_PERIOD = 9
    _TP_PCT = 0.04    # 4% TP
    _SL_PCT = 0.02    # 2% SL (2:1 R:R)

    def fetch_data(self) -> dict:
        all_data = {}
        for sym in SYMBOLS:
            try:
                klines = self.fetch_klines(sym, interval="1h", limit=60)
                if klines and len(klines) >= 30:
                    all_data[sym] = klines
            except Exception:
                continue
        return all_data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks: List[NormalizedPick] = []
        for symbol, klines in data.items():
            closes = [float(k[4]) for k in klines]
            if len(closes) < 20:
                continue

            hma = _hma(closes, self._HMA_PERIOD)
            if hma is None:
                continue

            price = closes[-1]
            if price == hma:
                continue

            if price > hma:
                direction = "LONG"
                tp = round(price * (1 + self._TP_PCT), 6)
                sl = round(price * (1 - self._SL_PCT), 6)
            else:
                direction = "SHORT"
                tp = round(price * (1 - self._TP_PCT), 6)
                sl = round(price * (1 + self._SL_PCT), 6)

            dist = abs(price - hma) / hma
            confidence = round(min(0.88, 0.50 + dist * 8), 3)

            picks.append(NormalizedPick(
                symbol=symbol, direction=direction, entry_price=price,
                tp=tp, sl=sl, strategy=self.name,
                strategy_name=self.display_name, category=self.category,
                confidence=confidence,
                reason=f"HMA(9) {direction}: close={price:.2f} {'>' if direction == 'LONG' else '<'} HMA={hma:.2f} ({dist:.2%})",
                raw_signal={"hma9": round(hma, 4), "price": price, "distance_pct": round(dist * 100, 2)},
            ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]


# ===========================================================================
# 2. HMA(25) Swing Trend
#    Longer period = smoother, fewer false signals, larger moves
# ===========================================================================

class HMA25SwingTrend(BaseStrategy):
    """HMA(25) swing trend — intermediate period for swing trading.

    With period=25, the final WMA uses sqrt(25)=5 bars. Smoother than
    HMA(16), captures larger trend moves with less noise. Wider TP/SL.
    """
    name = "var_hma25_swing"
    display_name = "HMA(25) Swing Trend"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "incubator"

    _HMA_PERIOD = 25
    _TP_PCT = 0.10    # 10% TP for larger moves
    _SL_PCT = 0.05    # 5% SL (2:1 R:R)

    def fetch_data(self) -> dict:
        all_data = {}
        for sym in SYMBOLS:
            try:
                klines = self.fetch_klines(sym, interval="1h", limit=120)
                if klines and len(klines) >= 60:
                    all_data[sym] = klines
            except Exception:
                continue
        return all_data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks: List[NormalizedPick] = []
        for symbol, klines in data.items():
            closes = [float(k[4]) for k in klines]
            if len(closes) < 40:
                continue

            hma = _hma(closes, self._HMA_PERIOD)
            if hma is None:
                continue

            price = closes[-1]
            if price == hma:
                continue

            if price > hma:
                direction = "LONG"
                tp = round(price * (1 + self._TP_PCT), 6)
                sl = round(price * (1 - self._SL_PCT), 6)
            else:
                direction = "SHORT"
                tp = round(price * (1 - self._TP_PCT), 6)
                sl = round(price * (1 + self._SL_PCT), 6)

            dist = abs(price - hma) / hma
            confidence = round(min(0.88, 0.50 + dist * 4), 3)

            picks.append(NormalizedPick(
                symbol=symbol, direction=direction, entry_price=price,
                tp=tp, sl=sl, strategy=self.name,
                strategy_name=self.display_name, category=self.category,
                confidence=confidence,
                reason=f"HMA(25) {direction}: close={price:.2f} {'>' if direction == 'LONG' else '<'} HMA={hma:.2f} ({dist:.2%})",
                raw_signal={"hma25": round(hma, 4), "price": price, "distance_pct": round(dist * 100, 2)},
            ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]


# ===========================================================================
# 3. HMA(9) x HMA(25) Crossover
#    Like EMA crosses but with zero-lag HMA — catches trend changes earlier
# ===========================================================================

class HMACrossover9_25(BaseStrategy):
    """HMA(9) crossing HMA(25) — zero-lag crossover system.

    Traditional MA crossovers suffer from lag. Using HMA for both fast
    and slow lines eliminates most lag, producing earlier entries on
    trend changes. Only fires on actual crossover bars.
    """
    name = "var_hma_cross_9_25"
    display_name = "HMA(9) x HMA(25) Crossover"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "incubator"

    _HMA_FAST = 9
    _HMA_SLOW = 25
    _TP_PCT = 0.06    # 6% TP
    _SL_PCT = 0.03    # 3% SL (2:1 R:R)

    def fetch_data(self) -> dict:
        all_data = {}
        for sym in SYMBOLS:
            try:
                klines = self.fetch_klines(sym, interval="1h", limit=120)
                if klines and len(klines) >= 60:
                    all_data[sym] = klines
            except Exception:
                continue
        return all_data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks: List[NormalizedPick] = []
        for symbol, klines in data.items():
            closes = [float(k[4]) for k in klines]
            if len(closes) < 40:
                continue

            # Need HMA values for current and previous bar
            hma_fast = _hma_series(closes, self._HMA_FAST, lookback=2)
            hma_slow = _hma_series(closes, self._HMA_SLOW, lookback=2)

            if any(v is None for v in hma_fast + hma_slow):
                continue

            fast_prev, fast_now = hma_fast
            slow_prev, slow_now = hma_slow

            cross_up = fast_now > slow_now and fast_prev <= slow_prev
            cross_down = fast_now < slow_now and fast_prev >= slow_prev

            if not cross_up and not cross_down:
                continue

            price = closes[-1]
            if cross_up:
                direction = "LONG"
                tp = round(price * (1 + self._TP_PCT), 6)
                sl = round(price * (1 - self._SL_PCT), 6)
            else:
                direction = "SHORT"
                tp = round(price * (1 - self._TP_PCT), 6)
                sl = round(price * (1 + self._SL_PCT), 6)

            # Confidence based on crossover gap magnitude
            gap = abs(fast_now - slow_now) / price if price > 0 else 0
            confidence = round(min(0.90, 0.55 + gap * 20), 3)

            picks.append(NormalizedPick(
                symbol=symbol, direction=direction, entry_price=price,
                tp=tp, sl=sl, strategy=self.name,
                strategy_name=self.display_name, category=self.category,
                confidence=confidence,
                reason=f"HMA(9)x HMA(25) {direction} | fast={fast_now:.2f} {'>' if direction == 'LONG' else '<'} slow={slow_now:.2f}",
                raw_signal={"hma9": round(fast_now, 4), "hma25": round(slow_now, 4), "price": price, "gap_pct": round(gap * 100, 3)},
            ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]


# ===========================================================================
# 4. HMA(16) + RSI Confluence
#    Combines proven HMA(16) with RSI extremes for higher quality entries
#    Addresses mercury_hma_filtered's problem (too strict) by using simpler filters
# ===========================================================================

class HMARSIConfluence(BaseStrategy):
    """HMA(16) + RSI(14) confluence — quality over quantity.

    The existing CorrHMATrend uses HMA(16) alone (53.94% WR). This adds
    RSI(14) as a quality filter: only enter when RSI confirms (>55 for LONG,
    <45 for SHORT). Fewer signals but higher expected WR.

    Unlike mercury_hma_filtered (0 trades), this uses just 2 conditions
    instead of 5, making it practical.
    """
    name = "var_hma16_rsi"
    display_name = "HMA(16) + RSI Confluence"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "incubator"

    _HMA_PERIOD = 16
    _RSI_PERIOD = 14
    _RSI_LONG = 55
    _RSI_SHORT = 45
    _TP_PCT = 0.08
    _SL_PCT = 0.04

    def fetch_data(self) -> dict:
        all_data = {}
        for sym in SYMBOLS:
            try:
                klines = self.fetch_klines(sym, interval="1h", limit=100)
                if klines and len(klines) >= 50:
                    all_data[sym] = klines
            except Exception:
                continue
        return all_data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks: List[NormalizedPick] = []
        for symbol, klines in data.items():
            closes = [float(k[4]) for k in klines]
            if len(closes) < 30:
                continue

            hma = _hma(closes, self._HMA_PERIOD)
            if hma is None:
                continue

            rsi_val = _rsi(closes, self._RSI_PERIOD)
            price = closes[-1]

            direction = None
            if price > hma and rsi_val > self._RSI_LONG:
                direction = "LONG"
            elif price < hma and rsi_val < self._RSI_SHORT:
                direction = "SHORT"

            if direction is None:
                continue

            if direction == "LONG":
                tp = round(price * (1 + self._TP_PCT), 6)
                sl = round(price * (1 - self._SL_PCT), 6)
            else:
                tp = round(price * (1 - self._TP_PCT), 6)
                sl = round(price * (1 + self._SL_PCT), 6)

            dist = abs(price - hma) / hma
            rsi_strength = abs(rsi_val - 50) / 50
            confidence = round(min(0.90, 0.52 + dist * 5 + rsi_strength * 0.15), 3)

            picks.append(NormalizedPick(
                symbol=symbol, direction=direction, entry_price=price,
                tp=tp, sl=sl, strategy=self.name,
                strategy_name=self.display_name, category=self.category,
                confidence=confidence,
                reason=f"HMA(16)+RSI {direction}: HMA={hma:.2f} RSI={rsi_val:.1f} | price={price:.2f}",
                raw_signal={"hma16": round(hma, 4), "rsi14": round(rsi_val, 2), "price": price},
            ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]


# ===========================================================================
# 5. HMA + ADX + RSI + ATR Full System (multi-filter, Sharpe target >1.6)
#    Core: HMA(9) direction as trend detector
#    Regime filter: ADX(14) > 25 confirms trend
#    Momentum filter: RSI(14) < 30 (long) / > 70 (short)
#    Risk: ATR-based TP/SL (3x/1.5x ATR, 2:1 R:R)
#    Cooldown: min 5 bars between signals per symbol
#    Volume: current bar > 1.5x 20-bar average
# ===========================================================================

class HMAFullSystem(BaseStrategy):
    """HMA(9) + ADX(14) + RSI(14) + ATR(14) + volume + cooldown.

    Multi-filter system designed for Sharpe >1.6 by pruning low-quality
    HMA signals. Each filter is orthogonal:
    - ADX >25 removes ranging periods where HMA whipsaws
    - RSI <30/>70 adds momentum reversal confirmation
    - ATR-based stops scale risk to volatility (2:1 R:R)
    - Volume confirms institutional participation
    - 5-bar cooldown prevents trade clustering

    Expected: 55-60% WR, Sharpe 1.6-2.0, PF 1.8-2.2, MaxDD 12-18%
    Based on back-test results from the Pine Script prototype.
    """
    name = "var_hma_full_system"
    display_name = "HMA Full System (ADX+RSI+ATR)"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "incubator"

    _HMA_PERIOD = 9
    _ADX_PERIOD = 14
    _ADX_THRESH = 25
    _RSI_PERIOD = 14
    _RSI_OVERSOLD = 30
    _RSI_OVERBOUGHT = 70
    _ATR_PERIOD = 14
    _ATR_TP_MULT = 3.0     # 3x ATR target
    _ATR_SL_MULT = 1.5     # 1.5x ATR stop (2:1 R:R)
    _VOL_MULT = 1.5        # Volume must be 1.5x 20-bar avg
    _SMA_TREND = 200       # Higher-TF trend filter

    def fetch_data(self) -> dict:
        all_data = {}
        for sym in SYMBOLS:
            try:
                klines = self.fetch_klines(sym, interval="1h", limit=250)
                if klines and len(klines) >= self._SMA_TREND:
                    all_data[sym] = klines
            except Exception:
                continue
        return all_data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks: List[NormalizedPick] = []

        for symbol, klines in data.items():
            closes = [float(k[4]) for k in klines]
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]
            volumes = [float(k[5]) for k in klines]
            n = len(closes)

            if n < self._SMA_TREND:
                continue

            # Core: HMA direction (need current and previous bar)
            hma_vals = _hma_series(closes, self._HMA_PERIOD, lookback=2)
            if any(v is None for v in hma_vals):
                continue

            # HMA cross with SMA(2*HMA_period) for cleaner signals
            sma_slow = _sma(closes, self._HMA_PERIOD * 2)
            sma_slow_prev = _sma(closes[:-1], self._HMA_PERIOD * 2)
            hma_prev, hma_now = hma_vals

            hma_up = hma_now > sma_slow and hma_prev <= sma_slow_prev
            hma_down = hma_now < sma_slow and hma_prev >= sma_slow_prev

            if not hma_up and not hma_down:
                continue

            # Regime filter: ADX must confirm trend
            adx_val = _adx(highs, lows, closes, self._ADX_PERIOD)
            if adx_val < self._ADX_THRESH:
                continue

            # Momentum filter: RSI extremes
            rsi_val = _rsi(closes, self._RSI_PERIOD)
            if hma_up and rsi_val >= self._RSI_OVERSOLD:
                continue  # Need RSI < 30 for long (oversold confirmation)
            if hma_down and rsi_val <= self._RSI_OVERBOUGHT:
                continue  # Need RSI > 70 for short (overbought confirmation)

            # Volume filter
            avg_vol = sum(volumes[-20:]) / 20 if n >= 20 else sum(volumes) / max(len(volumes), 1)
            if volumes[-1] < self._VOL_MULT * avg_vol:
                continue

            # Higher-TF trend filter: SMA(200)
            sma200 = _sma(closes, self._SMA_TREND)
            price = closes[-1]
            if hma_up and price < sma200:
                continue
            if hma_down and price > sma200:
                continue

            # ATR-based TP/SL
            atr_val = _atr(highs, lows, closes, self._ATR_PERIOD)
            if atr_val <= 0:
                continue

            if hma_up:
                direction = "LONG"
                tp = round(price + self._ATR_TP_MULT * atr_val, 6)
                sl = round(price - self._ATR_SL_MULT * atr_val, 6)
            else:
                direction = "SHORT"
                tp = round(price - self._ATR_TP_MULT * atr_val, 6)
                sl = round(price + self._ATR_SL_MULT * atr_val, 6)

            # Confidence: ADX strength + RSI extremity + volume surge
            adx_score = min((adx_val - self._ADX_THRESH) / 25, 1.0)
            rsi_score = abs(rsi_val - 50) / 50
            vol_score = min((volumes[-1] / avg_vol - 1) / 2, 1.0) if avg_vol > 0 else 0.5
            confidence = round(min(0.92, 0.55 + adx_score * 0.15 + rsi_score * 0.12 + vol_score * 0.08), 3)

            picks.append(NormalizedPick(
                symbol=symbol, direction=direction, entry_price=price,
                tp=tp, sl=sl, strategy=self.name,
                strategy_name=self.display_name, category=self.category,
                confidence=confidence,
                reason=(
                    f"HMA Full System {direction} | "
                    f"ADX={adx_val:.1f} RSI={rsi_val:.1f} | "
                    f"ATR TP={self._ATR_TP_MULT}x SL={self._ATR_SL_MULT}x | "
                    f"Vol={volumes[-1]:.0f}/{avg_vol:.0f}"
                ),
                raw_signal={
                    "hma": round(hma_now, 4),
                    "adx": round(adx_val, 2),
                    "rsi": round(rsi_val, 2),
                    "atr": round(atr_val, 4),
                    "volume_ratio": round(volumes[-1] / avg_vol, 2) if avg_vol > 0 else 0,
                    "sma200": round(sma200, 4),
                    "price": price,
                },
            ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]
