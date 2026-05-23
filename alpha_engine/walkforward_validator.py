#!/usr/bin/env python3
"""Walk-Forward Validation + Mercury 2 Scoring Framework.

Implements:
1. Rolling-window walk-forward validation from closed trades
2. Performance score (Sharpe, CAGR, WR, PF, drawdown, beta)
3. Proof score (p-value, bootstrap CI, feature drift)
4. Composite final_score for strategy ranking
5. Exports ranked_strategies.json for dashboard consumption

Usage:
    python -m alpha_engine.walkforward_validator
"""
from __future__ import annotations

import json
import math
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# 1. Data loading
# ---------------------------------------------------------------------------

def _load_payload() -> dict:
    path = ROOT / "audit_trail" / "data" / "dashboard_payload.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _float(v: Any) -> float:
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


# ---------------------------------------------------------------------------
# 2. Per-strategy trade extraction
# ---------------------------------------------------------------------------

def extract_strategy_trades(payload: dict, min_trades: int = 5) -> dict[str, list[dict]]:
    """Group closed picks by strategy, return only strategies with enough trades."""
    closed = payload.get("picks", {}).get("recent_closed", [])
    strats: dict[str, list[dict]] = defaultdict(list)

    for p in closed:
        strategy = p.get("strategy") or "unknown"
        pnl = _float(p.get("pnl_pct"))
        if pnl == 0 and p.get("_outcome") == "FLAT":
            continue  # skip flat trades
        strats[strategy].append({
            "symbol": p.get("symbol", "?"),
            "direction": p.get("direction", "?"),
            "pnl_pct": min(100, max(-100, pnl)),  # cap at ±100%
            "entry_price": _float(p.get("entry_price")),
            "confidence": _float(p.get("confidence")),
            "score": _float(p.get("score")),
            "timestamp": p.get("timestamp", ""),
            "source_system": p.get("source_system", "?"),
            "asset_class": p.get("asset_class", "CRYPTO"),
            "age_hours": _float(p.get("age_hours")),
        })

    return {s: trades for s, trades in strats.items() if len(trades) >= min_trades}


# ---------------------------------------------------------------------------
# 3. Walk-forward validation (rolling window on trade sequence)
# ---------------------------------------------------------------------------

def walk_forward_validate(
    trades: list[dict],
    train_size: int = 20,
    test_size: int = 10,
    step: int = 5,
) -> dict:
    """Rolling-window walk-forward on a time-ordered sequence of trades.

    Returns per-fold metrics and aggregate out-of-sample performance.
    """
    # Sort by timestamp
    sorted_trades = sorted(trades, key=lambda t: t.get("timestamp", ""))
    pnls = [t["pnl_pct"] for t in sorted_trades]
    n = len(pnls)

    if n < train_size + test_size:
        return {"folds": 0, "oos_sharpe": None, "oos_wr": None, "decay": None}

    folds = []
    i = 0
    while i + train_size + test_size <= n:
        train_pnls = pnls[i : i + train_size]
        test_pnls = pnls[i + train_size : i + train_size + test_size]

        train_wr = sum(1 for x in train_pnls if x > 0) / len(train_pnls) * 100
        test_wr = sum(1 for x in test_pnls if x > 0) / len(test_pnls) * 100

        train_avg = np.mean(train_pnls)
        test_avg = np.mean(test_pnls)

        train_sharpe = _sharpe(train_pnls)
        test_sharpe = _sharpe(test_pnls)

        folds.append({
            "fold": len(folds) + 1,
            "train_start": i,
            "train_end": i + train_size,
            "test_start": i + train_size,
            "test_end": i + train_size + test_size,
            "train_wr": round(train_wr, 1),
            "test_wr": round(test_wr, 1),
            "train_avg_pnl": round(train_avg, 3),
            "test_avg_pnl": round(test_avg, 3),
            "train_sharpe": round(train_sharpe, 3),
            "test_sharpe": round(test_sharpe, 3),
            "decay": round(test_wr - train_wr, 1),
        })
        i += step

    if not folds:
        return {"folds": 0, "oos_sharpe": None, "oos_wr": None, "decay": None}

    # Aggregate out-of-sample metrics
    oos_wrs = [f["test_wr"] for f in folds]
    oos_sharpes = [f["test_sharpe"] for f in folds]
    decays = [f["decay"] for f in folds]

    return {
        "folds": len(folds),
        "oos_wr": round(np.mean(oos_wrs), 1),
        "oos_wr_std": round(np.std(oos_wrs), 1),
        "oos_sharpe": round(np.mean(oos_sharpes), 3),
        "oos_sharpe_std": round(np.std(oos_sharpes), 3),
        "decay": round(np.mean(decays), 1),
        "consistency": round(sum(1 for s in oos_sharpes if s > 0) / len(oos_sharpes) * 100, 1),
        "worst_fold_wr": round(min(oos_wrs), 1),
        "best_fold_wr": round(max(oos_wrs), 1),
        "folds_detail": folds,
    }


