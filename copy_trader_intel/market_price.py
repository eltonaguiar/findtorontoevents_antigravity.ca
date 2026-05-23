#!/usr/bin/env python3
"""
Market Price Fetcher — Failover Chain
======================================
Fetches current spot price from multiple exchanges with automatic failover.
Used by copy trader scrapers to record OUR entry price (current market price)
instead of the trader's historical entry.

Failover chain:
  Binance mirrors (api, api1, api2, api3, data-api) → CoinGecko → KuCoin
"""

import time
import logging
from functools import lru_cache

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)

# Cache prices for 30 seconds to avoid hammering APIs within the same scan cycle
_price_cache = {}  # {symbol: (price, timestamp)}
CACHE_TTL_SECONDS = 30

# Binance mirror endpoints
BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
]


def _normalize_symbol_for_coingecko(symbol: str) -> str:
    """Convert trading symbol like BTCUSDT to CoinGecko id like bitcoin."""
    # Strip common quote currencies
    base = symbol.upper()
    for suffix in ("USDT", "USD", "BUSD", "USDC", "TUSD"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break

    # Common mappings
    CG_MAP = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "BNB": "binancecoin",
        "SOL": "solana",
        "XRP": "ripple",
        "ADA": "cardano",
        "DOGE": "dogecoin",
        "DOT": "polkadot",
        "AVAX": "avalanche-2",
        "MATIC": "matic-network",
        "POL": "matic-network",
        "LINK": "chainlink",
        "UNI": "uniswap",
        "SHIB": "shiba-inu",
        "LTC": "litecoin",
        "ATOM": "cosmos",
        "NEAR": "near",
        "ARB": "arbitrum",
        "OP": "optimism",
        "APT": "aptos",
        "SUI": "sui",
        "FIL": "filecoin",
        "AAVE": "aave",
        "MKR": "maker",
        "FET": "fetch-ai",
        "INJ": "injective-protocol",
        "TIA": "celestia",
        "SEI": "sei-network",
        "PEPE": "pepe",
        "WIF": "dogwifcoin",
        "RENDER": "render-token",
        "RNDR": "render-token",
        "JUP": "jupiter-exchange-solana",
        "WLD": "worldcoin-wld",
        "ORDI": "ordinals",
        "STX": "blockstack",
        "TRX": "tron",
        "BCH": "bitcoin-cash",
        "ETC": "ethereum-classic",
        "HBAR": "hedera-hashgraph",
        "IMX": "immutable-x",
        "SAND": "the-sandbox",
        "MANA": "decentraland",
        "AXS": "axie-infinity",
        "CRV": "curve-dao-token",
        "LDO": "lido-dao",
        "RUNE": "thorchain",
        "GRT": "the-graph",
        "ENS": "ethereum-name-service",
        "ALGO": "algorand",
        "XLM": "stellar",
        "VET": "vechain",
        "THETA": "theta-token",
        "FTM": "fantom",
        "EOS": "eos",
        "IOTA": "iota",
        "XTZ": "tezos",
    }
    return CG_MAP.get(base, base.lower())


def _normalize_symbol_for_kucoin(symbol: str) -> str:
    """Convert BTCUSDT to BTC-USDT for KuCoin API."""
    upper = symbol.upper()
    for suffix in ("USDT", "USD", "BUSD", "USDC"):
        if upper.endswith(suffix):
            base = upper[: -len(suffix)]
            return f"{base}-{suffix}"
    return upper


