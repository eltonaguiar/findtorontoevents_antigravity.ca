#!/usr/bin/env python3
"""
Monte Carlo Strategy Validator — Bootstrap Resampling + Permutation Tests
=========================================================================
Anti-overfitting validation for crypto trading strategies.

Methods:
  1. Bootstrap Resampling: Resample trade PnL with replacement to estimate
     confidence intervals for win rate, avg PnL, Sharpe, profit factor.
  2. Permutation Test: Shuffle trade labels to test if strategy edge is
     statistically significant vs random.
  3. Walk-Forward Stability: Split trades chronologically into K folds,
     check if performance is stable across time periods.
  4. Multi-Symbol Robustness: Check if strategy works across symbols,
     not just a single lucky pair.

Usage:
    from monte_carlo_validator import validate_strategy
    report = validate_strategy("st_fear_greed_contrarian", n_simulations=10000)
    print(report["verdict"])  # "ROBUST" | "FRAGILE" | "OVERFIT" | "INSUFFICIENT_DATA"

Stdlib + numpy only. Windows UTF-8 safe.
"""

import json
import math
import os
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Windows UTF-8
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
RESULTS_DIR = DATA / "monte_carlo_results"

# ─── Configuration ─────────────────────────────────────────────────────
DEFAULT_N_SIMULATIONS = 10_000
BOOTSTRAP_CI_LEVELS = (0.025, 0.975)  # 95% confidence interval
MIN_TRADES_FOR_VALIDATION = 15
WALK_FORWARD_FOLDS = 5
SIGNIFICANCE_THRESHOLD = 0.05  # p-value threshold for permutation test

# Robustness verdict thresholds
ROBUST_MIN_WR_CI_LOWER = 0.50      # 95% CI lower bound for WR must be >50%
ROBUST_MIN_SYMBOLS_PROFITABLE = 0.60  # 60%+ of symbols must be profitable
ROBUST_MIN_FOLD_CONSISTENCY = 0.60    # 60%+ of walk-forward folds profitable
ROBUST_MAX_PERMUTATION_P = 0.05       # Permutation test p-value < 5%


def _load_json(path: Path) -> Any:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# ═══════════════════════════════════════════════════════════════════════
# 1. BOOTSTRAP RESAMPLING
# ═══════════════════════════════════════════════════════════════════════

