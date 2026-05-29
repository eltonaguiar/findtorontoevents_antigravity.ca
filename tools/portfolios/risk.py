"""Risk gates, TP/SL derivation, breach checks and exit logic (Phase 2).

PURE / DETERMINISTIC: no DB, no network, no file IO. The ``appetite`` arg is
one of the dicts returned by ``tools.portfolios.profiles.get_profile`` (see
config/portfolio_risk_profiles.json). Directions are case-insensitive
("long"/"short"). See docs/DESIGN_AI_MODEL_HEDGE_FUND_PORTFOLIOS_2026-05-29.md
§4 (knobs) + §5 (② trend filter, ④ risk check, ⑥ exit).

position dict shape (the fields this module reads):
    {
      "direction": "long"|"short",
      "asset_class": "EQUITY"|...,
      "entry_price": float,
      "tp_price": float|None,
      "sl_price": float|None,
      "weight_at_entry": float,          # fraction of NAV (0..1)
      "entry_date": "YYYY-MM-DD" (optional, for time-stop),
      "max_hold_days": int|None (optional, for time-stop),
    }
"""
from __future__ import annotations

from datetime import date, datetime


def _norm_dir(direction: str) -> str:
    return (direction or "").strip().lower()


def _is_long(direction: str) -> bool:
    return _norm_dir(direction) in ("long", "buy")


def _parse_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# ② TREND FILTER
# --------------------------------------------------------------------------- #
def passes_trend_filter(direction: str, price: float, ma_value: float | None,
                        ma_days: int | None) -> bool:
    """EOD trend gate.

    - ma_days is None  -> no trend filter for this appetite -> always True.
    - ma_value is None -> we cannot confirm the trend -> reject (False).
    - LONG  passes when price >= ma_value.
    - SHORT passes when price <= ma_value.
    """
    if ma_days is None:
        return True
    if ma_value is None or price is None:
        return False
    if _is_long(direction):
        return price >= ma_value
    return price <= ma_value


# --------------------------------------------------------------------------- #
# ⑤ TP / SL derivation
# --------------------------------------------------------------------------- #
def compute_tp_sl(direction: str, entry_price: float, appetite: dict,
                  atr: float | None = None) -> tuple[float | None, float | None]:
    """Return ``(tp_price, sl_price)`` for a new position.

    Stop-loss: ``atr_mult * atr`` distance if an ATR is supplied, otherwise
    the ``pct_floor`` percentage of entry. Take-profit: ``pct`` if defined,
    else an ``r_multiple`` of the stop distance; a ``"trail"`` r_multiple
    (or missing TP config) yields ``tp_price = None`` (trail-only / let
    winners run). Signs are flipped for shorts.
    """
    if entry_price is None or entry_price <= 0:
        return (None, None)

    long_side = _is_long(direction)
    sl_cfg = appetite.get("stop_loss") or {}
    tp_cfg = appetite.get("take_profit") or {}

    # --- stop-loss distance (always positive) ---
    atr_mult = sl_cfg.get("atr_mult")
    pct_floor = sl_cfg.get("pct_floor")  # e.g. -5.0 meaning -5%
    sl_distance = None
    if atr is not None and atr_mult is not None and atr > 0:
        sl_distance = atr_mult * atr
    elif pct_floor is not None:
        sl_distance = abs(pct_floor) / 100.0 * entry_price

    if sl_distance is None or sl_distance <= 0:
        sl_price = None
    elif long_side:
        sl_price = entry_price - sl_distance
    else:
        sl_price = entry_price + sl_distance

    # --- take-profit ---
    tp_pct = tp_cfg.get("pct")
    r_multiple = tp_cfg.get("r_multiple")

    tp_price: float | None = None
    if tp_pct is not None:
        move = abs(tp_pct) / 100.0 * entry_price
        tp_price = entry_price + move if long_side else entry_price - move
    elif isinstance(r_multiple, (int, float)) and sl_distance and sl_distance > 0:
        move = r_multiple * sl_distance
        tp_price = entry_price + move if long_side else entry_price - move
    else:
        # r_multiple == "trail" (or no usable TP config) -> trail-only.
        tp_price = None

    return (tp_price, sl_price)


