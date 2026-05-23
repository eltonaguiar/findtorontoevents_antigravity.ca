"""
Alpha Arena AI Competition Strategies - Baby Strats
====================================================

Created by: AI Assistant
Date: 2026-03-04

Six strategies derived from the Alpha Arena AI crypto trading competition
(Oct-Nov 2025). Top performers used Qwen 3 Max and DeepSeek V3.1.

Strategies:
  1. AlphaAggressivePatience   (Qwen 3 Max) — BTC-only high-conviction golden cross
  2. AlphaRiskParity           (DeepSeek V3.1) — Multi-asset inverse-vol weighting
  3. AlphaFourLayerConfluence  (Unified) — 4-layer simultaneous confirmation
  4. AlphaRegimeSwitcher       (DeepSeek) — ADX-based trend/range regime detection
  5. AlphaDrawdownResponsive   (Both winners) — Vol-scaled momentum with drawdown guard
  6. AlphaPartialScaleOut      (Qwen) — EMA stack + volume with scale-out plan
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass


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


# =============================================================================
# Shared indicator helpers
# =============================================================================

def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    return 100 - 100 / (1 + rs)


def _macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = _ema(series, fast)
    ema_slow = _ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
    high = data['high']
    low = data['low']
    close = data['close']
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period, min_periods=1).mean()


def _adx(data: pd.DataFrame, period: int = 14) -> pd.Series:
    high = data['high']
    low = data['low']
    close = data['close']

    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr_smooth = tr.ewm(span=period, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr_smooth.replace(0, 1e-10))
    minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr_smooth.replace(0, 1e-10))

    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1e-10))
    adx = dx.ewm(span=period, adjust=False).mean()
    return adx


# =============================================================================
# Strategy 1: AlphaAggressivePatience (Qwen 3 Max)
# =============================================================================

class AlphaAggressivePatience:
    """
    BTC-only high-conviction strategy from Alpha Arena winner Qwen 3 Max.
    Waits for golden cross + MACD expansion + RSI sweet spot alignment.
    Only fires when ALL conditions align — patience is the edge.
    """

    NAME = "AlphaAggressivePatience"
    DESCRIPTION = "BTC-only golden cross + MACD expansion + RSI 40-65 sweet spot (Qwen 3 Max, Alpha Arena Oct 2025)"

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.ema_fast = self.params.get('ema_fast', 50)
        self.ema_slow = self.params.get('ema_slow', 200)
        self.rsi_period = self.params.get('rsi_period', 14)
        self.atr_period = self.params.get('atr_period', 14)
        self.swing_lookback = self.params.get('swing_lookback', 10)
        self.min_rr = self.params.get('min_rr', 2.5)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        NAME = "AlphaAggressivePatience"
        DESCRIPTION = "BTC-only golden cross + MACD expansion + RSI 40-65 sweet spot"

        if len(data) < self.ema_slow + 10:
            return []

        close = data['close']
        ema50 = _ema(close, self.ema_fast)
        ema200 = _ema(close, self.ema_slow)
        rsi = _rsi(close, self.rsi_period)
        _, _, macd_hist = _macd(close)
        atr = _atr(data, self.atr_period)

        current_price = float(close.iloc[-1])
        current_atr = float(atr.iloc[-1])

        # Condition 1: Golden cross — EMA(50) > EMA(200)
        golden_cross = float(ema50.iloc[-1]) > float(ema200.iloc[-1])

        # Condition 2: MACD histogram expanding (last 2 bars increasing)
        if len(macd_hist) < 3:
            return []
        macd_expanding = (
            float(macd_hist.iloc[-1]) > float(macd_hist.iloc[-2]) > 0
        )

        # Condition 3: RSI in 40-65 sweet spot with upward slope
        current_rsi = float(rsi.iloc[-1])
        prev_rsi = float(rsi.iloc[-2])
        rsi_sweet = 40 <= current_rsi <= 65
        rsi_rising = current_rsi > prev_rsi

        if not (golden_cross and macd_expanding and rsi_sweet and rsi_rising):
            return []

        # TP at 3x ATR
        tp = current_price + (3.0 * current_atr)

        # SL at swing low (lowest low of last N bars) or 2x ATR, whichever is tighter
        swing_low = float(data['low'].iloc[-self.swing_lookback:].min())
        atr_sl = current_price - (2.0 * current_atr)
        sl = max(swing_low, atr_sl)  # tighter = higher SL

        # Check minimum R:R
        risk = current_price - sl
        reward = tp - current_price
        if risk <= 0 or reward / risk < self.min_rr:
            return []

        rr_ratio = reward / risk
        confidence = min(0.65 + (current_rsi - 40) / 100 + (rr_ratio - 2.5) * 0.05, 0.92)

        return [Signal(
            symbol=symbol,
            direction="BUY",
            confidence=round(confidence, 3),
            entry_price=round(current_price, 8),
            take_profit=round(tp, 8),
            stop_loss=round(sl, 8),
            reason=(
                f"{NAME}: Golden cross + MACD expanding + RSI={current_rsi:.1f} rising | "
                f"R:R={rr_ratio:.1f}:1 | ATR={current_atr:.2f}"
            )
        )]


# =============================================================================
# Strategy 2: AlphaRiskParity (DeepSeek V3.1)
# =============================================================================

class AlphaRiskParity:
    """
    Multi-asset inverse-volatility weighting from DeepSeek V3.1.
    Allocates higher weight to lower-volatility assets, then only enters
    when momentum confirms and allocation is meaningful (>15%).
    """

    NAME = "AlphaRiskParity"
    DESCRIPTION = "Multi-asset inverse-vol weighting + momentum filter (DeepSeek V3.1, Alpha Arena Oct 2025)"

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.vol_period = self.params.get('vol_period', 20)
        self.ema_period = self.params.get('ema_period', 50)
        self.min_weight = self.params.get('min_weight', 0.15)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT",
        all_symbols_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> List[Signal]:
        NAME = "AlphaRiskParity"
        DESCRIPTION = "Multi-asset inverse-vol weighting + momentum filter"

        if len(data) < self.ema_period + 10:
            return []

        close = data['close']
        returns = close.pct_change()
        vol = float(returns.rolling(self.vol_period).std().iloc[-1])

        if vol <= 0 or np.isnan(vol):
            return []

        # Calculate inverse-vol weight
        if all_symbols_data:
            inv_vols = {}
            for sym, df in all_symbols_data.items():
                if len(df) < self.vol_period + 5:
                    continue
                sym_ret = df['close'].pct_change()
                sym_vol = float(sym_ret.rolling(self.vol_period).std().iloc[-1])
                if sym_vol > 0 and not np.isnan(sym_vol):
                    inv_vols[sym] = 1.0 / sym_vol
            total_inv_vol = sum(inv_vols.values()) if inv_vols else 1.0
            vol_weight = inv_vols.get(symbol, 1.0 / vol) / total_inv_vol if total_inv_vol > 0 else 0
        else:
            # Single-asset fallback
            vol_weight = 1.0 / vol
            vol_weight = min(vol_weight * 0.01, 1.0)  # normalize

        # Check minimum weight
        if vol_weight < self.min_weight:
            return []

        # Momentum filter: close > EMA(50)
        ema50 = _ema(close, self.ema_period)
        current_price = float(close.iloc[-1])
        current_ema = float(ema50.iloc[-1])

        if current_price <= current_ema:
            return []

        # TP: +10%, SL: -5%
        tp = current_price * 1.10
        sl = current_price * 0.95

        # Confidence scales with vol_weight
        confidence = min(0.45 + vol_weight * 0.4, 0.88)

        return [Signal(
            symbol=symbol,
            direction="BUY",
            confidence=round(confidence, 3),
            entry_price=round(current_price, 8),
            take_profit=round(tp, 8),
            stop_loss=round(sl, 8),
            reason=(
                f"{NAME}: Inv-vol weight={vol_weight:.2f} | "
                f"Vol={vol:.4f} | Price > EMA({self.ema_period})"
            )
        )]


# =============================================================================
# Strategy 3: AlphaFourLayerConfluence (Unified methodology)
# =============================================================================

class AlphaFourLayerConfluence:
    """
    Four independent confirmation layers must ALL agree before entry.
    Layer 1: Trend (EMA 50/200), Layer 2: RSI momentum,
    Layer 3: BB squeeze breakout, Layer 4: Momentum composite.
    """

    NAME = "AlphaFourLayerConfluence"
    DESCRIPTION = "4-layer simultaneous confirmation: trend + RSI + BB squeeze + momentum composite (Alpha Arena unified)"

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.atr_period = self.params.get('atr_period', 14)
        self.bb_period = self.params.get('bb_period', 20)
        self.bb_std = self.params.get('bb_std', 2.0)
        self.bb_squeeze_lookback = self.params.get('bb_squeeze_lookback', 100)
        self.bb_squeeze_pctile = self.params.get('bb_squeeze_pctile', 20)
        self.vol_avg_period = self.params.get('vol_avg_period', 20)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        NAME = "AlphaFourLayerConfluence"
        DESCRIPTION = "4-layer simultaneous confirmation: trend + RSI + BB squeeze + momentum"

        min_bars = max(200, self.bb_squeeze_lookback) + 10
        if len(data) < min_bars:
            return []

        close = data['close']
        current_price = float(close.iloc[-1])

        # --- Layer 1: Trend (EMA 50 > EMA 200) ---
        ema50 = _ema(close, 50)
        ema200 = _ema(close, 200)
        layer1_bull = float(ema50.iloc[-1]) > float(ema200.iloc[-1])
        layer1_bear = float(ema50.iloc[-1]) < float(ema200.iloc[-1])

        # --- Layer 2: RSI between 30-70, slope > 0 for longs ---
        rsi = _rsi(close, 14)
        current_rsi = float(rsi.iloc[-1])
        prev_rsi = float(rsi.iloc[-2])
        rsi_in_range = 30 <= current_rsi <= 70
        layer2_bull = rsi_in_range and (current_rsi > prev_rsi)
        layer2_bear = rsi_in_range and (current_rsi < prev_rsi)

        # --- Layer 3: Bollinger Band squeeze then breakout ---
        sma_bb = close.rolling(self.bb_period).mean()
        std_bb = close.rolling(self.bb_period).std()
        bb_upper = sma_bb + (std_bb * self.bb_std)
        bb_lower = sma_bb - (std_bb * self.bb_std)
        bandwidth = (bb_upper - bb_lower) / sma_bb

        # Squeeze: bandwidth < 20th percentile of last 100 bars
        lookback_bw = bandwidth.iloc[-self.bb_squeeze_lookback:]
        squeeze_threshold = float(np.nanpercentile(lookback_bw.dropna().values, self.bb_squeeze_pctile))
        recent_bw = float(bandwidth.iloc[-2]) if not pd.isna(bandwidth.iloc[-2]) else 999
        was_squeezed = recent_bw < squeeze_threshold

        # Breakout above upper band
        prev_price = float(close.iloc[-2])
        current_bb_upper = float(bb_upper.iloc[-1])
        current_bb_lower = float(bb_lower.iloc[-1])
        layer3_bull = was_squeezed and current_price > current_bb_upper
        layer3_bear = was_squeezed and current_price < current_bb_lower

        # --- Layer 4: Momentum composite ---
        ema20 = _ema(close, 20)
        macd_line, signal_line, _ = _macd(close)
        vol_avg = data['volume'].rolling(self.vol_avg_period).mean()

        price_above_ema20 = current_price > float(ema20.iloc[-1])
        macd_above_signal = float(macd_line.iloc[-1]) > float(signal_line.iloc[-1])
        volume_surge = float(data['volume'].iloc[-1]) > 1.2 * float(vol_avg.iloc[-1])

        price_below_ema20 = current_price < float(ema20.iloc[-1])
        macd_below_signal = float(macd_line.iloc[-1]) < float(signal_line.iloc[-1])

        layer4_bull = price_above_ema20 and macd_above_signal and volume_surge
        layer4_bear = price_below_ema20 and macd_below_signal and volume_surge

        # --- ALL 4 layers must confirm ---
        atr = _atr(data, self.atr_period)
        current_atr = float(atr.iloc[-1])

        signals = []

        if layer1_bull and layer2_bull and layer3_bull and layer4_bull:
            tp = current_price + (2.5 * current_atr)
            sl = current_price - (1.5 * current_atr)
            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=1.0,
                entry_price=round(current_price, 8),
                take_profit=round(tp, 8),
                stop_loss=round(sl, 8),
                reason=(
                    f"{NAME}: All 4 layers confirmed LONG | RSI={current_rsi:.1f} | "
                    f"BB squeeze breakout | Volume surge"
                )
            ))

        elif layer1_bear and layer2_bear and layer3_bear and layer4_bear:
            tp = current_price - (2.5 * current_atr)
            sl = current_price + (1.5 * current_atr)
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=1.0,
                entry_price=round(current_price, 8),
                take_profit=round(tp, 8),
                stop_loss=round(sl, 8),
                reason=(
                    f"{NAME}: All 4 layers confirmed SHORT | RSI={current_rsi:.1f} | "
                    f"BB squeeze breakdown | Volume surge"
                )
            ))

        return signals


# =============================================================================
# Strategy 4: AlphaRegimeSwitcher (DeepSeek adaptation)
# =============================================================================

class AlphaRegimeSwitcher:
    """
    ADX-based regime detection: trending (ADX>25) vs ranging (ADX<=25).
    Uses EMA crossover in trends and RSI mean-reversion in ranges.
    """

    NAME = "AlphaRegimeSwitcher"
    DESCRIPTION = "ADX regime detection: EMA crossover in trends, RSI mean-reversion in ranges (DeepSeek, Alpha Arena)"

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.adx_period = self.params.get('adx_period', 14)
        self.adx_trend_threshold = self.params.get('adx_trend_threshold', 25)
        self.ema_fast = self.params.get('ema_fast', 21)
        self.ema_slow = self.params.get('ema_slow', 55)
        self.rsi_period = self.params.get('rsi_period', 14)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        NAME = "AlphaRegimeSwitcher"
        DESCRIPTION = "ADX regime detection: EMA crossover in trends, RSI mean-reversion in ranges"

        if len(data) < max(self.ema_slow, 200) + 10:
            return []

        close = data['close']
        current_price = float(close.iloc[-1])
        adx = _adx(data, self.adx_period)
        current_adx = float(adx.iloc[-1])

        signals = []

        is_trending = current_adx > self.adx_trend_threshold

        if is_trending:
            # --- TRENDING REGIME: EMA(21/55) crossover ---
            ema21 = _ema(close, self.ema_fast)
            ema55 = _ema(close, self.ema_slow)
            cur_fast = float(ema21.iloc[-1])
            prev_fast = float(ema21.iloc[-2])
            cur_slow = float(ema55.iloc[-1])
            prev_slow = float(ema55.iloc[-2])

            # Bullish crossover
            if prev_fast <= prev_slow and cur_fast > cur_slow:
                tp = current_price * 1.15
                sl = current_price * 0.94
                confidence = min(0.55 + (current_adx - 25) * 0.01, 0.90)
                signals.append(Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=(
                        f"{NAME}: Trending regime (ADX={current_adx:.1f}) | "
                        f"EMA {self.ema_fast}/{self.ema_slow} bullish cross"
                    )
                ))

            # Bearish crossover
            elif prev_fast >= prev_slow and cur_fast < cur_slow:
                tp = current_price * 0.85
                sl = current_price * 1.06
                confidence = min(0.55 + (current_adx - 25) * 0.01, 0.90)
                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=(
                        f"{NAME}: Trending regime (ADX={current_adx:.1f}) | "
                        f"EMA {self.ema_fast}/{self.ema_slow} bearish cross"
                    )
                ))

        else:
            # --- RANGING REGIME: RSI oversold/overbought mean-reversion ---
            rsi = _rsi(close, self.rsi_period)
            current_rsi = float(rsi.iloc[-1])

            if current_rsi < 30:
                tp = current_price * 1.08
                sl = current_price * 0.96
                confidence = min(0.50 + (30 - current_rsi) * 0.015, 0.85)
                if current_adx < 15:
                    confidence = min(confidence + 0.05, 0.90)
                signals.append(Signal(
                    symbol=symbol,
                    direction="BUY",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=(
                        f"{NAME}: Ranging regime (ADX={current_adx:.1f}) | "
                        f"RSI={current_rsi:.1f} oversold mean-reversion"
                    )
                ))

            elif current_rsi > 70:
                tp = current_price * 0.92
                sl = current_price * 1.04
                confidence = min(0.50 + (current_rsi - 70) * 0.015, 0.85)
                if current_adx < 15:
                    confidence = min(confidence + 0.05, 0.90)
                signals.append(Signal(
                    symbol=symbol,
                    direction="SELL",
                    confidence=round(confidence, 3),
                    entry_price=round(current_price, 8),
                    take_profit=round(tp, 8),
                    stop_loss=round(sl, 8),
                    reason=(
                        f"{NAME}: Ranging regime (ADX={current_adx:.1f}) | "
                        f"RSI={current_rsi:.1f} overbought mean-reversion"
                    )
                ))

        return signals


# =============================================================================
# Strategy 5: AlphaDrawdownResponsive (Both winners)
# =============================================================================

class AlphaDrawdownResponsive:
    """
    Volatility-scaled momentum with drawdown protection.
    Signal strength = momentum / realized vol (risk-adjusted).
    Reduces confidence when price is in drawdown from recent highs.
    """

    NAME = "AlphaDrawdownResponsive"
    DESCRIPTION = "Vol-scaled momentum + drawdown guard: signal_strength = momentum / vol (Alpha Arena both winners)"

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.mom_period = self.params.get('mom_period', 14)
        self.vol_period = self.params.get('vol_period', 20)
        self.hh_lookback = self.params.get('hh_lookback', 50)
        self.dd_threshold = self.params.get('dd_threshold', 0.05)  # 5%
        self.dd_penalty = self.params.get('dd_penalty', 0.30)  # 30% confidence reduction
        self.atr_period = self.params.get('atr_period', 14)
        self.max_confidence = self.params.get('max_confidence', 0.85)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        NAME = "AlphaDrawdownResponsive"
        DESCRIPTION = "Vol-scaled momentum + drawdown guard"

        min_bars = max(self.hh_lookback, self.vol_period, self.mom_period) + 10
        if len(data) < min_bars:
            return []

        close = data['close']
        current_price = float(close.iloc[-1])

        # 14-bar momentum
        mom_price = float(close.iloc[-self.mom_period - 1])
        momentum = (current_price / mom_price) - 1.0 if mom_price > 0 else 0.0

        # 20-bar realized vol
        returns = close.pct_change()
        vol = float(returns.rolling(self.vol_period).std().iloc[-1])
        if vol <= 0 or np.isnan(vol):
            return []

        # Signal strength = momentum / vol (risk-adjusted)
        signal_strength = momentum / vol

        # Drawdown check: price < 0.95 * highest_high(50)
        highest_high = float(data['high'].iloc[-self.hh_lookback:].max())
        in_drawdown = current_price < (1.0 - self.dd_threshold) * highest_high

        # ATR for TP/SL
        atr = _atr(data, self.atr_period)
        current_atr = float(atr.iloc[-1])

        if abs(signal_strength) < 0.5:
            return []

        # Confidence scales with |signal_strength|, capped at 0.85
        confidence = min(0.40 + abs(signal_strength) * 0.08, self.max_confidence)

        # Drawdown penalty
        if in_drawdown:
            confidence *= (1.0 - self.dd_penalty)

        signals = []

        if signal_strength > 0.5:
            tp = current_price + (2.0 * current_atr)
            sl = current_price - (1.5 * current_atr)
            dd_note = " [DRAWDOWN -30% conf]" if in_drawdown else ""
            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 8),
                take_profit=round(tp, 8),
                stop_loss=round(sl, 8),
                reason=(
                    f"{NAME}: Momentum={momentum:.2%} / Vol={vol:.4f} = "
                    f"strength={signal_strength:.2f}{dd_note}"
                )
            ))

        elif signal_strength < -0.5:
            tp = current_price - (2.0 * current_atr)
            sl = current_price + (1.5 * current_atr)
            dd_note = " [DRAWDOWN -30% conf]" if in_drawdown else ""
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 8),
                take_profit=round(tp, 8),
                stop_loss=round(sl, 8),
                reason=(
                    f"{NAME}: Momentum={momentum:.2%} / Vol={vol:.4f} = "
                    f"strength={signal_strength:.2f}{dd_note}"
                )
            ))

        return signals


# =============================================================================
# Strategy 6: AlphaPartialScaleOut (Qwen execution)
# =============================================================================

class AlphaPartialScaleOut:
    """
    EMA(9/21/50) stack alignment + volume confirmation.
    Enters on strong stack with RSI 45-65 and volume > 1.3x avg.
    Reason field includes scale-out plan: 50% at 2R, 25% at 3R, 25% trail.
    """

    NAME = "AlphaPartialScaleOut"
    DESCRIPTION = "EMA 9/21/50 stack + volume surge with scale-out plan (Qwen execution, Alpha Arena)"

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.rsi_period = self.params.get('rsi_period', 14)
        self.vol_avg_period = self.params.get('vol_avg_period', 20)
        self.vol_mult = self.params.get('vol_mult', 1.3)
        self.atr_period = self.params.get('atr_period', 14)

    def generate_signals(
        self,
        data: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> List[Signal]:
        NAME = "AlphaPartialScaleOut"
        DESCRIPTION = "EMA 9/21/50 stack + volume surge with scale-out plan"

        if len(data) < 60:
            return []

        close = data['close']
        current_price = float(close.iloc[-1])

        # EMA stack
        ema9 = float(_ema(close, 9).iloc[-1])
        ema21 = float(_ema(close, 21).iloc[-1])
        ema50 = float(_ema(close, 50).iloc[-1])

        bullish_stack = ema9 > ema21 > ema50
        bearish_stack = ema9 < ema21 < ema50

        if not bullish_stack and not bearish_stack:
            return []

        # RSI 45-65
        rsi = _rsi(close, self.rsi_period)
        current_rsi = float(rsi.iloc[-1])
        if not (45 <= current_rsi <= 65):
            return []

        # Volume > 1.3x 20-bar average
        vol_avg = float(data['volume'].rolling(self.vol_avg_period).mean().iloc[-1])
        current_vol = float(data['volume'].iloc[-1])
        if vol_avg <= 0 or current_vol <= vol_avg * self.vol_mult:
            return []

        # ATR for TP/SL
        atr = _atr(data, self.atr_period)
        current_atr = float(atr.iloc[-1])

        vol_ratio = current_vol / vol_avg
        confidence = min(0.60 + (vol_ratio - 1.3) * 0.15 + (current_rsi - 45) / 100, 0.90)

        signals = []

        if bullish_stack:
            tp = current_price + (3.0 * current_atr)
            sl = current_price - (1.0 * current_atr)
            signals.append(Signal(
                symbol=symbol,
                direction="BUY",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 8),
                take_profit=round(tp, 8),
                stop_loss=round(sl, 8),
                reason=(
                    f"{NAME}: EMA 9>21>50 stack | RSI={current_rsi:.1f} | "
                    f"Vol={vol_ratio:.1f}x avg | "
                    f"Scale: 50%@2R, 25%@3R, 25% trail"
                )
            ))

        elif bearish_stack:
            tp = current_price - (3.0 * current_atr)
            sl = current_price + (1.0 * current_atr)
            signals.append(Signal(
                symbol=symbol,
                direction="SELL",
                confidence=round(confidence, 3),
                entry_price=round(current_price, 8),
                take_profit=round(tp, 8),
                stop_loss=round(sl, 8),
                reason=(
                    f"{NAME}: EMA 9<21<50 stack | RSI={current_rsi:.1f} | "
                    f"Vol={vol_ratio:.1f}x avg | "
                    f"Scale: 50%@2R, 25%@3R, 25% trail"
                )
            ))

        return signals


# =============================================================================
# TESTING — Live Binance 4H data
# =============================================================================

def fetch_binance_klines(symbol: str = "BTCUSDT", interval: str = "4h",
                         limit: int = 500) -> Optional[pd.DataFrame]:
    """Fetch OHLCV from Binance spot API. Returns pd.DataFrame."""
    import requests
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        raw = resp.json()
        if not raw:
            return None
        df = pd.DataFrame({
            'open': [float(c[1]) for c in raw],
            'high': [float(c[2]) for c in raw],
            'low': [float(c[3]) for c in raw],
            'close': [float(c[4]) for c in raw],
            'volume': [float(c[5]) for c in raw],
        })
        return df
    except Exception as e:
        print(f"  ERROR fetching {symbol}: {e}")
        return None


if __name__ == "__main__":
    print("=" * 70)
    print("Alpha Arena AI Competition Strategies -- Live Test")
    print("=" * 70)

    # Fetch BTC 4H data
    print("\nFetching BTCUSDT 4H from Binance (500 bars)...")
    btc_data = fetch_binance_klines("BTCUSDT", "4h", 500)

    if btc_data is None:
        print("ERROR: Could not fetch Binance data. Using synthetic data.")
        np.random.seed(42)
        n = 500
        returns = np.random.normal(0.0002, 0.015, n)
        prices = 85000 * np.exp(np.cumsum(returns))
        btc_data = pd.DataFrame({
            'open': prices * (1 + np.random.normal(0, 0.002, n)),
            'high': prices * (1 + abs(np.random.normal(0, 0.008, n))),
            'low': prices * (1 - abs(np.random.normal(0, 0.008, n))),
            'close': prices,
            'volume': np.random.uniform(500, 5000, n),
        })
    else:
        print(f"  Got {len(btc_data)} bars, latest close: ${btc_data['close'].iloc[-1]:,.2f}")

    # Fetch multi-symbol data for risk-parity
    multi_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
    all_symbols_data: Dict[str, pd.DataFrame] = {}
    print(f"\nFetching multi-symbol data for RiskParity: {multi_symbols}")
    for sym in multi_symbols:
        df = fetch_binance_klines(sym, "4h", 500)
        if df is not None:
            all_symbols_data[sym] = df
            print(f"  {sym}: {len(df)} bars, close=${df['close'].iloc[-1]:,.2f}")
        else:
            print(f"  {sym}: FAILED")

    # --- Test each strategy ---
    strategies = [
        ("1. AlphaAggressivePatience", AlphaAggressivePatience(), "BTCUSDT", btc_data),
        ("2. AlphaRiskParity", AlphaRiskParity(), "BTCUSDT", btc_data),
        ("3. AlphaFourLayerConfluence", AlphaFourLayerConfluence(), "BTCUSDT", btc_data),
        ("4. AlphaRegimeSwitcher", AlphaRegimeSwitcher(), "BTCUSDT", btc_data),
        ("5. AlphaDrawdownResponsive", AlphaDrawdownResponsive(), "BTCUSDT", btc_data),
        ("6. AlphaPartialScaleOut", AlphaPartialScaleOut(), "BTCUSDT", btc_data),
    ]

    total_signals = 0

    for label, strat, sym, data in strategies:
        print(f"\n{'-' * 60}")
        print(f"  {label} ({strat.NAME})")
        print(f"  {strat.DESCRIPTION}")
        print(f"{'-' * 60}")

        if isinstance(strat, AlphaRiskParity):
            sigs = strat.generate_signals(data, sym, all_symbols_data=all_symbols_data)
        else:
            sigs = strat.generate_signals(data, sym)

        if not sigs:
            print("  No signals (conditions not met)")
        for sig in sigs:
            total_signals += 1
            rr = abs(sig.take_profit - sig.entry_price) / abs(sig.entry_price - sig.stop_loss) if abs(sig.entry_price - sig.stop_loss) > 0 else 0
            print(f"  {sig.direction} {sig.symbol} @ ${sig.entry_price:,.2f}")
            print(f"    Confidence: {sig.confidence:.1%}")
            print(f"    TP: ${sig.take_profit:,.2f} | SL: ${sig.stop_loss:,.2f} | R:R={rr:.1f}")
            print(f"    Reason: {sig.reason}")

    # Test RiskParity across all symbols
    print(f"\n{'-' * 60}")
    print("  RiskParity -- Multi-symbol scan")
    print(f"{'-' * 60}")
    rp = AlphaRiskParity()
    for sym, df in all_symbols_data.items():
        sigs = rp.generate_signals(df, sym, all_symbols_data=all_symbols_data)
        for sig in sigs:
            total_signals += 1
            print(f"  {sig.direction} {sig.symbol} @ ${sig.entry_price:,.2f} | Conf={sig.confidence:.1%}")
            print(f"    {sig.reason}")

    print(f"\n{'=' * 70}")
    print(f"Total signals generated: {total_signals}")
    print(f"{'=' * 70}")
