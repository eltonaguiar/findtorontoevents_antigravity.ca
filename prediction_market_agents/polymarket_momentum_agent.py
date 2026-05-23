#!/usr/bin/env python3
"""
Agent 2: Polymarket Momentum Detector

Thin wrapper around alpha_engine.polymarket_signals so the agent workflow uses
the same strict crypto filtering and momentum logic as the Alpha Engine feed.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = DATA_DIR / "momentum_signals.json"


def _save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)


def _snapshot_trade_levels(symbol: str, direction: str) -> tuple[float, float, float]:
    try:
        from alpha_engine.api_failover import fetch_price
    except Exception:
        return (0.0, 0.0, 0.0)

    entry_price = fetch_price(symbol)
    if not entry_price:
        return (0.0, 0.0, 0.0)

    entry_price = round(float(entry_price), 8)
    if direction == "SHORT":
        return (
            entry_price,
            round(entry_price * 0.975, 8),
            round(entry_price * 1.015, 8),
        )
    return (
        entry_price,
        round(entry_price * 1.025, 8),
        round(entry_price * 0.985, 8),
    )


def scan_momentum() -> dict[str, Any]:
    try:
        from alpha_engine.polymarket_signals import fetch_crypto_markets, get_clob_momentum_signals
    except Exception as exc:
        logger.error("Failed to import shared Polymarket momentum logic: %s", exc)
        return {"signals": [], "error": str(exc)}

    logger.info("=" * 60)
    logger.info("  Polymarket Momentum Detector")
    logger.info("=" * 60)

    markets = fetch_crypto_markets()
    raw_signals = get_clob_momentum_signals(markets)

    signals = []
    for signal in raw_signals:
        entry_price, take_profit, stop_loss = _snapshot_trade_levels(signal["symbol"], signal["direction"])
        signals.append(
            {
                "id": f"pm_momentum_{signal['symbol']}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}",
                "symbol": signal["symbol"],
                "direction": signal["direction"],
                "confidence": signal["confidence"],
                "strategy": "pm_momentum_detector",
                "source_system": "polymarket_momentum",
                "category": "crypto",
                "signal_type": "BUY" if signal["direction"] == "LONG" else "SELL",
                "status": "OPEN" if entry_price > 0 else "SIGNAL",
                "entry_price": entry_price,
                "take_profit": take_profit,
                "stop_loss": stop_loss,
                "type_label": "🔮 PM Momentum",
                "momentum_data": {
                    "question": signal["question"],
                    "market_id": signal["market_id"],
                    "market_type": signal.get("market_type"),
                    "current_prob": signal["probability"],
                    "delta_4h": signal.get("momentum_4h"),
                    "delta_24h": signal.get("momentum_24h"),
                    "velocity": signal.get("velocity"),
                    "volume_usd": signal.get("volume"),
                },
                "reason": signal["reason"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "entry_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            }
        )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "polymarket_momentum_detector",
        "markets_analyzed": len(markets),
        "momentum_signals": len(signals),
        "signals": signals,
    }

    _save_json(OUTPUT_FILE, payload)
    logger.info("Saved %d momentum signals to %s", len(signals), OUTPUT_FILE)
    return payload


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = scan_momentum()
    print(f"\nMomentum Detector Complete:")
    print(f"  Markets analyzed: {result.get('markets_analyzed', 0)}")
    print(f"  Momentum signals: {result.get('momentum_signals', 0)}")
    for sig in result.get("signals", [])[:10]:
        md = sig.get("momentum_data", {})
        print(f"  {sig.get('direction','?'):5s} {sig.get('symbol','?'):12s} Δ4h={md.get('delta_4h', 0):+.2%}")
