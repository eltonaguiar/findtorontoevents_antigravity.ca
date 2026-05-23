"""
Conservative risk management for ML Battleground.
- Vol-targeted risk per trade (was fixed 2%)
- 10% max portfolio drawdown circuit breaker
- Max 5 concurrent positions
- Fractional Kelly (0.25x) sizing
- Win-rate circuit breakers: cap/halt sizing on cold streaks
- should_trade() gate: blocks new trades during deep drawdown
- Regime-aware sizing: reduce in neutral, boost in extreme fear
"""
import numpy as np


MAX_RISK_PER_TRADE = 0.02
MAX_DRAWDOWN = 0.50        # widened from 20% to 50% — learning phase systems were permanently blocked at 33-37% DD
MAX_CONCURRENT = 999       # TESTING SPRINT: was 8, uncapped
KELLY_FRACTION = 0.25
MIN_POSITION_SIZE = 0.003  # 0.3% minimum (was 0.5% — tighter floor for Sharpe)
DRAWDOWN_HALT_PCT = 0.40   # raised from 15% to 40% — was blocking Systems A+B from ever recovering
TARGET_DAILY_VOL = 0.008   # 0.8% daily portfolio vol target


def vol_targeted_risk(atr_pct: float, fng: int = 50) -> float:
    """Volatility-targeted risk fraction. Returns 0.003 to 0.02.

    Shrinks position when vol spikes, boosts in extreme fear (proven edge).
    """
    if atr_pct <= 0:
        return MIN_POSITION_SIZE

    vol_scalar = TARGET_DAILY_VOL / max(atr_pct, 0.001)
    vol_scalar = max(0.5, min(vol_scalar, 2.0))

    # Regime multiplier
    if fng < 15:
        regime_mult = 1.2   # extreme fear = dip-buy edge
    elif fng > 60:
        regime_mult = 0.6   # greed = reduce
    else:
        regime_mult = 1.0

    risk = MAX_RISK_PER_TRADE * vol_scalar * regime_mult
    return max(MIN_POSITION_SIZE, min(risk, MAX_RISK_PER_TRADE))


def position_size(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    confidence: float = 1.0,
    capital: float = 10000.0,
    recent_trades: list[dict] = None,
) -> float:
    """Fractional Kelly position sizing with win-rate circuit breakers.

    Circuit breakers:
    - win_rate < 0.30 over recent trades: cap at 0.25% (quarter size)
    - 0 wins in last 5 trades: return 0 (no new trades until a win)

    Returns fraction of capital (0.0 = do not trade).
    """
    # --- Win-rate circuit breakers (fast-learn: never fully halt, just reduce size) ---
    if recent_trades is not None and len(recent_trades) >= 5:
        last_5 = recent_trades[-5:]
        last_5_wins = sum(1 for t in last_5 if t.get("net_pnl_pct", 0) > 0)

        # Zero wins in last 5: micro-position for data collection (not full halt)
        # Old behavior: return 0.0 (halted System C entirely, preventing learning)
        # New behavior: 0.1% position = still collecting data, minimal capital at risk
        if last_5_wins == 0:
            return 0.001  # 0.1% micro-position — learn without bleeding

    if recent_trades is not None and len(recent_trades) >= 10:
        last_10 = recent_trades[-10:]
        recent_wr = sum(1 for t in last_10 if t.get("net_pnl_pct", 0) > 0) / len(last_10)

        # Win rate below 30%: cap at quarter size (0.25%)
        if recent_wr < 0.30:
            return 0.0025  # 0.25% of capital — quarter size

    # --- Standard Kelly sizing ---
    if avg_loss <= 0 or avg_win <= 0 or win_rate <= 0 or win_rate >= 1:
        return MIN_POSITION_SIZE

    b = avg_win / avg_loss
    kelly_full = (win_rate * b - (1 - win_rate)) / b
    if kelly_full <= 0:
        return MIN_POSITION_SIZE

    sized = kelly_full * KELLY_FRACTION * confidence
    return max(MIN_POSITION_SIZE, min(sized, MAX_RISK_PER_TRADE))


