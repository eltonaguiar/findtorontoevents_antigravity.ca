#!/usr/bin/env python3
"""
Dynamic Universe Scanner
========================
Fetches ALL USDT perpetual pairs from Binance Futures, filters for tradeable
pairs, ranks by momentum + volume spike + volatility, and returns the top 50
"hottest" symbols. These supplement (never replace) the core static symbols
from config.py.

Output: data/dynamic_universe.json
  {
    "updated_at": "2026-03-18T19:00:00Z",
    "core_count": 96,
    "dynamic_count": 50,
    "total_unique": 80,
    "core_symbols": ["BTCUSDT", ...],
    "dynamic_symbols": ["XYZUSDT", ...],
    "merged_symbols": ["BTCUSDT", "XYZUSDT", ...],
    "rankings": [{"symbol": "XYZUSDT", "score": 0.87, ...}, ...]
  }

API failover: Uses Binance mirrors -> Bybit -> CoinGecko (per project rules).

Usage:
  python -m alpha_engine.dynamic_universe          # standalone
  python alpha_engine/dynamic_universe.py           # direct
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Ensure local imports work
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import CRYPTO_SYMBOLS, DATA_DIR, FAPI_BASES, SPOT_BASES

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("dynamic_universe")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MIN_DAILY_VOLUME_USD = 1_000_000    # $1M minimum 24h volume
MIN_PRICE = 0.001                    # Filter out sub-penny dust
TOP_N_DYNAMIC = 50                   # Pick top 50 hottest non-core symbols
OUTPUT_PATH = DATA_DIR / "dynamic_universe.json"

# Bybit fallback for when Binance futures is geo-blocked (GitHub Actions)
BYBIT_TICKERS_URL = "https://api.bybit.com/v5/market/tickers?category=linear"


# ---------------------------------------------------------------------------
# API Fetching with failover (respects project API failover rule: 3+ fallback)
# ---------------------------------------------------------------------------
def _http_get_json(url: str, timeout: int = 15) -> dict | list | None:
    """Fetch JSON with User-Agent header."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "AlphaEngine/2.0",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def fetch_all_futures_tickers() -> list[dict]:
    """Fetch 24hr ticker data for ALL Binance USDT perpetual pairs.

    Failover chain: Binance fapi mirrors -> Bybit -> empty list.
    Returns normalized list of dicts with: symbol, price, volume_usd,
    price_change_pct, high, low.
    """
    # Try Binance futures endpoints (multiple mirrors)
    for base in FAPI_BASES:
        url = f"{base}/fapi/v1/ticker/24hr"
        data = _http_get_json(url, timeout=20)
        if data and isinstance(data, list) and len(data) > 50:
            log.info(f"  Fetched {len(data)} futures tickers from {base}")
            return _normalize_binance_tickers(data)

    # Fallback: Bybit linear perpetuals
    log.info("  Binance futures blocked, trying Bybit fallback...")
    data = _http_get_json(BYBIT_TICKERS_URL, timeout=20)
    if data and isinstance(data, dict):
        tickers = data.get("result", {}).get("list", [])
        if tickers:
            log.info(f"  Fetched {len(tickers)} linear tickers from Bybit")
            return _normalize_bybit_tickers(tickers)

    # Fallback: Binance spot (not futures, but better than nothing)
    for base in SPOT_BASES:
        url = f"{base}/api/v3/ticker/24hr"
        data = _http_get_json(url, timeout=20)
        if data and isinstance(data, list) and len(data) > 50:
            log.info(f"  Fetched {len(data)} spot tickers from {base} (spot fallback)")
            return _normalize_binance_spot_tickers(data)

    log.warning("  All ticker endpoints failed!")
    return []


def _normalize_binance_tickers(data: list[dict]) -> list[dict]:
    """Normalize Binance futures 24hr ticker response."""
    result = []
    for t in data:
        sym = t.get("symbol", "")
        if not sym.endswith("USDT"):
            continue
        # Skip margin/index tokens
        if "_" in sym or sym.endswith("USDT_PERP"):
            continue
        try:
            price = float(t.get("lastPrice", 0))
            vol_usd = float(t.get("quoteVolume", 0))
            pct_change = float(t.get("priceChangePercent", 0))
            high = float(t.get("highPrice", 0))
            low = float(t.get("lowPrice", 0))
            result.append({
                "symbol": sym,
                "price": price,
                "volume_usd": vol_usd,
                "price_change_pct": pct_change,
                "high": high,
                "low": low,
            })
        except (ValueError, TypeError):
            continue
    return result


def _normalize_bybit_tickers(data: list[dict]) -> list[dict]:
    """Normalize Bybit v5 linear ticker response to our format."""
    result = []
    for t in data:
        sym = t.get("symbol", "")
        if not sym.endswith("USDT"):
            continue
        try:
            price = float(t.get("lastPrice", 0))
            vol_usd = float(t.get("turnover24h", 0))
            pct_change = float(t.get("price24hPcnt", 0)) * 100  # Bybit uses decimal
            high = float(t.get("highPrice24h", 0))
            low = float(t.get("lowPrice24h", 0))
            result.append({
                "symbol": sym,
                "price": price,
                "volume_usd": vol_usd,
                "price_change_pct": pct_change,
                "high": high,
                "low": low,
            })
        except (ValueError, TypeError):
            continue
    return result


