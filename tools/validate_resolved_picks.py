#!/usr/bin/env python3
"""
===============================================================================
validate_resolved_picks.py
===============================================================================
Feed REAL resolver output (universal_resolved_picks.json) through the
statistical_validation_framework.py to produce genuine validation results.

For each strategy with >= MIN_TRADES resolved picks:
  1. Build chronological PnL series from trade outcomes
  2. Compute per-trade Sharpe, win-rate, profit factor
  3. BootstrapValidator → Sharpe CI + p-value
  4. WalkForwardValidator → OOS consistency
  5. MonteCarloStressTester → stress-test passes
  6. MultipleTestingCorrector → FDR across all strategies

Output: JSON report + human-readable summary

Usage:
    python3 tools/validate_resolved_picks.py
    python3 tools/validate_resolved_picks.py --min-trades 30
    python3 tools/validate_resolved_picks.py --by-asset-class
===============================================================================
"""
import json
import logging
import sys
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from alpha_engine.statistical_validation_framework import (
    BootstrapValidator,
    WalkForwardValidator,
    MonteCarloStressTester,
    MultipleTestingCorrector,
    RISK_FREE_RATE,
    TRADING_DAYS_YEAR,
    SHARPE_MIN,
    PVALUE_MAX,
    MAX_DRAWDOWN_MAX,
    _setup_logging,
)

_setup_logging(logging.INFO)
log = logging.getLogger("validate_resolved_picks")

# ---------------------------------------------------------------------------
# Config & Logging
# ---------------------------------------------------------------------------
DATA_PATH = ROOT / "audit_trail" / "data" / "universal_resolved_picks.json"
OUTPUT_DIR = ROOT / "reports"
DEFAULT_MIN_TRADES = 20

# Ensure root logger is configured so our messages appear
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stderr,
)

# Time-based exit is an artifact of the resolver (auto-expiry), not a real trade outcome
EXCLUDE_REASONS = {"TIME_EXIT"}

# Avoid conflating zero-PnL or flat entries
EXCLUDE_PNL_ABS_MAX = 100.0  # already clamped in resolver but safety check


def _sharpe_from_trades(pnl_values: np.ndarray, n_calendar_days: int) -> float:
    """Compute annualized Sharpe from per-trade PnL values.

    Scales by sqrt(trades_per_year) so that a strategy with few trades isn't
    artificially inflated (or deflated) relative to a frequent trader.
    """
    if len(pnl_values) < 5 or pnl_values.std(ddof=1) == 0:
        return 0.0
    n_days = max(n_calendar_days, 1)
    years = n_days / 365.0
    trades_per_year = len(pnl_values) / max(years, 0.01)
    xs = pnl_values - (RISK_FREE_RATE / max(trades_per_year, 1))
    sharpe = float(xs.mean() / xs.std(ddof=1) * np.sqrt(trades_per_year))
    return sharpe


def _max_drawdown_from_trades(pnl_values: np.ndarray) -> float:
    """Compute max drawdown from cumulative trade PnL series."""
    if len(pnl_values) == 0:
        return 0.0
    cum = np.cumprod(1 + pnl_values / 100.0)  # pnl_pct is in %, convert to decimal
    peak = np.maximum.accumulate(cum)
    dd = (cum - peak) / peak
    return float(dd.min())


def _safe_mean(arr):
    return float(np.mean(arr)) if len(arr) > 0 else 0.0


def load_picks(path: Path) -> list[dict]:
    """Load and basic-validate resolved picks."""
    if not path.exists():
        log.error("File not found: %s", path)
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        log.error("Expected list, got %s", type(data).__name__)
        return []
    log.info("Loaded %d resolved picks from %s", len(data), path.name)
    return data


def group_by_strategy(picks: list[dict]) -> dict[str, list[dict]]:
    """Group resolved picks by strategy name."""
    groups = defaultdict(list)
    for p in picks:
        strategy = str(p.get("strategy", "unknown") or "unknown").strip()
        if not strategy:
            strategy = "unknown"
        groups[strategy].append(p)
    return dict(groups)