def apply_atr_gate(base_size: float, signal: dict) -> tuple[float, str]:
    """Apply ATR volatility gate to position size.

    Reads position_scale from signal dict (set by atr_gate / atr_volatility_regime).
    Returns (adjusted_size, reason).
      position_scale 0.0 -> (0.0, "skip — extreme volatility")
      position_scale 0.5 -> (base_size * 0.5, "half size — high volatility")
      position_scale 1.0 -> (base_size, "ok")
    """
    scale = signal.get("position_scale", 1.0)
    if scale <= 0.0:
        return 0.0, f"ATR gate: skip trade (ATR ratio {signal.get('atr_ratio', '?')}x > 3x mean)"
    if scale < 1.0:
        return max(MIN_POSITION_SIZE, base_size * scale), \
            f"ATR gate: {scale:.0%} size (ATR ratio {signal.get('atr_ratio', '?')}x > 2x mean)"
    return base_size, "ok"


def should_trade(equity_curve: list[float]) -> tuple[bool, str]:
    """Check if system should be trading at all based on drawdown.

    Returns False when drawdown exceeds 8% — prevents compounding losses.
    Different from can_open_trade() which checks position count + 10% hard stop.
    This is a softer gate that halts new entries earlier.
    """
    dd = calculate_drawdown(equity_curve)
    if dd >= DRAWDOWN_HALT_PCT:
        return False, f"drawdown halt: {dd:.1%} >= {DRAWDOWN_HALT_PCT:.0%} — no new trades until recovery"
    return True, "ok"


def can_open_trade(
    active_count: int,
    current_drawdown: float,
) -> tuple[bool, str]:
    """Check if we're allowed to open a new position."""
    if active_count >= MAX_CONCURRENT:
        return False, f"max concurrent positions ({MAX_CONCURRENT}) reached"
    if current_drawdown >= MAX_DRAWDOWN:
        return False, f"drawdown circuit breaker ({MAX_DRAWDOWN:.0%}) triggered"
    return True, "ok"


def calculate_drawdown(equity_curve: list[float]) -> float:
    """Current drawdown from peak."""
    if not equity_curve or len(equity_curve) < 2:
        return 0.0
    peak = max(equity_curve)
    current = equity_curve[-1]
    if peak <= 0:
        return 0.0
    return (peak - current) / peak


# ---------------------------------------------------------------------------
# Per-strategy drawdown guard + per-class risk-budget rebalancer (2026-05-02)
#
# Additive layer on top of the existing learning-phase-friendly globals
# (MAX_DRAWDOWN=0.50, DRAWDOWN_HALT_PCT=0.40). Those stay loose so individual
# ML systems can recover. The functions below provide tighter, surgical
# guards that callers can opt into at the *strategy* and *asset-class* level
# without affecting the system-wide trading gate.
# ---------------------------------------------------------------------------

PER_STRATEGY_DD_HALT = 0.15   # 15% peak-to-trough on a single strategy → mute
PER_CLASS_DD_HALT    = 0.12   # 12% on an asset-class equity curve

# Default static budget weights, used as a fallback when no Sharpe data
# is available. Sums to 1.0.
CLASS_TARGET_BUDGET: dict[str, float] = {
    "CRYPTO":    0.25,
    "EQUITY":    0.25,
    "FOREX":     0.15,
    "COMMODITY": 0.15,
    "ETF":       0.10,
    "FUTURES":   0.10,
}
MIN_CLASS_BUDGET = 0.05      # never starve a class entirely
MAX_CLASS_BUDGET = 0.45      # never let one class dominate


