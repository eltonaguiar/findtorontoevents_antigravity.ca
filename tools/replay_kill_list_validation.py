"""Replay validation for the 2026-10-20 operator kill list + fail-closed gate.

Simulates a replay window (Oct 12-19 surrogate batch) through
blocklist_gate.filter_blocked_picks and asserts the operator's validation rules:

  1. All kill-list (asset_class, strategy) pairs -> 0 emitted.
  2. forex_rsi2_mean_reversion::EURUSD=X -> 0 emitted (BANNED).
  3. ETF rs-breakout-scout STILL issues (operator exception, forward-test).

This is the deterministic, offline equivalent of the production "24h
post-deploy blocked-strategy count = 0" check (which requires live deployment).
Run from the repo root:  python3 tools/replay_kill_list_validation.py
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from alpha_engine.blocklist_gate import filter_blocked_picks
from alpha_engine.strategy_blocklist import _CLASS_SCOPED_BLOCKED_PAIRS

# One sample pick per killed pair (surrogate replay-window batch).
BATCH: list[dict] = [
    {"strategy": strat, "asset_class": acls, "source_system": "replay", "symbol": "SAMPLE"}
    for acls, strat in _CLASS_SCOPED_BLOCKED_PAIRS
]

# BANNED FOREX pair must also be dropped.
BATCH.append({"strategy": "forex_rsi2_mean_reversion", "asset_class": "FOREX", "symbol": "EURUSD=X", "source_system": "multi_asset_copytrader"})
# Operator exception: ETF rs-breakout-scout must survive.
BATCH.append({"strategy": "rs-breakout-scout", "asset_class": "ETF", "symbol": "SPY", "source_system": "etf"})
# Unrelated live pair must survive.
BATCH.append({"strategy": "proven_pair", "asset_class": "CRYPTO", "symbol": "BTCUSDT", "source_system": "alpha_engine"})


def main() -> int:
    emitted = filter_blocked_picks(BATCH)

    killed_pairs = [(a, s) for a, s in _CLASS_SCOPED_BLOCKED_PAIRS]
    surviving_killed = [p for p in emitted if (p["asset_class"], p["strategy"]) in killed_pairs]
    assert not surviving_killed, f"FAIL: killed pairs emitted: {surviving_killed}"

    forex_emitted = [p for p in emitted if p["strategy"] == "forex_rsi2_mean_reversion"]
    assert not forex_emitted, "FAIL: banned forex_rsi2_mean_reversion emitted"

    etf_rs = [p for p in emitted if p["strategy"] == "rs-breakout-scout" and p["asset_class"] == "ETF"]
    assert len(etf_rs) == 1, "FAIL: ETF rs-breakout-scout did not survive"

    proven = [p for p in emitted if p["strategy"] == "proven_pair"]
    assert len(proven) == 1, "FAIL: unrelated live pair was dropped"

    print(f"PASS: replay batch={len(BATCH)} emitted={len(emitted)}")
    print(f"  killed pairs emitted: {len(surviving_killed)} (expected 0)")
    print(f"  forex_rsi2_mean_reversion emitted: {len(forex_emitted)} (expected 0)")
    print(f"  ETF rs-breakout-scout survives: {len(etf_rs)} (expected 1)")
    print(f"  unrelated live pair survives: {len(proven)} (expected 1)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
