"""
Risk-Parity Position Sizer — inverse-volatility weighting, Kelly criterion,
correlation-adjusted allocation, and drawdown guard.

Replaces fixed "1% of equity" sizing with volatility-scaled positions so that
risky assets get smaller bets and the portfolio-level risk stays bounded.

Usage:
    from shared.risk_parity_sizer import (
        calc_position_size, kelly_optimal_size, risk_parity_weights,
        correlation_adjusted_size, portfolio_allocator, max_drawdown_check,
    )

    size = calc_position_size("BTCUSDT", capital=100_000, volatility=0.04)
    kelly = kelly_optimal_size(win_rate=0.60, avg_win=0.03, avg_loss=0.02)

Dependencies: numpy only.
"""

from typing import Dict, List, Optional, Tuple, Union

import numpy as np

# ---------------------------------------------------------------------------
# Asset-class heuristic for correlation grouping
# ---------------------------------------------------------------------------
_CRYPTO_SUFFIXES = ("USDT", "USD", "BUSD", "BTC", "ETH")
_FOREX_QUOTES = ("USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD")


def _asset_class(symbol: str) -> str:
    """Infer asset class from symbol name (simple heuristic)."""
    s = symbol.upper().strip()
    # Forex: 6-letter all-alpha with known quote currency
    if len(s) == 6 and s.isalpha() and s[3:] in _FOREX_QUOTES:
        return "forex"
    # Crypto: ends with common quote suffixes
    for suf in _CRYPTO_SUFFIXES:
        if s.endswith(suf):
            return "crypto"
    # Equity: short alphabetic tickers
    if len(s) <= 5 and s.isalpha():
        return "equity"
    return "unknown"


# ---------------------------------------------------------------------------
# Core position sizing
# ---------------------------------------------------------------------------

def calc_position_size(
    symbol: str,
    capital: float,
    volatility: float,
    max_risk_pct: float = 0.02,
    max_position_pct: float = 0.20,
) -> float:
    """Compute dollar amount to allocate using volatility-based sizing.

    Size = (capital * max_risk_pct) / volatility, capped at
    max_position_pct of capital.

    Parameters
    ----------
    symbol : str
        Trading pair (used for logging / future enhancements).
    capital : float
        Total portfolio value in USD.
    volatility : float
        Asset's annualized volatility as a decimal (e.g. 0.04 = 4%).
    max_risk_pct : float
        Maximum fraction of capital to risk per trade (default 2%).
    max_position_pct : float
        Hard cap on position size as fraction of capital (default 20%).

    Returns
    -------
    float
        Dollar amount to allocate.
    """
    if volatility <= 0 or capital <= 0:
        return 0.0

    raw_size = (capital * max_risk_pct) / volatility
    cap = capital * max_position_pct
    return min(raw_size, cap)


# ---------------------------------------------------------------------------
# Kelly criterion
# ---------------------------------------------------------------------------

def kelly_optimal_size(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    cap: float = 0.02,
) -> float:
    """Compute Kelly-optimal fraction of capital to bet.

    Kelly fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win

    Capped at ``cap`` (default 2%) to prevent over-betting (fractional Kelly).
    Returns 0 if edge is negative.

    Parameters
    ----------
    win_rate : float
        Historical win rate as a fraction (e.g. 0.60 = 60%).
    avg_win : float
        Average winning trade return as a fraction (e.g. 0.03 = 3%).
    avg_loss : float
        Average losing trade return as a POSITIVE fraction (e.g. 0.02 = 2%).
    cap : float
        Maximum allowed fraction (default 0.02 = 2% of capital).

    Returns
    -------
    float
        Fraction of capital to allocate (0.0 to ``cap``).
    """
    if avg_win <= 0:
        return 0.0

    edge = win_rate * avg_win - (1.0 - win_rate) * avg_loss
    if edge <= 0:
        return 0.0

    kelly = edge / avg_win
    return min(kelly, cap)


# ---------------------------------------------------------------------------
# Inverse-volatility (risk parity) weights
# ---------------------------------------------------------------------------