def _normalize_binance_spot_tickers(data: list[dict]) -> list[dict]:
    """Normalize Binance spot 24hr ticker as last-resort fallback."""
    result = []
    for t in data:
        sym = t.get("symbol", "")
        if not sym.endswith("USDT"):
            continue
        try:
            price = float(t.get("lastPrice", 0))
            vol_usd = float(t.get("quoteVolume", 0))
            pct_change = float(t.get("priceChangePercent", 0))
            high = float(t.get("highPrice", 0))
            low = float(t.get("lowPrice", 0))
            result.append({
                "symbol": sym,
                "price": price,
                "volume_usd": vol_usd,
                "price_change_pct": pct_change,
                "high": high,
                "low": low,
            })
        except (ValueError, TypeError):
            continue
    return result


# ---------------------------------------------------------------------------
# Filtering & Ranking
# ---------------------------------------------------------------------------
def filter_tradeable(tickers: list[dict]) -> list[dict]:
    """Filter to tradeable pairs: volume > $1M, price > $0.001."""
    filtered = [
        t for t in tickers
        if t["volume_usd"] >= MIN_DAILY_VOLUME_USD
        and t["price"] >= MIN_PRICE
    ]
    log.info(f"  Filtered: {len(filtered)}/{len(tickers)} pairs meet volume/price thresholds")
    return filtered


def rank_by_hotness(tickers: list[dict]) -> list[dict]:
    """Rank symbols by composite hotness score.

    Score = weighted combination of:
      - Momentum (1h price change magnitude): 40%
      - Volume spike (volume vs median): 35%
      - Volatility (high-low range / price): 25%

    Higher score = more potential for moves.
    """
    if not tickers:
        return []

    # Compute median volume for normalization
    volumes = sorted(t["volume_usd"] for t in tickers)
    median_vol = volumes[len(volumes) // 2] if volumes else 1

    for t in tickers:
        # Momentum: absolute price change (we want movers in either direction)
        momentum = abs(t["price_change_pct"])

        # Volume spike: how much above median
        vol_ratio = t["volume_usd"] / max(median_vol, 1)
        vol_spike = min(vol_ratio, 20)  # Cap at 20x to avoid extreme outliers

        # Volatility: (high - low) / price as percentage
        price = t["price"]
        if price > 0 and t["high"] > 0 and t["low"] > 0:
            volatility = ((t["high"] - t["low"]) / price) * 100
        else:
            volatility = 0

        # Composite score (normalized roughly to 0-100 range)
        # momentum: typical 0-20, weight 0.4
        # vol_spike: typical 0-20, weight 0.35
        # volatility: typical 0-30, weight 0.25
        t["momentum_score"] = round(momentum, 2)
        t["volume_spike"] = round(vol_spike, 2)
        t["volatility_score"] = round(volatility, 2)
        t["hotness_score"] = round(
            momentum * 0.40 + vol_spike * 0.35 + volatility * 0.25,
            3
        )

    # Sort by hotness descending
    tickers.sort(key=lambda t: t["hotness_score"], reverse=True)
    return tickers


# ---------------------------------------------------------------------------
# Core symbol extraction
# ---------------------------------------------------------------------------
def get_core_binance_symbols() -> set[str]:
    """Extract Binance symbol names from the static CRYPTO_SYMBOLS config.

    Returns set of Binance-format symbols like {"BTCUSDT", "ETHUSDT", ...}.
    """
    core = set()
    for _yf_ticker, meta in CRYPTO_SYMBOLS.items():
        binance_sym = meta.get("binance", "")
        if binance_sym:
            core.add(binance_sym)
    return core


def build_yf_ticker(binance_symbol: str) -> str:
    """Convert Binance symbol to yfinance ticker format.

    BTCUSDT -> BTC-USD, ETHUSDT -> ETH-USD, etc.
    """
    # Strip USDT suffix
    base = binance_symbol.replace("USDT", "")
    return f"{base}-USD"


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------
def generate_dynamic_universe() -> dict:
    """Fetch, filter, rank, and merge dynamic symbols with core.

    Returns the full universe dict that gets saved to JSON.
    """
    log.info("\n=== Dynamic Universe Scanner ===")
    log.info(f"  Timestamp: {datetime.now(timezone.utc).isoformat()}")

    # Step 1: Fetch all tickers
    log.info("[1/4] Fetching all USDT perpetual tickers...")
    all_tickers = fetch_all_futures_tickers()
    if not all_tickers:
        log.warning("  No tickers fetched. Returning empty dynamic universe.")
        return _empty_result()

    # Step 2: Filter tradeable
    log.info("[2/4] Filtering tradeable pairs...")
    tradeable = filter_tradeable(all_tickers)

    # Step 3: Rank by hotness
    log.info("[3/4] Ranking by momentum + volume spike + volatility...")
    ranked = rank_by_hotness(tradeable)

    # Step 4: Separate core vs dynamic
    core_symbols = get_core_binance_symbols()
    log.info(f"  Core static symbols: {len(core_symbols)}")

    # Pick top N non-core symbols
    dynamic_picks = []
    for t in ranked:
        if t["symbol"] not in core_symbols and len(dynamic_picks) < TOP_N_DYNAMIC:
            dynamic_picks.append(t)

    dynamic_symbol_set = {t["symbol"] for t in dynamic_picks}
    merged = sorted(core_symbols | dynamic_symbol_set)

    log.info(f"[4/4] Universe built:")
    log.info(f"  Core symbols:    {len(core_symbols)}")
    log.info(f"  Dynamic adds:    {len(dynamic_picks)}")
    log.info(f"  Total unique:    {len(merged)}")

    if dynamic_picks:
        log.info(f"\n  Top 10 hottest dynamic adds:")
        for i, t in enumerate(dynamic_picks[:10], 1):
            log.info(
                f"    {i:2d}. {t['symbol']:15s}  "
                f"price=${t['price']:<10.4f}  "
                f"vol=${t['volume_usd']/1e6:>8.1f}M  "
                f"change={t['price_change_pct']:+.1f}%  "
                f"hotness={t['hotness_score']:.1f}"
            )

    result = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "core_count": len(core_symbols),
        "dynamic_count": len(dynamic_picks),
        "total_unique": len(merged),
        "core_symbols": sorted(core_symbols),
        "dynamic_symbols": [t["symbol"] for t in dynamic_picks],
        "merged_symbols": merged,
        # Include yfinance ticker mapping for dynamic symbols
        "dynamic_yf_map": {
            t["symbol"]: build_yf_ticker(t["symbol"])
            for t in dynamic_picks
        },
        "rankings": [
            {
                "symbol": t["symbol"],
                "price": t["price"],
                "volume_usd": round(t["volume_usd"], 2),
                "price_change_pct": t["price_change_pct"],
                "momentum_score": t["momentum_score"],
                "volume_spike": t["volume_spike"],
                "volatility_score": t["volatility_score"],
                "hotness_score": t["hotness_score"],
            }
            for t in dynamic_picks
        ],
    }
    return result