def fetch_current_price(symbol: str, timeout: float = 3.0) -> float:
    """
    Fetch current market price for a crypto symbol with 3+ exchange failover.

    Args:
        symbol: Trading pair like 'BTCUSDT', 'ETHUSDT', 'SOLUSDT'
        timeout: Request timeout in seconds

    Returns:
        Current price as float, or 0.0 if all sources fail
    """
    if requests is None:
        return 0.0

    # Check cache first
    cached = _price_cache.get(symbol)
    if cached:
        price, ts = cached
        if time.time() - ts < CACHE_TTL_SECONDS:
            return price

    price = 0.0

    # 1. Try Binance mirrors
    for mirror in BINANCE_MIRRORS:
        try:
            url = f"{mirror}/api/v3/ticker/price?symbol={symbol.upper()}"
            resp = requests.get(url, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                price = float(data.get("price", 0))
                if price > 0:
                    _price_cache[symbol] = (price, time.time())
                    return price
        except Exception:
            continue

    # 2. Try CoinGecko
    try:
        cg_id = _normalize_symbol_for_coingecko(symbol)
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd"
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            if cg_id in data and "usd" in data[cg_id]:
                price = float(data[cg_id]["usd"])
                if price > 0:
                    _price_cache[symbol] = (price, time.time())
                    return price
    except Exception:
        pass

    # 3. Try KuCoin
    try:
        kucoin_symbol = _normalize_symbol_for_kucoin(symbol)
        url = f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={kucoin_symbol}"
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("code") == "200000" and data.get("data"):
                price = float(data["data"].get("price", 0))
                if price > 0:
                    _price_cache[symbol] = (price, time.time())
                    return price
    except Exception:
        pass

    return 0.0


def replace_entry_with_market_price(pick: dict) -> dict:
    """
    For a NEW pick dict, replace entry_price with current market price.
    Stores the original trader entry as 'original_trader_entry'.

    Only operates on crypto picks with a valid symbol.
    If market price fetch fails, keeps the original entry_price.

    Args:
        pick: A pick dictionary with at least 'symbol' and 'entry_price'

    Returns:
        The same pick dict, modified in place (and returned for convenience)
    """
    if not isinstance(pick, dict):
        return pick

    symbol = pick.get("symbol", "")
    trader_entry = pick.get("entry_price", 0)
    category = pick.get("category", "crypto").lower()

    # Only fetch market price for crypto picks (forex/equity use different sources)
    if category not in ("crypto", "cryptocurrency"):
        # Still store original_trader_entry for consistency
        if "original_trader_entry" not in pick:
            pick["original_trader_entry"] = trader_entry
        return pick

    if not symbol or trader_entry <= 0:
        return pick

    # Store original trader entry
    pick["original_trader_entry"] = trader_entry

    # Fetch current market price
    market_price = fetch_current_price(symbol)

    if market_price > 0:
        # Calculate how much price has moved since trader entered
        deviation_pct = abs(market_price - trader_entry) / trader_entry * 100 if trader_entry > 0 else 0

        pick["entry_price"] = market_price
        pick["entry_price_source"] = "market"
        pick["trader_entry_deviation_pct"] = round(deviation_pct, 2)

        # Recalculate TP/SL based on new entry if they were percentage-based defaults
        # (i.e., not set by the trader explicitly)
        _recalc_tp_sl(pick, market_price, trader_entry)

        if deviation_pct > 1.0:
            logger.info(
                f"  [MARKET ENTRY] {symbol}: trader entry ${trader_entry:.4f} -> "
                f"market ${market_price:.4f} (moved {deviation_pct:.1f}%)"
            )
    else:
        pick["entry_price_source"] = "trader_fallback"
        pick["trader_entry_deviation_pct"] = 0.0
        logger.warning(f"  [WARN] {symbol}: market price fetch failed, using trader entry ${trader_entry:.4f}")

    return pick


def _recalc_tp_sl(pick: dict, market_price: float, trader_entry: float):
    """
    Recalculate TP/SL if they appear to be default percentage-based values
    (not custom-set by the trader).

    We detect default TP/SL by checking if they are a clean percentage offset
    from the trader's original entry. If so, apply the same percentage to our
    market entry price.
    """
    tp = pick.get("take_profit", 0)
    sl = pick.get("stop_loss", 0)
    direction = pick.get("direction", "LONG")

    if not tp or not sl or trader_entry <= 0:
        return

    # Calculate the original TP/SL percentages relative to trader's entry
    if direction == "LONG":
        tp_pct = (tp - trader_entry) / trader_entry if trader_entry > 0 else 0
        sl_pct = (trader_entry - sl) / trader_entry if trader_entry > 0 else 0
    else:
        tp_pct = (trader_entry - tp) / trader_entry if trader_entry > 0 else 0
        sl_pct = (sl - trader_entry) / trader_entry if trader_entry > 0 else 0

    # Only recalculate if TP/SL look like default percentages (0.5% to 15%)
    if 0.005 <= tp_pct <= 0.15 and 0.005 <= sl_pct <= 0.15:
        if direction == "LONG":
            pick["take_profit"] = round(market_price * (1 + tp_pct), 8)
            pick["stop_loss"] = round(market_price * (1 - sl_pct), 8)
        else:
            pick["take_profit"] = round(market_price * (1 - tp_pct), 8)
            pick["stop_loss"] = round(market_price * (1 + sl_pct), 8)
