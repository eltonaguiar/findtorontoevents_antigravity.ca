#!/usr/bin/env python3
"""
SPORTS BETTING EDGE STRATEGIES
===============================
Integrates bookmaker odds from OLG and Betway with prediction market
probabilities and situational models to identify value bets and
arbitrage opportunities in sports betting.

This module is the high-level orchestrator:
  1. Sync prediction market signals (Polymarket)
  2. Scan for arbitrage across all books
  3. Run situational edge adjustments
  4. Output unified edge picks

Usage:
    python3 alpha_engine/sports_betting_edge.py
    python3 alpha_engine/sports_betting_edge.py --sport icehockey_nhl --min-ev 0.02
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional

from alpha_engine.sports_prediction_market_sync import fetch_polymarket_sports_signals
from alpha_engine.sports_arbitrage_scanner import find_arbitrages, fetch_active_odds, _connect
from alpha_engine.sports_edge_finder import SportsEdgeFinder


def sports_betting_edge_scanner(
    sport: str = "basketball_nba",
    min_ev: float = 0.02,
    include_arbitrage: bool = True,
) -> Dict[str, List[Dict]]:
    """
    Main scanner function for sports betting edges.
    Returns dict with keys: value_bets, arbitrages, pm_signals.
    """
    results: Dict[str, List[Dict]] = {
        "value_bets": [],
        "arbitrages": [],
        "pm_signals": [],
    }

    # 1. Prediction market signals
    print(f"[edge-scan] Fetching PM signals...")
    pm_signals = fetch_polymarket_sports_signals(limit=500)
    results["pm_signals"] = pm_signals
    print(f"[edge-scan] PM signals: {len(pm_signals)}")

    # 2. Value bets (+EV)
    print(f"[edge-scan] Scanning {sport} for +EV...")
    finder = SportsEdgeFinder()
    value_bets = finder.scan_for_edges(sport, min_ev=min_ev)
    results["value_bets"] = value_bets
    print(f"[edge-scan] Value bets: {len(value_bets)}")

    # 3. Arbitrage
    if include_arbitrage:
        print(f"[edge-scan] Scanning for arbitrage...")
        conn = _connect()
        if conn:
            try:
                rows = fetch_active_odds(conn, hours_ahead=48)
                arbs = find_arbitrages(rows, min_profit_pct=0.5)
                results["arbitrages"] = arbs
                print(f"[edge-scan] Arbitrages: {len(arbs)}")
            finally:
                conn.close()
        else:
            print("[edge-scan] DB unavailable; arbitrage scan skipped")

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Sports betting edge scanner")
    parser.add_argument("--sport", default="basketball_nba",
                        help="Sport key, e.g. basketball_nba, icehockey_nhl")
    parser.add_argument("--min-ev", type=float, default=0.02)
    parser.add_argument("--no-arb", action="store_true", help="Skip arbitrage scan")
    parser.add_argument("--output", default=None, help="Optional JSON output path")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    results = sports_betting_edge_scanner(
        sport=args.sport,
        min_ev=args.min_ev,
        include_arbitrage=not args.no_arb,
    )

    payload = {
        "ok": True,
        "sport": args.sport,
        "min_ev": args.min_ev,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "value_bet_count": len(results["value_bets"]),
        "arbitrage_count": len(results["arbitrages"]),
        "pm_signal_count": len(results["pm_signals"]),
        "value_bets": results["value_bets"],
        "arbitrages": results["arbitrages"],
        "pm_signals": results["pm_signals"],
    }

    if args.verbose:
        print(json.dumps(payload, indent=2, default=str))
    else:
        print(f"Value bets: {payload['value_bet_count']}")
        print(f"Arbitrages: {payload['arbitrage_count']}")
        print(f"PM signals: {payload['pm_signal_count']}")

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, default=str)
        print(f"[edge-scan] Wrote results to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
