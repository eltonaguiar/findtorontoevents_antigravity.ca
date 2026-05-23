"""
ALPHA_ENGINE -- Quant Research Strategies
==========================================
Thirteen quantitative / statistical strategies using stdlib only.

Strategies (original 8):
  1. fisher_transform      -- Ehlers Fisher Transform crossover (58-65% WR)
  2. garman_klass_breakout  -- GK volatility breakout (55-62% WR)
  3. ttm_squeeze            -- BB inside KC squeeze release (60-68% WR)
  4. hurst_mean_reversion   -- R/S Hurst exponent mean-revert (55-60% WR)
  5. kama_trend             -- Kaufman Adaptive MA trend (58-65% WR)
  6. vortex_crossover       -- Vortex Indicator crossover (55-62% WR)
  7. amihud_reversal        -- Amihud illiquidity z-score reversal (52-58% WR)
  8. vol_term_structure     -- RV(5)/RV(30) regime detector (55-62% WR)

Strategies (new 5 -- catalog #13, #22, #11, #63, #56):
  9. bayesian_posterior      -- Bayesian P(up|features) updates per bar (64-70% WR)
 10. zscore_momentum         -- Z-score of 20-day returns, momentum + mean-revert (62-68% WR)
 11. gaussian_mean_revert    -- Gaussian model with dynamic GARCH sigma (62-68% WR)
 12. vwap_deviation_trade    -- VWAP deviation with volume surge/decline filter (62-68% WR)
 13. dynamic_rsi_percentile  -- Rolling percentile RSI thresholds instead of fixed 30/70 (63-68% WR)

Data sources:
  - Binance 4-mirror failover: api/api1/api2/api3.binance.com (klines)

stdlib only (urllib.request, json, datetime, math, statistics, ssl).
"""

from __future__ import annotations

import json
import math
import ssl
import statistics
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

try:
    _SSL_CTX = ssl.create_default_context()
except Exception:
    _SSL_CTX = ssl._create_unverified_context()

_REQUEST_TIMEOUT = 15

_BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

