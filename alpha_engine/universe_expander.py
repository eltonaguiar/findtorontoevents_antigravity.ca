#!/usr/bin/env python3
"""
Universe Expander -- Catch Top Gainers We're Missing
=====================================================
Expands the crypto symbol universe by discovering:
  1. New Binance USDT listings (last N days)
  2. CoinGecko trending coins
  3. Top 24h gainers on Binance (by % change)
  4. Gap detection vs top-200 by volume

All sources are deduplicated against the current universe and filtered
by minimum 24h volume to avoid illiquid traps.

API failover: Binance mirrors -> CoinGecko -> KuCoin (per project rules: always 3+).

Output: alpha_engine/data/universe_expansion.json

Public API:
  fetch_binance_new_listings(days=30) -> list[str]
  fetch_trending_coingecko()          -> list[str]
  fetch_top_gainers_24h(limit=50)     -> list[str]
  expand_universe(current)            -> dict
  get_gainer_candidates(min_volume_usd=1_000_000) -> list[dict]
  get_expansion_for_scanner(...)      -> (dict, str)   # scanner integration

Usage:
    python alpha_engine/universe_expander.py
    python -m alpha_engine.universe_expander
"""
from __future__ import annotations

import json
import logging
import os
import ssl
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Windows UTF-8 fix
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("universe_expander")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

ALPHA_PICKS = ROOT / "data" / "active_picks.json"
COPY_TRADER_PICKS = ROOT.parent / "copy_trader_intel" / "data" / "active_picks.json"
OUTPUT_FILE = DATA_DIR / "universe_expansion.json"

# ---------------------------------------------------------------------------
# Binance API mirrors -- 5-mirror failover (project rules: always 3+)
# Prefer data-api.binance.vision first (unrestricted, works on GitHub Actions)
# ---------------------------------------------------------------------------
BINANCE_MIRRORS = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

# In CI, prefer non-geo-blocked endpoints first
if os.environ.get("GITHUB_ACTIONS"):
    BINANCE_MIRRORS = [
        "https://data-api.binance.vision",
        "https://api.binance.us",
        "https://api.binance.com",
        "https://api1.binance.com",
        "https://api2.binance.com",
        "https://api3.binance.com",
    ]

# Non-Binance fallbacks (CoinGecko, KuCoin)
_COINGECKO_BASE = "https://api.coingecko.com/api/v3"
_KUCOIN_BASE = "https://api.kucoin.com"

# Stablecoins / wrapped tokens -- never trading opportunities
EXCLUDED_TOKENS = {
    "USDCUSDT", "BUSDUSDT", "TUSDUSDT", "USDPUSDT", "DAIUSDT",
    "FDUSDUSDT", "EURUSDT", "GBPUSDT", "PAXUSDT", "USTCUSDT",
    "WBTCUSDT", "WBETHUSDT", "STETHUSDT", "CBETHUSDT", "RETHUSDT",
    "BETHUSDT", "USD1USDT", "USDDUSDT", "PYUSDUSDT",
}
_STABLECOIN_BASES = {"USDC", "BUSD", "DAI", "TUSD", "FDUSD", "USDP", "USDD", "PYUSD", "USD1", "USDJ", "USDT"}
_LEVERAGED_TAGS = ("UP", "DOWN", "BULL", "BEAR", "3L", "3S", "2L", "2S")

_HDR = {"User-Agent": "AlphaEngine/UniverseExpander/2.0", "Accept": "application/json"}

# ---------------------------------------------------------------------------
# HTTP helpers with failover
# ---------------------------------------------------------------------------

def _ssl_ctx() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    return ctx


def _http_get(url: str, timeout: int = 15) -> dict | list | None:
    """Fetch JSON from a single URL."""
    try:
        req = urllib.request.Request(url, headers=_HDR)
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx()) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        log.debug("HTTP GET failed %s: %s", url, exc)
        return None


