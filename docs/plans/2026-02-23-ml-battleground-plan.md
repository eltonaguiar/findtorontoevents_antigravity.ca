# ML Battleground Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build 3 competing ML crypto trading systems (The Filter, The Regime, The Neural Net) with "Superpowers" dashboards and an Arena comparison page, running autonomously via GitHub Actions.

**Architecture:** Three independent scanner pipelines in `ml_battleground/`, sharing data fetching, indicators, validation, risk management, and cost modeling via `ml_battleground/shared/`. Each system writes its own `data/active_picks.json` and `data/closed_picks.json`, with a self-updating HTML dashboard. An Arena meta-dashboard compares all three.

**Tech Stack:** Python 3.11, XGBoost, LightGBM, scikit-learn, PyTorch (System C only), yfinance, Binance REST API, GitHub Actions, static HTML+JS dashboards.

---

## Phase 1: Shared Infrastructure

### Task 1: Create directory structure and requirements

**Files:**
- Create: `ml_battleground/shared/__init__.py`
- Create: `ml_battleground/system_a_filter/__init__.py`
- Create: `ml_battleground/system_b_regime/__init__.py`
- Create: `ml_battleground/system_c_deeplearn/__init__.py`
- Create: `ml_battleground/requirements.txt`

**Step 1: Create all directories**

```bash
mkdir -p ml_battleground/shared ml_battleground/system_a_filter/models ml_battleground/system_a_filter/data ml_battleground/system_b_regime/models ml_battleground/system_b_regime/data ml_battleground/system_c_deeplearn/models ml_battleground/system_c_deeplearn/data
```

**Step 2: Write requirements.txt**

```
# ml_battleground/requirements.txt
numpy>=1.24.0
pandas>=2.0.0
scipy>=1.10.0
scikit-learn>=1.3.0
xgboost>=2.0.0
lightgbm>=4.0.0
imbalanced-learn>=0.11.0
yfinance>=0.2.30
requests>=2.31.0
joblib>=1.3.0
torch>=2.1.0
```

**Step 3: Create empty __init__.py files**

Each `__init__.py` is empty.

**Step 4: Commit**

```bash
git add ml_battleground/
git commit -m "feat(battleground): scaffold directory structure and requirements"
```

---

### Task 2: Shared data fetcher (`shared/data_fetcher.py`)

**Files:**
- Create: `ml_battleground/shared/data_fetcher.py`

This module wraps Binance REST API for OHLCV with multi-exchange failover. Adapted from `claude_gainer_ml/data_fetcher.py` but outputs DataFrames with capitalized columns (matching alpha_engine convention) keyed by USDT pair.

**Step 1: Write data_fetcher.py**

```python
"""
Shared OHLCV data fetcher for ML Battleground.
Primary: Binance REST. Failover: OKX, Bybit.
Returns: dict[str, pd.DataFrame] with columns [Open, High, Low, Close, Volume].
"""
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Optional

PAIRS = [
    # Tier 1 (liquid)
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    # Tier 2 (alt L1)
    "ADAUSDT", "DOTUSDT", "AVAXUSDT", "LINKUSDT", "NEARUSDT",
    "SUIUSDT", "APTUSDT",
    # Tier 3 (mid-cap)
    "DOGEUSDT", "ARBUSDT", "OPUSDT", "INJUSDT", "FETUSDT",
    "TIAUSDT", "SEIUSDT", "FILUSDT",
]

BINANCE_BASE = "https://api.binance.com"
OKX_BASE = "https://www.okx.com"
BYBIT_BASE = "https://api.bybit.com"


def fetch_ohlcv(
    pairs: Optional[list[str]] = None,
    interval: str = "1h",
    limit: int = 500,
) -> dict[str, pd.DataFrame]:
    """Fetch OHLCV for all pairs. Returns {pair: DataFrame}."""
    pairs = pairs or PAIRS
    result = {}

    for pair in pairs:
        df = _fetch_binance_klines(pair, interval, limit)
        if df is None or len(df) < 50:
            df = _fetch_okx_klines(pair, interval, limit)
        if df is None or len(df) < 50:
            df = _fetch_bybit_klines(pair, interval, limit)
        if df is not None and len(df) >= 50:
            result[pair] = df
        time.sleep(0.1)

    return result


def fetch_single(pair: str, interval: str = "1h", limit: int = 500) -> Optional[pd.DataFrame]:
    """Fetch OHLCV for a single pair."""
    df = _fetch_binance_klines(pair, interval, limit)
    if df is None or len(df) < 50:
        df = _fetch_okx_klines(pair, interval, limit)
    if df is None or len(df) < 50:
        df = _fetch_bybit_klines(pair, interval, limit)
    return df


def _fetch_binance_klines(pair: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
    try:
        url = f"{BINANCE_BASE}/api/v3/klines"
        resp = requests.get(url, params={"symbol": pair, "interval": interval, "limit": limit}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return None
        df = pd.DataFrame(data, columns=[
            "timestamp", "Open", "High", "Low", "Close", "Volume",
            "close_time", "quote_vol", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore"
        ])
        df = df[["timestamp", "Open", "High", "Low", "Close", "Volume"]].copy()
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df.set_index("timestamp", inplace=True)
        df.dropna(inplace=True)
        return df
    except Exception:
        return None


def _fetch_okx_klines(pair: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
    try:
        inst_id = pair.replace("USDT", "-USDT")
        bar_map = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "1H", "4h": "4H", "1d": "1D"}
        bar = bar_map.get(interval, "1H")
        url = f"{OKX_BASE}/api/v5/market/candles"
        resp = requests.get(url, params={"instId": inst_id, "bar": bar, "limit": str(min(limit, 300))}, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if not data:
            return None
        data.reverse()
        df = pd.DataFrame(data, columns=["timestamp", "Open", "High", "Low", "Close", "Volume", "vol_ccy", "vol_ccy_quote", "confirm"])
        df = df[["timestamp", "Open", "High", "Low", "Close", "Volume"]].copy()
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["timestamp"] = pd.to_datetime(df["timestamp"].astype(float), unit="ms", utc=True)
        df.set_index("timestamp", inplace=True)
        df.dropna(inplace=True)
        return df
    except Exception:
        return None


def _fetch_bybit_klines(pair: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
    try:
        interval_map = {"1m": "1", "5m": "5", "15m": "15", "1h": "60", "4h": "240", "1d": "D"}
        bybit_interval = interval_map.get(interval, "60")
        url = f"{BYBIT_BASE}/v5/market/kline"
        resp = requests.get(url, params={"category": "spot", "symbol": pair, "interval": bybit_interval, "limit": str(min(limit, 200))}, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("result", {}).get("list", [])
        if not data:
            return None
        data.reverse()
        df = pd.DataFrame(data, columns=["timestamp", "Open", "High", "Low", "Close", "Volume", "turnover"])
        df = df[["timestamp", "Open", "High", "Low", "Close", "Volume"]].copy()
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["timestamp"] = pd.to_datetime(df["timestamp"].astype(float), unit="ms", utc=True)
        df.set_index("timestamp", inplace=True)
        df.dropna(inplace=True)
        return df
    except Exception:
        return None


def fetch_fear_greed() -> int:
    """Fetch current Fear & Greed Index (0-100)."""
    try:
        resp = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5)
        return int(resp.json()["data"][0]["value"])
    except Exception:
        return 50


def fetch_funding_rates(pairs: Optional[list[str]] = None) -> dict[str, float]:
    """Fetch Binance futures funding rates."""
    pairs = pairs or PAIRS
    result = {}
    try:
        resp = requests.get(f"{BINANCE_BASE.replace('api', 'fapi')}/fapi/v1/premiumIndex", timeout=10)
        resp.raise_for_status()
        for item in resp.json():
            sym = item.get("symbol", "")
            if sym in pairs:
                result[sym] = float(item.get("lastFundingRate", 0))
    except Exception:
        pass
    return result


def fetch_btc_price() -> float:
    """Quick BTC price fetch."""
    try:
        resp = requests.get(f"{BINANCE_BASE}/api/v3/ticker/price", params={"symbol": "BTCUSDT"}, timeout=5)
        return float(resp.json()["price"])
    except Exception:
        return 0.0
```

**Step 2: Commit**

```bash
git add ml_battleground/shared/data_fetcher.py
git commit -m "feat(battleground): shared data fetcher with Binance/OKX/Bybit failover"
```

---

### Task 3: Shared indicators (`shared/indicators.py`)

**Files:**
- Create: `ml_battleground/shared/indicators.py`

Pure-numpy/pandas indicator library. No external TA-lib dependency. Covers all indicators needed by all 3 systems.

**Step 1: Write indicators.py**