_DEFAULT_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
    "MATICUSDT", "LTCUSDT", "NEARUSDT", "UNIUSDT", "ATOMUSDT",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_json(url: str, timeout: int = _REQUEST_TIMEOUT) -> Optional[Any]:
    """Fetch JSON from URL with error handling."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/2.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _fetch_klines(symbol: str, interval: str = "4h",
                  limit: int = 100) -> Optional[List[list]]:
    """Fetch klines from Binance with 4-mirror failover."""
    for mirror in _BINANCE_MIRRORS:
        url = (f"{mirror}/api/v3/klines"
               f"?symbol={symbol}&interval={interval}&limit={limit}")
        data = _fetch_json(url)
        if data and isinstance(data, list) and len(data) > 10:
            return data
    return None


def _parse_ohlcv(klines: List[list]) -> Dict[str, List[float]]:
    """Parse Binance klines into OHLCV lists."""
    o, h, l, c, v = [], [], [], [], []
    for k in klines:
        o.append(float(k[1]))
        h.append(float(k[2]))
        l.append(float(k[3]))
        c.append(float(k[4]))
        v.append(float(k[5]))
    return {"open": o, "high": h, "low": l, "close": c, "volume": v}


# ---------------------------------------------------------------------------
# Technical helpers
# ---------------------------------------------------------------------------

def _atr(high: List[float], low: List[float], close: List[float],
         period: int = 14) -> float:
    """Average True Range over last `period` bars."""
    trs = []
    for i in range(1, len(high)):
        tr = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
        trs.append(tr)
    if len(trs) < period:
        return statistics.mean(trs) if trs else 0.0
    return statistics.mean(trs[-period:])


def _sma(values: List[float], period: int) -> List[float]:
    """Simple moving average."""
    result = []
    for i in range(len(values)):
        if i < period - 1:
            result.append(None)
        else:
            result.append(statistics.mean(values[i - period + 1: i + 1]))
    return result


def _stdev(values: List[float], period: int) -> List[float]:
    """Rolling standard deviation."""
    result = []
    for i in range(len(values)):
        if i < period - 1:
            result.append(None)
        else:
            window = values[i - period + 1: i + 1]
            result.append(statistics.pstdev(window))
    return result


def _ema(values: List[float], period: int) -> List[float]:
    """Exponential moving average."""
    result = []
    k = 2.0 / (period + 1)
    for i, v in enumerate(values):
        if i == 0:
            result.append(v)
        else:
            result.append(v * k + result[-1] * (1 - k))
    return result


def _linreg_slope(values: List[float], period: int) -> Optional[float]:
    """Linear regression slope over last `period` values."""
    if len(values) < period:
        return None
    window = values[-period:]
    n = len(window)
    x_mean = (n - 1) / 2.0
    y_mean = statistics.mean(window)
    num = sum((i - x_mean) * (window[i] - y_mean) for i in range(n))
    den = sum((i - x_mean) ** 2 for i in range(n))
    if den == 0:
        return 0.0
    return num / den


# ---------------------------------------------------------------------------
# Strategy 1: Fisher Transform
# ---------------------------------------------------------------------------

def _fisher_transform(high: List[float], low: List[float],
                      period: int = 10) -> tuple:
    """Ehlers Fisher Transform. Returns (fisher, trigger) lists."""
    hl2 = [(h + l) / 2.0 for h, l in zip(high, low)]
    fisher = [0.0]
    trigger = [0.0]
    val = 0.0

    for i in range(1, len(hl2)):
        start = max(0, i - period + 1)
        window = hl2[start: i + 1]
        hi = max(window)
        lo = min(window)
        rng = hi - lo if hi != lo else 1e-10
        raw = 2.0 * ((hl2[i] - lo) / rng - 0.5)
        # Clamp to avoid math domain error
        val = 0.33 * raw + 0.67 * val
        val = max(-0.999, min(0.999, val))
        f = 0.5 * math.log((1.0 + val) / (1.0 - val))
        fisher.append(f)
        trigger.append(fisher[-2] if len(fisher) >= 2 else 0.0)

    return fisher, trigger


def _eval_fisher_transform(ohlcv: Dict[str, List[float]], symbol: str,
                           price: float, atr_val: float) -> Optional[Dict]:
    """Evaluate Fisher Transform strategy."""
    fisher, trigger = _fisher_transform(ohlcv["high"], ohlcv["low"])
    if len(fisher) < 3:
        return None

    f_now, f_prev = fisher[-1], fisher[-2]
    t_now, t_prev = trigger[-1], trigger[-2]

    signal = None
    # Long: fisher crosses trigger from below -1.0
    if f_prev < t_prev and f_now > t_now and f_now < -1.0:
        signal = "LONG"
    # Short: fisher crosses trigger from above +1.0
    elif f_prev > t_prev and f_now < t_now and f_now > 1.0:
        signal = "SHORT"

    if not signal:
        return None

    tp_pct = (2.0 * atr_val / price) * 100
    sl_pct = (1.0 * atr_val / price) * 100
    return _make_pick(symbol, "fisher_transform", signal, price,
                      tp_pct, sl_pct, f"Fisher={f_now:.2f} Trigger={t_now:.2f}")


# ---------------------------------------------------------------------------
# Strategy 2: Garman-Klass Breakout
# ---------------------------------------------------------------------------

def _garman_klass_vol(ohlcv: Dict[str, List[float]],
                      period: int = 20) -> List[float]:
    """Garman-Klass volatility estimator."""
    o, h, l, c = ohlcv["open"], ohlcv["high"], ohlcv["low"], ohlcv["close"]
    gk = []
    ln2 = math.log(2)
    for i in range(len(o)):
        if h[i] <= 0 or l[i] <= 0 or o[i] <= 0 or c[i] <= 0:
            gk.append(0.0)
            continue
        hl_ratio = h[i] / l[i] if l[i] != 0 else 1.0
        co_ratio = c[i] / o[i] if o[i] != 0 else 1.0
        val = (0.5 * math.log(hl_ratio) ** 2
               - (2.0 * ln2 - 1.0) * math.log(co_ratio) ** 2)
        gk.append(val)
    return gk


def _eval_garman_klass(ohlcv: Dict[str, List[float]], symbol: str,
                       price: float, atr_val: float) -> Optional[Dict]:
    """Evaluate Garman-Klass breakout strategy."""
    gk = _garman_klass_vol(ohlcv)
    if len(gk) < 25:
        return None

    window = gk[-20:]
    gk_mean = statistics.mean(window)
    gk_std = statistics.pstdev(window)
    if gk_std == 0:
        return None

    current_gk = gk[-1]
    threshold = gk_mean + 1.5 * gk_std

    if current_gk <= threshold:
        return None

    # 5-bar momentum direction
    closes = ohlcv["close"]
    if len(closes) < 6:
        return None
    momentum = closes[-1] - closes[-6]
    signal = "LONG" if momentum > 0 else "SHORT"

    tp_pct = (3.0 * atr_val / price) * 100
    sl_pct = (1.5 * atr_val / price) * 100
    return _make_pick(symbol, "garman_klass_breakout", signal, price,
                      tp_pct, sl_pct,
                      f"GK={current_gk:.6f} thresh={threshold:.6f} mom={momentum:.2f}")


# ---------------------------------------------------------------------------
# Strategy 3: TTM Squeeze
# ---------------------------------------------------------------------------

def _eval_ttm_squeeze(ohlcv: Dict[str, List[float]], symbol: str,
                      price: float, atr_val: float) -> Optional[Dict]:
    """TTM Squeeze: BB(20,2) inside KC(20, 1.5*ATR) = squeeze. Trade release."""
    closes = ohlcv["close"]
    highs = ohlcv["high"]
    lows = ohlcv["low"]
    if len(closes) < 25:
        return None

    period = 20
    mult_bb = 2.0
    mult_kc = 1.5

    sma_vals = _sma(closes, period)
    std_vals = _stdev(closes, period)

    # Check squeeze: are BB inside KC?
    # We need current and previous bar
    for idx in [-2, -1]:
        if sma_vals[idx] is None or std_vals[idx] is None:
            return None

    # Current bars
    bb_upper = sma_vals[-1] + mult_bb * std_vals[-1]
    bb_lower = sma_vals[-1] - mult_bb * std_vals[-1]

    # KC uses ATR
    kc_atr = _atr(highs, lows, closes, period)
    kc_upper = sma_vals[-1] + mult_kc * kc_atr
    kc_lower = sma_vals[-1] - mult_kc * kc_atr

    squeeze_now = (bb_lower > kc_lower) and (bb_upper < kc_upper)

    # Previous bar squeeze
    bb_upper_prev = sma_vals[-2] + mult_bb * std_vals[-2]
    bb_lower_prev = sma_vals[-2] - mult_bb * std_vals[-2]
    kc_upper_prev = sma_vals[-2] + mult_kc * kc_atr
    kc_lower_prev = sma_vals[-2] - mult_kc * kc_atr
    squeeze_prev = (bb_lower_prev > kc_lower_prev) and (bb_upper_prev < kc_upper_prev)

    # Signal on squeeze release (was in squeeze, now released)
    if not (squeeze_prev and not squeeze_now):
        return None

    # Direction from linear regression slope
    slope = _linreg_slope(closes, period)
    if slope is None or slope == 0:
        return None

    signal = "LONG" if slope > 0 else "SHORT"
    tp_pct = (2.5 * atr_val / price) * 100
    sl_pct = (1.5 * atr_val / price) * 100
    return _make_pick(symbol, "ttm_squeeze", signal, price, tp_pct, sl_pct,
                      f"Squeeze released, slope={slope:.4f}")


# ---------------------------------------------------------------------------
# Strategy 4: Hurst Mean Reversion
# ---------------------------------------------------------------------------

def _hurst_rs(values: List[float], period: int = 50) -> Optional[float]:
    """Rescaled Range (R/S) Hurst exponent estimate."""
    if len(values) < period:
        return None
    window = values[-period:]
    mean_val = statistics.mean(window)
    deviations = [v - mean_val for v in window]
    cumulative = []
    s = 0.0
    for d in deviations:
        s += d
        cumulative.append(s)
    r = max(cumulative) - min(cumulative)
    std = statistics.pstdev(window)
    if std == 0 or r == 0:
        return None
    rs = r / std
    # H = log(R/S) / log(n)
    h = math.log(rs) / math.log(period)
    return h


def _eval_hurst_mean_reversion(ohlcv: Dict[str, List[float]], symbol: str,
                                price: float, atr_val: float) -> Optional[Dict]:
    """Mean-revert only when H < 0.45 and price 2+ std from mean."""
    closes = ohlcv["close"]
    if len(closes) < 50:
        return None

    h = _hurst_rs(closes, 50)
    if h is None or h >= 0.45:
        return None

    window = closes[-50:]
    mean_val = statistics.mean(window)
    std_val = statistics.pstdev(window)
    if std_val == 0:
        return None

    z_score = (price - mean_val) / std_val

    signal = None
    if z_score <= -2.0:
        signal = "LONG"
    elif z_score >= 2.0:
        signal = "SHORT"

    if not signal:
        return None

    tp_pct = (1.5 * atr_val / price) * 100
    sl_pct = (1.0 * atr_val / price) * 100
    return _make_pick(symbol, "hurst_mean_reversion", signal, price,
                      tp_pct, sl_pct,
                      f"Hurst={h:.3f} z={z_score:.2f}")


# ---------------------------------------------------------------------------
# Strategy 5: KAMA Trend
# ---------------------------------------------------------------------------

def _kama(closes: List[float], period: int = 10,
          fast_sc: float = 2.0 / 3.0,
          slow_sc: float = 2.0 / 31.0) -> List[float]:
    """Kaufman Adaptive Moving Average."""
    if len(closes) < period + 1:
        return closes[:]
    result = [closes[0]] * (period)
    for i in range(period, len(closes)):
        direction = abs(closes[i] - closes[i - period])
        volatility = sum(abs(closes[j] - closes[j - 1])
                         for j in range(i - period + 1, i + 1))
        if volatility == 0:
            er = 0.0
        else:
            er = direction / volatility
        sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2
        kama_val = result[-1] + sc * (closes[i] - result[-1])
        result.append(kama_val)
    return result


def _eval_kama_trend(ohlcv: Dict[str, List[float]], symbol: str,
                     price: float, atr_val: float) -> Optional[Dict]:
    """Long when close > KAMA and ER > 0.3."""
    closes = ohlcv["close"]
    if len(closes) < 15:
        return None

    period = 10
    kama_vals = _kama(closes, period)
    if len(kama_vals) < 2:
        return None

    # Calculate current ER
    i = len(closes) - 1
    direction = abs(closes[i] - closes[i - period])
    volatility = sum(abs(closes[j] - closes[j - 1])
                     for j in range(i - period + 1, i + 1))
    er = direction / volatility if volatility != 0 else 0.0

    if er <= 0.3:
        return None

    kama_now = kama_vals[-1]
    signal = None
    if price > kama_now:
        signal = "LONG"
    elif price < kama_now:
        signal = "SHORT"

    if not signal:
        return None

    tp_pct = (3.0 * atr_val / price) * 100
    sl_pct = (1.5 * atr_val / price) * 100
    return _make_pick(symbol, "kama_trend", signal, price, tp_pct, sl_pct,
                      f"KAMA={kama_now:.2f} ER={er:.3f}")


# ---------------------------------------------------------------------------
# Strategy 6: Vortex Crossover
# ---------------------------------------------------------------------------

def _vortex(high: List[float], low: List[float], close: List[float],
            period: int = 14) -> tuple:
    """Vortex Indicator. Returns (vi_plus, vi_minus) lists."""
    vi_plus = [None] * period
    vi_minus = [None] * period

    for i in range(period, len(high)):
        vm_plus = sum(abs(high[j] - low[j - 1]) for j in range(i - period + 1, i + 1))
        vm_minus = sum(abs(low[j] - high[j - 1]) for j in range(i - period + 1, i + 1))
        tr_sum = sum(
            max(high[j] - low[j],
                abs(high[j] - close[j - 1]),
                abs(low[j] - close[j - 1]))
            for j in range(i - period + 1, i + 1)
        )
        if tr_sum == 0:
            vi_plus.append(1.0)
            vi_minus.append(1.0)
        else:
            vi_plus.append(vm_plus / tr_sum)
            vi_minus.append(vm_minus / tr_sum)
    return vi_plus, vi_minus


def _eval_vortex_crossover(ohlcv: Dict[str, List[float]], symbol: str,
                           price: float, atr_val: float) -> Optional[Dict]:
    """Vortex crossover with 0.1 minimum spread."""
    vi_plus, vi_minus = _vortex(ohlcv["high"], ohlcv["low"], ohlcv["close"])
    if len(vi_plus) < 3 or vi_plus[-1] is None or vi_plus[-2] is None:
        return None

    spread = abs(vi_plus[-1] - vi_minus[-1])
    if spread < 0.1:
        return None

    signal = None
    # Bullish crossover: VI+ crosses above VI-
    if vi_plus[-2] <= vi_minus[-2] and vi_plus[-1] > vi_minus[-1]:
        signal = "LONG"
    # Bearish crossover: VI- crosses above VI+
    elif vi_minus[-2] <= vi_plus[-2] and vi_minus[-1] > vi_plus[-1]:
        signal = "SHORT"

    if not signal:
        return None

    tp_pct = (2.5 * atr_val / price) * 100
    sl_pct = (1.5 * atr_val / price) * 100
    return _make_pick(symbol, "vortex_crossover", signal, price, tp_pct, sl_pct,
                      f"VI+={vi_plus[-1]:.3f} VI-={vi_minus[-1]:.3f} spread={spread:.3f}")


# ---------------------------------------------------------------------------
# Strategy 7: Amihud Reversal
# ---------------------------------------------------------------------------

def _eval_amihud_reversal(ohlcv: Dict[str, List[float]], symbol: str,
                          price: float, atr_val: float) -> Optional[Dict]:
    """Amihud illiquidity z-scored. Reversal when z > 2 and price moved >2%."""
    closes = ohlcv["close"]
    volumes = ohlcv["volume"]
    if len(closes) < 25 or len(volumes) < 25:
        return None

    # Amihud illiquidity = |return| / volume
    illiq = []
    for i in range(1, len(closes)):
        ret = abs((closes[i] - closes[i - 1]) / closes[i - 1]) if closes[i - 1] != 0 else 0
        vol = volumes[i] if volumes[i] > 0 else 1e-10
        illiq.append(ret / vol)

    if len(illiq) < 21:
        return None

    window = illiq[-20:]
    mean_illiq = statistics.mean(window)
    std_illiq = statistics.pstdev(window)
    if std_illiq == 0:
        return None

    z = (illiq[-1] - mean_illiq) / std_illiq
    if z <= 2.0:
        return None

    # Price change over last 5 bars
    pct_change = ((closes[-1] - closes[-6]) / closes[-6]) * 100 if closes[-6] != 0 else 0.0

    signal = None
    if pct_change <= -2.0:
        signal = "LONG"    # Dropped >2%, reversal up
    elif pct_change >= 2.0:
        signal = "SHORT"   # Rose >2%, reversal down

    if not signal:
        return None

    tp_pct = (2.0 * atr_val / price) * 100
    sl_pct = (1.5 * atr_val / price) * 100
    return _make_pick(symbol, "amihud_reversal", signal, price, tp_pct, sl_pct,
                      f"Illiq_z={z:.2f} pct_chg={pct_change:.2f}%")


# ---------------------------------------------------------------------------
# Strategy 8: Volatility Term Structure
# ---------------------------------------------------------------------------

def _realized_vol(closes: List[float], period: int) -> Optional[float]:
    """Annualized realized volatility from log returns."""
    if len(closes) < period + 1:
        return None
    log_rets = []
    start = len(closes) - period - 1
    for i in range(start + 1, len(closes)):
        if closes[i] > 0 and closes[i - 1] > 0:
            log_rets.append(math.log(closes[i] / closes[i - 1]))
    if len(log_rets) < 2:
        return None
    return statistics.pstdev(log_rets) * math.sqrt(365)


def _eval_vol_term_structure(ohlcv: Dict[str, List[float]], symbol: str,
                             price: float, atr_val: float) -> Optional[Dict]:
    """RV(5)/RV(30) ratio. <0.7 = breakout regime, >1.5 = mean reversion."""
    closes = ohlcv["close"]
    rv5 = _realized_vol(closes, 5)
    rv30 = _realized_vol(closes, 30)
    if rv5 is None or rv30 is None or rv30 == 0:
        return None

    ratio = rv5 / rv30

    signal = None
    # Low short-term vol relative to long-term => breakout regime
    if ratio < 0.7:
        # Breakout: use momentum direction
        if len(closes) >= 6:
            mom = closes[-1] - closes[-6]
            signal = "LONG" if mom > 0 else "SHORT"
        detail = f"Breakout regime ratio={ratio:.3f}"
        tp_pct = (3.0 * atr_val / price) * 100
        sl_pct = (1.5 * atr_val / price) * 100
    # High short-term vol => mean reversion regime
    elif ratio > 1.5:
        sma20 = statistics.mean(closes[-20:]) if len(closes) >= 20 else None
        if sma20 is not None:
            signal = "LONG" if price < sma20 else "SHORT"
        detail = f"Mean-revert regime ratio={ratio:.3f}"
        tp_pct = (2.0 * atr_val / price) * 100
        sl_pct = (1.0 * atr_val / price) * 100
    else:
        return None

    if not signal:
        return None

    return _make_pick(symbol, "vol_term_structure", signal, price,
                      tp_pct, sl_pct, detail)


# ---------------------------------------------------------------------------
# RSI helper (Wilder 1978 smoothing)
# ---------------------------------------------------------------------------

def _rsi(closes: List[float], period: int = 14) -> List[Optional[float]]:
    """Relative Strength Index with Wilder smoothing."""
    result: List[Optional[float]] = [None] * len(closes)
    if len(closes) < period + 1:
        return result

    gains = []
    losses = []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))

    # Seed with SMA
    avg_gain = statistics.mean(gains[:period])
    avg_loss = statistics.mean(losses[:period])

    for i in range(period, len(gains)):
        if i == period:
            ag = avg_gain
            al = avg_loss
        else:
            ag = (ag * (period - 1) + gains[i]) / period
            al = (al * (period - 1) + losses[i]) / period

        if al == 0:
            result[i + 1] = 100.0
        else:
            rs = ag / al
            result[i + 1] = 100.0 - (100.0 / (1.0 + rs))

    return result


# ---------------------------------------------------------------------------
# VWAP helper
# ---------------------------------------------------------------------------

def _vwap(closes: List[float], highs: List[float], lows: List[float],
          volumes: List[float]) -> List[float]:
    """Cumulative VWAP (resets each session -- approximated as rolling 20-bar)."""
    n = len(closes)
    result = []
    for i in range(n):
        start = max(0, i - 19)
        tp_sum = 0.0
        vol_sum = 0.0
        for j in range(start, i + 1):
            typical = (highs[j] + lows[j] + closes[j]) / 3.0
            tp_sum += typical * volumes[j]
            vol_sum += volumes[j]
        if vol_sum > 0:
            result.append(tp_sum / vol_sum)
        else:
            result.append(closes[i])
    return result


# ---------------------------------------------------------------------------
# Strategy 9: Bayesian Posterior Updates (#13 in catalog, 64-70% WR)
# ---------------------------------------------------------------------------
# Maintain prior P(up|features) and update with each bar via Bayes rule.
# Features: 5-bar momentum direction, volume surge, close vs SMA(20).
# BUY when posterior > 0.65, SELL when posterior < 0.35.
#
# Reference: De Prado (2018) "Advances in Financial Machine Learning", Ch.3
#            Kevin Murphy (2012) "Machine Learning: A Probabilistic Perspective"
# ---------------------------------------------------------------------------

def _eval_bayesian_posterior(ohlcv: Dict[str, List[float]], symbol: str,
                             price: float, atr_val: float) -> Optional[Dict]:
    """Bayesian posterior probability of upward move."""
    closes = ohlcv["close"]
    volumes = ohlcv["volume"]
    if len(closes) < 30 or len(volumes) < 30:
        return None

    # Compute features for last 20 bars, then update posterior
    sma20 = statistics.mean(closes[-20:])

    # Prior: start at 0.5 (uninformative)
    posterior = 0.5

    # Likelihood parameters (empirical from crypto: momentum + volume + trend)
    # P(feature | up) and P(feature | down)
    for i in range(-20, 0):
        idx = len(closes) + i
        if idx < 5:
            continue

        # Feature 1: 5-bar momentum positive?
        mom_up = 1 if closes[idx] > closes[idx - 5] else 0
        # Feature 2: volume above 20-bar average?
        vol_avg = statistics.mean(volumes[max(0, idx - 19):idx + 1])
        vol_surge = 1 if volumes[idx] > 1.2 * vol_avg else 0
        # Feature 3: close above SMA(20)?
        sma_window = closes[max(0, idx - 19):idx + 1]
        local_sma = statistics.mean(sma_window) if len(sma_window) >= 10 else closes[idx]
        above_sma = 1 if closes[idx] > local_sma else 0

        # Observed: did next bar go up?
        if idx + 1 < len(closes):
            actual_up = 1 if closes[idx + 1] > closes[idx] else 0
        else:
            actual_up = 1 if closes[idx] > closes[idx - 1] else 0

        # Likelihood: P(features | up) and P(features | down)
        # Higher likelihood when features align with actual direction
        feature_score = (mom_up + vol_surge + above_sma) / 3.0

        if actual_up:
            likelihood_up = 0.5 + 0.3 * feature_score    # P(features | up)
            likelihood_down = 0.5 - 0.2 * feature_score   # P(features | down)
        else:
            likelihood_up = 0.5 - 0.2 * feature_score
            likelihood_down = 0.5 + 0.3 * feature_score

        # Bayes update: P(up|D) = P(D|up)*P(up) / [P(D|up)*P(up) + P(D|down)*P(down)]
        numerator = likelihood_up * posterior
        denominator = numerator + likelihood_down * (1.0 - posterior)
        if denominator > 0:
            posterior = numerator / denominator

        # Clamp to avoid degenerate priors
        posterior = max(0.01, min(0.99, posterior))

    signal = None
    if posterior > 0.65:
        signal = "LONG"
    elif posterior < 0.35:
        signal = "SHORT"

    if not signal:
        return None

    confidence = abs(posterior - 0.5) * 2.0  # 0..1 scale
    tp_pct = (2.5 * atr_val / price) * 100
    sl_pct = (1.5 * atr_val / price) * 100
    return _make_pick(symbol, "bayesian_posterior", signal, price,
                      tp_pct, sl_pct,
                      f"P(up)={posterior:.3f} conf={confidence:.3f}")


# ---------------------------------------------------------------------------
# Strategy 10: Z-Score Momentum (#22 in catalog, 62-68% WR)
# ---------------------------------------------------------------------------
# Compute z-score of 20-day returns. BUY when z > 1.5 (strong momentum),
# SELL when z < -1.5 (strong negative momentum).
# Mean-revert when |z| > 2.5 (exhaustion).
#
# Reference: Jegadeesh & Titman (1993) "Returns to Buying Winners and
#            Selling Losers"; Moskowitz, Ooi & Pedersen (2012) "TSMOM"
# ---------------------------------------------------------------------------

def _eval_zscore_momentum_qr(ohlcv: Dict[str, List[float]], symbol: str,
                              price: float, atr_val: float) -> Optional[Dict]:
    """Z-score of 20-bar returns for momentum and mean-reversion signals."""
    closes = ohlcv["close"]
    if len(closes) < 30:
        return None

    # Compute returns over last 30 bars
    returns = []
    for i in range(1, len(closes)):
        if closes[i - 1] > 0:
            returns.append((closes[i] - closes[i - 1]) / closes[i - 1])
        else:
            returns.append(0.0)

    if len(returns) < 20:
        return None

    window = returns[-20:]
    mean_ret = statistics.mean(window)
    std_ret = statistics.pstdev(window)
    if std_ret == 0:
        return None

    # Current bar return z-score relative to 20-bar distribution
    current_ret = returns[-1]
    z = (current_ret - mean_ret) / std_ret

    # Also compute cumulative z-score of the 20-bar return
    cum_ret = (closes[-1] - closes[-21]) / closes[-21] if closes[-21] > 0 else 0
    cum_returns = []
    for i in range(20, len(closes)):
        cr = (closes[i] - closes[i - 20]) / closes[i - 20] if closes[i - 20] > 0 else 0
        cum_returns.append(cr)

    if len(cum_returns) < 5:
        return None

    cum_mean = statistics.mean(cum_returns[-10:])
    cum_std = statistics.pstdev(cum_returns[-10:])
    if cum_std == 0:
        return None

    cum_z = (cum_ret - cum_mean) / cum_std

    signal = None
    detail = ""

    # Mean-reversion at extremes (exhaustion)
    if cum_z > 2.5:
        signal = "SHORT"
        detail = f"Exhaustion reversal cum_z={cum_z:.2f}"
        tp_pct = (2.0 * atr_val / price) * 100
        sl_pct = (1.5 * atr_val / price) * 100
    elif cum_z < -2.5:
        signal = "LONG"
        detail = f"Exhaustion reversal cum_z={cum_z:.2f}"
        tp_pct = (2.0 * atr_val / price) * 100
        sl_pct = (1.5 * atr_val / price) * 100
    # Momentum at intermediate z-scores
    elif cum_z > 1.5:
        signal = "LONG"
        detail = f"Momentum continuation cum_z={cum_z:.2f}"
        tp_pct = (3.0 * atr_val / price) * 100
        sl_pct = (1.5 * atr_val / price) * 100
    elif cum_z < -1.5:
        signal = "SHORT"
        detail = f"Momentum continuation cum_z={cum_z:.2f}"
        tp_pct = (3.0 * atr_val / price) * 100
        sl_pct = (1.5 * atr_val / price) * 100

    if not signal:
        return None

    return _make_pick(symbol, "zscore_momentum_qr", signal, price,
                      tp_pct, sl_pct, detail)


# ---------------------------------------------------------------------------
# Strategy 11: Gaussian Mean Reversion (#11 in catalog, 62-68% WR)
# ---------------------------------------------------------------------------
# Model price distribution as Gaussian. BUY when price < mean - 2*sigma,
# SELL when > mean + 2*sigma. Dynamic sigma from simplified GARCH(1,1).
#
# Reference: Bollerslev (1986) "Generalized Autoregressive Conditional
#            Heteroskedasticity"; Avellaneda & Lee (2010) "Statistical Arb"
# ---------------------------------------------------------------------------

def _garch_sigma(returns: List[float], omega: float = 0.00001,
                 alpha: float = 0.1, beta: float = 0.85) -> float:
    """Simplified GARCH(1,1) variance estimate from return series.

    sigma_t^2 = omega + alpha * r_{t-1}^2 + beta * sigma_{t-1}^2
    """
    if not returns:
        return 0.0

    # Seed with sample variance
    var = statistics.pvariance(returns) if len(returns) > 1 else returns[0] ** 2

    for r in returns:
        var = omega + alpha * (r ** 2) + beta * var

    return math.sqrt(max(var, 1e-12))


def _eval_gaussian_mean_revert(ohlcv: Dict[str, List[float]], symbol: str,
                                price: float, atr_val: float) -> Optional[Dict]:
    """Gaussian mean-reversion with GARCH dynamic sigma."""
    closes = ohlcv["close"]
    if len(closes) < 40:
        return None

    # Compute log returns
    log_returns = []
    for i in range(1, len(closes)):
        if closes[i] > 0 and closes[i - 1] > 0:
            log_returns.append(math.log(closes[i] / closes[i - 1]))

    if len(log_returns) < 30:
        return None

    # GARCH(1,1) dynamic sigma
    sigma = _garch_sigma(log_returns[-30:])
    if sigma <= 0:
        return None

    # Rolling mean of closes (30-bar)
    mean_price = statistics.mean(closes[-30:])

    # Z-score of current price in Gaussian model
    price_sigma = mean_price * sigma  # Convert return vol to price vol
    if price_sigma <= 0:
        return None

    z = (price - mean_price) / price_sigma

    signal = None
    if z <= -2.0:
        signal = "LONG"
    elif z >= 2.0:
        signal = "SHORT"

    if not signal:
        return None

    tp_pct = (2.0 * atr_val / price) * 100
    sl_pct = (1.5 * atr_val / price) * 100
    return _make_pick(symbol, "gaussian_mean_revert", signal, price,
                      tp_pct, sl_pct,
                      f"z={z:.2f} sigma={sigma:.6f} mean={mean_price:.2f}")


# ---------------------------------------------------------------------------
# Strategy 12: VWAP Deviation Trading (#63 in catalog, 62-68% WR)
# ---------------------------------------------------------------------------
# BUY when price is >1% below VWAP with volume surge (>1.5x avg).
# SELL when >1% above VWAP with declining volume (<0.8x avg).
# Uses rolling 20-bar VWAP approximation.
#
# Reference: Brian Shannon (2018) "Technical Analysis Using Multiple
#            Timeframes"; Kevin Davey "Building Winning Algorithmic
#            Trading Systems" (2014)
# ---------------------------------------------------------------------------

def _eval_vwap_deviation_trade(ohlcv: Dict[str, List[float]], symbol: str,
                                price: float, atr_val: float) -> Optional[Dict]:
    """VWAP deviation with volume confirmation."""
    closes = ohlcv["close"]
    highs = ohlcv["high"]
    lows = ohlcv["low"]
    volumes = ohlcv["volume"]

    if len(closes) < 25 or len(volumes) < 25:
        return None

    # Compute rolling VWAP
    vwap_vals = _vwap(closes, highs, lows, volumes)
    current_vwap = vwap_vals[-1]

    if current_vwap <= 0:
        return None

    # VWAP deviation percentage
    deviation_pct = ((price - current_vwap) / current_vwap) * 100.0

    # Volume analysis: current vs 20-bar average
    vol_avg = statistics.mean(volumes[-20:])
    if vol_avg <= 0:
        return None
    vol_ratio = volumes[-1] / vol_avg

    signal = None
    detail = ""

    # BUY: price >1% below VWAP with volume surge (>1.5x)
    if deviation_pct < -1.0 and vol_ratio > 1.5:
        signal = "LONG"
        detail = f"Below VWAP dev={deviation_pct:.2f}% vol_ratio={vol_ratio:.2f}"
        tp_pct = (2.5 * atr_val / price) * 100
        sl_pct = (1.5 * atr_val / price) * 100
    # SELL: price >1% above VWAP with declining volume (<0.8x)
    elif deviation_pct > 1.0 and vol_ratio < 0.8:
        signal = "SHORT"
        detail = f"Above VWAP dev={deviation_pct:.2f}% vol_ratio={vol_ratio:.2f}"
        tp_pct = (2.5 * atr_val / price) * 100
        sl_pct = (1.5 * atr_val / price) * 100

    if not signal:
        return None

    return _make_pick(symbol, "vwap_deviation_trade", signal, price,
                      tp_pct, sl_pct, detail)


# ---------------------------------------------------------------------------
# Strategy 13: Dynamic RSI Percentile Thresholds (#56 in catalog, 63-68% WR)
# ---------------------------------------------------------------------------
# Instead of fixed 30/70 RSI thresholds, compute rolling percentiles of RSI
# values. BUY when RSI hits its own 10th percentile (adaptive oversold),
# SELL when RSI hits its own 90th percentile (adaptive overbought).
#
# Reference: Connors & Alvarez (2009) "Short-Term Trading Strategies That
#            Work"; Chande (1997) "Beyond Technical Analysis"
# ---------------------------------------------------------------------------

def _percentile(values: List[float], pct: float) -> float:
    """Simple percentile calculation (0-100 scale)."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    k = (pct / 100.0) * (n - 1)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)


