"""M-017: Standalone volatility-target + per-name cap position sizer (2026-05-15).

Dependency-free (no numpy/pandas/indicators). Safe to import in any context.
Observational only — wire to score_pick reporting first, not live execution.

Usage::

    from alpha_engine.vol_target_sizer import compute_position_size
    result = compute_position_size(pick, portfolio_equity=10_000)
    # result: {position_size_pct, position_size_usd, sizing_method, cap_applied, ...}

Wiring Plan (per CLAUDE.md Wire-Up Rule):
    Target: alpha_engine/smart_picks_engine.py::score_pick — shadow reporting.
    Expected wire-up: shadow first (log only), then production after 30-day live
    validation shows sizing_allowed=true and no MDD breach.
"""
from __future__ import annotations

_VOL_TARGET_BY_CLASS: dict[str, float] = {
    "CRYPTO": 0.005,    # 0.5% of equity per pick (high vol class)
    "EQUITY": 0.008,    # 0.8% (liquid large-cap, lower vol)
    "ETF": 0.010,       # 1.0% (diversified, lower vol)
    "COMMODITY": 0.005, # 0.5% (futures-like vol)
    "FUTURES": 0.005,   # 0.5% (high vol, thin market)
    "FOREX": 0.003,     # 0.3% (FOREX disabled, low allocation when on)
    "BOND": 0.015,      # 1.5% (low vol, can size up more)
}

_MAX_PER_NAME_PCT: float = 0.02    # 2% of equity max per single name
_MAX_PER_CLASS_PCT: float = 0.15   # 15% of equity max per asset class


def compute_position_size(
    pick: dict,
    portfolio_equity: float = 10_000.0,
    pick_volatility_pct: float | None = None,
) -> dict:
    """Volatility-target position size with per-name cap.

    Args:
        pick: pick dict (needs asset_class, symbol)
        portfolio_equity: total portfolio equity in USD (default $10k for shadow)
        pick_volatility_pct: annualized vol (0-1), e.g. 0.40 = 40%.
                             If None, uses asset-class default.

    Returns:
        dict: position_size_pct, position_size_usd, sizing_method, cap_applied, ...
    """
    try:
        ac = str(pick.get("asset_class", "") or "CRYPTO").upper()
        vol_target = _VOL_TARGET_BY_CLASS.get(ac, 0.005)

        if pick_volatility_pct and pick_volatility_pct > 0:
            pv = max(0.05, min(2.0, float(pick_volatility_pct)))
            raw_pct = vol_target / pv
            sizing_method = "vol_target"
        else:
            raw_pct = vol_target
            sizing_method = "class_default"

        cap_applied = False
        if raw_pct > _MAX_PER_NAME_PCT:
            raw_pct = _MAX_PER_NAME_PCT
            cap_applied = True

        return {
            "position_size_pct": round(raw_pct * 100, 3),
            "position_size_usd": round(portfolio_equity * raw_pct, 2),
            "sizing_method": sizing_method,
            "cap_applied": cap_applied,
            "vol_target_pct": round(vol_target * 100, 3),
            "portfolio_equity": portfolio_equity,
        }
    except Exception:
        return {
            "position_size_pct": 0.5,
            "position_size_usd": round(portfolio_equity * 0.005, 2),
            "sizing_method": "fallback",
            "cap_applied": False,
            "vol_target_pct": 0.5,
            "portfolio_equity": portfolio_equity,
        }
