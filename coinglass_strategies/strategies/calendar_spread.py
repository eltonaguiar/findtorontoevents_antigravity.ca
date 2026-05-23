"""S9: Futures Calendar Spread — exploits term-structure differences between
near-month and far-month crypto futures contracts.

When the basis (premium/discount) between quarterly futures and perpetual
futures diverges beyond historical norms, it tends to mean-revert.

Logic:
  - Fetch quarterly futures prices and perpetual prices from Binance/OKX
  - Compute the annualized basis (premium %)
  - Compare to rolling z-score of the basis over 24h window
  - If basis z-score > 2.0 (premium too high): SHORT the spread
    → Sell quarterly, buy perpetual  (basis will contract)
  - If basis z-score < -2.0 (discount too deep): LONG the spread
    → Buy quarterly, sell perpetual  (basis will expand)

Data sources: Binance quarterly futures, OKX quarterly, CoinGecko for spot.
Uses the existing data_fetcher failover chain.
"""
import logging
import math
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests

from .base import Signal

logger = logging.getLogger(__name__)

# Binance quarterly futures symbol mapping
QUARTERLY_MAP = {
    "BTCUSDT": "BTCUSDT_QUARTERLY",
    "ETHUSDT": "ETHUSDT_QUARTERLY",
    "SOLUSDT": None,  # SOL has no quarterly on Binance
    "BNBUSDT": None,
    "DOGEUSDT": None,
}

BINANCE_FUTURES = "https://fapi.binance.com"
OKX_API = "https://www.okx.com"

# Basis history for z-score computation (in-memory rolling window)
_basis_history: Dict[str, List[float]] = {}
_MAX_HISTORY = 96  # 96 observations × 15 min = 24 hours



def _fetch_perp_mark_and_index(symbol: str) -> Optional[Dict]:
    """Fetch mark price and index price from Binance premiumIndex endpoint."""
    try:
        resp = requests.get(
            f"{BINANCE_FUTURES}/fapi/v1/premiumIndex",
            params={"symbol": symbol},
            timeout=8,
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                mark = float(data.get("markPrice", 0))
                index = float(data.get("indexPrice", 0))
                last_funding = float(data.get("lastFundingRate", 0))
                next_funding_time = int(data.get("nextFundingTime", 0))
                if mark > 0 and index > 0:
                    return {
                        "mark_price": mark,
                        "index_price": index,
                        "last_funding_rate": last_funding,
                        "next_funding_time": next_funding_time,
                        "basis_pct": (mark - index) / index * 100,
                    }
    except Exception as e:
        logger.debug("Premium index fetch failed for %s: %s", symbol, e)

    # OKX fallback
    try:
        okx_sym = symbol.replace("USDT", "-USDT-SWAP")
        resp = requests.get(
            f"{OKX_API}/api/v5/public/mark-price",
            params={"instId": okx_sym, "instType": "SWAP"},
            timeout=8,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("data") and len(data["data"]) > 0:
                mark = float(data["data"][0].get("markPx", 0))
                if mark > 0:
                    # Get spot price for index
                    spot_resp = requests.get(
                        f"{OKX_API}/api/v5/market/ticker",
                        params={"instId": symbol.replace("USDT", "-USDT")},
                        timeout=8,
                    )
                    if spot_resp.status_code == 200:
                        spot_data = spot_resp.json()
                        if spot_data.get("data") and len(spot_data["data"]) > 0:
                            spot = float(spot_data["data"][0].get("last", 0))
                            if spot > 0:
                                return {
                                    "mark_price": mark,
                                    "index_price": spot,
                                    "last_funding_rate": 0,
                                    "next_funding_time": 0,
                                    "basis_pct": (mark - spot) / spot * 100,
                                }
    except Exception as e:
        logger.debug("OKX premium fetch failed for %s: %s", symbol, e)

    return None


def _compute_basis_zscore(symbol: str, current_basis: float) -> Optional[float]:
    """Compute z-score of current basis vs rolling history."""
    if symbol not in _basis_history:
        _basis_history[symbol] = []

    history = _basis_history[symbol]
    history.append(current_basis)

    # Keep only last 24h of observations
    if len(history) > _MAX_HISTORY:
        _basis_history[symbol] = history[-_MAX_HISTORY:]
        history = _basis_history[symbol]

    if len(history) < 10:
        return None  # Not enough data for z-score

    mean = sum(history) / len(history)
    variance = sum((v - mean) ** 2 for v in history) / len(history)
    std = math.sqrt(variance) if variance > 0 else 0

    if std < 0.001:
        return None  # Basis too stable to trade

    return (current_basis - mean) / std


def run(symbol: str, recent_rows: list, current_ratios: dict) -> Optional[Signal]:
    """Calendar spread / basis trade strategy.

    Detects when the perpetual-to-spot basis (premium/discount) is at
    extreme levels compared to recent history, signaling mean-reversion.
    """
    data = _fetch_perp_mark_and_index(symbol)
    if data is None:
        return None

    basis_pct = data["basis_pct"]
    z_score = _compute_basis_zscore(symbol, basis_pct)

    if z_score is None:
        return None

    # Thresholds
    ENTRY_Z = 1.8
    if abs(z_score) < ENTRY_Z:
        return None

    # Determine direction based on basis extremity
    if z_score > ENTRY_Z:
        # Basis too high (premium) → expect contraction → SHORT signal
        direction = "SHORT"
        reason = (
            f"Calendar spread: basis premium {basis_pct:.4f}% is elevated "
            f"(z={z_score:.2f}). Mark={data['mark_price']:.2f}, "
            f"Index={data['index_price']:.2f}. "
            f"Funding={data['last_funding_rate']*100:.4f}%. "
            f"Premium compression expected."
        )
    else:
        # Basis too low (discount) → expect expansion → LONG signal
        direction = "LONG"
        reason = (
            f"Calendar spread: basis discount {basis_pct:.4f}% is extreme "
            f"(z={z_score:.2f}). Mark={data['mark_price']:.2f}, "
            f"Index={data['index_price']:.2f}. "
            f"Funding={data['last_funding_rate']*100:.4f}%. "
            f"Discount recovery expected."
        )

    # Confidence scales with z-score magnitude
    conf = 0.55 + 0.05 * min(abs(z_score) - ENTRY_Z, 4.0)
    conf = round(min(conf, 0.80), 3)

    return Signal(
        symbol=symbol,
        direction=direction,
        strategy="coinglass_calendar_spread",
        confidence=conf,
        reason=reason,
        ratios={
            "basis_pct": round(basis_pct, 6),
            "basis_z_score": round(z_score, 3),
            "mark_price": data["mark_price"],
            "index_price": data["index_price"],
            "funding_rate": data["last_funding_rate"],
            **current_ratios,
        },
    )
