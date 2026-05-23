#!/usr/bin/env python3
"""
Agent 4: Cross-Market Consensus Engine
========================================
Aggregates signals from all prediction market agents (Polymarket whales,
Polymarket momentum, Kalshi) plus existing prediction scrapers (Polymarket
consensus, Limitless) into a single weighted consensus.

When multiple independent prediction markets agree on a direction for a
crypto asset, that's a high-conviction signal.

Output: prediction_market_agents/data/consensus_signals.json
Integration: Merges into alpha_engine/data/active_picks.json
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = DATA_DIR / "consensus_signals.json"

# Data source paths
WHALE_SIGNALS = DATA_DIR / "whale_signals.json"
MOMENTUM_SIGNALS = DATA_DIR / "momentum_signals.json"
KALSHI_SIGNALS = DATA_DIR / "kalshi_signals.json"

# External prediction sources (from existing scrapers)
ALPHA_DATA = Path(__file__).parent.parent / "alpha_engine" / "data"
POLYMARKET_ALPHA = ALPHA_DATA / "polymarket_signals.json"

PREDICTIONS_DB = Path(__file__).parent.parent / "predictions" / "data"

# Source weights for consensus scoring
SOURCE_WEIGHTS = {
    "polymarket_whale_tracker": 0.30,    # Highest: proven profitable traders
    "polymarket_momentum": 0.20,          # Leading indicator
    "kalshi_signal_agent": 0.20,          # Regulated market, institutional money
    "polymarket_prediction": 0.15,        # Polymarket market probabilities
    "polymarket_consensus": 0.10,         # Polymarket scraper consensus
    "limitless": 0.05,                    # Lower liquidity
}

# Minimum consensus requirements
MIN_SOURCES_FOR_SIGNAL = 1    # Lowered from 2: only 1 PM source currently, was blocking ALL signals
MIN_WEIGHTED_SCORE = 0.15     # Minimum weighted consensus score
HIGH_CONVICTION_SCORE = 0.40  # 3+ sources strongly agree


def _load_json(path: Path) -> Optional[Any]:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.debug("Error loading %s: %s", path, e)
        return None


def _extract_signals(data: Any, source: str) -> List[Dict]:
    """Extract normalized signal dicts from various data formats."""
    signals = []

    if not data:
        return signals

    # Handle different formats
    raw = []
    if isinstance(data, list):
        raw = data
    elif isinstance(data, dict):
        raw = data.get("signals", data.get("picks", []))
        if isinstance(raw, dict):
            # Polymarket PMXT format: signals keyed by symbol
            for sym, sig_data in raw.items():
                if isinstance(sig_data, dict):
                    direction = sig_data.get("direction", "neutral")
                    if direction == "bullish":
                        direction = "LONG"
                    elif direction == "bearish":
                        direction = "SHORT"
                    else:
                        continue
                    raw.append({
                        "symbol": sig_data.get("symbol", sym) + "USDT" if not sig_data.get("symbol", sym).endswith("USDT") else sig_data.get("symbol", sym),
                        "direction": direction,
                        "confidence": abs(sig_data.get("confidence_boost", 0)) * 10 + 0.50,
                        "source_system": source,
                    })
            raw = [x for x in raw if isinstance(x, dict) and x.get("symbol")]

    for item in raw:
        if not isinstance(item, dict):
            continue

        symbol = str(item.get("symbol", "")).upper()
        if not symbol or not symbol.endswith("USDT"):
            continue

        direction = str(item.get("direction", item.get("signal_type", ""))).upper()
        if direction in ("BUY", "LONG"):
            direction = "LONG"
        elif direction in ("SELL", "SHORT"):
            direction = "SHORT"
        else:
            continue

        confidence = float(item.get("confidence", 0.5) or 0.5)
        if confidence > 1.0:
            confidence = confidence / 100.0

        signals.append({
            "symbol": symbol,
            "direction": direction,
            "confidence": confidence,
            "source": item.get("source_system", source),
            "strategy": item.get("strategy", source),
            "reason": item.get("reason", ""),
            "extra": item,
            # Audit metadata for dashboard display
            "history_wr_bayes": item.get("history_wr_bayes") or item.get("profile_crypto_wr_bayes"),
            "history_trades": item.get("history_trades"),
            "history_wr": item.get("history_wr"),
            "forward_wr": item.get("forward_wr"),
            "forward_trades": item.get("forward_trades"),
            "trader_label": item.get("trader_label") or item.get("trader_name"),
            "type_label": item.get("type_label"),
        })

    return signals


def build_consensus() -> Dict[str, Any]:
    """
    Build cross-market consensus from all available signal sources.

    For each symbol, check how many independent sources agree on direction.
    Weight each source by its reliability track record.
    """
    logger.info("=" * 60)
    logger.info("  Cross-Market Consensus Engine — Aggregating signals")
    logger.info("=" * 60)

    now = datetime.now(timezone.utc)

    # Load all signal sources
    sources = {
        "polymarket_whale_tracker": _extract_signals(_load_json(WHALE_SIGNALS), "polymarket_whale_tracker"),
        "polymarket_momentum": _extract_signals(
            _load_json(MOMENTUM_SIGNALS).get("signals", []) if _load_json(MOMENTUM_SIGNALS) else [],
            "polymarket_momentum"
        ),
        "kalshi_signal_agent": _extract_signals(
            _load_json(KALSHI_SIGNALS).get("signals", []) if _load_json(KALSHI_SIGNALS) else [],
            "kalshi_signal_agent"
        ),
        "polymarket_prediction": _extract_signals(_load_json(POLYMARKET_ALPHA), "polymarket_prediction"),
    }

    total_signals = sum(len(v) for v in sources.values())
    logger.info("Signal sources loaded:")
    for name, sigs in sources.items():
        if sigs:
            logger.info("  %s: %d signals", name, len(sigs))

    if total_signals == 0:
        logger.warning("No signals from any source")
        return {"signals": [], "consensus": {}}

    # Group all signals by symbol
    by_symbol: Dict[str, Dict[str, List]] = {}
    for source_name, sigs in sources.items():
        for sig in sigs:
            sym = sig["symbol"]
            if sym not in by_symbol:
                by_symbol[sym] = {"LONG": [], "SHORT": []}
            by_symbol[sym][sig["direction"]].append({
                "source": source_name,
                "confidence": sig["confidence"],
                "strategy": sig["strategy"],
                "reason": sig["reason"],
                # Pass through audit metadata for aggregation
                "history_wr_bayes": sig.get("history_wr_bayes"),
                "history_trades": sig.get("history_trades"),
                "forward_wr": sig.get("forward_wr"),
                "forward_trades": sig.get("forward_trades"),
                "trader_label": sig.get("trader_label"),
                "type_label": sig.get("type_label"),
            })

    # Build consensus for each symbol
    consensus = {}
    output_signals = []

    for sym, directions in by_symbol.items():
        long_signals = directions["LONG"]
        short_signals = directions["SHORT"]

        # Calculate weighted scores
        long_score = 0
        short_score = 0
        long_sources = set()
        short_sources = set()

        for sig in long_signals:
            weight = SOURCE_WEIGHTS.get(sig["source"], 0.05)
            long_score += weight * sig["confidence"]
            long_sources.add(sig["source"])

        for sig in short_signals:
            weight = SOURCE_WEIGHTS.get(sig["source"], 0.05)
            short_score += weight * sig["confidence"]
            short_sources.add(sig["source"])

        # Determine consensus direction
        if long_score > short_score and long_score >= MIN_WEIGHTED_SCORE:
            direction = "LONG"
            consensus_score = long_score
            num_sources = len(long_sources)
            source_list = list(long_sources)
            contributing = long_signals
        elif short_score > long_score and short_score >= MIN_WEIGHTED_SCORE:
            direction = "SHORT"
            consensus_score = short_score
            num_sources = len(short_sources)
            source_list = list(short_sources)
            contributing = short_signals
        else:
            # No consensus or scores too low
            consensus[sym] = {
                "direction": "NEUTRAL",
                "score": 0,
                "sources": 0,
            }
            continue

        # Require minimum number of agreeing sources
        if num_sources < MIN_SOURCES_FOR_SIGNAL:
            consensus[sym] = {
                "direction": direction,
                "score": round(consensus_score, 4),
                "sources": num_sources,
                "blocked_reason": f"only {num_sources} source(s), need {MIN_SOURCES_FOR_SIGNAL}",
            }
            continue

        # Calculate final confidence
        # Base confidence from weighted score (0.15-1.0 range → 0.60-0.95)
        conf = min(0.95, 0.55 + consensus_score * 0.80)

        # Boost for high conviction (many sources agreeing)
        if num_sources >= 4:
            conf = min(0.95, conf + 0.10)
        elif num_sources >= 3:
            conf = min(0.95, conf + 0.05)

        # Build reason string
        source_reasons = []
        for sig in contributing[:5]:
            reason_short = sig["reason"][:50] if sig["reason"] else sig["source"]
            source_reasons.append(f"{sig['source']}: {reason_short}")

        is_high_conviction = consensus_score >= HIGH_CONVICTION_SCORE or num_sources >= 3

        # Aggregate audit metadata from contributing signals
        def _aggregate_audit_metadata(signals):
            """Weighted average of win rates from contributing signals."""
            history_sum, history_weight = 0.0, 0.0
            forward_sum, forward_weight = 0.0, 0.0
            history_max_trades, forward_max_trades = 0, 0
            trader_labels, type_labels = set(), set()
            
            for sig in signals:
                wr = sig.get("history_wr_bayes")
                trades = sig.get("history_trades") or 0
                if wr and trades > 0:
                    weight = max(1, trades)
                    history_sum += wr * weight
                    history_weight += weight
                    history_max_trades = max(history_max_trades, trades)
                
                fwd_wr = sig.get("forward_wr")
                fwd_trades = sig.get("forward_trades") or 0
                if fwd_wr and fwd_trades > 0:
                    weight = max(1, fwd_trades)
                    forward_sum += fwd_wr * weight
                    forward_weight += weight
                    forward_max_trades = max(forward_max_trades, fwd_trades)
                
                if sig.get("trader_label"):
                    trader_labels.add(sig["trader_label"])
                if sig.get("type_label"):
                    type_labels.add(sig["type_label"])
            
            return {
                "history_wr_bayes": round(history_sum / history_weight, 4) if history_weight > 0 else None,
                "history_trades": history_max_trades if history_max_trades > 0 else None,
                "forward_wr": round(forward_sum / forward_weight, 4) if forward_weight > 0 else None,
                "forward_trades": forward_max_trades if forward_max_trades > 0 else None,
                "trader_label": ", ".join(sorted(trader_labels))[:60] if trader_labels else None,
                "type_label": "🔮 PM Consensus" if type_labels else None,
            }
        
        audit_meta = _aggregate_audit_metadata(contributing)

        consensus[sym] = {
            "direction": direction,
            "score": round(consensus_score, 4),
            "sources": num_sources,
            "source_list": source_list,
            "high_conviction": is_high_conviction,
        }

        signal = {
            "id": f"pm_consensus_{sym}_{now.strftime('%Y%m%d%H%M')}",
            "symbol": sym,
            "direction": direction,
            "confidence": round(conf, 3),
            "strategy": "prediction_market_consensus",
            "source_system": "prediction_market_agents",
            "category": "crypto",
            "signal_type": "BUY" if direction == "LONG" else "SELL",
            "status": "OPEN",
            "entry_price": 0,   # Filled by price enricher
            "take_profit": 0,   # Filled by tp_sl_filler
            "stop_loss": 0,     # Filled by tp_sl_filler
            "consensus_data": {
                "score": round(consensus_score, 4),
                "num_sources": num_sources,
                "sources": source_list,
                "high_conviction": is_high_conviction,
                "long_score": round(long_score, 4),
                "short_score": round(short_score, 4),
            },
            "reason": (
                f"Prediction market consensus: {num_sources} sources agree {direction} {sym} "
                f"(score: {consensus_score:.2f}, "
                f"{'HIGH CONVICTION' if is_high_conviction else 'moderate'}). "
                f"Sources: {', '.join(source_list)}"
            ),
            "timestamp": now.isoformat(),
            "entry_date": now.strftime("%Y-%m-%d"),
            # Audit metadata for dashboard WR display
            "history_wr_bayes": audit_meta.get("history_wr_bayes"),
            "history_trades": audit_meta.get("history_trades"),
            "forward_wr": audit_meta.get("forward_wr"),
            "forward_trades": audit_meta.get("forward_trades"),
            "trader_label": audit_meta.get("trader_label"),
            "type_label": audit_meta.get("type_label"),
        }

        output_signals.append(signal)
        logger.info(
            "  CONSENSUS: %s %s — %d sources, score=%.2f, conf=%.0f%% %s",
            direction, sym, num_sources, consensus_score, conf * 100,
            "★ HIGH CONVICTION" if is_high_conviction else "",
        )

    # Sort by consensus score descending
    output_signals.sort(key=lambda x: x.get("consensus_data", {}).get("score", 0), reverse=True)

    result = {
        "generated_at": now.isoformat(),
        "source": "cross_market_consensus",
        "total_signals_aggregated": total_signals,
        "symbols_analyzed": len(by_symbol),
        "consensus_signals": len(output_signals),
        "high_conviction_count": sum(1 for s in output_signals if s.get("consensus_data", {}).get("high_conviction")),
        "consensus": consensus,
        "signals": output_signals,
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    logger.info("Consensus: %d signals (%d high conviction)", len(output_signals),
                result["high_conviction_count"])

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = build_consensus()
    print(f"\nCross-Market Consensus Complete:")
    print(f"  Signals aggregated: {result.get('total_signals_aggregated', 0)}")
    print(f"  Consensus signals: {result.get('consensus_signals', 0)}")
    print(f"  High conviction: {result.get('high_conviction_count', 0)}")
    for sig in result.get("signals", []):
        cd = sig.get("consensus_data", {})
        print(f"  {sig['direction']:5s} {sig['symbol']:12s} conf={sig['confidence']:.2f} "
              f"sources={cd.get('num_sources', 0)} score={cd.get('score', 0):.2f}")
