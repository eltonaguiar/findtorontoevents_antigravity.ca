"""EQUITY winner: sector rotation top-3 (backtest 51.4% WR, PF 1.27)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

STRATEGY_NAME = "equity_sector_rotation_winner"
SECTOR_ETFS = (
    "XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLU", "XLY", "XLRE", "XLB", "XLC",
)
LOOKBACK = 63
TOP_N = 3
TP_PCT, SL_PCT = 0.08, 0.05


def generate_equity_sector_rotation_winner_picks() -> list[dict[str, Any]]:
    try:
        import yfinance as yf
        import pandas as pd
    except ImportError:
        return []

    raw = yf.download(list(SECTOR_ETFS), period="6mo", progress=False, auto_adjust=True)
    if raw is None or raw.empty:
        return []

    scored: list[tuple[str, float, float]] = []
    for sym in SECTOR_ETFS:
        try:
            if isinstance(raw.columns, pd.MultiIndex):
                if sym not in raw.columns.get_level_values(1):
                    continue
                close = raw["Close", sym].dropna()
            elif len(SECTOR_ETFS) == 1:
                close = raw["Close"].dropna()
            else:
                continue
            if len(close) < LOOKBACK + 5:
                continue
            px = float(close.iloc[-1])
            ago = float(close.iloc[-LOOKBACK - 1])
            if ago <= 0:
                continue
            mom = (px - ago) / ago
            if mom > 0:
                scored.append((sym, mom, px))
        except Exception:
            continue

    scored.sort(key=lambda x: x[1], reverse=True)
    now = datetime.now(timezone.utc).isoformat()
    picks: list[dict[str, Any]] = []

    for rank, (sym, mom, px) in enumerate(scored[:TOP_N], 1):
        conf = min(0.78, 0.60 + mom * 0.5)
        picks.append({
            "symbol": sym,
            "direction": "LONG",
            "strategy": STRATEGY_NAME,
            "asset_class": "EQUITY",
            "category": "equity",
            "entry_price": round(px, 2),
            "take_profit": round(px * (1 + TP_PCT), 2),
            "stop_loss": round(px * (1 - SL_PCT), 2),
            "confidence": round(conf, 3),
            "generated_at": now,
            "reason": f"Sector rotation rank #{rank}: 3m momentum {mom*100:+.1f}%",
            "source": "alpha_engine",
            "source_system": STRATEGY_NAME,
            "forced_resolution": {"max_hold_hours": 720, "tp_pct": TP_PCT * 100, "sl_pct": SL_PCT * 100, "time_exit_at_market": True},
            "paper_pilot": True,
        })

    logger.info("%s: %d picks", STRATEGY_NAME, len(picks))
    return picks