```python
"""
Shared technical indicators for ML Battleground.
All functions take pd.Series and return pd.Series (or float for single values).
"""
import numpy as np
import pandas as pd
from typing import Optional


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """Returns (macd_line, signal_line, histogram)."""
    fast_ema = ema(close, fast)
    slow_ema = ema(close, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, min_periods=period).mean()


def bollinger_bands(close: pd.Series, period: int = 20, std_mult: float = 2.0):
    """Returns (upper, middle, lower, width, pctb)."""
    middle = sma(close, period)
    std = close.rolling(period).std()
    upper = middle + std_mult * std
    lower = middle - std_mult * std
    width = (upper - lower) / middle
    pctb = (close - lower) / (upper - lower).replace(0, np.nan)
    return upper, middle, lower, width, pctb


def keltner_channels(high: pd.Series, low: pd.Series, close: pd.Series,
                     ema_period: int = 20, atr_period: int = 14, atr_mult: float = 1.5):
    """Returns (upper, middle, lower)."""
    middle = ema(close, ema_period)
    atr_val = atr(high, low, close, atr_period)
    upper = middle + atr_mult * atr_val
    lower = middle - atr_mult * atr_val
    return upper, middle, lower


def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    mask = plus_dm < minus_dm
    plus_dm[mask] = 0
    minus_dm[~mask] = 0
    atr_val = atr(high, low, close, period)
    plus_di = 100 * ema(plus_dm, period) / atr_val.replace(0, np.nan)
    minus_di = 100 * ema(minus_dm, period) / atr_val.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return ema(dx, period), plus_di, minus_di


def supertrend(high: pd.Series, low: pd.Series, close: pd.Series,
               period: int = 10, multiplier: float = 3.0) -> pd.Series:
    """Returns pd.Series of 1 (bullish) or -1 (bearish)."""
    hl2 = (high + low) / 2
    atr_val = atr(high, low, close, period)
    upper_band = hl2 + multiplier * atr_val
    lower_band = hl2 - multiplier * atr_val

    direction = pd.Series(1, index=close.index)
    final_upper = upper_band.copy()
    final_lower = lower_band.copy()

    for i in range(1, len(close)):
        if lower_band.iloc[i] > final_lower.iloc[i - 1]:
            final_lower.iloc[i] = lower_band.iloc[i]
        else:
            final_lower.iloc[i] = final_lower.iloc[i - 1]
        if upper_band.iloc[i] < final_upper.iloc[i - 1]:
            final_upper.iloc[i] = upper_band.iloc[i]
        else:
            final_upper.iloc[i] = final_upper.iloc[i - 1]

        if direction.iloc[i - 1] == 1:
            if close.iloc[i] < final_lower.iloc[i]:
                direction.iloc[i] = -1
            else:
                direction.iloc[i] = 1
        else:
            if close.iloc[i] > final_upper.iloc[i]:
                direction.iloc[i] = 1
            else:
                direction.iloc[i] = -1

    return direction


def stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
               k_period: int = 14, d_period: int = 3):
    """Returns (%K, %D)."""
    lowest_low = low.rolling(k_period).min()
    highest_high = high.rolling(k_period).max()
    k = 100 * (close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)
    d = sma(k, d_period)
    return k, d


def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    highest_high = high.rolling(period).max()
    lowest_low = low.rolling(period).min()
    return -100 * (highest_high - close) / (highest_high - lowest_low).replace(0, np.nan)


def cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
    tp = (high + low + close) / 3
    sma_tp = sma(tp, period)
    mad = tp.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    return (tp - sma_tp) / (0.015 * mad).replace(0, np.nan)


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff()).fillna(0)
    return (volume * direction).cumsum()


def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    tp = (high + low + close) / 3
    return (tp * volume).cumsum() / volume.cumsum().replace(0, np.nan)


def hurst_exponent(series: pd.Series, max_lag: int = 50) -> float:
    """Estimate Hurst exponent. H > 0.5 = trending, H < 0.5 = mean-reverting."""
    if len(series) < max_lag * 2:
        return 0.5
    lags = range(2, max_lag)
    tau = []
    for lag in lags:
        diff = series.diff(lag).dropna()
        if len(diff) > 0:
            tau.append(np.sqrt(np.abs(diff).mean()))
        else:
            tau.append(np.nan)
    tau = np.array(tau)
    valid = ~np.isnan(tau) & (tau > 0)
    if valid.sum() < 5:
        return 0.5
    log_lags = np.log(np.array(list(lags))[valid])
    log_tau = np.log(tau[valid])
    poly = np.polyfit(log_lags, log_tau, 1)
    return max(0.0, min(1.0, poly[0]))


def realized_volatility(close: pd.Series, period: int = 20) -> pd.Series:
    """Annualized realized volatility from log returns."""
    log_ret = np.log(close / close.shift(1))
    return log_ret.rolling(period).std() * np.sqrt(365 * 24)  # hourly assumption
```

**Step 2: Commit**

```bash
git add ml_battleground/shared/indicators.py
git commit -m "feat(battleground): shared indicator library (RSI, MACD, ATR, Supertrend, Hurst, etc.)"
```

---

### Task 4: Shared S/R engine (`shared/sr_engine.py`)

**Files:**
- Create: `ml_battleground/shared/sr_engine.py`

Consolidated from `alpha_engine/pattern_strategies.py` fractal pivot + volume profile logic.

**Step 1: Write sr_engine.py**

