#!/usr/bin/env python3
"""
Funding Rate + Open Interest Signal Engine
===========================================
Fetches funding rates and open interest from Binance Futures API (with
failover) and computes contrarian signals for crypto picks.

Signals:
  - funding_signal: extreme positive (>0.05%) = crowded long -> contrarian SHORT.
                    extreme negative (<-0.03%) = crowded short -> contrarian LONG.
  - oi_trend: rising OI + rising price = bullish continuation.
              rising OI + falling price = bearish (shorts piling in).

Output: alpha_engine/data/funding_rate_signals.json

Uses api_failover.py for all HTTP calls (3+ Binance fapi mirrors + Bybit).
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Windows UTF-8 fix
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

# Ensure repo root on path for imports
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from alpha_engine.api_failover import (
    BINANCE_FAPI_BASES,
    _http_get_json,
    _normalize_symbol,
)

_log = logging.getLogger("alpha_engine.funding_rate_signal")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

# ---------------------------------------------------------------------------
# Top symbols by perpetual futures volume (hardcoded universe — avoids an
# extra API call; updated periodically)
# ---------------------------------------------------------------------------
TOP_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT",
    "NEARUSDT", "SUIUSDT", "ARBUSDT", "OPUSDT", "APTUSDT",
    "INJUSDT", "FETUSDT", "PEPEUSDT", "WIFUSDT", "RENDERUSDT",
    "TONUSDT", "TRXUSDT", "LTCUSDT", "BCHUSDT", "ETCUSDT",
    "HBARUSDT", "SEIUSDT", "TIAUSDT", "ONDOUSDT", "TAOUSDT",
]

# ---------------------------------------------------------------------------
# Thresholds (basis points expressed as decimal fractions)
# Normal funding = ~0.01% (0.0001). Extreme = >0.05% or < -0.03%.
# ---------------------------------------------------------------------------
EXTREME_LONG_THRESHOLD = 0.0005   # 0.05% — longs paying heavily, crowded long
EXTREME_SHORT_THRESHOLD = -0.0003  # -0.03% — shorts paying, crowded short

DATA_DIR = Path(__file__).resolve().parent / "data"
OUTPUT_PATH = DATA_DIR / "funding_rate_signals.json"


def _fetch_premium_index_all() -> List[Dict[str, Any]]:
    """Fetch premiumIndex for ALL symbols in one call (no per-symbol loop needed)."""
    for base in BINANCE_FAPI_BASES:
        data = _http_get_json(f"{base}/fapi/v1/premiumIndex", timeout=8)
        if data and isinstance(data, list) and len(data) > 5:
            _log.info("premiumIndex: got %d symbols from %s", len(data), base)
            return data
    _log.warning("premiumIndex: all Binance fapi mirrors failed")
    return []


def _fetch_open_interest(symbol: str) -> Optional[float]:
    """Fetch open interest for a single symbol."""
    sym = _normalize_symbol(symbol)
    for base in BINANCE_FAPI_BASES:
        data = _http_get_json(f"{base}/fapi/v1/openInterest?symbol={sym}", timeout=5)
        if data and isinstance(data, dict) and "openInterest" in data:
            try:
                return float(data["openInterest"])
            except (ValueError, TypeError):
                continue
    return None


def _fetch_24h_change(symbol: str) -> Optional[float]:
    """Fetch 24h price change percent from the premium index ticker."""
    # We already have mark/index prices; use ticker for change%.
    sym = _normalize_symbol(symbol)
    for base in BINANCE_FAPI_BASES:
        data = _http_get_json(f"{base}/fapi/v1/ticker/24hr?symbol={sym}", timeout=5)
        if data and isinstance(data, dict) and "priceChangePercent" in data:
            try:
                return float(data["priceChangePercent"])
            except (ValueError, TypeError):
                continue
    return None


def compute_funding_signals() -> Dict[str, Any]:
    """
    Main entry point. Fetches funding rates and OI, computes signals.
    Returns dict keyed by symbol with signal data.
    """
    _log.info("=== Funding Rate Signal Engine starting ===")
    now_utc = datetime.now(timezone.utc).isoformat()

    # 1. Bulk-fetch all premium index data
    premium_data = _fetch_premium_index_all()
    premium_map: Dict[str, Dict] = {}
    for item in premium_data:
        sym = item.get("symbol", "")
        if sym:
            premium_map[sym] = item

    signals: Dict[str, Any] = {}
    symbols_processed = 0
    contrarian_long = 0
    contrarian_short = 0

    for symbol in TOP_SYMBOLS:
        sym = _normalize_symbol(symbol)
        pi = premium_map.get(sym)
        if not pi:
            continue

        try:
            funding_rate = float(pi.get("lastFundingRate", 0))
            mark_price = float(pi.get("markPrice", 0))
            index_price = float(pi.get("indexPrice", 0))
        except (ValueError, TypeError):
            continue

        # Compute funding signal
        funding_signal = "NEUTRAL"
        funding_strength = 0.0
        if funding_rate >= EXTREME_LONG_THRESHOLD:
            funding_signal = "CONTRARIAN_SHORT"  # longs crowded, fade them
            funding_strength = min(1.0, funding_rate / (EXTREME_LONG_THRESHOLD * 3))
            contrarian_short += 1
        elif funding_rate <= EXTREME_SHORT_THRESHOLD:
            funding_signal = "CONTRARIAN_LONG"  # shorts crowded, fade them
            funding_strength = min(1.0, abs(funding_rate) / (abs(EXTREME_SHORT_THRESHOLD) * 3))
            contrarian_long += 1

        # Fetch OI (rate-limited: only for top symbols)
        oi_value = _fetch_open_interest(sym)

        # Fetch 24h price change for OI trend interpretation
        price_change_24h = _fetch_24h_change(sym)

        # Compute OI trend signal
        oi_trend = "NEUTRAL"
        if oi_value and price_change_24h is not None:
            # We don't have historical OI in this simple version, so we use
            # funding rate as a proxy: rising funding + rising price = OI building on longs
            if funding_rate > 0.0001 and price_change_24h > 1.0:
                oi_trend = "BULLISH_CONTINUATION"
            elif funding_rate > 0.0001 and price_change_24h < -1.0:
                oi_trend = "LONG_LIQUIDATION_RISK"
            elif funding_rate < -0.0001 and price_change_24h < -1.0:
                oi_trend = "BEARISH_CONTINUATION"
            elif funding_rate < -0.0001 and price_change_24h > 1.0:
                oi_trend = "SHORT_SQUEEZE_RISK"

        signals[sym] = {
            "symbol": sym,
            "funding_rate": round(funding_rate, 8),
            "funding_rate_pct": round(funding_rate * 100, 4),
            "funding_signal": funding_signal,
            "funding_strength": round(funding_strength, 3),
            "mark_price": mark_price,
            "index_price": index_price,
            "open_interest": oi_value,
            "price_change_24h": price_change_24h,
            "oi_trend": oi_trend,
            "timestamp": now_utc,
        }
        symbols_processed += 1

        # Gentle rate limit to avoid 429s
        if symbols_processed % 10 == 0:
            time.sleep(0.5)

    result = {
        "generated_at": now_utc,
        "symbols_processed": symbols_processed,
        "contrarian_long_signals": contrarian_long,
        "contrarian_short_signals": contrarian_short,
        "signals": signals,
    }

    # Write output
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    _log.info(
        "=== Done: %d symbols, %d contrarian-LONG, %d contrarian-SHORT signals -> %s ===",
        symbols_processed, contrarian_long, contrarian_short, OUTPUT_PATH.name,
    )
    return result


if __name__ == "__main__":
    compute_funding_signals()
