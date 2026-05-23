"""PnL computation utilities."""


def compute_pnl_pct(entry: float, current: float, direction: str) -> float:
    """Compute unrealized PnL percentage.

    For SHORT: profit when price drops → (entry - current) / entry * 100
    For LONG:  profit when price rises → (current - entry) / entry * 100
    """
    if entry <= 0:
        return 0.0
    if direction.upper() == "SHORT":
        return round((entry - current) / entry * 100, 4)
    return round((current - entry) / entry * 100, 4)


def check_tp_sl(
    entry: float,
    current: float,
    tp: float,
    sl: float,
    direction: str,
) -> str:
    """Check if TP or SL was hit.

    Returns: 'TP_HIT', 'SL_HIT', or 'ACTIVE'.
    Rule: if both crossed in same check, TP wins.
    """
    d = direction.upper()
    tp_hit = False
    sl_hit = False

    if d == "SHORT":
        tp_hit = current <= tp
        sl_hit = current >= sl
    else:  # LONG
        tp_hit = current >= tp
        sl_hit = current <= sl

    if tp_hit:
        return "TP_HIT"
    if sl_hit:
        return "SL_HIT"
    return "ACTIVE"
