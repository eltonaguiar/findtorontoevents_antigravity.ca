"""Paper portfolio manager — $10K virtual equity, ATR-based sizing.

NOTE — SNAPSHOT-RESOLVER ARTIFACT (2026-06-03): WR/PF here is inflated by single
daily-snapshot TP/SL resolution (no intrabar OHLC path) — intraday SL touches are missed.
Do not size up on these numbers. See docs/RESOLVER_SNAPSHOT_ARTIFACT_AFFECTED_PORTFOLIOS_2026-06-03.md
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List

from . import config
from .data_fetcher import fetch_current_price
from . import ratio_store

logger = logging.getLogger(__name__)


def compute_position_size(equity: float, entry_price: float, stop_loss: float) -> float:
    risk_per_unit = abs(entry_price - stop_loss)
    if risk_per_unit == 0:
        return 0
    risk_amount = equity * (config.RISK_PER_TRADE_PCT / 100)
    quantity = risk_amount / risk_per_unit
    return round(quantity * entry_price, 2)


def open_positions_from_picks(picks: List[Dict]):
    open_positions = ratio_store.get_open_positions()
    if len(open_positions) >= config.MAX_CONCURRENT_POSITIONS:
        logger.info("Max positions (%d) reached, skipping new entries", config.MAX_CONCURRENT_POSITIONS)
        return
    equity = ratio_store.get_portfolio_equity()
    existing_symbols = {p["symbol"] for p in open_positions}
    slots = config.MAX_CONCURRENT_POSITIONS - len(open_positions)
    for pick in picks[:slots]:
        if pick["symbol"] in existing_symbols:
            continue
        entry = pick.get("entry_price", 0)
        sl = pick.get("stop_loss", 0)
        if entry == 0 or sl == 0:
            continue
        qty = compute_position_size(equity, entry, sl)
        risk_amount = equity * (config.RISK_PER_TRADE_PCT / 100)
        ratio_store.open_position(pick, quantity=qty, risk_amount=risk_amount)
        logger.info("Opened %s %s @ %.2f (qty=$%.2f, TP=%.2f, SL=%.2f)",
                     pick["direction"], pick["symbol"], entry, qty, pick["take_profit"], pick["stop_loss"])


def monitor_positions():
    positions = ratio_store.get_open_positions()
    if not positions:
        return
    for pos in positions:
        symbol = pos["symbol"]
        price = fetch_current_price(symbol)
        if price is None:
            continue
        entry = pos["entry_price"]
        tp = pos["take_profit"]
        sl = pos["stop_loss"]
        direction = pos["direction"]
        if direction == "LONG":
            if price >= tp:
                ratio_store.close_position(pos["signal_id"], price, "TP_HIT")
                logger.info("TP HIT: %s LONG @ %.2f -> %.2f", symbol, entry, price)
            elif price <= sl:
                ratio_store.close_position(pos["signal_id"], price, "SL_HIT")
                logger.info("SL HIT: %s LONG @ %.2f -> %.2f", symbol, entry, price)
        else:
            if price <= tp:
                ratio_store.close_position(pos["signal_id"], price, "TP_HIT")
                logger.info("TP HIT: %s SHORT @ %.2f -> %.2f", symbol, entry, price)
            elif price >= sl:
                ratio_store.close_position(pos["signal_id"], price, "SL_HIT")
                logger.info("SL HIT: %s SHORT @ %.2f -> %.2f", symbol, entry, price)
        opened = datetime.fromisoformat(pos["opened_at"].replace("Z", "+00:00"))
        age_hours = (datetime.now(timezone.utc) - opened).total_seconds() / 3600
        if age_hours > config.MAX_HOLD_HOURS:
            ratio_store.close_position(pos["signal_id"], price, "TIMEOUT")
            logger.info("TIMEOUT: %s %s after %.1fh", symbol, direction, age_hours)
    ratio_store.save_snapshot()


def get_portfolio_summary() -> Dict:
    equity = ratio_store.get_portfolio_equity()
    open_pos = ratio_store.get_open_positions()
    closed = ratio_store.get_closed_positions(limit=9999)
    wins = sum(1 for p in closed if (p.get("pnl_pct") or 0) > 0)
    losses = sum(1 for p in closed if (p.get("pnl_pct") or 0) <= 0)
    total = wins + losses
    total_pnl = sum(float(p.get("pnl_dollar", 0) or 0) for p in closed)
    return {
        "equity": round(equity, 2),
        "starting_capital": config.STARTING_CAPITAL,
        "pnl_pct": round((equity - config.STARTING_CAPITAL) / config.STARTING_CAPITAL * 100, 2),
        "total_pnl": round(total_pnl, 2),
        "open_positions": len(open_pos),
        "positions": open_pos,
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / total * 100, 2) if total else 0,
    }