def _binance_get(path: str, params: str = "") -> dict | list | None:
    """Fetch JSON from Binance with 5-mirror failover."""
    for base in BINANCE_MIRRORS:
        url = f"{base}{path}"
        if params:
            url += f"?{params}"
        result = _http_get(url)
        if result is not None:
            return result
    log.warning("All Binance mirrors failed for %s", path)
    return None


def _is_valid_trading_pair(symbol: str) -> bool:
    """Check if a USDT pair is valid for trading (not stablecoin, not leveraged)."""
    if not symbol.endswith("USDT"):
        return False
    base = symbol.replace("USDT", "")
    if base in _STABLECOIN_BASES:
        return False
    if any(base.endswith(tag) for tag in _LEVERAGED_TAGS):
        return False
    if "_" in symbol:
        return False
    if symbol in EXCLUDED_TOKENS:
        return False
    return True


# ---------------------------------------------------------------------------
# 1. Fetch recently listed USDT pairs from Binance
# ---------------------------------------------------------------------------
def fetch_binance_new_listings(days: int = 30) -> list[str]:
    """Get recently listed USDT pairs from Binance.

    Strategy: Fetch exchange info for all TRADING USDT pairs, then sample
    kline history depth to identify pairs with < N days of data (= new listing).

    Falls back to KuCoin if Binance is unavailable.

    Args:
        days: Look back this many days for new listings (default 30).

    Returns:
        List of Binance symbol strings (e.g. ["XYZUSDT", ...]).
    """
    new_symbols = []

    # Step 1: Get all active USDT pairs from exchange info
    exchange_info = _binance_get("/api/v3/exchangeInfo")
    if not exchange_info or "symbols" not in exchange_info:
        log.warning("[NEW LISTINGS] exchangeInfo failed, trying KuCoin fallback")
        return _new_listings_kucoin_fallback()

    all_usdt = []
    for s in exchange_info["symbols"]:
        sym = s.get("symbol", "")
        status = s.get("status", "")
        if status == "TRADING" and _is_valid_trading_pair(sym):
            all_usdt.append(sym)

    log.info("[NEW LISTINGS] %d active USDT pairs on Binance", len(all_usdt))

    # Step 2: Get 24hr tickers to pre-filter by volume (avoid hammering klines API)
    tickers_24h = _binance_get("/api/v3/ticker/24hr")
    ticker_map = {}
    if tickers_24h:
        for t in tickers_24h:
            ticker_map[t.get("symbol", "")] = t

    # Step 3: Check kline start time for pairs with decent volume
    cutoff_ts = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
    checked = 0
    for sym in all_usdt:
        # Skip low-volume pairs (< $500k/day)
        t = ticker_map.get(sym, {})
        vol = float(t.get("quoteVolume", 0))
        if vol < 500_000:
            continue

        # Check first available 1d kline timestamp
        klines = _binance_get(
            "/api/v3/klines",
            f"symbol={sym}&interval=1d&limit=1&startTime=0"
        )
        if klines and len(klines) > 0:
            first_open_time = klines[0][0]  # ms timestamp
            if first_open_time > cutoff_ts:
                new_symbols.append(sym)
                listing_date = datetime.fromtimestamp(
                    first_open_time / 1000, tz=timezone.utc
                ).strftime("%Y-%m-%d")
                log.info("  New listing: %s (first candle: %s, vol: $%.0fK)",
                         sym, listing_date, vol / 1000)

        checked += 1
        # Rate limit: stay well under 1200 req/min
        if checked % 15 == 0:
            time.sleep(1.0)
        # Cap checks to avoid excessive API calls
        if checked >= 120:
            break

    log.info("[NEW LISTINGS] Found %d new listings in last %d days (checked %d pairs)",
             len(new_symbols), days, checked)
    return list(set(new_symbols))


