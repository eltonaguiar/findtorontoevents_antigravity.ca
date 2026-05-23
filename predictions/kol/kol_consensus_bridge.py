"""
KOL Consensus Bridge
====================
Converts consensus signals from kol_consensus_engine into standard pick
format compatible with the cross-aggregation pipeline.

Usage:
    Called by kol_consensus_engine.run() — not typically run standalone.
"""

from __future__ import annotations

import sys
import json
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Optional price fetcher (graceful degradation)
# ---------------------------------------------------------------------------

HAS_PRICE = False
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "alpha_engine"))
    from api_failover import fetch_price
    HAS_PRICE = True
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "kol_consensus_picks.json"


# ---------------------------------------------------------------------------
# Asset category detection
# ---------------------------------------------------------------------------

_FOREX_PAIRS = {
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD",
    "USDCAD", "EURGBP", "EURJPY", "GBPJPY",
}


def _detect_category(symbol: str) -> str:
    """Determine asset category from symbol name."""
    upper = symbol.upper()
    if upper.endswith("USDT") or upper.endswith("BTC") or upper.endswith("BUSD"):
        return "crypto"
    if upper in _FOREX_PAIRS or upper.endswith("USD") and len(upper) == 6:
        return "forex"
    # Default: equity (covers stocks, ETFs, indices)
    return "equity"


# ---------------------------------------------------------------------------
# Core conversion
# ---------------------------------------------------------------------------

def consensus_to_picks(consensus_signals: list[dict]) -> list[dict]:
    """
    Convert consensus signals into standard pick dicts for cross-aggregation.
    """
    picks = []
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")

    for sig in consensus_signals:
        symbol = sig["symbol"]
        direction = sig["direction"]
        strength = sig["strength"]
        confidence = sig["confidence"]
        consensus_count = sig["consensus_count"]
        kol_names = sig.get("kol_names", sig.get("kol_handles", []))
        category_diversity = sig.get("category_diversity", 1)
        avg_wr = sig.get("avg_kol_wr", 0.0)
        avg_entry = sig.get("avg_entry_price")

        # --- Entry price: live price preferred, fallback to avg from KOL predictions ---
        entry_price = None
        if HAS_PRICE:
            try:
                entry_price = fetch_price(symbol)
            except Exception:
                pass

        if not entry_price and avg_entry:
            entry_price = avg_entry

        if not entry_price:
            # Cannot create a meaningful pick without a price
            print(f"[kol_bridge] Skipping {symbol} {direction}: no price available")
            continue

        # --- TP / SL: prefer median of stated KOL targets when >=2 sources ---
        # Falls back to conservative 5% defaults only when no real data exists.
        median_tp = sig.get("median_take_profit")
        median_sl = sig.get("median_stop_loss")
        is_long = direction.upper() == "LONG"

        if median_tp and median_sl:
            # Use real KOL-stated levels (most accurate)
            tp = round(median_tp, 8)
            sl = round(median_sl, 8)
        elif median_tp:
            tp = round(median_tp, 8)
            # Derive SL from TP distance (mirror)
            tp_dist = abs(tp - entry_price)
            sl = round(entry_price - tp_dist, 8) if is_long else round(entry_price + tp_dist, 8)
        elif median_sl:
            sl = round(median_sl, 8)
            sl_dist = abs(entry_price - sl)
            tp = round(entry_price + sl_dist, 8) if is_long else round(entry_price - sl_dist, 8)
        else:
            # Default 5% when no KOL-stated levels available
            if is_long:
                tp = round(entry_price * 1.05, 8)
                sl = round(entry_price * 0.95, 8)
            else:
                tp = round(entry_price * 0.95, 8)
                sl = round(entry_price * 1.05, 8)

        # --- Risk/reward ---
        # PEER_INTEL: R:R 1.0-1.5 = 70.8% WR, R:R 2.0-3.0 = 42.4%.
        # Cap R:R at 1.5 for crypto consensus picks to stay in the sweet spot.
        sl_dist = abs(entry_price - sl)
        tp_dist = abs(tp - entry_price)
        risk_reward = round(tp_dist / sl_dist, 2) if sl_dist > 0 else 1.0
        if risk_reward > 1.5 and _detect_category(symbol) == "crypto":
            # Tighten TP to bring R:R back to 1.5
            capped_tp_dist = sl_dist * 1.5
            tp = round(entry_price + capped_tp_dist, 8) if is_long else round(entry_price - capped_tp_dist, 8)
            risk_reward = 1.5

        # PEER_INTEL: SHORT 50.3% WR vs LONG 43.6% overall.
        # Give SHORT consensus a small confidence bump.
        if not is_long:
            confidence = min(confidence + 0.03, 0.95)

        # --- Asset category ---
        asset_category = _detect_category(symbol)

        news_inferred = bool(
            sig.get("_news_consensus")
            or sig.get("consensus_signal_source") == "news_inferred"
            or (sig.get("categories") == ["news_inferred"])
        )
        signal_source = "news_inferred" if news_inferred else "kol_weighted"
        if news_inferred:
            reason = (
                f"News headline consensus: {consensus_count} articles/sources align "
                f"({strength}) — not verified individual KOL calls; weak prior"
            )
        else:
            reason = (
                f"KOL consensus: {consensus_count} KOLs from "
                f"{category_diversity} categories agree ({strength})"
            )

        pick = {
            "id": f"kol_consensus::{symbol}::{direction}::{date_str}",
            "source_system": "kol_consensus",
            "strategy": f"kol_consensus_{category_diversity}cat",
            "symbol": symbol,
            "direction": direction,
            "signal_type": direction,
            "confidence": confidence,
            "category": asset_category,
            "entry_price": entry_price,
            "take_profit": tp,
            "stop_loss": sl,
            "risk_reward": risk_reward,
            "reason": reason,
            "consensus_count": consensus_count,
            "consensus_sources": kol_names,
            "kol_category_diversity": category_diversity,
            "kol_avg_wr": avg_wr,
            "consensus_signal_source": signal_source,
            "forward_test_only": True,
            "status": "ACTIVE",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        picks.append(pick)

    return picks


# ---------------------------------------------------------------------------
# File output
# ---------------------------------------------------------------------------

def write_picks(picks: list[dict]) -> None:
    """Write picks to the standard output path as JSON."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(picks, indent=2, default=str))
    print(f"[kol_bridge] Wrote {len(picks)} picks to {OUTPUT_PATH}")


def generate_picks(consensus_signals: list[dict]) -> list[dict]:
    """
    Main entry point called from kol_consensus_engine.run().
    Converts consensus signals to picks and writes to file.
    Returns the picks list.
    """
    picks = consensus_to_picks(consensus_signals)
    write_picks(picks)
    return picks


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Quick test with synthetic data
    test_signals = [
        {
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "strength": "STRONG",
            "confidence": 0.70,
            "weighted_votes": 3.5,
            "consensus_count": 4,
            "kol_handles": ["CryptoMichNL", "woonomic", "RaoulGMI", "Pentosh1"],
            "kol_names": ["Michael van de Poppe", "Willy Woo", "Raoul Pal", "Pentoshi"],
            "categories": ["macro", "on_chain", "ta_daily"],
            "category_diversity": 3,
            "avg_kol_wr": 0.55,
            "avg_entry_price": 84000.0,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        },
    ]
    result = generate_picks(test_signals)
    for p in result:
        print(json.dumps(p, indent=2))
