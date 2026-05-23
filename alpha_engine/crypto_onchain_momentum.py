"""
ALPHA_ENGINE -- crypto_onchain_momentum strategy
================================================
On-chain accumulation/distribution signals using Glassnode MVRV-Z + confirmations.

Logic (per Grok-4 #3 of reports/edge_research_synthesis_2026_05_12.md):
  LONG  when MVRV-Z < -0.5 (oversold accumulation)
              AND active addresses rising over 30d (network growth)
  SHORT when MVRV-Z > 2.0 (overbought distribution)
              AND exchange balance falling over 30d
              (coins leaving exchanges yet price extended => smart money exit)

Universe: BTCUSDT, ETHUSDT (Glassnode free tier).
Confidence: scaled 0.55-0.75 by signal extremity.
Default-OFF unless CRYPTO_ONCHAIN_MOMENTUM_ENABLED=1.
Expected: PF ~1.7, ~20h hold (Grok-4 synthesis).

Family: structure
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Optional

# Make sibling tools/ importable when running from repo root
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from tools import glassnode_data_fetcher as glass
except ImportError:
    glass = None  # type: ignore


STRATEGY_NAME = "crypto_onchain_momentum"
ENABLED_ENV_VAR = "CRYPTO_ONCHAIN_MOMENTUM_ENABLED"

# Signal thresholds (Grok-4 synthesis)
MVRV_Z_LONG_THRESHOLD = -0.5   # below = oversold/accumulation
MVRV_Z_SHORT_THRESHOLD = 2.0   # above = overbought/distribution

# Asset -> trading symbol mapping
_ASSET_TO_SYMBOL = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
}


def is_enabled() -> bool:
    """Default-OFF gate."""
    return os.environ.get(ENABLED_ENV_VAR, "0").strip() == "1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _confidence_long(mvrv_z: float) -> float:
    """More-negative MVRV-Z => higher confidence. Range 0.55-0.75."""
    # Map [-0.5, -2.5] -> [0.55, 0.75]
    depth = max(0.0, (MVRV_Z_LONG_THRESHOLD - mvrv_z) / 2.0)
    return round(min(0.75, 0.55 + depth * 0.20), 2)


def _confidence_short(mvrv_z: float) -> float:
    """Higher MVRV-Z => higher confidence. Range 0.55-0.75."""
    # Map [2.0, 4.0] -> [0.55, 0.75]
    height = max(0.0, (mvrv_z - MVRV_Z_SHORT_THRESHOLD) / 2.0)
    return round(min(0.75, 0.55 + height * 0.20), 2)


def _evaluate_asset(asset: str) -> Optional[dict]:
    """Evaluate one asset (BTC or ETH). Returns pick dict or None."""
    if glass is None:
        return None

    mvrv_series = glass.fetch_mvrv_z(asset)
    mvrv_z = glass.latest_value(mvrv_series)
    if mvrv_z is None:
        return None

    symbol = _ASSET_TO_SYMBOL.get(asset.upper())
    if not symbol:
        return None

    # LONG: oversold + active addresses rising
    if mvrv_z < MVRV_Z_LONG_THRESHOLD:
        aa_series = glass.fetch_active_addresses(asset)
        aa_trend = glass.trend_30d(aa_series)
        if aa_trend is None or aa_trend <= 0.0:
            return None
        return {
            "strategy": STRATEGY_NAME,
            "symbol": symbol,
            "asset_class": "CRYPTO",
            "category": "crypto",
            "signal_type": "LONG",
            "side": "LONG",
            "confidence": _confidence_long(mvrv_z),
            "timeframe": "1d",
            "expected_hold_hours": 20,
            "reason": (
                f"MVRV-Z {mvrv_z:.2f} below {MVRV_Z_LONG_THRESHOLD} (accumulation); "
                f"active-addresses 30d trend +{aa_trend*100:.1f}%"
            ),
            "extra": {
                "mvrv_z_score": round(mvrv_z, 3),
                "active_addr_trend_30d": round(aa_trend, 4),
                "source": "Glassnode MVRV-Z + active addresses",
            },
            "timestamp": _now_iso(),
        }

    # SHORT: overbought + exchange balance falling
    if mvrv_z > MVRV_Z_SHORT_THRESHOLD:
        eb_series = glass.fetch_exchange_balance(asset)
        eb_trend = glass.trend_30d(eb_series)
        if eb_trend is None or eb_trend >= 0.0:
            return None
        return {
            "strategy": STRATEGY_NAME,
            "symbol": symbol,
            "asset_class": "CRYPTO",
            "category": "crypto",
            "signal_type": "SHORT",
            "side": "SHORT",
            "confidence": _confidence_short(mvrv_z),
            "timeframe": "1d",
            "expected_hold_hours": 20,
            "reason": (
                f"MVRV-Z {mvrv_z:.2f} above {MVRV_Z_SHORT_THRESHOLD} (distribution); "
                f"exchange-balance 30d trend {eb_trend*100:.1f}%"
            ),
            "extra": {
                "mvrv_z_score": round(mvrv_z, 3),
                "exchange_balance_trend_30d": round(eb_trend, 4),
                "source": "Glassnode MVRV-Z + exchange balance",
            },
            "timestamp": _now_iso(),
        }

    return None


def generate_signals(data: Optional[dict] = None) -> list[dict]:
    """Return list of pick dicts. Empty list if disabled or no signals."""
    if not is_enabled():
        return []
    if glass is None:
        return []

    picks: list[dict] = []
    for asset in ("BTC", "ETH"):
        try:
            pick = _evaluate_asset(asset)
            if pick is not None:
                picks.append(pick)
        except Exception:
            continue
    return picks


# Standard entrypoint alias used by some callers
run = generate_signals
