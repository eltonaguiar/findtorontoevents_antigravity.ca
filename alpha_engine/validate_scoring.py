#!/usr/bin/env python3
"""
Validate ML/Elite scoring against actual forward outcomes.
Tests Criterion 3: Positive ML score correlation with outcomes.

Loads closed_picks.json, computes elite scores for each pick,
and measures Spearman correlation + precision@K against actual PnL.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Allow running from repo root or alpha_engine/
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def validate():
    try:
        from scipy import stats
    except ImportError:
        stats = None
        print("[WARN] scipy not installed -- skipping significance test")

    try:
        import numpy as np
    except ImportError:
        np = None
        print("[WARN] numpy not installed -- using built-in mean")

    from elite_scorer import (
        compute_elite_score,
        load_monte_carlo_results,
        load_strategy_performance,
    )

    # Load closed picks
    data_dir = Path(__file__).resolve().parent / "data"
    picks_file = data_dir / "closed_picks.json"
    if not picks_file.exists():
        print(f"ERROR: {picks_file} not found")
        return

    with open(picks_file, encoding="utf-8") as f:
        picks = json.load(f)

    print(f"Loaded {len(picks)} closed picks")

    # Load supporting data
    mc_results = load_monte_carlo_results(data_dir)
    strat_perf = load_strategy_performance(data_dir)

    # Score each pick and collect (score, pnl) pairs
    scores = []
    pnls = []
    scored_picks = []

    for p in picks:
        pnl = p.get("pnl_pct")
        if pnl is None:
            continue
        pnl = float(pnl)

        result = compute_elite_score(p, mc_results, strat_perf)
        elite_score = result["elite_score"]

        scores.append(elite_score)
        pnls.append(pnl)
        scored_picks.append({
            "symbol": p.get("symbol", "?"),
            "strategy": p.get("strategy", "?"),
            "elite_score": elite_score,
            "elite_grade": result["elite_grade"],
            "pnl_pct": pnl,
            "confidence": p.get("confidence"),
            "status": p.get("status"),
        })

    print(f"Scored {len(scores)} picks with PnL data")
    if len(scores) < 10:
        print(f"Insufficient data: {len(scores)} scored picks (need >= 10)")
        return

    # -------------------------------------------------------------------
    # Spearman rank correlation: score vs PnL
    # -------------------------------------------------------------------
    if stats:
        corr, pval = stats.spearmanr(scores, pnls)
        print(f"\nSpearman correlation: {corr:.4f} (p={pval:.4f})")
        print(f"Significant at 95%: {'YES' if pval < 0.05 else 'NO'}")
    else:
        corr = _manual_spearman(scores, pnls)
        pval = None
        print(f"\nSpearman correlation (manual): {corr:.4f}")

    # -------------------------------------------------------------------
    # Precision@K: top-K picks by score, what fraction are winners?
    # -------------------------------------------------------------------
    sorted_picks = sorted(zip(scores, pnls), key=lambda x: -x[0])

    print("\n--- Precision@K ---")
    for k in [10, 20, 50]:
        if len(sorted_picks) >= k:
            top_k_wins = sum(1 for _, pnl in sorted_picks[:k] if pnl > 0)
            print(f"Precision@{k}: {top_k_wins/k:.1%} ({top_k_wins}/{k} winners)")

    # -------------------------------------------------------------------
    # Win rate by score quartile
    # -------------------------------------------------------------------
    n = len(sorted_picks)
    q_size = n // 4
    print("\n--- Win Rate by Score Quartile ---")
    for i, label in enumerate(["Top 25%", "2nd 25%", "3rd 25%", "Bottom 25%"]):
        q_picks = sorted_picks[i * q_size : (i + 1) * q_size]
        if not q_picks:
            continue
        q_wr = sum(1 for _, pnl in q_picks if pnl > 0) / len(q_picks)
        if np is not None:
            q_avg = float(np.mean([pnl for _, pnl in q_picks]))
        else:
            q_pnls = [pnl for _, pnl in q_picks]
            q_avg = sum(q_pnls) / len(q_pnls)
        q_scores = [s for s, _ in q_picks]
        print(f"  {label}: {q_wr:.1%} WR, avg PnL {q_avg:+.2f}%, "
              f"score range [{min(q_scores)}-{max(q_scores)}]")

    # -------------------------------------------------------------------
    # Score distribution summary
    # -------------------------------------------------------------------
    if np is not None:
        print(f"\nScore stats: min={min(scores)}, max={max(scores)}, "
              f"mean={float(np.mean(scores)):.1f}, median={float(np.median(scores)):.1f}")
    else:
        sorted_scores = sorted(scores)
        mid = len(sorted_scores) // 2
        median = sorted_scores[mid]
        mean = sum(scores) / len(scores)
        print(f"\nScore stats: min={min(scores)}, max={max(scores)}, "
              f"mean={mean:.1f}, median={median}")

    # -------------------------------------------------------------------
    # Summary verdict
    # -------------------------------------------------------------------
    print("\n" + "=" * 50)
    if corr > 0:
        sig = " (statistically significant)" if pval is not None and pval < 0.05 else ""
        print(f"PASS: Positive correlation {corr:.4f}{sig}")
    else:
        print(f"FAIL: Non-positive correlation {corr:.4f}")

    top20_wr = None
    if len(sorted_picks) >= 20:
        top20_wr = sum(1 for _, pnl in sorted_picks[:20] if pnl > 0) / 20
        if top20_wr >= 0.52:
            print(f"PASS: Precision@20 = {top20_wr:.1%} (target >= 52%)")
        else:
            print(f"FAIL: Precision@20 = {top20_wr:.1%} (target >= 52%)")

    # Save results for KPI monitor
    kpi_output = {
        "spearman_correlation": round(corr, 4),
        "spearman_pval": round(pval, 6) if pval is not None else None,
        "precision_at_10": round(
            sum(1 for _, pnl in sorted_picks[:10] if pnl > 0) / 10, 4
        ) if len(sorted_picks) >= 10 else 0,
        "precision_at_20": round(top20_wr, 4) if top20_wr is not None else 0,
        "precision_at_50": round(
            sum(1 for _, pnl in sorted_picks[:50] if pnl > 0) / 50, 4
        ) if len(sorted_picks) >= 50 else 0,
        "scored_picks": len(scores),
        "total_closed_picks": len(picks),
    }
    kpi_path = data_dir / "scoring_validation.json"
    with open(kpi_path, "w", encoding="utf-8") as f:
        json.dump(kpi_output, f, indent=2)
    print(f"\nSaved validation results to {kpi_path}")


def _manual_spearman(x, y):
    """Simple Spearman correlation without scipy."""
    n = len(x)
    if n == 0:
        return 0.0

    def _rank(vals):
        indexed = sorted(enumerate(vals), key=lambda t: t[1])
        ranks = [0.0] * n
        for rank_idx, (orig_idx, _) in enumerate(indexed):
            ranks[orig_idx] = rank_idx + 1
        return ranks

    rx = _rank(x)
    ry = _rank(y)
    d_sq = sum((a - b) ** 2 for a, b in zip(rx, ry))
    return 1 - (6 * d_sq) / (n * (n ** 2 - 1))


if __name__ == "__main__":
    validate()
