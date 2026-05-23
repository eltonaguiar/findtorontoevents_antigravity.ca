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
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "LTCUSDT",
    # Tier 2 (alt L1 + AI narrative)
    # Rotated Feb 26 2026: DOT → TAO (AI narrative momentum)
    "ADAUSDT", "TAOUSDT", "AVAXUSDT", "LINKUSDT", "NEARUSDT",
    "SUIUSDT", "APTUSDT",
    # Tier 3 (mid-cap)
    "DOGEUSDT", "ARBUSDT", "OPUSDT", "INJUSDT", "FETUSDT",
    "TIAUSDT", "SEIUSDT", "FILUSDT",
    # Tier 4 (new additions — Mar 19 2026)
    "ETHFIUSDT", "QNTUSDT", "DEXEUSDT", "ENJUSDT", "THEUSDT",
    "PIXELUSDT", "ANKRUSDT", "HOTUSDT", "SAHARAUSDT",
]

_BINANCE_BASES = [
    "https://api.binance.com",
    "https://data-api.binance.vision",
    "https://api.binance.us",
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
    for base in _BINANCE_BASES:
        try:
            url = f"{base}/api/v3/klines"
            resp = requests.get(url, params={"symbol": pair, "interval": interval, "limit": limit}, timeout=10)
            if resp.status_code in (451, 403):
                continue  # geo-blocked, try next
            resp.raise_for_status()
            data = resp.json()
            if not data:
                continue
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
            continue
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
    """Fetch current Fear & Greed Index (0-100).

    Failover chain: alternative.me → CoinGecko BTC 24h proxy → cached value.
    """
    import time as _time
    # Source 1: alternative.me (primary, free, no key) — with retry
    for _attempt in range(3):
        try:
            resp = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5)
            val = int(resp.json()["data"][0]["value"])
            _fg_cache["last"] = val
            return val
        except Exception:
            if _attempt < 2:
                _time.sleep(2 * (_attempt + 1))

    # Source 2: Derive F&G proxy from BTC 24h change via CoinGecko — with retry
    # Heuristic: BTC -10% ≈ F&G 10, BTC +10% ≈ F&G 80
    for _attempt in range(2):
        try:
            resp = requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "bitcoin", "vs_currencies": "usd", "include_24hr_change": "true"},
                timeout=8,
            )
            change = float(resp.json()["bitcoin"]["usd_24h_change"])
            # Linear map: -10% → 10, 0% → 50, +10% → 90, clamped [5, 95]
            proxy = int(max(5, min(95, 50 + change * 4)))
            print(f"  [F&G fallback] CoinGecko BTC proxy: {proxy} (BTC 24h={change:+.1f}%)")
            return proxy
        except Exception:
            if _attempt < 1:
                _time.sleep(3)

    # Source 3: Stale cache
    if "last" in _fg_cache:
        print(f"  [F&G fallback] Using cached value: {_fg_cache['last']}")
        return _fg_cache["last"]

    return 50  # neutral default

_fg_cache: dict = {}


def fetch_fear_greed_history(days: int = 7) -> list[int]:
    """Fetch last N days of Fear & Greed Index values with retry.
    Returns list of integers [oldest, ..., newest]."""
    import time as _time
    for attempt in range(3):
        try:
            resp = requests.get(f"https://api.alternative.me/fng/?limit={days}", timeout=5)
            data = resp.json().get("data", [])
            # API returns newest first, reverse to oldest first
            return [int(d["value"]) for d in reversed(data)]
        except Exception:
            if attempt < 2:
                _time.sleep(2 * (attempt + 1))
    return []