```python
"""
Support/Resistance detection engine for ML Battleground.
Combines Williams fractal pivots, volume profile (POC/VAH/VAL),
multi-touch clustering, and round-number magnetism.
"""
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional


@dataclass
class SRLevel:
    price: float
    strength: float       # composite score (higher = stronger)
    touches: int
    level_type: str       # "support" | "resistance"
    source: str           # "fractal" | "volume_profile" | "round_number"
    recency: float        # 0-1, higher = more recent


def detect_sr_levels(
    df: pd.DataFrame,
    current_price: Optional[float] = None,
    fractal_window: int = 5,
    cluster_tolerance: float = 0.003,
    min_touches: int = 2,
    n_volume_bins: int = 50,
    volume_lookback: int = 100,
    max_levels: int = 10,
) -> list[SRLevel]:
    """
    Detect support and resistance levels from OHLCV data.

    Args:
        df: DataFrame with columns [Open, High, Low, Close, Volume]
        current_price: Current price (defaults to last close)
        fractal_window: Window for Williams fractal detection
        cluster_tolerance: Clustering tolerance as fraction of price
        min_touches: Minimum touches for a level to qualify
        n_volume_bins: Number of bins for volume profile
        volume_lookback: Bars to look back for volume profile
        max_levels: Maximum S/R levels to return

    Returns:
        List of SRLevel sorted by strength (strongest first)
    """
    if current_price is None:
        current_price = float(df["Close"].iloc[-1])

    levels = []

    # 1. Fractal pivots + clustering
    fractal_levels = _fractal_sr(df, fractal_window, cluster_tolerance, min_touches)
    levels.extend(fractal_levels)

    # 2. Volume profile
    vp_levels = _volume_profile_sr(df, n_volume_bins, volume_lookback)
    levels.extend(vp_levels)

    # 3. Round numbers
    round_levels = _round_number_sr(current_price)
    levels.extend(round_levels)

    # Label as support/resistance relative to current price
    for level in levels:
        if level.price < current_price:
            level.level_type = "support"
        else:
            level.level_type = "resistance"

    # Merge nearby levels from different sources
    levels = _merge_nearby(levels, tolerance=cluster_tolerance)

    # Sort by strength descending
    levels.sort(key=lambda x: x.strength, reverse=True)

    return levels[:max_levels]


def nearest_support(levels: list[SRLevel], price: float) -> Optional[SRLevel]:
    """Find strongest support level below price."""
    supports = [l for l in levels if l.level_type == "support" and l.price < price]
    if not supports:
        return None
    return max(supports, key=lambda x: x.strength)


def nearest_resistance(levels: list[SRLevel], price: float) -> Optional[SRLevel]:
    """Find strongest resistance level above price."""
    resistances = [l for l in levels if l.level_type == "resistance" and l.price > price]
    if not resistances:
        return None
    return max(resistances, key=lambda x: x.strength)


def sr_based_tp_sl(
    entry_price: float,
    levels: list[SRLevel],
    atr_value: float,
    signal_type: str = "BUY",
    min_rr: float = 1.5,
    tp_atr_fallback: float = 2.5,
    sl_atr_fallback: float = 1.5,
) -> tuple[float, float, str]:
    """
    Set TP/SL using S/R levels with ATR fallback.

    Returns:
        (take_profit, stop_loss, method) where method is "sr" or "atr"
    """
    if signal_type == "BUY":
        resistance = nearest_resistance(levels, entry_price)
        support = nearest_support(levels, entry_price)

        tp = resistance.price if resistance else entry_price + tp_atr_fallback * atr_value
        sl = support.price * 0.998 if support else entry_price - sl_atr_fallback * atr_value

        # Ensure minimum R:R
        risk = entry_price - sl
        reward = tp - entry_price
        if risk > 0 and reward / risk < min_rr:
            tp = entry_price + min_rr * risk

        method = "sr" if (resistance or support) else "atr"
    else:  # SELL
        support = nearest_support(levels, entry_price)
        resistance = nearest_resistance(levels, entry_price)

        tp = support.price if support else entry_price - tp_atr_fallback * atr_value
        sl = resistance.price * 1.002 if resistance else entry_price + sl_atr_fallback * atr_value

        risk = sl - entry_price
        reward = entry_price - tp
        if risk > 0 and reward / risk < min_rr:
            tp = entry_price - min_rr * risk

        method = "sr" if (support or resistance) else "atr"

    return tp, sl, method


def _fractal_sr(
    df: pd.DataFrame,
    window: int = 5,
    tolerance: float = 0.003,
    min_touches: int = 2,
) -> list[SRLevel]:
    """Williams fractal pivots → clustered S/R levels."""
    high = df["High"].values
    low = df["Low"].values
    n = len(df)
    half = window // 2
    pivots = []

    for i in range(half, n - half):
        is_high = True
        is_low = True
        for j in range(i - half, i + half + 1):
            if j == i:
                continue
            if high[j] >= high[i]:
                is_high = False
            if low[j] <= low[i]:
                is_low = False
        if is_high:
            pivots.append((i, float(high[i]), "high"))
        if is_low:
            pivots.append((i, float(low[i]), "low"))

    # Cluster pivots
    if not pivots:
        return []

    pivots.sort(key=lambda x: x[1])
    clusters = []
    used = set()

    for idx, (i, price, ptype) in enumerate(pivots):
        if idx in used:
            continue
        cluster = [(i, price, ptype)]
        used.add(idx)
        for jdx, (j, price2, ptype2) in enumerate(pivots):
            if jdx in used:
                continue
            if abs(price2 - price) / price <= tolerance:
                cluster.append((j, price2, ptype2))
                used.add(jdx)

        if len(cluster) >= min_touches:
            avg_price = np.mean([p for _, p, _ in cluster])
            max_idx = max(c[0] for c in cluster)
            recency = max_idx / n if n > 0 else 0.5
            strength = len(cluster) * (1.0 + 0.5 * recency)

            levels_out = SRLevel(
                price=round(avg_price, 8),
                strength=strength,
                touches=len(cluster),
                level_type="support",  # will be relabeled
                source="fractal",
                recency=recency,
            )
            clusters.append(levels_out)

    return clusters


def _volume_profile_sr(
    df: pd.DataFrame,
    n_bins: int = 50,
    lookback: int = 100,
) -> list[SRLevel]:
    """Volume profile → POC, VAH, VAL as S/R levels."""
    data = df.tail(lookback)
    if len(data) < 20:
        return []

    price_min = float(data["Low"].min())
    price_max = float(data["High"].max())
    if price_max <= price_min:
        return []

    bin_edges = np.linspace(price_min, price_max, n_bins + 1)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    profile = np.zeros(n_bins)

    for _, row in data.iterrows():
        bar_low = float(row["Low"])
        bar_high = float(row["High"])
        bar_vol = float(row["Volume"])
        if bar_high <= bar_low or bar_vol <= 0:
            continue
        for k in range(n_bins):
            overlap = max(0, min(bar_high, bin_edges[k + 1]) - max(bar_low, bin_edges[k]))
            bar_range = bar_high - bar_low
            if bar_range > 0:
                profile[k] += bar_vol * (overlap / bar_range)

    if profile.sum() == 0:
        return []

    # POC
    poc_idx = int(np.argmax(profile))
    poc_price = float(bin_centers[poc_idx])

    # Value Area (70% of volume)
    total_vol = profile.sum()
    target = 0.70 * total_vol
    accumulated = profile[poc_idx]
    lo_idx = poc_idx
    hi_idx = poc_idx

    while accumulated < target and (lo_idx > 0 or hi_idx < n_bins - 1):
        expand_lo = profile[lo_idx - 1] if lo_idx > 0 else 0
        expand_hi = profile[hi_idx + 1] if hi_idx < n_bins - 1 else 0
        if expand_lo >= expand_hi and lo_idx > 0:
            lo_idx -= 1
            accumulated += profile[lo_idx]
        elif hi_idx < n_bins - 1:
            hi_idx += 1
            accumulated += profile[hi_idx]
        else:
            break

    val = float(bin_centers[lo_idx])
    vah = float(bin_centers[hi_idx])

    levels = [
        SRLevel(price=round(poc_price, 8), strength=5.0, touches=0,
                level_type="support", source="volume_profile", recency=0.9),
        SRLevel(price=round(val, 8), strength=3.5, touches=0,
                level_type="support", source="volume_profile", recency=0.9),
        SRLevel(price=round(vah, 8), strength=3.5, touches=0,
                level_type="resistance", source="volume_profile", recency=0.9),
    ]
    return levels


def _round_number_sr(price: float) -> list[SRLevel]:
    """Psychological round-number levels near current price."""
    if price <= 0:
        return []

    magnitude = 10 ** int(np.log10(price))
    step = magnitude / 10 if price < magnitude * 5 else magnitude / 5
    if step < 0.01:
        step = 0.01

    levels = []
    base = round(price / step) * step
    for offset in [-3, -2, -1, 0, 1, 2, 3]:
        level_price = base + offset * step
        if level_price > 0 and abs(level_price - price) / price < 0.10:
            distance = abs(level_price - price) / price
            strength = max(0.5, 2.0 - distance * 20)
            levels.append(SRLevel(
                price=round(level_price, 8),
                strength=strength,
                touches=0,
                level_type="support",
                source="round_number",
                recency=1.0,
            ))
    return levels


def _merge_nearby(levels: list[SRLevel], tolerance: float = 0.003) -> list[SRLevel]:
    """Merge S/R levels from different sources that are very close."""
    if not levels:
        return []

    levels.sort(key=lambda x: x.price)
    merged = [levels[0]]

    for level in levels[1:]:
        prev = merged[-1]
        if abs(level.price - prev.price) / prev.price <= tolerance:
            # Merge: keep higher strength, sum touches, combine sources
            if level.strength > prev.strength:
                merged[-1] = SRLevel(
                    price=(prev.price + level.price) / 2,
                    strength=prev.strength + level.strength,
                    touches=prev.touches + level.touches,
                    level_type=prev.level_type,
                    source=f"{prev.source}+{level.source}",
                    recency=max(prev.recency, level.recency),
                )
            else:
                merged[-1] = SRLevel(
                    price=(prev.price + level.price) / 2,
                    strength=prev.strength + level.strength,
                    touches=prev.touches + level.touches,
                    level_type=prev.level_type,
                    source=f"{prev.source}+{level.source}",
                    recency=max(prev.recency, level.recency),
                )
        else:
            merged.append(level)

    return merged
```

**Step 2: Commit**

```bash
git add ml_battleground/shared/sr_engine.py
git commit -m "feat(battleground): S/R engine with fractal pivots, volume profile, round numbers"
```

---

### Task 5: Shared risk manager + cost model + performance (`shared/risk_manager.py`, `shared/cost_model.py`, `shared/performance.py`)

**Files:**
- Create: `ml_battleground/shared/risk_manager.py`
- Create: `ml_battleground/shared/cost_model.py`
- Create: `ml_battleground/shared/performance.py`

**Step 1: Write risk_manager.py**

```python
"""
Conservative risk management for ML Battleground.
- 2% risk per trade
- 10% max portfolio drawdown circuit breaker
- Max 5 concurrent positions
- Fractional Kelly (0.25x) sizing
"""
import numpy as np


MAX_RISK_PER_TRADE = 0.02
MAX_DRAWDOWN = 0.10
MAX_CONCURRENT = 5
KELLY_FRACTION = 0.25
MIN_POSITION_SIZE = 0.005  # 0.5% minimum


def position_size(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    confidence: float = 1.0,
    capital: float = 10000.0,
) -> float:
    """Fractional Kelly position sizing. Returns fraction of capital."""
    if avg_loss <= 0 or win_rate <= 0 or win_rate >= 1:
        return MIN_POSITION_SIZE

    b = avg_win / avg_loss
    kelly_full = (win_rate * b - (1 - win_rate)) / b
    if kelly_full <= 0:
        return MIN_POSITION_SIZE

    sized = kelly_full * KELLY_FRACTION * confidence
    return max(MIN_POSITION_SIZE, min(sized, MAX_RISK_PER_TRADE))


def can_open_trade(
    active_count: int,
    current_drawdown: float,
) -> tuple[bool, str]:
    """Check if we're allowed to open a new position."""
    if active_count >= MAX_CONCURRENT:
        return False, f"max concurrent positions ({MAX_CONCURRENT}) reached"
    if current_drawdown >= MAX_DRAWDOWN:
        return False, f"drawdown circuit breaker ({MAX_DRAWDOWN:.0%}) triggered"
    return True, "ok"


def calculate_drawdown(equity_curve: list[float]) -> float:
    """Current drawdown from peak."""
    if not equity_curve or len(equity_curve) < 2:
        return 0.0
    peak = max(equity_curve)
    current = equity_curve[-1]
    if peak <= 0:
        return 0.0
    return (peak - current) / peak
```

**Step 2: Write cost_model.py**

```python
"""
Transaction cost model for crypto trading.
Adapted from alpha_engine/transaction_costs.py.
"""

# Round-trip costs (entry + exit) as decimal
COST_BY_TIER = {
    "tier1": 0.0025,   # BTC, ETH, BNB, SOL, XRP — tight spreads
    "tier2": 0.004,    # alt L1 — moderate spreads
    "tier3": 0.007,    # mid-cap — wider spreads
}

PAIR_TIER = {
    "BTCUSDT": "tier1", "ETHUSDT": "tier1", "BNBUSDT": "tier1",
    "SOLUSDT": "tier1", "XRPUSDT": "tier1",
    "ADAUSDT": "tier2", "DOTUSDT": "tier2", "AVAXUSDT": "tier2",
    "LINKUSDT": "tier2", "NEARUSDT": "tier2", "SUIUSDT": "tier2",
    "APTUSDT": "tier2",
    "DOGEUSDT": "tier3", "ARBUSDT": "tier3", "OPUSDT": "tier3",
    "INJUSDT": "tier3", "FETUSDT": "tier3", "TIAUSDT": "tier3",
    "SEIUSDT": "tier3", "FILUSDT": "tier3",
}


def round_trip_cost(pair: str) -> float:
    tier = PAIR_TIER.get(pair, "tier3")
    return COST_BY_TIER[tier]


def net_pnl(entry: float, exit_price: float, pair: str, signal_type: str = "BUY") -> float:
    """Net PnL percentage after costs."""
    cost = round_trip_cost(pair)
    if signal_type == "BUY":
        gross = (exit_price - entry) / entry
    else:
        gross = (entry - exit_price) / entry
    return gross - cost
```