def _new_listings_kucoin_fallback() -> list[str]:
    """Fallback: Get potential new listings from KuCoin symbol list."""
    new_symbols = []
    kucoin_data = _http_get(f"{_KUCOIN_BASE}/api/v1/symbols")
    if kucoin_data and kucoin_data.get("code") == "200000":
        symbols_list = kucoin_data.get("data", [])
        for s in symbols_list:
            sym_name = s.get("symbol", "")
            if not sym_name.endswith("-USDT"):
                continue
            base = sym_name.replace("-USDT", "")
            binance_sym = f"{base}USDT"
            if _is_valid_trading_pair(binance_sym):
                new_symbols.append(binance_sym)
        # Take last 30 entries as "probably newest"
        new_symbols = new_symbols[-30:]
        log.info("[NEW LISTINGS] KuCoin fallback: %d candidates", len(new_symbols))
    return new_symbols


# ---------------------------------------------------------------------------
# 2. Fetch trending coins from CoinGecko
# ---------------------------------------------------------------------------
def fetch_trending_coingecko() -> list[str]:
    """Get CoinGecko trending coins, map to Binance USDT pairs.

    Falls back to KuCoin top movers if CoinGecko is unavailable.

    Returns:
        List of Binance symbol strings (e.g. ["XYZUSDT", ...]).
    """
    trending_symbols = []

    # Primary: CoinGecko trending endpoint
    data = _http_get(f"{_COINGECKO_BASE}/search/trending")
    if data and isinstance(data, dict):
        coins = data.get("coins", [])
        for item in coins:
            coin = item.get("item", {})
            symbol = coin.get("symbol", "").upper()
            if not symbol:
                continue
            binance_sym = f"{symbol}USDT"
            if _is_valid_trading_pair(binance_sym):
                trending_symbols.append(binance_sym)
                log.info("  Trending: %s (%s, MCap rank #%s)",
                         binance_sym, coin.get("name", "?"),
                         coin.get("market_cap_rank", "?"))

    # Fallback: KuCoin top movers by absolute change
    if not trending_symbols:
        log.info("[TRENDING] CoinGecko returned 0, trying KuCoin top movers...")
        kucoin_data = _http_get(f"{_KUCOIN_BASE}/api/v1/market/allTickers")
        if kucoin_data and kucoin_data.get("code") == "200000":
            tickers = kucoin_data.get("data", {}).get("ticker", [])
            usdt_tickers = []
            for t in tickers:
                if not t.get("symbol", "").endswith("-USDT"):
                    continue
                try:
                    vol = float(t.get("volValue", 0))
                    change = abs(float(t.get("changeRate", 0)))
                except (ValueError, TypeError):
                    continue
                if vol > 1_000_000:
                    usdt_tickers.append((t, change))
            usdt_tickers.sort(key=lambda x: x[1], reverse=True)
            for t, _ in usdt_tickers[:15]:
                base = t["symbol"].replace("-USDT", "")
                binance_sym = f"{base}USDT"
                if _is_valid_trading_pair(binance_sym):
                    trending_symbols.append(binance_sym)

    log.info("[TRENDING] Found %d trending coins", len(trending_symbols))
    return list(set(trending_symbols))


