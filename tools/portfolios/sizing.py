"""Position-sizing primitives for the AI-model paper portfolios (Phase 2).

PURE / DETERMINISTIC: no DB, no network, no file IO. Inputs are plain
numbers; outputs are plain numbers. The daily runner (Phase 3) supplies
the prices / NAV / appetite knobs and persists results.

See docs/DESIGN_AI_MODEL_HEDGE_FUND_PORTFOLIOS_2026-05-29.md §5 (③ SIZING):

    target_weight = clamp(kelly_fraction * edge_signal * vol_scalar, 0, max_pos)
    vol_scalar    = appetite_vol_target / trailing_realized_vol(symbol)
"""
from __future__ import annotations

import math

TRADING_DAYS = 252

# vol_scalar clamp bounds (§5): never scale a position below 0.1x or above 3.0x.
_VOL_SCALAR_MIN = 0.1
_VOL_SCALAR_MAX = 3.0


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def realized_vol(prices: list[float], window: int = 20) -> float | None:
    """Annualized stdev of daily log returns over the trailing ``window``.

    Uses the most recent ``window`` returns (i.e. ``window + 1`` prices).
    Returns ``None`` when there is insufficient data or prices are
    non-positive (log return undefined). Sample stdev (ddof=1) is used.
    """
    if not prices or window < 1:
        return None
    # Need window+1 prices to form `window` consecutive returns.
    if len(prices) < window + 1:
        return None

    series = prices[-(window + 1):]
    log_returns: list[float] = []
    for prev, cur in zip(series[:-1], series[1:]):
        if prev is None or cur is None or prev <= 0 or cur <= 0:
            return None
        log_returns.append(math.log(cur / prev))

    n = len(log_returns)
    if n < 2:
        return None

    mean = sum(log_returns) / n
    variance = sum((r - mean) ** 2 for r in log_returns) / (n - 1)  # sample
    daily_std = math.sqrt(variance)
    return daily_std * math.sqrt(TRADING_DAYS)


def vol_scalar(appetite_vol_target: float, symbol_realized_vol: float | None) -> float:
    """Ratio of target vol to a symbol's realized vol, clamped to [0.1, 3.0].

    If realized vol is unknown (None) or zero, return a neutral 1.0 — we
    do not amplify or shrink sizing without a usable volatility estimate.
    """
    if symbol_realized_vol is None or symbol_realized_vol == 0:
        return 1.0
    raw = appetite_vol_target / symbol_realized_vol
    return _clamp(raw, _VOL_SCALAR_MIN, _VOL_SCALAR_MAX)


def target_weight(
    edge_signal: float,
    kelly_fraction: float,
    vol_scalar: float,
    max_single_position_pct: float,
) -> float:
    """Fraction of NAV to allocate (0..max_single_position_pct/100).

    ``edge_signal`` is expected in [0, 1]; it is clamped defensively.
    The product kelly*edge*vol_scalar is clamped to [0, max_pos_fraction].
    """
    edge = _clamp(edge_signal, 0.0, 1.0)
    raw = kelly_fraction * edge * vol_scalar
    max_fraction = max(0.0, max_single_position_pct) / 100.0
    return _clamp(raw, 0.0, max_fraction)


def position_qty(target_weight: float, nav_usd: float, price: float) -> float:
    """Quantity of units to buy/sell for a given target weight.

    notional = target_weight * NAV ; qty = notional / price.
    Returns 0.0 for non-positive price (undefined) or non-positive notional.
    """
    if price is None or price <= 0:
        return 0.0
    notional = target_weight * nav_usd
    if notional <= 0:
        return 0.0
    return notional / price