**Step 3: Write performance.py**

```python
"""
Performance metrics for ML Battleground.
Sharpe, Sortino, Calmar, DSR, Monte Carlo, equity curve.
"""
import numpy as np
from scipy import stats
from typing import Optional


def sharpe_ratio(returns: list[float], risk_free: float = 0.0, annualize: float = 252.0) -> float:
    """Annualized Sharpe ratio."""
    if not returns or len(returns) < 2:
        return 0.0
    arr = np.array(returns)
    excess = arr - risk_free / annualize
    if np.std(excess) == 0:
        return 0.0
    return float(np.mean(excess) / np.std(excess) * np.sqrt(annualize))


def sortino_ratio(returns: list[float], risk_free: float = 0.0, annualize: float = 252.0) -> float:
    """Annualized Sortino ratio (downside deviation only)."""
    if not returns or len(returns) < 2:
        return 0.0
    arr = np.array(returns)
    excess = arr - risk_free / annualize
    downside = excess[excess < 0]
    if len(downside) == 0:
        return 10.0  # cap
    downside_std = np.std(downside)
    if downside_std == 0:
        return 10.0
    return float(np.mean(excess) / downside_std * np.sqrt(annualize))


def calmar_ratio(total_return: float, max_drawdown: float, years: float = 1.0) -> float:
    """Calmar ratio: annualized return / max drawdown."""
    if max_drawdown <= 0 or years <= 0:
        return 0.0
    annual_return = total_return / years
    return float(annual_return / max_drawdown)


def max_drawdown(equity_curve: list[float]) -> tuple[float, int]:
    """Returns (max_dd_fraction, duration_in_periods)."""
    if not equity_curve or len(equity_curve) < 2:
        return 0.0, 0
    arr = np.array(equity_curve)
    peak = np.maximum.accumulate(arr)
    dd = (peak - arr) / np.where(peak > 0, peak, 1)
    max_dd = float(np.max(dd))
    # Duration: longest streak below peak
    below_peak = dd > 0
    max_dur = 0
    cur_dur = 0
    for b in below_peak:
        if b:
            cur_dur += 1
            max_dur = max(max_dur, cur_dur)
        else:
            cur_dur = 0
    return max_dd, max_dur


def profit_factor(wins: list[float], losses: list[float]) -> float:
    """Sum of wins / abs(sum of losses)."""
    total_wins = sum(wins) if wins else 0
    total_losses = abs(sum(losses)) if losses else 0
    if total_losses == 0:
        return 10.0 if total_wins > 0 else 0.0
    return float(total_wins / total_losses)


def deflated_sharpe_ratio(
    observed_sharpe: float,
    n_trials: int,
    n_observations: int,
    skewness: float = 0.0,
    kurtosis: float = 3.0,
) -> float:
    """Bailey & Lopez de Prado (2014). Returns probability true Sharpe > 0."""
    if n_trials <= 1 or n_observations <= 1:
        return 0.5
    e_max_sharpe = np.sqrt(2 * np.log(n_trials)) * (1 - np.euler_gamma / (2 * np.log(n_trials)))
    se = np.sqrt((1 - skewness * observed_sharpe + (kurtosis - 1) / 4 * observed_sharpe ** 2) / (n_observations - 1))
    if se <= 0:
        return 0.5
    z = (observed_sharpe - e_max_sharpe) / se
    return float(stats.norm.cdf(z))


def monte_carlo_test(
    trade_pnls: list[float],
    n_permutations: int = 1000,
    metric: str = "sharpe",
) -> tuple[float, float]:
    """
    Permutation test. Returns (p_value, observed_metric).
    Shuffles trade order to test if sequence matters.
    """
    if not trade_pnls or len(trade_pnls) < 5:
        return 1.0, 0.0

    arr = np.array(trade_pnls)
    observed = sharpe_ratio(list(arr)) if metric == "sharpe" else float(np.mean(arr))

    count_better = 0
    rng = np.random.default_rng(42)
    for _ in range(n_permutations):
        shuffled = rng.permutation(arr)
        shuffled_metric = sharpe_ratio(list(shuffled)) if metric == "sharpe" else float(np.mean(shuffled))
        if shuffled_metric >= observed:
            count_better += 1

    p_value = (count_better + 1) / (n_permutations + 1)
    return float(p_value), float(observed)


def compute_stats(closed_picks: list[dict]) -> dict:
    """Compute comprehensive stats from closed picks."""
    if not closed_picks:
        return {"trades": 0, "win_rate": 0, "sharpe": 0, "max_dd": 0, "pf": 0}

    pnls = [p.get("net_pnl_pct", p.get("pnl_pct", 0)) for p in closed_picks]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    equity = [10000.0]
    for pnl in pnls:
        equity.append(equity[-1] * (1 + pnl / 100))

    dd, dd_dur = max_drawdown(equity)

    return {
        "trades": len(closed_picks),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": len(wins) / len(closed_picks) if closed_picks else 0,
        "avg_win_pct": float(np.mean(wins)) if wins else 0,
        "avg_loss_pct": float(np.mean(losses)) if losses else 0,
        "total_pnl_pct": sum(pnls),
        "sharpe": sharpe_ratio(pnls),
        "sortino": sortino_ratio(pnls),
        "max_dd": dd,
        "max_dd_duration": dd_dur,
        "profit_factor": profit_factor(wins, losses),
        "expectancy": float(np.mean(pnls)) if pnls else 0,
        "equity_curve": equity,
    }
```

**Step 4: Commit**

```bash
git add ml_battleground/shared/risk_manager.py ml_battleground/shared/cost_model.py ml_battleground/shared/performance.py
git commit -m "feat(battleground): shared risk manager, cost model, and performance metrics"
```

---

### Task 6: Shared forward validator (`shared/validator.py`)

**Files:**
- Create: `ml_battleground/shared/validator.py`

Adapted from `alpha_engine/forward_validator.py`. Checks active picks against live prices, records outcomes.

**Step 1: Write validator.py**

