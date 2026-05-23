#!/usr/bin/env python3
"""
Combined Confidence Strategy
=============================
Blends copy-trader edge (win rate) with prediction market probability
to produce a single Combined Confidence Score (CS) per pick.

Formula:
    TE  = (WinRate - 0.5) * 2          # Trader Edge: maps 0.50-1.00 → 0.00-1.00
    MP  = prediction_market_probability # Market Probability (already 0-1)
    CS  = (TE + MP) / 2                # Combined Confidence Score

Position sizing:
    CS >= 0.70   → HIGH   (full size, 1.0x-1.2x)
    0.55 <= CS   → MEDIUM (0.5x-0.7x, SL tightened 5-10%)
    CS < 0.55    → LOW    (skip)

Pipeline integration:
    Reads:
      - alpha_engine/data/prediction_market_picks.json  (PM consensus picks)
      - copy_trader_intel/data/non_crypto_consensus_picks.json  (copy-trader picks)
      - alpha_engine/data/active_picks.json  (existing picks with win-rate metadata)
    Writes:
      - alpha_engine/data/combined_confidence_picks.json  (new scored picks)
    Merges into:
      - alpha_engine/data/active_picks.json  (for audit dashboard)
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).resolve().parent / "data"
PM_PICKS_PATH = DATA_DIR / "prediction_market_picks.json"
ACTIVE_PICKS_PATH = DATA_DIR / "active_picks.json"
NON_CRYPTO_PICKS_PATH = ROOT_DIR / "copy_trader_intel" / "data" / "non_crypto_consensus_picks.json"
OUTPUT_PATH = DATA_DIR / "combined_confidence_picks.json"

# Ensure repo root is importable
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("combined_confidence")

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
CS_HIGH = 0.70        # Full size (1.0x–1.2x)
CS_MEDIUM = 0.55      # Reduced size (0.5x–0.7x), tighten SL 5-10%
CS_LOW = 0.55         # Below this → skip
DEFAULT_WIN_RATE = 0.55  # Fallback when no history available
MIN_TRADES_FOR_TE = 5    # Need at least N closed trades to trust WR

STRATEGY_NAME = "combined_confidence"
SOURCE_SYSTEM = "combined_confidence_strategy"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _load_json(path: Path) -> list | dict | None:
    """Load a JSON file, returning None if missing or corrupt."""
    if not path.exists():
        logger.warning("File not found: %s", path)
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to load %s: %s", path, exc)
        return None


def _save_json(path: Path, data) -> None:
    """Save data to JSON atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    tmp.replace(path)


def compute_trader_edge(win_rate: float) -> float:
    """Map win rate (0.50-1.00) to trader edge (0.00-1.00).

    TE = (WR - 0.5) * 2
    Clamp to [0, 1].
    """
    te = (win_rate - 0.5) * 2.0
    return max(0.0, min(1.0, te))


def compute_combined_score(trader_edge: float, market_prob: float) -> float:
    """CS = (TE + MP) / 2, clamped to [0, 1]."""
    cs = (trader_edge + market_prob) / 2.0
    return max(0.0, min(1.0, cs))


def classify_confidence(cs: float) -> str:
    """Return confidence tier: HIGH, MEDIUM, or LOW."""
    if cs >= CS_HIGH:
        return "HIGH"
    if cs >= CS_MEDIUM:
        return "MEDIUM"
    return "LOW"


def compute_position_multiplier(tier: str) -> float:
    """Position sizing multiplier based on confidence tier."""
    if tier == "HIGH":
        return 1.0
    if tier == "MEDIUM":
        return 0.6
    return 0.0  # LOW = skip


def tighten_stop_loss(entry: float, sl: float, direction: str, tier: str) -> float:
    """Tighten SL by 5-10% for MEDIUM tier. HIGH/LOW unchanged."""
    if tier != "MEDIUM" or entry <= 0 or sl <= 0:
        return sl
    # Tighten by 7.5% of the entry-SL distance (midpoint of 5-10%)
    distance = abs(entry - sl)
    tighten = distance * 0.075
    if direction in ("LONG", "BUY"):
        return round(sl + tighten, 8)
    return round(sl - tighten, 8)


# ---------------------------------------------------------------------------
# Win-rate extraction from active picks history
# ---------------------------------------------------------------------------
def _extract_win_rates(active_picks: list[dict]) -> dict[str, dict]:
    """Build {strategy -> {win_rate, trades}} from closed picks in active_picks."""
    stats: dict[str, dict] = {}
    for pick in active_picks:
        status = str(pick.get("status", "")).upper()
        if status not in ("CLOSED", "HIT_TP", "HIT_SL", "EXPIRED", "RESOLVED"):
            continue
        strategy = pick.get("strategy", "")
        if not strategy:
            continue
        if strategy not in stats:
            stats[strategy] = {"wins": 0, "total": 0}
        stats[strategy]["total"] += 1
        # Determine win: hit TP, or positive PnL
        pnl = float(pick.get("pnl_pct", 0) or pick.get("unrealized_pnl_pct", 0) or 0)
        if status == "HIT_TP" or pnl > 0:
            stats[strategy]["wins"] += 1
    result = {}
    for strat, s in stats.items():
        if s["total"] >= MIN_TRADES_FOR_TE:
            result[strat] = {
                "win_rate": s["wins"] / s["total"],
                "trades": s["total"],
            }
    return result