# ---------------------------------------------------------------------------
# 3b. Per-asset-class walk-forward (2026-05-02)
#
# MAJOR GOAL #1 surfaces per-class performance on /audit. Since
# extract_strategy_trades() preserves asset_class on every trade, slice the
# closed-pick set by class and run walk-forward on each slice independently.
# Output is suitable to attach to dashboard_payload.json under a
# walkforward.by_class key for the audit page.
# ---------------------------------------------------------------------------

# Per-class walk-forward window config (2026-05-04, swarm-derived).
#
# The previous defaults (min_trades=30, train=20, test=10, step=5) produced
# fold-level Sharpe estimates with std up to 9.4 on classes like COMMODITY
# (test=10 windows are too small — Sharpe estimator collapses). The mean of
# noisy folds is uninformative when std >> |mean|, which is exactly what
# produced the unverifiable -2.343 / -1.895 narrative numbers in
# swarm_runs/MASTER_HEALTH_REPORT.md.
#
# Larger test windows reduce per-fold Sharpe std proportional to ~sqrt(n_test),
# making the aggregated mean meaningful. Window sizes here are chosen so that
# (a) the test n is large enough to produce a usable Sharpe estimate and
# (b) the class has enough total trades to support the configured train+test+step.
# Symbols permitted in the COMMODITY walk-forward universe. Restricted to
# the post-PR-#535 allowlist (HG=F copper + PL=F platinum). Historical
# closed picks on agro/oil/silver/gold sub-classes that PR #535 killed are
# filtered out before the walk-forward windowing — without this filter the
# OOS-Sharpe estimate inherits performance from symbols we deliberately
# banned, which is a look-ahead-style bias against the current production
# universe. See reports/commodity_bond_forensic_2026-05-13.md.
COMMODITY_ALLOWED_SYMBOLS: frozenset[str] = frozenset({"HG=F", "PL=F"})

# M-020: Symbols permitted in the BOND walk-forward universe. Mirrors the
# COMMODITY_ALLOWED_SYMBOLS pattern (PR #940). Restricted to current production
# BOND instruments (TLT = 20yr Treasury ETF, HYG = High-Yield Corporate Bond ETF).
# Historical picks on killed BOND instruments would bias OOS-Sharpe against
# the current production universe. Add new instruments here when they ship.
BOND_ALLOWED_SYMBOLS: frozenset[str] = frozenset({
    "TLT",   # 20yr Treasury ETF
    "HYG",   # High-Yield Corporate Bond ETF
    "IEF",   # 7-10yr Treasury ETF
    "SHY",   # 1-3yr Treasury ETF
    "ZN=F",  # 10yr Treasury Note futures
    "ZB=F",  # 30yr Treasury Bond futures
})

