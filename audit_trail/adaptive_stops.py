"""
Asset-class-aware TP/SL calibration for audit dashboard + ATR-based absolute levels.

- `get_vol_tier_percentages`: crypto tier + non-crypto % floors (dashboard_generator).
- `classify_regime` / `ASSET_CLASS_CONFIG` / `calculate_adaptive_stop_dict`: aligned with
  Downloads/adaptive_stops.py (ATR multipliers, regime + VIX + earnings week, net R:R).
"""

from __future__ import annotations

import math
from typing import Any, Optional

# tier -> (tp_pct, sl_pct, atr_tp_mult, atr_sl_mult); R:R enforced in dashboard_generator
_CRYPTO_VOL_TIER_DEFAULTS: dict[str, tuple[float, float, float, float]] = {
    "LOW": (0.020, 0.0315, 1.0, 1.5),
    "MID": (0.028, 0.0315, 1.4, 1.5),
    "HIGH": (0.035, 0.0315, 1.6, 1.5),
    "DEFAULT": (0.025, 0.0315, 1.5, 1.5),
}

_NON_CRYPTO_DEFAULTS: dict[str, tuple[float, float, float, float]] = {
    "EQUITY": (0.028, 0.052, 2.2, 2.4),
    "STOCK": (0.028, 0.052, 2.2, 2.4),
    "FOREX": (0.018, 0.032, 1.4, 1.6),
    "FX": (0.018, 0.032, 1.4, 1.6),
    "ETF": (0.022, 0.045, 1.9, 2.1),
    "COMMODITY": (0.024, 0.048, 2.0, 2.2),
    "COMMODITIES": (0.024, 0.048, 2.0, 2.2),
    "BOND": (0.012, 0.022, 1.0, 1.2),
    "DEFAULT": (0.025, 0.048, 2.0, 2.2),
}

# Reference Downloads/adaptive_stops.py — ATR multipliers + costs
ASSET_CLASS_CONFIG: dict[str, dict[str, float]] = {
    "CRYPTO": {
        "atr_multiplier_sl": 2.0,
        "atr_multiplier_tp": 3.0,
        "commission_rt": 0.0030,
        "slippage": 0.0005,
    },
    "EQUITY": {
        "atr_multiplier_sl": 1.5,
        "atr_multiplier_tp": 2.5,
        "commission_rt": 0.0070,
        "slippage": 0.0010,
    },
    "FOREX": {
        "atr_multiplier_sl": 1.2,
        "atr_multiplier_tp": 2.0,
        "commission_rt": 0.0002,
        "slippage": 0.0001,
    },
    "ETF": {
        "atr_multiplier_sl": 1.3,
        "atr_multiplier_tp": 2.0,
        "commission_rt": 0.0005,
        "slippage": 0.0003,
    },
    "FUTURES": {
        "atr_multiplier_sl": 1.4,
        "atr_multiplier_tp": 2.2,
        "commission_rt": 0.0020,
        "slippage": 0.0005,
    },
    "COMMODITY": {
        "atr_multiplier_sl": 1.3,
        "atr_multiplier_tp": 2.0,
        "commission_rt": 0.0015,
        "slippage": 0.0004,
    },
}

REGIME_ADJUSTMENTS: dict[str, dict[str, float]] = {
    "CLEAR_BULL": {"sl_mult": 0.90, "tp_mult": 1.10},
    "PARTLY_CLOUDY": {"sl_mult": 1.00, "tp_mult": 1.00},
    "OVERCAST": {"sl_mult": 1.20, "tp_mult": 0.85},
    "STORM": {"sl_mult": 1.50, "tp_mult": 0.75},
    "HURRICANE": {"sl_mult": 2.00, "tp_mult": 0.60},
    "UNKNOWN": {"sl_mult": 1.10, "tp_mult": 0.95},
}


def _norm_ac(asset_class: str) -> str:
    return str(asset_class or "").strip().upper() or "DEFAULT"


def classify_regime(
    vix: Optional[float] = None,
    spx_vs_200dma: Optional[float] = None,
    breadth_pct: Optional[float] = None,
) -> str:
    _ = breadth_pct  # reserved for future breadth rules
    if vix is None:
        return "UNKNOWN"
    if vix > 35:
        return "HURRICANE"
    if vix > 25 and spx_vs_200dma is not None and spx_vs_200dma < 0:
        return "STORM"
    if vix > 20:
        return "OVERCAST"
    if vix > 15:
        return "PARTLY_CLOUDY"
    return "CLEAR_BULL"


def get_vol_tier_percentages(
    symbol: str,
    asset_class: str,
    *,
    crypto_tier: str,
) -> tuple[float, float, float, float]:
    ac = _norm_ac(asset_class)
    if ac == "CRYPTO":
        tier = str(crypto_tier or "DEFAULT").upper()
        return _CRYPTO_VOL_TIER_DEFAULTS.get(tier, _CRYPTO_VOL_TIER_DEFAULTS["DEFAULT"])
    return _NON_CRYPTO_DEFAULTS.get(ac, _NON_CRYPTO_DEFAULTS["DEFAULT"])


