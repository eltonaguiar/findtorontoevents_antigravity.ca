"""HyroTrader risk-sizer — volatility-scaled position sizing (FIX-9).

Implements Rob Carver's systematic approach (`pysystemtrade`) combined with
HyroTrader prop-challenge constraints from `docs/HYROTRADER_CHALLENGE_STRATEGY.md`:

  * Target volatility: 15% annualized on portfolio (typical hedge-fund target)
  * Instrument-specific scaling: position_size = target_risk / stop_distance
  * Half-Kelly cap: never exceed 0.5 * kelly_fraction for safety
  * Prop-challenge guardrails: 3% hard max per trade, 0.75% recommended,
    mandatory SL, daily 2.5% soft stop (reject new picks after this)

Inputs per pick:
  - account_balance : USD
  - entry_price     : float > 0
  - stop_loss       : float > 0 (same units as entry)
  - direction       : "LONG" | "SHORT"
  - win_rate_est    : float in [0, 1] for Kelly sizing (optional)
  - avg_win_pct     : typical win payoff (e.g. 2.5 means +2.5% per win)
  - avg_loss_pct    : typical loss (e.g. 1.0 means -1.0% per loss)
  - asset_class     : used for class-specific caps

Returns the sized-order record + human-readable rationale.

References:
  * Rob Carver, "Systematic Trading" (2015) — target-vol sizing
  * Kelly criterion, John Kelly (1956)
  * docs/HYROTRADER_CHALLENGE_STRATEGY.md — prop-challenge constraints
"""
from __future__ import annotations

from typing import Any


HYRO_HARD_MAX_RISK_PCT = 3.0
HYRO_RECOMMENDED_RISK_PCT = 0.75
HYRO_DAILY_SOFT_STOP_PCT = -2.5
HYRO_MIN_RR = 2.0
HYRO_CLASS_CAPS = {
    "CRYPTO": 0.75,       # high vol -> tight cap
    "FOREX": 1.0,
    "EQUITY": 1.25,
    "FUTURES": 1.0,
    "COMMODITY": 1.0,
    "ETF": 1.25,
    "BOND": 1.5,
}