def risk_parity_weights(
    assets: List[str],
    volatilities: List[float],
) -> Dict[str, float]:
    """Compute inverse-volatility weights that sum to 1.0.

    weight_i = (1 / vol_i) / sum(1 / vol_j)

    Parameters
    ----------
    assets : list[str]
        Asset symbols.
    volatilities : list[float]
        Corresponding annualized volatilities (same order as assets).

    Returns
    -------
    dict[str, float]
        Mapping of symbol -> weight.  All weights sum to 1.0.

    Raises
    ------
    ValueError
        If lengths differ or any volatility is <= 0.
    """
    if len(assets) != len(volatilities):
        raise ValueError(
            f"Length mismatch: {len(assets)} assets vs {len(volatilities)} volatilities"
        )
    if any(v <= 0 for v in volatilities):
        raise ValueError("All volatilities must be > 0")

    inv_vols = [1.0 / v for v in volatilities]
    total = sum(inv_vols)

    return {asset: iv / total for asset, iv in zip(assets, inv_vols)}


# ---------------------------------------------------------------------------
# Correlation-adjusted sizing
# ---------------------------------------------------------------------------

def correlation_adjusted_size(
    base_size: float,
    new_symbol: str,
    existing_positions: Dict[str, float],
    correlation_threshold: float = 0.7,
) -> float:
    """Reduce position size if new trade is highly correlated with existing ones.

    Uses a simple asset-class heuristic: if the new symbol shares its asset
    class with any existing position, reduce the allocation by 50% for each
    correlated position (multiplicative, floored at 25% of base_size).

    Parameters
    ----------
    base_size : float
        Unadjusted dollar allocation for the new trade.
    new_symbol : str
        Symbol of the proposed trade.
    existing_positions : dict[str, float]
        Mapping of currently-held symbols to their dollar sizes.
    correlation_threshold : float
        Unused in the heuristic version but kept for API compatibility
        with a future covariance-matrix implementation.

    Returns
    -------
    float
        Adjusted dollar allocation.
    """
    if not existing_positions:
        return base_size

    new_class = _asset_class(new_symbol)
    adjusted = base_size

    for sym in existing_positions:
        if _asset_class(sym) == new_class:
            adjusted *= 0.5  # halve for each correlated position

    # Floor at 25% of original to avoid sizing down to near-zero
    return max(adjusted, base_size * 0.25)


# ---------------------------------------------------------------------------
# Portfolio allocator (target-vol scaling)
# ---------------------------------------------------------------------------

def portfolio_allocator(
    signals: List[Dict],
    capital: float,
    target_vol_annual: float = 0.10,
) -> List[Dict]:
    """Allocate capital across signals so portfolio vol ~ target_vol_annual.

    Each signal dict must contain:
        symbol, direction, confidence, volatility

    Returns the same list with ``position_size_usd`` and ``weight`` added.

    Parameters
    ----------
    signals : list[dict]
        Signal dicts with at least {symbol, direction, confidence, volatility}.
    capital : float
        Total portfolio capital in USD.
    target_vol_annual : float
        Desired annualized portfolio volatility (default 10%).

    Returns
    -------
    list[dict]
        Input dicts enriched with position_size_usd and weight fields.
    """
    if not signals or capital <= 0:
        return signals

    # Filter out signals with invalid volatility
    valid = [s for s in signals if s.get("volatility", 0) > 0]
    if not valid:
        for s in signals:
            s["position_size_usd"] = 0.0
            s["weight"] = 0.0
        return signals

    # Step 1: inverse-vol weights
    vols = [s["volatility"] for s in valid]
    symbols = [s["symbol"] for s in valid]
    weights = risk_parity_weights(symbols, vols)

    # Step 2: portfolio vol under equal-correlation assumption (rho = 0.5)
    rho = 0.5
    n = len(valid)
    w_arr = np.array([weights[s["symbol"]] for s in valid])
    v_arr = np.array(vols)

    # Portfolio variance = sum(wi^2 * vi^2) + rho * sum_i!=j(wi*wj*vi*vj)
    port_var = np.sum((w_arr * v_arr) ** 2) + rho * (
        np.sum(w_arr * v_arr) ** 2 - np.sum((w_arr * v_arr) ** 2)
    )
    port_vol = np.sqrt(max(port_var, 1e-12))

    # Step 3: scale factor to hit target vol
    scale = target_vol_annual / port_vol if port_vol > 0 else 1.0
    # Don't lever up beyond 1.5x
    scale = min(scale, 1.5)

    # Step 4: assign sizes
    for s in signals:
        sym = s["symbol"]
        if sym in weights:
            w = weights[sym] * scale
            s["weight"] = round(w, 6)
            s["position_size_usd"] = round(capital * w, 2)
        else:
            s["weight"] = 0.0
            s["position_size_usd"] = 0.0

    return signals


