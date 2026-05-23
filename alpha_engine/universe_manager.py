#!/usr/bin/env python3
"""
Universe Manager -- Dynamic Symbol Rotation
============================================
Swaps bottom-N symbols by 30d volume for top-N trending symbols.
Prevents stale low-vol symbols (LTC, BCH, DOT) from wasting scan cycles.

From KIMI Research Compilation (Feb 2026):
  "Stale low-vol symbols waste scan cycles. Fix: rotate bottom-3
   by 30d volume for top-3 trending."

Uses CoinGecko free API:
  - /coins/markets for 30d volume ranking
  - /search/trending for trending coins

Results cached for 6 hours to avoid API rate limits.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path
from typing import Optional

# Cache config
_CACHE_DIR = Path(__file__).resolve().parent / "data" / "cache"
_CACHE_FILE = _CACHE_DIR / "universe_cache.json"
_CACHE_TTL_SECONDS = 6 * 3600  # 6 hours

# CoinGecko endpoints (free tier, no auth required)
_CG_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"
_CG_TRENDING_URL = "https://api.coingecko.com/api/v3/search/trending"

# Map yfinance tickers to CoinGecko IDs for volume lookup
_YF_TO_CG: dict[str, str] = {
    "BTC-USD": "bitcoin",
    "ETH-USD": "ethereum",
    "SOL-USD": "solana",
    "BNB-USD": "binancecoin",
    "XRP-USD": "ripple",
    "ADA-USD": "cardano",
    "AVAX-USD": "avalanche-2",
    "LINK-USD": "chainlink",
    "DOT-USD": "polkadot",
    "NEAR-USD": "near",
    "TRX-USD": "tron",
    "TON11419-USD": "the-open-network",
    "LTC-USD": "litecoin",
    "ETC-USD": "ethereum-classic",
    "SUI-USD": "sui",
    "TIA-USD": "celestia",
    "INJ-USD": "injective-protocol",
    "ATOM-USD": "cosmos",
    "FIL-USD": "filecoin",
    "APT-USD": "aptos",
    "SEI-USD": "sei-network",
    "PENDLE-USD": "pendle",
    "GALA-USD": "gala",
    "WLD-USD": "worldcoin-wld",
    "NOT-USD": "notcoin",
    "TURBO-USD": "turbo",
    "UNI-USD": "uniswap",
    "AAVE-USD": "aave",
    "MAV-USD": "maverick-protocol",
    "PEPE-USD": "pepe",
    "WIF-USD": "dogwifcoin",
    "BONK-USD": "bonk",
    "FLOKI-USD": "floki",
    "MEME-USD": "memecoin",
    "BOME-USD": "book-of-meme",
}

# Reverse map: CoinGecko ID -> yfinance ticker
_CG_TO_YF: dict[str, str] = {v: k for k, v in _YF_TO_CG.items()}


def _http_get_json(url: str, timeout: int = 15) -> Optional[dict | list]:
    """Fetch JSON from URL with error handling."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "AlphaEngine/2.0",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [UNIVERSE] HTTP error: {e}")
        return None


def _load_cache() -> Optional[dict]:
    """Load cached universe data if still valid."""
    try:
        if not _CACHE_FILE.exists():
            return None
        with open(_CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)
        cached_at = cache.get("cached_at", 0)
        if time.time() - cached_at > _CACHE_TTL_SECONDS:
            return None  # Expired
        return cache
    except Exception:
        return None


def _save_cache(data: dict):
    """Save universe data to cache."""
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        data["cached_at"] = time.time()
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"  [UNIVERSE] Cache write error: {e}")


def _fetch_volume_rankings(cg_ids: list[str]) -> dict[str, float]:
    """Fetch 30d total volume for given CoinGecko IDs.

    Returns dict of {coingecko_id: total_volume_usd}.
    """
    # CoinGecko /coins/markets returns volume data
    # We fetch in batches of 50 (API limit per_page max 250)
    volumes: dict[str, float] = {}
    ids_str = ",".join(cg_ids)
    url = (
        f"{_CG_MARKETS_URL}?vs_currency=usd"
        f"&ids={ids_str}"
        f"&order=volume_desc&per_page=250&sparkline=false"
    )

    data = _http_get_json(url)
    if not data or not isinstance(data, list):
        return volumes

    for coin in data:
        cg_id = coin.get("id", "")
        vol = coin.get("total_volume") or 0
        volumes[cg_id] = float(vol)

    return volumes


def _fetch_trending() -> list[dict]:
    """Fetch trending coins from CoinGecko.

    Returns list of dicts with 'id', 'symbol', 'name', 'market_cap_rank'.
    """
    data = _http_get_json(_CG_TRENDING_URL)
    if not data or not isinstance(data, dict):
        return []

    coins = data.get("coins", [])
    result = []
    for item in coins:
        coin = item.get("item", {})
        result.append({
            "id": coin.get("id", ""),
            "symbol": coin.get("symbol", "").upper(),
            "name": coin.get("name", ""),
            "market_cap_rank": coin.get("market_cap_rank"),
            "score": coin.get("score", 999),
        })
    return result


def _cg_id_to_yf_ticker(cg_id: str, symbol: str) -> str:
    """Convert CoinGecko ID to yfinance ticker format."""
    if cg_id in _CG_TO_YF:
        return _CG_TO_YF[cg_id]
    # Fallback: construct from symbol
    return f"{symbol.upper()}-USD"