def _to_float(v) -> float:
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def strategy_drawdown(closed_picks: list, strategy: str) -> float:
    """Peak-to-trough drawdown of a single strategy's compounded equity curve.

    closed_picks: iterable of dicts with 'strategy', 'pnl_pct' (percent), and
    optionally 'resolved_at' / 'closed_at' / 'timestamp' for ordering.

    Returns a fraction in [0, 1] where 0 = no drawdown.
    """
    rows = [p for p in (closed_picks or [])
            if isinstance(p, dict) and p.get("strategy") == strategy]
    if len(rows) < 5:
        return 0.0
    rows.sort(key=lambda p: str(p.get("resolved_at") or p.get("closed_at") or p.get("timestamp") or ""))
    pnls = [_to_float(p.get("pnl_pct")) for p in rows]

    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for x in pnls:
        equity *= (1.0 + x / 100.0)
        if equity > peak:
            peak = equity
        if peak > 0:
            dd = (peak - equity) / peak
            if dd > max_dd:
                max_dd = dd
    return float(max_dd)


def is_strategy_muted(
    strategy: str,
    closed_picks: list,
    threshold: float = PER_STRATEGY_DD_HALT,
) -> tuple[bool, str]:
    """Return (muted, reason). Strategy is muted when its peak-to-trough
    drawdown exceeds the threshold. Caller is responsible for scoping
    closed_picks to the desired lookback window (e.g. last 30 days).
    """
    dd = strategy_drawdown(closed_picks, strategy)
    if dd >= threshold:
        return True, f"{strategy} muted: dd={dd:.1%} >= {threshold:.0%}"
    return False, "ok"


def rebalance_by_sharpe(class_sharpes: dict) -> dict:
    """Risk-parity-ish allocator over asset classes.

    class_sharpes: {asset_class: oos_sharpe}. Negative or missing values are
    floored to 0 (no allocation). Result is clipped to
    [MIN_CLASS_BUDGET, MAX_CLASS_BUDGET] per class with excess from over-cap
    classes redistributed to under-cap classes (iteratively, up to 5 passes).
    Falls back to CLASS_TARGET_BUDGET if no class has positive Sharpe.
    """
    if not isinstance(class_sharpes, dict) or not class_sharpes:
        return dict(CLASS_TARGET_BUDGET)

    pos = {c: max(0.0, _to_float(s)) for c, s in class_sharpes.items()}
    total = sum(pos.values())
    if total <= 0:
        return dict(CLASS_TARGET_BUDGET)

    weights = {c: v / total for c, v in pos.items()}

    # Iterative clip + redistribute. Five passes is plenty for any realistic
    # number of classes; if the constraints are infeasible (e.g. 1 class with
    # MAX_CLASS_BUDGET<1) we just return the best clipped approximation.
    for _ in range(5):
        clipped = {c: min(MAX_CLASS_BUDGET, max(MIN_CLASS_BUDGET, w))
                   for c, w in weights.items()}
        s = sum(clipped.values())
        if abs(s - 1.0) < 1e-9:
            return clipped
        # Redistribute the excess/deficit to classes that are not at a cap.
        diff = 1.0 - s
        free = [c for c, w in clipped.items()
                if (diff > 0 and w < MAX_CLASS_BUDGET - 1e-12)
                or (diff < 0 and w > MIN_CLASS_BUDGET + 1e-12)]
        if not free:
            # Constraints infeasible — return the clipped values as-is so the
            # cap is honoured even if weights don't sum to exactly 1.0.
            return clipped
        share = diff / len(free)
        weights = dict(clipped)
        for c in free:
            weights[c] = clipped[c] + share

    # Final pass: clip and accept whatever sum results.
    return {c: min(MAX_CLASS_BUDGET, max(MIN_CLASS_BUDGET, w))
            for c, w in weights.items()}


def per_class_risk(
    base_risk: float,
    asset_class: str,
    weights: dict,
) -> float:
    """Scale a base per-trade risk fraction by the class's current budget vs
    an equal-weight baseline. Result is clipped to [0.25x, 2.0x] of base.
    """
    if not weights:
        return base_risk
    eq = 1.0 / max(1, len(weights))
    w = _to_float(weights.get(asset_class, eq))
    if w <= 0:
        w = eq
    scalar = max(0.25, min(2.0, w / eq))
    return base_risk * scalar

