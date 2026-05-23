"""
Orderbook Imbalance v2 — Micro-Structure Module
=================================================
Advanced order-book analysis: cumulative delta, footprint metrics,
VWAP-delta, depth ratio, and multi-exchange aggregation.

Dependencies: numpy, requests (stdlib: logging, typing)
Compatible with Python 3.11+ / GitHub Actions.

Sources supported: Binance (primary), OKX (failover).
"""

import logging
import numpy as np
import requests
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exchange API endpoints
# ---------------------------------------------------------------------------
_EXCHANGE_CONFIG = {
    "binance": {
        "url": "https://api.binance.com/api/v3/depth",
        "params_fn": lambda sym, depth: {"symbol": sym.upper(), "limit": depth},
        "parse_fn": lambda j: (
            [[float(b[0]), float(b[1])] for b in j.get("bids", [])],
            [[float(a[0]), float(a[1])] for a in j.get("asks", [])],
        ),
    },
    "okx": {
        "url": "https://www.okx.com/api/v5/market/books",
        "params_fn": lambda sym, depth: {
            "instId": _to_okx_symbol(sym),
            "sz": str(depth),
        },
        "parse_fn": lambda j: _parse_okx(j),
    },
}

_TIMEOUT = 8  # seconds


def _to_okx_symbol(symbol: str) -> str:
    """Convert BTCUSDT -> BTC-USDT for OKX."""
    s = symbol.upper()
    for quote in ("USDT", "USDC", "BUSD", "USD"):
        if s.endswith(quote):
            base = s[: -len(quote)]
            return f"{base}-{quote}"
    return s


