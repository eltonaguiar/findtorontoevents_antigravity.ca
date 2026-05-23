"""Convert cross-aggregation consensus picks into Strategy Registry envelopes."""

from datetime import datetime, timezone


def consensus_pick_to_envelope(pick: dict) -> dict:
    """Convert a consensus pick dict into a Strategy Registry envelope."""
    symbol = pick.get("symbol", "UNKNOWN")
    direction = pick.get("direction", "LONG")
    strategy = pick.get("strategy", "consensus")
    timestamp = datetime.now(timezone.utc).isoformat()
    sid = f"consensus_{symbol}_{direction}_{strategy}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    return {
        "strategy_id": sid,
        "name": f"Consensus {symbol} {direction} ({strategy})",
        "type": "consensus",
        "source_system": "cross_aggregation",
        "parameters": {
            "confidence": pick.get("confidence", 0),
            "agreement_count": pick.get("agreement_count", 0),
            "source_systems": pick.get("source_systems", []),
        },
        "backtest_results": {
            "tier_1": {
                "passed": pick.get("agreement_count", 0) >= 2,
                "win_rate": pick.get("confidence", 0) * 100,
                "pair": symbol,
                "direction": direction,
                "entry_price": pick.get("entry_price"),
                "take_profit": pick.get("take_profit"),
                "stop_loss": pick.get("stop_loss"),
            },
        },
        "tags": {
            "symbol_scope": "single_symbol",
            "direction_bias": "long_only" if direction == "LONG" else "short_only",
            "source": "consensus",
            "agreement": str(pick.get("agreement_count", 0)),
        },
        "generated_at": timestamp,
    }
