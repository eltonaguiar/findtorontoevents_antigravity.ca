"""
Order Book Imbalance (OBI) Fetcher
===================================
Fetches Binance order book depth and computes imbalance metrics.
Based on: "82.68% direction accuracy" (2024 microstructure study, 5.6M observations).

Uses REST API snapshots (not WebSocket) for compatibility with hourly GitHub Actions.
For each symbol: fetches 20-level depth, computes OBI, stores to JSON cache.
"""

import requests
import json
import time
import numpy as np
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

CACHE_DIR = Path(__file__).resolve().parent / "data" / "orderbook_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


# Binance spot mirrors. api.binance.com is geo-blocked (HTTP 451) from GitHub
# runners; data-api.binance.vision is the public-data mirror and is NOT
# geo-blocked, binance.us is the US-accessible exchange. Per CLAUDE.md API
# Failover Rule, never rely on a single endpoint.
BINANCE_DEPTH_BASES = [
    "https://data-api.binance.vision",  # public data API — not geo-blocked
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api.binance.us",
]


def _fetch_orderbook_kucoin(symbol: str, levels: int) -> Dict:
    """Failover: KuCoin order book. Symbol BTCUSDT -> BTC-USDT."""
    if symbol.endswith("USDT"):
        ku_sym = f"{symbol[:-4]}-USDT"
    else:
        ku_sym = symbol
    # KuCoin level2_20 returns top-20 depth (use level2_100 for deeper).
    endpoint = "level2_20" if levels <= 20 else "level2_100"
    r = requests.get(
        f"https://api.kucoin.com/api/v1/market/orderbook/{endpoint}",
        params={"symbol": ku_sym}, timeout=10)
    r.raise_for_status()
    data = (r.json() or {}).get("data") or {}
    return {"bids": data.get("bids", [])[:levels],
            "asks": data.get("asks", [])[:levels]}


def fetch_orderbook_snapshot(symbol: str = "BTCUSDT", levels: int = 20) -> Dict:
    """
    Fetch order book snapshot with multi-endpoint failover.

    Tries Binance spot mirrors in order; HTTP 451 (geo-block) is treated as
    "endpoint dead -> fall through", NOT a fatal error. If every Binance
    mirror is geo-blocked, falls back to KuCoin. Returns empty bids/asks only
    when all providers fail.
    """
    for base in BINANCE_DEPTH_BASES:
        try:
            r = requests.get(f"{base}/api/v3/depth",
                             params={"symbol": symbol, "limit": levels}, timeout=10)
            if r.status_code in (451, 403):
                # Geo-blocked — endpoint dead, try next provider.
                continue
            r.raise_for_status()
            ob = r.json()
            if ob.get("bids") and ob.get("asks"):
                return ob
        except Exception as e:
            print(f"[OBI] {symbol} depth via {base} failed: {e}")
            continue

    # All Binance mirrors exhausted/geo-blocked — fall through to KuCoin.
    try:
        ob = _fetch_orderbook_kucoin(symbol, levels)
        if ob.get("bids") and ob.get("asks"):
            print(f"[OBI] {symbol}: served from KuCoin failover")
            return ob
    except Exception as e:
        print(f"[OBI] {symbol} depth via KuCoin failover failed: {e}")

    print(f"[OBI] Failed to fetch {symbol} depth from all providers")
    return {"bids": [], "asks": []}


