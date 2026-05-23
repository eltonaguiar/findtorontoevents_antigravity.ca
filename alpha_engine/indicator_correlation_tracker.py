#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Indicator Correlation Tracker
==============================
Monitors active picks alongside 13 technical indicators to discover which
indicators actually predict whether a pick will be profitable.

Standalone CLI:  python indicator_correlation_tracker.py
Library export:  get_indicator_filter_recommendations()

Writes:
  - data/indicator_correlation_log.json   (rolling 7-day observation log)
  - data/indicator_predictive_power.json  (ranked indicator stats + recommendations)
"""

from __future__ import annotations

import io, json, math, os, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Windows UTF-8 fix ────────────────────────────────────────────────
if sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

# ── Paths ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ACTIVE_PICKS_PATH = DATA_DIR / "active_picks.json"
CORRELATION_LOG_PATH = DATA_DIR / "indicator_correlation_log.json"
PREDICTIVE_POWER_PATH = DATA_DIR / "indicator_predictive_power.json"

# ── Binance 4-mirror failover (API failover rule) ───────────────────
_BINANCE_KLINE_BASES = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]
# CI: prefer non-geo-blocked endpoints first
if os.environ.get("GITHUB_ACTIONS"):
    _BINANCE_KLINE_BASES = [
        "https://data-api.binance.vision",
        "https://api.binance.us",
    ] + _BINANCE_KLINE_BASES

_COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# Rate limiting
_RATE_LIMIT_SECONDS = 0.5
_REQUEST_TIMEOUT = 10
_last_request_ts: float = 0.0

LOG_RETENTION_DAYS = 7

# ── Indicator names (canonical order) ────────────────────────────────
INDICATOR_NAMES = [
    "rsi_14",
    "rsi_2",
    "macd_histogram",
    "bollinger_pct_b",
    "volume_ratio",
    "atr_pct",
    "ema_alignment",
    "stoch_k",
    "stoch_d",
    "obv_trend",
    "adx",
    "vwap_deviation_pct",
    "consecutive_candles",
    "dist_from_200sma_pct",
]


# =====================================================================
#  HTTP helpers with failover
# =====================================================================

def _rate_limit():
    global _last_request_ts
    elapsed = time.time() - _last_request_ts
    if elapsed < _RATE_LIMIT_SECONDS:
        time.sleep(_RATE_LIMIT_SECONDS - elapsed)
    _last_request_ts = time.time()


def _http_get_json(url: str, timeout: int = _REQUEST_TIMEOUT):
    """GET JSON with timeout. Returns parsed dict/list or None."""
    req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def fetch_klines_binance(symbol: str, interval: str = "1h", limit: int = 100):
    """Fetch klines with 4-mirror failover + CoinGecko fallback.
    Returns list of [open_time, open, high, low, close, volume, ...] or None.
    """
    for base in _BINANCE_KLINE_BASES:
        _rate_limit()
        url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        data = _http_get_json(url)
        if data and isinstance(data, list) and len(data) > 10:
            return data
    return None


def fetch_current_price_binance(symbol: str) -> float | None:
    """Fetch latest price with failover."""
    for base in _BINANCE_KLINE_BASES:
        _rate_limit()
        url = f"{base}/api/v3/ticker/price?symbol={symbol}"
        data = _http_get_json(url)
        if data and "price" in data:
            try:
                return float(data["price"])
            except (ValueError, TypeError):
                continue
    # CoinGecko fallback — convert symbol to CG id heuristic
    cg_id = _symbol_to_coingecko_id(symbol)
    if cg_id:
        _rate_limit()
        url = f"{_COINGECKO_BASE}/simple/price?ids={cg_id}&vs_currencies=usd"
        data = _http_get_json(url)
        if data and cg_id in data:
            return float(data[cg_id].get("usd", 0)) or None
    return None


def _symbol_to_coingecko_id(symbol: str) -> str | None:
    """Best-effort mapping from Binance symbol to CoinGecko id."""
    mapping = {
        "BTC": "bitcoin", "ETH": "ethereum", "BNB": "binancecoin",
        "SOL": "solana", "XRP": "ripple", "DOGE": "dogecoin",
        "ADA": "cardano", "AVAX": "avalanche-2", "DOT": "polkadot",
        "MATIC": "matic-network", "LINK": "chainlink", "ATOM": "cosmos",
        "UNI": "uniswap", "LTC": "litecoin", "FIL": "filecoin",
        "NEAR": "near", "APT": "aptos", "ARB": "arbitrum",
        "OP": "optimism", "SUI": "sui", "SEI": "sei-network",
        "TIA": "celestia", "INJ": "injective-protocol", "FET": "fetch-ai",
        "PEPE": "pepe", "WIF": "dogwifcoin", "RENDER": "render-token",
    }
    base = symbol.replace("USDT", "").replace("BUSD", "").replace("USD", "")
    return mapping.get(base)


# =====================================================================
#  Pure-numpy technical indicator calculations
# =====================================================================

def _to_float_array(klines, idx: int):
    """Extract a column from klines as a list of floats."""
    return [float(k[idx]) for k in klines]


def calc_rsi(closes: list[float], period: int = 14) -> float | None:
    """RSI using Wilder's smoothing method."""
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0) for d in deltas]
    losses = [max(-d, 0) for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def calc_ema(data: list[float], period: int) -> list[float]:
    """Exponential moving average. Returns list same length as data."""
    if len(data) < period:
        return []
    k = 2.0 / (period + 1)
    ema = [sum(data[:period]) / period]
    for val in data[period:]:
        ema.append(val * k + ema[-1] * (1 - k))
    return ema


def calc_sma(data: list[float], period: int) -> list[float]:
    """Simple moving average."""
    if len(data) < period:
        return []
    result = []
    for i in range(period - 1, len(data)):
        result.append(sum(data[i - period + 1: i + 1]) / period)
    return result


def calc_macd_histogram(closes: list[float]) -> float | None:
    """MACD(12,26,9) histogram — last value."""
    if len(closes) < 35:
        return None
    ema12 = calc_ema(closes, 12)
    ema26 = calc_ema(closes, 26)
    # Align: ema12 starts at index 11, ema26 at index 25
    # So macd line starts at index 25 of closes
    offset = 26 - 12  # 14
    macd_line = [ema12[i + offset] - ema26[i] for i in range(len(ema26))]
    if len(macd_line) < 9:
        return None
    signal_line = calc_ema(macd_line, 9)
    # histogram = macd_line aligned to signal
    sig_offset = 9 - 1
    if len(macd_line) <= sig_offset or not signal_line:
        return None
    hist = macd_line[-1] - signal_line[-1]
    return hist


def calc_bollinger_pct_b(closes: list[float], period: int = 20, num_std: float = 2.0) -> float | None:
    """Bollinger %B — where price sits relative to bands (0=lower, 1=upper)."""
    if len(closes) < period:
        return None
    window = closes[-period:]
    mid = sum(window) / period
    variance = sum((x - mid) ** 2 for x in window) / period
    std = math.sqrt(variance)
    if std == 0:
        return 0.5
    upper = mid + num_std * std
    lower = mid - num_std * std
    band_width = upper - lower
    if band_width == 0:
        return 0.5
    return (closes[-1] - lower) / band_width


def calc_volume_ratio(volumes: list[float], period: int = 20) -> float | None:
    """Current volume / 20-period average volume."""
    if len(volumes) < period + 1:
        return None
    avg = sum(volumes[-period - 1:-1]) / period
    if avg == 0:
        return None
    return volumes[-1] / avg


def calc_atr_pct(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> float | None:
    """ATR as percentage of current price."""
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    if len(trs) < period:
        return None
    atr = sum(trs[-period:]) / period
    price = closes[-1]
    if price == 0:
        return None
    return (atr / price) * 100.0


def calc_ema_alignment(closes: list[float]) -> int:
    """Score 0-4: how many EMA pairs are in bullish order (9>21>50>200)."""
    if len(closes) < 200:
        # Use what we can
        pass
    periods = [9, 21, 50, 200]
    emas = {}
    for p in periods:
        e = calc_ema(closes, p)
        if e:
            emas[p] = e[-1]
        else:
            emas[p] = None
    score = 0
    pairs = [(9, 21), (21, 50), (50, 200), (9, 200)]
    for fast, slow in pairs:
        if emas.get(fast) is not None and emas.get(slow) is not None:
            if emas[fast] > emas[slow]:
                score += 1
    return score


def calc_stochastic(highs: list[float], lows: list[float], closes: list[float],
                    k_period: int = 14, d_period: int = 3) -> tuple[float | None, float | None]:
    """Stochastic %K and %D."""
    if len(closes) < k_period:
        return None, None
    k_values = []
    for i in range(k_period - 1, len(closes)):
        window_high = max(highs[i - k_period + 1: i + 1])
        window_low = min(lows[i - k_period + 1: i + 1])
        denom = window_high - window_low
        if denom == 0:
            k_values.append(50.0)
        else:
            k_values.append(((closes[i] - window_low) / denom) * 100.0)
    k_val = k_values[-1] if k_values else None
    d_val = None
    if len(k_values) >= d_period:
        d_val = sum(k_values[-d_period:]) / d_period
    return k_val, d_val


def calc_obv_trend(closes: list[float], volumes: list[float], lookback: int = 20) -> float:
    """OBV trend: +1 rising, -1 falling, 0 flat.
    Uses slope of OBV over last `lookback` bars."""
    if len(closes) < lookback + 1:
        return 0.0
    obv = [0.0]
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            obv.append(obv[-1] + volumes[i])
        elif closes[i] < closes[i - 1]:
            obv.append(obv[-1] - volumes[i])
        else:
            obv.append(obv[-1])
    recent = obv[-lookback:]
    # Simple linear regression slope sign
    n = len(recent)
    x_mean = (n - 1) / 2.0
    y_mean = sum(recent) / n
    numerator = sum((i - x_mean) * (recent[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return 0.0
    slope = numerator / denominator
    # Normalize to -1..+1 range based on magnitude relative to avg OBV
    if y_mean == 0:
        return 0.0
    normalized = slope * n / abs(y_mean) if y_mean != 0 else 0
    return max(-1.0, min(1.0, normalized))


def calc_adx(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> float | None:
    """Average Directional Index (ADX)."""
    if len(closes) < 2 * period + 1:
        return None
    plus_dm = []
    minus_dm = []
    tr_list = []
    for i in range(1, len(closes)):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm.append(up if (up > down and up > 0) else 0)
        minus_dm.append(down if (down > up and down > 0) else 0)
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        tr_list.append(tr)

    # Wilder smoothing
    def wilder_smooth(data, p):
        if len(data) < p:
            return []
        result = [sum(data[:p])]
        for val in data[p:]:
            result.append(result[-1] - result[-1] / p + val)
        return result

    sm_tr = wilder_smooth(tr_list, period)
    sm_plus = wilder_smooth(plus_dm, period)
    sm_minus = wilder_smooth(minus_dm, period)

    min_len = min(len(sm_tr), len(sm_plus), len(sm_minus))
    if min_len == 0:
        return None

    dx_list = []
    for i in range(min_len):
        if sm_tr[i] == 0:
            continue
        plus_di = (sm_plus[i] / sm_tr[i]) * 100
        minus_di = (sm_minus[i] / sm_tr[i]) * 100
        denom = plus_di + minus_di
        if denom == 0:
            dx_list.append(0)
        else:
            dx_list.append(abs(plus_di - minus_di) / denom * 100)

    if len(dx_list) < period:
        return sum(dx_list) / len(dx_list) if dx_list else None

    adx = sum(dx_list[:period]) / period
    for i in range(period, len(dx_list)):
        adx = (adx * (period - 1) + dx_list[i]) / period
    return adx


def calc_vwap_deviation(closes: list[float], volumes: list[float], highs: list[float], lows: list[float]) -> float | None:
    """VWAP deviation % — how far current price is from session VWAP."""
    if len(closes) < 2:
        return None
    typical_prices = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
    cum_tp_vol = 0.0
    cum_vol = 0.0
    for tp, v in zip(typical_prices, volumes):
        cum_tp_vol += tp * v
        cum_vol += v
    if cum_vol == 0:
        return None
    vwap = cum_tp_vol / cum_vol
    if vwap == 0:
        return None
    return ((closes[-1] - vwap) / vwap) * 100.0


def calc_consecutive_candles(opens: list[float], closes: list[float]) -> int:
    """Count consecutive green (+) or red (-) candles from the latest bar.
    Positive = green streak, negative = red streak."""
    if len(closes) < 2:
        return 0
    count = 0
    direction = None
    for i in range(len(closes) - 1, -1, -1):
        is_green = closes[i] >= opens[i]
        if direction is None:
            direction = is_green
            count = 1
        elif is_green == direction:
            count += 1
        else:
            break
    return count if direction else -count


def calc_dist_from_200sma(closes: list[float]) -> float | None:
    """Distance from 200-period SMA as percentage."""
    sma_values = calc_sma(closes, 200)
    if not sma_values:
        # Fall back to whatever SMA we can compute
        available = min(len(closes), 200)
        if available < 20:
            return None
        sma_values = calc_sma(closes, available)
        if not sma_values:
            return None
    sma_200 = sma_values[-1]
    if sma_200 == 0:
        return None
    return ((closes[-1] - sma_200) / sma_200) * 100.0


# =====================================================================
#  Compute all indicators for a set of klines
# =====================================================================

def compute_all_indicators(klines: list) -> dict:
    """Given raw Binance klines, compute all 14 indicators.
    Returns dict of indicator_name -> value (or None if incalculable).
    """
    opens = _to_float_array(klines, 1)
    highs = _to_float_array(klines, 2)
    lows = _to_float_array(klines, 3)
    closes = _to_float_array(klines, 4)
    volumes = _to_float_array(klines, 5)

    stoch_k, stoch_d = calc_stochastic(highs, lows, closes)

    return {
        "rsi_14": calc_rsi(closes, 14),
        "rsi_2": calc_rsi(closes, 2),
        "macd_histogram": calc_macd_histogram(closes),
        "bollinger_pct_b": calc_bollinger_pct_b(closes),
        "volume_ratio": calc_volume_ratio(volumes),
        "atr_pct": calc_atr_pct(highs, lows, closes),
        "ema_alignment": calc_ema_alignment(closes),
        "stoch_k": stoch_k,
        "stoch_d": stoch_d,
        "obv_trend": calc_obv_trend(closes, volumes),
        "adx": calc_adx(highs, lows, closes),
        "vwap_deviation_pct": calc_vwap_deviation(closes, volumes, highs, lows),
        "consecutive_candles": calc_consecutive_candles(opens, closes),
        "dist_from_200sma_pct": calc_dist_from_200sma(closes),
    }


# =====================================================================
#  Active picks loader
# =====================================================================

def load_active_picks() -> list[dict]:
    """Load active picks from alpha_engine's active_picks.json."""
    if not ACTIVE_PICKS_PATH.exists():
        print(f"[WARN] No active picks file at {ACTIVE_PICKS_PATH}")
        return []
    try:
        with open(ACTIVE_PICKS_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"[ERROR] Failed to load active picks: {e}")
        return []

    if isinstance(raw, dict):
        entries = raw.get("activePicks", raw.get("picks", []))
    elif isinstance(raw, list):
        entries = raw
    else:
        return []

    picks = []
    for p in entries:
        symbol = p.get("symbol", "")
        entry_price = p.get("entry_price") or p.get("entryPrice")
        if not symbol or entry_price is None:
            continue
        try:
            entry_price = float(entry_price)
        except (ValueError, TypeError):
            continue
        if entry_price <= 0:
            continue

        direction = (p.get("direction", "") or p.get("signal_type", "") or "LONG").upper()
        if direction in ("BUY", "LONG"):
            direction = "LONG"
        elif direction in ("SELL", "SHORT"):
            direction = "SHORT"
        else:
            direction = "LONG"

        category = (p.get("category", "") or "").lower()
        # Only process crypto picks (they have Binance kline data)
        if category and category not in ("crypto", "cryptocurrency", ""):
            continue

        # Ensure symbol ends with USDT for Binance
        binance_symbol = symbol.upper()
        if not binance_symbol.endswith(("USDT", "BUSD", "USD")):
            binance_symbol = binance_symbol + "USDT"

        picks.append({
            "id": p.get("id", f"{symbol}_{entry_price}"),
            "symbol": symbol,
            "binance_symbol": binance_symbol,
            "direction": direction,
            "entry_price": entry_price,
            "strategy": p.get("strategy", "unknown"),
            "confidence": p.get("confidence") or p.get("ml_score"),
            "entry_date": p.get("entry_date") or p.get("open_time", ""),
        })

    return picks


# =====================================================================
#  Correlation log management
# =====================================================================

def load_correlation_log() -> list[dict]:
    """Load existing correlation log, return empty list if missing."""
    if not CORRELATION_LOG_PATH.exists():
        return []
    try:
        with open(CORRELATION_LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_correlation_log(log: list[dict]):
    """Save correlation log, pruning entries older than LOG_RETENTION_DAYS."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOG_RETENTION_DAYS)
    cutoff_str = cutoff.isoformat()
    pruned = [entry for entry in log if entry.get("timestamp", "") >= cutoff_str]
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CORRELATION_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(pruned, f, indent=2, default=str)
    return pruned


# =====================================================================
#  Spearman rank correlation (pure Python, no scipy)
# =====================================================================

def _rank(values: list[float]) -> list[float]:
    """Assign ranks to values (handles ties with average rank)."""
    n = len(values)
    indexed = sorted(enumerate(values), key=lambda x: x[1])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n - 1 and indexed[j + 1][1] == indexed[j][1]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1  # 1-based
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg_rank
        i = j + 1
    return ranks


def spearman_correlation(x: list[float], y: list[float]) -> float | None:
    """Compute Spearman rank correlation between two lists."""
    if len(x) != len(y) or len(x) < 3:
        return None
    rx = _rank(x)
    ry = _rank(y)
    n = len(x)
    mean_rx = sum(rx) / n
    mean_ry = sum(ry) / n
    cov = sum((rx[i] - mean_rx) * (ry[i] - mean_ry) for i in range(n))
    std_x = math.sqrt(sum((rx[i] - mean_rx) ** 2 for i in range(n)))
    std_y = math.sqrt(sum((ry[i] - mean_ry) ** 2 for i in range(n)))
    if std_x == 0 or std_y == 0:
        return 0.0
    return cov / (std_x * std_y)


# =====================================================================
#  Correlation analysis
# =====================================================================

def analyze_correlations(log: list[dict]) -> dict:
    """Analyze indicator-PnL correlations from the log.
    Returns per-indicator stats and recommendations.
    """
    if len(log) < 5:
        return {"error": "Insufficient data", "sample_count": len(log),
                "indicators": {}, "recommendations": [], "best_combinations": []}

    results = {}

    for ind_name in INDICATOR_NAMES:
        # Gather (indicator_value, pnl) pairs where both exist
        pairs = []
        for entry in log:
            ind_val = entry.get("indicators", {}).get(ind_name)
            pnl = entry.get("pnl_pct")
            if ind_val is not None and pnl is not None:
                try:
                    pairs.append((float(ind_val), float(pnl)))
                except (ValueError, TypeError):
                    continue

        if len(pairs) < 5:
            results[ind_name] = {
                "correlation": None,
                "above_median_pnl": None,
                "below_median_pnl": None,
                "sample_count": len(pairs),
                "signal_strength": "INSUFFICIENT_DATA",
            }
            continue

        ind_values = [p[0] for p in pairs]
        pnl_values = [p[1] for p in pairs]

        # Spearman correlation
        corr = spearman_correlation(ind_values, pnl_values)

        # Median split analysis
        sorted_ind = sorted(ind_values)
        median_val = sorted_ind[len(sorted_ind) // 2]

        above_pnl = [p[1] for p in pairs if p[0] >= median_val]
        below_pnl = [p[1] for p in pairs if p[0] < median_val]

        avg_above = sum(above_pnl) / len(above_pnl) if above_pnl else 0.0
        avg_below = sum(below_pnl) / len(below_pnl) if below_pnl else 0.0

        # Classify signal strength
        abs_corr = abs(corr) if corr is not None else 0
        if abs_corr >= 0.3:
            signal = "STRONG"
        elif abs_corr >= 0.15:
            signal = "MODERATE"
        elif abs_corr >= 0.05:
            signal = "WEAK"
        else:
            signal = "NONE"

        if corr is not None and corr < 0:
            signal += " (inverse)"

        results[ind_name] = {
            "correlation": round(corr, 4) if corr is not None else None,
            "above_median_pnl": round(avg_above, 4),
            "below_median_pnl": round(avg_below, 4),
            "median_value": round(median_val, 4),
            "sample_count": len(pairs),
            "signal_strength": signal,
        }

    # Best indicator combinations (top 3 pairs)
    best_combinations = _find_best_combinations(log, results)

    # Generate recommendations
    recommendations = _generate_recommendations(results)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_observations": len(log),
        "indicators": results,
        "best_combinations": best_combinations,
        "recommendations": recommendations,
    }


def _find_best_combinations(log: list[dict], indicator_stats: dict) -> list[dict]:
    """Find the top 3 indicator pairs that together best predict PnL."""
    if len(log) < 10:
        return []

    # Only consider indicators with enough data
    valid_indicators = [
        name for name, stats in indicator_stats.items()
        if stats.get("sample_count", 0) >= 5 and stats.get("correlation") is not None
    ]

    if len(valid_indicators) < 2:
        return []

    combo_scores = []
    for i in range(len(valid_indicators)):
        for j in range(i + 1, len(valid_indicators)):
            ind_a = valid_indicators[i]
            ind_b = valid_indicators[j]

            # Get entries where both indicators have values
            quadrant_pnl = {"HH": [], "HL": [], "LH": [], "LL": []}
            vals_a = []
            vals_b = []
            pnls = []

            for entry in log:
                va = entry.get("indicators", {}).get(ind_a)
                vb = entry.get("indicators", {}).get(ind_b)
                pnl = entry.get("pnl_pct")
                if va is not None and vb is not None and pnl is not None:
                    vals_a.append(float(va))
                    vals_b.append(float(vb))
                    pnls.append(float(pnl))

            if len(pnls) < 10:
                continue

            med_a = sorted(vals_a)[len(vals_a) // 2]
            med_b = sorted(vals_b)[len(vals_b) // 2]

            for va, vb, pnl in zip(vals_a, vals_b, pnls):
                key = ("H" if va >= med_a else "L") + ("H" if vb >= med_b else "L")
                quadrant_pnl[key].append(pnl)

            # Score = spread between best and worst quadrant
            quad_avgs = {}
            for q, values in quadrant_pnl.items():
                if values:
                    quad_avgs[q] = sum(values) / len(values)

            if len(quad_avgs) < 2:
                continue

            best_q = max(quad_avgs.values())
            worst_q = min(quad_avgs.values())
            spread = best_q - worst_q

            combo_scores.append({
                "indicators": [ind_a, ind_b],
                "spread": round(spread, 4),
                "best_quadrant": max(quad_avgs, key=quad_avgs.get),
                "best_quadrant_avg_pnl": round(best_q, 4),
                "worst_quadrant": min(quad_avgs, key=quad_avgs.get),
                "worst_quadrant_avg_pnl": round(worst_q, 4),
                "sample_count": len(pnls),
            })

    combo_scores.sort(key=lambda x: x["spread"], reverse=True)
    return combo_scores[:3]


def _generate_recommendations(indicator_stats: dict) -> list[dict]:
    """Generate actionable filter recommendations based on indicator analysis."""
    recs = []

    for name, stats in indicator_stats.items():
        corr = stats.get("correlation")
        above_pnl = stats.get("above_median_pnl")
        below_pnl = stats.get("below_median_pnl")
        median = stats.get("median_value")
        sample = stats.get("sample_count", 0)

        if corr is None or sample < 10 or median is None:
            continue

        abs_corr = abs(corr)
        if abs_corr < 0.1:
            continue

        # Determine direction of recommendation
        if above_pnl is not None and below_pnl is not None:
            if above_pnl > below_pnl and corr > 0:
                action = "boost"
                condition = f"{name} >= {round(median, 2)}"
                rationale = f"Picks with {name} above median ({round(median, 2)}) average {round(above_pnl, 2)}% PnL vs {round(below_pnl, 2)}% below"
            elif below_pnl > above_pnl and corr < 0:
                action = "block"
                condition = f"{name} >= {round(median, 2)}"
                rationale = f"Picks with {name} above median ({round(median, 2)}) average {round(above_pnl, 2)}% PnL vs {round(below_pnl, 2)}% below"
            else:
                continue

            confidence = "high" if abs_corr >= 0.3 else "medium" if abs_corr >= 0.15 else "low"

            recs.append({
                "indicator": name,
                "action": action,
                "condition": condition,
                "threshold": round(median, 4),
                "correlation": round(corr, 4),
                "confidence": confidence,
                "rationale": rationale,
                "sample_count": sample,
            })

    # Sort by absolute correlation
    recs.sort(key=lambda r: abs(r["correlation"]), reverse=True)
    return recs


# =====================================================================
#  Public API: get recommendations for use by other modules
# =====================================================================

def get_indicator_filter_recommendations() -> list[dict]:
    """Return recommended indicator thresholds based on historical correlations.
    Can be imported by quality gate modules.
    Returns list of dicts: {indicator, action, condition, threshold, correlation, confidence}
    """
    if not PREDICTIVE_POWER_PATH.exists():
        return []
    try:
        with open(PREDICTIVE_POWER_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return []
    return data.get("recommendations", [])


# =====================================================================
#  Main runner
# =====================================================================

def run():
    """Main execution: fetch data, compute indicators, analyze correlations."""
    print("=" * 72)
    print("  INDICATOR CORRELATION TRACKER")
    print("  Discovering which technicals predict profitable picks")
    print("=" * 72)

    # 1. Load active picks
    picks = load_active_picks()
    print(f"\n[1/5] Loaded {len(picks)} active crypto picks")

    if not picks:
        print("[DONE] No picks to analyze.")
        return

    # 2. Fetch klines and compute indicators for each pick
    now_ts = datetime.now(timezone.utc).isoformat()
    new_entries = []
    success = 0
    fail = 0

    print(f"[2/5] Fetching klines and computing 14 indicators per pick...")

    for i, pick in enumerate(picks):
        symbol = pick["binance_symbol"]
        sys.stdout.write(f"  [{i+1}/{len(picks)}] {symbol}...")
        sys.stdout.flush()

        # Fetch klines
        klines = fetch_klines_binance(symbol, interval="1h", limit=200)
        if not klines or len(klines) < 20:
            print(f" SKIP (no kline data)")
            fail += 1
            continue

        # Get current price from last kline close
        current_price = float(klines[-1][4])
        if current_price <= 0:
            print(f" SKIP (zero price)")
            fail += 1
            continue

        # Compute PnL
        entry_price = pick["entry_price"]
        if pick["direction"] == "LONG":
            pnl_pct = ((current_price - entry_price) / entry_price) * 100.0
        else:
            pnl_pct = ((entry_price - current_price) / entry_price) * 100.0

        # Compute all indicators
        indicators = compute_all_indicators(klines)

        entry = {
            "timestamp": now_ts,
            "pick_id": pick["id"],
            "symbol": pick["symbol"],
            "binance_symbol": symbol,
            "direction": pick["direction"],
            "strategy": pick["strategy"],
            "entry_price": entry_price,
            "current_price": round(current_price, 6),
            "pnl_pct": round(pnl_pct, 4),
            "indicators": {k: round(v, 6) if v is not None else None for k, v in indicators.items()},
        }
        new_entries.append(entry)
        success += 1

        pnl_str = f"+{pnl_pct:.2f}%" if pnl_pct >= 0 else f"{pnl_pct:.2f}%"
        print(f" OK  price={current_price:.4f}  PnL={pnl_str}  EMA={indicators.get('ema_alignment', '?')}")

    print(f"\n  Fetched: {success} success, {fail} failed/skipped")

    # 3. Append to correlation log
    print(f"[3/5] Updating correlation log...")
    log = load_correlation_log()
    log.extend(new_entries)
    log = save_correlation_log(log)
    print(f"  Log now has {len(log)} observations (last {LOG_RETENTION_DAYS} days)")

    # 4. Compute correlations
    print(f"[4/5] Computing indicator-PnL correlations...")
    analysis = analyze_correlations(log)

    # 5. Save results
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PREDICTIVE_POWER_PATH, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, default=str)
    print(f"  Saved analysis to {PREDICTIVE_POWER_PATH}")

    # Print ranked table
    _print_ranked_table(analysis)

    # Print recommendations
    _print_recommendations(analysis)

    print(f"\n{'=' * 72}")
    print(f"  DONE. Files written:")
    print(f"    {CORRELATION_LOG_PATH}")
    print(f"    {PREDICTIVE_POWER_PATH}")
    print(f"{'=' * 72}")


def _print_ranked_table(analysis: dict):
    """Print the ranked indicator table."""
    indicators = analysis.get("indicators", {})
    if not indicators:
        print("\n  [No indicator data to rank]")
        return

    # Sort by absolute correlation
    ranked = sorted(
        indicators.items(),
        key=lambda x: abs(x[1].get("correlation") or 0),
        reverse=True,
    )

    print(f"\n{'=' * 90}")
    print(f"  INDICATOR PREDICTIVE POWER RANKING  ({analysis.get('total_observations', 0)} observations)")
    print(f"{'=' * 90}")
    header = f"{'Rank':<6}{'Indicator':<24}{'Corr':>8}{'Above-Med PnL':>16}{'Below-Med PnL':>16}{'Signal':>18}"
    print(header)
    print("-" * 90)

    for rank, (name, stats) in enumerate(ranked, 1):
        corr = stats.get("correlation")
        above = stats.get("above_median_pnl")
        below = stats.get("below_median_pnl")
        signal = stats.get("signal_strength", "N/A")

        corr_str = f"{corr:+.3f}" if corr is not None else "N/A"
        above_str = f"{above:+.2f}%" if above is not None else "N/A"
        below_str = f"{below:+.2f}%" if below is not None else "N/A"

        print(f"{rank:<6}{name:<24}{corr_str:>8}{above_str:>16}{below_str:>16}{signal:>18}")

    print("-" * 90)

    # Print best combinations
    combos = analysis.get("best_combinations", [])
    if combos:
        print(f"\n  TOP INDICATOR COMBINATIONS:")
        for i, combo in enumerate(combos, 1):
            inds = " + ".join(combo["indicators"])
            print(f"    {i}. {inds}")
            print(f"       Spread: {combo['spread']:.2f}%  |  "
                  f"Best: {combo['best_quadrant']}={combo['best_quadrant_avg_pnl']:+.2f}%  |  "
                  f"Worst: {combo['worst_quadrant']}={combo['worst_quadrant_avg_pnl']:+.2f}%  "
                  f"(n={combo['sample_count']})")


def _print_recommendations(analysis: dict):
    """Print actionable recommendations."""
    recs = analysis.get("recommendations", [])
    if not recs:
        print("\n  [Insufficient data for recommendations — need more observations]")
        return

    print(f"\n  RECOMMENDED FILTERS (data-driven):")
    print(f"  {'=' * 70}")
    for r in recs:
        icon = "BOOST" if r["action"] == "boost" else "BLOCK"
        print(f"    [{icon}] {r['condition']}  (corr={r['correlation']:+.3f}, "
              f"conf={r['confidence']}, n={r['sample_count']})")
        print(f"           {r['rationale']}")


# =====================================================================
if __name__ == "__main__":
    run()