def _empty_result() -> dict:
    """Return an empty-but-valid universe dict when fetch fails."""
    core_symbols = get_core_binance_symbols()
    return {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "core_count": len(core_symbols),
        "dynamic_count": 0,
        "total_unique": len(core_symbols),
        "core_symbols": sorted(core_symbols),
        "dynamic_symbols": [],
        "merged_symbols": sorted(core_symbols),
        "dynamic_yf_map": {},
        "rankings": [],
        "error": "Failed to fetch tickers from all endpoints",
    }


def save_universe(result: dict) -> Path:
    """Save universe to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    log.info(f"\n  Saved to {OUTPUT_PATH}")
    return OUTPUT_PATH


# ---------------------------------------------------------------------------
# Public API for scanner.py integration
# ---------------------------------------------------------------------------
def load_dynamic_symbols() -> list[str]:
    """Load dynamic symbols from cached JSON. Returns yfinance ticker list.

    Called by scanner.py to supplement the static symbol list.
    Falls back to empty list if file doesn't exist or is stale (>2h).
    """
    try:
        if not OUTPUT_PATH.exists():
            return []

        # Check staleness (>2 hours = stale, don't use)
        file_age_s = time.time() - OUTPUT_PATH.stat().st_mtime
        if file_age_s > 7200:  # 2 hours
            return []

        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        yf_map = data.get("dynamic_yf_map", {})
        # Return yfinance tickers for dynamic symbols
        return list(yf_map.values())

    except Exception:
        return []


def load_dynamic_symbol_meta() -> dict[str, dict]:
    """Load dynamic symbols with metadata for config integration.

    Returns dict compatible with CRYPTO_SYMBOLS format:
      {"BTC-USD": {"name": "Bitcoin", "tier": "dynamic", "cat": "crypto", "binance": "BTCUSDT"}}
    """
    try:
        if not OUTPUT_PATH.exists():
            return {}

        file_age_s = time.time() - OUTPUT_PATH.stat().st_mtime
        if file_age_s > 7200:
            return {}

        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        yf_map = data.get("dynamic_yf_map", {})
        rankings = {r["symbol"]: r for r in data.get("rankings", [])}

        meta = {}
        for binance_sym, yf_ticker in yf_map.items():
            base = binance_sym.replace("USDT", "")
            ranking = rankings.get(binance_sym, {})
            meta[yf_ticker] = {
                "name": base,
                "tier": "dynamic",
                "cat": "crypto",
                "binance": binance_sym,
                "hotness_score": ranking.get("hotness_score", 0),
                "dynamic": True,  # Flag so strategies know this is a dynamic add
            }
        return meta

    except Exception:
        return {}


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    result = generate_dynamic_universe()
    save_universe(result)

    # Summary
    print(f"\n{'='*50}")
    print(f"  Dynamic Universe: {result['dynamic_count']} hot symbols")
    print(f"  Core symbols:     {result['core_count']}")
    print(f"  Total universe:   {result['total_unique']}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