def compute_obi_features(orderbook: Dict) -> Dict[str, float]:
    """
    Compute Order Book Imbalance features from a depth snapshot.

    Features:
    - obi_1: Imbalance at best bid/ask (level 1)
    - obi_5: Imbalance across top 5 levels
    - obi_10: Imbalance across top 10 levels
    - obi_20: Imbalance across top 20 levels
    - bid_depth_total: Total bid volume
    - ask_depth_total: Total ask volume
    - spread_bps: Bid-ask spread in basis points
    - depth_ratio: bid_total / ask_total
    - weighted_mid: Volume-weighted mid price
    - imbalance_gradient: OBI change across depth levels (5 vs 20)
    """
    bids = orderbook.get("bids", [])
    asks = orderbook.get("asks", [])

    if not bids or not asks:
        return {k: 0.0 for k in ["obi_1", "obi_5", "obi_10", "obi_20",
                                   "bid_depth_total", "ask_depth_total",
                                   "spread_bps", "depth_ratio", "weighted_mid",
                                   "imbalance_gradient"]}

    # Parse price/quantity pairs
    bid_prices = np.array([float(b[0]) for b in bids])
    bid_qtys = np.array([float(b[1]) for b in bids])
    ask_prices = np.array([float(a[0]) for a in asks])
    ask_qtys = np.array([float(a[1]) for a in asks])

    features = {}

    # OBI at various depths: (bid_vol - ask_vol) / (bid_vol + ask_vol)
    for n, key in [(1, "obi_1"), (5, "obi_5"), (10, "obi_10"), (20, "obi_20")]:
        bv = bid_qtys[:n].sum() if len(bid_qtys) >= n else bid_qtys.sum()
        av = ask_qtys[:n].sum() if len(ask_qtys) >= n else ask_qtys.sum()
        total = bv + av
        features[key] = (bv - av) / total if total > 0 else 0.0

    # Total depth
    features["bid_depth_total"] = float(bid_qtys.sum())
    features["ask_depth_total"] = float(ask_qtys.sum())

    # Spread in basis points
    best_bid = bid_prices[0] if len(bid_prices) > 0 else 0.0
    best_ask = ask_prices[0] if len(ask_prices) > 0 else 0.0
    mid = (best_bid + best_ask) / 2 if (best_bid + best_ask) > 0 else 1.0
    features["spread_bps"] = (best_ask - best_bid) / mid * 10000

    # Depth ratio
    total_ask = float(ask_qtys.sum())
    features["depth_ratio"] = float(bid_qtys.sum()) / total_ask if total_ask > 0 else 1.0

    # Volume-weighted mid price
    bid_vwap = np.sum(bid_prices[:5] * bid_qtys[:5]) / max(bid_qtys[:5].sum(), 1e-10)
    ask_vwap = np.sum(ask_prices[:5] * ask_qtys[:5]) / max(ask_qtys[:5].sum(), 1e-10)
    features["weighted_mid"] = (bid_vwap + ask_vwap) / 2

    # Imbalance gradient: how OBI changes with depth
    features["imbalance_gradient"] = features["obi_5"] - features["obi_20"]

    return features


def fetch_and_cache_obi(symbols: List[str], prefix: str = "ext_obi") -> Dict[str, Dict[str, float]]:
    """
    Fetch OBI for multiple symbols, cache results.
    Returns {symbol: {feature_name: value}}.
    """
    results = {}
    timestamp = datetime.now(timezone.utc).isoformat()

    for i, symbol in enumerate(symbols):
        ob = fetch_orderbook_snapshot(symbol)
        features = compute_obi_features(ob)
        # Prefix features
        prefixed = {f"{prefix}_{k}": v for k, v in features.items()}
        prefixed[f"{prefix}_timestamp"] = timestamp
        results[symbol] = prefixed

        # Rate limit: Binance allows 1200 req/min for depth
        if (i + 1) % 20 == 0:
            time.sleep(1)

    # Cache
    cache_file = CACHE_DIR / "latest_obi.json"
    with open(cache_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    return results


def get_cached_obi(symbol: str) -> Dict[str, float]:
    """Read cached OBI features for a symbol."""
    cache_file = CACHE_DIR / "latest_obi.json"
    if not cache_file.exists():
        return {}
    try:
        age_h = (time.time() - cache_file.stat().st_mtime) / 3600
        if age_h > 2.0:  # stale after 2 hours
            return {}
        with open(cache_file) as f:
            data = json.load(f)
        return data.get(symbol, {})
    except Exception:
        return {}


if __name__ == "__main__":
    # Test: fetch BTC order book and compute OBI
    print("Fetching BTCUSDT order book...")
    ob = fetch_orderbook_snapshot("BTCUSDT", 20)
    features = compute_obi_features(ob)
    print(f"\nOrder Book Imbalance Features:")
    for k, v in features.items():
        print(f"  {k}: {v:.6f}")
