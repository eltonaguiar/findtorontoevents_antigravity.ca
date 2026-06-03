"""Portfolio engine: orchestrates the §5 position lifecycle (Phase 2).

PURE / DETERMINISTIC: no DB, no network, no file IO. The daily runner
(Phase 3) supplies DB-backed ``portfolio_state`` + ``market`` data dicts and
persists the returned decisions.

See docs/DESIGN_AI_MODEL_HEDGE_FUND_PORTFOLIOS_2026-05-29.md §5:
    eligibility gate -> trend filter -> sizing -> risk check -> open w/ TP/SL
    -> daily mark -> exit (TP/SL/trend-flip/time-stop).

DICT SHAPES
-----------
pick = {
    "model": str, "symbol": str, "direction": "long"|"short",
    "asset_class": "EQUITY"|"CRYPTO"|..., "confidence": float (0..1, optional),
    "thesis": str (optional), "edge_signal": float (0..1),
    "source_pick_id": str (optional),
}

portfolio_state = {
    "nav_usd": float,
    "cash_usd": float,
    "open_positions": [position_dict, ...],
    "mtd_return_pct": float,            # month-to-date return %, negative = down
}

market = {
    "price": float,                     # EOD close used as entry / mark
    "ma_value": float|None,             # trailing MA for the appetite's ma_days
    "realized_vol": float|None,         # annualized realized vol of the symbol
    "atr": float|None,                  # for ATR-based stops (optional)
}

A `position` (returned by evaluate_entry on "open", and consumed by
mark_position / evaluate_exit) carries:
    symbol, asset_class, direction, entry_price, qty, weight_at_entry,
    tp_price, sl_price, entry_reason, sizing_reason, source_pick_id,
    entry_date (set by the runner), max_hold_days (optional).
"""
from __future__ import annotations

from . import risk, sizing


def _has_edge(pick: dict) -> bool:
    """A model is allowed to trade a pick only with a positive edge signal."""
    edge = pick.get("edge_signal")
    return isinstance(edge, (int, float)) and edge > 0


def _already_held(symbol: str, open_positions: list[dict]) -> bool:
    sym = (symbol or "").upper()
    return any((p.get("symbol") or "").upper() == sym for p in (open_positions or []))


def evaluate_entry(pick: dict, portfolio_state: dict, appetite: dict,
                   market: dict) -> dict:
    """Run the full entry pipeline for one pick.

    Returns a decision dict::

        {"action": "open", "reason": "opened",
         "weight": float, "qty": float, "tp_price": float|None,
         "sl_price": float|None, "position": {...}}

    or::

        {"action": "reject", "reason": <gate name>, ...}

    Reject reasons: "class_not_allowed", "already_held", "no_edge",
    "trend_filter", "drawdown_breaker", "zero_weight", or any
    would_breach() cap name.
    """
    symbol = pick.get("symbol")
    asset_class = (pick.get("asset_class") or "").upper()
    direction = pick.get("direction", "long")
    open_positions = portfolio_state.get("open_positions") or []
    nav_usd = float(portfolio_state.get("nav_usd") or 0.0)
    price = market.get("price")

    base = {"action": "reject", "symbol": symbol, "weight": 0.0, "qty": 0.0,
            "tp_price": None, "sl_price": None}

    # ① ELIGIBILITY GATE -----------------------------------------------------
    allowlist = [c.upper() for c in (appetite.get("asset_class_allowlist") or [])]
    if asset_class not in allowlist:
        return {**base, "reason": "class_not_allowed"}

    if _already_held(symbol, open_positions):
        return {**base, "reason": "already_held"}

    if not _has_edge(pick):
        return {**base, "reason": "no_edge"}

    # drawdown circuit-breaker halts NEW entries
    if risk.drawdown_breaker_tripped(portfolio_state.get("mtd_return_pct"), appetite):
        return {**base, "reason": "drawdown_breaker"}

    # ② TREND FILTER ---------------------------------------------------------
    ma_days = appetite.get("trend_filter_ma_days")
    if not risk.passes_trend_filter(direction, price, market.get("ma_value"), ma_days):
        return {**base, "reason": "trend_filter"}

    # ③ SIZING ---------------------------------------------------------------
    vscalar = sizing.vol_scalar(appetite.get("vol_target_annual"),
                                market.get("realized_vol"))
    weight = sizing.target_weight(
        edge_signal=float(pick.get("edge_signal") or 0.0),
        kelly_fraction=appetite.get("kelly_fraction"),
        vol_scalar=vscalar,
        max_single_position_pct=appetite.get("max_single_position_pct"),
    )
    if weight <= 0:
        return {**base, "reason": "zero_weight", "weight": weight}

    qty = sizing.position_qty(weight, nav_usd, price)
    if qty <= 0:
        return {**base, "reason": "zero_weight", "weight": weight, "qty": qty}

    # ④ RISK CHECK -----------------------------------------------------------
    candidate = {"asset_class": asset_class, "weight_at_entry": weight}
    ok, breach_reason = risk.would_breach(open_positions, candidate, appetite, nav_usd)
    if not ok:
        return {**base, "reason": breach_reason, "weight": weight, "qty": qty}

    # ⑤ OPEN POSITION --------------------------------------------------------
    tp_price, sl_price = risk.compute_tp_sl(direction, price, appetite,
                                            atr=market.get("atr"))

    sizing_reason = (
        f"kelly={appetite.get('kelly_fraction')} x edge={pick.get('edge_signal')} "
        f"x vol_scalar={round(vscalar, 4)} -> weight={round(weight, 4)} "
        f"(vol_target={appetite.get('vol_target_annual')}, "
        f"realized_vol={market.get('realized_vol')})"
    )
    entry_reason = (
        f"{pick.get('model', '?')}: {pick.get('thesis', '')} | "
        f"passed eligibility+trend(ma_days={ma_days})"
    ).strip()

    position = {
        "symbol": symbol,
        "asset_class": asset_class,
        "direction": risk._norm_dir(direction),
        "entry_price": price,
        "qty": qty,
        "weight_at_entry": weight,
        "tp_price": tp_price,
        "sl_price": sl_price,
        "entry_reason": entry_reason,
        "sizing_reason": sizing_reason,
        "source_pick_id": pick.get("source_pick_id"),
        "status": "open",
    }

    return {
        "action": "open",
        "reason": "opened",
        "symbol": symbol,
        "weight": weight,
        "qty": qty,
        "tp_price": tp_price,
        "sl_price": sl_price,
        "position": position,
    }