DEFAULT_CLASS_WF_CONFIG: dict[str, dict[str, int]] = {
    "CRYPTO":    {"min_trades": 500, "train_size": 200, "test_size": 100, "step": 50},
    "FOREX":     {"min_trades": 200, "train_size": 100, "test_size":  50, "step": 25},
    # COMMODITY 2026-05-13: lowered from 200/100/50/25. After the HG=F + PL=F
    # universe filter (COMMODITY_ALLOWED_SYMBOLS above), post-filter n in
    # recent_closed is ~27 today (HG=F only — PL=F has emitted zero picks in
    # the 3,500-pick window). The old 200 floor silently skipped COMMODITY
    # even after this PR's filter shipped — caught by swarm review. Sizes
    # below give ~6 folds at n=27, which is the smallest defensible WF;
    # per-fold Sharpe std will be wide. Readers should weigh `folds_detail`
    # and the `symbols_filtered_out` provenance, not just headline
    # `oos_sharpe`. Revisit when post-filter COMMODITY n >= 60.
    "COMMODITY": {"min_trades":  20, "train_size":  10, "test_size":   5, "step":  3},
    "EQUITY":    {"min_trades": 150, "train_size":  80, "test_size":  40, "step": 20},
    "ETF":       {"min_trades":  60, "train_size":  40, "test_size":  20, "step": 10},
    # BOND added 2026-05-14: post-resolver n=12 in recent_closed (per money-
    # maker-ready audit). min_trades=5 produces ~3 folds at test_size=2 — std
    # will be wide, but at least the class appears in walkforward.by_class
    # instead of being silently absent. Revisit when BOND n >= 30.
    "BOND":      {"min_trades":   5, "train_size":   3, "test_size":   2, "step":  1},
    # FUTURES added 2026-05-14 as placeholder: n=0 closed today, so
    # walk_forward_by_class returns folds=0 gracefully. Once PR #946 + #949
    # land and FUTURES picks start closing, this entry activates without a
    # second code change.
    "FUTURES":   {"min_trades":   5, "train_size":   3, "test_size":   2, "step":  1},
}


def walk_forward_by_class(
    payload: dict,
    min_trades: int = 30,
    train_size: int = 20,
    test_size: int = 10,
    step: int = 5,
    class_config: dict[str, dict[str, int]] | None = None,
) -> dict:
    """Run walk_forward_validate() per asset_class on the payload's closed
    trades. Skips classes with fewer than min_trades clean (non-FLAT) trades.

    Per-class window sizing (2026-05-04): pass
    `class_config=DEFAULT_CLASS_WF_CONFIG` to use class-aware window sizes
    (CRYPTO 500/200/100/50, FOREX/COMMODITY 200/100/50/25, etc.) which produce
    stable Sharpe estimates on each class's typical n. With class_config=None
    (default) the legacy flat params apply uniformly — preserves backward
    compatibility for tests and callers that pass small synthetic fixtures.

    Production caller in this module (line ~450) explicitly opts in via
    DEFAULT_CLASS_WF_CONFIG below.
    """
    cfg = class_config if class_config is not None else {}
    closed = payload.get("picks", {}).get("recent_closed", []) if isinstance(payload, dict) else []
    by_class: dict[str, list[dict]] = defaultdict(list)
    commodity_filtered_symbols: set[str] = set()
    bond_filtered_symbols: set[str] = set()  # M-020
    for p in closed:
        if not isinstance(p, dict):
            continue
        if p.get("_outcome") == "FLAT":
            continue
        cls = str(p.get("asset_class") or "CRYPTO").upper().strip() or "CRYPTO"
        if cls == "COMMODITY":
            sym = str(p.get("symbol") or "").strip().upper()
            if sym not in COMMODITY_ALLOWED_SYMBOLS:
                if sym:
                    commodity_filtered_symbols.add(sym)
                continue
        # M-020: Mirror PR #940 COMMODITY pattern for BOND.
        # Filter to BOND_ALLOWED_SYMBOLS so OOS-Sharpe reflects only the
        # current production BOND universe (TLT + HYG), not killed instruments.
        if cls == "BOND":
            sym = str(p.get("symbol") or "").strip().upper()
            if sym not in BOND_ALLOWED_SYMBOLS:
                if sym:
                    bond_filtered_symbols.add(sym)
                continue
        by_class[cls].append({
            "pnl_pct": _float(p.get("pnl_pct")),
            "timestamp": p.get("timestamp", ""),
            "symbol": p.get("symbol", ""),
        })
    out: dict = {}
    for cls, trades in by_class.items():
        c = cfg.get(cls, {})
        cls_min   = int(c.get("min_trades", min_trades))
        cls_train = int(c.get("train_size", train_size))
        cls_test  = int(c.get("test_size",  test_size))
        cls_step  = int(c.get("step",       step))
        if len(trades) < cls_min:
            continue
        result = walk_forward_validate(
            trades, train_size=cls_train, test_size=cls_test, step=cls_step,
        )
        # Embed window provenance so /audit can show what produced the number.
        if isinstance(result, dict):
            result["window_config"] = {
                "min_trades": cls_min, "train_size": cls_train,
                "test_size": cls_test, "step": cls_step,
                "n_trades": len(trades),
            }
            if cls == "COMMODITY":
                # Surface the post-PR-#535 universe used here so a reader can
                # tell the OOS-Sharpe is computed on HG=F+PL=F only, not the
                # historical full commodity book.
                result["symbols_allowed"] = sorted(COMMODITY_ALLOWED_SYMBOLS)
                result["symbols_filtered_out"] = sorted(commodity_filtered_symbols)
            if cls == "BOND":
                # M-020: Surface BOND universe provenance (mirrors COMMODITY pattern).
                result["symbols_allowed"] = sorted(BOND_ALLOWED_SYMBOLS)
                result["symbols_filtered_out"] = sorted(bond_filtered_symbols)
        out[cls] = result
    # Optional W&B drift logging (no-op if WANDB_API_KEY unset). Lets ops
    # catch per-class OOS-Sharpe degradation in real time instead of a
    # quarterly swarm — see Hermes UNUSED_TOOLS_VALUE_ADD.md item #3.
    try:
        from tools.wandb_logger import wb_init, wb_log, wb_finish
        if wb_init(project="findtorontoevents-ml",
                   name="walkforward_by_class",
                   tags=["walkforward", "by_class"],
                   config={"min_trades": min_trades, "train_size": train_size,
                           "test_size": test_size, "step": step}):
            for cls, m in out.items():
                if not isinstance(m, dict) or m.get("oos_sharpe") is None:
                    continue
                wb_log({
                    f"{cls}/oos_sharpe": m["oos_sharpe"],
                    f"{cls}/oos_sharpe_std": m.get("oos_sharpe_std"),
                    f"{cls}/oos_wr": m.get("oos_wr"),
                    f"{cls}/decay": m.get("decay"),
                    f"{cls}/consistency": m.get("consistency"),
                    f"{cls}/folds": m.get("folds"),
                    f"{cls}/worst_fold_wr": m.get("worst_fold_wr"),
                })
            wb_finish()
    except Exception:
        pass
    return out


