"""Core flip logic, types, and symbol normalization."""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Tuple

# Import config values - these files are created in parallel,
# so use lazy defaults if config not yet available
try:
    from sandbox.config import DEFAULT_TP_PCT, DEFAULT_SL_PCT, EXPIRATION_SECONDS
except ImportError:
    DEFAULT_TP_PCT = 5.0
    DEFAULT_SL_PCT = 3.0
    EXPIRATION_SECONDS = 86400


@dataclass
class NormalizedPick:
    symbol: str
    original_direction: str
    opposite_direction: str
    entry_price: float
    original_tp: float
    original_sl: float
    opposite_tp: float
    opposite_sl: float
    source_engine: str
    source_pick_id: str
    picked_at: str
    expiration_at: str
    confidence: float = 0.0


# ── Symbol normalization ────────────────────────────────────────────

_STRIP_SUFFIXES = ["-USD", "/USDT", "/USD", "USDT", "USD"]

def normalize_symbol(raw: str) -> str:
    """Normalize any symbol variant to XXXUSDT format.

    Examples:
        BTC-USD   → BTCUSDT
        BTCUSD    → BTCUSDT
        BTC       → BTCUSDT
        ETHUSDT   → ETHUSDT
        ETH/USD   → ETHUSDT
    """
    s = raw.upper().strip()
    if s.endswith("USDT"):
        return s
    for suffix in _STRIP_SUFFIXES:
        if s.endswith(suffix):
            s = s[: -len(suffix)]
            break
    return s + "USDT"


# ── Direction flip ──────────────────────────────────────────────────

def flip_direction(direction: str) -> str:
    """LONG → SHORT, SHORT → LONG. Also handles BUY/SELL."""
    d = direction.upper().strip()
    if d in ("LONG", "BUY"):
        return "SHORT"
    return "LONG"


# ── Distance-based TP/SL inversion ─────────────────────────────────

def flip_tp_sl(
    entry: float,
    tp: float,
    sl: float,
    original_direction: str,
) -> Tuple[float, float]:
    """Compute opposite TP/SL using distance from entry.

    For LONG→SHORT: new_tp = entry - |tp - entry|, new_sl = entry + |entry - sl|
    For SHORT→LONG: new_tp = entry + |entry - tp|, new_sl = entry - |sl - entry|
    """
    dist_tp = abs(tp - entry)
    dist_sl = abs(sl - entry)

    if original_direction.upper() in ("LONG", "BUY"):
        # Flipping to SHORT
        return round(entry - dist_tp, 8), round(entry + dist_sl, 8)
    else:
        # Flipping to LONG
        return round(entry + dist_tp, 8), round(entry - dist_sl, 8)


def default_tp_sl(entry: float, direction: str) -> Tuple[float, float]:
    """Generate default TP/SL when source doesn't provide them."""
    tp_dist = entry * DEFAULT_TP_PCT / 100
    sl_dist = entry * DEFAULT_SL_PCT / 100
    if direction.upper() in ("LONG", "BUY"):
        return round(entry + tp_dist, 8), round(entry - sl_dist, 8)
    return round(entry - tp_dist, 8), round(entry + sl_dist, 8)


def make_pick_id(source_engine: str, symbol: str, direction: str, timestamp: str) -> str:
    """Generate a unique pick ID."""
    return f"opp::{source_engine}::{symbol}::{direction}::{timestamp[:19]}"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def expiration_from(picked_at: str) -> str:
    dt = datetime.fromisoformat(picked_at.replace("Z", "+00:00"))
    exp = dt + timedelta(seconds=EXPIRATION_SECONDS)
    return exp.strftime("%Y-%m-%dT%H:%M:%SZ")