def validate_strategy(strategy: str, picks: list[dict], min_trades: int = DEFAULT_MIN_TRADES) -> dict | None:
    """Run full validation on a single strategy's resolved picks.

    Returns dict with validation results, or None if strategy doesn't meet
    minimum trade threshold.
    """
    # Filter out TIME_EXIT (artifact of auto-resolver, not real trade)
    trades = [p for p in picks
              if p.get("exit_reason", "") not in EXCLUDE_REASONS
              and p.get("pnl_pct") is not None
              and abs(float(p.get("pnl_pct", 0))) < EXCLUDE_PNL_ABS_MAX]

    if len(trades) < min_trades:
        return {
            "strategy": strategy,
            "n_trades": len(trades),
            "n_raw": len(picks),
            "skipped": True,
            "reason": f"Only {len(trades)} valid trades (need {min_trades})",
        }

    # Extract PnL and sort by resolution date
    sorted_trades = sorted(trades, key=lambda p: str(p.get("resolved_at", p.get("timestamp", ""))))
    pnl_pcts = np.array([float(t["pnl_pct"]) for t in sorted_trades])
    pnl_pcts_decimal = pnl_pcts / 100.0  # convert % to decimal for compounding

    # Date range
    first_ts = str(sorted_trades[0].get("resolved_at", sorted_trades[0].get("timestamp", "")))
    last_ts = str(sorted_trades[-1].get("resolved_at", sorted_trades[-1].get("timestamp", "")))
    n_calendar_days = 0
    try:
        dt1 = datetime.fromisoformat(first_ts.replace("Z", "+00:00"))
        dt2 = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
        n_calendar_days = max((dt2 - dt1).days, 1)
    except Exception:
        n_calendar_days = max(len(pnl_pcts), 1)

    # --- Trade-level statistics ---
    wins = pnl_pcts[pnl_pcts > 0]
    losses = pnl_pcts[pnl_pcts <= 0]
    n_trades = len(pnl_pcts)
    n_wins = len(wins)
    n_losses = len(losses)
    win_rate = n_wins / n_trades if n_trades > 0 else 0.0
    avg_win = float(wins.mean()) if n_wins > 0 else 0.0
    avg_loss = float(losses.mean()) if n_losses > 0 else 0.0
    total_pnl = float(pnl_pcts.sum())
    avg_pnl = float(pnl_pcts.mean())
    profit_factor = abs(avg_win * n_wins / (avg_loss * n_losses)) if avg_loss != 0 and n_losses > 0 else 0.0

    # Sharpe (per-trade, annualized by trades/year)
    sharpe = _sharpe_from_trades(pnl_pcts_decimal, n_calendar_days)

    # Max drawdown from trade sequence
    max_dd = _max_drawdown_from_trades(pnl_pcts)

    # Sortino (downside deviation)
    downside = pnl_pcts_decimal[pnl_pcts_decimal < 0]
    downside_std = downside.std(ddof=1) if len(downside) > 5 else pnl_pcts_decimal.std(ddof=1)
    years = n_calendar_days / 365.0
    trades_per_year = n_trades / max(years, 0.01)
    xs_mean = (pnl_pcts_decimal.mean() - (RISK_FREE_RATE / max(trades_per_year, 1)))
    sortino = float(xs_mean / downside_std * np.sqrt(trades_per_year)) if downside_std > 0 else 0.0

    # --- Bootstrap Validation ---
    boot = BootstrapValidator(pnl_pcts_decimal, n_resamples=10_000, random_seed=42)
    boot_ci_lower, boot_ci_upper = boot.sharpe_confidence_interval(alpha=0.05)
    boot_p = boot.p_value(null_sharpe=0.0)

    # --- Walk-Forward Validation ---
    # NOTE: WalkForwardValidator's window sizes are designed for daily data
    # (252/year). On trade-level data, "months" maps to trade-count-based
    # windows. Using train_months=1, test_months=1 = 21 train / 21 test trades
    # per window, requiring 42+ trades for at least 1 window.
    # Strategies with < 42 trades get 0 windows (wf_skipped=True).
    wfv = WalkForwardValidator(pnl_pcts_decimal, train_months=1, test_months=1)
    wfv_result = wfv.run(strategy_id=strategy, min_train_days=10)
    wfv_skipped = wfv_result.windows == 0
    wfv_robust = wfv_result.is_robust if not wfv_skipped else False
    wfv_consistency = wfv_result.consistency_score if not wfv_skipped else 0.0
    wfv_n_windows = wfv_result.windows
    wfv_is_sharpe_mean = float(np.mean(wfv_result.in_sample_sharpes)) if wfv_result.in_sample_sharpes else (None if wfv_skipped else 0.0)
    wfv_oos_sharpe_mean = float(np.mean(wfv_result.out_of_sample_sharpes)) if wfv_result.out_of_sample_sharpes else (None if wfv_skipped else 0.0)

    # Gate WF: only test if we had enough trades for at least 1 window
    gate_wf_consistency = wfv_consistency >= 0.5 if not wfv_skipped else False

    # --- Monte Carlo Stress Test ---
    mc = MonteCarloStressTester(pnl_pcts_decimal, n_runs=5_000, random_seed=42)
    mc_result_boot = mc.run(strategy_id=strategy, scenario="bootstrap")
    mc_result_crash = mc.run(strategy_id=strategy, scenario="crash", shock_params={"crash_pct": -0.10})
    mc_result_regime = mc.run(strategy_id=strategy, scenario="regime_shift", shock_params={"vol_multiplier": 2.0})

    # --- Pass/fail gates ---
    # Gate A: Sharpe > 1.0
    gate_sharpe = sharpe >= SHARPE_MIN
    # Gate B: Bootstrap p-value < 0.05 (edge is not zero)
    gate_pvalue = boot_p < PVALUE_MAX
    # Gate C: CI lower bound > 0 (95% confidence Sharpe > 0)
    gate_ci_lower = boot_ci_lower > 0

    # Gate E: Monte Carlo bootstrap passes (5th percentile bootstrap Sharpe > 0)
    # Means 95%+ of bootstrap resamples produce positive Sharpe — tight gate.
    gate_mc_bootstrap = mc_result_boot.passes_stress
    # Gate F: Monte Carlo crash scenario not catastrophic
    mc_crash_percentile_5 = mc_result_crash.percentile_5
    gate_mc_crash = mc_crash_percentile_5 > -2.0  # crash scenario Sharpe > -2 is resilient
    # Gate G: Positive win rate
    gate_winrate = win_rate > 0.40
    # Gate H: Profit factor > 1.0
    gate_profit_factor = profit_factor > 1.0

    gates_passed = sum([gate_sharpe, gate_pvalue, gate_ci_lower, gate_wf_consistency,
                        gate_mc_bootstrap, gate_mc_crash, gate_winrate, gate_profit_factor])
    n_gates = 8

    result = {
        "strategy": strategy,
        "n_trades": n_trades,
        "n_raw": len(picks),
        "n_time_exits": len(picks) - len(trades),
        "date_range_days": n_calendar_days,
        "trades_per_year": round(trades_per_year, 1),
        "skipped": False,

        # Trade stats
        "win_rate": round(win_rate, 4),
        "avg_pnl_pct": round(avg_pnl, 4),
        "total_pnl_pct": round(total_pnl, 4),
        "avg_win_pct": round(avg_win, 4),
        "avg_loss_pct": round(avg_loss, 4),
        "profit_factor": round(profit_factor, 4),
        "max_drawdown": round(max_dd, 4),

        # Risk metrics
        "sharpe_ratio": round(sharpe, 4),
        "sortino_ratio": round(sortino, 4),

        # Bootstrap
        "bootstrap_ci_95_lower": round(boot_ci_lower, 4),
        "bootstrap_ci_95_upper": round(boot_ci_upper, 4),
        "bootstrap_p_value": round(boot_p, 6),

        # Walk-forward
        "wf_n_windows": wfv_n_windows,
        "wf_is_sharpe_mean": round(wfv_is_sharpe_mean, 4) if wfv_is_sharpe_mean is not None else None,
        "wf_oos_sharpe_mean": round(wfv_oos_sharpe_mean, 4) if wfv_oos_sharpe_mean is not None else None,
        "wf_consistency": round(wfv_consistency, 4),
        "wf_robust": wfv_robust,
        "wf_skipped": wfv_skipped,

        # Monte Carlo
        "mc_bootstrap_sharpe_5pct": round(mc_result_boot.percentile_5, 4),
        "mc_bootstrap_prob_loss": round(mc_result_boot.probability_of_loss, 4),
        "mc_bootstrap_passes": mc_result_boot.passes_stress,
        "mc_crash_sharpe_5pct": round(mc_crash_percentile_5, 4),
        "mc_crash_prob_loss": round(mc_result_crash.probability_of_loss, 4),
        "mc_crash_passes": mc_result_crash.passes_stress,
        "mc_regime_sharpe_5pct": round(mc_result_regime.percentile_5, 4),
        "mc_regime_prob_loss": round(mc_result_regime.probability_of_loss, 4),
        "mc_regime_passes": mc_result_regime.passes_stress,

        # Gate results
        "gates_passed": gates_passed,
        "gates_total": n_gates,
        "gate_sharpe_above_min": gate_sharpe,
        "gate_pvalue_significant": gate_pvalue,
        "gate_ci_lower_positive": gate_ci_lower,
        "gate_wf_consistent": gate_wf_consistency,
        "gate_mc_bootstrap": gate_mc_bootstrap,
        "gate_mc_crash_resilient": gate_mc_crash,
        "gate_winrate_above_40pct": gate_winrate,
        "gate_profit_factor_above_1": gate_profit_factor,
    }

    # Asset class breakdown
    asset_classes = defaultdict(int)
    for t in trades:
        ac = str(t.get("asset_class", "UNKNOWN") or "UNKNOWN").upper()
        asset_classes[ac] += 1
    result["asset_class_breakdown"] = dict(asset_classes)

    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Validate resolved picks through statistical framework")
    parser.add_argument("--min-trades", type=int, default=DEFAULT_MIN_TRADES,
                        help=f"Minimum trades per strategy (default: {DEFAULT_MIN_TRADES})")
    parser.add_argument("--by-asset-class", action="store_true",
                        help="Also group and validate by asset class separately")
    parser.add_argument("--output", type=str, default="validation_real_data_report.json",
                        help="Output JSON filename (default: validation_real_data_report.json)")
    parser.add_argument("--save-csv", action="store_true",
                        help="Save per-strategy results as CSV for easy analysis")
    args = parser.parse_args()

    log.info("=" * 70)
    log.info("REAL-DATA STATISTICAL VALIDATION")
    log.info("=" * 70)

    # 1. Load data
    picks = load_picks(DATA_PATH)
    if not picks:
        log.error("No picks loaded — aborting")
        return

    # 2. Group by strategy
    by_strategy = group_by_strategy(picks)
    log.info("Found %d unique strategies", len(by_strategy))

    # 3. Validate each strategy
    results = []
    skipped = []
    for strategy, strategy_picks in sorted(by_strategy.items(), key=lambda x: len(x[1]), reverse=True):
        log.info("Validating: %s (%d picks)", strategy, len(strategy_picks))
        result = validate_strategy(strategy, strategy_picks, min_trades=args.min_trades)
        if result:
            if result.get("skipped"):
                skipped.append(result)
            else:
                results.append(result)
                log.info("  Trades=%d Sharpe=%.2f WR=%.1f%% WF_OOS=%.2f MC_pass=%s Gates=%d/%d",
                         result["n_trades"], result["sharpe_ratio"], result["win_rate"] * 100,
                         result["wf_oos_sharpe_mean"], result["mc_bootstrap_passes"],
                         result["gates_passed"], result["gates_total"])

    log.info("")
    log.info("=" * 70)
    log.info("RESULTS SUMMARY")
    log.info("=" * 70)
    log.info("Total strategies: %d", len(by_strategy))
    log.info("Validated (>=%d trades): %d", args.min_trades, len(results))
    log.info("Skipped (insufficient trades): %d", len(skipped))

    # 4. Multiple testing correction across all strategies
    p_values = [r["bootstrap_p_value"] for r in results]
    strategy_names = [r["strategy"] for r in results]
    sharpes = [r["sharpe_ratio"] for r in results]

    if p_values:
        mtc = MultipleTestingCorrector(p_values)
        bh_sig = mtc.bh_fdr(alpha=0.05)
        bonf_sig = mtc.bonferroni(alpha=0.05)
        adaptive_sig = mtc.adaptive_fdr(alpha=0.05)

        fdr_results = []
        for i, name in enumerate(strategy_names):
            fdr_results.append({
                "strategy": name,
                "sharpe": round(sharpes[i], 4),
                "p_value": round(p_values[i], 6),
                "passed_bh_fdr": bool(bh_sig[i]),
                "passed_bonferroni": bool(bonf_sig[i]),
                "passed_adaptive_fdr": bool(adaptive_sig[i]),
                "passed_6_of_8_gates": results[i]["gates_passed"] >= 6,
            })

        n_bh = int(bh_sig.sum())
        n_bonf = int(bonf_sig.sum())
        n_adaptive = int(adaptive_sig.sum())
        n_all_gates = sum(1 for r in results if r["gates_passed"] >= 6)

        log.info("")
        log.info("--- Multiple Testing Correction (FDR) ---")
        log.info("BH-FDR significant: %d / %d", n_bh, len(results))
        log.info("Bonferroni significant: %d / %d", n_bonf, len(results))
        log.info("Adaptive FDR (Storey) significant: %d / %d", n_adaptive, len(results))
        log.info("Passed 6+/8 gates: %d / %d", n_all_gates, len(results))

        log.info("")
        log.info("--- Top strategies by Sharpe (FDR-passing) ---")
        mtc_detail = mtc.summary(alpha=0.05)
        log.info("FDR summary: %s", json.dumps(mtc_detail, indent=2))

        # Sort by Sharpe, show only FDR-passing
        sorted_results = sorted(
            [(s, sh, pv, bh) for s, sh, pv, bh in zip(strategy_names, sharpes, p_values, bh_sig)],
            key=lambda x: x[1], reverse=True
        )
        for s, sh, pv, bh in sorted_results[:20]:
            marker = "✅" if bh else "  "
            log.info("  %s %-45s Sharpe=%.2f p=%.4f", marker, s, sh, pv)

    else:
        fdr_results = []
        mtc_detail = {"error": "no strategies to test"}

    # 5. Build full report
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_data": str(DATA_PATH),
        "n_total_picks": len(picks),
        "n_strategies_total": len(by_strategy),
        "n_strategies_validated": len(results),
        "n_strategies_skipped": len(skipped),
        "min_trades_threshold": args.min_trades,

        "overall_stats": {
            "n_bh_fdr_significant": int(bh_sig.sum()) if p_values else 0,
            "n_bonferroni_significant": int(bonf_sig.sum()) if p_values else 0,
            "n_adaptive_fdr_significant": n_adaptive,
            "n_passed_6_of_8_gates": n_all_gates,
            "fraction_bh_sig": round(float(bh_sig.mean()), 4) if p_values else 0.0,
        },

        "mtc_summary": mtc_detail,
        "fdr_results": fdr_results,
        "per_strategy_results": results,
        "skipped_strategies": skipped,
    }

    # 6. Write output
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / args.output
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    log.info("")
    log.info("Report written to: %s (%d bytes)", out_path, out_path.stat().st_size)

    # 7. Optional CSV
    if args.save_csv:
        try:
            import csv
            csv_path = OUTPUT_DIR / args.output.replace(".json", ".csv")
            with open(csv_path, "w", newline="") as f:
                if results:
                    w = csv.DictWriter(f, fieldnames=results[0].keys())
                    w.writeheader()
                    w.writerows(results)
            log.info("CSV written to: %s", csv_path)
        except Exception as e:
            log.warning("CSV save failed: %s", e)

    # 8. Human-readable summary
    log.info("")
    log.info("=" * 70)
    log.info("HUMAN-READABLE SUMMARY")
    log.info("=" * 70)

    # Per-asset-class totals
    ac_totals = defaultdict(lambda: {"strategies": 0, "trades": 0, "wins": 0, "losses": 0, "sharpe_sum": 0.0})
    for r in results:
        for ac, cnt in r.get("asset_class_breakdown", {}).items():
            ac_totals[ac]["strategies"] += 1
            ac_totals[ac]["trades"] += cnt
    log.info("Asset class distribution (validated strategies):")
    for ac, info in sorted(ac_totals.items(), key=lambda x: x[1]["trades"], reverse=True):
        log.info("  %-12s %d strategies, %d trades", ac, info["strategies"], info["trades"])

    # Best performers
    log.info("")
    log.info("Top 10 strategies by Sharpe (6+/8 gates):")
    passed_6 = [r for r in results if r["gates_passed"] >= 6]
    for r in sorted(passed_6, key=lambda x: x["sharpe_ratio"], reverse=True)[:10]:
        log.info("  ✅ %-45s Sharpe=%.2f WR=%.1f%% PF=%.1f Gates=%d/%d WF_OOS=%.2f MC_pass=%s",
                 r["strategy"][:45], r["sharpe_ratio"], r["win_rate"] * 100,
                 r["profit_factor"], r["gates_passed"], r["gates_total"],
                 r["wf_oos_sharpe_mean"], r["mc_bootstrap_passes"])

    # Worst performers (passed FDR but have low Sharpe — possible flukes)
    log.info("")
    log.info("Strategies that failed scrutiny (Sharpe < 1.0 or < 4 gates):")
    failed = [r for r in results if r["sharpe_ratio"] < 1.0 or r["gates_passed"] < 4]
    for r in sorted(failed, key=lambda x: x["sharpe_ratio"])[:10]:
        log.info("  ❌ %-45s Sharpe=%.2f Gates=%d/%d WR=%.1f%% WF_OOS=%.2f",
                 r["strategy"][:45], r["sharpe_ratio"],
                 r["gates_passed"], r["gates_total"],
                 r["win_rate"] * 100, r["wf_oos_sharpe_mean"])

    log.info("")
    log.info("=== Validation complete ===")

    # Return the report for programmatic use
    return report


if __name__ == "__main__":
    main()
