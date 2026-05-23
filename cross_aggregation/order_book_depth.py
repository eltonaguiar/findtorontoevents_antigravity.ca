"""
Order-Book Depth — Binance public API integration for bid/ask imbalance.
Feeds into beta confluence scorer On-Chain pillar.
"""
import logging
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_SYMBOL_MAP = {
    "BTC-USD": "BTCUSDT", "ETH-USD": "ETHUSDT", "SOL-USD": "SOLUSDT",
    "XRP-USD": "XRPUSDT", "BNB-USD": "BNBUSDT", "ADA-USD": "ADAUSDT",
    "DOGE-USD": "DOGEUSDT", "AVAX-USD": "AVAXUSDT", "DOT-USD": "DOTUSDT",
    "LINK-USD": "LINKUSDT", "MATIC-USD": "MATICUSDT",
}

_OB_CACHE: Dict[str, dict] = {}
_OB_CACHE_TTL = 120


def get_order_book_imbalance(symbol: str, depth: int = 20) -> Optional[Dict[str, float]]:
    binance_sym = _SYMBOL_MAP.get(symbol)
    if not binance_sym:
        return None

    cached = _OB_CACHE.get(binance_sym)
    if cached and (time.time() - cached.get("_ts", 0)) < _OB_CACHE_TTL:
        return {k: v for k, v in cached.items() if k != "_ts"}

    try:
        import requests
        r = requests.get(f"https://api.binance.com/api/v3/depth",
                         params={"symbol": binance_sym, "limit": depth}, timeout=5)
        if r.status_code != 200:
            return None
        data = r.json()
        bids = data.get("bids", [])
        asks = data.get("asks", [])
        if not bids or not asks:
            return None

        bid_volume = sum(float(b[1]) for b in bids)
        ask_volume = sum(float(a[1]) for a in asks)
        total = bid_volume + ask_volume
        imbalance = (bid_volume - ask_volume) / total if total > 0 else 0

        best_bid = float(bids[0][0])
        best_ask = float(asks[0][0])
        mid = (best_bid + best_ask) / 2
        spread_pct = (best_ask - best_bid) / mid * 100 if mid > 0 else 0

        result = {"imbalance": round(imbalance, 4), "bid_volume": round(bid_volume, 2),
                  "ask_volume": round(ask_volume, 2), "spread_pct": round(spread_pct, 4)}
        _OB_CACHE[binance_sym] = {**result, "_ts": time.time()}
        return result
    except Exception as e:
        logger.warning(f"Order book fetch failed for {symbol}: {e}")
        return None


def get_bulk_imbalance(symbols: list, depth: int = 20) -> Dict[str, dict]:
    results = {}
    for sym in symbols:
        ob = get_order_book_imbalance(sym, depth)
        if ob:
            results[sym] = ob
    return results
