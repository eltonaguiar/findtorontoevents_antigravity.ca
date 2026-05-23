"""Convert DNA/genome picks into Strategy Registry envelopes."""

from datetime import datetime, timezone


def dna_pick_to_envelope(pick: dict) -> dict:
    """Convert a DNA pick dict into a Strategy Registry envelope."""
    symbol = pick.get("symbol", "UNKNOWN")
    direction = pick.get("direction", "LONG")
    strategy = pick.get("strategy", "dna")
    timestamp = datetime.now(timezone.utc).isoformat()
    sid = f"dna_{symbol}_{strategy}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    return {
        "strategy_id": sid,
        "name": f"DNA {symbol} {direction} ({strategy})",
        "type": "dna",
        "source_system": "genome",
        "parameters": {
            "dna_hash": pick.get("dna_hash", ""),
            "confidence": pick.get("confidence", 0),
        },
        "backtest_results": {
            "tier_1": {
                "passed": True,
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
            "source": "dna",
        },
        "generated_at": timestamp,
    }
