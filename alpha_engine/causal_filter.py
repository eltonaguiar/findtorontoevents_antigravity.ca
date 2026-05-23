#!/usr/bin/env python3
"""
ALPHA_ENGINE -- Causal Inference Filter
==========================================
Granger causality tests, BTC lead-lag signals, and spurious correlation filter.

1. Granger Causality: tests if BTC returns Granger-cause alt returns at lag 1-4h
2. Lead-Lag Signal: BTC return over significant lag -> confidence boost/penalty
3. Spurious Correlation Filter: partial correlation controlling for BTC return

Pure Python implementation (no statsmodels). Uses Binance klines with 4-mirror
failover per project rules. Cached for 5 minutes.

Usage:
    from causal_filter import get_btc_lead_signal, run_granger_tests, run_spurious_filter
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_ENGINE_DIR = Path(__file__).resolve().parent
_DATA_DIR = _ENGINE_DIR / "data"

# ---------------------------------------------------------------------------
# Binance kline fetcher with 4-mirror failover + CoinGecko fallback
# ---------------------------------------------------------------------------
_SPOT_BASES = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
    "https://api.binance.us",
]

# In CI, prefer non-geo-blocked endpoints first
if os.environ.get("GITHUB_ACTIONS"):
    _preferred = ["https://data-api.binance.vision", "https://api.binance.us"]
    _SPOT_BASES = _preferred + [u for u in _SPOT_BASES if u not in _preferred]

_COINGECKO_BASE = "https://api.coingecko.com/api/v3"
_KUCOIN_BASE = "https://api.kucoin.com"
_CRYPTOCOMPARE_BASE = "https://min-api.cryptocompare.com/data"

HTTP_TIMEOUT = 10

# ---------------------------------------------------------------------------
# In-memory kline cache (symbol -> (timestamp, klines))
# ---------------------------------------------------------------------------
_kline_cache: dict[str, tuple[float, list[list]]] = {}
_CACHE_TTL = 300  # 5 minutes


def _fetch_json(url: str, timeout: int = HTTP_TIMEOUT) -> Optional[list | dict]:
    """Fetch JSON from a URL, return None on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def fetch_klines(symbol: str = "BTCUSDT", interval: str = "1h",
                 limit: int = 100) -> list[list]:
    """Fetch klines with Binance 4-mirror failover + CoinGecko + KuCoin + CryptoCompare.

    Returns list of [open_time, open, high, low, close, volume, ...] arrays.
    Each price field is a float. Returns empty list on total failure.
    """
    cache_key = f"{symbol}_{interval}_{limit}"
    now = time.time()
    if cache_key in _kline_cache:
        cached_time, cached_data = _kline_cache[cache_key]
        if now - cached_time < _CACHE_TTL:
            return cached_data

    path = f"/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"

    # Try Binance mirrors (4+ mirrors)
    for base in _SPOT_BASES:
        data = _fetch_json(f"{base}{path}")
        if data and isinstance(data, list) and len(data) > 0:
            klines = _normalize_binance_klines(data)
            _kline_cache[cache_key] = (now, klines)
            return klines

    # Fallback 1: CoinGecko (OHLC endpoint, limited granularity)
    cg_klines = _coingecko_fallback(symbol, limit)
    if cg_klines:
        _kline_cache[cache_key] = (now, cg_klines)
        return cg_klines

    # Fallback 2: KuCoin
    kucoin_klines = _kucoin_fallback(symbol, interval, limit)
    if kucoin_klines:
        _kline_cache[cache_key] = (now, kucoin_klines)
        return kucoin_klines

    # Fallback 3: CryptoCompare
    cc_klines = _cryptocompare_fallback(symbol, limit)
    if cc_klines:
        _kline_cache[cache_key] = (now, cc_klines)
        return cc_klines

    return []