def _get_pick_win_rate(pick: dict, win_rates: dict[str, dict]) -> tuple[float, int]:
    """Get win rate for a pick, checking multiple metadata sources."""
    # 1. Check pick-level metadata (PM picks have history_wr_bayes)
    wr = pick.get("history_wr_bayes")
    trades = pick.get("history_trades", 0)
    if wr is not None and trades >= MIN_TRADES_FOR_TE:
        return float(wr), int(trades)

    # 2. Check forward WR
    fwr = pick.get("forward_wr")
    ft = pick.get("forward_trades", 0)
    if fwr is not None and ft >= MIN_TRADES_FOR_TE:
        return float(fwr), int(ft)

    # 3. Check strategy-level win rates from closed picks
    for key in [pick.get("strategy", ""), pick.get("source_system", "")]:
        if key in win_rates:
            return win_rates[key]["win_rate"], win_rates[key]["trades"]

    # 4. Check consensus source details
    consensus = pick.get("consensus_data", {})
    if isinstance(consensus, dict):
        for src in consensus.get("source_details", []):
            if isinstance(src, dict):
                src_conf = src.get("confidence")
                if src_conf and float(src_conf) > 0.5:
                    return float(src_conf), 1

    # 5. Use pick confidence as proxy (degraded)
    conf = float(pick.get("confidence", DEFAULT_WIN_RATE) or DEFAULT_WIN_RATE)
    return max(conf, DEFAULT_WIN_RATE), 0


# ---------------------------------------------------------------------------
# Core: Generate combined-confidence picks
# ---------------------------------------------------------------------------
def generate_combined_confidence_picks() -> list[dict]:
    """
    Load PM + copy-trader picks, compute Combined Confidence Score,
    filter by tier, and return scored picks.
    """
    now = datetime.now(timezone.utc)

    # Load input sources
    pm_raw = _load_json(PM_PICKS_PATH)
    pm_picks = []
    if isinstance(pm_raw, dict):
        pm_picks = pm_raw.get("picks", [])
    elif isinstance(pm_raw, list):
        pm_picks = pm_raw

    noncrypto_raw = _load_json(NON_CRYPTO_PICKS_PATH)
    noncrypto_picks = noncrypto_raw if isinstance(noncrypto_raw, list) else []

    active_raw = _load_json(ACTIVE_PICKS_PATH)
    active_picks = []
    if isinstance(active_raw, list):
        active_picks = active_raw
    elif isinstance(active_raw, dict):
        active_picks = active_raw.get("picks", [])

    # Build strategy win-rate lookup from historical data
    win_rates = _extract_win_rates(active_picks)

    # Combine all candidate picks
    candidates = []
    for pick in pm_picks:
        pick["_source_type"] = "prediction_market"
        candidates.append(pick)
    for pick in noncrypto_picks:
        pick["_source_type"] = "copy_trader"
        candidates.append(pick)

    logger.info(
        "Candidates: %d PM picks + %d copy-trader picks = %d total",
        len(pm_picks), len(noncrypto_picks), len(candidates),
    )

    results = []
    seen = set()

    for pick in candidates:
        symbol = str(pick.get("symbol", "")).upper()
        direction = str(pick.get("direction", pick.get("signal_type", ""))).upper()
        if direction in ("BUY", "LONG"):
            direction = "LONG"
        elif direction in ("SELL", "SHORT"):
            direction = "SHORT"
        else:
            continue

        # Dedup by symbol+direction
        dedup_key = f"{symbol}_{direction}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        # Extract trader edge
        wr, trade_count = _get_pick_win_rate(pick, win_rates)
        trader_edge = compute_trader_edge(wr)

        # Extract market probability
        # For PM picks, confidence IS the market probability
        # For copy-trader picks, use consensus confidence as market proxy
        market_prob = float(pick.get("confidence", 0) or 0)

        # Compute combined score
        cs = compute_combined_score(trader_edge, market_prob)
        tier = classify_confidence(cs)

        # Skip LOW confidence
        if tier == "LOW":
            logger.debug("SKIP %s %s: CS=%.3f (LOW)", symbol, direction, cs)
            continue

        pos_mult = compute_position_multiplier(tier)
        entry_price = float(pick.get("entry_price", 0) or 0)
        tp = float(pick.get("take_profit", 0) or 0)
        sl = float(pick.get("stop_loss", 0) or 0)

        # Tighten SL for MEDIUM tier
        sl = tighten_stop_loss(entry_price, sl, direction, tier)

        # Recalculate risk/reward after SL adjustment
        rr = 0.0
        if entry_price > 0 and abs(entry_price - sl) > 0:
            rr = abs(tp - entry_price) / abs(entry_price - sl)

        signal_type = "BUY" if direction == "LONG" else "SELL"

        result = {
            "id": f"cc_{symbol}_{direction[0]}_{now.strftime('%Y%m%d%H%M')}",
            "strategy": STRATEGY_NAME,
            "symbol": symbol,
            "category": pick.get("category", "crypto"),
            "asset_class": pick.get("asset_class", pick.get("category", "crypto")).upper(),
            "signal_type": signal_type,
            "direction": direction,
            "entry_price": entry_price,
            "entry_date": now.strftime("%Y-%m-%d"),
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": round(cs, 4),
            "risk_reward": round(rr, 2),
            "status": "OPEN",
            "source_system": SOURCE_SYSTEM,
            "source": pick.get("_source_type", "combined"),
            "timestamp": now.isoformat(),
            "created_at": now.isoformat(),
            "forward_validated": False,
            "forward_test_only": True,
            # Combined confidence metadata
            "combined_confidence_data": {
                "combined_score": round(cs, 4),
                "tier": tier,
                "position_multiplier": pos_mult,
                "trader_edge": round(trader_edge, 4),
                "market_probability": round(market_prob, 4),
                "win_rate": round(wr, 4),
                "trade_count": trade_count,
                "sl_tightened": tier == "MEDIUM",
            },
            "reason": (
                f"Combined Confidence: CS={cs:.2f} ({tier}), "
                f"TE={trader_edge:.2f} (WR={wr:.1%}, {trade_count} trades), "
                f"MP={market_prob:.2f}; "
                f"size={pos_mult:.1f}x"
            ),
        }
        results.append(result)
        logger.info(
            "PICK %s %s: CS=%.3f (%s) TE=%.3f MP=%.3f → %sx",
            symbol, direction, cs, tier, trader_edge, market_prob, pos_mult,
        )

    logger.info("Generated %d combined-confidence picks", len(results))
    return results