def _f(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def kelly_fraction(win_rate: float, win_pct: float, loss_pct: float) -> float:
    """Standard Kelly: f = W/L * p - (1-p)/L where W=avg_win, L=avg_loss.

    Simplified for fixed-payoff: f = p - (1-p) * (L/W)
    Returns fraction of capital; clamp to [0, 1].
    """
    if win_pct <= 0 or loss_pct <= 0 or not (0 <= win_rate <= 1):
        return 0.0
    # Edge form of Kelly for asymmetric payoffs
    f = (win_rate * win_pct - (1 - win_rate) * loss_pct) / (win_pct * loss_pct)
    return max(0.0, min(1.0, f))


def size_pick(
    pick: dict,
    account_balance: float = 5000.0,
    target_risk_pct: float = HYRO_RECOMMENDED_RISK_PCT,
    todays_realized_pnl_pct: float = 0.0,
    win_rate_est: float | None = None,
    avg_win_pct: float | None = None,
    avg_loss_pct: float | None = None,
    half_kelly: bool = True,
) -> dict:
    """Compute a position-sized order for a pick. Returns all reasoning.

    If the daily-soft-stop is triggered (todays_realized_pnl_pct <= -2.5),
    returns size=0 with reject reason.
    """
    entry = _f(pick.get("entry_price"))
    stop = _f(pick.get("stop_loss"))
    direction = (pick.get("direction") or "LONG").upper()
    ac = (pick.get("asset_class") or "UNKNOWN").upper()
    rr = _f(pick.get("risk_reward") or pick.get("rr_ratio"))

    rej: list[str] = []

    # Daily soft-stop — strongest reject
    if todays_realized_pnl_pct <= HYRO_DAILY_SOFT_STOP_PCT:
        rej.append(f"daily_soft_stop({todays_realized_pnl_pct:.2f}% <= {HYRO_DAILY_SOFT_STOP_PCT}%)")
    if entry <= 0 or stop <= 0:
        rej.append("missing_entry_or_stop")
    if rr > 0 and rr < HYRO_MIN_RR:
        rej.append(f"rr_below_floor({rr:.2f}<{HYRO_MIN_RR})")

    stop_distance_pct = abs(entry - stop) / entry * 100.0 if entry > 0 else 0.0
    if stop_distance_pct <= 0:
        rej.append("degenerate_stop")

    if rej:
        return {"size_units": 0, "size_usd": 0.0, "reject_reasons": rej, "passed": False}

    # Target-volatility sizing: risk_amount = target_risk_pct * balance
    risk_amount_usd = (target_risk_pct / 100.0) * account_balance
    # Position value such that stop_distance loss == risk_amount
    # position_value * (stop_distance_pct / 100) = risk_amount
    position_value_usd = risk_amount_usd / (stop_distance_pct / 100.0)

    # Apply class cap
    class_cap_pct = HYRO_CLASS_CAPS.get(ac, HYRO_RECOMMENDED_RISK_PCT)
    class_cap_usd = (class_cap_pct / 100.0) * account_balance / (stop_distance_pct / 100.0)
    if position_value_usd > class_cap_usd:
        position_value_usd = class_cap_usd

    # Apply hard 3% cap (Hyro absolute)
    hard_cap_usd = (HYRO_HARD_MAX_RISK_PCT / 100.0) * account_balance / (stop_distance_pct / 100.0)
    if position_value_usd > hard_cap_usd:
        position_value_usd = hard_cap_usd

    # Kelly overlay (if user supplies win-rate estimate)
    kelly_applied = None
    if win_rate_est is not None and avg_win_pct and avg_loss_pct:
        k = kelly_fraction(win_rate_est, avg_win_pct, avg_loss_pct)
        if half_kelly:
            k = k * 0.5
        kelly_cap_usd = k * account_balance / (stop_distance_pct / 100.0)
        if kelly_cap_usd < position_value_usd:
            position_value_usd = kelly_cap_usd
            kelly_applied = round(k, 4)

    # Convert value to units
    size_units = position_value_usd / entry if entry > 0 else 0.0
    size_pct_of_balance = position_value_usd / account_balance * 100.0
    risk_actual_pct = size_pct_of_balance * (stop_distance_pct / 100.0)

    return {
        "size_units": round(size_units, 6),
        "size_usd": round(position_value_usd, 2),
        "size_pct_of_balance": round(size_pct_of_balance, 3),
        "risk_actual_pct": round(risk_actual_pct, 4),
        "stop_distance_pct": round(stop_distance_pct, 3),
        "class_cap_pct": class_cap_pct,
        "kelly_applied": kelly_applied,
        "reject_reasons": [],
        "passed": True,
        "direction": direction,
        "rationale": (
            f"target_risk={target_risk_pct}% -> {risk_amount_usd:.2f} USD; "
            f"stop_dist={stop_distance_pct:.2f}%; "
            f"class_cap={class_cap_pct}%; "
            f"hard_cap=3%"
            + (f"; half_kelly={kelly_applied}" if kelly_applied else "")
        ),
    }


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description="HyroTrader risk-sizer demo.")
    ap.add_argument("--entry", type=float, required=True)
    ap.add_argument("--stop", type=float, required=True)
    ap.add_argument("--rr", type=float, default=2.5)
    ap.add_argument("--direction", default="LONG")
    ap.add_argument("--asset-class", default="CRYPTO")
    ap.add_argument("--balance", type=float, default=5000.0)
    ap.add_argument("--target-risk-pct", type=float, default=HYRO_RECOMMENDED_RISK_PCT)
    args = ap.parse_args()

    p = dict(entry_price=args.entry, stop_loss=args.stop, risk_reward=args.rr,
             direction=args.direction, asset_class=args.asset_class)
    out = size_pick(p, account_balance=args.balance, target_risk_pct=args.target_risk_pct)
    print(json.dumps(out, indent=2))
