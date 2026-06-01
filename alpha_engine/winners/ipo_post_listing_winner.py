"""IPO research emitter: LONG T+90 momentum window (backtest WR 42%, PF 1.15 — REHAB tier).

Lockup-expiry SHORT is KILLED (PF 0.18). Emits only when a calendar name is in the
active post-listing window with positive 63d momentum. Often returns [] — by design.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

STRATEGY_NAME = "ipo_post_listing_momentum_long"
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CAL_PATH = DATA_DIR / "ipo_calendar.json"

ENTRY_DAYS_MIN = 85
ENTRY_DAYS_MAX = 150
MOM_DAYS = 63
MIN_PRICE = 5.0


def _days_since_ipo(ipo_date: str, now: datetime) -> int:
    ipo = datetime.strptime(ipo_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return (now.date() - ipo.date()).days


def generate_ipo_post_listing_winner_picks() -> list[dict[str, Any]]:
    if not CAL_PATH.exists():
        logger.warning("IPO calendar missing: %s", CAL_PATH)
        return []

    try:
        import yfinance as yf
        import pandas as pd
    except ImportError:
        return []

    cal = json.loads(CAL_PATH.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    picks: list[dict[str, Any]] = []

    for ipo in cal.get("ipos", []):
        sym = ipo.get("symbol")
        ipo_date = ipo.get("ipo_date")
        if not sym or not ipo_date:
            continue
        age = _days_since_ipo(ipo_date, now)
        if not (ENTRY_DAYS_MIN <= age <= ENTRY_DAYS_MAX):
            continue
        try:
            hist = yf.download(sym, period="1y", progress=False, auto_adjust=True)
        except Exception:
            continue
        if hist is None or hist.empty:
            continue
        if hasattr(hist.columns, "get_level_values"):
            try:
                hist.columns = hist.columns.get_level_values(0)
            except Exception:
                pass
        close = hist["Close"].dropna().astype(float)
        if len(close) < MOM_DAYS + 5:
            continue
        px = float(close.iloc[-1])
        if px < MIN_PRICE:
            continue
        ago = float(close.iloc[-MOM_DAYS - 1])
        if ago <= 0:
            continue
        mom = (px - ago) / ago
        if mom <= 0:
            continue
        picks.append({
            "symbol": sym,
            "direction": "LONG",
            "strategy": STRATEGY_NAME,
            "asset_class": "IPO",
            "category": "equity",
            "entry_price": round(px, 2),
            "take_profit": round(px * 1.15, 2),
            "stop_loss": round(px * 0.92, 2),
            "confidence": round(min(0.68, 0.55 + mom), 3),
            "generated_at": now.isoformat(),
            "reason": f"Post-listing day {age}: 63d momentum {mom*100:+.1f}%",
            "source": "alpha_engine",
            "source_system": STRATEGY_NAME,
            "forced_resolution": {
                "max_hold_hours": 1440,
                "tp_pct": 15.0,
                "sl_pct": 8.0,
                "time_exit_at_market": True,
            },
            "paper_pilot": True,
            "extra": {
                "ipo_date": ipo_date,
                "days_since_ipo": age,
                "backtest_tier": "REHAB",
                "expected_slippage_bps": 20,
            },
        })

    logger.info("%s: %d picks (REHAB — n<100 backtest)", STRATEGY_NAME, len(picks))
    return picks[:3]