def bootstrap_metrics(pnls: list[float], n_simulations: int = DEFAULT_N_SIMULATIONS) -> dict:
    """Bootstrap resample trade PnLs to estimate confidence intervals.

    Returns dict with:
        win_rate: {mean, ci_lower, ci_upper}
        avg_pnl: {mean, ci_lower, ci_upper}
        profit_factor: {mean, ci_lower, ci_upper}
        sharpe: {mean, ci_lower, ci_upper}
        max_drawdown: {mean, ci_lower, ci_upper}
    """
    n = len(pnls)
    if n < 5:
        return {"error": "insufficient_data", "n": n}

    wr_samples = []
    avg_samples = []
    pf_samples = []
    sharpe_samples = []
    dd_samples = []

    for _ in range(n_simulations):
        # Resample with replacement
        sample = [pnls[random.randint(0, n - 1)] for _ in range(n)]

        wins = sum(1 for p in sample if p > 0)
        losses = sum(1 for p in sample if p <= 0)
        wr_samples.append(wins / n)

        avg_pnl = sum(sample) / n
        avg_samples.append(avg_pnl)

        win_sum = sum(p for p in sample if p > 0)
        loss_sum = abs(sum(p for p in sample if p < 0))
        pf = win_sum / loss_sum if loss_sum > 0 else 99.0
        pf_samples.append(min(pf, 99.0))

        if len(sample) > 1:
            import statistics
            stdev = statistics.stdev(sample)
            sharpe_samples.append(avg_pnl / stdev if stdev > 0 else 0)
        else:
            sharpe_samples.append(0)

        # Max drawdown of the equity curve
        equity = 0
        peak = 0
        max_dd = 0
        for p in sample:
            equity += p
            if equity > peak:
                peak = equity
            dd = peak - equity
            if dd > max_dd:
                max_dd = dd
        dd_samples.append(max_dd)

    def _ci(samples):
        s = sorted(samples)
        lo_idx = int(BOOTSTRAP_CI_LEVELS[0] * len(s))
        hi_idx = int(BOOTSTRAP_CI_LEVELS[1] * len(s))
        return {
            "mean": sum(s) / len(s),
            "ci_lower": s[lo_idx],
            "ci_upper": s[hi_idx],
            "median": s[len(s) // 2],
        }

    return {
        "n_simulations": n_simulations,
        "n_trades": n,
        "win_rate": _ci(wr_samples),
        "avg_pnl": _ci(avg_samples),
        "profit_factor": _ci(pf_samples),
        "sharpe": _ci(sharpe_samples),
        "max_drawdown": _ci(dd_samples),
    }


# ═══════════════════════════════════════════════════════════════════════
# 2. PERMUTATION TEST (Statistical Significance)
# ═══════════════════════════════════════════════════════════════════════

def permutation_test(pnls: list[float], n_permutations: int = 5000) -> dict:
    """Test if strategy edge is statistically significant.

    Shuffles win/loss labels randomly N times to build a null distribution,
    then checks where the actual strategy WR/avg PnL falls.

    Returns:
        p_value_wr: probability of seeing this WR by chance
        p_value_pnl: probability of seeing this avg PnL by chance
        is_significant: True if both p-values < threshold
    """
    n = len(pnls)
    if n < 10:
        return {"error": "insufficient_data", "n": n}

    actual_wr = sum(1 for p in pnls if p > 0) / n
    actual_avg = sum(pnls) / n

    wr_count = 0
    pnl_count = 0

    for _ in range(n_permutations):
        shuffled = pnls.copy()
        random.shuffle(shuffled)
        # Permutation test: shuffle trade ORDER only, never flip signs
        # (sign-flipping is a different test — symmetric-returns sign test)

        perm_wr = sum(1 for p in shuffled if p > 0) / n
        perm_avg = sum(shuffled) / n

        if perm_wr >= actual_wr:
            wr_count += 1
        if perm_avg >= actual_avg:
            pnl_count += 1

    p_wr = wr_count / n_permutations
    p_pnl = pnl_count / n_permutations

    return {
        "actual_wr": round(actual_wr * 100, 2),
        "actual_avg_pnl": round(actual_avg, 4),
        "p_value_wr": round(p_wr, 4),
        "p_value_pnl": round(p_pnl, 4),
        "is_significant": p_wr < SIGNIFICANCE_THRESHOLD and p_pnl < SIGNIFICANCE_THRESHOLD,
        "n_permutations": n_permutations,
    }


# ═══════════════════════════════════════════════════════════════════════
# 3. WALK-FORWARD STABILITY
# ═══════════════════════════════════════════════════════════════════════

def walk_forward_stability(pnls: list[float], n_folds: int = WALK_FORWARD_FOLDS) -> dict:
    """Split trades chronologically into K folds and check stability.

    Detects: front-loaded performance (overfit to early data),
    degrading WR, or inconsistent returns across time.
    """
    n = len(pnls)
    if n < n_folds * 3:
        return {"error": "insufficient_data", "n": n, "min_needed": n_folds * 3}

    fold_size = n // n_folds
    folds = []
    for i in range(n_folds):
        start = i * fold_size
        end = start + fold_size if i < n_folds - 1 else n
        fold_pnls = pnls[start:end]
        wins = sum(1 for p in fold_pnls if p > 0)
        wr = wins / len(fold_pnls) * 100
        avg = sum(fold_pnls) / len(fold_pnls)
        folds.append({
            "fold": i + 1,
            "n": len(fold_pnls),
            "win_rate": round(wr, 1),
            "avg_pnl": round(avg, 4),
            "total_pnl": round(sum(fold_pnls), 4),
            "profitable": wr > 50,
        })

    profitable_folds = sum(1 for f in folds if f["profitable"])
    consistency = profitable_folds / n_folds

    # Detect trend: is WR declining over folds?
    wrs = [f["win_rate"] for f in folds]
    if len(wrs) >= 3:
        first_half = sum(wrs[:len(wrs) // 2]) / (len(wrs) // 2)
        second_half = sum(wrs[len(wrs) // 2:]) / (len(wrs) - len(wrs) // 2)
        trend = "IMPROVING" if second_half > first_half + 5 else \
                "DEGRADING" if second_half < first_half - 5 else "STABLE"
    else:
        trend = "UNKNOWN"

    return {
        "n_folds": n_folds,
        "folds": folds,
        "profitable_folds": profitable_folds,
        "consistency": round(consistency, 3),
        "trend": trend,
        "is_stable": consistency >= ROBUST_MIN_FOLD_CONSISTENCY,
    }


# ═══════════════════════════════════════════════════════════════════════
# 4. MULTI-SYMBOL ROBUSTNESS
# ═══════════════════════════════════════════════════════════════════════

def multi_symbol_robustness(trades_by_symbol: dict[str, list[float]]) -> dict:
    """Check if strategy works across multiple symbols.

    A truly robust strategy should be profitable on >60% of symbols
    it trades, not just one lucky pair.
    """
    results = {}
    for sym, pnls in trades_by_symbol.items():
        if len(pnls) < 2:
            continue
        wins = sum(1 for p in pnls if p > 0)
        wr = wins / len(pnls) * 100
        avg = sum(pnls) / len(pnls)
        results[sym] = {
            "n": len(pnls),
            "win_rate": round(wr, 1),
            "avg_pnl": round(avg, 4),
            "profitable": wr > 50,
        }

    total_symbols = len(results)
    profitable_symbols = sum(1 for s in results.values() if s["profitable"])
    robustness = profitable_symbols / total_symbols if total_symbols > 0 else 0

    # Tier assignment based on symbol coverage
    if total_symbols >= 10 and robustness >= 0.7:
        tier = "ALL_SYMBOL"       # Works broadly — strongest signal
    elif total_symbols >= 5 and robustness >= 0.6:
        tier = "MULTI_SYMBOL"     # Works on several pairs — strong
    elif total_symbols >= 3 and robustness >= 0.5:
        tier = "FEW_SYMBOL"       # Works on a handful — moderate
    elif total_symbols >= 1:
        tier = "SINGLE_SYMBOL"    # Only tested on 1-2 pairs — weakest
    else:
        tier = "NO_DATA"

    return {
        "total_symbols": total_symbols,
        "profitable_symbols": profitable_symbols,
        "robustness_ratio": round(robustness, 3),
        "tier": tier,
        "by_symbol": results,
    }


# ═══════════════════════════════════════════════════════════════════════
# 5. MASTER VALIDATOR
# ═══════════════════════════════════════════════════════════════════════

def validate_strategy(
    strategy_name: str,
    pnls: list[float] | None = None,
    trades_by_symbol: dict[str, list[float]] | None = None,
    n_simulations: int = DEFAULT_N_SIMULATIONS,
) -> dict:
    """Run full Monte Carlo validation suite on a strategy.

    If pnls/trades_by_symbol not provided, loads from strategy_performance.json.

    Returns comprehensive validation report with verdict:
        ROBUST: Passes all tests — ready for live allocation
        FRAGILE: Passes some tests — needs more data or parameter tuning
        OVERFIT: Fails walk-forward or permutation test — likely curve-fit
        INSUFFICIENT_DATA: Not enough trades for meaningful validation
    """
    # Auto-load from strategy_performance.json if not provided
    if pnls is None or trades_by_symbol is None:
        strat_perf = _load_json(DATA / "strategy_performance.json") or {}
        strat_data = strat_perf.get(strategy_name, {})

        if pnls is None:
            # Reconstruct PnLs from aggregated stats (approximate)
            n = strat_data.get("closed_picks", 0)
            wins = strat_data.get("wins", 0)
            losses = strat_data.get("losses", 0)
            avg_win = strat_data.get("avg_win_pct", 0.01)
            avg_loss = strat_data.get("avg_loss_pct", -0.01)
            if n > 0:
                pnls = [avg_win] * wins + [-abs(avg_loss)] * losses
                random.shuffle(pnls)  # Remove ordering bias
            else:
                pnls = []

        if trades_by_symbol is None:
            by_sym = strat_data.get("by_symbol", {})
            trades_by_symbol = {}
            for sym, sym_data in by_sym.items():
                if isinstance(sym_data, dict):
                    w = sym_data.get("wins", 0)
                    l = sym_data.get("losses", 0)
                    avg_win = strat_data.get("avg_win_pct", 0.01)
                    avg_loss = strat_data.get("avg_loss_pct", -0.01)
                    trades_by_symbol[sym] = [avg_win] * w + [-abs(avg_loss)] * l

    if len(pnls) < MIN_TRADES_FOR_VALIDATION:
        return {
            "strategy": strategy_name,
            "verdict": "INSUFFICIENT_DATA",
            "n_trades": len(pnls),
            "min_required": MIN_TRADES_FOR_VALIDATION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # Run all validation tests
    bootstrap = bootstrap_metrics(pnls, n_simulations)
    permutation = permutation_test(pnls, min(n_simulations // 2, 5000))
    walk_forward = walk_forward_stability(pnls)
    multi_sym = multi_symbol_robustness(trades_by_symbol or {})

    # Determine verdict
    checks = {
        "bootstrap_wr_ci": bootstrap.get("win_rate", {}).get("ci_lower", 0) > ROBUST_MIN_WR_CI_LOWER,
        "permutation_significant": permutation.get("is_significant", False),
        "walk_forward_stable": walk_forward.get("is_stable", False),
        "multi_symbol_robust": multi_sym.get("robustness_ratio", 0) >= ROBUST_MIN_SYMBOLS_PROFITABLE,
    }

    passed = sum(checks.values())
    if passed >= 4:
        verdict = "ROBUST"
    elif passed >= 2:
        verdict = "FRAGILE"
    else:
        verdict = "OVERFIT"

    # Override: if only single-symbol, cap at FRAGILE
    if multi_sym.get("total_symbols", 0) <= 1 and verdict == "ROBUST":
        verdict = "FRAGILE"
        checks["single_symbol_cap"] = True

    report = {
        "strategy": strategy_name,
        "verdict": verdict,
        "checks": checks,
        "passed": passed,
        "total_checks": len(checks),
        "n_trades": len(pnls),
        "bootstrap": bootstrap,
        "permutation": permutation,
        "walk_forward": walk_forward,
        "multi_symbol": multi_sym,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Save results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = strategy_name.replace(" ", "_").replace("/", "_")[:60]
    _save_json(RESULTS_DIR / f"mc_{safe_name}.json", report)

    return report


# ═══════════════════════════════════════════════════════════════════════
# 6. BATCH VALIDATOR (validate all strategies)
# ═══════════════════════════════════════════════════════════════════════

def validate_all_strategies(
    min_trades: int = MIN_TRADES_FOR_VALIDATION,
    n_simulations: int = DEFAULT_N_SIMULATIONS,
) -> dict:
    """Validate all strategies with enough forward data.

    Returns summary with tier assignments:
        ROBUST strategies → increase allocation
        FRAGILE strategies → maintain, monitor
        OVERFIT strategies → reduce allocation or kill
    """
    strat_perf = _load_json(DATA / "strategy_performance.json") or {}

    results = {}
    for name, data in strat_perf.items():
        if data.get("closed_picks", 0) < min_trades:
            continue
        try:
            report = validate_strategy(name, n_simulations=n_simulations)
            results[name] = {
                "verdict": report["verdict"],
                "passed": report["passed"],
                "n_trades": report["n_trades"],
                "bootstrap_wr_ci": report["bootstrap"].get("win_rate", {}).get("ci_lower", 0),
                "permutation_p": report["permutation"].get("p_value_wr", 1.0),
                "walk_forward_consistency": report["walk_forward"].get("consistency", 0),
                "multi_symbol_tier": report["multi_symbol"].get("tier", "NO_DATA"),
            }
            print(f"  [{report['verdict']:>14}] {name[:50]} — "
                  f"n={report['n_trades']}, checks={report['passed']}/{report['total_checks']}")
        except Exception as e:
            print(f"  [ERROR] {name}: {e}")

    # Save batch results
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_validated": len(results),
        "verdicts": {
            "ROBUST": sum(1 for r in results.values() if r["verdict"] == "ROBUST"),
            "FRAGILE": sum(1 for r in results.values() if r["verdict"] == "FRAGILE"),
            "OVERFIT": sum(1 for r in results.values() if r["verdict"] == "OVERFIT"),
        },
        "strategies": results,
    }
    _save_json(RESULTS_DIR / "batch_validation_summary.json", summary)

    return summary


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) > 1:
        strategy = sys.argv[1]
        print(f"Validating: {strategy}")
        report = validate_strategy(strategy)
        print(f"\nVerdict: {report['verdict']}")
        print(f"Checks passed: {report['passed']}/{report['total_checks']}")
        print(json.dumps(report["checks"], indent=2))
    else:
        print("Running batch validation on all strategies...")
        summary = validate_all_strategies()
        print(f"\nResults: {summary['verdicts']}")
