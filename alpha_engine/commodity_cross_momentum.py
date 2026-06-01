"""Cross-Commodity Momentum Strategy
=====================================
Academic citation: Szymanowska et al. (JFE 2014)
"An Anatomy of Commodity Futures Returns"

Logic:
  Rank all 6 commodities by 1-month momentum. Long top-2, short bottom-2.
  Rebalance weekly. Captures cross-sectional momentum premium documented
  in commodity futures.

Entry:
  Top-2 by 1m return → LONG, Bottom-2 → SHORT

Exit:
  When falls out of top/bottom-3  OR  max hold 168h (7 days)

Universe: GC=F, SI=F, CL=F, NG=F, HG=F, ZC=F

DEFAULT-OFF. Set env COMMODITY_CROSS_MOMENTUM_ENABLED=1 to emit picks.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)

STRATEGY_NAME = "commodity_cross_momentum"
ACADEMIC_CITATION = "Szymanowska-et-al (JFE 2014)"

COMMODITY_UNIVERSE: dict[str, dict[str, str]] = {
    "GC=F": {"name": "Gold", "sector": "precious_metals"},
    "SI=F": {"name": "Silver", "sector": "precious_metals"},
    "CL=F": {"name": "WTI Crude Oil", "sector": "energy"},
    "NG=F": {"name": "Natural Gas", "sector": "energy"},
    "HG=F": {"name": "Copper", "sector": "industrial_metals"},
    "ZC=F": {"name": "Corn", "sector": "agriculture"},
}

FETCH_PERIOD = "3mo"
MOMENTUM_WINDOW = 21
TOP_N = 2
BOTTOM_N = 2
TP_PCT = 3.0
SL_PCT = 2.0
MAX_HOLD_HOURS = 168


def _enabled() -> bool:
    return os.environ.get("COMMODITY_CROSS_MOMENTUM_ENABLED", "0") == "1"


def _is_rebalance_day(now: Optional[datetime] = None) -> bool:
    """Rebalance weekly — trigger on Monday (day 0) or if last rebalance > 5 days."""
    now = now or datetime.now(timezone.utc)
    return now.weekday() == 0


def _fetch_momentum(symbol: str) -> Optional[dict[str, float]]:
    """Fetch latest close and 1-month momentum for *symbol* via yfinance."""
    try:
        import yfinance as yf
        df = yf.download(symbol, period=FETCH_PERIOD, interval="1d",
                         auto_adjust=True, progress=False)
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
        momentum = (last_close - lookback_close) / lookback_close

        if lookback_close <= 0:
            return None

        return {
            "last_close": last_close,
            "lookback_close": lookback_close,
            "momentum": momentum,
        }
    except Exception as e:
        logger.warning("Data fetch failed for %s: %s", symbol, e)
        return None


def generate_picks(now: Optional[datetime] = None) -> list[dict[str, Any]]:
    """Generate cross-commodity momentum picks."""
    if not _enabled():
        logger.info("commodity_cross_momentum disabled (set COMMODITY_CROSS_MOMENTUM_ENABLED=1)")
        return []

    now = now or datetime.now(timezone.utc)
    if not _is_rebalance_day(now):
        logger.info("Not a rebalance day (weekday=%d) — no picks", now.weekday())
        return []

    now_iso = now.isoformat()
    rankings: list[dict[str, Any]] = []

    for symbol, meta in COMMODITY_UNIVERSE.items():
        data = _fetch_momentum(symbol)
        if data is None:
            logger.warning("Skipping %s — no data", symbol)
            continue
        rankings.append({
            "symbol": symbol,
            "name": meta["name"],
            "sector": meta["sector"],
            "momentum": data["momentum"],
            "last_close": data["last_close"],
        })

    if len(rankings) < 4:
        logger.warning("Only %d commodities with data — need at least 4", len(rankings))
        return []

    rankings.sort(key=lambda x: x["momentum"], reverse=True)

    logger.info("Cross-Momentum rankings (highest → lowest 1m return):")
    for i, r in enumerate(rankings):
        logger.info("  %d. %s  mom=%+.4f  price=%.2f",
                     i + 1, r["symbol"], r["momentum"], r["last_close"])

    top = rankings[:TOP_N]
    bottom = rankings[-BOTTOM_N:]

    picks: list[dict[str, Any]] = []

    for r in top:
        confidence = round(min(0.76, 0.55 + abs(r["momentum"]) * 2), 4)
        picks.append({
            "symbol": r["symbol"],
            "direction": "LONG",
            "strategy": STRATEGY_NAME,
            "asset_class": "COMMODITY",
            "category": "commodity",
            "confidence": confidence,
            "generated_at": now_iso,
            "timestamp": now_iso,
            "reason": (
                f"Cross-Momentum LONG: {r['name']} ranked top-{TOP_N} by "
                f"1m momentum ({r['momentum']*100:+.2f}%). "
                f"Szymanowska et al. cross-sectional momentum premium."
            ),
            "source": "alpha_engine",
            "source_system": STRATEGY_NAME,
            "forced_resolution": {
                "max_hold_hours": MAX_HOLD_HOURS,
                "tp_pct": TP_PCT,
                "sl_pct": SL_PCT,
                "time_exit_at_market": True,
            },
            "paper_pilot": True,
            "academic_citation": ACADEMIC_CITATION,
            "extra": {
                "momentum_1m": round(r["momentum"], 6),
                "last_close": round(r["last_close"], 4),
                "rank": rankings.index(r) + 1,
                "universe_size": len(rankings),
                "rebalance": "weekly",
                "exit_condition": "falls_out_of_top3_or_max_hold",
                "tp_pct": TP_PCT,
                "sl_pct": SL_PCT,
            },
        })

    for r in bottom:
        confidence = round(min(0.72, 0.55 + abs(r["momentum"]) * 2), 4)
        picks.append({
            "symbol": r["symbol"],
            "direction": "SHORT",
            "strategy": STRATEGY_NAME,
            "asset_class": "COMMODITY",
            "category": "commodity",
            "confidence": confidence,
            "generated_at": now_iso,
            "timestamp": now_iso,
            "reason": (
                f"Cross-Momentum SHORT: {r['name']} ranked bottom-{BOTTOM_N} by "
                f"1m momentum ({r['momentum']*100:+.2f}%). "
                f"Szymanowska et al. cross-sectional momentum reversal."
            ),
            "source": "alpha_engine",
            "source_system": STRATEGY_NAME,
            "forced_resolution": {
                "max_hold_hours": MAX_HOLD_HOURS,
                "tp_pct": TP_PCT,
                "sl_pct": SL_PCT,
                "time_exit_at_market": True,
            },
            "paper_pilot": True,
            "academic_citation": ACADEMIC_CITATION,
            "extra": {
                "momentum_1m": round(r["momentum"], 6),
                "last_close": round(r["last_close"], 4),
                "rank": rankings.index(r) + 1,
                "universe_size": len(rankings),
                "rebalance": "weekly",
                "exit_condition": "falls_out_of_bottom3_or_max_hold",
                "tp_pct": TP_PCT,
                "sl_pct": SL_PCT,
            },
        })

    logger.info("Cross-Momentum: %d commodities ranked, %d picks generated "
                "(%d LONG, %d SHORT)", len(rankings), len(picks), len(top), len(bottom))
    return picks


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("Running Cross-Commodity Momentum strategy (standalone)...")
    picks = generate_picks()
    if picks:
        print(json.dumps(picks, indent=2))
    else:
        logger.info("No picks generated (disabled, not rebalance day, or data failure)")
        print("[]")