# ---------------------------------------------------------------------------
# Merge into active_picks.json
# ---------------------------------------------------------------------------
def merge_into_active_picks(picks: list[dict]) -> int:
    """Merge combined-confidence picks into active_picks.json for dashboard."""
    active_raw = _load_json(ACTIVE_PICKS_PATH)
    if isinstance(active_raw, list):
        active_picks = active_raw
    elif isinstance(active_raw, dict):
        active_picks = active_raw.get("picks", [])
    else:
        active_picks = []

    # Remove stale combined_confidence picks (replace with fresh)
    active_picks = [
        p for p in active_picks
        if str(p.get("source_system", "")).lower() != SOURCE_SYSTEM
    ]

    # Build dedup set from remaining picks (dedupe across source systems —
    # prevents double exposure on the same (symbol, direction) when another
    # source has already published it).
    existing_keys = set()
    for p in active_picks:
        sym = str(p.get("symbol", "")).upper()
        d = str(p.get("direction", p.get("signal_type", ""))).upper()
        if d in ("BUY", "LONG"):
            d = "LONG"
        elif d in ("SELL", "SHORT"):
            d = "SHORT"
        existing_keys.add(f"{sym}_{d}")

    merged = 0
    for pick in picks:
        key = f"{pick['symbol']}_{pick['direction']}"
        if key in existing_keys:
            logger.debug("SKIP duplicate %s (already in active_picks)", key)
            continue
        active_picks.append(pick)
        existing_keys.add(key)
        merged += 1

    # Sanitize via feed_hygiene if available
    try:
        from alpha_engine.feed_hygiene import sanitize_active_picks
        active_picks = sanitize_active_picks(active_picks, "combined_confidence")
    except ImportError:
        pass

    _save_json(ACTIVE_PICKS_PATH, active_picks)
    logger.info(
        "Merged %d combined-confidence picks into active_picks.json (total: %d)",
        merged, len(active_picks),
    )
    return merged


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    """Generate combined-confidence picks and merge into active pipeline."""
    logger.info("=== Combined Confidence Strategy ===")

    picks = generate_combined_confidence_picks()

    # Save standalone output
    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": STRATEGY_NAME,
        "pick_count": len(picks),
        "thresholds": {
            "high": CS_HIGH,
            "medium": CS_MEDIUM,
        },
        "picks": picks,
    }
    _save_json(OUTPUT_PATH, output)
    logger.info("Saved %d picks to %s", len(picks), OUTPUT_PATH)

    # Merge into active picks for audit dashboard
    merged = merge_into_active_picks(picks)
    logger.info("Pipeline complete: %d picks generated, %d merged", len(picks), merged)


if __name__ == "__main__":
    main()