def _build_binance_symbol(symbol: str) -> str:
    """Build Binance symbol from coin symbol (e.g. RENDER -> RENDERUSDT)."""
    return f"{symbol.upper()}USDT"


def get_dynamic_universe(
    base_symbols: dict[str, dict],
    n_swap: int = 3,
    protected_tiers: tuple[str, ...] = ("major",),
) -> tuple[dict[str, dict], list[str], list[str]]:
    """Swap bottom-N symbols by 30d volume for top-N trending symbols.

    Args:
        base_symbols: The CRYPTO_SYMBOLS dict from config.py
        n_swap: Number of symbols to swap (default 3)
        protected_tiers: Tiers that cannot be swapped out (default: majors)

    Returns:
        (updated_symbols, removed_list, added_list)
        - updated_symbols: New dict with swaps applied
        - removed_list: Symbols that were removed (e.g. ["LTC-USD", "DOT-USD"])
        - added_list: Symbols that were added (e.g. ["RENDER-USD", "FET-USD"])
    """
    # Short-circuit: skip network calls to prevent I/O errors on Windows
    return dict(base_symbols), [], []

    # Identify swappable symbols (non-protected tiers)
    swappable = {
        yf_ticker: meta
        for yf_ticker, meta in base_symbols.items()
        if meta.get("tier", "") not in protected_tiers
    }

    # Fetch volume data for swappable symbols
    cg_ids_to_check = {
        yf_ticker: _YF_TO_CG[yf_ticker]
        for yf_ticker in swappable
        if yf_ticker in _YF_TO_CG
    }

    if not cg_ids_to_check:
        print("  [UNIVERSE] No swappable symbols mapped to CoinGecko")
        return dict(base_symbols), [], []

    print(f"  [UNIVERSE] Fetching volume data for {len(cg_ids_to_check)} swappable symbols...")
    volumes = _fetch_volume_rankings(list(cg_ids_to_check.values()))

    if not volumes:
        print("  [UNIVERSE] Volume fetch failed, keeping base universe")
        return dict(base_symbols), [], []

    # Rank swappable symbols by volume (lowest first)
    ranked = sorted(
        cg_ids_to_check.items(),
        key=lambda x: volumes.get(x[1], 0)
    )

    # Bottom N by volume = candidates for removal
    bottom_n = ranked[:n_swap]
    to_remove = [yf_ticker for yf_ticker, _ in bottom_n]
    bottom_volumes = {yf: volumes.get(cg_id, 0) for yf, cg_id in bottom_n}

    # Fetch trending coins
    print(f"  [UNIVERSE] Fetching trending coins...")
    trending = _fetch_trending()

    if not trending:
        print("  [UNIVERSE] Trending fetch failed, keeping base universe")
        return dict(base_symbols), [], []

    # Filter trending: must not already be in base_symbols, must have reasonable market cap
    existing_cg_ids = set(_YF_TO_CG.values())
    candidates = [
        t for t in trending
        if t["id"] not in existing_cg_ids
        and t.get("market_cap_rank") is not None
        and t["market_cap_rank"] < 200  # Only top-200 by market cap
    ]

    # Take top N trending as replacements
    to_add = candidates[:n_swap]

    if not to_add:
        print("  [UNIVERSE] No qualifying trending coins found, keeping base universe")
        _save_cache({
            "base_count": len(base_symbols),
            "removed": [],
            "added": [],
            "added_entries": [],
        })
        return dict(base_symbols), [], []

    # Only remove as many as we can replace
    actual_swap_count = min(len(to_remove), len(to_add))
    to_remove = to_remove[:actual_swap_count]
    to_add = to_add[:actual_swap_count]

    # Build updated symbols dict
    updated = dict(base_symbols)
    removed_list = []
    added_list = []
    added_entries = []

    for sym in to_remove:
        vol_str = f"${bottom_volumes.get(sym, 0):,.0f}"
        print(f"  [UNIVERSE] Removing {sym} (24h vol: {vol_str})")
        updated.pop(sym, None)
        removed_list.append(sym)

    for t in to_add:
        yf_ticker = _cg_id_to_yf_ticker(t["id"], t["symbol"])
        binance_sym = _build_binance_symbol(t["symbol"])
        meta = {
            "name": t["name"],
            "tier": "trending",
            "cat": "crypto",
            "binance": binance_sym,
            "trending_rank": t.get("score", 0),
            "market_cap_rank": t.get("market_cap_rank"),
            "dynamic_add": True,  # Flag for tracking
        }
        updated[yf_ticker] = meta
        added_list.append(yf_ticker)
        added_entries.append({"ticker": yf_ticker, "meta": meta})
        print(f"  [UNIVERSE] Adding {yf_ticker} ({t['name']}, MCap rank #{t.get('market_cap_rank', '?')})")

    # Cache result
    _save_cache({
        "base_count": len(base_symbols),
        "removed": removed_list,
        "added": added_list,
        "added_entries": added_entries,
        "bottom_volumes": {k: v for k, v in bottom_volumes.items()},
        "trending_used": [t["id"] for t in to_add],
    })

    if removed_list or added_list:
        print(f"  [UNIVERSE] Swap complete: removed {removed_list}, added {added_list}")
    else:
        print(f"  [UNIVERSE] No swaps needed")

    return updated, removed_list, added_list
