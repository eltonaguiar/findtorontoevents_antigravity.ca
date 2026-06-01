"""CHEAP_STOCKS winner: cross-sectional momentum $2–$12 (backtest WR 61%, PF 2.79)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

STRATEGY_NAME = "cheap_stock_cross_momentum_winner"
UNIVERSE = (
    "F", "NIO", "SNAP", "SOFI", "PLUG", "SOUN", "LCID", "RIVN", "HOOD",
    "AAL", "DAL", "UAL", "CCL", "MARA", "RIOT", "COIN", "CLSK", "BITF", "HUT",
    "WBD", "IONQ", "OPEN", "CHPT", "BLNK", "RUN", "XPEV", "LI",
)
PRICE_MIN, PRICE_MAX = 2.0, 12.0
MOM_DAYS = 63
TOP_N = 5
TP_PCT, SL_PCT = 0.12, 0.08


def generate_cheap_stock_momentum_winner_picks() -> list[dict[str, Any]]:
    try:
        import yfinance as yf
        import pandas as pd
    except ImportError:
        return []

    raw = yf.download(list(UNIVERSE), period="6mo", progress=False, auto_adjust=True)
    if raw is None or raw.empty:
        return []

    scored: list[tuple[float, str, float]] = []
    for sym in UNIVERSE:
        try:
            if isinstance(raw.columns, pd.MultiIndex):
                if sym not in raw.columns.get_level_values(1):
                    continue
                close = raw["Close", sym].dropna()
                vol = raw["Volume", sym].dropna()
            else:
                continue
            if len(close) < MOM_DAYS + 5:
                continue
            px = float(close.iloc[-1])
            if not (PRICE_MIN <= px <= PRICE_MAX):
                continue
            if len(vol) >= 20 and float(vol.tail(20).mean()) < 500_000:
                continue
            ago = float(close.iloc[-MOM_DAYS - 1])
            if ago <= 0:
                continue
            mom = (px - ago) / ago
            if mom > 0:
                scored.append((mom, sym, px))
        except Exception:
            continue

    scored.sort(key=lambda x: x[0], reverse=True)
    now = datetime.now(timezone.utc).isoformat()
    picks: list[dict[str, Any]] = []
    for rank, (mom, sym, px) in enumerate(scored[:TOP_N], 1):
        conf = min(0.72, max(0.55, 0.58 + min(0.12, mom)))
        picks.append({
            "symbol": sym,
            "direction": "LONG",
            "strategy": STRATEGY_NAME,
            "asset_class": "CHEAP_STOCKS",
            "category": "equity",
            "entry_price": round(px, 2),
            "take_profit": round(px * (1 + TP_PCT), 2),
            "stop_loss": round(px * (1 - SL_PCT), 2),
            "confidence": round(conf, 3),
            "generated_at": now,
            "reason": f"Cheap-band momentum rank #{rank}: {mom*100:+.1f}% (price ${px:.2f})",
            "source": "alpha_engine",
            "source_system": STRATEGY_NAME,
            "forced_resolution": {
                "max_hold_hours": 504,
                "tp_pct": TP_PCT * 100,
                "sl_pct": SL_PCT * 100,
                "time_exit_at_market": True,
            },
            "paper_pilot": True,
            "extra": {
                "expected_slippage_bps": 25,
                "max_reasonable_aum_usd": 75000,
                "price_band": [PRICE_MIN, PRICE_MAX],
            },
        })
    logger.info("%s: %d picks", STRATEGY_NAME, len(picks))
    return picks
