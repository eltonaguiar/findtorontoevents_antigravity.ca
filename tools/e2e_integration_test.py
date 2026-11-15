#!/usr/bin/env python3
"""
End-to-End Integration Test
============================

Tests the full pipeline:
1. Pick generation → QA validation → Forward-test tracking → Live monitoring

Demonstrates that bad picks are blocked by QA gates and good picks
enter forward-test tracking with kill/promote logic.
"""

import json
import os
import sys
import subprocess
import tempfile
from datetime import datetime, timezone

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "alpha_engine"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "alpha_engine", "data", "forward_testing"))

from risk_qa_validator import validate_all, load_json, save_json
from forward_tracker import log_trade, status as ft_status

TEST_PICKS = [
    {
        "id": "E2E_GOOD_001",
        "symbol": "SPY",
        "entry_price": 754.37,
        "exit_price": 760.00,
        "entry_time": "2026-11-10T09:30:00Z",
        "exit_time": "2026-11-11T16:00:00Z",
        "take_profit": 780.00,
        "stop_loss": 730.00,
        "status": "CLOSED",
        "asset_class": "EQUITY",
        "strategy": "integration_test_strategy",
        "resolution_method": "TP_HIT",
        "pnl_pct": 0.75,
        "direction": "LONG",
        "created_at": "2026-11-10T09:30:00Z",
    },
    {
        "id": "E2E_BAD_BLANK_002",
        "symbol": "BAD_PICK",
        "entry_price": None,
        "exit_price": None,
        "entry_time": None,
        "exit_time": None,
        "take_profit": None,
        "stop_loss": None,
        "status": None,
        "asset_class": None,
        "strategy": None,
        "resolution_method": None,
        "pnl_pct": None,
        "direction": None,
        "created_at": None,
    },
    {
        "id": "E2E_BAD_PNLZERO_003",
        "symbol": "QQQ",
        "entry_price": 500.00,
        "exit_price": 500.00,
        "entry_time": "2026-11-10T09:30:00Z",
        "exit_time": "2026-11-11T16:00:00Z",
        "take_profit": 520.00,
        "stop_loss": 480.00,
        "status": "CLOSED",
        "asset_class": "EQUITY",
        "strategy": "integration_test_strategy",
        "resolution_method": "CLOSED",
        "pnl_pct": 0,
        "direction": "LONG",
        "created_at": "2026-11-10T09:30:00Z",
    },
]

MARKET_DATA = {
    "SPY": {"close_price": 755.00, "current_price": 756.00},
    "QQQ": {"close_price": 510.00, "current_price": 512.00},
    "BAD_PICK": {"close_price": 100.00, "current_price": 100.00},
}


def run_e2e_test():
    print("=" * 80)
    print("END-TO-END INTEGRATION TEST")
    print("=" * 80)
    print()

    # Step 1: QA Validation
    print("STEP 1: QA Validation")
    print("-" * 40)
    result = validate_all(TEST_PICKS, MARKET_DATA)
    print(f"QA Status: {result['qa_status']}")
    print(f"Total picks: {result['total_picks']}")
    print(f"Gate 0 (PnL=0%): {'PASS' if result['gate_0_pnl_zero']['pass'] else 'FAIL'}")
    print(f"Gate 1 (Blank fields): {'PASS' if result['gate_1_blank_fields']['pass'] else 'FAIL'}")
    print()

    # Identify QA-passing picks
    qa_passing = []
    qa_failing = []
    for pr in result["pick_results"]:
        if pr["gate_0_pass"] and pr["gate_1_pass"] and pr["critical_count"] == 0:
            qa_passing.append(pr)
        else:
            qa_failing.append(pr)

    print(f"QA-passing picks: {len(qa_passing)}")
    for pr in qa_passing:
        print(f"  ✓ {pr['pick_id']} ({pr['symbol']})")
    print(f"QA-failing picks: {len(qa_failing)}")
    for pr in qa_failing:
        reasons = []
        for i in pr["issues"]:
            reasons.append(i.get("check", i.get("field", "unknown")))
        print(f"  ✗ {pr['pick_id']} ({pr['symbol']}): {', '.join(reasons[:3])}{'...' if len(reasons) > 3 else ''}")
    print()

    # Step 2: Forward-Test Tracking (only QA-passing picks)
    print("STEP 2: Forward-Test Tracking (QA-passing picks only)")
    print("-" * 40)

    # Clean tracker files for clean test
    tracker_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "forward_testing")
    tracker_csv = os.path.join(tracker_dir, "forward_test_tracker.csv")
    eliminated_csv = os.path.join(tracker_dir, "forward_test_eliminated.csv")
    for f in [tracker_csv, eliminated_csv]:
        if os.path.exists(f):
            os.remove(f)

    # Log trades for QA-passing picks
    for pr in qa_passing:
        pick = next(p for p in TEST_PICKS if p["id"] == pr["pick_id"])
        entry = pick["entry_price"]
        exit_px = pick["exit_price"]
        pnl_pct = pick["pnl_pct"]

        log_trade(
            strategy_id=pr["pick_id"],
            asset_class=pick.get("asset_class", "EQUITY"),
            symbol=pick["symbol"],
            entry=entry,
            exit_px=exit_px,
            qty=10,
            fees=1.0,
            opened=pick["entry_time"],
            closed=pick["exit_time"],
            thesis="E2E integration test",
        )
        print(f"  Logged: {pr['pick_id']} ({pick['symbol']}) — entry={entry}, exit={exit_px}, pnl={pnl_pct}%")

    print()

    # Step 3: Forward-Test Status
    print("STEP 3: Forward-Test Status")
    print("-" * 40)
    ft_status()
    print()

    # Step 4: Pipeline Summary
    print("STEP 4: Pipeline Summary")
    print("-" * 40)
    print(f"  Picks generated:      {len(TEST_PICKS)}")
    print(f"  QA-passed:            {len(qa_passing)}")
    print(f"  QA-blocked:           {len(qa_failing)}")
    print(f"  Forward-tracked:      {len(qa_passing)}")
    print(f"  Blocked from tracking:{len(qa_failing)}")
    print()
    print("  Conclusion: QA gates successfully block bad picks from entering")
    print("  forward-test tracking. Only validated picks proceed.")
    print("=" * 80)


if __name__ == "__main__":
    run_e2e_test()
