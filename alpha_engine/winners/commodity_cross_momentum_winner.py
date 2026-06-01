"""COMMODITY fallback when planting/harvest window is off (Szymanowska JFE 2014)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

STRATEGY_NAME = "commodity_cross_momentum_winner"

COMMODITY_UNIVERSE: dict[str, dict[str, str]] = {
    "GC=F": {"name": "Gold"},
    "SI=F": {"name": "Silver"},
    "CL=F": {"name": "WTI Crude Oil"},
    "NG=F": {"name": "Natural Gas"},
    "HG=F": {"name": "Copper"},
    "ZC=F": {"name": "Corn"},
}
MOMENTUM_WINDOW = 21
TOP_N = 2
BOTTOM_N = 2
TP_PCT = 3.0
SL_PCT = 2.0
MAX_HOLD_HOURS = 168


def _fetch_momentum(symbol: str) -> Optional[dict[str, float]]:
    try:
        import yfinance as yf
        df = yf.download(symbol, period="3mo", interval="1d", auto_adjust=True, progress=False)
        if df is None or df.empty:
            return None
        if hasattr(df.columns, "get_level_values"):
            try:
                df.columns = df.columns.get_level_values(0)
            except Exception:
                pass
        close = df["Close"].dropna().astype(float)
        if len(close) < MOMENTUM_WINDOW + 5:
            return None
        last_close = float(close.iloc[-1])
        lookback_close = float(close.iloc[-MOMENTUM_WINDOW])
        if lookback_close <= 0:
            return None
        return {
            "last_close": last_close,
            "momentum": (last_close - lookback_close) / lookback_close,
        }
    except Exception as e:
        logger.warning("momentum fetch %s: %s", symbol, e)
        return None


def generate_commodity_cross_momentum_winner_picks(
    now: Optional[datetime] = None,
) -> list[dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    now_iso = now.isoformat()
    rankings: list[dict[str, Any]] = []

    for symbol, meta in COMMODITY_UNIVERSE.items():
        data = _fetch_momentum(symbol)
        if data is None:
            continue
        rankings.append({
            "symbol": symbol,
            "name": meta["name"],
            "momentum": data["momentum"],
            "last_close": data["last_close"],
        })

    if len(rankings) < TOP_N + BOTTOM_N:
        logger.info("%s: insufficient rankings (%d)", STRATEGY_NAME, len(rankings))
        return []

    rankings.sort(key=lambda x: x["momentum"], reverse=True)
    picks: list[dict[str, Any]] = []

    for rank, row in enumerate(rankings[:TOP_N], 1):
        px = float(row["last_close"])
        picks.append({
            "symbol": row["symbol"],
            "direction": "LONG",
            "strategy": STRATEGY_NAME,
            "asset_class": "COMMODITY",
            "category": "commodity",
            "entry_price": round(px, 4),
            "take_profit": round(px * (1 + TP_PCT / 100), 4),
            "stop_loss": round(px * (1 - SL_PCT / 100), 4),
            "confidence": round(min(0.72, 0.58 + 0.04 * rank), 3),
            "generated_at": now_iso,
            "reason": f"Cross-commodity momentum LONG #{rank} (1m {row['momentum']*100:+.1f}%)",
            "source": "alpha_engine",
            "source_system": STRATEGY_NAME,
            "forced_resolution": {
                "max_hold_hours": MAX_HOLD_HOURS,
                "tp_pct": TP_PCT,
                "sl_pct": SL_PCT,
                "time_exit_at_market": True,
            },
            "paper_pilot": True,
        })

    for rank, row in enumerate(rankings[-BOTTOM_N:], 1):
        px = float(row["last_close"])
        picks.append({
            "symbol": row["symbol"],
            "direction": "SHORT",
            "strategy": STRATEGY_NAME,
            "asset_class": "COMMODITY",
            "category": "commodity",
            "entry_price": round(px, 4),
            "take_profit": round(px * (1 - TP_PCT / 100), 4),
            "stop_loss": round(px * (1 + SL_PCT / 100), 4),
            "confidence": round(min(0.70, 0.56 + 0.04 * rank), 3),
            "generated_at": now_iso,
            "reason": f"Cross-commodity momentum SHORT #{rank} (1m {row['momentum']*100:+.1f}%)",
            "source": "alpha_engine",
            "source_system": STRATEGY_NAME,
            "forced_resolution": {
                "max_hold_hours": MAX_HOLD_HOURS,
                "tp_pct": TP_PCT,
                "sl_pct": SL_PCT,
                "time_exit_at_market": True,
            },
            "paper_pilot": True,
        })

    logger.info("%s: %d picks", STRATEGY_NAME, len(picks))
    return picks