# ---------------------------------------------------------------------------
# 3. Fetch top 24h gainers from Binance
# ---------------------------------------------------------------------------
def fetch_top_gainers_24h(limit: int = 50) -> list[str]:
    """Get top 24h gainers from Binance by % price change.

    Failover chain: Binance mirrors -> KuCoin -> CoinGecko.

    Args:
        limit: Max number of gainers to return (default 50).

    Returns:
        List of Binance symbol strings sorted by % gain descending.
    """
    gainers = []

    # Primary: Binance 24hr ticker
    tickers = _binance_get("/api/v3/ticker/24hr")
    if tickers:
        candidates = []
        for t in tickers:
            sym = t.get("symbol", "")
            if not _is_valid_trading_pair(sym):
                continue
            try:
                change_pct = float(t.get("priceChangePercent", 0))
                vol_usd = float(t.get("quoteVolume", 0))
            except (ValueError, TypeError):
                continue
            if vol_usd < 500_000 or change_pct <= 0:
                continue
            candidates.append({"symbol": sym, "change_pct": change_pct, "volume_usd": vol_usd})

        candidates.sort(key=lambda x: x["change_pct"], reverse=True)
        gainers = [c["symbol"] for c in candidates[:limit]]
        if candidates:
            log.info("[GAINERS] Top gainer: %s (+%.1f%%)",
                     candidates[0]["symbol"], candidates[0]["change_pct"])

    # Fallback: KuCoin
    if not gainers:
        log.info("[GAINERS] Binance failed, trying KuCoin...")
        kucoin_data = _http_get(f"{_KUCOIN_BASE}/api/v1/market/allTickers")
        if kucoin_data and kucoin_data.get("code") == "200000":
            tickers_kc = kucoin_data.get("data", {}).get("ticker", [])
            candidates = []
            for t in tickers_kc:
                sym_name = t.get("symbol", "")
                if not sym_name.endswith("-USDT"):
                    continue
                try:
                    change_rate = float(t.get("changeRate", 0))
                    vol_usd = float(t.get("volValue", 0))
                except (ValueError, TypeError):
                    continue
                if vol_usd < 500_000 or change_rate <= 0:
                    continue
                base = sym_name.replace("-USDT", "")
                binance_sym = f"{base}USDT"
                if _is_valid_trading_pair(binance_sym):
                    candidates.append({
                        "symbol": binance_sym,
                        "change_pct": change_rate * 100,
                        "volume_usd": vol_usd,
                    })
            candidates.sort(key=lambda x: x["change_pct"], reverse=True)
            gainers = [c["symbol"] for c in candidates[:limit]]

    # Fallback: CoinGecko
    if not gainers:
        log.info("[GAINERS] KuCoin failed, trying CoinGecko...")
        cg_data = _http_get(
            f"{_COINGECKO_BASE}/coins/markets?vs_currency=usd"
            f"&order=percent_change_24h_desc&per_page={limit}&page=1&sparkline=false"
        )
        if cg_data and isinstance(cg_data, list):
            for coin in cg_data:
                symbol = coin.get("symbol", "").upper()
                binance_sym = f"{symbol}USDT"
                if _is_valid_trading_pair(binance_sym):
                    gainers.append(binance_sym)

    log.info("[GAINERS] Found %d top gainers (24h)", len(gainers))
    return gainers