```python
"""
Forward validation for ML Battleground.
Checks active picks against live Binance prices.
Records TP/SL/trailing/expiry outcomes.
"""
import json
import os
import time
import requests
from datetime import datetime, timezone, timedelta
from typing import Optional

from . import cost_model


TRAIL_ACTIVATE_PCT = 0.03   # activate trailing after +3%
TRAIL_STOP_PCT = 0.05       # trail 5% from high-water mark
MAX_HOLD_HOURS = {
    "15m": 48,    # 2 days for scalp
    "1h": 168,    # 7 days for swing
}


def validate_picks(
    active: list[dict],
    system_name: str,
    data_dir: str,
) -> tuple[list[dict], list[dict]]:
    """
    Validate active picks against live prices.
    Returns (still_active, newly_closed).
    """
    if not active:
        return [], []

    # Fetch current prices
    symbols = list(set(p["symbol"] for p in active))
    prices = _fetch_live_prices(symbols)

    still_active = []
    newly_closed = []
    now = datetime.now(timezone.utc)

    for pick in active:
        symbol = pick["symbol"]
        if symbol not in prices:
            still_active.append(pick)
            continue

        price_data = prices[symbol]
        current = price_data["price"]
        day_high = price_data["high"]
        day_low = price_data["low"]

        entry = pick["entry_price"]
        tp = pick["take_profit"]
        sl = pick["stop_loss"]
        signal = pick.get("signal_type", "BUY")
        timeframe = pick.get("timeframe", "1h")
        opened_at = datetime.fromisoformat(pick["timestamp"])

        # Track high-water mark
        if signal == "BUY":
            hwm = max(pick.get("hwm", entry), day_high)
        else:
            hwm = min(pick.get("hwm", entry), day_low)
        pick["hwm"] = hwm

        # Check expiry
        max_hold = MAX_HOLD_HOURS.get(timeframe, 168)
        hours_held = (now - opened_at).total_seconds() / 3600
        if hours_held > max_hold:
            pick["exit_price"] = current
            pick["exit_reason"] = "expiry"
            pick["closed_at"] = now.isoformat()
            _record_pnl(pick)
            newly_closed.append(pick)
            continue

        # Check SL (priority over TP — conservative)
        sl_hit = (day_low <= sl) if signal == "BUY" else (day_high >= sl)
        if sl_hit:
            pick["exit_price"] = sl
            pick["exit_reason"] = "stop_loss"
            pick["closed_at"] = now.isoformat()
            _record_pnl(pick)
            newly_closed.append(pick)
            continue

        # Check TP
        tp_hit = (day_high >= tp) if signal == "BUY" else (day_low <= tp)
        if tp_hit:
            pick["exit_price"] = tp
            pick["exit_reason"] = "take_profit"
            pick["closed_at"] = now.isoformat()
            _record_pnl(pick)
            newly_closed.append(pick)
            continue

        # Check trailing stop
        if signal == "BUY":
            unrealized = (hwm - entry) / entry
            if unrealized > TRAIL_ACTIVATE_PCT:
                trail_level = hwm * (1 - TRAIL_STOP_PCT)
                if day_low <= trail_level:
                    pick["exit_price"] = trail_level
                    pick["exit_reason"] = "trailing_stop"
                    pick["closed_at"] = now.isoformat()
                    _record_pnl(pick)
                    newly_closed.append(pick)
                    continue
        else:
            unrealized = (entry - hwm) / entry
            if unrealized > TRAIL_ACTIVATE_PCT:
                trail_level = hwm * (1 + TRAIL_STOP_PCT)
                if day_high >= trail_level:
                    pick["exit_price"] = trail_level
                    pick["exit_reason"] = "trailing_stop"
                    pick["closed_at"] = now.isoformat()
                    _record_pnl(pick)
                    newly_closed.append(pick)
                    continue

        # Update current price for dashboard
        pick["current_price"] = current
        pick["unrealized_pnl_pct"] = ((current - entry) / entry * 100) if signal == "BUY" else ((entry - current) / entry * 100)
        still_active.append(pick)

    return still_active, newly_closed


def save_picks(active: list[dict], closed: list[dict], data_dir: str):
    """Save active and closed picks to JSON files."""
    os.makedirs(data_dir, exist_ok=True)

    with open(os.path.join(data_dir, "active_picks.json"), "w") as f:
        json.dump(active, f, indent=2, default=str)

    closed_path = os.path.join(data_dir, "closed_picks.json")
    existing_closed = []
    if os.path.exists(closed_path):
        with open(closed_path) as f:
            existing_closed = json.load(f)

    existing_closed.extend(closed)
    with open(closed_path, "w") as f:
        json.dump(existing_closed, f, indent=2, default=str)


def load_active(data_dir: str) -> list[dict]:
    """Load active picks from JSON."""
    path = os.path.join(data_dir, "active_picks.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []


def load_closed(data_dir: str) -> list[dict]:
    """Load closed picks from JSON."""
    path = os.path.join(data_dir, "closed_picks.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []


def _record_pnl(pick: dict):
    """Calculate and record PnL on a closed pick."""
    entry = pick["entry_price"]
    exit_price = pick["exit_price"]
    signal = pick.get("signal_type", "BUY")
    pair = pick["symbol"]

    if signal == "BUY":
        gross_pnl = (exit_price - entry) / entry * 100
    else:
        gross_pnl = (entry - exit_price) / entry * 100

    cost = cost_model.round_trip_cost(pair) * 100
    pick["gross_pnl_pct"] = round(gross_pnl, 4)
    pick["net_pnl_pct"] = round(gross_pnl - cost, 4)
    pick["cost_pct"] = round(cost, 4)


def _fetch_live_prices(symbols: list[str]) -> dict:
    """Fetch 24h ticker from Binance for price + high + low."""
    result = {}
    try:
        resp = requests.get(
            "https://api.binance.com/api/v3/ticker/24hr",
            timeout=10,
        )
        resp.raise_for_status()
        for item in resp.json():
            sym = item["symbol"]
            if sym in symbols:
                result[sym] = {
                    "price": float(item["lastPrice"]),
                    "high": float(item["highPrice"]),
                    "low": float(item["lowPrice"]),
                }
    except Exception:
        pass
    return result


def passes_validation_gate(stats: dict) -> tuple[bool, str]:
    """Check if a system has earned 'proven' status."""
    trades = stats.get("trades", 0)
    wr = stats.get("win_rate", 0)
    sr = stats.get("sharpe", 0)
    dd = stats.get("max_dd", 1)

    if trades < 50:
        return False, f"need 50+ trades (have {trades})"
    if wr < 0.55:
        return False, f"need WR > 55% (have {wr:.1%})"
    if sr < 1.0:
        return False, f"need Sharpe > 1.0 (have {sr:.2f})"
    if dd > 0.15:
        return False, f"need DD < 15% (have {dd:.1%})"

    return True, "PROVEN"
```

**Step 2: Commit**

```bash
git add ml_battleground/shared/validator.py
git commit -m "feat(battleground): shared forward validator with TP/SL/trailing/expiry checking"
```

---

## Phase 2: System A — "The Filter"

### Task 7: System A strategies (`system_a_filter/strategies.py`)

**Files:**
- Create: `ml_battleground/system_a_filter/strategies.py`

8 proven strategies, each returning standardized signal dicts. Logic adapted from existing alpha_engine code but self-contained.

**Step 1: Write strategies.py**

This is a large file (~400 lines). Each strategy takes a DataFrame and returns a list of signal dicts. I'll implement the 8 strategies as individual functions, all sharing the same signature:

```python
def strategy_name(df: pd.DataFrame, pair: str) -> list[dict]
```

Where `df` has columns `[Open, High, Low, Close, Volume]` and each returned dict has:
`strategy, symbol, signal_type, entry_price, confidence, timeframe, timestamp, reason, atr_value, rsi_value, volume_ratio`

TP/SL will be set by the S/R engine in the scanner, not here.

The 8 strategies to implement:
1. `supertrend_follow` — Supertrend direction change (from shared/indicators.py)
2. `connors_rsi2` — RSI(2) < 5 + price > SMA(200) + RSI(14) > 20
3. `bollinger_keltner_squeeze` — BB inside Keltner for ≥3 bars, signal on first release
4. `rsi_macd_confluence` — RSI crosses 30 from below + MACD hist rising + price > SMA(200)
5. `ema_stack` — EMA 9>21>50>200 alignment + price pullback to EMA9
6. `volume_climax_reversal` — Vol > 5x avg + close in top 30% of bar
7. `swing_failure_pattern` — Wick below swing low + close above it
8. `ornstein_uhlenbeck` — OLS AR(1) mean-reversion when deviation > 1.5σ

Each function: ~30-50 lines. Total file: ~400-500 lines.

**Step 2: Commit**

```bash
git add ml_battleground/system_a_filter/strategies.py
git commit -m "feat(battleground/A): 8 proven strategies for The Filter"
```

---

### Task 8: System A ML filter (`system_a_filter/ml_filter.py` + `train_filter.py`)

**Files:**
- Create: `ml_battleground/system_a_filter/ml_filter.py`
- Create: `ml_battleground/system_a_filter/train_filter.py`

**Step 1: Write ml_filter.py**

XGBoost binary classifier. Features are computed from the signal context (S/R proximity, volume, RSI, etc.). Falls back to heuristic scoring when no trained model exists.

```python
"""
ML Context Filter for System A.
Scores each raw signal as "take" (1) or "skip" (0).
Falls back to heuristic when no trained model available.
"""
import os
import numpy as np
import joblib
from typing import Optional

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "filter_xgb.joblib")
SCALER_PATH = os.path.join(os.path.dirname(__file__), "models", "filter_scaler.joblib")

FEATURE_NAMES = [
    "dist_to_support_pct",
    "dist_to_resistance_pct",
    "sr_support_strength",
    "sr_resistance_strength",
    "sr_spread_pct",
    "volume_ratio_20",
    "rsi_14",
    "atr_percentile",
    "fear_greed",
    "funding_rate",
    "hour_sin",
    "hour_cos",
    "btc_correlation",
    "btc_return_1h",
    "consecutive_green",
    "bollinger_pctb",
    "strategy_supertrend",
    "strategy_connors",
    "strategy_squeeze",
    "strategy_rsi_macd",
    "strategy_ema_stack",
    "strategy_volume_climax",
    "strategy_sfp",
    "strategy_ou",
]


def compute_filter_features(
    signal: dict,
    sr_levels: list,
    df,
    fear_greed: int = 50,
    funding_rate: float = 0.0,
    btc_return_1h: float = 0.0,
) -> np.ndarray:
    """Compute feature vector for the ML filter."""
    from ..shared import indicators as ind
    from ..shared.sr_engine import nearest_support, nearest_resistance

    price = signal["entry_price"]
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    # S/R features
    sup = nearest_support(sr_levels, price)
    res = nearest_resistance(sr_levels, price)
    dist_sup = (price - sup.price) / price if sup else 0.05
    dist_res = (res.price - price) / price if res else 0.05
    sup_strength = sup.strength if sup else 0.0
    res_strength = res.strength if res else 0.0
    sr_spread = dist_sup + dist_res

    # Technical features
    vol_ratio = float(volume.iloc[-1] / volume.rolling(20).mean().iloc[-1]) if volume.rolling(20).mean().iloc[-1] > 0 else 1.0
    rsi_val = float(ind.rsi(close).iloc[-1])
    atr_val = ind.atr(high, low, close)
    atr_pctile = float((atr_val.iloc[-1] <= atr_val.tail(60)).mean()) if len(atr_val) >= 60 else 0.5
    _, _, _, _, pctb = ind.bollinger_bands(close)
    pctb_val = float(pctb.iloc[-1]) if not np.isnan(pctb.iloc[-1]) else 0.5

    # Time features
    hour = df.index[-1].hour if hasattr(df.index[-1], 'hour') else 12
    hour_sin = np.sin(2 * np.pi * hour / 24)
    hour_cos = np.cos(2 * np.pi * hour / 24)

    # BTC correlation (placeholder — computed in scanner with BTC data)
    btc_corr = 0.5

    # Consecutive green candles
    greens = 0
    for i in range(len(close) - 1, max(0, len(close) - 11), -1):
        if close.iloc[i] > df["Open"].iloc[i]:
            greens += 1
        else:
            break

    # Strategy one-hot
    strat = signal.get("strategy", "")
    strat_features = [
        1.0 if "supertrend" in strat else 0.0,
        1.0 if "connors" in strat else 0.0,
        1.0 if "squeeze" in strat else 0.0,
        1.0 if "rsi_macd" in strat else 0.0,
        1.0 if "ema_stack" in strat else 0.0,
        1.0 if "volume_climax" in strat else 0.0,
        1.0 if "sfp" in strat else 0.0,
        1.0 if "ornstein" in strat or "ou" in strat else 0.0,
    ]

    features = [
        dist_sup, dist_res, sup_strength, res_strength, sr_spread,
        vol_ratio, rsi_val, atr_pctile, fear_greed / 100.0, funding_rate,
        hour_sin, hour_cos, btc_corr, btc_return_1h, float(greens), pctb_val,
    ] + strat_features

    return np.array(features, dtype=np.float64)


def predict(features: np.ndarray) -> tuple[float, str]:
    """
    Predict whether to take a signal.
    Returns (score 0-1, method "ml"|"heuristic").
    """
    if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
        try:
            model = joblib.load(MODEL_PATH)
            scaler = joblib.load(SCALER_PATH)
            X = scaler.transform(features.reshape(1, -1))
            prob = float(model.predict_proba(X)[0][1])
            return prob, "ml"
        except Exception:
            pass

    # Heuristic fallback
    return _heuristic_score(features), "heuristic"


def _heuristic_score(features: np.ndarray) -> float:
    """Simple rule-based scoring when no ML model available."""
    score = 0.5

    dist_sup = features[0]
    dist_res = features[1]
    sup_strength = features[2]
    rsi_val = features[6]
    vol_ratio = features[5]

    # Close to strong support = good for BUY
    if dist_sup < 0.02 and sup_strength >= 3:
        score += 0.15
    # Good R:R (far resistance, close support)
    if dist_res > 2 * dist_sup and dist_sup > 0:
        score += 0.10
    # Oversold RSI
    if rsi_val < 35:
        score += 0.10
    # Volume confirmation
    if vol_ratio > 1.5:
        score += 0.05
    # Extreme greed penalty
    if features[8] > 0.80:
        score -= 0.10

    return max(0.0, min(1.0, score))
```

