"""CRYPTO fallback: funding-rate carry (Binance live API, no placeholder prices)."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

STRATEGY_NAME = "crypto_funding_carry_winner"


def generate_crypto_funding_carry_winner_picks() -> list[dict[str, Any]]:
    try:
        from alpha_engine.funding_rate_arb import scan_funding_rate_arb
        raw = scan_funding_rate_arb(verbose=False)
    except Exception as e:
        logger.warning("funding carry failed: %s", e)
        return []

    out: list[dict[str, Any]] = []
    for p in raw[:5]:
        entry = float(p.get("entry_price") or 0)
        if entry <= 0:
            continue
        out.append({
            "symbol": p["symbol"],
            "direction": p.get("direction", "LONG"),
            "strategy": STRATEGY_NAME,
            "asset_class": "CRYPTO",
            "category": "crypto",
            "entry_price": entry,
            "take_profit": float(p.get("take_profit") or entry * 1.02),
            "stop_loss": float(p.get("stop_loss") or entry * 0.985),
            "confidence": float(p.get("confidence") or 0.6),
            "reason": p.get("reason", "Funding rate extreme (live Binance)"),
            "source": "alpha_engine",
            "source_system": "funding_rate_arb",
            "forced_resolution": {
                "max_hold_hours": 48,
                "tp_pct": 2.0,
                "sl_pct": 1.5,
                "time_exit_at_market": True,
            },
            "paper_pilot": True,
            "extra": {
                "funding_rate_8h": p.get("funding_rate_8h"),
                "funding_rate_annualized": p.get("funding_rate_annualized"),
            },
        })
    logger.info("%s: %d picks", STRATEGY_NAME, len(out))
    return out