# --------------------------------------------------------------------------- #
# ④ RISK CHECK (caps)
# --------------------------------------------------------------------------- #
def _weight_of(p: dict) -> float:
    return float(p.get("weight_at_entry") or 0.0)


def would_breach(open_positions: list[dict], candidate: dict, appetite: dict,
                 nav_usd: float) -> tuple[bool, str]:
    """Check whether opening ``candidate`` breaches any appetite cap.

    Returns ``(ok, reason)``. ``ok`` is True (reason "") when the candidate
    fits within: max_open_positions, max_single_position_pct,
    max_class_exposure_pct (candidate + existing in that class), and
    gross_exposure_cap_pct (candidate + all existing). The FIRST breach
    found is reported.
    """
    open_positions = open_positions or []
    cand_weight = _weight_of(candidate)
    cand_class = (candidate.get("asset_class") or "").upper()

    # max open positions
    max_open = appetite.get("max_open_positions")
    if max_open is not None and len(open_positions) + 1 > max_open:
        return (False, "max_open_positions")

    # single position cap
    max_single = appetite.get("max_single_position_pct")
    if max_single is not None and cand_weight * 100.0 > max_single + 1e-9:
        return (False, "max_single_position_pct")

    # class exposure cap
    max_class = appetite.get("max_class_exposure_pct")
    if max_class is not None:
        class_sum = cand_weight + sum(
            _weight_of(p) for p in open_positions
            if (p.get("asset_class") or "").upper() == cand_class
        )
        if class_sum * 100.0 > max_class + 1e-9:
            return (False, "max_class_exposure_pct")

    # gross exposure cap
    gross_cap = appetite.get("gross_exposure_cap_pct")
    if gross_cap is not None:
        gross_sum = cand_weight + sum(_weight_of(p) for p in open_positions)
        if gross_sum * 100.0 > gross_cap + 1e-9:
            return (False, "gross_exposure_cap_pct")

    return (True, "")


# --------------------------------------------------------------------------- #
# ④ DRAWDOWN CIRCUIT-BREAKER
# --------------------------------------------------------------------------- #
def drawdown_breaker_tripped(mtd_return_pct: float | None, appetite: dict) -> bool:
    """True when month-to-date return has hit/breached the breaker threshold.

    ``drawdown_breaker_pct`` is a negative number (e.g. -8.0). When the
    portfolio's MTD return is at or below it, new entries are halted.
    """
    breaker = appetite.get("drawdown_breaker_pct")
    if breaker is None or mtd_return_pct is None:
        return False
    return mtd_return_pct <= breaker


# --------------------------------------------------------------------------- #
# ⑥ EXIT
# --------------------------------------------------------------------------- #
def check_exit(position: dict, current_price: float, ma_value: float | None = None,
               asof_date=None) -> tuple[bool, str]:
    """Evaluate exit conditions for an open position at EOD.

    Priority: TP -> SL -> trend_flip -> time_stop. Returns
    ``(should_exit, reason)`` where reason is one of
    {"tp", "sl", "trend_flip", "time_stop", ""}.
    """
    if current_price is None or current_price <= 0:
        return (False, "")

    long_side = _is_long(position.get("direction"))
    tp_price = position.get("tp_price")
    sl_price = position.get("sl_price")

    # TP hit
    if tp_price is not None:
        if long_side and current_price >= tp_price:
            return (True, "tp")
        if not long_side and current_price <= tp_price:
            return (True, "tp")

    # SL hit
    if sl_price is not None:
        if long_side and current_price <= sl_price:
            return (True, "sl")
        if not long_side and current_price >= sl_price:
            return (True, "sl")

    # Trend flip (price crosses the MA against the position)
    if ma_value is not None:
        if long_side and current_price < ma_value:
            return (True, "trend_flip")
        if not long_side and current_price > ma_value:
            return (True, "trend_flip")

    # Time stop
    max_hold = position.get("max_hold_days")
    if max_hold is not None:
        entry_d = _parse_date(position.get("entry_date"))
        asof_d = _parse_date(asof_date)
        if entry_d is not None and asof_d is not None:
            if (asof_d - entry_d).days >= max_hold:
                return (True, "time_stop")

    return (False, "")
