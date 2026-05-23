#!/usr/bin/env python3
"""
Agent 5: Prediction Market Orchestrator
=========================================
Runs all prediction market agents in sequence, then merges the consensus
signals into alpha_engine/data/active_picks.json so they flow through
to the audit dashboard at findtorontoevents.ca/audit.

Pipeline:
  1. polymarket_whale_tracker   → whale copy signals
  2. polymarket_momentum_agent  → momentum leading indicators
  3. kalshi_signal_agent        → multi-timeframe consensus
  4. cross_market_consensus     → aggregated consensus
  5. MERGE → alpha_engine/data/active_picks.json

The merged picks include:
  - source_system: "prediction_market_agents"
  - strategy: "prediction_market_consensus"
  - entry_price/tp/sl: filled downstream by universal_price_enricher + tp_sl_filler
"""

import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PM_DATA_DIR = Path(__file__).parent / "data"
ALPHA_DATA_DIR = Path(__file__).parent.parent / "alpha_engine" / "data"
ACTIVE_PICKS_PATH = ALPHA_DATA_DIR / "active_picks.json"

# Maximum age in hours for prediction market signals
MAX_SIGNAL_AGE_HOURS = 12

# Minimum confidence for prediction-market picks that are allowed onto the dashboard
MIN_MERGE_CONFIDENCE = 0.60  # Lowered from 0.80: PM signals were all blocked
MERGEABLE_STRATEGIES = {"prediction_market_consensus"}


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_json(path: Path, data: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def _is_prediction_market_pick(pick: Dict[str, Any]) -> bool:
    source_system = str(pick.get("source_system", "")).lower()
    source = str(pick.get("source", "")).lower()
    strategy = str(pick.get("strategy", "")).lower()
    return any(
        token in value
        for token in ("prediction_market", "polymarket", "kalshi")
        for value in (source_system, source, strategy)
    )


def _is_mergeable_dashboard_signal(pick: Dict[str, Any]) -> bool:
    strategy = str(pick.get("strategy", "")).strip()
    confidence = float(pick.get("confidence", 0) or 0)
    return strategy in MERGEABLE_STRATEGIES and confidence >= MIN_MERGE_CONFIDENCE


# ---------------------------------------------------------------------------
# Run individual agents
# ---------------------------------------------------------------------------

def run_whale_tracker() -> Dict[str, Any]:
    """Run the Polymarket whale tracker agent."""
    try:
        from prediction_market_agents.polymarket_whale_tracker import scan_whales
        return scan_whales(top_n=15)
    except Exception as e:
        logger.error("Whale tracker failed: %s", e)
        traceback.print_exc()
        return {"signals": [], "error": str(e)}


def run_momentum_detector() -> Dict[str, Any]:
    """Run the Polymarket momentum detector agent."""
    try:
        from prediction_market_agents.polymarket_momentum_agent import scan_momentum
        return scan_momentum()
    except Exception as e:
        logger.error("Momentum detector failed: %s", e)
        traceback.print_exc()
        return {"signals": [], "error": str(e)}


def run_kalshi_agent() -> Dict[str, Any]:
    """Run the Kalshi multi-timeframe agent."""
    try:
        from prediction_market_agents.kalshi_signal_agent import scan_kalshi
        return scan_kalshi()
    except Exception as e:
        logger.error("Kalshi agent failed: %s", e)
        traceback.print_exc()
        return {"signals": [], "error": str(e)}


def run_consensus() -> Dict[str, Any]:
    """Run the cross-market consensus engine."""
    try:
        from prediction_market_agents.cross_market_consensus import build_consensus
        result = build_consensus()
        _save_json(PM_DATA_DIR / "consensus_signals.json", result)
        return result
    except Exception as e:
        logger.error("Consensus engine failed: %s", e)
        traceback.print_exc()
        return {"signals": [], "error": str(e)}


# ---------------------------------------------------------------------------
# Merge into alpha_engine pipeline
# ---------------------------------------------------------------------------

def merge_into_active_picks(signals: List[Dict]) -> int:
    """
    Merge prediction market signals into alpha_engine/data/active_picks.json.

    This is the critical integration point — once a pick is in active_picks.json,
    the downstream pipeline handles:
      - universal_price_enricher.py → fills entry_price from Binance
      - tp_sl_filler.py → sets take_profit and stop_loss
      - smart_picks_engine.py → scores and ranks for the dashboard
      - audit dashboard → displays on findtorontoevents.ca/audit
    """
    # Load existing active picks
    active_data = _load_json(ACTIVE_PICKS_PATH)
    if active_data is None:
        active_picks = []
    elif isinstance(active_data, list):
        active_picks = active_data
    else:
        active_picks = active_data.get("picks", [])

    # Keep raw prediction-market outputs for research, but only let the
    # highest-conviction consensus layer feed the dashboard pipeline.
    filtered_active_picks = []
    removed_raw = 0
    for pick in active_picks:
        if _is_prediction_market_pick(pick) and not _is_mergeable_dashboard_signal(pick):
            removed_raw += 1
            continue
        filtered_active_picks.append(pick)
    active_picks = filtered_active_picks

    # Build set of existing keys to avoid duplicates
    def _normalize_direction(value: str) -> str:
        value = str(value).upper()
        if value in ("BUY", "LONG"):
            return "LONG"
        if value in ("SELL", "SHORT"):
            return "SHORT"
        return value

    def _rebuild_existing_keys() -> set[str]:
        keys: set[str] = set()
        for pick in active_picks:
            sym = str(pick.get("symbol", "")).upper()
            direction = _normalize_direction(pick.get("direction", pick.get("signal_type", "")))
            source = str(pick.get("source_system", "")).lower()
            if sym and direction:
                keys.add(f"{sym}_{direction}_{source}")
                if "prediction_market" in source or "polymarket" in source or "kalshi" in source:
                    keys.add(f"{sym}_{direction}_pm")
        return keys

    existing_keys = _rebuild_existing_keys()

    now = datetime.now(timezone.utc)
    merged = 0
    skipped_conf = 0
    skipped_dup = 0
    skipped_conflict = 0
    removed_conflicts = 0

    for signal in signals:
        # Filter by confidence
        conf = float(signal.get("confidence", 0) or 0)
        if conf < MIN_MERGE_CONFIDENCE:
            skipped_conf += 1
            continue

        sym = str(signal.get("symbol", "")).upper()
        direction = _normalize_direction(signal.get("direction", ""))
        source = str(signal.get("source_system", "")).lower()

        conflicting_indices = []
        conflicting_confidences = []
        for idx, pick in enumerate(active_picks):
            if not _is_prediction_market_pick(pick):
                continue
            existing_sym = str(pick.get("symbol", "")).upper()
            existing_direction = _normalize_direction(pick.get("direction", pick.get("signal_type", "")))
            if existing_sym == sym and existing_direction and existing_direction != direction:
                conflicting_indices.append(idx)
                conflicting_confidences.append(float(pick.get("confidence", 0) or 0))

        if conflicting_confidences and max(conflicting_confidences) >= conf:
            skipped_conflict += 1
            continue
        if conflicting_indices:
            for idx in reversed(conflicting_indices):
                del active_picks[idx]
                removed_conflicts += 1
            existing_keys = _rebuild_existing_keys()

        # Check for duplicates
        key_with_source = f"{sym}_{direction}_{source}"
        key_pm = f"{sym}_{direction}_pm"

        if key_with_source in existing_keys or key_pm in existing_keys:
            skipped_dup += 1
            continue

        # Enrich with live price if entry_price is missing
        entry_price = float(signal.get("entry_price", 0) or 0)
        if entry_price <= 0:
            try:
                api_failover_path = Path(__file__).parent.parent / "alpha_engine" / "api_failover.py"
                if api_failover_path.exists():
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("api_failover", api_failover_path)
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    entry_price = mod.fetch_price(sym) or 0
            except Exception as e:
                logger.warning("[MERGE] Could not fetch price for %s: %s", sym, e)

        # Hard gate: never merge a pick with zero entry price
        if entry_price <= 0:
            logger.warning("[MERGE] BLOCKED %s %s: entry_price=0 after price fetch — cannot trade without entry", sym, direction)
            skipped_conf += 1
            continue

        tp_price = float(signal.get("take_profit", 0) or 0)
        sl_price = float(signal.get("stop_loss", 0) or 0)
        if entry_price > 0 and tp_price <= 0:
            if direction == "LONG":
                tp_price = round(entry_price * 1.025, 8)
                sl_price = round(entry_price * 0.985, 8)
            else:
                tp_price = round(entry_price * 0.975, 8)
                sl_price = round(entry_price * 1.015, 8)

        # Build the pick in alpha_engine standard format
        pick = {
            "id": signal.get("id", f"pm_{sym}_{now.strftime('%Y%m%d%H%M')}"),
            "strategy": signal.get("strategy", "prediction_market_consensus"),
            "symbol": sym,
            "category": signal.get("category", "crypto"),
            "signal_type": signal.get("signal_type", "BUY" if direction == "LONG" else "SELL"),
            "direction": direction,
            "entry_price": entry_price,
            "entry_date": signal.get("entry_date", now.strftime("%Y-%m-%d")),
            "take_profit": tp_price,
            "stop_loss": sl_price,
            "confidence": conf,
            "ml_score": None,
            "status": "OPEN",
            "source_system": source or "prediction_market_agents",
            "source": "prediction_market_agents",

            # Prediction market metadata
            "consensus_data": signal.get("consensus_data"),
            "whale_data": signal.get("whale_data"),
            "momentum_data": signal.get("momentum_data"),
            "kalshi_data": signal.get("kalshi_data"),

            "reason": signal.get("reason", ""),
            "timestamp": signal.get("timestamp", now.isoformat()),
            "created_at": now.isoformat(),
        }

        active_picks.append(pick)
        existing_keys.add(key_with_source)
        existing_keys.add(key_pm)
        merged += 1

    logger.info(
        "[MERGE] %d picks merged into active_picks.json "
        "(removed: %d raw PM picks, %d conflicting PM picks; skipped: %d low-conf, %d lower-conf conflicts, %d dupes; total now: %d)",
        merged, removed_raw, removed_conflicts, skipped_conf, skipped_conflict, skipped_dup, len(active_picks),
    )

    if removed_raw > 0 or removed_conflicts > 0 or merged > 0:
        try:
            from alpha_engine.feed_hygiene import sanitize_active_picks
        except ImportError:
            sanitize_active_picks = lambda picks, label="": picks
        active_picks = sanitize_active_picks(active_picks, "prediction_market")
        _save_json(ACTIVE_PICKS_PATH, active_picks)
        logger.info("[MERGE] Saved %d total picks to %s", len(active_picks), ACTIVE_PICKS_PATH)
    elif not signals:
        logger.info("[MERGE] No new consensus signals to merge")

    return merged


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def run_all_agents() -> Dict[str, Any]:
    """
    Run the full prediction market agent pipeline:
    1. Run each agent (fail-safe — one agent failing doesn't stop others)
    2. Build cross-market consensus
    3. Merge all signals into active_picks.json
    4. Return summary
    """
    start_time = datetime.now(timezone.utc)
    logger.info("=" * 70)
    logger.info("  PREDICTION MARKET AGENT ORCHESTRATOR")
    logger.info("  %s", start_time.strftime("%Y-%m-%d %H:%M:%S UTC"))
    logger.info("=" * 70)

    results = {}
    all_signals = []

    # Agent 1: Polymarket Whale Tracker
    logger.info("\n[1/4] Running Polymarket Whale Tracker...")
    whale_result = run_whale_tracker()
    results["whale_tracker"] = {
        "traders": whale_result.get("total_traders_scanned", 0),
        "signals": whale_result.get("total_signals", 0),
        "error": whale_result.get("error"),
    }
    whale_signals = whale_result.get("signals", [])
    all_signals.extend(whale_signals)

    # Agent 2: Polymarket Momentum Detector
    logger.info("\n[2/4] Running Polymarket Momentum Detector...")
    momentum_result = run_momentum_detector()
    results["momentum_detector"] = {
        "markets_analyzed": momentum_result.get("markets_analyzed", 0),
        "signals": momentum_result.get("momentum_signals", 0),
        "error": momentum_result.get("error"),
    }
    momentum_signals = momentum_result.get("signals", [])
    all_signals.extend(momentum_signals)

    # Agent 3: Kalshi Multi-Timeframe Agent
    logger.info("\n[3/4] Running Kalshi Multi-Timeframe Agent...")
    kalshi_result = run_kalshi_agent()
    results["kalshi_agent"] = {
        "events": kalshi_result.get("events_analyzed", 0),
        "signals": kalshi_result.get("signals_generated", 0),
        "error": kalshi_result.get("error"),
    }
    kalshi_signals = kalshi_result.get("signals", [])
    all_signals.extend(kalshi_signals)

    # Agent 4: Cross-Market Consensus (reads from agent data files)
    logger.info("\n[4/4] Running Cross-Market Consensus Engine...")
    consensus_result = run_consensus()
    results["consensus"] = {
        "signals_aggregated": consensus_result.get("total_signals_aggregated", 0),
        "consensus_signals": consensus_result.get("consensus_signals", 0),
        "high_conviction": consensus_result.get("high_conviction_count", 0),
        "error": consensus_result.get("error"),
    }
    consensus_signals = consensus_result.get("signals", [])

    # Merge only the consensus layer into active_picks.json.
    # Individual whale/momentum/Kalshi outputs stay in prediction_market_agents/data
    # for research and diagnostics, but they do not go directly to the dashboard feed.
    logger.info("\n[MERGE] Merging signals into alpha_engine pipeline...")
    merged_consensus = merge_into_active_picks(consensus_signals)
    total_merged = merged_consensus

    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    summary = {
        "generated_at": end_time.isoformat(),
        "duration_seconds": round(duration, 1),
        "agent_results": results,
        "total_raw_signals": len(all_signals),
        "consensus_signals": len(consensus_signals),
        "merged_to_pipeline": total_merged,
    }

    # Save orchestrator summary
    PM_DATA_DIR.mkdir(parents=True, exist_ok=True)
    _save_json(PM_DATA_DIR / "orchestrator_summary.json", summary)

    logger.info("\n" + "=" * 70)
    logger.info("  ORCHESTRATOR COMPLETE — %.1fs", duration)
    logger.info("  Raw signals: %d | Consensus: %d | Merged to pipeline: %d",
                len(all_signals), len(consensus_signals), total_merged)
    logger.info("=" * 70)

    return summary


if __name__ == "__main__":
    summary = run_all_agents()
    print(json.dumps(summary, indent=2))
