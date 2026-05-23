"""
ALPHA ENGINE -- Gainer Universe Expander
=========================================
Automatically discovers top-gaining crypto symbols missing from our universe.

Sources:
  1. Binance 24h top gainers (5-mirror failover)
  2. CoinGecko trending coins
  3. Binance new listings (< 30 days of kline data)

Filters:
  - Minimum $1M 24h volume (no illiquid garbage)
  - Exclude stablecoins (USDT, USDC, BUSD, DAI, TUSD, FDUSD)
  - Only USDT-quoted pairs

Output: data/universe_expansion.json
"""

from __future__ import annotations

import json
import logging
import os
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
ENGINE_DIR = Path(__file__).resolve().parent
DATA_DIR = ENGINE_DIR / "data"

# Binance 5-mirror failover (per CLAUDE.md API Failover Rule)
BINANCE_MIRRORS = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

COINGECKO_TRENDING_URL = "https://api.coingecko.com/api/v3/search/trending"

# Stablecoins to exclude
STABLECOINS = {"USDT", "USDC", "BUSD", "DAI", "TUSD", "FDUSD", "USDP", "PYUSD", "FRAX", "LUSD"}

# Minimum 24h volume in USD
MIN_VOLUME_USD = 1_000_000

# Minimum 24h gain % to qualify as a "gainer"
MIN_GAIN_PCT = 5.0

# Request timeout in seconds
REQUEST_TIMEOUT = 15

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_ssl_context() -> ssl.SSLContext:
    """Create an SSL context that works in CI environments."""
    ctx = ssl.create_default_context()
    return ctx