def _eval_dynamic_rsi_percentile(ohlcv: Dict[str, List[float]], symbol: str,
                                  price: float, atr_val: float) -> Optional[Dict]:
    """Dynamic RSI thresholds via rolling percentiles."""
    closes = ohlcv["close"]
    if len(closes) < 50:
        return None

    rsi_vals = _rsi(closes, 14)

    # Collect valid RSI values for percentile calculation (last 50 bars)
    valid_rsi = [v for v in rsi_vals[-50:] if v is not None]
    if len(valid_rsi) < 30:
        return None

    current_rsi = rsi_vals[-1]
    if current_rsi is None:
        return None

    # Compute dynamic thresholds from RSI distribution
    low_thresh = _percentile(valid_rsi, 10.0)    # 10th percentile
    high_thresh = _percentile(valid_rsi, 90.0)    # 90th percentile

    # Also check RSI slope (2-bar) for confirmation
    prev_rsi = rsi_vals[-2] if rsi_vals[-2] is not None else current_rsi

    signal = None
    detail = ""

    # BUY: RSI at its own 10th percentile (adaptive oversold) + turning up
    if current_rsi <= low_thresh and current_rsi > prev_rsi:
        signal = "LONG"
        detail = (f"RSI={current_rsi:.1f} <= P10={low_thresh:.1f} "
                  f"(P90={high_thresh:.1f}) turning up")
        tp_pct = (2.5 * atr_val / price) * 100
        sl_pct = (1.5 * atr_val / price) * 100
    # SELL: RSI at its own 90th percentile (adaptive overbought) + turning down
    elif current_rsi >= high_thresh and current_rsi < prev_rsi:
        signal = "SHORT"
        detail = (f"RSI={current_rsi:.1f} >= P90={high_thresh:.1f} "
                  f"(P10={low_thresh:.1f}) turning down")
        tp_pct = (2.5 * atr_val / price) * 100
        sl_pct = (1.5 * atr_val / price) * 100

    if not signal:
        return None

    return _make_pick(symbol, "dynamic_rsi_percentile", signal, price,
                      tp_pct, sl_pct, detail)