# ---------------------------------------------------------------------------
# 4. Expand universe -- combine all sources, deduplicate
# ---------------------------------------------------------------------------
def expand_universe(current: list[str]) -> dict:
    """Combine all discovery sources, deduplicate against current universe.

    Args:
        current: List of current Binance symbols (e.g. ["BTCUSDT", "ETHUSDT", ...])

    Returns:
        dict with keys:
          - new_symbols: symbols not in current universe (deduplicated union)
          - trending: currently trending (new only)
          - new_listings: recently listed (new only)
          - top_gainers: 24h top gainers (new only)
          - metadata: {symbol: {"sources": [...]}} for each new symbol
          - stats: summary counts
    """
    current_set = set(s.upper() for s in current)
    log.info("[UNIVERSE EXPANDER] Current universe: %d symbols", len(current_set))

    # Fetch all sources
    trending = fetch_trending_coingecko()
    top_gainers = fetch_top_gainers_24h(limit=50)
    new_listings = fetch_binance_new_listings(days=30)

    # Build metadata: track which source(s) flagged each symbol
    all_discovered = {}
    for sym in trending:
        all_discovered.setdefault(sym, {"sources": []})
        all_discovered[sym]["sources"].append("trending")
    for sym in top_gainers:
        all_discovered.setdefault(sym, {"sources": []})
        all_discovered[sym]["sources"].append("top_gainer")
    for sym in new_listings:
        all_discovered.setdefault(sym, {"sources": []})
        all_discovered[sym]["sources"].append("new_listing")

    # Deduplicate against current universe
    new_symbols = [sym for sym in all_discovered if sym not in current_set]

    # Sort by number of sources (multi-source = higher conviction), then alphabetically
    new_symbols.sort(key=lambda s: (-len(all_discovered[s]["sources"]), s))

    metadata = {sym: all_discovered[sym] for sym in new_symbols}

    n_trending = len([s for s in new_symbols if "trending" in all_discovered[s]["sources"]])
    n_gainers = len([s for s in new_symbols if "top_gainer" in all_discovered[s]["sources"]])
    n_new = len([s for s in new_symbols if "new_listing" in all_discovered[s]["sources"]])

    log.info("[UNIVERSE EXPANDER] Expanded by %d symbols (%d trending, %d new listings, %d gainers)",
             len(new_symbols), n_trending, n_new, n_gainers)

    result = {
        "new_symbols": new_symbols,
        "trending": [s for s in trending if s not in current_set],
        "new_listings": [s for s in new_listings if s not in current_set],
        "top_gainers": [s for s in top_gainers if s not in current_set],
        "metadata": metadata,
        "stats": {
            "current_universe_size": len(current_set),
            "total_discovered": len(all_discovered),
            "new_unique": len(new_symbols),
            "already_covered": len(all_discovered) - len(new_symbols),
            "trending_new": n_trending,
            "new_listings_new": n_new,
            "gainers_new": n_gainers,
        },
        "expanded_at": datetime.now(timezone.utc).isoformat(),
    }

    # Cache result
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
    except Exception as exc:
        log.warning("Failed to cache expansion result: %s", exc)

    return result


# ---------------------------------------------------------------------------
# 5. Get gainer candidates with volume filter + metadata
# ---------------------------------------------------------------------------
def get_gainer_candidates(min_volume_usd: float = 1_000_000) -> list[dict]:
    """Filter expanded universe by minimum 24h volume, return with metadata.

    Args:
        min_volume_usd: Minimum 24h quote volume in USD (default $1M).

    Returns:
        List of dicts sorted by change_pct descending, each containing:
          symbol, volume_usd, change_pct, price, market_cap_rank, sources.
    """
    candidates = []

    # Fetch Binance 24hr tickers for volume/change data
    tickers = _binance_get("/api/v3/ticker/24hr")
    ticker_map = {}
    if tickers:
        for t in tickers:
            sym = t.get("symbol", "")
            if not _is_valid_trading_pair(sym):
                continue
            try:
                ticker_map[sym] = {
                    "volume_usd": float(t.get("quoteVolume", 0)),
                    "change_pct": float(t.get("priceChangePercent", 0)),
                    "price": float(t.get("lastPrice", 0)),
                    "high_24h": float(t.get("highPrice", 0)),
                    "low_24h": float(t.get("lowPrice", 0)),
                    "trades_24h": int(t.get("count", 0)),
                }
            except (ValueError, TypeError):
                continue

    # Fallback: KuCoin tickers
    if not ticker_map:
        log.info("[CANDIDATES] Binance tickers failed, trying KuCoin...")
        kucoin_data = _http_get(f"{_KUCOIN_BASE}/api/v1/market/allTickers")
        if kucoin_data and kucoin_data.get("code") == "200000":
            for t in kucoin_data.get("data", {}).get("ticker", []):
                sym_name = t.get("symbol", "")
                if not sym_name.endswith("-USDT"):
                    continue
                base = sym_name.replace("-USDT", "")
                binance_sym = f"{base}USDT"
                if _is_valid_trading_pair(binance_sym):
                    try:
                        ticker_map[binance_sym] = {
                            "volume_usd": float(t.get("volValue", 0)),
                            "change_pct": float(t.get("changeRate", 0)) * 100,
                            "price": float(t.get("last", 0)),
                            "high_24h": float(t.get("high", 0)),
                            "low_24h": float(t.get("low", 0)),
                            "trades_24h": 0,
                        }
                    except (ValueError, TypeError):
                        continue

    # Get CoinGecko market cap ranks for enrichment
    mcap_ranks = {}
    cg_data = _http_get(
        f"{_COINGECKO_BASE}/coins/markets?vs_currency=usd&order=market_cap_desc"
        f"&per_page=250&page=1&sparkline=false"
    )
    if cg_data and isinstance(cg_data, list):
        for coin in cg_data:
            symbol = coin.get("symbol", "").upper()
            binance_sym = f"{symbol}USDT"
            mcap_ranks[binance_sym] = coin.get("market_cap_rank", 9999)

    # Load cached expansion data for source info
    expansion_meta = {}
    try:
        if OUTPUT_FILE.exists():
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
            expansion_meta = cached.get("metadata", {})
    except Exception:
        pass

    # Build candidate list (positive movers above volume threshold)
    for sym, data in ticker_map.items():
        if data["volume_usd"] < min_volume_usd:
            continue
        if data["change_pct"] <= 0:
            continue

        sources = expansion_meta.get(sym, {}).get("sources", [])
        candidates.append({
            "symbol": sym,
            "volume_usd": round(data["volume_usd"], 2),
            "change_pct": round(data["change_pct"], 2),
            "price": data["price"],
            "high_24h": data["high_24h"],
            "low_24h": data["low_24h"],
            "trades_24h": data["trades_24h"],
            "market_cap_rank": mcap_ranks.get(sym, 9999),
            "sources": sources,
        })

    candidates.sort(key=lambda x: x["change_pct"], reverse=True)

    log.info("[CANDIDATES] %d gainer candidates with >$%sK volume",
             len(candidates), f"{min_volume_usd/1000:.0f}")
    return candidates