def calculate_adaptive_stop_dict(
    entry: float,
    atr: float,
    asset_class: str,
    direction: str = "LONG",
    regime: str = "UNKNOWN",
    vix: Optional[float] = None,
    is_earnings_week: bool = False,
) -> dict[str, Any]:
    """
    ATR-based SL/TP with regime/VIX/earnings adjustments and net R:R vs commission.
    Matches semantics of Downloads/adaptive_stops.py.
    """
    ac = _norm_ac(asset_class)
    if ac not in ASSET_CLASS_CONFIG:
        ac = "CRYPTO"
    config = dict(ASSET_CLASS_CONFIG[ac])
    regime_adj = REGIME_ADJUSTMENTS.get(regime, REGIME_ADJUSTMENTS["UNKNOWN"])

    sl_mult = config["atr_multiplier_sl"] * regime_adj["sl_mult"]
    tp_mult = config["atr_multiplier_tp"] * regime_adj["tp_mult"]

    if ac in ("EQUITY", "ETF") and vix is not None and math.isfinite(vix):
        if vix > 30:
            sl_mult *= 1.3
        elif vix < 12:
            sl_mult *= 0.85

    if is_earnings_week:
        sl_mult *= 1.5
        tp_mult *= 0.8

    direction_u = str(direction or "LONG").upper()
    if direction_u in ("LONG", "BUY"):
        sl = entry - (atr * sl_mult)
        tp = entry + (atr * tp_mult)
    else:
        sl = entry + (atr * sl_mult)
        tp = entry - (atr * tp_mult)

    risk = abs(entry - sl)
    reward = abs(tp - entry)
    rr = reward / risk if risk > 0 else 0.0

    commission = config["commission_rt"]
    net_risk = risk + (entry * commission)
    net_reward = reward - (entry * commission)
    net_rr = net_reward / net_risk if net_risk > 0 else 0.0

    if net_rr < 1.2:
        return {
            "sl": None,
            "tp": None,
            "rr": round(rr, 4),
            "net_rr": round(net_rr, 4),
            "rejected": True,
            "reason": "net_rr_too_low: %.2f (need >= 1.2)" % net_rr,
            "sl_multiplier_used": round(sl_mult, 4),
            "tp_multiplier_used": round(tp_mult, 4),
            "regime": regime,
            "asset_class": ac,
        }

    return {
        "sl": round(sl, 8),
        "tp": round(tp, 8),
        "rr": round(rr, 4),
        "net_rr": round(net_rr, 4),
        "rejected": False,
        "reason": "passed",
        "sl_multiplier_used": round(sl_mult, 4),
        "tp_multiplier_used": round(tp_mult, 4),
        "regime": regime,
        "asset_class": ac,
    }


def batch_calculate_stops(picks: list[dict], market_state: Optional[dict] = None) -> list[dict]:
    """Enrich picks with adaptive_stop dict; optional market_state: vix, spx_vs_200dma, breadth_pct."""
    market_state = market_state or {}
    regime = classify_regime(
        vix=market_state.get("vix"),
        spx_vs_200dma=market_state.get("spx_vs_200dma"),
        breadth_pct=market_state.get("breadth_pct"),
    )
    out: list[dict] = []
    for pick in picks:
        entry = float(pick.get("entry", 0) or pick.get("entry_price", 0) or 0)
        atr = float(pick.get("atr", 0) or 0)
        if atr <= 0 and entry > 0:
            atr = entry * 0.02
        ac = pick.get("asset_class", "CRYPTO")
        result = calculate_adaptive_stop_dict(
            entry=entry,
            atr=atr,
            asset_class=str(ac),
            direction=str(pick.get("direction", "LONG")),
            regime=regime,
            vix=market_state.get("vix"),
            is_earnings_week=bool(pick.get("is_earnings_week", False)),
        )
        enriched = {**pick, "adaptive_stop": result}
        if not result.get("rejected"):
            enriched["sl"] = result["sl"]
            enriched["tp"] = result["tp"]
            enriched["rr"] = result["rr"]
        out.append(enriched)
    return out


def calculate_adaptive_stop(
    entry: float,
    atr: float,
    asset_class: str,
    regime: str,
    vix: float | None = None,
    direction: str = "LONG",
) -> tuple[float | None, float | None, float]:
    """
    Legacy tuple API for tests: (tp, sl, rr) for LONG-style geometry.
    SHORT returns (tp, sl, rr) with tp below entry.
    """
    d = calculate_adaptive_stop_dict(
        entry, atr, asset_class, direction=direction, regime=regime, vix=vix
    )
    if d.get("rejected"):
        return (None, None, float(d.get("rr") or 0))
    direction_u = str(direction or "LONG").upper()
    if direction_u in ("LONG", "BUY"):
        return (float(d["tp"]), float(d["sl"]), float(d["rr"]))
    return (float(d["tp"]), float(d["sl"]), float(d["rr"]))