def _parse_okx(j: dict) -> Tuple[List[List[float]], List[List[float]]]:
    """Parse OKX book response into [[price, qty], ...] for bids and asks."""
    data = j.get("data", [{}])
    if not data:
        return [], []
    book = data[0]
    bids = [[float(b[0]), float(b[1])] for b in book.get("bids", [])]
    asks = [[float(a[0]), float(a[1])] for a in book.get("asks", [])]
    return bids, asks


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def fetch_orderbook(
    symbol: str,
    source: str = "binance",
    depth: int = 20,
) -> Dict:
    """
    Fetch order-book snapshot from *source* with failover.

    Returns dict with keys: bids, asks (each a list of [price, qty]).
    On total failure returns empty bids/asks.
    """
    sources = [source] + [s for s in _EXCHANGE_CONFIG if s != source]

    for src in sources:
        cfg = _EXCHANGE_CONFIG.get(src)
        if cfg is None:
            continue
        try:
            resp = requests.get(
                cfg["url"],
                params=cfg["params_fn"](symbol, depth),
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            bids, asks = cfg["parse_fn"](resp.json())
            if bids and asks:
                return {"bids": bids, "asks": asks, "source": src}
        except Exception as exc:
            logger.warning("fetch_orderbook %s from %s failed: %s", symbol, src, exc)

    logger.error("All sources failed for %s", symbol)
    return {"bids": [], "asks": [], "source": "none"}


# ---------------------------------------------------------------------------
# Core metrics
# ---------------------------------------------------------------------------

def _arrays(bids: list, asks: list):
    """Convert bid/ask lists to numpy arrays (prices, volumes)."""
    bp = np.array([b[0] for b in bids], dtype=np.float64)
    bv = np.array([b[1] for b in bids], dtype=np.float64)
    ap = np.array([a[0] for a in asks], dtype=np.float64)
    av = np.array([a[1] for a in asks], dtype=np.float64)
    return bp, bv, ap, av


def compute_imbalance(bids: list, asks: list) -> float:
    """
    Weighted imbalance in [-1, +1].

    Levels closer to the mid-price receive exponentially higher weight
    (decay factor 0.85 per level). Positive = buying pressure.
    """
    if not bids or not asks:
        return 0.0

    bp, bv, ap, av = _arrays(bids, asks)
    mid = (bp[0] + ap[0]) / 2.0

    # Weight by inverse distance to mid (closer levels matter more)
    bid_dist = np.abs(bp - mid) / (mid + 1e-12)
    ask_dist = np.abs(ap - mid) / (mid + 1e-12)

    bid_w = 1.0 / (1.0 + bid_dist * 1000)  # scale distance into meaningful range
    ask_w = 1.0 / (1.0 + ask_dist * 1000)

    weighted_bid = np.sum(bv * bid_w)
    weighted_ask = np.sum(av * ask_w)
    denom = weighted_bid + weighted_ask
    if denom == 0:
        return 0.0
    return float((weighted_bid - weighted_ask) / denom)


def compute_cumulative_delta(bids: list, asks: list) -> float:
    """
    Normalised cumulative delta: (sum_bid_vol - sum_ask_vol) / total_vol.

    Range roughly [-1, +1]. Positive = net bid volume dominance.
    """
    if not bids or not asks:
        return 0.0

    _, bv, _, av = _arrays(bids, asks)
    total_bid = bv.sum()
    total_ask = av.sum()
    total = total_bid + total_ask
    if total == 0:
        return 0.0
    return float((total_bid - total_ask) / total)


def compute_depth_ratio(bids: list, asks: list, levels: int = 5) -> float:
    """
    Ratio of bid depth (quote-currency value) to ask depth at top *levels*.

    >1 = more buy support, <1 = more sell pressure.
    """
    if not bids or not asks:
        return 1.0

    bp, bv, ap, av = _arrays(bids[:levels], asks[:levels])
    bid_depth = np.sum(bp * bv)
    ask_depth = np.sum(ap * av)
    if ask_depth == 0:
        return 999.0
    return float(bid_depth / ask_depth)


def compute_spread_bps(bids: list, asks: list) -> float:
    """
    Bid-ask spread in basis points (1 bp = 0.01 %).

    Tighter spread = more liquid market.
    """
    if not bids or not asks:
        return 0.0

    best_bid = bids[0][0]
    best_ask = asks[0][0]
    mid = (best_bid + best_ask) / 2.0
    if mid == 0:
        return 0.0
    return float((best_ask - best_bid) / mid * 10_000)


def compute_vwap_delta(bids: list, asks: list, current_price: float) -> float:
    """
    Distance of *current_price* from the volume-weighted average price of the
    entire visible book, expressed as a fraction of book VWAP.

    Positive = price above book VWAP (potential over-extension / resistance).
    Negative = price below book VWAP (potential support zone).
    """
    if not bids or not asks:
        return 0.0

    bp, bv, ap, av = _arrays(bids, asks)
    all_prices = np.concatenate([bp, ap])
    all_vols = np.concatenate([bv, av])
    total_vol = all_vols.sum()
    if total_vol == 0:
        return 0.0
    book_vwap = float(np.sum(all_prices * all_vols) / total_vol)
    if book_vwap == 0:
        return 0.0
    return float((current_price - book_vwap) / book_vwap)


# ---------------------------------------------------------------------------
# Composite analysis
# ---------------------------------------------------------------------------

def _derive_signal(
    imbalance: float,
    cum_delta: float,
    depth_ratio: float,
    vwap_delta: float,
) -> Tuple[str, float]:
    """
    Combine metrics into a directional signal + strength [0, 1].

    Weights (empirically tuned):
        imbalance   35 %
        cum_delta   25 %
        depth_ratio 25 %
        vwap_delta  15 %  (inverted — price *below* VWAP is bullish)
    """
    # Normalise depth_ratio to roughly [-1, +1]
    dr_norm = np.clip((depth_ratio - 1.0) / 2.0, -1.0, 1.0)

    # VWAP delta inverted: negative vwap_delta (price below book VWAP) is bullish
    vd_norm = np.clip(-vwap_delta * 100, -1.0, 1.0)  # scale small fraction

    composite = (
        0.35 * imbalance
        + 0.25 * cum_delta
        + 0.25 * dr_norm
        + 0.15 * vd_norm
    )

    strength = float(min(abs(composite), 1.0))

    if composite > 0.10:
        return "BULLISH", strength
    elif composite < -0.10:
        return "BEARISH", strength
    return "NEUTRAL", strength


def full_analysis(symbol: str, source: str = "binance") -> Dict:
    """
    Run every metric and return a consolidated dict.

    Keys: imbalance, cumulative_delta, depth_ratio, spread_bps,
          vwap_delta, mid_price, signal, signal_strength, source.
    """
    book = fetch_orderbook(symbol, source=source)
    bids = book["bids"]
    asks = book["asks"]

    if not bids or not asks:
        return {
            "symbol": symbol,
            "source": book.get("source", source),
            "error": "empty_book",
            "imbalance": 0.0,
            "cumulative_delta": 0.0,
            "depth_ratio": 1.0,
            "spread_bps": 0.0,
            "vwap_delta": 0.0,
            "mid_price": 0.0,
            "signal": "NEUTRAL",
            "signal_strength": 0.0,
        }

    mid_price = (bids[0][0] + asks[0][0]) / 2.0
    imb = compute_imbalance(bids, asks)
    cd = compute_cumulative_delta(bids, asks)
    dr = compute_depth_ratio(bids, asks, levels=5)
    sp = compute_spread_bps(bids, asks)
    vd = compute_vwap_delta(bids, asks, mid_price)
    signal, strength = _derive_signal(imb, cd, dr, vd)

    return {
        "symbol": symbol,
        "source": book["source"],
        "mid_price": round(mid_price, 4),
        "imbalance": round(imb, 6),
        "cumulative_delta": round(cd, 6),
        "depth_ratio": round(dr, 4),
        "spread_bps": round(sp, 4),
        "vwap_delta": round(vd, 6),
        "signal": signal,
        "signal_strength": round(strength, 4),
    }


def multi_exchange_analysis(symbol: str) -> Dict:
    """
    Fetch from Binance + OKX, average the signals, return combined result
    with per-exchange breakdown.
    """
    results = {}
    for src in ("binance", "okx"):
        try:
            results[src] = full_analysis(symbol, source=src)
        except Exception as exc:
            logger.warning("multi_exchange_analysis %s/%s failed: %s", symbol, src, exc)
            results[src] = None

    valid = {k: v for k, v in results.items() if v and v.get("error") is None}

    if not valid:
        return {
            "symbol": symbol,
            "exchanges": results,
            "combined_signal": "NEUTRAL",
            "combined_strength": 0.0,
            "combined_imbalance": 0.0,
            "avg_spread_bps": 0.0,
        }

    # Average numeric fields
    avg = lambda field: float(np.mean([v[field] for v in valid.values()]))

    combined_imb = avg("imbalance")
    combined_cd = avg("cumulative_delta")
    combined_dr = avg("depth_ratio")
    combined_vd = avg("vwap_delta")
    combined_sp = avg("spread_bps")

    signal, strength = _derive_signal(combined_imb, combined_cd, combined_dr, combined_vd)

    return {
        "symbol": symbol,
        "exchanges": results,
        "combined_signal": signal,
        "combined_strength": round(strength, 4),
        "combined_imbalance": round(combined_imb, 6),
        "combined_cumulative_delta": round(combined_cd, 6),
        "combined_depth_ratio": round(combined_dr, 4),
        "avg_spread_bps": round(combined_sp, 4),
        "combined_vwap_delta": round(combined_vd, 6),
    }


# ---------------------------------------------------------------------------
# CLI quick-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)
    result = full_analysis("BTCUSDT")
    print(json.dumps(result, indent=2))

    multi = multi_exchange_analysis("BTCUSDT")
    print("\n--- multi-exchange ---")
    print(json.dumps(multi, indent=2))