**Step 2: Write train_filter.py**

Training script that builds labels from historical strategy signals + triple-barrier outcomes.

```python
"""
Train the ML filter for System A.
Uses walk-forward validation on historical strategy signals.
Run: python -m ml_battleground.system_a_filter.train_filter
"""
import os
import sys
import numpy as np
import pandas as pd
import joblib
from datetime import datetime, timezone
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
from sklearn.model_selection import TimeSeriesSplit

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.data_fetcher import fetch_ohlcv, PAIRS
from shared.indicators import atr, rsi
from shared.sr_engine import detect_sr_levels
from system_a_filter.strategies import run_all_strategies
from system_a_filter.ml_filter import compute_filter_features, FEATURE_NAMES, MODEL_PATH, SCALER_PATH


def build_training_data(
    pairs: list[str] = None,
    interval: str = "1h",
    limit: int = 500,
    tp_atr_mult: float = 2.5,
    sl_atr_mult: float = 2.0,
    max_horizon: int = 48,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Build labeled dataset from historical strategy signals.
    Label = 1 if TP hit before SL within horizon, else 0.
    """
    pairs = pairs or PAIRS[:10]  # Train on subset for speed
    all_X = []
    all_y = []

    data = fetch_ohlcv(pairs, interval, limit)

    for pair, df in data.items():
        if len(df) < 200:
            continue

        # Run strategies on historical slices
        for end_idx in range(250, len(df) - max_horizon, 10):
            slice_df = df.iloc[:end_idx].copy()
            future_df = df.iloc[end_idx:end_idx + max_horizon]

            signals = run_all_strategies(slice_df, pair)
            if not signals:
                continue

            sr_levels = detect_sr_levels(slice_df)
            atr_val = atr(slice_df["High"], slice_df["Low"], slice_df["Close"])

            for sig in signals:
                entry = sig["entry_price"]
                atr_now = float(atr_val.iloc[-1]) if len(atr_val) > 0 else entry * 0.02

                tp = entry + tp_atr_mult * atr_now
                sl = entry - sl_atr_mult * atr_now

                # Label via triple barrier on future data
                label = _triple_barrier_label(future_df, entry, tp, sl, sig.get("signal_type", "BUY"))

                features = compute_filter_features(sig, sr_levels, slice_df)
                all_X.append(features)
                all_y.append(label)

    if not all_X:
        return np.array([]), np.array([])

    return np.array(all_X), np.array(all_y)


def _triple_barrier_label(
    future_df: pd.DataFrame,
    entry: float,
    tp: float,
    sl: float,
    signal_type: str,
) -> int:
    """1 if TP hit first, 0 if SL hit first or neither."""
    for _, row in future_df.iterrows():
        if signal_type == "BUY":
            if row["Low"] <= sl:
                return 0
            if row["High"] >= tp:
                return 1
        else:
            if row["High"] >= sl:
                return 0
            if row["Low"] <= tp:
                return 1
    return 0  # horizon expired


def train():
    """Main training loop."""
    print("Building training data...")
    X, y = build_training_data()

    if len(X) < 100:
        print(f"Insufficient data: {len(X)} samples. Need 100+. Skipping training.")
        return

    print(f"Training on {len(X)} samples. Positive rate: {y.mean():.1%}")

    # Scale
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Walk-forward CV
    tscv = TimeSeriesSplit(n_splits=5)
    scores = []

    for fold, (train_idx, val_idx) in enumerate(tscv.split(X_scaled)):
        X_train, X_val = X_scaled[train_idx], X_scaled[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        model = XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.03,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.5,
            reg_lambda=2.0,
            scale_pos_weight=max(1, (y_train == 0).sum() / max(1, (y_train == 1).sum())),
            eval_metric="logloss",
            random_state=42,
        )
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
        score = model.score(X_val, y_val)
        scores.append(score)
        print(f"  Fold {fold + 1}: accuracy {score:.3f}")

    print(f"Mean CV accuracy: {np.mean(scores):.3f}")

    # Train final model on all data
    final_model = XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.03,
        subsample=0.8, colsample_bytree=0.8,
        reg_alpha=0.5, reg_lambda=2.0,
        scale_pos_weight=max(1, (y == 0).sum() / max(1, (y == 1).sum())),
        eval_metric="logloss", random_state=42,
    )
    final_model.fit(X_scaled, y, verbose=False)

    # Save
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(final_model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    print(f"Model saved to {MODEL_PATH}")


if __name__ == "__main__":
    train()
```

**Step 3: Commit**

```bash
git add ml_battleground/system_a_filter/ml_filter.py ml_battleground/system_a_filter/train_filter.py
git commit -m "feat(battleground/A): XGBoost context filter with heuristic fallback + training pipeline"
```

---

### Task 9: System A scanner (`system_a_filter/scanner.py`)

**Files:**
- Create: `ml_battleground/system_a_filter/scanner.py`

Main entry point. Fetches data → runs strategies → filters via ML → sets S/R TP/SL → validates existing picks → saves.

**Step 1: Write scanner.py**