def _normalize_binance_klines(data: list) -> list[list]:
    """Convert Binance kline strings to floats."""
    result = []
    for k in data:
        try:
            result.append([
                int(k[0]),       # open_time
                float(k[1]),     # open
                float(k[2]),     # high
                float(k[3]),     # low
                float(k[4]),     # close
                float(k[5]),     # volume
            ])
        except (IndexError, ValueError, TypeError):
            continue
    return result


def _coingecko_fallback(symbol: str, limit: int) -> list[list]:
    """CoinGecko OHLC fallback (hourly for 1-2 day range)."""
    # Map BTCUSDT -> bitcoin, ETHUSDT -> ethereum, etc.
    _cg_map = {
        "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana",
        "BNBUSDT": "binancecoin", "XRPUSDT": "ripple", "ADAUSDT": "cardano",
        "AVAXUSDT": "avalanche-2", "LINKUSDT": "chainlink", "NEARUSDT": "near",
        "DOGEUSDT": "dogecoin", "DOTUSDT": "polkadot", "SUIUSDT": "sui",
    }
    cg_id = _cg_map.get(symbol)
    if not cg_id:
        return []
    # days=2 gives hourly candles from CoinGecko
    days = max(2, limit // 24 + 1)
    url = f"{_COINGECKO_BASE}/coins/{cg_id}/ohlc?vs_currency=usd&days={days}"
    data = _fetch_json(url)
    if not data or not isinstance(data, list):
        return []
    result = []
    for candle in data[-limit:]:
        try:
            result.append([
                int(candle[0]),
                float(candle[1]),  # open
                float(candle[2]),  # high
                float(candle[3]),  # low
                float(candle[4]),  # close
                0.0,               # volume not available from CG OHLC
            ])
        except (IndexError, ValueError, TypeError):
            continue
    return result


def _kucoin_fallback(symbol: str, interval: str, limit: int) -> list[list]:
    """KuCoin klines fallback."""
    # Map BTCUSDT -> BTC-USDT
    if symbol.endswith("USDT"):
        kc_symbol = symbol[:-4] + "-USDT"
    else:
        return []
    # KuCoin interval: 1hour
    kc_interval = "1hour" if interval == "1h" else interval
    end_at = int(time.time())
    start_at = end_at - limit * 3600
    url = (f"{_KUCOIN_BASE}/api/v1/market/candles"
           f"?type={kc_interval}&symbol={kc_symbol}&startAt={start_at}&endAt={end_at}")
    data = _fetch_json(url)
    if not data or not isinstance(data, dict):
        return []
    candles = data.get("data", [])
    if not candles:
        return []
    result = []
    for c in candles:
        try:
            result.append([
                int(c[0]) * 1000,  # timestamp to ms
                float(c[1]),       # open
                float(c[3]),       # high
                float(c[4]),       # low
                float(c[2]),       # close
                float(c[5]),       # volume
            ])
        except (IndexError, ValueError, TypeError):
            continue
    result.sort(key=lambda x: x[0])
    return result[-limit:]


def _cryptocompare_fallback(symbol: str, limit: int) -> list[list]:
    """CryptoCompare histohour fallback."""
    if symbol.endswith("USDT"):
        fsym = symbol[:-4]
    else:
        return []
    url = f"{_CRYPTOCOMPARE_BASE}/v2/histohour?fsym={fsym}&tsym=USD&limit={limit}"
    data = _fetch_json(url)
    if not data or not isinstance(data, dict):
        return []
    entries = (data.get("Data") or {}).get("Data", [])
    if not entries:
        return []
    result = []
    for e in entries:
        try:
            result.append([
                int(e["time"]) * 1000,
                float(e["open"]),
                float(e["high"]),
                float(e["low"]),
                float(e["close"]),
                float(e.get("volumefrom", 0)),
            ])
        except (KeyError, ValueError, TypeError):
            continue
    return result[-limit:]


# ---------------------------------------------------------------------------
# Helper: compute log returns from kline close prices
# ---------------------------------------------------------------------------
def _compute_returns(klines: list[list]) -> list[float]:
    """Compute log returns from close prices (index 4)."""
    returns = []
    for i in range(1, len(klines)):
        prev_close = klines[i - 1][4]
        curr_close = klines[i][4]
        if prev_close > 0 and curr_close > 0:
            returns.append(math.log(curr_close / prev_close))
        else:
            returns.append(0.0)
    return returns


# ---------------------------------------------------------------------------
# Pure Python OLS via normal equations
# ---------------------------------------------------------------------------
def _ols_rss(y: list[float], X: list[list[float]]) -> float:
    """Fit OLS via normal equations (X'X)^{-1} X'y and return RSS.

    X is a list of rows (each row is a list of feature values).
    Uses Gaussian elimination for matrix inversion (pure Python).
    Returns float('inf') on singular matrix.
    """
    n = len(y)
    if n == 0:
        return float('inf')
    k = len(X[0]) if X else 0
    if k == 0 or n <= k:
        return float('inf')

    # Compute X'X (k x k)
    XtX = [[0.0] * k for _ in range(k)]
    for i in range(k):
        for j in range(k):
            s = 0.0
            for t in range(n):
                s += X[t][i] * X[t][j]
            XtX[i][j] = s

    # Compute X'y (k x 1)
    Xty = [0.0] * k
    for i in range(k):
        s = 0.0
        for t in range(n):
            s += X[t][i] * y[t]
        Xty[i] = s

    # Solve XtX * beta = Xty via Gaussian elimination with partial pivoting
    aug = [XtX[i][:] + [Xty[i]] for i in range(k)]

    for col in range(k):
        # Partial pivot
        max_row = col
        max_val = abs(aug[col][col])
        for row in range(col + 1, k):
            if abs(aug[row][col]) > max_val:
                max_val = abs(aug[row][col])
                max_row = row
        if max_val < 1e-15:
            return float('inf')  # Singular
        aug[col], aug[max_row] = aug[max_row], aug[col]

        pivot = aug[col][col]
        for j in range(col, k + 1):
            aug[col][j] /= pivot
        for row in range(k):
            if row == col:
                continue
            factor = aug[row][col]
            for j in range(col, k + 1):
                aug[row][j] -= factor * aug[col][j]

    beta = [aug[i][k] for i in range(k)]

    # Compute RSS = sum((y_i - X_i @ beta)^2)
    rss = 0.0
    for t in range(n):
        pred = sum(X[t][j] * beta[j] for j in range(k))
        rss += (y[t] - pred) ** 2

    return rss


# ---------------------------------------------------------------------------
# F-distribution p-value approximation (Abramowitz & Stegun)
# ---------------------------------------------------------------------------
def _f_pvalue(f_stat: float, df1: int, df2: int) -> float:
    """Approximate upper-tail p-value of F-distribution.

    Uses the beta incomplete function approximation.
    For large df2, uses the chi-squared approximation: df1*F ~ chi2(df1).
    """
    if f_stat <= 0 or df1 <= 0 or df2 <= 0:
        return 1.0

    # Use beta incomplete function: P(F > f) = I_x(df2/2, df1/2)
    # where x = df2 / (df2 + df1 * f)
    x = df2 / (df2 + df1 * f_stat)
    a = df2 / 2.0
    b = df1 / 2.0

    # Regularized incomplete beta function via continued fraction (Lentz's method)
    return _beta_inc(a, b, x)


def _beta_inc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function I_x(a, b) via continued fraction."""
    if x < 0 or x > 1:
        return 0.0
    if x == 0:
        return 0.0
    if x == 1:
        return 1.0

    # Use symmetry relation for numerical stability
    if x > (a + 1) / (a + b + 2):
        return 1.0 - _beta_inc(b, a, 1.0 - x)

    # Log beta function via Stirling
    lbeta = _log_beta(a, b)

    # Front factor
    front = math.exp(a * math.log(x) + b * math.log(1 - x) - lbeta) / a

    # Continued fraction (Lentz's method)
    cf = _beta_cf(a, b, x)
    return front * cf


def _log_beta(a: float, b: float) -> float:
    """Log of Beta function: log(B(a,b)) = lgamma(a) + lgamma(b) - lgamma(a+b)."""
    return math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)


def _beta_cf(a: float, b: float, x: float, max_iter: int = 200) -> float:
    """Continued fraction for incomplete beta function."""
    tiny = 1e-30
    f = 1.0
    c = 1.0
    d = 1.0 - (a + b) * x / (a + 1)
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    f = d

    for m in range(1, max_iter + 1):
        # Even step
        m2 = 2 * m
        num = m * (b - m) * x / ((a + m2 - 1) * (a + m2))
        d = 1.0 + num * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + num / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        f *= c * d

        # Odd step
        num = -(a + m) * (a + b + m) * x / ((a + m2) * (a + m2 + 1))
        d = 1.0 + num * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + num / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = c * d
        f *= delta

        if abs(delta - 1.0) < 1e-10:
            break

    return f


# ---------------------------------------------------------------------------
# 1. Granger Causality Tests
# ---------------------------------------------------------------------------
# Default alt symbols to test against BTC
_DEFAULT_ALTS = [
    "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
    "AVAXUSDT", "LINKUSDT", "NEARUSDT", "DOGEUSDT", "SUIUSDT",
    "INJUSDT", "APTUSDT", "FILUSDT", "ATOMUSDT", "TIAUSDT",
    "SEIUSDT", "WLDUSDT", "GALAUSDT", "PENDLEUSDT", "TRXUSDT",
    "TONUSDT", "RENDERUSDT", "ETCUSDT", "LTCUSDT", "TAOUSDT",
    "HYPEUSDT", "NOTUSDT", "TURBOUSDT",
]


def run_granger_tests(
    max_lag: int = 4,
    n_hours: int = 100,
    p_threshold: float = 0.05,
    alt_symbols: Optional[list[str]] = None,
) -> dict:
    """Run Granger causality tests: BTC returns -> alt returns at lags 1-4h.

    For each alt, fits:
      Restricted:   alt_ret_t = c + sum(a_i * alt_ret_{t-i})
      Unrestricted: alt_ret_t = c + sum(a_i * alt_ret_{t-i}) + sum(b_j * btc_ret_{t-j})

    F-test: ((RSS_r - RSS_u) / max_lag) / (RSS_u / (n - 2*max_lag - 1))

    Returns dict with per-pair results and saves to data/granger_causality.json.
    """
    if alt_symbols is None:
        alt_symbols = list(_DEFAULT_ALTS)

    # Fetch BTC klines
    btc_klines = fetch_klines("BTCUSDT", "1h", n_hours)
    if len(btc_klines) < max_lag + 10:
        print("[CAUSAL] Insufficient BTC kline data, skipping Granger tests")
        return {}

    btc_returns = _compute_returns(btc_klines)

    results = {}
    significant_count = 0

    for alt_sym in alt_symbols:
        try:
            alt_klines = fetch_klines(alt_sym, "1h", n_hours)
            if len(alt_klines) < max_lag + 10:
                continue

            alt_returns = _compute_returns(alt_klines)

            # Align lengths
            min_len = min(len(btc_returns), len(alt_returns))
            btc_ret = btc_returns[-min_len:]
            alt_ret = alt_returns[-min_len:]

            best_result = _granger_test_pair(alt_ret, btc_ret, max_lag, p_threshold)
            if best_result:
                results[alt_sym] = best_result
                if best_result["p_value"] < p_threshold:
                    significant_count += 1

        except Exception as e:
            print(f"  [CAUSAL] {alt_sym} Granger test failed: {e}")
            continue

    # Save results
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "btc_reference": "BTCUSDT",
        "max_lag": max_lag,
        "n_hours": n_hours,
        "p_threshold": p_threshold,
        "significant_pairs": significant_count,
        "total_tested": len(alt_symbols),
        "pairs": results,
    }

    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        out_path = _DATA_DIR / "granger_causality.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
        print(f"[CAUSAL] Granger tests: {significant_count}/{len(alt_symbols)} "
              f"significant pairs (p<{p_threshold}) -> {out_path.name}")
    except Exception as e:
        print(f"[CAUSAL] Failed to save granger_causality.json: {e}")

    return output


def _granger_test_pair(
    alt_ret: list[float],
    btc_ret: list[float],
    max_lag: int,
    p_threshold: float,
) -> Optional[dict]:
    """Run Granger test for a single BTC->alt pair at lags 1..max_lag.

    Returns result dict for the best (lowest p-value) significant lag,
    or the best lag overall if none are significant.
    """
    n = len(alt_ret)
    if n <= 2 * max_lag + 1:
        return None

    best = None

    for lag in range(1, max_lag + 1):
        # Build data matrices starting from index=lag
        y = []
        X_restricted = []
        X_unrestricted = []

        for t in range(lag, n):
            y.append(alt_ret[t])

            # Restricted: intercept + alt own lags
            row_r = [1.0]  # intercept
            for i in range(1, lag + 1):
                row_r.append(alt_ret[t - i])
            X_restricted.append(row_r)

            # Unrestricted: intercept + alt own lags + btc lags
            row_u = list(row_r)  # copy restricted
            for i in range(1, lag + 1):
                if t - i >= 0:
                    row_u.append(btc_ret[t - i])
                else:
                    row_u.append(0.0)
            X_unrestricted.append(row_u)

        n_obs = len(y)
        k_r = len(X_restricted[0]) if X_restricted else 0
        k_u = len(X_unrestricted[0]) if X_unrestricted else 0
        df1 = k_u - k_r  # = lag (number of BTC lag terms added)
        df2 = n_obs - k_u

        if df1 <= 0 or df2 <= 2:
            continue

        rss_r = _ols_rss(y, X_restricted)
        rss_u = _ols_rss(y, X_unrestricted)

        if rss_u <= 0 or math.isinf(rss_r) or math.isinf(rss_u):
            continue

        # F-statistic
        if rss_u < 1e-30:
            f_stat = 0.0
        else:
            f_stat = ((rss_r - rss_u) / df1) / (rss_u / df2)

        if f_stat < 0:
            f_stat = 0.0

        p_val = _f_pvalue(f_stat, df1, df2)

        result = {
            "lag": lag,
            "f_stat": round(f_stat, 4),
            "p_value": round(p_val, 6),
            "significant": p_val < p_threshold,
            "n_obs": n_obs,
            "df1": df1,
            "df2": df2,
        }

        if best is None or p_val < best["p_value"]:
            best = result

    return best


# ---------------------------------------------------------------------------
# 2. BTC Lead-Lag Signal
# ---------------------------------------------------------------------------
# Cache for granger results (loaded once per session)
_granger_cache: Optional[dict] = None
_granger_cache_time: float = 0.0


def _load_granger_results() -> dict:
    """Load granger_causality.json with 5-min in-memory cache."""
    global _granger_cache, _granger_cache_time
    now = time.time()
    if _granger_cache and (now - _granger_cache_time) < _CACHE_TTL:
        return _granger_cache

    path = _DATA_DIR / "granger_causality.json"
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                _granger_cache = json.load(f)
            _granger_cache_time = now
        except Exception:
            _granger_cache = {}
    else:
        _granger_cache = {}

    return _granger_cache


def get_btc_lead_signal(symbol: str) -> dict:
    """Get BTC lead-lag signal for a symbol.

    Returns dict with:
      - btc_lead_signal: float (BTC return over significant lag period)
      - btc_lead_lag: int (significant lag in hours)
      - btc_lead_boost: int (+3 if BTC up & BUY aligned, -5 if BTC down & BUY)
      - btc_granger_significant: bool
    If no significant Granger relationship exists, returns neutral dict.
    """
    # Normalize symbol to Binance format
    binance_sym = _normalize_to_binance(symbol)

    granger = _load_granger_results()
    pairs = granger.get("pairs", {})
    pair_data = pairs.get(binance_sym, {})

    result = {
        "btc_lead_signal": 0.0,
        "btc_lead_lag": 0,
        "btc_lead_boost": 0,
        "btc_granger_significant": False,
    }

    if not pair_data or not pair_data.get("significant"):
        return result

    lag = pair_data.get("lag", 1)
    result["btc_lead_lag"] = lag
    result["btc_granger_significant"] = True

    # Fetch BTC klines to compute return over the lag period
    btc_klines = fetch_klines("BTCUSDT", "1h", lag + 2)
    if len(btc_klines) >= lag + 1:
        # BTC return over last N hours (where N = significant lag)
        recent_close = btc_klines[-1][4]
        lagged_close = btc_klines[-(lag + 1)][4]
        if lagged_close > 0:
            btc_return = (recent_close - lagged_close) / lagged_close
            result["btc_lead_signal"] = round(btc_return, 6)

            # Boost/penalty logic
            if btc_return > 0.001:  # BTC up > 0.1%
                result["btc_lead_boost"] = 3   # +3 confidence boost for BUY alts
            elif btc_return < -0.001:  # BTC down > 0.1%
                result["btc_lead_boost"] = -5  # -5 penalty for BUY alts
            # else: neutral, no adjustment

    return result


def _normalize_to_binance(symbol: str) -> str:
    """Normalize various symbol formats to Binance perpetual format.

    BTC-USD -> BTCUSDT, BTCUSD -> BTCUSDT, btcusdt -> BTCUSDT
    """
    s = symbol.upper().strip()
    # Handle yfinance format: BTC-USD -> BTCUSDT
    if "-USD" in s:
        s = s.replace("-USD", "USDT")
    # Handle BTCUSD without T
    if s.endswith("USD") and not s.endswith("USDT"):
        s = s + "T"
    return s


def apply_btc_lead_to_pick(pick: dict) -> dict:
    """Enrich a single pick with BTC lead-lag signal.

    Adds btc_lead_signal, btc_lead_lag, btc_lead_boost to pick's extra dict.
    Adjusts btc_lead_boost based on pick direction:
      - BUY + BTC up: +3
      - BUY + BTC down: -5
      - SELL/SHORT + BTC down: +3 (inverse)
      - SELL/SHORT + BTC up: -5 (inverse)
    """
    symbol = pick.get("symbol", "")
    cat = (pick.get("category") or "crypto").lower()

    # Only apply to crypto picks (BTC lead-lag is crypto-specific)
    if cat not in ("crypto", "meme"):
        return pick

    # Skip BTC itself
    binance_sym = _normalize_to_binance(symbol)
    if binance_sym in ("BTCUSDT", "BTCUSD"):
        return pick

    lead_data = get_btc_lead_signal(symbol)

    direction = (pick.get("direction") or pick.get("signal_type") or "BUY").upper()

    # Invert boost for SHORT/SELL direction
    if direction in ("SHORT", "SELL"):
        lead_data["btc_lead_boost"] = -lead_data["btc_lead_boost"]

    # Store in pick's extra dict
    extra = pick.get("extra", {}) or {}
    extra["btc_lead_signal"] = lead_data["btc_lead_signal"]
    extra["btc_lead_lag"] = lead_data["btc_lead_lag"]
    extra["btc_lead_boost"] = lead_data["btc_lead_boost"]
    extra["btc_granger_significant"] = lead_data["btc_granger_significant"]
    pick["extra"] = extra

    return pick


def enrich_picks_with_btc_lead(picks: list[dict]) -> list[dict]:
    """Batch-enrich all picks with BTC lead-lag signals.

    Fail-safe: any error leaves picks unchanged.
    """
    enriched = 0
    for pick in picks:
        try:
            apply_btc_lead_to_pick(pick)
            if (pick.get("extra") or {}).get("btc_granger_significant"):
                enriched += 1
        except Exception:
            continue

    if enriched:
        print(f"  [CAUSAL] BTC lead-lag: enriched {enriched}/{len(picks)} "
              f"crypto picks with Granger-significant signals")
    return picks


# ---------------------------------------------------------------------------
# 3. Spurious Correlation Filter
# ---------------------------------------------------------------------------
def _partial_correlation(
    x: list[float],
    y: list[float],
    z: list[float],
) -> float:
    """Compute partial correlation of x and y controlling for z.

    Uses the formula: r_xy.z = (r_xy - r_xz * r_yz) / sqrt((1 - r_xz^2)(1 - r_yz^2))
    Returns 0.0 on any numerical issue.
    """
    n = min(len(x), len(y), len(z))
    if n < 5:
        return 0.0

    x, y, z = x[:n], y[:n], z[:n]

    r_xy = _pearson(x, y)
    r_xz = _pearson(x, z)
    r_yz = _pearson(y, z)

    denom_sq = (1 - r_xz ** 2) * (1 - r_yz ** 2)
    if denom_sq <= 0:
        return 0.0

    return (r_xy - r_xz * r_yz) / math.sqrt(denom_sq)


def _pearson(x: list[float], y: list[float]) -> float:
    """Pearson correlation coefficient."""
    n = len(x)
    if n < 2:
        return 0.0

    mx = sum(x) / n
    my = sum(y) / n

    num = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    dx = math.sqrt(sum((x[i] - mx) ** 2 for i in range(n)))
    dy = math.sqrt(sum((y[i] - my) ** 2 for i in range(n)))

    if dx < 1e-15 or dy < 1e-15:
        return 0.0

    return num / (dx * dy)


def run_spurious_filter(
    partial_corr_threshold: float = 0.03,
) -> dict:
    """Identify features whose correlation with pnl_pct is spurious.

    For each feature in the ML FEATURES list:
      1. Compute raw correlation with pnl_pct
      2. Compute partial correlation controlling for BTC return
      3. If partial corr drops below threshold, flag as SPURIOUS

    Reads closed picks from data/closed_picks.json.
    Saves flagged features to data/spurious_features.json.
    """
    # Load ML feature list
    try:
        sys.path.insert(0, str(_ENGINE_DIR))
        from ml_ranker import MLSignalRanker
        features_list = list(MLSignalRanker.FEATURES)
    except Exception as e:
        print(f"[CAUSAL] Cannot load ML FEATURES: {e}")
        features_list = []

    if not features_list:
        return {}

    # Load closed picks
    closed_path = _DATA_DIR / "closed_picks.json"
    if not closed_path.exists():
        print("[CAUSAL] No closed_picks.json found, skipping spurious filter")
        return {}

    try:
        with open(closed_path, encoding="utf-8") as f:
            closed_picks = json.load(f)
    except Exception as e:
        print(f"[CAUSAL] Failed to load closed picks: {e}")
        return {}

    if not closed_picks or len(closed_picks) < 20:
        print(f"[CAUSAL] Insufficient closed picks ({len(closed_picks)}), need 20+")
        return {}

    # Extract pnl_pct and BTC return proxy
    pnl_values = []
    btc_returns_proxy = []
    feature_vectors: dict[str, list[float]] = {f: [] for f in features_list}

    for pick in closed_picks:
        pnl = pick.get("pnl_pct")
        if pnl is None:
            continue

        pnl_values.append(float(pnl))

        # BTC return proxy: use cs_relative_strength or compute from BTC context
        extra = pick.get("extra", {}) or {}
        extra_json = pick.get("extra_json", {})
        if isinstance(extra_json, str):
            try:
                extra_json = json.loads(extra_json)
            except (json.JSONDecodeError, TypeError):
                extra_json = {}
        merged = {**extra, **(extra_json or {})}

        # Best proxy for BTC return at time of trade
        btc_ret = merged.get("cs_relative_strength", 0.0)
        btc_returns_proxy.append(float(btc_ret) if btc_ret else 0.0)

        # Extract feature values
        for feat in features_list:
            val = merged.get(feat, pick.get(feat, 0.0))
            try:
                feature_vectors[feat].append(float(val) if val is not None else 0.0)
            except (ValueError, TypeError):
                feature_vectors[feat].append(0.0)

    n_samples = len(pnl_values)
    if n_samples < 20:
        print(f"[CAUSAL] Too few samples ({n_samples}) for spurious filter")
        return {}

    # Run partial correlation for each feature
    spurious = []
    clean = []

    for feat in features_list:
        fv = feature_vectors[feat][:n_samples]

        raw_corr = _pearson(fv, pnl_values)
        partial_corr = _partial_correlation(fv, pnl_values, btc_returns_proxy)

        entry = {
            "feature": feat,
            "raw_corr": round(raw_corr, 6),
            "partial_corr_btc": round(partial_corr, 6),
            "abs_drop": round(abs(raw_corr) - abs(partial_corr), 6),
        }

        if abs(partial_corr) < partial_corr_threshold:
            entry["spurious"] = True
            entry["reason"] = (
                f"partial_corr={partial_corr:.4f} < {partial_corr_threshold} "
                f"after controlling for BTC return (raw={raw_corr:.4f})"
            )
            spurious.append(entry)
        else:
            entry["spurious"] = False
            clean.append(entry)

    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_closed_picks": n_samples,
        "partial_corr_threshold": partial_corr_threshold,
        "spurious_count": len(spurious),
        "clean_count": len(clean),
        "total_features": len(features_list),
        "spurious_features": spurious,
        "clean_features": clean,
    }

    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        out_path = _DATA_DIR / "spurious_features.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
        print(f"[CAUSAL] Spurious filter: {len(spurious)}/{len(features_list)} "
              f"features flagged (partial_corr < {partial_corr_threshold}) -> {out_path.name}")
    except Exception as e:
        print(f"[CAUSAL] Failed to save spurious_features.json: {e}")

    return output


# ---------------------------------------------------------------------------
# 4. Integration helper: get BTC lead boost for elite_scorer
# ---------------------------------------------------------------------------
def get_btc_lead_boost(pick: dict) -> int:
    """Return btc_lead_boost from pick's extra dict (for elite_scorer integration).

    Returns 0 if no data available (backwards-compatible).
    """
    extra = pick.get("extra", {}) or {}
    return int(extra.get("btc_lead_boost", 0))


# ---------------------------------------------------------------------------
# CLI entry point: run all causal tests
# ---------------------------------------------------------------------------
def main():
    """Run all causal inference tests and save results."""
    print("=" * 60)
    print("ALPHA ENGINE -- Causal Inference Filter")
    print("=" * 60)

    print("\n[1/3] Running Granger causality tests (BTC -> alts)...")
    granger = run_granger_tests()
    pairs = granger.get("pairs", {})
    sig = [s for s, d in pairs.items() if d.get("significant")]
    if sig:
        print(f"  Significant: {', '.join(sig[:10])}")

    print("\n[2/3] Testing BTC lead-lag signal...")
    for sym in ["ETHUSDT", "SOLUSDT", "XRPUSDT"]:
        lead = get_btc_lead_signal(sym)
        print(f"  {sym}: btc_return={lead['btc_lead_signal']:.4f}, "
              f"lag={lead['btc_lead_lag']}h, boost={lead['btc_lead_boost']}, "
              f"granger={lead['btc_granger_significant']}")

    print("\n[3/3] Running spurious correlation filter...")
    spurious = run_spurious_filter()
    sp_feats = spurious.get("spurious_features", [])
    if sp_feats:
        print(f"  Flagged: {', '.join(f['feature'] for f in sp_feats[:10])}")

    print("\nDone.")


if __name__ == "__main__":
    main()
