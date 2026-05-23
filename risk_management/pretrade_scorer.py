"""
Pre-Trade Signal Scorer — Monte Carlo + Cost-Adjusted Signal Quality
=====================================================================
For each candidate pick, simulates price paths to estimate:
  - Probability of hitting TP before SL
  - Expected net P&L after transaction costs
  - Risk-adjusted score (Sharpe-like per-trade metric)

Used by picks_router to reject signals with poor risk/reward BEFORE
they reach Discord.

Design: Lightweight, no heavy dependencies. Uses numpy geometric
Brownian motion — no external libraries beyond numpy.
"""

import numpy as np
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Lazy imports to avoid circular deps
_cost_model = None
_vol_forecaster = None


def _get_cost_model():
    global _cost_model
    if _cost_model is None:
        try:
            from ml_battleground.shared import cost_model
            _cost_model = cost_model
        except ImportError:
            _cost_model = False  # sentinel: tried and failed
    return _cost_model if _cost_model else None


def _get_vol(pair: str) -> float:
    """Get vol forecast, with graceful fallback."""
    try:
        from risk_management.crypto_vol_forecaster import forecast_crypto_vol
        return forecast_crypto_vol(pair)
    except Exception:
        return 0.02  # 2% default


def score_signal(
    symbol: str,
    entry_price: float,
    target_price: float,
    stop_price: float,
    direction: str = "BUY",
    vol_override: Optional[float] = None,
    n_sims: int = 500,
    horizon_bars: int = 24,
) -> Dict:
    """
    Score a trading signal using Monte Carlo simulation + cost adjustment.

    Returns dict with:
        prob_tp: probability of hitting TP first
        prob_sl: probability of hitting SL first
        expected_net_pnl: expected P&L after costs
        cost_pct: round-trip transaction cost
        vol_forecast: volatility used
        grade: "A" (strong), "B" (acceptable), "C" (marginal), "F" (reject)
        pass_filter: True if grade is A or B
    """
    # Get volatility
    vol = vol_override or _get_vol(symbol)

    # Get transaction cost
    cm = _get_cost_model()
    cost = cm.round_trip_cost(symbol) if cm else 0.005  # 0.5% default

    # Compute distances as percentage of entry
    if direction.upper() == "BUY":
        tp_dist = (target_price - entry_price) / entry_price
        sl_dist = (entry_price - stop_price) / entry_price
    else:  # SELL/SHORT
        tp_dist = (entry_price - target_price) / entry_price
        sl_dist = (stop_price - entry_price) / entry_price

    if tp_dist <= 0 or sl_dist <= 0:
        return {
            "prob_tp": 0.0, "prob_sl": 1.0,
            "expected_net_pnl": -sl_dist - cost,
            "cost_pct": cost, "vol_forecast": vol,
            "grade": "F", "pass_filter": False,
            "reason": "invalid TP/SL distances"
        }

    # Monte Carlo: simulate price paths as GBM
    rng = np.random.default_rng()
    dt = 1.0  # per bar

    tp_hits = 0
    sl_hits = 0
    pnls = []

    # Vectorized simulation
    # Generate all random returns at once: (n_sims, horizon_bars)
    z = rng.standard_normal((n_sims, horizon_bars))
    log_returns = -0.5 * vol**2 * dt + vol * np.sqrt(dt) * z

    # Cumulative returns from entry
    cum_returns = np.cumsum(log_returns, axis=1)
    # Price paths as ratio to entry (entry = 1.0)
    price_ratios = np.exp(cum_returns)

    for i in range(n_sims):
        path = price_ratios[i]
        hit_tp = False
        hit_sl = False

        for ratio in path:
            move = ratio - 1.0  # percent move from entry
            if move >= tp_dist:
                hit_tp = True
                break
            if move <= -sl_dist:
                hit_sl = True
                break

        if hit_tp:
            tp_hits += 1
            pnls.append(tp_dist - cost)
        elif hit_sl:
            sl_hits += 1
            pnls.append(-sl_dist - cost)
        else:
            # Mark to market at horizon end
            final_move = float(path[-1] - 1.0)
            pnls.append(final_move - cost)

    pnls = np.array(pnls)
    prob_tp = tp_hits / n_sims
    prob_sl = sl_hits / n_sims
    expected_net = float(pnls.mean())

    # Grade the signal
    rr_ratio = tp_dist / sl_dist if sl_dist > 0 else 0

    # Grade based on risk-reward structure and Monte Carlo outcomes.
    # IMPORTANT: Don't be overly strict — the user has been burned by
    # quality gates that filter out everything. Only reject truly bad setups.

    if rr_ratio >= 1.5 and prob_tp >= 0.30 and expected_net > -cost:
        grade = "A"
    elif rr_ratio >= 1.0 and prob_tp >= 0.25 and expected_net > -2 * cost:
        grade = "B"
    elif prob_tp >= 0.20 and rr_ratio >= 0.8:
        grade = "C"
    else:
        grade = "F"

    return {
        "prob_tp": round(prob_tp, 4),
        "prob_sl": round(prob_sl, 4),
        "expected_net_pnl": round(expected_net, 6),
        "cost_pct": round(cost, 4),
        "vol_forecast": round(vol, 6),
        "rr_ratio": round(rr_ratio, 2),
        "grade": grade,
        "pass_filter": grade in ("A", "B"),
        "n_sims": n_sims,
    }
