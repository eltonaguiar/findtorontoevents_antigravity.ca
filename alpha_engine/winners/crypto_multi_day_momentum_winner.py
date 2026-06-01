"""CRYPTO fallback winner: ST Multi-Day Momentum (WF 62.7% WR, PF 3.84, n=75)."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

STRATEGY_NAME = "st_multi_day_momentum_winner"


def _pick_to_dict(p: Any) -> dict[str, Any]:
    return {
        "symbol": p.symbol,
        "direction": p.direction,
        "strategy": STRATEGY_NAME,
        "asset_class": "CRYPTO",
        "category": "crypto",
        "entry_price": float(p.entry_price),
        "take_profit": float(p.tp),
        "stop_loss": float(p.sl),
        "confidence": float(p.confidence),
        "reason": getattr(p, "reason", "") or "Multi-day momentum (WF validated)",
        "source": "paper_trading",
        "source_system": "st_multi_day_momentum",
        "forced_resolution": {
            "max_hold_hours": 120,
            "tp_pct": 4.0,
            "sl_pct": 2.0,
            "time_exit_at_market": True,
        },
        "paper_pilot": True,
        "extra": getattr(p, "raw_signal", {}) or {},
    }


def generate_crypto_multi_day_momentum_winner_picks() -> list[dict[str, Any]]:
    try:
        from paper_trading.strategies.walkforward_elite_strategies import STMultiDayMomentum
        raw = STMultiDayMomentum().run()
        out = [_pick_to_dict(p) for p in raw]
        logger.info("%s: %d picks", STRATEGY_NAME, len(out))
        return out
    except Exception as e:
        logger.warning("crypto multi-day momentum winner failed: %s", e)
        return []
