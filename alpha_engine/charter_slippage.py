"""Charter §7 execution-cost (slippage) model — per-class round-trip bps.

Pure functions. No I/O at import. Companion to alpha_engine/charter_position_sizer.py.
Consumed by outcome_resolver.py to stamp `_pnl_pct_gross` and `_pnl_pct_net`
on every closed pick so /audit can show both.

Spec: reports/implementation_plan_v2_2026-05-13.md P0.5-2.

Rationale per session findings:
- multi_asset_cot verifier (2026-05-13) showed top winning trade is 7.18bp
  gross; at COMMODITY 12bp round-trip every win mechanically becomes a 4-5bp
  loss. The "REAL gross" verdict survives but the "real money" verdict
  doesn't. See reports/multi_asset_cot_slippage_analysis_2026-05-13.md.
- External model second-opinion (OpenRouter free models, 2026-05-13):
  3 of 3 (GPT-OSS-120B / GLM-4.5-air / Nemotron-3-super-120B) named the
  slippage model as the highest-leverage gap not yet shipped.

Numbers per class are based on typical spreads + market-impact for retail
notional. They are conservative (lean wider) on the assumption that thin
real-money sizing pays the full spread, not the mid-market quote.
"""
from __future__ import annotations

from typing import Final, Literal

AssetClass = Literal[
    "CRYPTO", "EQUITY", "ETF", "COMMODITY", "FOREX", "BOND", "FUTURES",
]

# Round-trip basis points per class. Includes spread + market impact + fees
# averaged across typical retail-sized fills. Multiplied by 2 for round-trip
# (entry + exit) when deducted from gross pnl_pct.
#
# CRYPTO 4: typical 2-3bp spread on majors + 1bp taker fee one-way
# EQUITY 3: tight spreads on liquid US large-cap; 0.5bp impact at retail size
# ETF 2: tightest spreads in the universe (SPY/QQQ); minimal impact
# COMMODITY 6: futures tick + half-tick avg slippage; HG=F ~5bp, less liquid 8bp
# FOREX 1: institutional-floor majors; retail mark-up varies (treat as institutional)
# BOND 3: TLT/IEF tighter than equity; HY ETFs wider; weighted average
# FUTURES 4: ES/NQ tight; smaller contracts wider. Avg.
ONE_WAY_BPS_BY_CLASS: Final[dict[str, int]] = {
    "CRYPTO":    4,
    "EQUITY":    3,
    "ETF":       2,
    "COMMODITY": 6,
    "FOREX":     1,
    "BOND":      3,
    "FUTURES":   4,
}

# Default for unknown class. Conservative — wider than every class above.
_DEFAULT_ONE_WAY_BPS: Final[int] = 8


def one_way_bps(asset_class: str | None) -> int:
    """Return the per-class one-way execution-cost in basis points."""
    if not asset_class:
        return _DEFAULT_ONE_WAY_BPS
    return ONE_WAY_BPS_BY_CLASS.get(asset_class.upper(), _DEFAULT_ONE_WAY_BPS)


def round_trip_bps(asset_class: str | None) -> int:
    """Return entry + exit execution cost in basis points."""
    return 2 * one_way_bps(asset_class)


def deduct_slippage(pnl_pct_gross: float, asset_class: str | None) -> float:
    """Convert gross pnl_pct (raw price-move return) into net pnl_pct
    (after round-trip execution costs).

    pnl_pct convention in this repo: a FRACTION, not a percentage and not
    basis points. A pnl_pct of 0.0327 means a +3.27% return. (Verified
    empirically against closed_picks.json — 99%+ of rows fall in [-1, 1],
    e.g. -0.0328 == -3.28%, 0.93 == +93%.)

    Round-trip cost is `round_trip_bps` basis points; one bp == 0.0001 as a
    fraction, so we deduct `round_trip_bps / 10000`.

    UNITS BUG FIX (M-069, 2026-05-17): the prior implementation deducted
    `2*one_way_bps/100`, i.e. it treated pnl_pct as percentage-points. Every
    real caller (`stamp_pick_net_pnl`, dashboard_generator verdict aggregate)
    feeds the fractional ledger value, so the deduction was 100x too large —
    8bp of CRYPTO slippage was subtracted as 8 percentage points, flipping
    real wins into losses. See reports/MASTER_ACTION_PLAN_2026-05-15.md M-069.
    """
    rt_frac = round_trip_bps(asset_class) / 10000.0
    return pnl_pct_gross - rt_frac


def stamp_pick_net_pnl(pick: dict) -> dict:
    """Mutate `pick` in place to add `_pnl_pct_gross` and `_pnl_pct_net`.

    Idempotent: if `_pnl_pct_gross` already present (already stamped),
    re-compute from it. Otherwise read `pnl_pct` as the gross value.

    Returns the mutated pick for chaining.
    """
    if "_pnl_pct_gross" not in pick:
        gross = pick.get("pnl_pct")
        if gross is None:
            return pick
        try:
            pick["_pnl_pct_gross"] = float(gross)
        except (TypeError, ValueError):
            return pick
    pick["_pnl_pct_net"] = deduct_slippage(
        pick["_pnl_pct_gross"],
        pick.get("asset_class"),
    )
    return pick
