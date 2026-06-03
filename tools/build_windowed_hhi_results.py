"""Windowed HHI for EAGLE-6 v2 — per-strategy source-system concentration over rolling windows.

EAGLE-6 v1 measures HHI over the active pick universe (single snapshot, all current
picks). This misses per-strategy source concentration: a strategy can have 100% of
its history from a single source_system, but the per-pick HHI on a diverse active
universe would still pass.

This tool implements the v2 design: for each strategy, compute HHI over a moving
window of last K picks, where HHI = sum( (count_per_source / K)^2 ). Verdict:
- PASS if HHI < 0.20 in >=80% of windows
- BORDERLINE if HHI < 0.20 in 50-80% of windows
- FAIL if HHI < 0.20 in <50% of windows
- INSUFFICIENT if total n < window

Usage:
    DB_PASS_STOCKS=stocks1234560 python3 tools/build_windowed_hhi_results.py

Output: tools/windowed_hhi_results.json
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pymysql


def _rolling_hhi(series: list[str], window: int) -> list[float]:
    """Compute rolling-window HHI over a sequence of source labels.
    HHI = sum(share^2) per window. Returns one HHI value per rolling position.
    """
    if len(series) < window:
        return []
    out: list[float] = []
    for i in range(len(series) - window + 1):
        chunk = series[i : i + window]
        counts: dict[str, int] = {}
        for s in chunk:
            counts[s] = counts.get(s, 0) + 1
        hhi = sum((c / window) ** 2 for c in counts.values())
        out.append(round(hhi, 4))
    return out


def _verdict(pass_pct: float, n: int, window: int) -> str:
    if n < window:
        return "INSUFFICIENT"
    if pass_pct >= 0.80:
        return "PASS"
    if pass_pct >= 0.50:
        return "BORDERLINE"
    return "FAIL"


def main(window: int = 50, threshold: float = 0.20, only_strategies: list[str] | None = None) -> None:
    pwd = os.environ.get("DB_PASS_STOCKS")
    if not pwd:
        raise SystemExit("DB_PASS_STOCKS env var not set")

    # Load candidate strategies. Prefer bootstrap_ci_results.json (latest cascade
    # output), fall back to walkforward_oos_results.json (WFO survivors), fall
    # back to a hardcoded list of known candidates.
    bc_path = os.path.join(ROOT, "tools", "bootstrap_ci_results.json")
    wfo_path = os.path.join(ROOT, "tools", "walkforward_oos_results.json")
    candidates: list[str]
    if os.path.exists(bc_path):
        with open(bc_path) as f:
            bc = json.load(f)
        candidates = [s["strategy"] for s in bc["per_strategy"] if s["verdict"] in ("PASS", "BORDERLINE")]
        print(f"[hhi-v2] loaded {len(candidates)} candidates from bootstrap_ci_results.json", flush=True)
    elif os.path.exists(wfo_path):
        with open(wfo_path) as f:
            wfo = json.load(f)
        candidates = [s["strategy"] for s in wfo["per_strategy"] if s["verdict"] in ("PASS", "BORDERLINE")]
        print(f"[hhi-v2] loaded {len(candidates)} candidates from walkforward_oos_results.json", flush=True)
    else:
        candidates = [
            "crypto_liquidity_wick_reversal_v1",
            "prediction_market_consensus",
            "drawdown_recovery_rsi_xrp",
            "rsi_overbought",
            "B_flip_PriceRocMeanReversion",
            "fx_smart_carry_trade_momentum",
            "ml_crypto_pred",
            "claude_ml_moderate_mut",
            "inverse_ml_enhanced_BTCUSDT_15m_D",
            "ensemble",
            "luxalgo_confluence",
            "regime_mild_bull",
            "quan_engine_swing",
            "cvd_divergence",
        ]
        print(f"[hhi-v2] using hardcoded candidate list ({len(candidates)} strategies)", flush=True)
    if only_strategies is not None:
        candidates = [s for s in candidates if s in only_strategies]
    print(f"[hhi-v2] {len(candidates)} candidate strategies (window={window}, threshold={threshold})", flush=True)

    conn = pymysql.connect(
        host="mysql.50webs.com",
        user="ejaguiar1_stocks",
        password=pwd,
        database="ejaguiar1_stocks",
        port=3306,
    )
    try:
        cur = conn.cursor()
        per_strategy: list[dict] = []
        for i, strat in enumerate(candidates, 1):
            cur.execute(
                """
                SELECT IFNULL(source_system, '(null)') AS src
                FROM at_signal_outcomes
                WHERE strategy = %s
                  AND outcome IN ('WON','LOST','TP_HIT','SL_HIT','EXPIRED','CLOSED')
                  AND pnl_pct IS NOT NULL
                ORDER BY closed_at ASC
                """,
                (strat,),
            )
            sources = [r[0] for r in cur.fetchall()]
            n = len(sources)
            hhi_series = _rolling_hhi(sources, window)
            n_windows = len(hhi_series)
            if hhi_series:
                pass_windows = sum(1 for h in hhi_series if h < threshold)
                pass_pct = pass_windows / n_windows
                max_hhi = max(hhi_series)
                median_hhi = sorted(hhi_series)[n_windows // 2]
            else:
                pass_windows = 0
                pass_pct = 0.0
                max_hhi = 0.0
                median_hhi = 0.0
            # Also compute whole-history HHI for context
            if n > 0:
                counts: dict[str, int] = {}
                for s in sources:
                    counts[s] = counts.get(s, 0) + 1
                whole_hhi = sum((c / n) ** 2 for c in counts.values())
                unique_sources = len(counts)
            else:
                whole_hhi = 0.0
                unique_sources = 0
            per_strategy.append({
                "strategy": strat,
                "n_total": n,
                "unique_sources": unique_sources,
                "whole_history_hhi": round(whole_hhi, 4),
                "window": window,
                "n_windows": n_windows,
                "pass_windows": pass_windows,
                "pass_pct": round(pass_pct, 4),
                "max_window_hhi": round(max_hhi, 4),
                "median_window_hhi": round(median_hhi, 4),
                "verdict": _verdict(pass_pct, n, window),
            })
            if i % 5 == 0 or i == len(candidates):
                print(f"[hhi-v2]   {i}/{len(candidates)} processed", flush=True)

        n_pass = sum(1 for s in per_strategy if s["verdict"] == "PASS")
        n_border = sum(1 for s in per_strategy if s["verdict"] == "BORDERLINE")
        n_fail = sum(1 for s in per_strategy if s["verdict"] == "FAIL")
        n_insuf = sum(1 for s in per_strategy if s["verdict"] == "INSUFFICIENT")

        out = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "window": window,
            "threshold": threshold,
            "rule": (
                f"PASS if HHI < {threshold} in >=80% of rolling {window}-pick windows; "
                f"BORDERLINE if 50-80%; FAIL if <50%; INSUFFICIENT if n_total < {window}."
            ),
            "n_candidates": len(per_strategy),
            "eagle6_v2_windowed_hhi_gate": (
                f"PASS={n_pass} BORDERLINE={n_border} FAIL={n_fail} INSUFFICIENT={n_insuf} total={len(per_strategy)}"
            ),
            "per_strategy": per_strategy,
        }
        out_path = os.path.join(ROOT, "tools", "windowed_hhi_results.json")
        with open(out_path, "w") as f:
            json.dump(out, f, indent=2)
        print(
            f"[hhi-v2] PASS={n_pass} BORDERLINE={n_border} FAIL={n_fail} "
            f"INSUFFICIENT={n_insuf} -> {out_path}"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
