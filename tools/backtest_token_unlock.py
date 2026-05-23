"""
Token Unlock Event-Study Backtest — STUB (S0)

STATUS: NOT_YET_RUN. Placeholder for the event-study calibration harness
required by Strategy Factory v1.1 §6 before the strategy can advance to S1.

Usage:
    python tools/backtest_token_unlock.py \\
        --start 2023-01-01 --end 2026-04-01 \\
        --output artifacts/event_studies/token_unlock.json

When implemented, this script will execute the plan in
`docs/event_studies/token_unlock_calibration_plan.md`:

    1. Load historical unlock calendar (tokenunlocks.app + on-chain).
    2. Load OHLCV 1h bars for each event asset, T-90d..T+7d.
    3. Load BTC 1h returns as market benchmark.
    4. OLS fit (alpha, beta) on estimation window T-90d..T-7d.
    5. Compute abnormal returns and CAR slices.
    6. Per cohort: bootstrap CI, pre-emption ratio, liquidity split,
       sign consistency, chrono holdout.
    7. Emit JSON with PASS / DOWNGRADE / KILL decision per cohort.

Currently emits a skeleton JSON document with status NOT_YET_RUN and the
list of inputs required for a real run.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone


REQUIRED_INPUTS = [
    "historical_unlock_calendar (tokenunlocks.app export, 2023-01-01+)",
    "on_chain_vesting_contract_map (Sablier/Hedgey/OZ VestingWallet)",
    "ohlcv_1h_spot (Binance, failover: CoinGecko/KuCoin/CryptoCompare)",
    "ohlcv_1h_perp (Binance USDT perp)",
    "btc_1h_returns (benchmark)",
    "adv_30d_median_perp_volume (liquidity filter)",
    "macro_event_calendar (Fed/CPI dates for exclusion)",
]

COHORTS = [
    "investor_large_gt5pct_float_short",
    "investor_small_lt2pct_float_long",
    "team_any_size_asymmetry_test",
    "airdrop_tge_regime_only",
]


def parse_args(argv: list) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--start", required=True, help="YYYY-MM-DD")
    p.add_argument("--end", required=True, help="YYYY-MM-DD")
    p.add_argument("--output", required=True, help="path to output JSON")
    return p.parse_args(argv)


def build_stub_report(start: str, end: str) -> dict:
    return {
        "strategy": "token_unlock_event_driven",
        "lifecycle_stage": "S0",
        "status": "NOT_YET_RUN",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "window": {"start": start, "end": end},
        "required_inputs": REQUIRED_INPUTS,
        "planned_cohorts": COHORTS,
        "promotion_gate": {
            "min_events_per_cohort": 30,
            "bootstrap_ci_excludes_zero": True,
            "pre_emption_share_lt": 0.30,
            "liquidity_split_p_lt": 0.10,
            "sign_consistency_gte": 0.60,
            "event_level_sharpe_gte": 0.8,
        },
        "notes": (
            "Implementation deferred. See "
            "docs/event_studies/token_unlock_calibration_plan.md."
        ),
    }


def main(argv: list) -> int:
    args = parse_args(argv)
    report = build_stub_report(args.start, args.end)
    out_dir = os.path.dirname(os.path.abspath(args.output))
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
    print(f"[NOT_YET_RUN] wrote stub report to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