def fear_greed_persistence(history: list[int], threshold_low: int = 25, threshold_high: int = 75, min_days: int = 3) -> dict:
    """Check if F&G has been persistently extreme for min_days.

    Returns dict with:
        - extreme_fear: True if F&G <= threshold_low for min_days consecutive days
        - extreme_greed: True if F&G >= threshold_high for min_days consecutive days
        - fear_days: number of consecutive days at or below threshold_low (from most recent)
        - greed_days: number of consecutive days at or above threshold_high (from most recent)
        - persistent: True if either extreme is persistent
        - direction: "BUY" if persistent fear, "SELL" if persistent greed, None otherwise
    """
    if len(history) < min_days:
        return {"extreme_fear": False, "extreme_greed": False, "fear_days": 0, "greed_days": 0, "persistent": False, "direction": None}

    # Count consecutive extreme days from most recent backward
    fear_days = 0
    for val in reversed(history):
        if val <= threshold_low:
            fear_days += 1
        else:
            break

    greed_days = 0
    for val in reversed(history):
        if val >= threshold_high:
            greed_days += 1
        else:
            break

    extreme_fear = fear_days >= min_days
    extreme_greed = greed_days >= min_days

    direction = None
    if extreme_fear:
        direction = "BUY"
    elif extreme_greed:
        direction = "SELL"

    return {
        "extreme_fear": extreme_fear,
        "extreme_greed": extreme_greed,
        "fear_days": fear_days,
        "greed_days": greed_days,
        "persistent": extreme_fear or extreme_greed,
        "direction": direction,
    }


def fetch_funding_rates(pairs: Optional[list[str]] = None) -> dict[str, float]:
    """Fetch perpetual funding rates with Binance → OKX → Bybit fallback."""
    pairs = pairs or PAIRS
    result = {}

    # Try Binance Futures first
    try:
        resp = requests.get(f"{BINANCE_BASE.replace('api', 'fapi')}/fapi/v1/premiumIndex", timeout=10)
        resp.raise_for_status()
        for item in resp.json():
            sym = item.get("symbol", "")
            if sym in pairs:
                result[sym] = float(item.get("lastFundingRate", 0))
    except Exception:
        pass

    # Fallback to OKX if Binance returned nothing (geo-blocked on GitHub Actions)
    if not result:
        try:
            resp = requests.get(f"{OKX_BASE}/api/v5/public/funding-rate", timeout=10)
            resp.raise_for_status()
            for item in resp.json().get("data", []):
                inst_id = item.get("instId", "")
                sym = inst_id.replace("-", "")  # BTC-USDT-SWAP → BTCUSDTSWAP
                sym = sym.replace("SWAP", "")   # → BTCUSDT
                if sym in pairs:
                    result[sym] = float(item.get("fundingRate", 0))
        except Exception:
            pass

    # Fallback to Bybit
    if not result:
        try:
            resp = requests.get(
                f"{BYBIT_BASE}/v5/market/tickers",
                params={"category": "linear"},
                timeout=10,
            )
            resp.raise_for_status()
            for item in resp.json().get("result", {}).get("list", []):
                sym = item.get("symbol", "")
                if sym in pairs and "fundingRate" in item:
                    result[sym] = float(item["fundingRate"])
        except Exception:
            pass

    return result


def fetch_btc_price() -> float:
    """Quick BTC price fetch with Binance → OKX → Bybit → CoinGecko failover."""
    # 1. Binance
    try:
        resp = requests.get(f"{BINANCE_BASE}/api/v3/ticker/price", params={"symbol": "BTCUSDT"}, timeout=5)
        if resp.ok:
            return float(resp.json()["price"])
    except Exception:
        pass
    # 2. OKX
    try:
        resp = requests.get(f"{OKX_BASE}/api/v5/market/ticker", params={"instId": "BTC-USDT"}, timeout=5)
        if resp.ok:
            data = resp.json().get("data", [])
            if data:
                return float(data[0]["last"])
    except Exception:
        pass
    # 3. Bybit
    try:
        resp = requests.get(f"{BYBIT_BASE}/v5/market/tickers",
                            params={"category": "spot", "symbol": "BTCUSDT"}, timeout=5)
        if resp.ok:
            items = resp.json().get("result", {}).get("list", [])
            if items:
                return float(items[0]["lastPrice"])
    except Exception:
        pass
    # 4. CoinGecko
    try:
        resp = requests.get("https://api.coingecko.com/api/v3/simple/price",
                            params={"ids": "bitcoin", "vs_currencies": "usd"}, timeout=8)
        if resp.ok:
            return float(resp.json()["bitcoin"]["usd"])
    except Exception:
        pass
    return 0.0
