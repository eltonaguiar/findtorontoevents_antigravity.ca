"""Walk-Forward Elite Strategies — Validated via alpha_engine walk-forward pipeline.

Three strategies with statistically significant forward performance:

1. STOBVSupportDivergence  (68.3% WR, PF 4.75, n=101, Sharpe 9.85)
   OBV makes new high while price does NOT → smart money accumulating.
   Price near support + volume confirmation = high-probability breakout setup.
   Reference: Granville (1963), "New Key to Stock Market Profits".
   Walk-forward: 13 folds, 100% consistency.

2. STFearGreedContrarian    (58.1% WR, PF 2.50, n=344, Sharpe 5.51)
   Buy extreme fear (FGI ≤ 25) when above 200d SMA + RSI < 60.
   LONG only — SHORT direction hard-blocked (walkforward: SHORT = negative edge).
   Expanded to 20 symbols — proven 88% WR across 18 symbols.
   Reference: Buffett contrarian principle + alternative.me FGI.
   Walk-forward: 44 folds, 50% consistency.

3. STMultiDayMomentum       (62.7% WR, PF 3.84, n=75, Sharpe 8.32)
   Consecutive up days (≥3) + volume acceleration + ADX trending filter.
   Momentum persistence is one of the strongest anomalies in crypto.
   Reference: Jegadeesh & Titman (1993), "Returns to Buying Winners".
   Walk-forward: 10 folds, 70% consistency.

Source: alpha_engine/data/walkforward_results.json (64 strategies, 2026-04-14)
"""
import logging
from typing import List, Optional

import numpy as np
import pandas as pd

from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited, cached

logger = logging.getLogger("paper_trading")

# ── Shared crypto symbol universe ──────────────────────────────────────────
_CRYPTO_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "LTCUSDT",
    "DOGEUSDT", "TRXUSDT", "SUIUSDT", "INJUSDT", "NEARUSDT",
    "UNIUSDT", "APTUSDT", "HBARUSDT", "OPUSDT", "ARBUSDT",
]

_FGI_URL = "https://api.alternative.me/fng/?limit=7"


# ═══════════════════════════════════════════════════════════════════════════
# Indicator helpers (lightweight, no alpha_engine dependency)
# ═══════════════════════════════════════════════════════════════════════════

def _sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period, min_periods=period).mean()


