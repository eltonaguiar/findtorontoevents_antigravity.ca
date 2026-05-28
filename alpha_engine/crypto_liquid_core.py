"""
CRYPTO liquid-core whitelist + BTC UTC death-zone filter (M-001 from EAGLE plan).

Two production gates for CRYPTO picks:

1. **Liquid-core whitelist (`is_in_liquid_core`)** — pick's symbol must be one of
   the top-25 crypto symbols by 30-day ADV (average daily volume). Hardcoded
   static list drawn from `config.py::CRYPTO_SYMBOLS`; refresh quarterly.

2. **BTC UTC death-zone (`is_in_btc_death_zone`)** — pick's entry hour (UTC)
   must not be in the empirically-worst hours for BTC continuation
   (peer-agent verified: 9, 10, 18, 21 UTC). These are low-WR thin-liquidity
   windows around US pre-market open and London/Asia handoff.

Both gates env-kill-switchable (default ON):
    CRYPTO_LIQUID_CORE_ENABLED=0       → disable whitelist gate
    CRYPTO_BTC_HOUR_GATE_ENABLED=0     → disable death-zone gate
    CRYPTO_BTC_DEATH_ZONE_HOURS=h,h,h  → override the 9,10,18,21 default
                                         (comma-separated UTC integers 0-23).

Refresh cadence (per swarm review 2026-05-28 feedback):
    LIQUID_CORE_TOP_25 and BTC_UTC_DEATH_ZONE_HOURS are stable enough that
    quarterly review off resolved-pick aggregates is sufficient. Track in
    incidents/enhancements feed as ENH-LIQUID-CORE-REFRESH (quarterly cron).
    The CRYPTO_BTC_DEATH_ZONE_HOURS env override exists for emergency
    regime-shift / DST-anomaly response without a code deploy.

Wired into: audit_trail/quality_gates.py::passes_active_gate().
Addresses: CRYPTO 47% raw skew + 29% WR quan_engine drag — only 1/229 picks
land on the canonical edge `crypto_liquidity_wick_reversal_v1`; the rest is
illiquid alt long-tail.

Failure mode: fail-OPEN. Any exception inside a helper returns "no block"
so the gate never breaks admission on import or parse error.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Optional


# Top-25 by 30-day ADV (sourced from config.py::CRYPTO_SYMBOLS,
# common Binance USDT pairs + USD aliases). Hardcoded static list —
# liquidity rankings are stable enough that quarterly refresh suffices.
LIQUID_CORE_TOP_25 = frozenset({
    "BTC", "ETH", "BNB", "SOL", "XRP",
    "ADA", "DOGE", "AVAX", "LINK", "DOT",
    "MATIC", "ATOM", "LTC", "UNI", "NEAR",
    "ARB", "OP", "FIL", "ETC", "APT",
    "INJ", "SUI", "TIA", "SEI", "PYTH",
})

# UTC hours with empirically low BTC continuation WR
# (peer-agent verified — refresh quarterly off resolved picks).
# Override via env CRYPTO_BTC_DEATH_ZONE_HOURS="9,10,18,21" for regime-shift response.
BTC_UTC_DEATH_ZONE_HOURS_DEFAULT = (9, 10, 18, 21)


def _get_death_zone_hours() -> tuple:
    """Read env override or fall back to the default tuple. Invalid envs fail-open
    to the default (never throws). Returned as a tuple of ints (0-23)."""
    env_val = os.environ.get("CRYPTO_BTC_DEATH_ZONE_HOURS", "")
    if not env_val.strip():
        return BTC_UTC_DEATH_ZONE_HOURS_DEFAULT
    try:
        hours = tuple(sorted({
            int(x.strip()) for x in env_val.split(",")
            if x.strip() and 0 <= int(x.strip()) <= 23
        }))
        return hours if hours else BTC_UTC_DEATH_ZONE_HOURS_DEFAULT
    except (ValueError, TypeError):
        return BTC_UTC_DEATH_ZONE_HOURS_DEFAULT


# Backwards-compat alias: existing call sites read BTC_UTC_DEATH_ZONE_HOURS directly.
BTC_UTC_DEATH_ZONE_HOURS = BTC_UTC_DEATH_ZONE_HOURS_DEFAULT


def _extract_base_symbol(symbol: str) -> Optional[str]:
    """Strip quote suffix from common formats. Returns uppercase base or None.

    Handles: BTCUSDT, BTC-USDT, BTC/USD, BTCUSD, BTC-USD, BTC, btc-usd, etc.
    """
    if not symbol:
        return None
    s = str(symbol).upper().strip()
    if not s:
        return None
    # Normalize separators
    for sep in ("-", "/", "_", ":"):
        if sep in s:
            s = s.split(sep)[0]
            break
    else:
        # No separator — try stripping known quote suffixes
        for quote in ("USDT", "USDC", "BUSD", "USD", "DAI", "BTC", "ETH"):
            if s.endswith(quote) and len(s) > len(quote):
                s = s[: -len(quote)]
                break
    return s or None


def is_in_liquid_core(symbol: str) -> bool:
    """Return True if `symbol` is in the top-25 liquid-core whitelist.

    Gate is no-op (returns True for everything) when
    CRYPTO_LIQUID_CORE_ENABLED=0/false/False. Fail-open on any error.
    """
    try:
        if os.environ.get("CRYPTO_LIQUID_CORE_ENABLED", "1") in ("0", "false", "FALSE", "False"):
            return True  # gate disabled — admit everything
        base = _extract_base_symbol(symbol)
        if base is None:
            return True  # fail-open: unparsable symbol → don't block
        return base in LIQUID_CORE_TOP_25
    except Exception:
        return True  # fail-open


def is_in_btc_death_zone(submitted_at_iso: str) -> bool:
    """Return True if `submitted_at_iso` falls in a BTC UTC death-zone hour.

    Accepts ISO 8601 strings with or without 'Z' / explicit offset. Naive
    timestamps are treated as already-UTC (resolver convention).

    Gate is no-op (returns False, i.e. "not in death zone") when
    CRYPTO_BTC_HOUR_GATE_ENABLED=0/false/False. Fail-open on any error.
    """
    try:
        if os.environ.get("CRYPTO_BTC_HOUR_GATE_ENABLED", "1") in ("0", "false", "FALSE", "False"):
            return False  # gate disabled — never flag as death zone
        if not submitted_at_iso:
            return False  # fail-open: missing timestamp → don't block
        s = str(submitted_at_iso).strip()
        # Python <3.11 fromisoformat doesn't grok trailing 'Z'
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            # Last resort: try first 19 chars as naive UTC
            try:
                dt = datetime.fromisoformat(s[:19])
            except Exception:
                return False  # fail-open
        return dt.hour in _get_death_zone_hours()
    except Exception:
        return False  # fail-open