```python
"""
System A Scanner: "The Filter"
Proven strategies → ML filter → S/R-based TP/SL
Run: python -m ml_battleground.system_a_filter.scanner
"""
import os
import sys
import json
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.data_fetcher import fetch_ohlcv, fetch_fear_greed, fetch_funding_rates, PAIRS
from shared.indicators import atr, rsi
from shared.sr_engine import detect_sr_levels, sr_based_tp_sl
from shared.risk_manager import can_open_trade, calculate_drawdown, position_size
from shared.cost_model import round_trip_cost
from shared.validator import validate_picks, save_picks, load_active, load_closed
from shared.performance import compute_stats
from system_a_filter.strategies import run_all_strategies
from system_a_filter.ml_filter import compute_filter_features, predict

SYSTEM_NAME = "system_a_filter"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
FILTER_THRESHOLD = 0.55  # minimum ML score to take a signal
VERSION = "1.0.0"


def scan():
    """Main scan cycle."""
    now = datetime.now(timezone.utc)
    print(f"[System A] Scan started at {now.isoformat()}")

    # Load existing state
    active = load_active(DATA_DIR)
    closed = load_closed(DATA_DIR)

    # Validate existing picks first
    active, newly_closed = validate_picks(active, SYSTEM_NAME, DATA_DIR)
    closed.extend(newly_closed)
    if newly_closed:
        print(f"  Closed {len(newly_closed)} picks: {[p['symbol'] for p in newly_closed]}")

    # Check if we can open new trades
    stats = compute_stats(closed)
    equity_curve = stats.get("equity_curve", [10000.0])
    dd = calculate_drawdown(equity_curve)
    can_trade, reason = can_open_trade(len(active), dd)

    if not can_trade:
        print(f"  Cannot open new trades: {reason}")
        save_picks(active, newly_closed, DATA_DIR)
        _write_dashboard_data(active, closed, stats)
        return

    # Fetch market context
    fear_greed = fetch_fear_greed()
    funding_rates = fetch_funding_rates()

    # Fetch OHLCV for both timeframes
    new_signals = []
    active_symbols = {p["symbol"] for p in active}

    for interval in ["15m", "1h"]:
        limit = 500 if interval == "1h" else 400
        data = fetch_ohlcv(PAIRS, interval, limit)

        for pair, df in data.items():
            if pair in active_symbols:
                continue  # already have a position
            if len(df) < 210:
                continue

            # Run 8 strategies
            signals = run_all_strategies(df, pair)
            if not signals:
                continue

            # Compute S/R levels
            sr_levels = detect_sr_levels(df)

            # ML filter each signal
            for sig in signals:
                sig["timeframe"] = interval
                features = compute_filter_features(
                    sig, sr_levels, df,
                    fear_greed=fear_greed,
                    funding_rate=funding_rates.get(pair, 0.0),
                )
                ml_score, method = predict(features)

                if ml_score < FILTER_THRESHOLD:
                    continue

                # Set S/R-based TP/SL
                atr_val = atr(df["High"], df["Low"], df["Close"])
                atr_now = float(atr_val.iloc[-1]) if len(atr_val) > 0 else sig["entry_price"] * 0.02

                tp, sl, tp_sl_method = sr_based_tp_sl(
                    sig["entry_price"], sr_levels, atr_now,
                    signal_type=sig.get("signal_type", "BUY"),
                )

                # Calculate R:R
                entry = sig["entry_price"]
                if sig.get("signal_type", "BUY") == "BUY":
                    risk = entry - sl
                    reward = tp - entry
                else:
                    risk = sl - entry
                    reward = entry - tp

                rr = reward / risk if risk > 0 else 0

                sig.update({
                    "take_profit": round(tp, 8),
                    "stop_loss": round(sl, 8),
                    "risk_reward": round(rr, 2),
                    "ml_score": round(ml_score, 4),
                    "ml_method": method,
                    "tp_sl_method": tp_sl_method,
                    "confidence": round(sig.get("confidence", 0.5) * ml_score, 4),
                    "timestamp": now.isoformat(),
                    "system": SYSTEM_NAME,
                    "version": VERSION,
                    "fear_greed": fear_greed,
                    "funding_rate": funding_rates.get(pair, 0.0),
                })

                new_signals.append(sig)
                active_symbols.add(pair)

    # Sort by combined confidence, take top N that fit risk budget
    new_signals.sort(key=lambda s: s.get("confidence", 0), reverse=True)

    added = 0
    for sig in new_signals:
        can, reason = can_open_trade(len(active), dd)
        if not can:
            break
        active.append(sig)
        added += 1
        print(f"  NEW: {sig['symbol']} {sig['signal_type']} via {sig['strategy']} "
              f"(ML:{sig['ml_score']:.2f}, R:R:{sig['risk_reward']:.1f}, TP/SL:{sig['tp_sl_method']})")

    print(f"  Active: {len(active)} | Closed: {len(closed)} | New: {added}")
    print(f"  Stats: WR={stats.get('win_rate', 0):.1%} Sharpe={stats.get('sharpe', 0):.2f} DD={dd:.1%}")

    # Save everything
    save_picks(active, newly_closed, DATA_DIR)
    _write_dashboard_data(active, closed, stats)
    print(f"[System A] Scan complete.")


def _write_dashboard_data(active: list, closed: list, stats: dict):
    """Write JSON data for dashboard consumption."""
    dashboard_data = {
        "system": "The Filter",
        "version": VERSION,
        "updated": datetime.now(timezone.utc).isoformat(),
        "active_picks": active,
        "stats": {k: v for k, v in stats.items() if k != "equity_curve"},
        "equity_curve": stats.get("equity_curve", []),
        "total_closed": len(closed),
        "recent_closed": closed[-20:] if closed else [],
    }
    with open(os.path.join(DATA_DIR, "dashboard.json"), "w") as f:
        json.dump(dashboard_data, f, indent=2, default=str)


if __name__ == "__main__":
    scan()
```

**Step 2: Commit**

```bash
git add ml_battleground/system_a_filter/scanner.py
git commit -m "feat(battleground/A): main scanner — strategies → ML filter → S/R TP/SL → validate"
```

---

### Task 10: System A dashboard (`system_a_filter/index.html`)

**Files:**
- Create: `ml_battleground/system_a_filter/index.html`

Dark-themed "Superpowers: The Filter" dashboard. Reads `data/dashboard.json` from GitHub raw URL. Shows: active picks with S/R levels, ML filter stats, strategy breakdown, equity curve, performance metrics.

**Step 1: Write index.html**

