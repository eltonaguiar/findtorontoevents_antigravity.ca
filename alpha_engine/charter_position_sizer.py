"""Charter §7 position sizing — vol-targeted with hard concentration caps.

Distinct from the regime-adaptive sizer at `alpha_engine/position_sizer.py`
which adjusts size by market regime (BULL/BEAR/NEUTRAL multipliers). This
module enforces the per-pick and per-portfolio caps from
`docs/PERFORMANCE_CHARTER.md` §7 and computes a vol-targeted dollar size.
Call this AFTER the regime sizer in production.

Pure functions: no I/O at import, no globals mutated. Inputs are validated
by the calling layer; we trust the schema.

Spec: reports/implementation_plan_v2_2026-05-13.md P0.5-1.
Procedure: external-model review by drafters A + B; this draft adopts A's
two-clip-layer design (per-class risk ceiling + per-category notional
ceiling) and B's naming-collision avoidance.
"""

from __future__ import annotations

from typing import Literal, TypedDict

Category = Literal["long_term", "swing"]
AssetClass = Literal["CRYPTO", "EQUITY", "ETF", "COMMODITY", "FOREX", "BOND"]


class Pick(TypedDict, total=False):
    symbol: str
    asset_class: AssetClass
    confidence: float
    category: Category
    sector: str
    notional_pct: float


_DEFAULT_DAILY_VOL: dict[AssetClass, float] = {
    "CRYPTO":    0.04,
    "EQUITY":    0.015,
    "ETF":       0.012,
    "COMMODITY": 0.018,
    "FOREX":     0.008,
    "BOND":      0.005,
}

_MAX_RISK_PCT: dict[AssetClass, float] = {
    "CRYPTO":    0.020,
    "EQUITY":    0.015,
    "ETF":       0.012,
    "COMMODITY": 0.015,
    "FOREX":     0.010,
    "BOND":      0.008,
}

_MAX_NOTIONAL_PCT: dict[Category, float] = {
    "long_term": 0.05,
    "swing":     0.01,
}

_MAX_SECTOR_PCT: dict[Category, float] = {
    "long_term": 0.30,
    "swing":     0.20,
}

_TARGET_RISK_PCT = 0.0075
_DAILY_LOSS_KILL_PCT = -0.03


def _category(pick: Pick) -> Category:
    return pick.get("category", "swing")  # type: ignore[return-value]


def _confidence_multiplier(confidence: float) -> float:
    raw = 0.5 + 0.5 * confidence
    return min(1.0, max(0.5, raw))


def compute_position_size(
    pick: dict,
    portfolio_equity: float,
    daily_vol_estimate: float | None,
) -> float:
    if portfolio_equity <= 0:
        return 0.0

    asset_class: AssetClass = pick["asset_class"]
    category = _category(pick)  # type: ignore[arg-type]

    vol = daily_vol_estimate if daily_vol_estimate and daily_vol_estimate > 0 \
        else _DEFAULT_DAILY_VOL[asset_class]

    risk_pct = min(_TARGET_RISK_PCT / vol, _MAX_RISK_PCT[asset_class])
    risk_pct *= _confidence_multiplier(pick["confidence"])

    notional_pct = min(risk_pct, _MAX_NOTIONAL_PCT[category])
    return round(notional_pct * portfolio_equity, 2)


def validate_concentration(
    pick: dict,
    current_positions: list[dict],
) -> tuple[bool, str]:
    symbol = pick["symbol"]
    sector = pick.get("sector")
    category = _category(pick)  # type: ignore[arg-type]

    if any(p["symbol"] == symbol for p in current_positions):
        return False, f"duplicate_symbol:{symbol}"

    if sector is None:
        return True, "ok"

    sector_exposure = sum(
        p.get("notional_pct", 0.0)
        for p in current_positions
        if p.get("sector") == sector and p.get("category", "swing") == category
    )
    incoming_pct = pick.get("notional_pct", _MAX_NOTIONAL_PCT[category])
    if sector_exposure + incoming_pct > _MAX_SECTOR_PCT[category]:
        return False, (
            f"sector_cap:{sector}:{category}:"
            f"{sector_exposure + incoming_pct:.3f}>{_MAX_SECTOR_PCT[category]}"
        )

    return True, "ok"


def daily_loss_kill_switch(
    starting_equity: float,
    current_equity: float,
) -> tuple[bool, str]:
    if starting_equity <= 0:
        return False, "invalid_equity"
    drawdown = (current_equity - starting_equity) / starting_equity
    if drawdown <= _DAILY_LOSS_KILL_PCT:
        return True, f"daily_loss_kill:{drawdown:.4f}<={_DAILY_LOSS_KILL_PCT}"
    return False, f"ok:{drawdown:.4f}"