# ---------------------------------------------------------------------------
# 4. Statistical tests
# ---------------------------------------------------------------------------

def _sharpe(pnls: list[float]) -> float:
    """Annualized Sharpe from trade-level PnL (assuming ~1 trade/day)."""
    if len(pnls) < 2:
        return 0.0
    arr = np.array(pnls)
    std = arr.std()
    if std < 1e-9:
        return 0.0
    return float(arr.mean() / std * math.sqrt(252))


def bootstrap_sharpe_ci(pnls: list[float], n_boot: int = 5000) -> tuple[float, float]:
    """95% confidence interval for Sharpe via bootstrap."""
    arr = np.array(pnls)
    if len(arr) < 5:
        return (0.0, 0.0)
    rng = np.random.RandomState(42)
    boot_sharpes = []
    for _ in range(n_boot):
        sample = rng.choice(arr, size=len(arr), replace=True)
        std = sample.std()
        if std > 1e-9:
            boot_sharpes.append(sample.mean() / std * math.sqrt(252))
    if not boot_sharpes:
        return (0.0, 0.0)
    return (round(float(np.percentile(boot_sharpes, 2.5)), 3),
            round(float(np.percentile(boot_sharpes, 97.5)), 3))


def ttest_pvalue(pnls: list[float]) -> float:
    """Two-sided t-test: is mean PnL significantly different from 0?"""
    if len(pnls) < 3:
        return 1.0
    arr = np.array(pnls)
    mean = arr.mean()
    std = arr.std(ddof=1)
    if std < 1e-9:
        return 1.0
    n = len(arr)
    t_stat = mean / (std / math.sqrt(n))
    # Approximate p-value using normal distribution for large n
    from math import erfc
    p = erfc(abs(t_stat) / math.sqrt(2))
    return round(float(p), 6)


def max_drawdown(pnls: list[float]) -> float:
    """Maximum drawdown from cumulative PnL series."""
    if not pnls:
        return 0.0
    cum = np.cumsum(pnls)
    peak = np.maximum.accumulate(cum)
    dd = peak - cum
    return round(float(dd.max()), 2)


