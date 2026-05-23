"""
ALPHA_ENGINE -- Technical Features (Chi-Squared Validated, 92.4% XGBoost Accuracy)
==================================================================================
7 proven-predictive technical indicators validated by chi-squared statistical test
in academic research. Pure Python implementation (stdlib + math only, no numpy).

Features:
  MOM30       -- 30-period momentum: (close[-1] / close[-31]) - 1
  RSI30       -- 30-period RSI (Wilder smoothing), normalized [0, 1]
  MACD_hist   -- MACD histogram normalized by price, clipped [-0.05, 0.05]
  Stoch_K30   -- 30-period Stochastic %K [0, 1]
  Stoch_D30   -- 3-period SMA of %K30 [0, 1]
  CCI20       -- Commodity Channel Index 20, normalized [-1, 1]
  Williams_R  -- Williams %R 14-period [-1, 0]

All functions accept plain Python lists (no numpy/pandas required).
"""

from __future__ import annotations

import math


def _ema(values: list[float], span: int) -> list[float]:
    """Compute exponential moving average with given span. Returns list same length as input."""
    if not values:
        return []
    alpha = 2.0 / (span + 1)
    result = [values[0]]
    for i in range(1, len(values)):
        result.append(alpha * values[i] + (1 - alpha) * result[-1])
    return result


def _sma(values: list[float], period: int) -> list[float]:
    """Compute simple moving average. Returns list same length; first (period-1) entries are NaN."""
    result = [float('nan')] * len(values)
    if len(values) < period:
        return result
    window_sum = sum(values[:period])
    result[period - 1] = window_sum / period
    for i in range(period, len(values)):
        window_sum += values[i] - values[i - period]
        result[i] = window_sum / period
    return result


def _wilder_smooth(values: list[float], period: int) -> list[float]:
    """Wilder smoothing (used by RSI). First value is SMA, then exponential with alpha=1/period."""
    if len(values) < period:
        return [float('nan')] * len(values)
    result = [float('nan')] * len(values)
    # Seed with SMA of first `period` values
    result[period - 1] = sum(values[:period]) / period
    alpha = 1.0 / period
    for i in range(period, len(values)):
        result[i] = alpha * values[i] + (1 - alpha) * result[i - 1]
    return result


def compute_mom30(closes: list[float]) -> float:
    """30-period momentum: (close[-1] / close[-31]) - 1, clipped to [-0.5, 0.5]."""
    if len(closes) < 31:
        return 0.0
    if closes[-31] == 0:
        return 0.0
    mom = (closes[-1] / closes[-31]) - 1.0
    return max(-0.5, min(0.5, mom))


def compute_rsi30(closes: list[float]) -> float:
    """30-period RSI with Wilder smoothing, normalized to [0, 1]."""
    period = 30
    if len(closes) < period + 1:
        return 0.5  # neutral default
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]

    avg_gain = _wilder_smooth(gains, period)
    avg_loss = _wilder_smooth(losses, period)

    last_gain = avg_gain[-1]
    last_loss = avg_loss[-1]
    if math.isnan(last_gain) or math.isnan(last_loss):
        return 0.5

    if last_loss == 0:
        return 1.0 if last_gain > 0 else 0.5
    rs = last_gain / last_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi / 100.0  # normalize to [0, 1]


def compute_macd_hist(closes: list[float]) -> float:
    """MACD histogram (EMA12 - EMA26 - Signal9), normalized by price, clipped [-0.05, 0.05]."""
    if len(closes) < 35:
        return 0.0
    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    macd_line = [e12 - e26 for e12, e26 in zip(ema12, ema26)]
    signal_line = _ema(macd_line, 9)
    histogram = macd_line[-1] - signal_line[-1]

    price = closes[-1]
    if price == 0:
        return 0.0
    normalized = histogram / price
    return max(-0.05, min(0.05, normalized))


def compute_stoch_k30(closes: list[float], highs: list[float], lows: list[float]) -> float:
    """30-period Stochastic %K: (close - lowest_30) / (highest_30 - lowest_30), [0, 1]."""
    period = 30
    if len(closes) < period or len(highs) < period or len(lows) < period:
        return 0.5
    highest = max(highs[-period:])
    lowest = min(lows[-period:])
    range_val = highest - lowest
    if range_val == 0:
        return 0.5
    k = (closes[-1] - lowest) / range_val
    return max(0.0, min(1.0, k))


