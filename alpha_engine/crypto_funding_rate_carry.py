"""
crypto_funding_rate_carry.py -- Crypto Funding Rate Carry Strategy
==================================================================
Academic basis: Liu & Tsyvinski (RFS 2021) "Risks and Returns of Cryptocurrency"

Core thesis: Negative funding rates signal crowded shorts paying longs.
Entering a long position captures the carry (funding payment) plus
directional mean-reversion when shorts unwind.

Signal logic:
  LONG when 8h funding < -0.01% (shorts paying longs)
  EXIT  when funding flips positive OR max_hold_hours reached

Forced resolution:
  max_hold_hours = 72  (3 days of 8h funding settlements)
  tp_pct = 5.0%
  sl_pct = 3.0%
  time_exit_at_market = True

Data sources (all free, no API key):
  Primary: Binance fapi -> Bybit -> OKX -> Coinglass (via crypto_data_failover)
  Proxy fallback: yfinance perpetual-spot basis (BTCUSD perpetual vs BTC-USD spot)

Universe: BTC, ETH, SOL (top-3 by market cap)

Usage:
    python -m alpha_engine.crypto_funding_rate_carry
    python alpha_engine/crypto_funding_rate_carry.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Windows UTF-8 fix
if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Multi-source funding rate fetcher (Binance -> Bybit -> OKX -> Coinglass)
try:
    from alpha_engine.crypto_data_failover import (
        fetch_funding_rate as _fetch_funding_rate,
    )
    _HAS_FAILOVER = True
except ImportError:
    try:
        from crypto_data_failover import (  # type: ignore[no-redef]
            fetch_funding_rate as _fetch_funding_rate,
        )
        _HAS_FAILOVER = True
    except ImportError:
        _HAS_FAILOVER = False
        _fetch_funding_rate = None  # type: ignore[assignment]

_log = logging.getLogger("alpha_engine.crypto_funding_rate_carry")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
STRATEGY_NAME = "crypto_funding_rate_carry"
ACADEMIC_CITATION = "Liu-Tsyvinski (RFS 2021)"
CATEGORY = "crypto"

# Universe: top-3 by market cap
UNIVERSE: List[str] = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
UNIVERSE_YF: Dict[str, Tuple[str, str]] = {
    "BTCUSDT": ("BTC-USD", "BTCUSD=X"),
    "ETHUSDT": ("ETH-USD", "ETHUSD=X"),
    "SOLUSDT": ("SOL-USD", "SOLUSD=X"),
}

# Funding rate threshold: -0.01% per 8h (shorts paying longs)
FUNDING_THRESHOLD = -0.0001  # -0.01% as decimal

# Confidence scaling
CONFIDENCE_BASE = 0.55
CONFIDENCE_SCALE = 800.0  # confidence = base + |rate| * scale, capped at 0.90
CONFIDENCE_CAP = 0.90

# Forced resolution parameters
MAX_HOLD_HOURS = 72
TP_PCT = 5.0   # 5% take profit
SL_PCT = 3.0   # 3% stop loss
TIME_EXIT_AT_MARKET = True

# Binance fallback endpoints for spot/mark price
BINANCE_FAPI_BASES = [
    "https://fapi.binance.com",
    "https://fapi1.binance.com",
    "https://fapi2.binance.com",
]
BINANCE_SPOT_BASES = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://data-api.binance.vision",
    "https://api.binance.us",
]

REQUEST_TIMEOUT = 10

# Output
_DATA_DIR = Path(__file__).resolve().parent / "data"
OUTPUT_PATH = _DATA_DIR / "crypto_funding_carry_picks.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now_time_tag() -> str:
    return datetime.now(timezone.utc).strftime("%H%M")


def _annualized_pct(rate_8h: float) -> float:
    return rate_8h * 3 * 365 * 100


def _fetch_json(url: str, timeout: int = REQUEST_TIMEOUT) -> Optional[Any]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine-FundingCarry/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def _smart_round(v: float) -> float:
    a = abs(v)
    if a >= 100:
        return round(v, 2)
    elif a >= 1:
        return round(v, 4)
    elif a >= 0.01:
        return round(v, 6)
    return round(v, 10)


# ---------------------------------------------------------------------------
# Data fetchers
# ---------------------------------------------------------------------------
def _fetch_funding_rate_primary(symbol: str) -> Optional[float]:
    """Fetch via multi-source failover (Binance -> Bybit -> OKX -> Coinglass)."""
    if _HAS_FAILOVER and _fetch_funding_rate is not None:
        try:
            rate = _fetch_funding_rate(symbol)
            if rate is not None:
                return float(rate)
        except Exception as exc:
            _log.debug("Failover fetch_funding_rate(%s) failed: %s", symbol, exc)
    return None


def _fetch_funding_rate_binance_direct(symbol: str) -> Optional[float]:
    """Direct Binance fapi premiumIndex fallback."""
    for base in BINANCE_FAPI_BASES:
        data = _fetch_json(f"{base}/fapi/v1/premiumIndex")
        if data and isinstance(data, list):
            for item in data:
                if item.get("symbol") == symbol:
                    try:
                        return float(item["lastFundingRate"])
                    except (KeyError, ValueError, TypeError):
                        continue
    return None


def _fetch_mark_price(symbol: str) -> Optional[float]:
    """Fetch mark price from Binance premiumIndex."""
    for base in BINANCE_FAPI_BASES:
        data = _fetch_json(f"{base}/fapi/v1/premiumIndex?symbol={symbol}")
        if data and isinstance(data, dict):
            try:
                return float(data["markPrice"])
            except (KeyError, ValueError, TypeError):
                continue
    return None


def _fetch_spot_price(symbol: str) -> Optional[float]:
    """Fetch spot price from Binance spot API."""
    for base in BINANCE_SPOT_BASES:
        data = _fetch_json(f"{base}/api/v3/ticker/price?symbol={symbol}")
        if data and isinstance(data, dict):
            try:
                return float(data["price"])
            except (KeyError, ValueError, TypeError):
                continue
    return None


def _compute_basis_proxy(symbol: str) -> Optional[float]:
    """
    Proxy funding signal: perpetual-spot basis via yfinance.

    basis = (perp_price - spot_price) / spot_price
    Negative basis (backwardation) implies negative funding.

    This is a coarse proxy -- real funding rates from the failover chain
    are always preferred. Used only when all other sources fail.
    """
    yf_pair = UNIVERSE_YF.get(symbol)
    if not yf_pair:
        return None

    try:
        import yfinance as yf
    except ImportError:
        _log.debug("yfinance not installed; basis proxy unavailable")
        return None

    perp_ticker, spot_ticker = yf_pair
    try:
        perp_data = yf.download(perp_ticker, period="2d", interval="1h", progress=False)
        spot_data = yf.download(spot_ticker, period="2d", interval="1h", progress=False)
        if perp_data.empty or spot_data.empty:
            return None

        perp_close = float(perp_data["Close"].iloc[-1])
        spot_close = float(spot_data["Close"].iloc[-1])
        if spot_close <= 0:
            return None

        basis = (perp_close - spot_close) / spot_close
        _log.info("Basis proxy %s: perp=%.2f spot=%.2f basis=%.6f",
                  symbol, perp_close, spot_close, basis)
        return basis
    except Exception as exc:
        _log.debug("yfinance basis proxy for %s failed: %s", symbol, exc)
        return None


def _get_funding_rate(symbol: str) -> Tuple[Optional[float], str]:
    """Fetch funding rate with full fallback chain.

    Returns (rate, source_label).
    """
    # 1. Multi-source failover (Binance -> Bybit -> OKX -> Coinglass)
    rate = _fetch_funding_rate_primary(symbol)
    if rate is not None:
        return rate, "failover"

    # 2. Direct Binance fapi
    rate = _fetch_funding_rate_binance_direct(symbol)
    if rate is not None:
        return rate, "binance_direct"

    # 3. yfinance basis proxy
    basis = _compute_basis_proxy(symbol)
    if basis is not None:
        return basis, "yfinance_basis_proxy"

    return None, "none"


def _compute_confidence(rate: float) -> float:
    """Scale confidence with funding rate magnitude.

    More negative funding -> higher confidence (more crowded short trade).
    At threshold (-0.01%): ~0.55
    At -0.05%: 0.55 + 0.0005 * 800 = 0.95 -> capped at 0.90
    """
    return min(CONFIDENCE_CAP, CONFIDENCE_BASE + abs(rate) * CONFIDENCE_SCALE)


# ---------------------------------------------------------------------------
# Core scan
# ---------------------------------------------------------------------------
def scan_crypto_funding_carry(verbose: bool = True) -> List[Dict[str, Any]]:
    """
    Scan BTC/ETH/SOL funding rates. Generate LONG picks when funding is
    negative enough (< -0.01%/8h), meaning shorts are paying longs.

    Returns list of pick dicts compatible with the active_picks schema.
    """
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    now_utc = datetime.now(timezone.utc)
    now_str = _now_iso()
    date_str = _now_date()
    time_tag = _now_time_tag()

    if verbose:
        print("=" * 65)
        print("  CRYPTO FUNDING RATE CARRY STRATEGY")
        print(f"  Academic basis: {ACADEMIC_CITATION}")
        print(f"  Scan time: {now_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print("=" * 65)

    picks: List[Dict[str, Any]] = []

    for symbol in UNIVERSE:
        if verbose:
            print(f"\n  Scanning {symbol}...", end="", flush=True)

        # Fetch funding rate
        rate, source = _get_funding_rate(symbol)
        if rate is None:
            if verbose:
                print(" [SKIP -- no funding data]")
            _log.warning("No funding rate data for %s from any source", symbol)
            continue

        ann_rate = _annualized_pct(rate)
        rate_pct = rate * 100

        # Fetch entry price (mark preferred, spot fallback)
        entry_price = _fetch_mark_price(symbol)
        price_source = "mark"
        if entry_price is None or entry_price <= 0:
            entry_price = _fetch_spot_price(symbol)
            price_source = "spot"
        if entry_price is None or entry_price <= 0:
            if verbose:
                print(" [SKIP -- no price data]")
            continue

        # Signal logic: LONG when funding < -0.01% (shorts paying longs)
        if rate >= FUNDING_THRESHOLD:
            if verbose:
                direction_label = "NEUTRAL" if rate < 0.0005 else "AVOID (positive funding)"
                print(
                    f" [{direction_label}] "
                    f"FR={rate_pct:+.4f}%/8h ({ann_rate:+.1f}% ann) "
                    f"Entry={_smart_round(entry_price)} "
                    f"src={source}"
                )
            continue

        # Negative funding below threshold -> LONG signal
        confidence = _compute_confidence(rate)
        tp_price = _smart_round(entry_price * (1 + TP_PCT / 100))
        sl_price = _smart_round(entry_price * (1 - SL_PCT / 100))

        pick_id = f"{STRATEGY_NAME}::{symbol}::{date_str}_{time_tag}"

        pick = {
            "id": pick_id,
            "strategy": STRATEGY_NAME,
            "symbol": symbol,
            "category": CATEGORY,
            "signal_type": "BUY",
            "direction": "LONG",
            "entry_price": _smart_round(entry_price),
            "entry_date": date_str,
            "take_profit": tp_price,
            "stop_loss": sl_price,
            "tp_pct": TP_PCT,
            "sl_pct": SL_PCT,
            "confidence": round(confidence, 3),
            "ml_score": round(confidence, 3),
            "status": "OPEN",
            "reason": (
                f"Funding Rate Carry ({ACADEMIC_CITATION}) | "
                f"8h FR: {rate_pct:+.4f}% ({ann_rate:+.1f}% ann) | "
                f"Shorts paying longs -> contrarian LONG | "
                f"Threshold: {FUNDING_THRESHOLD*100:.4f}% | "
                f"Data source: {source}"
            ),
            "source_system": "alpha_engine",
            "trader_name": STRATEGY_NAME,
            # Forced resolution config
            "forced_resolution": {
                "max_hold_hours": MAX_HOLD_HOURS,
                "tp_pct": TP_PCT,
                "sl_pct": SL_PCT,
                "time_exit_at_market": TIME_EXIT_AT_MARKET,
            },
            # Academic metadata
            "academic_citation": ACADEMIC_CITATION,
            "strategy_type": "funding_carry",
            # Funding data
            "funding_rate_8h": round(rate, 8),
            "funding_rate_pct": round(rate_pct, 6),
            "funding_rate_annualized": round(ann_rate, 2),
            "funding_data_source": source,
            # Pricing
            "price_source": price_source,
            "mark_price": _smart_round(entry_price),
            # Standard fields
            "exit_price": None,
            "exit_date": None,
            "exit_reason": None,
            "pnl_pct": None,
            "pnl_dollar": None,
            "hold_days": None,
            "allocation": 200.0,
            "position_sizing": "funding_carry",
            "risk_per_trade_pct": 0.02,
            "max_safe_leverage": 2.0,
            "leverage": 2.0,
            "forward_trades": 0,
            "forward_wr": 0.0,
            "forward_validated": False,
            "elite_score": 0,
            "elite_grade": "N/A",
            "unrealized_pnl": 0,
            "open_time": now_str,
            "timestamp": now_str,
        }

        picks.append(pick)

        if verbose:
            print(
                f" [LONG] FR={rate_pct:+.4f}%/8h "
                f"({ann_rate:+.1f}% ann) "
                f"Conf={confidence:.0%} "
                f"Entry={_smart_round(entry_price)} "
                f"TP={tp_price} SL={sl_price} "
                f"src={source}"
            )

    # Save output
    payload = {
        "scanned_at": now_str,
        "strategy": STRATEGY_NAME,
        "academic_citation": ACADEMIC_CITATION,
        "description": (
            "Contrarian carry trade: LONG when 8h funding < -0.01% "
            "(shorts paying longs). Per Liu & Tsyvinski (RFS 2021)."
        ),
        "universe": UNIVERSE,
        "funding_threshold_pct": FUNDING_THRESHOLD * 100,
        "forced_resolution": {
            "max_hold_hours": MAX_HOLD_HOURS,
            "tp_pct": TP_PCT,
            "sl_pct": SL_PCT,
            "time_exit_at_market": TIME_EXIT_AT_MARKET,
        },
        "picks_generated": len(picks),
        "picks": picks,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    if verbose:
        print(f"\n  {'=' * 50}")
        print(f"  Picks generated: {len(picks)}")
        for p in picks:
            print(
                f"    {p['symbol']:<10} "
                f"FR={p['funding_rate_pct']:+.4f}%  "
                f"Conf={p['confidence']:.0%}  "
                f"Entry={p['entry_price']}"
            )
        print(f"  Saved -> {OUTPUT_PATH}")
        print(f"  {'=' * 50}")

    return picks


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def run() -> List[Dict[str, Any]]:
    """Entry point callable from workflows and other modules."""
    picks = scan_crypto_funding_carry(verbose=True)
    _log.info("Crypto Funding Rate Carry complete: %d picks generated", len(picks))
    return picks


if __name__ == "__main__":
    run()