# ---------------------------------------------------------------------------
# Drawdown guard
# ---------------------------------------------------------------------------

def max_drawdown_check(
    current_dd_pct: float,
    threshold: float = 0.12,
) -> Dict[str, Union[bool, str, float]]:
    """Check whether new trades are allowed given current drawdown.

    - DD < threshold/2:  full size (scale_factor = 1.0)
    - threshold/2 <= DD <= threshold:  linear ramp-down
    - DD > threshold:  trading halted (allowed = False)

    Parameters
    ----------
    current_dd_pct : float
        Current drawdown as a positive fraction (e.g. 0.08 = 8%).
    threshold : float
        Maximum tolerable drawdown (default 12%).

    Returns
    -------
    dict
        {allowed: bool, reason: str, scale_factor: float}
    """
    half = threshold / 2.0

    if current_dd_pct > threshold:
        return {
            "allowed": False,
            "reason": (
                f"Drawdown {current_dd_pct*100:.1f}% exceeds "
                f"threshold {threshold*100:.1f}%. Trading halted."
            ),
            "scale_factor": 0.0,
        }

    if current_dd_pct > half:
        # Linear ramp: 1.0 at half, 0.0 at threshold
        scale = (threshold - current_dd_pct) / half
        return {
            "allowed": True,
            "reason": (
                f"Drawdown {current_dd_pct*100:.1f}% is between "
                f"{half*100:.1f}%-{threshold*100:.1f}%. "
                f"Reducing size to {scale*100:.0f}%."
            ),
            "scale_factor": round(scale, 4),
        }

    return {
        "allowed": True,
        "reason": (
            f"Drawdown {current_dd_pct*100:.1f}% is within safe zone "
            f"(< {half*100:.1f}%). Full size allowed."
        ),
        "scale_factor": 1.0,
    }


# ---------------------------------------------------------------------------
# Quick sanity check when run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== Risk-Parity Position Sizer ===\n")

    # calc_position_size
    size = calc_position_size("BTCUSDT", capital=100_000, volatility=0.04)
    print(f"calc_position_size(BTCUSDT, $100k, vol=4%): ${size:,.2f}")

    # Kelly
    k = kelly_optimal_size(0.60, 0.03, 0.02)
    print(f"kelly_optimal_size(WR=60%, win=3%, loss=2%): {k*100:.4f}%")

    # Risk parity weights
    w = risk_parity_weights(
        ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        [0.60, 0.80, 1.20],
    )
    print(f"risk_parity_weights: {w}")

    # Correlation adjustment
    adj = correlation_adjusted_size(
        5000, "ETHUSDT", {"BTCUSDT": 10000, "SOLUSDT": 5000}
    )
    print(f"correlation_adjusted_size(ETH, existing BTC+SOL): ${adj:,.2f}")

    # Portfolio allocator
    sigs = [
        {"symbol": "BTCUSDT", "direction": "LONG", "confidence": 0.8, "volatility": 0.60},
        {"symbol": "EURUSD", "direction": "SHORT", "confidence": 0.6, "volatility": 0.08},
    ]
    alloc = portfolio_allocator(sigs, capital=100_000)
    for s in alloc:
        print(f"  {s['symbol']}: ${s['position_size_usd']:,.2f} (weight={s['weight']:.4f})")

    # Drawdown check
    for dd in [0.03, 0.08, 0.15]:
        chk = max_drawdown_check(dd)
        print(f"DD={dd*100:.0f}%: allowed={chk['allowed']}, scale={chk['scale_factor']}, {chk['reason']}")
