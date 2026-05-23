"""Fetch current prices from Binance (primary) and CoinGecko (fallback)."""

import logging
from typing import Dict, List

import requests

from sandbox.config import BINANCE_TICKER_URL, COINGECKO_URL

log = logging.getLogger(__name__)

# CoinGecko ID mapping for non-Binance symbols
_CG_MAP = {
    "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "BNBUSDT": "binancecoin",
    "SOLUSDT": "solana", "XRPUSDT": "ripple", "DOGEUSDT": "dogecoin",
    "ADAUSDT": "cardano", "AVAXUSDT": "avalanche-2", "DOTUSDT": "polkadot",
    "LINKUSDT": "chainlink", "NEARUSDT": "near", "SHIBUSDT": "shiba-inu",
    "TRXUSDT": "tron", "MATICUSDT": "matic-network",
}


def fetch_prices_binance(symbols: List[str]) -> Dict[str, float]:
    """Fetch all Binance USDT ticker prices in one request."""
    try:
        resp = requests.get(BINANCE_TICKER_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        price_map = {item["symbol"]: float(item["price"]) for item in data}
        return {s: price_map[s] for s in symbols if s in price_map}
    except Exception as exc:
        log.error("Binance price fetch failed: %s", exc)
        return {}


def fetch_prices_coingecko(symbols: List[str]) -> Dict[str, float]:
    """Fallback: CoinGecko for symbols missing from Binance."""
    ids_to_sym = {}
    for s in symbols:
        cg_id = _CG_MAP.get(s)
        if cg_id:
            ids_to_sym[cg_id] = s
    if not ids_to_sym:
        return {}
    try:
        resp = requests.get(COINGECKO_URL, params={
            "ids": ",".join(ids_to_sym.keys()),
            "vs_currencies": "usd",
        }, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        result = {}
        for cg_id, sym in ids_to_sym.items():
            if cg_id in data and "usd" in data[cg_id]:
                result[sym] = float(data[cg_id]["usd"])
        return result
    except Exception as exc:
        log.error("CoinGecko price fetch failed: %s", exc)
        return {}


def fetch_prices(symbols: List[str]) -> Dict[str, float]:
    """Fetch prices using Binance first, CoinGecko fallback for missing."""
    prices = fetch_prices_binance(symbols)
    missing = [s for s in symbols if s not in prices]
    if missing:
        prices.update(fetch_prices_coingecko(missing))
    return prices