# ---------------------------------------------------------------------------
# Pick builder
# ---------------------------------------------------------------------------

def _make_pick(symbol: str, strategy: str, signal: str, price: float,
               tp_pct: float, sl_pct: float, detail: str) -> Dict[str, Any]:
    """Build a standardized pick dictionary."""
    if signal == "LONG":
        tp_price = price * (1.0 + tp_pct / 100.0)
        sl_price = price * (1.0 - sl_pct / 100.0)
    else:
        tp_price = price * (1.0 - tp_pct / 100.0)
        sl_price = price * (1.0 + sl_pct / 100.0)

    return {
        "symbol": symbol,
        "strategy": strategy,
        "direction": signal,
        "entry_price": round(price, 8),
        "take_profit": round(tp_price, 8),
        "stop_loss": round(sl_price, 8),
        "tp_pct": round(tp_pct, 2),
        "sl_pct": round(sl_pct, 2),
        "category": "crypto",
        "timeframe": "4h",
        "detail": detail,
        "source": "quant_research",
        "timestamp": _now_iso(),
    }


# ---------------------------------------------------------------------------
# Strategy registry
# ---------------------------------------------------------------------------

QUANT_RESEARCH_STRATEGIES: Dict[str, Dict[str, Any]] = {
    "fisher_transform": {
        "name": "Ehlers Fisher Transform",
        "category": "crypto",
        "symbols": _DEFAULT_SYMBOLS,
        "timeframe": "4h",
        "description": "Ehlers Fisher Transform crossover -- Long below -1, Short above +1",
        "win_rate_est": "58-65%",
        "references": [
            "John Ehlers, Cybernetic Analysis for Stocks and Futures (2004)",
        ],
    },
    "garman_klass_breakout": {
        "name": "Garman-Klass Volatility Breakout",
        "category": "crypto",
        "symbols": _DEFAULT_SYMBOLS,
        "timeframe": "4h",
        "description": "GK vol > mean+1.5*std with 5-bar momentum direction",
        "win_rate_est": "55-62%",
        "references": [
            "Garman & Klass, On the Estimation of Security Price Volatilities (1980)",
        ],
    },
    "ttm_squeeze": {
        "name": "TTM Squeeze Release",
        "category": "crypto",
        "symbols": _DEFAULT_SYMBOLS,
        "timeframe": "4h",
        "description": "BB(20,2) inside KC(20,1.5*ATR) squeeze -- trade release via linreg slope",
        "win_rate_est": "60-68%",
        "references": [
            "John Carter, Mastering the Trade (2005) -- TTM Squeeze",
        ],
    },
    "hurst_mean_reversion": {
        "name": "Hurst Exponent Mean Reversion",
        "category": "crypto",
        "symbols": _DEFAULT_SYMBOLS,
        "timeframe": "4h",
        "description": "R/S Hurst < 0.45 and price 2+ std from mean -- mean-revert",
        "win_rate_est": "55-60%",
        "references": [
            "H.E. Hurst, Long-term storage capacity of reservoirs (1951)",
            "Edgar Peters, Fractal Market Analysis (1994)",
        ],
    },
    "kama_trend": {
        "name": "Kaufman Adaptive MA Trend",
        "category": "crypto",
        "symbols": _DEFAULT_SYMBOLS,
        "timeframe": "4h",
        "description": "KAMA with ER > 0.3 filter -- trend-following",
        "win_rate_est": "58-65%",
        "references": [
            "Perry Kaufman, Trading Systems and Methods (1995, 6th ed 2019)",
        ],
    },
    "vortex_crossover": {
        "name": "Vortex Indicator Crossover",
        "category": "crypto",
        "symbols": _DEFAULT_SYMBOLS,
        "timeframe": "4h",
        "description": "VI+ / VI- crossover with 0.1 minimum spread",
        "win_rate_est": "55-62%",
        "references": [
            "Etienne Botes & Douglas Siepman, The Vortex Indicator (2010, TASC)",
        ],
    },
    "amihud_reversal": {
        "name": "Amihud Illiquidity Reversal",
        "category": "crypto",
        "symbols": _DEFAULT_SYMBOLS,
        "timeframe": "4h",
        "description": "Amihud illiquidity z > 2 with >2% price move -- reversal",
        "win_rate_est": "52-58%",
        "references": [
            "Yakov Amihud, Illiquidity and stock returns (2002, JFM)",
        ],
    },
    "vol_term_structure": {
        "name": "Volatility Term Structure Regime",
        "category": "crypto",
        "symbols": _DEFAULT_SYMBOLS,
        "timeframe": "4h",
        "description": "RV(5)/RV(30) ratio -- <0.7 breakout, >1.5 mean-revert",
        "win_rate_est": "55-62%",
        "references": [
            "Emanuel Derman, The Volatility Smile (2016)",
        ],
    },
    "bayesian_posterior": {
        "name": "Bayesian Posterior Updates",
        "category": "crypto",
        "symbols": _DEFAULT_SYMBOLS,
        "timeframe": "4h",
        "description": "Bayesian P(up|features) updated each bar -- BUY >0.65, SELL <0.35",
        "win_rate_est": "64-70%",
        "references": [
            "De Prado (2018) Advances in Financial Machine Learning, Ch.3",
            "Kevin Murphy (2012) Machine Learning: A Probabilistic Perspective",
        ],
    },
    "zscore_momentum_qr": {
        "name": "Z-Score Momentum",
        "category": "crypto",
        "symbols": _DEFAULT_SYMBOLS,
        "timeframe": "4h",
        "description": "Z-score of 20-bar returns: momentum |z|>1.5, mean-revert |z|>2.5",
        "win_rate_est": "62-68%",
        "references": [
            "Jegadeesh & Titman (1993) Returns to Buying Winners and Selling Losers",
            "Moskowitz, Ooi & Pedersen (2012) Time-Series Momentum",
        ],
    },
    "gaussian_mean_revert": {
        "name": "Gaussian Mean Reversion (GARCH sigma)",
        "category": "crypto",
        "symbols": _DEFAULT_SYMBOLS,
        "timeframe": "4h",
        "description": "Gaussian model with GARCH(1,1) dynamic sigma -- BUY <-2sigma, SELL >+2sigma",
        "win_rate_est": "62-68%",
        "references": [
            "Bollerslev (1986) Generalized Autoregressive Conditional Heteroskedasticity",
            "Avellaneda & Lee (2010) Statistical Arbitrage in the US Equities Market",
        ],
    },
    "vwap_deviation_trade": {
        "name": "VWAP Deviation Trading",
        "category": "crypto",
        "symbols": _DEFAULT_SYMBOLS,
        "timeframe": "4h",
        "description": "BUY >1% below VWAP + vol surge, SELL >1% above VWAP + vol decline",
        "win_rate_est": "62-68%",
        "references": [
            "Brian Shannon (2018) Technical Analysis Using Multiple Timeframes",
            "Kevin Davey (2014) Building Winning Algorithmic Trading Systems",
        ],
    },
    "dynamic_rsi_percentile": {
        "name": "Dynamic RSI Percentile Thresholds",
        "category": "crypto",
        "symbols": _DEFAULT_SYMBOLS,
        "timeframe": "4h",
        "description": "RSI with rolling 10th/90th percentile thresholds instead of fixed 30/70",
        "win_rate_est": "63-68%",
        "references": [
            "Connors & Alvarez (2009) Short-Term Trading Strategies That Work",
            "Chande (1997) Beyond Technical Analysis",
        ],
    },
}


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