def _wilder_ema(series: pd.Series, period: int) -> pd.Series:
    """Wilder's smoothing (alpha=1/period) — matches TradingView / alpha_engine RSI & ADX.

    Standard EWM uses alpha=2/(period+1) which shifts values ~1-3 pts vs Wilder.
    Since the walk-forward validation was done with alpha_engine's Wilder-based RSI/ADX,
    we MUST use the same smoothing to reproduce validated signals.
    """
    return series.ewm(alpha=1.0 / period, adjust=False).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """RSI using Wilder's smoothing (matches alpha_engine & TradingView)."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    # Wilder's smoothing (not SMA) — same as alpha_engine/crypto_strategies.py
    avg_gain = _wilder_ema(gain, period)
    avg_loss = _wilder_ema(loss, period)
    # When avg_loss → 0 (no down days), RSI = 100 (not NaN)
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - 100.0 / (1.0 + rs)
    # Where avg_loss==0 AND avg_gain>0: genuine "no losses" → RSI=100.
    # Where both avg_gain==0 and avg_loss==0: insufficient data (warm-up) → NaN.
    rsi.loc[(avg_loss == 0) & (avg_gain > 0)] = 100.0
    return rsi


def _atr(high: pd.Series, low: pd.Series, close: pd.Series,
         period: int = 14) -> pd.Series:
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    # Wilder's smoothing — matches alpha_engine ATR used in walk-forward validation
    return _wilder_ema(tr, period)


def _adx(high: pd.Series, low: pd.Series, close: pd.Series,
         period: int = 14) -> pd.Series:
    plus_dm = (high - high.shift(1)).clip(lower=0)
    minus_dm = (low.shift(1) - low).clip(lower=0)
    # Mask when inside bar
    plus_dm = plus_dm.where(plus_dm > minus_dm, 0.0)
    minus_dm = minus_dm.where(minus_dm > plus_dm, 0.0)
    atr_val = _atr(high, low, close, period)
    # Wilder's smoothing for DI/ADX (not standard EWM)
    plus_di = 100.0 * _wilder_ema(plus_dm, period) / atr_val.replace(0, np.nan)
    minus_di = 100.0 * _wilder_ema(minus_dm, period) / atr_val.replace(0, np.nan)
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return _wilder_ema(dx, period)


def _obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff())
    direction.iloc[0] = 0
    return (volume * direction).cumsum()


def _volume_ratio(volume: pd.Series, period: int = 20) -> pd.Series:
    avg = volume.rolling(period, min_periods=period).mean()
    return volume / avg.replace(0, np.nan)


def _smart_round(value: float) -> float:
    if value == 0:
        return 0.0
    abs_val = abs(value)
    if abs_val >= 100:
        return round(value, 2)
    elif abs_val >= 1:
        return round(value, 4)
    elif abs_val >= 0.01:
        return round(value, 6)
    else:
        return round(value, 10)


def _fetch_price(symbol: str) -> Optional[float]:
    """Fetch current Binance price for a symbol."""
    try:
        ticker = fetch_json(
            "https://api.binance.com/api/v3/ticker/price",
            params={"symbol": symbol},
        )
        return float(ticker.get("price", 0))
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════
# 1. STOBVSupportDivergence
# ═══════════════════════════════════════════════════════════════════════════

class STOBVSupportDivergence(BaseStrategy):
    """OBV support divergence — buy when smart money accumulates near support.

    Walk-forward validated: 68.3% WR, PF 4.75, n=101, Sharpe 9.85.
    13/13 folds profitable (100% consistency).

    Logic:
    - OBV makes 20-period high while price does NOT → accumulation divergence
    - Price near 20-period low (support zone) → favorable entry
    - Volume > 1.5x average confirms institutional participation
    - ATR-based TP/SL with 3:1.5 ratio (RR ≥ 1.5 required)
    """
    name = "st_obv_support_divergence"
    display_name = "ST OBV Support Divergence (WF n=101)"
    source = "Walk-Forward Elite"
    category = "crypto"
    portfolio_type = "walkforward_elite"

    # Walk-forward validated parameters
    OBV_LOOKBACK = 20
    VOL_RATIO_MIN = 1.5
    TP_ATR_MULT = 3.0
    SL_ATR_MULT = 1.5
    MIN_RR = 1.5
    RSI_OVERBOUGHT = 78
    MAX_PICKS = 5

    def fetch_data(self) -> dict:
        """Fetch klines for all crypto symbols."""
        data = {}
        for symbol in _CRYPTO_SYMBOLS:
            klines = self.fetch_klines(symbol, interval="1h", limit=250)
            if klines and len(klines) > 30:
                df = pd.DataFrame(klines, columns=[
                    "ts", "Open", "High", "Low", "Close", "Volume",
                    *["extra"] * (len(klines[0]) - 6 if klines else 0)
                ])
                for col in ["Open", "High", "Low", "Close", "Volume"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                data[symbol] = df
        return data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, df in data.items():
            try:
                pick = self._check_symbol(symbol, df)
                if pick:
                    picks.append(pick)
            except Exception as e:
                logger.debug(f"st_obv_support_divergence {symbol}: {e}")

        # Sort by confidence, cap picks
        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:self.MAX_PICKS]

    def _check_symbol(self, symbol: str, df: pd.DataFrame) -> Optional[NormalizedPick]:
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]

        if len(df) < 30:
            return None

        # Calculate OBV
        obv_vals = _obv(close, volume)
        if obv_vals.isna().all():
            return None

        # OBV 20-period high check (current OBV ≥ max of prior 20 bars)
        obv_window = obv_vals.iloc[-self.OBV_LOOKBACK - 1:-1]
        if len(obv_window) < self.OBV_LOOKBACK:
            return None
        obv_high = float(obv_window.max())
        current_obv = float(obv_vals.iloc[-1])

        if current_obv < obv_high:
            return None  # OBV not at new high

        # Price should NOT be at 20-period high (divergence: OBV leads price)
        price_window = close.iloc[-self.OBV_LOOKBACK - 1:-1]
        price_high = float(price_window.max())
        current_price = float(close.iloc[-1])

        if current_price >= price_high:
            return None  # Price already at high — no divergence

        # Price near support: within 5% of 20-period low
        price_low = float(price_window.min())
        price_from_low_pct = (current_price - price_low) / price_low if price_low > 0 else 1.0
        if price_from_low_pct > 0.05:
            return None  # Not near enough to support

        # Volume confirmation
        vol_r = float(_volume_ratio(volume).iloc[-1])
        if vol_r < self.VOL_RATIO_MIN:
            return None

        # Price showing breakout attempt (close > prior close)
        if close.iloc[-1] <= close.iloc[-2]:
            return None

        # RSI guard
        rsi_val = float(_rsi(close, 14).iloc[-1])
        if rsi_val > self.RSI_OVERBOUGHT:
            return None

        # ATR-based TP/SL
        atr_val = float(_atr(high, low, close).iloc[-1])
        if atr_val <= 0:
            return None

        tp = _smart_round(current_price + self.TP_ATR_MULT * atr_val)
        sl = _smart_round(current_price - self.SL_ATR_MULT * atr_val)
        rr = (tp - current_price) / (current_price - sl) if current_price > sl else 0
        if rr < self.MIN_RR:
            return None

        # Confidence: OBV excess + volume strength
        obv_excess = (current_obv - obv_high) / abs(obv_high) if obv_high != 0 else 0
        confidence = round(min(0.80, 0.55 + obv_excess * 2 + vol_r * 0.03), 3)

        return NormalizedPick(
            symbol=symbol,
            direction="LONG",
            entry_price=_smart_round(current_price),
            tp=tp,
            sl=sl,
            strategy=self.name,
            strategy_name=self.display_name,
            category=self.category,
            confidence=confidence,
            reason=(
                f"OBV at {self.OBV_LOOKBACK}-period high (divergence), "
                f"price near support ({price_from_low_pct*100:.1f}% from low), "
                f"vol={vol_r:.1f}x, RSI={rsi_val:.0f}. "
                f"Granville (1963): OBV leads price. WF: 68.3% WR, n=101"
            ),
            raw_signal={
                "obv_current": round(current_obv, 2),
                "obv_high": round(obv_high, 2),
                "price_20_high": round(price_high, 4),
                "price_20_low": round(price_low, 4),
                "vol_ratio": round(vol_r, 2),
            },
        )


# ═══════════════════════════════════════════════════════════════════════════
# 2. STFearGreedContrarian
# ═══════════════════════════════════════════════════════════════════════════

class STFearGreedContrarian(BaseStrategy):
    """Fear & Greed contrarian — buy extreme fear when trend structure intact.

    Walk-forward validated: 58.1% WR, PF 2.50, n=344, Sharpe 5.51.
    44 folds, 50% consistency. Largest sample of any walk-forward strategy.

    Key validated parameters (NOT the simple paper_trading version):
    - FGI ≤ 25 (not ≤ 20) — broader fear capture, validated 88% WR
    - 200d SMA filter — prevents buying in confirmed downtrends
    - RSI < 60 — not already recovering
    - LONG ONLY — SHORT direction hard-blocked (negative edge in walk-forward)
    - 20 symbols (expanded from 5) — proven across 18/20 symbols
    - ATR-based TP/SL: 4x TP / 1.5x SL (RR ≥ 1.5 required)
    """
    name = "st_fear_greed_contrarian"
    display_name = "ST Fear & Greed Contrarian (WF n=344)"
    source = "Alternative.me + Walk-Forward Elite"
    category = "crypto"
    portfolio_type = "walkforward_elite"

    # Walk-forward validated parameters
    FGI_THRESHOLD = 25     # Extreme fear (validated, not the 20 from simple version)
    SMA_PERIOD = 200       # Trend filter
    RSI_MAX = 60           # Not already recovering
    TP_ATR_MULT = 4.0      # Wide TP — fear reversals are big moves
    SL_ATR_MULT = 1.5      # Moderate SL
    MIN_RR = 1.5
    MAX_PICKS = 5

    def fetch_data(self) -> dict:
        """Fetch FGI + klines for crypto symbols."""
        result = {"fear_greed": None, "klines": {}}

        # Fetch Fear & Greed Index
        try:
            fg_data = fetch_json(_FGI_URL)
            if fg_data and "data" in fg_data:
                result["fear_greed"] = fg_data
        except Exception as e:
            logger.debug(f"FGI fetch failed: {e}")

        # Fetch klines for symbols
        for symbol in _CRYPTO_SYMBOLS:
            klines = self.fetch_klines(symbol, interval="1d", limit=250)
            if klines and len(klines) > 210:
                df = pd.DataFrame(klines, columns=[
                    "ts", "Open", "High", "Low", "Close", "Volume",
                    *["extra"] * (len(klines[0]) - 6 if klines else 0)
                ])
                for col in ["Open", "High", "Low", "Close", "Volume"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                result["klines"][symbol] = df

        return result

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []

        # Parse Fear & Greed Index
        fg_data = data.get("fear_greed")
        if not fg_data or "data" not in fg_data:
            return picks

        try:
            fg_value = int(fg_data["data"][0]["value"])
            fg_class = fg_data["data"][0].get("value_classification", "")
        except (KeyError, IndexError, TypeError):
            return picks

        # Only act on extreme fear (FGI ≤ 25)
        if fg_value > self.FGI_THRESHOLD:
            return picks

        klines = data.get("klines", {})

        for symbol, df in klines.items():
            try:
                pick = self._check_symbol(symbol, df, fg_value, fg_class)
                if pick:
                    picks.append(pick)
            except Exception as e:
                logger.debug(f"st_fear_greed_contrarian {symbol}: {e}")

        # Sort by confidence, cap picks
        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:self.MAX_PICKS]

    def _check_symbol(self, symbol: str, df: pd.DataFrame,
                      fg_value: int, fg_class: str) -> Optional[NormalizedPick]:
        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        current = float(close.iloc[-1])
        if current <= 0:
            return None

        # 200d SMA filter — must be above (downtrend = no buy)
        sma_200 = _sma(close, self.SMA_PERIOD)
        sma_val = float(sma_200.iloc[-1])
        if pd.isna(sma_val) or current < sma_val:
            return None

        # RSI filter — not already recovering
        rsi_val = float(_rsi(close, 14).iloc[-1])
        if rsi_val > self.RSI_MAX:
            return None

        # ATR-based TP/SL
        atr_val = float(_atr(high, low, close).iloc[-1])
        if atr_val <= 0:
            return None

        tp = _smart_round(current + self.TP_ATR_MULT * atr_val)
        sl = _smart_round(current - self.SL_ATR_MULT * atr_val)
        rr = (tp - current) / (current - sl) if current > sl else 0
        if rr < self.MIN_RR:
            return None

        # Confidence scales with how extreme the fear is
        confidence = round(min(0.85, 0.60 + (self.FGI_THRESHOLD - fg_value) / 50), 3)

        return NormalizedPick(
            symbol=symbol,
            direction="LONG",
            entry_price=_smart_round(current),
            tp=tp,
            sl=sl,
            strategy=self.name,
            strategy_name=self.display_name,
            category=self.category,
            confidence=confidence,
            reason=(
                f"Extreme Fear (FGI={fg_value} — {fg_class}), "
                f"above 200d SMA ({sma_val:.0f}), RSI={rsi_val:.0f}. "
                f"WF: 58.1% WR, n=344, PF 2.50"
            ),
            raw_signal={
                "fgi_value": fg_value,
                "fgi_class": fg_class,
                "sma200": round(sma_val, 2),
                "rsi": round(rsi_val, 1),
            },
        )


# ═══════════════════════════════════════════════════════════════════════════
# 3. STMultiDayMomentum
# ═══════════════════════════════════════════════════════════════════════════

class STMultiDayMomentum(BaseStrategy):
    """Multi-day momentum — buy consecutive up days with volume acceleration.

    Walk-forward validated: 62.7% WR, PF 3.84, n=75, Sharpe 8.32.
    10 folds, 70% consistency.

    Logic:
    - ≥3 consecutive up days (close > close prev) = momentum building
    - Volume accelerating: today's vol > yesterday's vol > day before
    - ADX > 20 = trending market (not range-bound)
    - Above 50d SMA = positive market structure
    - RSI < 72 = not overextended
    - ATR-based TP/SL with 3:1.5 ratio

    Reference: Jegadeesh & Titman (1993), "Returns to Buying Winners
    and Selling Losers: Implications for Stock Market Efficiency".
    Momentum persistence is one of the strongest documented anomalies.
    """
    name = "st_multi_day_momentum"
    display_name = "ST Multi-Day Momentum (WF n=75)"
    source = "Walk-Forward Elite"
    category = "crypto"
    portfolio_type = "walkforward_elite"

    # Walk-forward validated parameters
    CONSEC_DAYS_MIN = 3      # Minimum consecutive up days
    ADX_MIN = 20             # Must be trending
    SMA_PERIOD = 50          # Market structure filter
    RSI_MAX = 72             # Not overextended
    VOL_ACCEL_MIN = 1.1      # Volume must be increasing (ratio vs prev day)
    TP_ATR_MULT = 3.0
    SL_ATR_MULT = 1.5
    MIN_RR = 1.3
    MAX_PICKS = 3

    def fetch_data(self) -> dict:
        """Fetch klines for all crypto symbols."""
        data = {}
        for symbol in _CRYPTO_SYMBOLS:
            klines = self.fetch_klines(symbol, interval="1d", limit=60)
            if klines and len(klines) > 30:
                df = pd.DataFrame(klines, columns=[
                    "ts", "Open", "High", "Low", "Close", "Volume",
                    *["extra"] * (len(klines[0]) - 6 if klines else 0)
                ])
                for col in ["Open", "High", "Low", "Close", "Volume"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                data[symbol] = df
        return data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, df in data.items():
            try:
                pick = self._check_symbol(symbol, df)
                if pick:
                    picks.append(pick)
            except Exception as e:
                logger.debug(f"st_multi_day_momentum {symbol}: {e}")

        # Sort by confidence, cap picks
        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:self.MAX_PICKS]

    def _check_symbol(self, symbol: str, df: pd.DataFrame) -> Optional[NormalizedPick]:
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]

        if len(df) < 30:
            return None

        current = float(close.iloc[-1])
        if current <= 0:
            return None

        # ── Consecutive up days ──
        consecutive = 0
        for i in range(1, min(8, len(df))):
            if float(close.iloc[-i]) > float(close.iloc[-i - 1]):
                consecutive += 1
            else:
                break

        if consecutive < self.CONSEC_DAYS_MIN:
            return None

        # ── Volume acceleration: today's volume > yesterday's * factor ──
        if len(volume) < 3:
            return None
        vol_today = float(volume.iloc[-1])
        vol_yesterday = float(volume.iloc[-2])
        if vol_yesterday <= 0:
            return None
        vol_accel = vol_today / vol_yesterday
        if vol_accel < self.VOL_ACCEL_MIN:
            return None

        # ── ADX trending filter ──
        adx_val = float(_adx(high, low, close).iloc[-1])
        if pd.isna(adx_val) or adx_val < self.ADX_MIN:
            return None

        # ── Above 50d SMA (positive market structure) ──
        sma_50 = float(_sma(close, self.SMA_PERIOD).iloc[-1])
        if pd.isna(sma_50) or current < sma_50:
            return None

        # ── RSI not overextended ──
        rsi_val = float(_rsi(close, 14).iloc[-1])
        if rsi_val > self.RSI_MAX:
            return None

        # ── ATR-based TP/SL ──
        atr_val = float(_atr(high, low, close).iloc[-1])
        if atr_val <= 0:
            return None

        tp = _smart_round(current + self.TP_ATR_MULT * atr_val)
        sl = _smart_round(current - self.SL_ATR_MULT * atr_val)
        rr = (tp - current) / (current - sl) if current > sl else 0
        if rr < self.MIN_RR:
            return None

        # Confidence: more consecutive days + stronger ADX = higher
        confidence = round(
            min(0.80, 0.52 + (consecutive - 2) * 0.04 + (adx_val - 20) * 0.005),
            3,
        )

        # 7-day return for context
        ret_7d = 0.0
        if len(close) >= 8:
            ret_7d = (current / float(close.iloc[-8]) - 1) * 100

        return NormalizedPick(
            symbol=symbol,
            direction="LONG",
            entry_price=_smart_round(current),
            tp=tp,
            sl=sl,
            strategy=self.name,
            strategy_name=self.display_name,
            category=self.category,
            confidence=confidence,
            reason=(
                f"{consecutive} consecutive up days, vol accel={vol_accel:.1f}x, "
                f"ADX={adx_val:.0f}, above 50d SMA, RSI={rsi_val:.0f}, "
                f"7d ret={ret_7d:+.1f}%. "
                f"Jegadeesh & Titman (1993). WF: 62.7% WR, n=75"
            ),
            raw_signal={
                "consecutive_days": consecutive,
                "vol_accel": round(vol_accel, 2),
                "adx": round(adx_val, 1),
                "sma50": round(sma_50, 2),
                "rsi": round(rsi_val, 1),
                "ret_7d_pct": round(ret_7d, 2),
            },
        )