Single-file HTML+CSS+JS dashboard (~500 lines). Dark theme (#0a0a12 background), auto-refreshes every 60s.

Key sections:
- Header: "SUPERPOWERS: THE FILTER" with version badge
- Stats bar: WR, Sharpe, Trades, Max DD, Active Count
- Active picks table: Symbol, Strategy, Entry, TP, SL, R:R, ML Score, TP/SL Method, Unrealized P&L
- Recent closed trades table: Symbol, Strategy, Entry, Exit, P&L, Exit Reason
- Strategy breakdown: Per-strategy WR and trade count
- Equity curve chart (canvas-based, no external deps)
- Validation gate progress bar (towards 50-trade "proven" status)

**Step 2: Commit**

```bash
git add ml_battleground/system_a_filter/index.html
git commit -m "feat(battleground/A): Superpowers: The Filter dashboard"
```

---

## Phase 3: System B — "The Regime"

### Task 11: System B regime classifier (`system_b_regime/regime_classifier.py`)

**Files:**
- Create: `ml_battleground/system_b_regime/regime_classifier.py`

XGBoost multi-class classifier (4 regimes: trending_up, trending_down, range_bound, high_volatility). Falls back to rule-based regime detection when no trained model exists.

Key logic:
- Features: ADX, +DI, -DI, EMA slope, BB width percentile, ATR percentile, Hurst exponent, volume trend, fear_greed, price vs EMA50/200, realized vol percentile (~15 features)
- Rule-based labeler for training data: ADX>25 + price>EMA50 = trending_up, ADX>25 + price<EMA50 = trending_down, ADX<20 + low BB width = range_bound, ATR>80th pctl = high_vol
- Walk-forward training on 500 bars of 1h data per pair

**Step 1: Write regime_classifier.py**

**Step 2: Commit**

```bash
git add ml_battleground/system_b_regime/regime_classifier.py
git commit -m "feat(battleground/B): regime classifier with rule-based fallback"
```

---

### Task 12: System B strategy router (`system_b_regime/strategy_router.py`)

**Files:**
- Create: `ml_battleground/system_b_regime/strategy_router.py`

Maps each regime to 3-4 strategies with regime-specific ATR TP/SL multipliers.

- trending_up → supertrend_follow, ema_stack, rsi_macd_confluence (TP 3.5× ATR, SL 1.5× ATR)
- trending_down → swing_failure_pattern (SELL), volume_climax_reversal (SELL) (TP 3.0× ATR, SL 1.5× ATR)
- range_bound → ornstein_uhlenbeck, connors_rsi2, bollinger_keltner_squeeze (TP 1.5× ATR, SL 1.0× ATR)
- high_volatility → bollinger_keltner_squeeze only, half position size (TP 2.0× ATR, SL 2.5× ATR)

**Step 1: Write strategy_router.py**

**Step 2: Commit**

```bash
git add ml_battleground/system_b_regime/strategy_router.py
git commit -m "feat(battleground/B): strategy router mapping regime to strategy+TP/SL"
```

---

### Task 13: System B scanner + training (`system_b_regime/scanner.py`, `train_regime.py`)

**Files:**
- Create: `ml_battleground/system_b_regime/scanner.py`
- Create: `ml_battleground/system_b_regime/train_regime.py`

Scanner: classify regime → route to strategies → set ATR TP/SL → validate existing picks → save.

**Step 1: Write scanner.py and train_regime.py**

**Step 2: Commit**

```bash
git add ml_battleground/system_b_regime/scanner.py ml_battleground/system_b_regime/train_regime.py
git commit -m "feat(battleground/B): scanner and regime training pipeline"
```

---

### Task 14: System B dashboard (`system_b_regime/index.html`)

**Files:**
- Create: `ml_battleground/system_b_regime/index.html`

"Superpowers: The Regime" dashboard. Same dark theme. Unique elements: regime indicator with confidence bar, regime timeline (color-coded 7-day history), per-regime stats.

**Step 1: Write index.html**

**Step 2: Commit**

```bash
git add ml_battleground/system_b_regime/index.html
git commit -m "feat(battleground/B): Superpowers: The Regime dashboard"
```

---

## Phase 4: System C — "The Neural Net"

### Task 15: System C model architecture (`system_c_deeplearn/model_arch.py`)

**Files:**
- Create: `ml_battleground/system_c_deeplearn/model_arch.py`

GRU-Attention model with 3 output heads (entry probability, TP distance, SL distance).

```python
"""
GRU-Attention architecture for System C.
Input: 200 bars × 16 features × 2 timeframes
Output: entry_prob (sigmoid), tp_dist (linear), sl_dist (linear)
"""
import torch
import torch.nn as nn


class GRUAttentionModel(nn.Module):
    def __init__(
        self,
        input_size: int = 16,
        hidden_size: int = 128,
        num_layers: int = 2,
        n_heads: int = 4,
        dropout: float = 0.3,
    ):
        super().__init__()

        # GRU for each timeframe
        self.gru_15m = nn.GRU(input_size, hidden_size, num_layers,
                              batch_first=True, dropout=dropout)
        self.gru_1h = nn.GRU(input_size, hidden_size, num_layers,
                             batch_first=True, dropout=dropout)

        # Multi-head self-attention on concatenated hidden states
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_size * 2,
            num_heads=n_heads,
            dropout=dropout,
            batch_first=True,
        )
        self.layer_norm = nn.LayerNorm(hidden_size * 2)

        # Output heads
        self.fc = nn.Sequential(
            nn.Linear(hidden_size * 2, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        self.head_entry = nn.Linear(64, 1)   # sigmoid for probability
        self.head_tp = nn.Linear(64, 1)      # linear, ATR units
        self.head_sl = nn.Linear(64, 1)      # linear, ATR units

    def forward(self, x_15m, x_1h):
        """
        x_15m: (batch, seq_len, input_size)  — 200 bars of 15m
        x_1h:  (batch, seq_len, input_size)  — 200 bars of 1h
        """
        out_15m, _ = self.gru_15m(x_15m)  # (batch, seq, hidden)
        out_1h, _ = self.gru_1h(x_1h)

        # Take last hidden state from each
        h_15m = out_15m[:, -1, :]  # (batch, hidden)
        h_1h = out_1h[:, -1, :]

        # Concatenate
        combined = torch.cat([h_15m, h_1h], dim=-1)  # (batch, hidden*2)
        combined = combined.unsqueeze(1)  # (batch, 1, hidden*2) for attention

        # Self-attention
        attn_out, attn_weights = self.attention(combined, combined, combined)
        combined = self.layer_norm(combined + attn_out)
        combined = combined.squeeze(1)  # (batch, hidden*2)

        # Shared trunk
        features = self.fc(combined)

        # 3 heads
        entry_prob = torch.sigmoid(self.head_entry(features))
        tp_dist = torch.relu(self.head_tp(features)) + 0.5  # min 0.5 ATR
        sl_dist = torch.relu(self.head_sl(features)) + 0.5

        return entry_prob.squeeze(-1), tp_dist.squeeze(-1), sl_dist.squeeze(-1), attn_weights
```

**Step 1: Write model_arch.py**

**Step 2: Commit**

```bash
git add ml_battleground/system_c_deeplearn/model_arch.py
git commit -m "feat(battleground/C): GRU-Attention model architecture"
```

---

### Task 16: System C training pipeline (`system_c_deeplearn/train_model.py`)

**Files:**
- Create: `ml_battleground/system_c_deeplearn/train_model.py`

Training on 6-month rolling window. Multi-task loss: BCE(entry) + MSE(TP) + MSE(SL). Purged walk-forward. Saves model to `models/gru_attention.pt`.

**Step 1: Write train_model.py**

**Step 2: Commit**

```bash
git add ml_battleground/system_c_deeplearn/train_model.py
git commit -m "feat(battleground/C): training pipeline with walk-forward + multi-task loss"
```

---

### Task 17: System C scanner (`system_c_deeplearn/scanner.py`)

**Files:**
- Create: `ml_battleground/system_c_deeplearn/scanner.py`

Loads trained model → feeds 200 bars of 15m + 1h → entry probability > 0.65 → convert TP/SL from ATR units → validate → save.

Falls back to "no signals" if model not yet trained (no fake data).

**Step 1: Write scanner.py**

**Step 2: Commit**

```bash
git add ml_battleground/system_c_deeplearn/scanner.py
git commit -m "feat(battleground/C): scanner with model inference and ATR TP/SL conversion"
```

---

### Task 18: System C dashboard (`system_c_deeplearn/index.html`)

**Files:**
- Create: `ml_battleground/system_c_deeplearn/index.html`

"Superpowers: The Neural Net" dashboard. Unique elements: confidence heatmap (pairs × entry probability), model diagnostics section, attention weights visualization.

**Step 1: Write index.html**

**Step 2: Commit**

```bash
git add ml_battleground/system_c_deeplearn/index.html
git commit -m "feat(battleground/C): Superpowers: The Neural Net dashboard"
```

---

## Phase 5: Arena + GitHub Actions

### Task 19: Arena meta-dashboard (`arena.html`)

**Files:**
- Create: `ml_battleground/arena.html`

"Superpowers Arena" — head-to-head comparison of all 3 systems. Reads dashboard.json from each system's data/ directory.

Key sections:
- Comparison table: WR, Sharpe, Total Return, Max DD, Trades, Status (proven/pending)
- Overlaid equity curves (3 lines, one canvas)
- Current picks comparison: shows where systems agree
- "Winner" badge auto-awarded to best risk-adjusted performer after 50+ trades
- Consensus signals section: pairs where 2+ systems agree

**Step 1: Write arena.html**

**Step 2: Commit**

```bash
git add ml_battleground/arena.html
git commit -m "feat(battleground): Superpowers Arena meta-dashboard"
```

---

### Task 20: GitHub Actions workflows

**Files:**
- Create: `.github/workflows/ml-battleground-a.yml`
- Create: `.github/workflows/ml-battleground-b.yml`
- Create: `.github/workflows/ml-battleground-c.yml`

Each workflow: checkout → setup python → pip install → run scanner → commit data + dashboard → push.

**Step 1: Write ml-battleground-a.yml**

```yaml
name: "ML Battleground - System A (The Filter)"
on:
  schedule:
    - cron: "*/15 * * * *"
  workflow_dispatch:

permissions:
  contents: write

jobs:
  scan:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: pip install -r ml_battleground/requirements.txt
      - name: Run System A scanner
        run: python -m ml_battleground.system_a_filter.scanner
        env:
          PYTHONPATH: ml_battleground
      - name: Commit results
        run: |
          git config user.name "ML Battleground Bot"
          git config user.email "bot@findtorontoevents.ca"
          git add ml_battleground/system_a_filter/data/
          git diff --cached --quiet || git commit -m "System A scan $(date -u +%Y-%m-%dT%H:%M:%SZ)"
          git pull --rebase origin main
          git push origin main
```

**Step 2: Write ml-battleground-b.yml** (same pattern, `*/30` cron, System B)

**Step 3: Write ml-battleground-c.yml** (same pattern, `*/15` cron, System C)

**Step 4: Commit**

```bash
git add .github/workflows/ml-battleground-a.yml .github/workflows/ml-battleground-b.yml .github/workflows/ml-battleground-c.yml
git commit -m "feat(battleground): GitHub Actions workflows for all 3 systems"
```

---

### Task 21: Deploy dashboards

**Files:**
- Modify: `.github/workflows/deploy-riseoftheclaw.yml` (or create new deploy workflow)

Add the 4 dashboard HTML files (system_a/index.html, system_b/index.html, system_c/index.html, arena.html) to the GitHub Pages deployment.

**Step 1: Add dashboard files to existing deploy workflow**

**Step 2: Verify deployment**

Expected URLs (GitHub Pages):
- `https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/ml_battleground/system_a_filter/`
- `https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/ml_battleground/system_b_regime/`
- `https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/ml_battleground/system_c_deeplearn/`
- `https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/ml_battleground/arena.html`

**Step 3: Commit**

```bash
git add .github/workflows/
git commit -m "feat(battleground): deploy dashboards to GitHub Pages"
```

---

### Task 22: Initial training run + first scan

**Step 1:** Run System A training locally:
```bash
python -m ml_battleground.system_a_filter.train_filter
```

**Step 2:** Run System B training locally:
```bash
python -m ml_battleground.system_b_regime.train_regime
```

**Step 3:** Run System C training locally:
```bash
python -m ml_battleground.system_c_deeplearn.train_model
```

**Step 4:** Run all 3 scanners once:
```bash
python -m ml_battleground.system_a_filter.scanner
python -m ml_battleground.system_b_regime.scanner
python -m ml_battleground.system_c_deeplearn.scanner
```

**Step 5:** Verify data files created in each system's `data/` directory

**Step 6:** Commit trained models + initial data:
```bash
git add ml_battleground/
git commit -m "feat(battleground): initial training + first scan results"
```

---

### Task 23: Update updates page

**Files:**
- Modify: `updates/index.html` (INSERT ONLY at top of February 2026 section)

Add entry documenting the ML Battleground launch with all 3 systems and the Arena.

**Step 1: Insert new entry** (following the exact format from MEMORY.md)

**Step 2: Commit**

```bash
git add updates/index.html
git commit -m "docs: add ML Battleground launch to updates page"
```

---

## Summary: 23 Tasks across 5 Phases

| Phase | Tasks | Description |
|-------|-------|-------------|
| 1: Shared Infrastructure | 1-6 | Directory structure, data fetcher, indicators, S/R engine, risk/cost/perf, validator |
| 2: System A (The Filter) | 7-10 | 8 strategies, ML filter + training, scanner, dashboard |
| 3: System B (The Regime) | 11-14 | Regime classifier, strategy router, scanner + training, dashboard |
| 4: System C (The Neural Net) | 15-18 | GRU-Attention model, training, scanner, dashboard |
| 5: Arena + Deploy | 19-23 | Arena dashboard, 3 GitHub Actions, deployment, training, updates page |

**Estimated complexity:** ~3,500-4,000 lines of Python + ~2,000 lines of HTML/CSS/JS across 4 dashboards.
