#!/usr/bin/env python3
"""Publish edge addendum findings to alpha_engine_bus."""

import json
import subprocess
from datetime import datetime, timezone

REDIS_CLI = "C:/Users/zerou/redis-bus/redis-cli.exe"
PORT = 6379


def run_redis_cmd(args):
    cmd = [REDIS_CLI, "-p", str(PORT)] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    envelope = {
        "bus_topic": "edge_addendum_smart_picks",
        "from": "kilo-edge-analysis",
        "ts": ts,
        "summary": "EDGE_ADDENDUM.md + HEDGE_FUND_ENHANCEMENT_PLAN.md v3. Root cause: backtest-forward correlation -0.91 (system selects overfit strategies). 78.9% SL hit rate. DNA mutations: 14.3% WR live. Only 1/260 strategies survive walk-forward. 7-action fix plan: (1) kill 150+ unvalidated strategies, (2) ATR dynamic TP/SL, (3) deploy structural edges (funding arb, ETF decay, Connors RSI-2), (4) fix forward validation gate, (5) regime-gate strategy selection, (6) symbol tier hard filter, (7) embrace mean-reversion identity. Non-crypto: KEEP Connors RSI-2 (75.7% WR on SPY), VIX Reversal (72%), Leveraged ETF Decay Shorts (77%). KILL Alpha Factors (3-5% WR), forex momentum (30% WR). Backtesting must use real data, walk-forward, anti-overfit 8-checks, DSR > 0.5, 100+ OOS trades, 0.25% real costs.",
        "doc_path_repo_relative": "EDGE_ADDENDUM.md",
        "related_docs": ["HEDGE_FUND_ENHANCEMENT_PLAN.md"],
        "key_findings": {
            "backtest_forward_correlation": -0.91,
            "sl_hit_rate": "78.9%",
            "elite_score_rho": 0.012,
            "dna_mutation_wr": "14.3%",
            "walk_forward_survivors": "1/260",
            "proven_crypto_strategies": [
                "st_rsi_momentum_confluence (65.1% WR)",
                "VWAP Mean Reversion (64.1% WR)",
                "st_fear_greed_contrarian (87.7% WR)",
            ],
            "proven_non_crypto": [
                "Connors RSI-2 SPY (75.7% WR, p=6e-6)",
                "VIX Spike Reversal (72% WR)",
                "ETF Decay LABD SHORT (77% WR)",
                "ETF Decay JDST SHORT (69% WR)",
            ],
            "killed_strategies": [
                "Alpha Factor family (3-5% WR)",
                "forex_logistic_direction (0% WR)",
                "quan_engine_scalp (25% WR, -353% PnL)",
            ],
        },
        "action_required": "Read EDGE_ADDENDUM.md. Priority: kill noise strategies, implement ATR TP/SL, deploy structural edges. This is the missing piece — hedge fund infrastructure without edge = fancy losing.",
    }
    body = json.dumps(envelope, separators=(",", ":"))
    _, code = run_redis_cmd(["PUBLISH", "alpha_engine_bus", body])
    short = (
        f"edge_addendum_smart_picks | EDGE_ADDENDUM.md | backtest-fwd-r=-0.91 | {ts}"
    )
    run_redis_cmd(["LPUSH", "bus:broadcast:log", short])
    run_redis_cmd(["LTRIM", "bus:broadcast:log", "0", "99"])
    print("[OK]" if code == 0 else "[WARN]", short)
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
