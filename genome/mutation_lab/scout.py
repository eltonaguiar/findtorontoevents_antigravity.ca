"""Stage 1: SCOUT — Identify mutation targets.

Queries all strategy performance data, ranks them, and selects
the top 15 winners and bottom 15 losers for mutation.

Usage:
    python -m genome.mutation_lab.scout [--output mutation_targets.json]
"""

from __future__ import annotations
import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from genome.mutation_lab.db_wrapper import fetch_all_strategies, compute_composite_score
from genome.mutation_lab.schemas import validate_targets
from genome.mutation_lab.backtester import fetch_klines, BACKTEST_SYMBOLS

logger = logging.getLogger(__name__)

TOP_N = 15
BOTTOM_N = 15
MIN_TRADES_WINNER = 10
MIN_TRADES_LOSER = 5


def identify_targets(strategies: list[dict]) -> dict:
    """Rank strategies and pick top winners + bottom losers."""
    # Deduplicate by name (keep highest trade count)
    by_name: dict[str, dict] = {}
    for s in strategies:
        name = s.get("name", "").strip()
        if not name:
            continue
        existing = by_name.get(name)
        if existing is None or s.get("total_trades", 0) > existing.get("total_trades", 0):
            by_name[name] = s

    # Score all strategies
    scored = []
    for name, s in by_name.items():
        s["composite_score"] = compute_composite_score(s)
        scored.append(s)

    # Winners: WR>50% or PF>1.0, meaningful trade count
    winner_candidates = [
        s for s in scored
        if (s.get("total_trades") or 0) >= MIN_TRADES_WINNER
        and (_norm_wr(s.get("win_rate") or 0) > 0.50 or (s.get("profit_factor") or 0) > 1.0)
    ]
    winners = sorted(winner_candidates, key=lambda x: x["composite_score"], reverse=True)[:TOP_N]

    # Assign mutation_type A (amplify) for winners
    for w in winners:
        w["mutation_type"] = "A"

    # Losers: WR<40% or PF<0.8, at least some trades (not untested)
    loser_candidates = [
        s for s in scored
        if (s.get("total_trades") or 0) >= MIN_TRADES_LOSER
        and (_norm_wr(s.get("win_rate") or 0) < 0.40 or (s.get("profit_factor") or 0) < 0.8)
    ]
    losers = sorted(loser_candidates, key=lambda x: x["composite_score"])[:BOTTOM_N]

    # Assign mutation_type: B (flip) for worst, C (fix) for fixable losers
    for i, l in enumerate(losers):
        wr = _norm_wr(l.get("win_rate", 0))
        if wr < 0.25:
            l["mutation_type"] = "B"  # flip — consistently wrong, invert signals
        elif l.get("total_trades", 0) < 3:
            l["mutation_type"] = "C"  # fix — broken/insufficient, add trend filter + tighten SL
        else:
            l["mutation_type"] = "C"  # fix — underperforming, adjust params

    # If we didn't get enough losers with strict criteria, fill with lowest scorers
    if len(losers) < BOTTOM_N:
        existing_names = {l.get("name") for l in losers}
        remaining = [
            s for s in scored
            if s.get("total_trades", 0) >= MIN_TRADES_LOSER
            and s.get("name") not in existing_names
        ]
        remaining.sort(key=lambda x: x["composite_score"])
        for r in remaining[:BOTTOM_N - len(losers)]:
            r["mutation_type"] = "C"
            losers.append(r)

    # Similarly fill winners if needed
    if len(winners) < TOP_N:
        existing_names = {w.get("name") for w in winners}
        remaining = [
            s for s in scored
            if s.get("total_trades", 0) >= MIN_TRADES_WINNER
            and s.get("name") not in existing_names
        ]
        remaining.sort(key=lambda x: x["composite_score"], reverse=True)
        for r in remaining[:TOP_N - len(winners)]:
            r["mutation_type"] = "A"
            winners.append(r)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_strategies_scanned": len(scored),
        "winners": winners,
        "losers": losers,
    }


def _norm_wr(wr: float) -> float:
    """Normalize win rate to 0-1 range."""
    return wr / 100.0 if wr > 1 else wr


def prefetch_market_data() -> dict:
    """Pre-fetch klines for all backtest symbols. Returns {symbol: path_to_cache}."""
    data_info = {}
    for sym in BACKTEST_SYMBOLS:
        df = fetch_klines(sym)
        if df is not None and len(df) > 100:
            data_info[sym] = {
                "bars": len(df),
                "start": str(df.index[0]),
                "end": str(df.index[-1]),
                "last_close": float(df["Close"].iloc[-1]),
            }
            logger.info(f"Fetched {len(df)} bars for {sym}")
        else:
            logger.warning(f"Failed to fetch data for {sym}")
    return data_info


def run_scout(output_path: str = "mutation_targets.json") -> dict:
    """Main scout entry point."""
    logger.info("SCOUT: Fetching strategy performance data...")
    strategies = fetch_all_strategies()
    logger.info(f"SCOUT: Found {len(strategies)} strategies")

    targets = identify_targets(strategies)
    logger.info(f"SCOUT: Selected {len(targets['winners'])} winners, {len(targets['losers'])} losers")

    # Prefetch market data info
    market_info = prefetch_market_data()
    targets["market_data"] = market_info

    # Validate
    errors = validate_targets(targets)
    if errors:
        logger.error(f"SCOUT: Validation errors: {errors}")
        # Still write, but log warnings
        targets["validation_warnings"] = errors

    # Write output
    out = Path(output_path)
    out.write_text(json.dumps(targets, indent=2, default=str))
    logger.info(f"SCOUT: Written to {out}")

    return targets


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Mutation Lab Scout")
    parser.add_argument("--output", default="mutation_targets.json")
    args = parser.parse_args()

    targets = run_scout(args.output)
    print(f"Scout complete: {len(targets['winners'])} winners, {len(targets['losers'])} losers")
    print(f"Top winner: {targets['winners'][0]['name'] if targets['winners'] else 'none'}")
    print(f"Worst loser: {targets['losers'][0]['name'] if targets['losers'] else 'none'}")


if __name__ == "__main__":
    main()
