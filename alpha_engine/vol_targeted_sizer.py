"""
Volatility-Targeted Position Sizer (U-1)
=========================================

Universal wrapper that scales any upstream signal's recommended position size
by the ratio of a target annualized volatility to the symbol's realized vol.

    size_multiplier = clip(target_vol / realized_vol, 0, cap)

Thesis
------
Moskowitz-Ooi-Pedersen (2012) and AQR/Man AHL both report a +0.3 to +0.5 Sharpe
lift when vol-targeting is layered on top of directional strategies. It does
not create alpha — it reshapes the return distribution by trimming exposure
in high-vol regimes and increasing it in low-vol regimes.

Why this module exists (lessons baked in from adversarial review)
-----------------------------------------------------------------
1. **Do NOT stack this with full Kelly sizing.** Kelly is `f* = μ/σ²` and
   vol-targeting is `k = σ_target/σ`. Naively multiplying the two divides
   by σ³ — that triple-penalises volatility, crushes size in stress regimes,
   and blows past the cap in low-vol regimes. If Kelly is used at all it
   must be applied as a **ceiling on top of the vol-targeted base size**,
   not a multiplier. A `kelly_ceiling` parameter is supported below; it's
   off by default until we have ≥500 closed trades per strategy to estimate
   edge stably (current ledger is too short).
2. **Hard 1.5× cap.** Vol-targeting is procyclical on the way in — low
   realized vol right before a regime break causes oversizing. The cap
   bounds that worst case to +50% vs flat sizing.
3. **Fallback to flat sizing** when realized-vol data is missing rather than
   crashing. The adversarial review correctly noted per-symbol realized vol
   is not currently computed in the scraper pipeline; the helper accepts an
   explicit `realized_vol` arg and only falls back to flat if absent.

Author: Claude Opus 4.7 — 2026-04-18 — Phase 2 U-1.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np
import pandas as pd


DEFAULT_TARGET_ANNUAL_VOL = 0.15   # 15 % annualised
DEFAULT_CAP = 1.5                  # clip multiplier at 1.5× base size
DEFAULT_FLOOR = 0.25               # never go below 0.25× — avoids zero-sizing whipsaws
ANNUALISATION_BARS = {
    "1m": 60 * 24 * 365,
    "5m": 12 * 24 * 365,
    "15m": 4 * 24 * 365,
    "1h": 24 * 365,
    "4h": 6 * 365,
    "1d": 252,
}


@dataclass
class SizingDecision:
    """Result of a sizing call. `multiplier=1.0` is unchanged from input."""
    multiplier: float
    base_size: float
    sized: float
    realized_vol_ann: Optional[float]
    reason: str
    applied: bool        # False if flat-fallback (no vol data / env disabled)


def realized_vol_from_returns(
    returns: Sequence[float],
    bars_per_year: float = ANNUALISATION_BARS["1h"],
) -> float:
    """Annualised realised σ from log-returns."""
    arr = np.asarray([r for r in returns if r is not None and np.isfinite(r)])
    if arr.size < 5:
        return float("nan")
    return float(np.std(arr, ddof=1) * math.sqrt(bars_per_year))


def realized_vol_from_closes(
    closes: Sequence[float],
    bars_per_year: float = ANNUALISATION_BARS["1h"],
    lookback: int = 20,
) -> float:
    """Annualised realised σ from a close-price series."""
    s = pd.Series(closes, dtype=float).dropna()
    if len(s) < lookback + 2:
        return float("nan")
    rets = np.log(s).diff().dropna().tail(lookback)
    return float(rets.std(ddof=1) * math.sqrt(bars_per_year))


def size_position(
    base_size: float,
    *,
    realized_vol_ann: Optional[float] = None,
    target_vol_ann: float = DEFAULT_TARGET_ANNUAL_VOL,
    cap: float = DEFAULT_CAP,
    floor: float = DEFAULT_FLOOR,
    kelly_ceiling: Optional[float] = None,
) -> SizingDecision:
    """Scale `base_size` by `target_vol / realized_vol`, clipped to [floor, cap].

    Parameters
    ----------
    base_size
        The strategy's pre-sizing position fraction (e.g. 0.02 = 2 % of book).
    realized_vol_ann
        Annualised realised volatility of the symbol. If None or not finite,
        we return flat `base_size` with `applied=False`.
    target_vol_ann
        Desired annualised portfolio-contribution vol per position.
    cap, floor
        Bounds on the size multiplier. Cap prevents pro-cyclical oversizing
        in low-vol regimes. Floor prevents zero-sizing when σ spikes.
    kelly_ceiling
        Optional absolute upper bound on `sized` output computed elsewhere as
        fractional Kelly (e.g. 0.25 × full-Kelly). Applied AFTER vol-targeting
        so Kelly acts as a ceiling, not a multiplier. Leave None until
        per-strategy edge is estimated on ≥500 closed trades.

    Env
    ---
    `VOL_TARGET_ENABLED=0` disables the wrapper (returns flat). Defaults on.
    `VOL_TARGET_SHADOW=1` computes the multiplier but returns flat, for
    logging / A-B comparison runs.
    """
    env_enabled = os.environ.get("VOL_TARGET_ENABLED", "1") != "0"
    shadow = os.environ.get("VOL_TARGET_SHADOW", "0") == "1"

    if not env_enabled:
        return SizingDecision(
            multiplier=1.0, base_size=base_size, sized=base_size,
            realized_vol_ann=realized_vol_ann,
            reason="VOL_TARGET_ENABLED=0 (wrapper disabled)", applied=False,
        )

    if realized_vol_ann is None or not np.isfinite(realized_vol_ann) or realized_vol_ann <= 0:
        return SizingDecision(
            multiplier=1.0, base_size=base_size, sized=base_size,
            realized_vol_ann=realized_vol_ann,
            reason="flat-fallback (no finite realized_vol_ann)", applied=False,
        )

    raw_mult = target_vol_ann / realized_vol_ann
    clipped = max(floor, min(cap, raw_mult))
    sized = base_size * clipped

    if kelly_ceiling is not None and np.isfinite(kelly_ceiling) and kelly_ceiling > 0:
        sized = min(sized, kelly_ceiling)

    if shadow:
        return SizingDecision(
            multiplier=clipped, base_size=base_size, sized=base_size,
            realized_vol_ann=realized_vol_ann,
            reason=f"SHADOW: would scale {base_size:.4f} × {clipped:.3f} = {sized:.4f}",
            applied=False,
        )

    reason = (
        f"σ̂={realized_vol_ann:.3f} target={target_vol_ann:.3f} "
        f"raw={raw_mult:.3f} → clip[{floor:.2f},{cap:.2f}]={clipped:.3f}"
    )
    if kelly_ceiling is not None:
        reason += f" kelly_ceil={kelly_ceiling:.4f}"
    return SizingDecision(
        multiplier=clipped, base_size=base_size, sized=float(sized),
        realized_vol_ann=realized_vol_ann, reason=reason, applied=True,
    )


def size_from_closes(
    base_size: float,
    closes: Sequence[float],
    *,
    bar_period: str = "1h",
    lookback: int = 20,
    target_vol_ann: float = DEFAULT_TARGET_ANNUAL_VOL,
    cap: float = DEFAULT_CAP,
    floor: float = DEFAULT_FLOOR,
    kelly_ceiling: Optional[float] = None,
) -> SizingDecision:
    """Convenience wrapper — derives realised vol from a close series first."""
    bars_per_year = ANNUALISATION_BARS.get(bar_period, ANNUALISATION_BARS["1h"])
    rv = realized_vol_from_closes(closes, bars_per_year=bars_per_year, lookback=lookback)
    return size_position(
        base_size,
        realized_vol_ann=rv,
        target_vol_ann=target_vol_ann,
        cap=cap,
        floor=floor,
        kelly_ceiling=kelly_ceiling,
    )


__all__ = [
    "SizingDecision",
    "size_position",
    "size_from_closes",
    "realized_vol_from_returns",
    "realized_vol_from_closes",
    "DEFAULT_TARGET_ANNUAL_VOL",
    "DEFAULT_CAP",
    "DEFAULT_FLOOR",
    "ANNUALISATION_BARS",
]