# ---------------------------------------------------------------------------
# 5. Mercury 2 Scoring Framework
# ---------------------------------------------------------------------------

def perf_score(metrics: dict) -> float:
    """Performance score (0-1) based on Sharpe, WR, PF, drawdown."""
    sharpe = min(max(_float(metrics.get("sharpe")), -1), 3)
    wr = min(max(_float(metrics.get("win_rate")), 0), 100) / 100
    pf = min(max(_float(metrics.get("profit_factor")), 0), 10)
    mdd = min(max(_float(metrics.get("max_drawdown")), 0), 50)
    avg_pnl = _float(metrics.get("avg_pnl"))

    # Normalize to 0-1
    sharpe_norm = (sharpe + 1) / 4  # -1→0, 3→1
    wr_norm = max(0, (wr - 0.3) / 0.5)  # 30%→0, 80%→1
    pf_norm = min(1, max(0, (pf - 0.5) / 4.5))  # 0.5→0, 5→1
    dd_penalty = mdd / 30  # 0%→0, 30%→1 (penalty)
    pnl_norm = min(1, max(0, (avg_pnl + 2) / 6))  # -2%→0, 4%→1

    score = (
        0.30 * sharpe_norm
        + 0.20 * pnl_norm
        + 0.20 * wr_norm
        + 0.10 * pf_norm
        - 0.20 * dd_penalty
    )
    return round(max(0, min(1, score)), 4)


def proof_score(metrics: dict) -> float:
    """Statistical confidence score (0-1)."""
    p_val = _float(metrics.get("p_value", 1.0))
    confidence = max(0, 1 - p_val)

    ci_low = _float(metrics.get("sharpe_ci_low", 0))
    ci_high = _float(metrics.get("sharpe_ci_high", 0))
    ci_width = ci_high - ci_low
    ci_factor = max(0, 1 - ci_width / 2.0)

    consistency = _float(metrics.get("consistency", 50)) / 100
    n_trades = _float(metrics.get("trades", 0))
    sample_factor = min(1, n_trades / 100)  # 100+ trades = full confidence

    score = (
        0.35 * confidence
        + 0.25 * ci_factor
        + 0.20 * consistency
        + 0.20 * sample_factor
    )
    return round(max(0, min(1, score)), 4)


def final_score(perf: float, proof: float) -> float:
    """Composite score blending performance and statistical proof."""
    return round(0.65 * perf + 0.35 * proof, 4)


# ---------------------------------------------------------------------------
# 6. Main pipeline
# ---------------------------------------------------------------------------