# ---------------------------------------------------------------------------
# Integration helper for production_scanner.py
# ---------------------------------------------------------------------------
def get_expansion_for_scanner(current_binance_symbols: list[str],
                               max_add: int = 30) -> tuple[dict[str, dict], str]:
    """One-call integration point for production_scanner.py.

    Runs expand_universe(), then converts results to CRYPTO_SYMBOLS-compatible
    format with yfinance tickers and metadata.

    Args:
        current_binance_symbols: List of Binance symbols currently in universe.
        max_add: Maximum symbols to add (default 30).

    Returns:
        (symbols_to_add, log_message)
        - symbols_to_add: dict of {yf_ticker: metadata} compatible with CRYPTO_SYMBOLS
        - log_message: summary string for logging
    """
    try:
        expansion = expand_universe(current_binance_symbols)
    except Exception as exc:
        return {}, f"[UNIVERSE] Expansion failed: {exc}"

    new_syms = expansion.get("new_symbols", [])[:max_add]
    if not new_syms:
        return {}, "[UNIVERSE] No new symbols to add"

    # Get volume/price data for the new symbols
    candidates_map = {}
    try:
        candidates = get_gainer_candidates(min_volume_usd=500_000)
        for c in candidates:
            candidates_map[c["symbol"]] = c
    except Exception:
        pass

    symbols_to_add = {}
    for binance_sym in new_syms:
        base = binance_sym.replace("USDT", "")
        yf_ticker = f"{base}-USD"
        meta = expansion.get("metadata", {}).get(binance_sym, {})
        sources = meta.get("sources", ["expansion"])
        cand = candidates_map.get(binance_sym, {})

        symbols_to_add[yf_ticker] = {
            "name": base,
            "tier": "dynamic_expansion",
            "cat": "crypto",
            "binance": binance_sym,
            "dynamic": True,
            "expansion_sources": sources,
            "change_pct_24h": cand.get("change_pct", 0),
            "volume_usd_24h": cand.get("volume_usd", 0),
        }

    stats = expansion.get("stats", {})
    n_trending = stats.get("trending_new", 0)
    n_new = stats.get("new_listings_new", 0)
    n_gainers = stats.get("gainers_new", 0)

    msg = (f"[UNIVERSE] Expanded by {len(symbols_to_add)} symbols "
           f"({n_trending} trending, {n_new} new listings, {n_gainers} gainers)")

    return symbols_to_add, msg


