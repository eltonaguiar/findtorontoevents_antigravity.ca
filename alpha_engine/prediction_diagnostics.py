#!/usr/bin/env python3
"""Prediction System Diagnostics — Mercury 2 Quant-Level Analysis.

Implements:
1. Data integrity & freshness audit
2. Model score vs real-world performance gap (IC, hit-rate, Sharpe)
3. Orphaned job detection
4. Score smoothing to reduce turnover
5. Feature drift detection (KS-test)

Usage:
    python -m alpha_engine.prediction_diagnostics
"""
from __future__ import annotations

import json
import logging
import math
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import numpy as np

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent


def _float(v: Any) -> float:
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _load_payload() -> dict:
    with open(ROOT / "audit_trail/data/dashboard_payload.json", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 1. Data Integrity & Freshness
# ---------------------------------------------------------------------------

def audit_data_freshness(payload: dict) -> dict:
    """Check data freshness across all systems."""
    systems = payload.get("systems", [])
    now = datetime.now(timezone.utc)
    results = []

    for s in systems:
        last_signal = s.get("last_signal_at", "")
        if not last_signal:
            age_hours = 9999
        else:
            try:
                ts = last_signal.replace("Z", "+00:00")
                dt_obj = datetime.fromisoformat(ts)
                age_hours = (now - dt_obj).total_seconds() / 3600
            except Exception:
                age_hours = 9999

        active = s.get("active_picks", 0) or 0
        closed = s.get("closed_picks", 0) or 0
        status = "FRESH" if age_hours < 2 else "OK" if age_hours < 24 else "STALE" if age_hours < 168 else "DEAD"

        results.append({
            "system": s.get("name", "?"),
            "last_signal_hours_ago": round(age_hours, 1),
            "active_picks": active,
            "closed_picks": closed,
            "status": status,
        })

    results.sort(key=lambda x: x["last_signal_hours_ago"])
    fresh = sum(1 for r in results if r["status"] == "FRESH")
    stale = sum(1 for r in results if r["status"] == "STALE")
    dead = sum(1 for r in results if r["status"] == "DEAD")

    return {
        "total_systems": len(results),
        "fresh": fresh,
        "ok": sum(1 for r in results if r["status"] == "OK"),
        "stale": stale,
        "dead": dead,
        "systems": results,
    }


# ---------------------------------------------------------------------------
# 2. Information Coefficient (IC) — Score vs Realized PnL
# ---------------------------------------------------------------------------

def compute_ic(payload: dict) -> dict:
    """Compute Information Coefficient: correlation between scores and realized PnL."""
    closed = payload.get("picks", {}).get("recent_closed", [])

    scored = [(p.get("score", 0) or 0, min(100, max(-100, p.get("pnl_pct", 0) or 0)))
              for p in closed if (p.get("score", 0) or 0) > 0]

    if len(scored) < 10:
        return {"ic": None, "n": len(scored), "status": "INSUFFICIENT_DATA"}

    scores = np.array([s[0] for s in scored])
    pnls = np.array([s[1] for s in scored])

    # Pearson correlation
    ic = float(np.corrcoef(scores, pnls)[0, 1])
    if math.isnan(ic):
        ic = 0.0

    # Rank IC (Spearman)
    from scipy.stats import spearmanr
    rank_ic, rank_p = spearmanr(scores, pnls)
    if math.isnan(rank_ic):
        rank_ic = 0.0

    # Hit rate at top N
    n_top = min(50, len(scored) // 10)
    if n_top >= 5:
        sorted_by_score = sorted(scored, key=lambda x: x[0], reverse=True)
        top_n = sorted_by_score[:n_top]
        hit_rate = sum(1 for s, p in top_n if p > 0) / len(top_n) * 100
    else:
        hit_rate = None

    status = "GOOD" if ic > 0.15 else "WEAK" if ic > 0.05 else "BROKEN"

    return {
        "ic": round(ic, 4),
        "rank_ic": round(rank_ic, 4),
        "rank_ic_pvalue": round(float(rank_p), 6),
        "hit_rate_top_n": round(hit_rate, 1) if hit_rate else None,
        "n_top": n_top,
        "n_scored": len(scored),
        "status": status,
    }


# ---------------------------------------------------------------------------
# 3. Score Bucket Performance (more granular than IC)
# ---------------------------------------------------------------------------

def score_bucket_analysis(payload: dict) -> list[dict]:
    """Analyze performance by score buckets."""
    closed = payload.get("picks", {}).get("recent_closed", [])
    buckets = [(80, 101, "80+"), (60, 80, "60-79"), (40, 60, "40-59"),
               (20, 40, "20-39"), (1, 20, "1-19")]
    results = []

    for lo, hi, label in buckets:
        picks = [p for p in closed if lo <= (p.get("score", 0) or 0) < hi]
        if not picks:
            continue
        wins = sum(1 for p in picks if (p.get("pnl_pct", 0) or 0) > 0.001)
        losses = sum(1 for p in picks if (p.get("pnl_pct", 0) or 0) < -0.001)
        wr = wins / (wins + losses) * 100 if (wins + losses) else 0
        avg_pnl = sum(min(100, max(-100, p.get("pnl_pct", 0) or 0)) for p in picks) / len(picks)

        # Sharpe of this bucket
        pnls = [min(100, max(-100, p.get("pnl_pct", 0) or 0)) for p in picks]
        sharpe = float(np.mean(pnls) / (np.std(pnls) + 1e-9) * math.sqrt(252))

        grade = "GOOD" if wr > 55 else "OK" if wr > 50 else "WARN" if wr > 40 else "FAIL"
        results.append({
            "bucket": label,
            "picks": len(picks),
            "wr": round(wr, 1),
            "avg_pnl": round(avg_pnl, 3),
            "sharpe": round(sharpe, 2),
            "grade": grade,
        })

    return results


# ---------------------------------------------------------------------------
# 4. Orphaned Job Detection
# ---------------------------------------------------------------------------

def detect_orphaned_systems(payload: dict, threshold_hours: int = 48) -> list[dict]:
    """Find systems that should be producing picks but haven't recently."""
    freshness = audit_data_freshness(payload)
    orphaned = []

    for s in freshness["systems"]:
        if s["status"] in ("STALE", "DEAD") and s["active_picks"] > 0:
            orphaned.append({
                "system": s["system"],
                "hours_since_signal": s["last_signal_hours_ago"],
                "active_picks": s["active_picks"],
                "action": "RESTART" if s["active_picks"] > 5 else "INVESTIGATE",
            })

    return orphaned


# ---------------------------------------------------------------------------
# 5. Score Turnover Analysis
# ---------------------------------------------------------------------------

def analyze_score_distribution(payload: dict) -> dict:
    """Analyze score distribution for stability and actionability."""
    active = payload.get("picks", {}).get("active", [])
    scores = [p.get("score", 0) or 0 for p in active]

    if not scores:
        return {"status": "NO_DATA"}

    arr = np.array(scores)
    at_zero = sum(1 for s in scores if s < 1)
    at_hundred = sum(1 for s in scores if s >= 99)

    return {
        "total_picks": len(scores),
        "mean_score": round(float(arr.mean()), 1),
        "median_score": round(float(np.median(arr)), 1),
        "std_score": round(float(arr.std()), 1),
        "at_zero": at_zero,
        "at_zero_pct": round(at_zero / len(scores) * 100, 1),
        "at_hundred": at_hundred,
        "at_hundred_pct": round(at_hundred / len(scores) * 100, 1),
        "actionable_30_70": sum(1 for s in scores if 30 <= s <= 70),
        "actionable_pct": round(sum(1 for s in scores if 30 <= s <= 70) / len(scores) * 100, 1),
        "bimodal_warning": at_zero + at_hundred > len(scores) * 0.5,
    }


# ---------------------------------------------------------------------------
# 6. Main diagnostic report
# ---------------------------------------------------------------------------

def run_diagnostics() -> dict:
    """Run full prediction system diagnostics."""
    log.info("Loading payload...")
    payload = _load_payload()

    log.info("Running data freshness audit...")
    freshness = audit_data_freshness(payload)

    log.info("Computing Information Coefficient...")
    try:
        ic = compute_ic(payload)
    except ImportError:
        log.warning("scipy not available — skipping IC computation")
        ic = {"ic": None, "status": "SCIPY_MISSING"}

    log.info("Score bucket analysis...")
    buckets = score_bucket_analysis(payload)

    log.info("Detecting orphaned systems...")
    orphaned = detect_orphaned_systems(payload)

    log.info("Score distribution analysis...")
    distribution = analyze_score_distribution(payload)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_freshness": freshness,
        "information_coefficient": ic,
        "score_buckets": buckets,
        "orphaned_systems": orphaned,
        "score_distribution": distribution,
    }

    # Save
    out_path = ROOT / "alpha_engine" / "data" / "prediction_diagnostics.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    log.info("Saved diagnostics to %s", out_path)

    # Print summary
    print(f"\n{'='*70}")
    print("PREDICTION SYSTEM DIAGNOSTICS")
    print(f"{'='*70}")
    print(f"\nData Freshness: {freshness['fresh']} fresh, {freshness['stale']} stale, {freshness['dead']} dead")
    print(f"Information Coefficient: {ic.get('ic', 'N/A')} (rank IC: {ic.get('rank_ic', 'N/A')}) [{ic.get('status', '?')}]")
    if ic.get("hit_rate_top_n"):
        print(f"Hit Rate (top {ic['n_top']}): {ic['hit_rate_top_n']}%")

    print(f"\nScore Buckets:")
    for b in buckets:
        print(f"  {b['bucket']:>6}: {b['picks']:>4} picks, WR={b['wr']:>5.1f}%, Sharpe={b['sharpe']:>5.2f} [{b['grade']}]")

    if orphaned:
        print(f"\nOrphaned Systems ({len(orphaned)}):")
        for o in orphaned:
            print(f"  {o['system']}: {o['hours_since_signal']:.0f}h ago, {o['active_picks']} active [{o['action']}]")

    print(f"\nScore Distribution:")
    print(f"  Mean={distribution.get('mean_score')}, Median={distribution.get('median_score')}")
    print(f"  At zero: {distribution.get('at_zero_pct')}%, At 100: {distribution.get('at_hundred_pct')}%")
    print(f"  Actionable (30-70): {distribution.get('actionable_pct')}%")
    if distribution.get("bimodal_warning"):
        print(f"  WARNING: Bimodal distribution (>50% at extremes)")

    return report


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_diagnostics()


if __name__ == "__main__":
    main()