def mark_position(position: dict, current_price: float) -> dict:
    """Mark an open position to market; return unrealized PnL fields.

    Returns ``{"current_price", "unrealized_pnl_pct", "unrealized_pnl_usd",
    "market_value_usd"}``. PnL sign respects direction (short profits when
    price falls). Percentages are in % (e.g. 5.0 == +5%).
    """
    # 2026-06-03 P0 fix: entry_price comes back from MySQL as `Decimal`, but
    # current_price is a `float` (from prices.get_close). Python's `-` operator
    # raises TypeError on mixed float/Decimal. This crashed run_daily.py on the
    # first portfolio with positions, blocking the entire daily lifecycle —
    # 44 new portfolios (kimi_k2_6, mistral_large, qwen3_5_plus, etc. seeded
    # 2026-06-01..06-03) never got positions inserted because the writer died
    # at line 183 before reaching them. PF_NAV_SNAPSHOT max stuck at 2026-05-31.
    entry_raw = position.get("entry_price")
    entry = float(entry_raw) if entry_raw is not None else None
    qty = float(position.get("qty") or 0.0)
    long_side = risk._is_long(position.get("direction"))

    if entry is None or entry <= 0 or current_price is None or current_price <= 0:
        return {"current_price": current_price, "unrealized_pnl_pct": 0.0,
                "unrealized_pnl_usd": 0.0, "market_value_usd": 0.0}

    current_price = float(current_price)
    raw_pct = (current_price - entry) / entry
    pnl_pct = raw_pct if long_side else -raw_pct
    # USD PnL: per-unit price move * qty, sign-adjusted for direction.
    pnl_usd = (current_price - entry) * qty
    if not long_side:
        pnl_usd = -pnl_usd
    market_value = current_price * qty

    return {
        "current_price": current_price,
        "unrealized_pnl_pct": pnl_pct * 100.0,
        "unrealized_pnl_usd": pnl_usd,
        "market_value_usd": market_value,
    }


def evaluate_exit(position: dict, market: dict, asof_date=None) -> dict:
    """Wrap risk.check_exit; on exit compute realized PnL at current price.

    Returns ``{"action": "exit"|"hold", "reason": <exit reason>,
    "exit_price": float|None, "realized_pnl_pct": float|None,
    "realized_pnl_usd": float|None}``.
    """
    current_price = market.get("price")
    should_exit, reason = risk.check_exit(
        position, current_price, ma_value=market.get("ma_value"), asof_date=asof_date,
    )
    if not should_exit:
        return {"action": "hold", "reason": "", "exit_price": None,
                "realized_pnl_pct": None, "realized_pnl_usd": None}

    marked = mark_position(position, current_price)
    return {
        "action": "exit",
        "reason": reason,
        "exit_price": current_price,
        "realized_pnl_pct": marked["unrealized_pnl_pct"],
        "realized_pnl_usd": marked["unrealized_pnl_usd"],
    }
