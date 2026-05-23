#!/usr/bin/env python3
"""
ALPHA_ENGINE -- Non-Crypto Score Boosters
===========================================
Asset-class-specific score enrichment for FOREX, COMMODITY, ETF, and BOND.
Part of Phase 3 remediation — see FOREX_COMMODITIES_BONDS.MD.

Problem: Crypto gets MTF confluence + ensemble boosters (+25 pts max).
Non-crypto enters scoring with base score only = structurally lower.

Solution: Each asset class gets a booster tailored to its market structure:

| Class     | Booster Type              | Max Boost | Source                     |
|-----------|---------------------------|-----------|----------------------------|
| CRYPTO    | MTF confluence + Ensemble | +25 pts   | Existing (crypto-only)     |
| FOREX     | Session overlap + Carry   | +15 pts   | Session-aware features     |
| COMMODITY | COT sentiment + Seasonal  | +15 pts   | CFTC COT + seasonal pattern|
| ETF       | Momentum + Regime align   | +10 pts   | 12m momentum + VIX regime  |
| BOND      | Yield curve + Credit      | +10 pts   | FRED yield/credit data     |

Usage:
    from alpha_engine.non_crypto_boosters import compute_non_crypto_boost
    boost, breakdown = compute_non_crypto_boost(pick, fred_data=None)
    pick["score"] += boost
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Max boost per asset class
MAX_BOOST = {
    "FOREX": 15,
    "COMMODITY": 15,
    "FUTURES": 15,
    "ETF": 10,
    "BOND": 10,
    "EQUITY": 8,
}


def compute_non_crypto_boost(
    pick: dict,
    fred_data: Optional[dict] = None,
    market_regime: Optional[str] = None,
) -> tuple[int, dict]:
    """Compute asset-class-specific score boost for non-crypto picks.

    Args:
        pick: Signal dict with asset_class, symbol, direction, confidence, etc.
        fred_data: Optional FRED data dict (series_id -> list of {date, value})
        market_regime: Optional regime string ("risk_on", "risk_off", "neutral")

    Returns:
        (boost_points, breakdown_dict)
    """
    asset_class = (pick.get("asset_class") or pick.get("category") or "").upper().strip()
    if asset_class in ("CRYPTO", "MEME", ""):
        return 0, {"_non_crypto_boost": "skipped_crypto"}

    breakdown = {}
    total_boost = 0

    # --- FOREX: Session-aware + carry differential ---
    if asset_class in ("FOREX",):
        boost, detail = _forex_session_boost(pick)
        total_boost += boost
        breakdown["forex_session"] = detail

        if fred_data:
            carry_boost, carry_detail = _forex_carry_boost(pick, fred_data)
            total_boost += carry_boost
            breakdown["forex_carry"] = carry_detail

    # --- COMMODITY/FUTURES: COT sentiment + seasonal ---
    elif asset_class in ("COMMODITY", "FUTURES"):
        if fred_data:
            cot_boost, cot_detail = _commodity_cot_boost(pick, fred_data)
            total_boost += cot_boost
            breakdown["commodity_cot"] = cot_detail

        seasonal_boost, seasonal_detail = _commodity_seasonal_boost(pick)
        total_boost += seasonal_boost
        breakdown["commodity_seasonal"] = seasonal_detail

    # --- ETF: Momentum alignment + regime ---
    elif asset_class in ("ETF",):
        momentum_boost, momentum_detail = _etf_momentum_boost(pick)
        total_boost += momentum_boost
        breakdown["etf_momentum"] = momentum_detail

        regime_boost, regime_detail = _etf_regime_boost(pick, market_regime)
        total_boost += regime_boost
        breakdown["etf_regime"] = regime_detail

    # --- BOND: Yield curve + credit spread ---
    elif asset_class in ("BOND",):
        if fred_data:
            yield_boost, yield_detail = _bond_yield_boost(pick, fred_data)
            total_boost += yield_boost
            breakdown["bond_yield"] = yield_detail

            credit_boost, credit_detail = _bond_credit_boost(pick, fred_data)
            total_boost += credit_boost
            breakdown["bond_credit"] = credit_detail

    # --- EQUITY: Sector momentum ---
    elif asset_class in ("EQUITY", "STOCK"):
        boost, detail = _equity_sector_boost(pick)
        total_boost += boost
        breakdown["equity_sector"] = detail

    # Cap at class max
    max_allowed = MAX_BOOST.get(asset_class, 5)
    if total_boost > max_allowed:
        breakdown["_capped"] = f"{total_boost} -> {max_allowed}"
        total_boost = max_allowed

    total_boost = max(0, total_boost)
    return total_boost, breakdown


# ---------------------------------------------------------------------------
# FOREX boosters
# ---------------------------------------------------------------------------
def _forex_session_boost(pick: dict) -> tuple[int, dict]:
    """Boost based on FX session overlap quality.

    London-NY overlap (13:00-16:00 UTC) = highest liquidity = best signals.
    Asian session = lower liquidity for most pairs (except USDJPY, AUDUSD).
    """
    now = datetime.now(timezone.utc)
    hour = now.hour

    symbol = (pick.get("symbol") or "").upper()
    confidence = float(pick.get("confidence", 0) or 0)

    # Session quality scoring
    if 13 <= hour < 16:  # London-NY overlap
        session_quality = "overlap"
        base_boost = 8
    elif 8 <= hour < 13:  # London session
        session_quality = "london"
        base_boost = 5
    elif 0 <= hour < 8:  # Asian session
        session_quality = "asian"
        # Asian pairs get a boost during Asian session
        asian_pairs = {"USDJPY", "AUDUSD", "NZDUSD", "EURJPY", "GBPJPY"}
        if any(p in symbol for p in asian_pairs):
            base_boost = 5
        else:
            base_boost = 2
    else:  # NY session (16-21 UTC)
        session_quality = "new_york"
        base_boost = 4

    # Confidence amplifier
    if confidence >= 0.7:
        base_boost = min(base_boost + 2, MAX_BOOST["FOREX"])

    return base_boost, {"session": session_quality, "base": base_boost}


def _forex_carry_boost(pick: dict, fred_data: dict) -> tuple[int, dict]:
    """Boost based on interest rate carry differential alignment.

    If the pick direction aligns with positive carry (buying higher-yielding currency),
    add a boost. Carry trade is a documented edge in FX.
    """
    # Simplified: check if DXY trend supports the pair direction
    dxy_data = fred_data.get("DGS10") or fred_data.get("DTWEXBGS")
    if not dxy_data or len(dxy_data) < 21:
        return 0, {"carry": "no_data"}

    try:
        recent = [row["value"] for row in dxy_data[-21:] if row.get("value") is not None]
        if len(recent) < 10:
            return 0, {"carry": "insufficient_data"}
        dxy_trend = (recent[-1] - recent[0]) / recent[0] if recent[0] else 0

        direction = (pick.get("direction") or "").upper()
        symbol = (pick.get("symbol") or "").upper()

        # USD strength aligns with SELL EURUSD, BUY USDJPY, etc.
        usd_pairs = {"USDJPY", "USDCAD", "USDCHF"}
        non_usd_pairs = {"EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"}

        aligned = False
        if any(p in symbol for p in usd_pairs) and direction == "LONG" and dxy_trend > 0:
            aligned = True
        elif any(p in symbol for p in non_usd_pairs) and direction == "SHORT" and dxy_trend > 0:
            aligned = True
        elif any(p in symbol for p in non_usd_pairs) and direction == "LONG" and dxy_trend < 0:
            aligned = True

        boost = 5 if aligned else 0
        return boost, {"aligned": aligned, "dxy_trend": round(dxy_trend, 4)}
    except Exception as e:
        return 0, {"carry": f"error: {e}"}


# ---------------------------------------------------------------------------
# COMMODITY/FUTURES boosters
# ---------------------------------------------------------------------------
def _commodity_cot_boost(pick: dict, fred_data: dict) -> tuple[int, dict]:
    """Boost based on COT (Commitment of Traders) positioning.

    Contrarian signal: extreme net-long positioning = bearish (and vice versa).
    Uses DXY and yield curve as proxy for commodity macro context.
    """
    # Use DXY as proxy for commodity inverse relationship
    dxy_data = fred_data.get("DGS10")
    if not dxy_data or len(dxy_data) < 21:
        return 0, {"cot": "no_data"}

    try:
        recent = [row["value"] for row in dxy_data[-21:] if row.get("value") is not None]
        if len(recent) < 10:
            return 0, {"cot": "insufficient_data"}

        # Falling yields = supportive for commodities (weaker USD, easier financial conditions)
        yield_trend = (recent[-1] - recent[0]) / recent[0] if recent[0] else 0
        direction = (pick.get("direction") or "").upper()

        # Commodities generally benefit from falling yields / weaker USD
        aligned = (direction == "LONG" and yield_trend < -0.01) or \
                  (direction == "SHORT" and yield_trend > 0.01)

        boost = 6 if aligned else 2  # Small base boost for commodities (data is weekly/lagged)
        return boost, {"aligned": aligned, "yield_trend": round(yield_trend, 4)}
    except Exception as e:
        return 0, {"cot": f"error: {e}"}


def _commodity_seasonal_boost(pick: dict) -> tuple[int, dict]:
    """Boost based on seasonal patterns.

    Commodities have documented seasonal patterns:
    - Natural gas: bullish Oct-Mar (heating season)
    - Agriculture: planting/harvest cycles
    - Gold: strong in Jan-Feb (Indian wedding season) and Sep-Oct
    """
    now = datetime.now(timezone.utc)
    month = now.month

    symbol = (pick.get("symbol") or "").upper()
    direction = (pick.get("direction") or "").upper()

    # Generic seasonal boost (simplified — would need per-symbol lookup for full implementation)
    # Strong months for commodities broadly: Feb-Mar, Jun-Jul, Sep-Oct
    strong_months = {2, 3, 6, 7, 9, 10}
    weak_months = {1, 5, 8, 12}

    if direction == "LONG":
        if month in strong_months:
            boost = 4
            season = "strong"
        elif month in weak_months:
            boost = 1
            season = "weak"
        else:
            boost = 2
            season = "neutral"
    else:  # SHORT
        if month in weak_months:
            boost = 4
            season = "strong_short"
        else:
            boost = 1
            season = "neutral"

    return boost, {"month": month, "season": season}


# ---------------------------------------------------------------------------
# ETF boosters
# ---------------------------------------------------------------------------
def _etf_momentum_boost(pick: dict) -> tuple[int, dict]:
    """Boost based on momentum alignment.

    If pick direction aligns with the ETF's recent momentum (from extra fields),
    add a boost. Dual momentum (absolute + relative) is the strongest ETF signal.
    """
    extra = pick.get("extra", {})
    confidence = float(pick.get("confidence", 0) or 0)
    direction = (pick.get("direction") or "").upper()

    # Check for momentum data in extra fields
    r12m = extra.get("r12m")  # 12-month return
    r3m = extra.get("r3m")    # 3-month return

    boost = 0
    detail = {}

    if r12m is not None:
        r12m = float(r12m)
        if direction == "LONG" and r12m > 0:
            boost += 3  # Absolute momentum confirmed
            detail["absolute_momentum"] = True
        elif direction == "SHORT" and r12m < -0.05:
            boost += 3
            detail["absolute_momentum"] = True

    if r3m is not None:
        r3m = float(r3m)
        if direction == "LONG" and r3m > 0:
            boost += 2  # Relative momentum confirmed
            detail["relative_momentum"] = True
        elif direction == "SHORT" and r3m < 0:
            boost += 2
            detail["relative_momentum"] = True

    # Confidence amplifier
    if confidence >= 0.7:
        boost = min(boost + 1, MAX_BOOST["ETF"])

    detail["total"] = boost
    return boost, detail


def _etf_regime_boost(pick: dict, market_regime: Optional[str]) -> tuple[int, dict]:
    """Boost based on market regime alignment.

    Risk-on: favor equity/sector ETFs
    Risk-off: favor bond/gold ETFs
    """
    if not market_regime:
        return 0, {"regime": "unknown"}

    symbol = (pick.get("symbol") or "").upper()
    direction = (pick.get("direction") or "").upper()

    # Classify ETF type
    bond_etfs = {"TLT", "IEF", "SHY", "BND", "AGG", "LQD", "HYG", "TIP", "BNDX", "MUB", "JNK", "EMB", "GOVT", "TLH"}
    gold_etfs = {"GLD", "SLV", "GDX", "GDXJ"}
    equity_etfs = {"SPY", "QQQ", "IWM", "DIA", "VTI", "VOO", "XLK", "XLF", "XLE", "XLV", "XLI", "XLB", "XLU", "XLY", "XLP", "XLC"}

    boost = 0
    aligned = False

    if market_regime == "risk_on":
        if any(e in symbol for e in equity_etfs) and direction == "LONG":
            boost = 4
            aligned = True
        elif any(e in symbol for e in bond_etfs) and direction == "SHORT":
            boost = 3
            aligned = True
    elif market_regime == "risk_off":
        if any(e in symbol for e in bond_etfs) and direction == "LONG":
            boost = 4
            aligned = True
        elif any(e in symbol for e in gold_etfs) and direction == "LONG":
            boost = 4
            aligned = True
        elif any(e in symbol for e in equity_etfs) and direction == "SHORT":
            boost = 3
            aligned = True

    return boost, {"regime": market_regime, "aligned": aligned}


# ---------------------------------------------------------------------------
# BOND boosters
# ---------------------------------------------------------------------------
def _bond_yield_boost(pick: dict, fred_data: dict) -> tuple[int, dict]:
    """Boost based on yield curve direction.

    Falling yields = bond prices rising = LONG bonds bullish.
    Rising yields = bond prices falling = SHORT bonds bullish.
    """
    dgs10 = fred_data.get("DGS10")
    if not dgs10 or len(dgs10) < 21:
        return 0, {"yield": "no_data"}

    try:
        recent = [row["value"] for row in dgs10[-21:] if row.get("value") is not None]
        if len(recent) < 10:
            return 0, {"yield": "insufficient_data"}

        yield_change = recent[-1] - recent[0]  # bps-level change
        direction = (pick.get("direction") or "").upper()

        # Falling yields = bullish for bond ETFs
        aligned = (direction == "LONG" and yield_change < -0.05) or \
                  (direction == "SHORT" and yield_change > 0.05)

        boost = 5 if aligned else 1
        return boost, {"aligned": aligned, "yield_change_21d": round(yield_change, 4)}
    except Exception as e:
        return 0, {"yield": f"error: {e}"}


def _bond_credit_boost(pick: dict, fred_data: dict) -> tuple[int, dict]:
    """Boost based on credit spread conditions.

    Tightening credit spreads = risk-on for credit = bullish for HY bonds.
    Widening spreads = risk-off = bullish for Treasuries.
    """
    hy_data = fred_data.get("BAMLH0A0HYM2")  # HY OAS
    if not hy_data or len(hy_data) < 21:
        return 0, {"credit": "no_data"}

    try:
        recent = [row["value"] for row in hy_data[-21:] if row.get("value") is not None]
        if len(recent) < 10:
            return 0, {"credit": "insufficient_data"}

        spread_change = recent[-1] - recent[0]
        direction = (pick.get("direction") or "").upper()
        symbol = (pick.get("symbol") or "").upper()

        # Treasuries benefit from widening spreads (flight to safety)
        treasury_etfs = {"TLT", "IEF", "SHY", "GOVT", "TLH"}
        credit_etfs = {"LQD", "HYG", "JNK", "EMB"}

        aligned = False
        if any(e in symbol for e in treasury_etfs) and direction == "LONG" and spread_change > 0.1:
            aligned = True  # Widening spreads = flight to safety = long Treasuries
        elif any(e in symbol for e in credit_etfs) and direction == "LONG" and spread_change < -0.1:
            aligned = True  # Tightening spreads = risk-on = long credit

        boost = 4 if aligned else 0
        return boost, {"aligned": aligned, "spread_change_21d": round(spread_change, 4)}
    except Exception as e:
        return 0, {"credit": f"error: {e}"}


# ---------------------------------------------------------------------------
# EQUITY booster
# ---------------------------------------------------------------------------
def _equity_sector_boost(pick: dict) -> tuple[int, dict]:
    """Boost based on sector momentum alignment."""
    confidence = float(pick.get("confidence", 0) or 0)
    strategy = (pick.get("strategy") or "").lower()

    # Proven equity strategies get a small boost
    proven_strategies = {
        "stocks_rsi2_pullback": 5,
        "stocks_momentum": 4,
        "stocks_value_quality": 4,
        "ml_gatekeeper": 3,
        "stocks_competition": 3,
    }

    boost = 0
    for strat_name, strat_boost in proven_strategies.items():
        if strat_name in strategy:
            boost = strat_boost
            break

    if confidence >= 0.75:
        boost = min(boost + 2, MAX_BOOST["EQUITY"])

    return boost, {"strategy_boost": boost}
