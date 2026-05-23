#!/usr/bin/env python3
"""Publish edge findings to alpha_engine_bus."""

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

    # Message 1: Score-PnL correlation findings
    envelope1 = {
        "bus_topic": "edge_findings_score_pnl",
        "from": "kilo-deep-analysis",
        "ts": ts,
        "summary": "SCORE-PNL CORRELATION: Confidence vs PnL r=+0.008 (noise). Elite Score vs PnL r=+0.203 (weak). 5 fixes projected to boost to +0.63-0.85: (1) TP/SL quality score component, (2) Replace backtest WR with forward WR in elite_score, (3) Symbol predictability score, (4) Direction-specific scoring (SHORT 72% WR vs LONG 20.3%), (5) Regime-conditional scoring. Elite score 40-59 range is the ONLY positive-expectancy bucket (60.8% WR). See EDGE_FINDINGS_2026-04-06.md Part 1.",
        "doc_path_repo_relative": "EDGE_FINDINGS_2026-04-06.md",
    }
    body1 = json.dumps(envelope1, separators=(",", ":"))
    run_redis_cmd(["PUBLISH", "alpha_engine_bus", body1])
    run_redis_cmd(
        [
            "LPUSH",
            "bus:broadcast:log",
            f"edge_findings_score_pnl | r=+0.008 conf, +0.203 elite | {ts}",
        ]
    )

    # Message 2: Where edge actually is
    envelope2 = {
        "bus_topic": "edge_findings_where_edge_is",
        "from": "kilo-deep-analysis",
        "ts": ts,
        "summary": "EDGE LOCATIONS: (1) quan_engine active: 95.8% WR +669% PnL 284 trades. (2) st_rsi_momentum_confluence: 65.1% WR PF 2.53 258 trades — ONLY ROBUST walk-forward strategy. (3) Commodities: 61.9% WR +4.59% PnL — only winning non-crypto. (4) XRPUSDT: 54.1% WR — only profitable symbol with 30+ trades. (5) SHORT direction: 72% WR vs LONG 20.3%. (6) Elite score 40-59: 60.8% WR. NOISE KILLERS: quan_engine_scalp 2512 trades -427% PnL. TRXUSDT -18779% (96.8% of all losses). Alpha Factors 3-5% WR. MATICUSDT 550 trades 0% WR. See EDGE_FINDINGS_2026-04-06.md Part 2.",
        "doc_path_repo_relative": "EDGE_FINDINGS_2026-04-06.md",
    }
    body2 = json.dumps(envelope2, separators=(",", ":"))
    run_redis_cmd(["PUBLISH", "alpha_engine_bus", body2])
    run_redis_cmd(
        [
            "LPUSH",
            "bus:broadcast:log",
            f"edge_findings_where_edge_is | quan 95.8%WR | st_rsi 65.1%WR | {ts}",
        ]
    )

    # Message 3: Non-crypto + ejaguiar1_stocks
    envelope3 = {
        "bus_topic": "edge_findings_non_crypto_mysql",
        "from": "kilo-deep-analysis",
        "ts": ts,
        "summary": "NON-CRYPTO: Only COMMODITY wins (61.9% WR +4.59%). EQUITY catastrophic (35.3% WR -363%). FOREX losing (29.7% WR -42%). But Connors RSI-2 (SPY 75.7% WR p=6e-6) and Leveraged ETF Decay Shorts (LABD 77% WR) are ready to deploy. MYSQL ejaguiar1_stocks: 55000+ picks, 1182 strategies, 8 tables. Schema gaps: no smart_score column, no walk-forward results in DB, no regime data, no TP/SL quality metrics. See EDGE_FINDINGS_2026-04-06.md Parts 3-4.",
        "doc_path_repo_relative": "EDGE_FINDINGS_2026-04-06.md",
    }
    body3 = json.dumps(envelope3, separators=(",", ":"))
    run_redis_cmd(["PUBLISH", "alpha_engine_bus", body3])
    run_redis_cmd(
        [
            "LPUSH",
            "bus:broadcast:log",
            f"edge_findings_non_crypto | commodity 61.9%WR | mysql 55k picks | {ts}",
        ]
    )

    # Message 4: What's remaining for hedge fund quality
    envelope4 = {
        "bus_topic": "edge_findings_remaining_gaps",
        "from": "kilo-deep-analysis",
        "ts": ts,
        "summary": "REMAINING FOR HEDGE FUND QUALITY (10 gaps): (1) Score-PnL correlation +0.008 -> +0.7 needed. (2) ATR dynamic TP/SL. (3) Forward validation gate (broken 7 weeks). (4) Symbol filtering (Tier 1/2 only). (5) Direction scoring (SHORT 72% WR advantage). (6) Regime routing. (7) Kill quan_engine_scalp (-427% PnL). (8) Deploy structural edges (funding arb, ETF decay, Connors RSI-2). (9) Deflated Sharpe gate. (10) TimescaleDB migration. BOTTOM LINE: Edge exists — quan_engine 95.8%WR, st_rsi 65.1%WR, commodities 61.9%WR, SHORT 72%WR. Kill noise, fix scoring, deploy proven edges = hedge fund quality. See EDGE_FINDINGS_2026-04-06.md Part 5.",
        "doc_path_repo_relative": "EDGE_FINDINGS_2026-04-06.md",
    }
    body4 = json.dumps(envelope4, separators=(",", ":"))
    run_redis_cmd(["PUBLISH", "alpha_engine_bus", body4])
    run_redis_cmd(
        [
            "LPUSH",
            "bus:broadcast:log",
            f"edge_findings_remaining_gaps | 10 gaps to HF quality | {ts}",
        ]
    )
    run_redis_cmd(["LTRIM", "bus:broadcast:log", "0", "99"])

    print(f"[OK] Published 4 messages to alpha_engine_bus at {ts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