# ---------------------------------------------------------------------------
# Legacy run() function (gap detection + scoring -- preserved for CLI usage)
# ---------------------------------------------------------------------------
def _load_current_picks_symbols() -> tuple[set[str], dict[str, int]]:
    """Load symbols from active picks files for gap detection."""
    symbols: set[str] = set()
    ct_counts: dict[str, int] = {}

    if ALPHA_PICKS.exists():
        try:
            with open(ALPHA_PICKS, "r", encoding="utf-8") as f:
                alpha_data = json.load(f)
            if isinstance(alpha_data, list):
                for pick in alpha_data:
                    sym = pick.get("symbol", "")
                    if sym:
                        symbols.add(sym)
        except Exception:
            pass

    if COPY_TRADER_PICKS.exists():
        try:
            with open(COPY_TRADER_PICKS, "r", encoding="utf-8") as f:
                ct_data = json.load(f)
            if isinstance(ct_data, list):
                for pick in ct_data:
                    sym = pick.get("symbol", "")
                    if sym:
                        symbols.add(sym)
                        ct_counts[sym] = ct_counts.get(sym, 0) + 1
        except Exception:
            pass

    return symbols, ct_counts


def run() -> dict:
    """Execute the full universe expansion pipeline (CLI entry point)."""
    log.info("=" * 60)
    log.info("Universe Expander -- Catch Top Gainers We're Missing")
    log.info("=" * 60)

    # Load current config universe
    try:
        sys.path.insert(0, str(ROOT))
        from config import CRYPTO_SYMBOLS
        current_binance = [
            meta.get("binance", "")
            for meta in CRYPTO_SYMBOLS.values()
            if meta.get("binance")
        ]
    except ImportError:
        current_binance = []
        log.warning("Could not load config.CRYPTO_SYMBOLS, using empty universe")

    # Run expansion
    expansion = expand_universe(current_binance)

    # Get gainer candidates with metadata
    candidates = get_gainer_candidates(min_volume_usd=1_000_000)

    # Summary
    stats = expansion.get("stats", {})
    log.info("-" * 60)
    log.info("RESULTS SUMMARY:")
    log.info("  Current universe: %d symbols", stats.get("current_universe_size", 0))
    log.info("  Total discovered: %d", stats.get("total_discovered", 0))
    log.info("  Already covered: %d", stats.get("already_covered", 0))
    log.info("  NEW symbols: %d", stats.get("new_unique", 0))
    log.info("    - Trending: %d", stats.get("trending_new", 0))
    log.info("    - New listings: %d", stats.get("new_listings_new", 0))
    log.info("    - Top gainers: %d", stats.get("gainers_new", 0))

    if expansion["new_symbols"]:
        log.info("  Top new symbols:")
        for sym in expansion["new_symbols"][:15]:
            meta = expansion["metadata"][sym]
            log.info("    %s  sources: %s", sym, ", ".join(meta["sources"]))

    if candidates:
        log.info("  Top gainer candidates (>$1M vol):")
        for c in candidates[:10]:
            log.info("    %s  +%.1f%%  vol=$%.1fM  MCap#%s",
                     c["symbol"], c["change_pct"],
                     c["volume_usd"] / 1e6, c["market_cap_rank"])

    log.info("-" * 60)
    log.info("Saved to: %s", OUTPUT_FILE)

    return expansion


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    run()