_EVALUATORS = [
    _eval_fisher_transform,
    _eval_garman_klass,
    _eval_ttm_squeeze,
    _eval_hurst_mean_reversion,
    _eval_kama_trend,
    _eval_vortex_crossover,
    _eval_amihud_reversal,
    _eval_vol_term_structure,
    _eval_bayesian_posterior,
    _eval_zscore_momentum_qr,
    _eval_gaussian_mean_revert,
    _eval_vwap_deviation_trade,
    _eval_dynamic_rsi_percentile,
]


def generate_quant_picks(symbols: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Generate picks from all 13 quant research strategies.

    Args:
        symbols: List of trading pairs (default: _DEFAULT_SYMBOLS).

    Returns:
        List of pick dicts with entry/TP/SL.
    """
    if symbols is None:
        symbols = _DEFAULT_SYMBOLS

    picks: List[Dict[str, Any]] = []

    for symbol in symbols:
        klines = _fetch_klines(symbol, interval="4h", limit=100)
        if not klines:
            continue

        ohlcv = _parse_ohlcv(klines)
        if len(ohlcv["close"]) < 20:
            continue

        price = ohlcv["close"][-1]
        atr_val = _atr(ohlcv["high"], ohlcv["low"], ohlcv["close"], 14)
        if atr_val <= 0 or price <= 0:
            continue

        for evaluator in _EVALUATORS:
            try:
                pick = evaluator(ohlcv, symbol, price, atr_val)
                if pick:
                    picks.append(pick)
            except Exception:
                continue

    return picks