def compute_stoch_d30(closes: list[float], highs: list[float], lows: list[float]) -> float:
    """3-period SMA of %K30 (Stochastic %D), [0, 1]."""
    period_k = 30
    period_d = 3
    needed = period_k + period_d - 1
    if len(closes) < needed or len(highs) < needed or len(lows) < needed:
        return 0.5

    # Compute %K for last 3 periods
    k_values = []
    for offset in range(period_d):
        idx = len(closes) - period_d + offset + 1  # end index (exclusive)
        start = idx - period_k
        if start < 0:
            k_values.append(0.5)
            continue
        highest = max(highs[start:idx])
        lowest = min(lows[start:idx])
        range_val = highest - lowest
        if range_val == 0:
            k_values.append(0.5)
        else:
            k = (closes[idx - 1] - lowest) / range_val
            k_values.append(max(0.0, min(1.0, k)))

    d = sum(k_values) / len(k_values)
    return max(0.0, min(1.0, d))


def compute_cci20(closes: list[float], highs: list[float], lows: list[float]) -> float:
    """CCI 20-period: (typical_price - SMA20) / (0.015 * mean_deviation), clipped [-3,3] then /3."""
    period = 20
    if len(closes) < period or len(highs) < period or len(lows) < period:
        return 0.0

    # Typical prices for last `period` bars
    tp_values = [(highs[-(period - i)] + lows[-(period - i)] + closes[-(period - i)]) / 3.0
                 for i in range(period)]
    tp_current = tp_values[-1]
    tp_mean = sum(tp_values) / period

    # Mean deviation
    mean_dev = sum(abs(tp - tp_mean) for tp in tp_values) / period
    if mean_dev == 0:
        return 0.0

    cci = (tp_current - tp_mean) / (0.015 * mean_dev)
    cci_clipped = max(-3.0, min(3.0, cci))
    return cci_clipped / 3.0  # normalize to [-1, 1]


def compute_williams_r(closes: list[float], highs: list[float], lows: list[float]) -> float:
    """Williams %R 14-period: (highest_14 - close) / (highest_14 - lowest_14) * -1, [-1, 0]."""
    period = 14
    if len(closes) < period or len(highs) < period or len(lows) < period:
        return -0.5  # neutral default
    highest = max(highs[-period:])
    lowest = min(lows[-period:])
    range_val = highest - lowest
    if range_val == 0:
        return -0.5
    wr = -1.0 * (highest - closes[-1]) / range_val
    return max(-1.0, min(0.0, wr))


# ---------------------------------------------------------------------------
# qlib Alpha158-family factors (2026-05-17) — volume + volatility + price-volume
# correlation. These are absent from the original 7; qlib's empirical research
# ranks price-volume correlation and volume factors among the highest-IC
# signals. Pure stdlib, same normalisation discipline as above.
# ---------------------------------------------------------------------------

def compute_volume_ratio(volumes: list[float], short: int = 5, long: int = 30) -> float:
    """Volume momentum: short-window mean volume / long-window mean volume,
    mapped to [-1, 1] (0 = volume in line with its longer baseline).

    qlib VMA family. >0 means recent volume expansion (often confirms a move).
    """
    if len(volumes) < long:
        return 0.0
    short_avg = sum(volumes[-short:]) / short
    long_avg = sum(volumes[-long:]) / long
    if long_avg <= 0:
        return 0.0
    ratio = short_avg / long_avg          # ~1.0 when in line
    # log-ratio keeps it symmetric; clip to [-1, 1].
    val = math.log(ratio) if ratio > 0 else 0.0
    return max(-1.0, min(1.0, val))


def compute_price_volume_corr(closes: list[float], volumes: list[float],
                               period: int = 30) -> float:
    """Pearson correlation of close price vs volume over `period` bars, [-1, 1].

    qlib CORR factor. Positive = price rises on rising volume (healthy trend);
    negative = price moves against volume (distribution / exhaustion).
    """
    if len(closes) < period or len(volumes) < period:
        return 0.0
    c = closes[-period:]
    v = volumes[-period:]
    n = period
    mc, mv = sum(c) / n, sum(v) / n
    cov = sum((c[i] - mc) * (v[i] - mv) for i in range(n))
    var_c = sum((x - mc) ** 2 for x in c)
    var_v = sum((x - mv) ** 2 for x in v)
    denom = math.sqrt(var_c * var_v)
    if denom == 0:
        return 0.0
    return max(-1.0, min(1.0, cov / denom))