def _fetch_json(url: str, timeout: int = REQUEST_TIMEOUT) -> dict | list | None:
    """Fetch JSON from a URL with error handling."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
        ctx = _create_ssl_context()
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError,
            TimeoutError, OSError) as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return None


def _binance_api(path: str) -> dict | list | None:
    """Call Binance API with 5-mirror failover."""
    for mirror in BINANCE_MIRRORS:
        url = f"{mirror}{path}"
        result = _fetch_json(url)
        if result is not None:
            return result
        logger.warning("Mirror %s failed, trying next...", mirror)
    logger.error("All Binance mirrors failed for %s", path)
    return None


def _is_stablecoin(symbol: str) -> bool:
    """Check if a symbol is a stablecoin pair (both base and quote)."""
    # Remove USDT suffix to get base asset
    base = symbol.replace("USDT", "").replace("BUSD", "").replace("USDC", "")
    return base in STABLECOINS or base == ""


def _is_usdt_pair(symbol: str) -> bool:
    """Check if symbol is a USDT-quoted pair."""
    return symbol.endswith("USDT")


# ---------------------------------------------------------------------------
# Core Functions
# ---------------------------------------------------------------------------

def fetch_binance_top_gainers(limit: int = 50) -> list[dict]:
    """
    Fetch 24h ticker data from Binance, sort by priceChangePercent descending.
    Returns top N gainers with symbol, price, 24h change%, volume.
    Uses 5-mirror failover per CLAUDE.md.
    """
    data = _binance_api("/api/v3/ticker/24hr")
    if not data:
        logger.error("Could not fetch Binance 24h tickers from any mirror")
        return []

    gainers = []
    for ticker in data:
        symbol = ticker.get("symbol", "")

        # Only USDT pairs, skip stablecoins and non-ASCII symbols
        if not _is_usdt_pair(symbol):
            continue
        if _is_stablecoin(symbol):
            continue
        if not symbol.isascii():
            continue

        try:
            change_pct = float(ticker.get("priceChangePercent", 0))
            price = float(ticker.get("lastPrice", 0))
            volume_usd = float(ticker.get("quoteVolume", 0))
        except (ValueError, TypeError):
            continue

        # Skip zero-price or negligible volume
        if price <= 0 or volume_usd < MIN_VOLUME_USD:
            continue

        gainers.append({
            "symbol": symbol,
            "price": price,
            "change_24h": round(change_pct, 2),
            "volume_24h": round(volume_usd, 2),
        })

    # Sort by 24h change descending
    gainers.sort(key=lambda x: x["change_24h"], reverse=True)
    return gainers[:limit]


def fetch_coingecko_trending() -> list[dict]:
    """
    Fetch trending coins from CoinGecko API.
    Returns trending coin symbols mapped to Binance format.
    """
    data = _fetch_json(COINGECKO_TRENDING_URL)
    if not data or "coins" not in data:
        logger.error("Could not fetch CoinGecko trending")
        return []

    trending = []
    for item in data.get("coins", []):
        coin = item.get("item", {})
        symbol_raw = coin.get("symbol", "").upper()
        name = coin.get("name", "")
        market_cap_rank = coin.get("market_cap_rank")

        if not symbol_raw:
            continue

        # Skip stablecoins
        if symbol_raw in STABLECOINS:
            continue

        binance_symbol = f"{symbol_raw}USDT"
        trending.append({
            "symbol": binance_symbol,
            "name": name,
            "market_cap_rank": market_cap_rank,
            "reason": "coingecko_trending",
        })

    return trending


def fetch_binance_new_listings() -> list[dict]:
    """
    Fetch exchange info from Binance, identify symbols listed recently
    by checking if they have less than 30 days of kline data.
    Uses 5-mirror failover.
    """
    # Get all USDT trading pairs
    info = _binance_api("/api/v3/exchangeInfo")
    if not info or "symbols" not in info:
        logger.error("Could not fetch Binance exchange info")
        return []

    # Filter to USDT pairs that are currently trading
    usdt_pairs = []
    for sym_info in info["symbols"]:
        if (sym_info.get("quoteAsset") == "USDT"
                and sym_info.get("status") == "TRADING"
                and not _is_stablecoin(sym_info.get("symbol", ""))):
            usdt_pairs.append(sym_info["symbol"])

    # Check kline count for candidates -- we sample a subset to avoid rate limits
    # Sort alphabetically and check only symbols not commonly known
    # Strategy: fetch 1d klines and count how many exist
    new_listings = []
    checked = 0
    max_checks = 60  # Rate limit protection

    # We only check symbols that "look new" (shorter names, less common prefixes)
    # This is a heuristic to avoid checking 500+ symbols
    for symbol in sorted(usdt_pairs):
        if checked >= max_checks:
            break

        # Quick heuristic: skip very well-known symbols
        base = symbol.replace("USDT", "")
        if len(base) <= 2:  # BTC, ETH, etc are well-known
            continue

        # Fetch daily klines -- if < 30, it's a new listing
        klines = _binance_api(
            f"/api/v3/klines?symbol={symbol}&interval=1d&limit=31"
        )
        if klines is None:
            continue
        checked += 1

        if len(klines) < 30:
            # Verify it has sufficient volume
            ticker = _binance_api(f"/api/v3/ticker/24hr?symbol={symbol}")
            if ticker:
                try:
                    volume_usd = float(ticker.get("quoteVolume", 0))
                    price = float(ticker.get("lastPrice", 0))
                    change_pct = float(ticker.get("priceChangePercent", 0))
                except (ValueError, TypeError):
                    continue

                if volume_usd >= MIN_VOLUME_USD:
                    new_listings.append({
                        "symbol": symbol,
                        "price": price,
                        "change_24h": round(change_pct, 2),
                        "volume_24h": round(volume_usd, 2),
                        "kline_days": len(klines),
                        "reason": "new_listing",
                    })

    return new_listings


def get_current_universe() -> set[str]:
    """
    Read config.py CRYPTO_SYMBOLS 'binance' field and active_picks.json
    to get all symbols we currently track. Returns set of Binance symbols
    (e.g., {'BTCUSDT', 'ETHUSDT', ...}).
    """
    tracked = set()

    # 1. Read from config.py CRYPTO_SYMBOLS
    try:
        # Import config to get the CRYPTO_SYMBOLS dict
        import importlib
        import sys
        # Add engine dir to path if not there
        engine_str = str(ENGINE_DIR)
        if engine_str not in sys.path:
            sys.path.insert(0, engine_str)
        # Direct import approach -- read the binance field from each entry
        config_path = ENGINE_DIR / "config.py"
        if config_path.exists():
            # Parse config.py for binance symbols using simple text extraction
            # This avoids importing the full module (which may have dependencies)
            content = config_path.read_text(encoding="utf-8")
            import re
            # Match "binance": "XXXUSDT" patterns
            binance_matches = re.findall(r'"binance"\s*:\s*"([A-Z0-9]+USDT)"', content)
            for sym in binance_matches:
                tracked.add(sym)
            logger.info("Loaded %d symbols from config.py", len(binance_matches))
    except Exception as exc:
        logger.warning("Could not parse config.py: %s", exc)

    # 2. Read from active_picks.json
    picks_path = DATA_DIR / "active_picks.json"
    if picks_path.exists():
        try:
            with open(picks_path, "r", encoding="utf-8") as f:
                picks = json.load(f)
            if isinstance(picks, list):
                for pick in picks:
                    sym = pick.get("symbol", "")
                    if sym and sym.endswith("USDT"):
                        tracked.add(sym)
                logger.info("Loaded symbols from active_picks.json (%d picks)", len(picks))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not read active_picks.json: %s", exc)

    return tracked


def find_missing_gainers() -> dict:
    """
    Compare top gainers + trending + new listings against current universe.
    Returns dict with 'gainers', 'trending', 'new_listings' -- all symbols
    we're missing that are gaining >5% in 24h or trending.
    """
    current = get_current_universe()
    logger.info("Current universe: %d symbols", len(current))

    # Fetch from all sources
    top_gainers = fetch_binance_top_gainers(limit=50)
    trending = fetch_coingecko_trending()
    new_listings = fetch_binance_new_listings()

    # Filter to missing symbols
    missing_gainers = []
    for g in top_gainers:
        if g["symbol"] not in current and g["change_24h"] >= MIN_GAIN_PCT:
            g["reason"] = "top_gainer"
            missing_gainers.append(g)

    missing_trending = []
    for t in trending:
        if t["symbol"] not in current:
            missing_trending.append(t)

    missing_new = []
    for n in new_listings:
        if n["symbol"] not in current:
            missing_new.append(n)

    return {
        "current_universe_size": len(current),
        "gainers": missing_gainers,
        "trending": missing_trending,
        "new_listings": missing_new,
    }


def expand_universe(dry_run: bool = True) -> dict:
    """
    Main entry point. Finds missing gainers, validates volume,
    generates report, optionally writes to data/universe_expansion.json.

    Args:
        dry_run: If True, only generates report without writing file.
                 If False, writes universe_expansion.json.

    Returns:
        Expansion report dict.
    """
    logger.info("=== Universe Expander: Starting scan (dry_run=%s) ===", dry_run)

    missing = find_missing_gainers()

    # Build the report
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # All missing symbols combined (deduplicated)
    seen = set()
    new_symbols = []

    for g in missing["gainers"]:
        if g["symbol"] not in seen:
            seen.add(g["symbol"])
            new_symbols.append({
                "symbol": g["symbol"],
                "reason": "top_gainer",
                "change_24h": g["change_24h"],
                "volume_24h": g["volume_24h"],
            })

    for t in missing["trending"]:
        if t["symbol"] not in seen:
            seen.add(t["symbol"])
            new_symbols.append({
                "symbol": t["symbol"],
                "reason": "coingecko_trending",
                "name": t.get("name", ""),
                "market_cap_rank": t.get("market_cap_rank"),
            })

    for n in missing["new_listings"]:
        if n["symbol"] not in seen:
            seen.add(n["symbol"])
            new_symbols.append({
                "symbol": n["symbol"],
                "reason": "new_listing",
                "change_24h": n.get("change_24h", 0),
                "volume_24h": n.get("volume_24h", 0),
                "kline_days": n.get("kline_days", 0),
            })

    report = {
        "generated_at": now,
        "new_symbols": new_symbols,
        "trending": missing["trending"],
        "new_listings": missing["new_listings"],
        "current_universe_size": missing["current_universe_size"],
        "expanded_universe_size": missing["current_universe_size"] + len(new_symbols),
    }

    # Log summary
    logger.info("Current universe: %d symbols", report["current_universe_size"])
    logger.info("New gainers found: %d", len(missing["gainers"]))
    logger.info("New trending found: %d", len(missing["trending"]))
    logger.info("New listings found: %d", len(missing["new_listings"]))
    logger.info("Total new symbols: %d", len(new_symbols))
    logger.info("Expanded universe would be: %d symbols", report["expanded_universe_size"])

    if new_symbols:
        logger.info("--- Top missing gainers ---")
        for s in new_symbols[:10]:
            logger.info(
                "  %s: %s (change=%.1f%%, vol=$%.0f)",
                s["symbol"],
                s["reason"],
                s.get("change_24h", 0),
                s.get("volume_24h", 0),
            )

    if not dry_run:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        output_path = DATA_DIR / "universe_expansion.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info("Wrote expansion report to %s", output_path)
    else:
        logger.info("Dry run -- no file written. Pass dry_run=False to write.")

    return report


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Alpha Engine Universe Expander")
    parser.add_argument(
        "--write", action="store_true",
        help="Write universe_expansion.json (default: dry run only)",
    )
    parser.add_argument(
        "--limit", type=int, default=50,
        help="Number of top gainers to fetch (default: 50)",
    )
    args = parser.parse_args()

    result = expand_universe(dry_run=not args.write)

    # Print summary to stdout for CI
    print(json.dumps({
        "new_symbols_count": len(result["new_symbols"]),
        "current_universe_size": result["current_universe_size"],
        "expanded_universe_size": result["expanded_universe_size"],
    }, indent=2))