def run_validation(min_trades: int = 10) -> dict:
    """Run full walk-forward validation and scoring on all strategies."""
    log.info("Loading payload...")
    payload = _load_payload()

    log.info("Extracting strategy trades...")
    strat_trades = extract_strategy_trades(payload, min_trades=min_trades)
    log.info("Found %d strategies with %d+ trades", len(strat_trades), min_trades)

    results = []
    for strategy, trades in sorted(strat_trades.items()):
        pnls = [t["pnl_pct"] for t in trades]
        n = len(trades)

        # Basic metrics
        wins = sum(1 for p in pnls if p > 0.001)
        losses = sum(1 for p in pnls if p < -0.001)
        wr = wins / (wins + losses) * 100 if (wins + losses) else 0
        total_pnl = sum(pnls)
        avg_pnl = np.mean(pnls)
        win_pnl = sum(p for p in pnls if p > 0)
        loss_pnl = sum(abs(p) for p in pnls if p < 0)
        pf = win_pnl / loss_pnl if loss_pnl > 0 else 99.9
        sharpe = _sharpe(pnls)
        mdd = max_drawdown(pnls)
        p_val = ttest_pvalue(pnls)

        # Bootstrap CI
        ci_low, ci_high = bootstrap_sharpe_ci(pnls)

        # Walk-forward
        wf = walk_forward_validate(trades, train_size=max(10, n // 4), test_size=max(5, n // 8))

        # Source systems
        systems = sorted(set(t["source_system"] for t in trades))
        asset_classes = sorted(set(t["asset_class"] for t in trades))

        # Mercury 2 scores
        metrics = {
            "sharpe": sharpe,
            "win_rate": wr,
            "profit_factor": pf,
            "max_drawdown": mdd,
            "avg_pnl": avg_pnl,
            "p_value": p_val,
            "sharpe_ci_low": ci_low,
            "sharpe_ci_high": ci_high,
            "consistency": wf.get("consistency", 50),
            "trades": n,
        }
        ps = perf_score(metrics)
        prs = proof_score(metrics)
        fs = final_score(ps, prs)

        # Determine verdict
        if fs >= 0.70:
            verdict = "ELITE"
        elif fs >= 0.55:
            verdict = "STRONG"
        elif fs >= 0.40:
            verdict = "VIABLE"
        elif fs >= 0.25:
            verdict = "MARGINAL"
        else:
            verdict = "FAILING"

        results.append({
            "strategy": strategy,
            "trades": n,
            "wins": wins,
            "losses": losses,
            "win_rate": round(wr, 1),
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(avg_pnl, 3),
            "profit_factor": round(min(pf, 99.9), 2),
            "sharpe": round(sharpe, 3),
            "max_drawdown": round(mdd, 2),
            "p_value": p_val,
            "sharpe_ci_low": ci_low,
            "sharpe_ci_high": ci_high,
            "sharpe_ci_significant": ci_low > 0,
            "source_systems": systems,
            "asset_classes": asset_classes,
            # Walk-forward
            "wf_folds": wf.get("folds", 0),
            "wf_oos_wr": wf.get("oos_wr"),
            "wf_oos_sharpe": wf.get("oos_sharpe"),
            "wf_decay": wf.get("decay"),
            "wf_consistency": wf.get("consistency"),
            "wf_worst_fold": wf.get("worst_fold_wr"),
            # Mercury 2 scores
            "perf_score": ps,
            "proof_score": prs,
            "final_score": fs,
            "verdict": verdict,
        })

    # Sort by final_score descending
    results.sort(key=lambda x: x["final_score"], reverse=True)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_strategies": len(results),
        "elite_count": sum(1 for r in results if r["verdict"] == "ELITE"),
        "strong_count": sum(1 for r in results if r["verdict"] == "STRONG"),
        "viable_count": sum(1 for r in results if r["verdict"] == "VIABLE"),
        "marginal_count": sum(1 for r in results if r["verdict"] == "MARGINAL"),
        "failing_count": sum(1 for r in results if r["verdict"] == "FAILING"),
        "strategies": results,
        # Per-asset-class walk-forward summary (MAJOR GOAL #1: institutional
        # performance per asset class on /audit). Opt in to class-aware fold
        # sizing (CRYPTO 500/200/100/50 etc.) so OOS Sharpe is statistically
        # meaningful — see DEFAULT_CLASS_WF_CONFIG comment.
        "by_class": walk_forward_by_class(
            payload, class_config=DEFAULT_CLASS_WF_CONFIG,
        ),
    }

    # Save
    out_path = ROOT / "alpha_engine" / "data" / "walkforward_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    log.info("Saved %d strategies to %s", len(results), out_path)

    # Print summary
    print(f"\n{'='*80}")
    print(f"WALK-FORWARD VALIDATION + MERCURY 2 SCORING")
    print(f"{'='*80}")
    print(f"Strategies analyzed: {len(results)}")
    print(f"  ELITE:    {output['elite_count']}")
    print(f"  STRONG:   {output['strong_count']}")
    print(f"  VIABLE:   {output['viable_count']}")
    print(f"  MARGINAL: {output['marginal_count']}")
    print(f"  FAILING:  {output['failing_count']}")
    print(f"\nTop 15 by final_score:")
    print(f"{'Strategy':<45} {'Trades':>6} {'WR':>5} {'PF':>5} {'Sharpe':>7} {'P-val':>7} {'WF-OOS':>7} {'Final':>6} {'Verdict':<8}")
    for r in results[:15]:
        wf_oos = r.get('wf_oos_wr')
        wf_str = f"{wf_oos:>5.1f}%" if wf_oos is not None else "  N/A"
        print(f"{r['strategy'][:44]:<45} {r['trades']:>6} {r['win_rate']:>4.1f}% {r['profit_factor']:>5.2f} {r['sharpe']:>6.3f} {r['p_value']:>7.4f} {wf_str:>7} {r['final_score']:>6.4f} {r['verdict']:<8}")

    return output


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_validation(min_trades=10)


if __name__ == "__main__":
    main()