def compute_realized_vol(closes: list[float], period: int = 30) -> float:
    """Realized volatility — std-dev of simple returns over `period` bars,
    clipped to [0, 1]. qlib STD factor.

    A volatility *level* feature (not directional); useful for regime / sizing.
    """
    if len(closes) < period + 1:
        return 0.0
    rets = []
    for i in range(len(closes) - period, len(closes)):
        prev = closes[i - 1]
        if prev > 0:
            rets.append(closes[i] / prev - 1.0)
    if len(rets) < 2:
        return 0.0
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    std = math.sqrt(var)
    return max(0.0, min(1.0, std * 10.0))   # ~10% bar-vol saturates to 1.0


def compute_technical_features(closes: list[float], highs: list[float],
                                lows: list[float], volumes: list[float]) -> dict:
    """Compute 7 proven technical indicators from OHLCV arrays.

    Returns dict of feature_name -> value (all normalized to roughly -1 to +1 or 0 to 1 range).
    Requires minimum 200 data points for full coverage.
    Falls back gracefully with fewer points.

    Features (chi-squared validated, 92.4% accuracy with XGBoost):
      mom30          -- 30-period momentum [-0.5, 0.5]
      rsi30          -- 30-period RSI [0, 1]
      macd_hist_norm -- MACD histogram / price [-0.05, 0.05]
      stoch_k30      -- 30-period Stochastic %K [0, 1]
      stoch_d30      -- 3-period SMA of %K30 [0, 1]
      cci20_norm     -- CCI 20 normalized [-1, 1]
      williams_r     -- Williams %R 14 [-1, 0]
      vol_ratio      -- volume short/long log-ratio [-1, 1]   (qlib VMA)
      pv_corr30      -- price-volume Pearson corr 30 [-1, 1]   (qlib CORR)
      realized_vol30 -- realized return volatility 30 [0, 1]   (qlib STD)
    """
    return {
        "mom30": compute_mom30(closes),
        "rsi30": compute_rsi30(closes),
        "macd_hist_norm": compute_macd_hist(closes),
        "stoch_k30": compute_stoch_k30(closes, highs, lows),
        "stoch_d30": compute_stoch_d30(closes, highs, lows),
        "cci20_norm": compute_cci20(closes, highs, lows),
        "williams_r": compute_williams_r(closes, highs, lows),
        "vol_ratio": compute_volume_ratio(volumes),
        "pv_corr30": compute_price_volume_corr(closes, volumes),
        "realized_vol30": compute_realized_vol(closes),
    }


def compute_all_from_klines(klines_list: list) -> dict:
    """Takes list of Binance kline arrays, extracts OHLCV, computes all features.

    Each kline is expected to be a list/tuple where:
      [0] = open_time, [1] = open, [2] = high, [3] = low, [4] = close, [5] = volume
    """
    if not klines_list or len(klines_list) < 10:
        return {
            "mom30": 0.0, "rsi30": 0.5, "macd_hist_norm": 0.0,
            "stoch_k30": 0.5, "stoch_d30": 0.5, "cci20_norm": 0.0,
            "williams_r": -0.5,
            "vol_ratio": 0.0, "pv_corr30": 0.0, "realized_vol30": 0.0,
        }

    closes = []
    highs = []
    lows = []
    volumes = []

    for k in klines_list:
        try:
            closes.append(float(k[4]))
            highs.append(float(k[2]))
            lows.append(float(k[3]))
            volumes.append(float(k[5]))
        except (IndexError, TypeError, ValueError):
            continue

    if len(closes) < 10:
        return {
            "mom30": 0.0, "rsi30": 0.5, "macd_hist_norm": 0.0,
            "stoch_k30": 0.5, "stoch_d30": 0.5, "cci20_norm": 0.0,
            "williams_r": -0.5,
            "vol_ratio": 0.0, "pv_corr30": 0.0, "realized_vol30": 0.0,
        }

    return compute_technical_features(closes, highs, lows, volumes)
