#!/usr/bin/env python3
"""
Decile Separation Test — THE ultimate validation for the elite scoring system.

Divides all closed picks into 10 deciles by elite score, then measures whether
higher-scored picks genuinely perform better (higher WR, PnL, profit factor).

Uses Spearman rank correlation to quantify monotonicity and produces a clear
STRONG / MODERATE / WEAK / BROKEN verdict.

Sub-segments: direction (LONG/SHORT), asset class, source system.
Stdlib only. Windows UTF-8 safe.
"""

import io
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Windows UTF-8 fix
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
DATA_IN = ROOT / "audit_trail" / "data" / "dashboard_payload.json"
DATA_OUT = ROOT / "alpha_engine" / "data" / "decile_test.json"


# ---------------------------------------------------------------------------
# Stats helpers
# ---------------------------------------------------------------------------

def _safe_div(a, b, default=0.0):
    return a / b if b else default


def compute_decile_stats(picks):
    """Compute WR, avg PnL, profit factor, Sharpe estimate for a list of picks."""
    if not picks:
        return {
            "count": 0, "win_rate": 0.0, "avg_pnl": 0.0,
            "profit_factor": 0.0, "sharpe_estimate": 0.0,
            "score_min": 0.0, "score_max": 0.0, "score_mean": 0.0,
        }

    pnls = [float(p.get("pnl_pct", 0) or 0) for p in picks]
    scores = [float(p.get("score", 0) or 0) for p in picks]
    wins = sum(1 for p in picks if str(p.get("status", "")).upper() == "WON")
    losses = sum(1 for p in picks if str(p.get("status", "")).upper() == "LOST")

    gross_win = sum(pnl for pnl in pnls if pnl > 0)
    gross_loss = abs(sum(pnl for pnl in pnls if pnl < 0))

    avg_pnl = _safe_div(sum(pnls), len(pnls))
    wr = _safe_div(wins, wins + losses) * 100

    # Sharpe estimate: mean / stdev of per-trade PnL
    if len(pnls) >= 2:
        mean_pnl = sum(pnls) / len(pnls)
        var = sum((x - mean_pnl) ** 2 for x in pnls) / (len(pnls) - 1)
        std = math.sqrt(var) if var > 0 else 0.001
        sharpe = mean_pnl / std
    else:
        sharpe = 0.0

    return {
        "count": len(picks),
        "win_rate": round(wr, 2),
        "avg_pnl": round(avg_pnl, 4),
        "profit_factor": round(_safe_div(gross_win, gross_loss), 3),
        "sharpe_estimate": round(sharpe, 4),
        "score_min": round(min(scores), 1),
        "score_max": round(max(scores), 1),
        "score_mean": round(sum(scores) / len(scores), 1),
    }


def spearman_rank_correlation(x, y):
    """Spearman rank correlation between two equal-length sequences."""
    n = len(x)
    if n < 3:
        return 0.0

    def _rank(seq):
        indexed = sorted(enumerate(seq), key=lambda t: t[1])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n - 1 and indexed[j + 1][1] == indexed[j][1]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                ranks[indexed[k][0]] = avg_rank
            i = j + 1
        return ranks

    rx = _rank(x)
    ry = _rank(y)
    d_sq = sum((a - b) ** 2 for a, b in zip(rx, ry))
    return round(1 - (6 * d_sq) / (n * (n * n - 1)), 4)


def check_monotonicity(values):
    """Count how many adjacent pairs increase (monotonicity fraction)."""
    if len(values) < 2:
        return 1.0
    increases = sum(1 for i in range(len(values) - 1) if values[i + 1] > values[i])
    return round(increases / (len(values) - 1), 3)


def classify_verdict(spearman_wr, spearman_pnl, mono_wr, mono_pnl):
    """Produce STRONG / MODERATE / WEAK / BROKEN verdict."""
    avg_sp = (spearman_wr + spearman_pnl) / 2
    avg_mono = (mono_wr + mono_pnl) / 2

    if avg_sp > 0.8 and avg_mono >= 0.7:
        grade = "STRONG"
        desc = "Elite score is a STRONG predictor. Monotonic increase across deciles."
    elif avg_sp > 0.5 and avg_mono >= 0.5:
        grade = "MODERATE"
        desc = "Elite score shows MODERATE predictive power. Mostly increasing across deciles."
    elif avg_sp > 0.2:
        grade = "WEAK"
        desc = "Elite score shows WEAK signal. Some pattern visible but noisy."
    else:
        grade = "BROKEN"
        desc = "Elite score shows NO predictive power. Flat or inverted relationship."

    return grade, desc


# ---------------------------------------------------------------------------
# Core decile analysis
# ---------------------------------------------------------------------------

def run_decile_analysis(picks, label="ALL"):
    """Sort picks by score, split into deciles, compute stats for each."""
    if len(picks) < 10:
        return {
            "label": label, "total_picks": len(picks),
            "deciles": [], "spearman_wr": 0.0, "spearman_pnl": 0.0,
            "monotonicity_wr": 0.0, "monotonicity_pnl": 0.0,
            "verdict": "INSUFFICIENT DATA", "verdict_desc": f"Only {len(picks)} picks, need 10+",
        }

    sorted_picks = sorted(picks, key=lambda p: float(p.get("score", 0) or 0))
    n = len(sorted_picks)
    decile_size = n // 10
    remainder = n % 10

    deciles = []
    idx = 0
    for d in range(10):
        # Distribute remainder picks to the last deciles
        sz = decile_size + (1 if d >= (10 - remainder) else 0)
        chunk = sorted_picks[idx:idx + sz]
        idx += sz
        stats = compute_decile_stats(chunk)
        stats["decile"] = d + 1  # D1 = lowest, D10 = highest
        deciles.append(stats)

    wr_values = [d["win_rate"] for d in deciles]
    pnl_values = [d["avg_pnl"] for d in deciles]
    ranks = list(range(1, 11))

    sp_wr = spearman_rank_correlation(ranks, wr_values)
    sp_pnl = spearman_rank_correlation(ranks, pnl_values)
    mono_wr = check_monotonicity(wr_values)
    mono_pnl = check_monotonicity(pnl_values)

    grade, desc = classify_verdict(sp_wr, sp_pnl, mono_wr, mono_pnl)

    # Q1 vs Q4 comparison (quartile check to match prior analysis)
    q1_picks = sorted_picks[:n // 4]
    q4_picks = sorted_picks[3 * n // 4:]
    q1_stats = compute_decile_stats(q1_picks)
    q4_stats = compute_decile_stats(q4_picks)

    return {
        "label": label,
        "total_picks": len(picks),
        "deciles": deciles,
        "spearman_wr": sp_wr,
        "spearman_pnl": sp_pnl,
        "monotonicity_wr": mono_wr,
        "monotonicity_pnl": mono_pnl,
        "verdict": grade,
        "verdict_desc": desc,
        "quartile_comparison": {
            "Q1_wr": q1_stats["win_rate"],
            "Q4_wr": q4_stats["win_rate"],
            "Q1_avg_pnl": q1_stats["avg_pnl"],
            "Q4_avg_pnl": q4_stats["avg_pnl"],
            "Q4_minus_Q1_wr": round(q4_stats["win_rate"] - q1_stats["win_rate"], 2),
            "Q4_minus_Q1_pnl": round(q4_stats["avg_pnl"] - q1_stats["avg_pnl"], 4),
        },
    }


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def print_decile_table(analysis):
    """Print a formatted decile table with visual bars."""
    label = analysis["label"]
    deciles = analysis.get("deciles", [])
    if not deciles:
        print(f"\n  [{label}] -- {analysis.get('verdict_desc', 'no data')}")
        return

    print(f"\n{'='*80}")
    print(f"  DECILE SEPARATION TEST: {label}  ({analysis['total_picks']} picks)")
    print(f"{'='*80}")
    print(f"  {'Decile':>6}  {'Score':>12}  {'Trades':>6}  {'WR%':>7}  {'AvgPnL':>8}  {'PF':>6}  {'Sharpe':>7}  Bar")
    print(f"  {'-'*6}  {'-'*12}  {'-'*6}  {'-'*7}  {'-'*8}  {'-'*6}  {'-'*7}  {'-'*20}")

    max_wr = max(d["win_rate"] for d in deciles) if deciles else 1

    for d in deciles:
        score_range = f"{d['score_min']:.0f}-{d['score_max']:.0f}"
        bar_len = int(d["win_rate"] / max(max_wr, 1) * 20) if max_wr > 0 else 0
        bar = "#" * bar_len
        pnl_str = f"{d['avg_pnl']:+.3f}" if d['avg_pnl'] != 0 else " 0.000"
        print(f"  D{d['decile']:>4}  {score_range:>12}  {d['count']:>6}  {d['win_rate']:>6.1f}%  {pnl_str:>8}  {d['profit_factor']:>6.2f}  {d['sharpe_estimate']:>+7.3f}  {bar}")

    print()
    qc = analysis.get("quartile_comparison", {})
    print(f"  Quartile gap:  Q4 WR={qc.get('Q4_wr',0):.1f}% vs Q1 WR={qc.get('Q1_wr',0):.1f}%  (delta={qc.get('Q4_minus_Q1_wr',0):+.1f}pp)")
    print(f"  Quartile gap:  Q4 PnL={qc.get('Q4_avg_pnl',0):+.4f}% vs Q1 PnL={qc.get('Q1_avg_pnl',0):+.4f}%")
    print()
    print(f"  Spearman(rank, WR):  {analysis['spearman_wr']:+.4f}   Monotonicity WR:  {analysis['monotonicity_wr']:.3f}")
    print(f"  Spearman(rank, PnL): {analysis['spearman_pnl']:+.4f}   Monotonicity PnL: {analysis['monotonicity_pnl']:.3f}")
    print()
    verdict_char = {"STRONG": "+", "MODERATE": "~", "WEAK": "!", "BROKEN": "X"}.get(analysis["verdict"], "?")
    print(f"  [{verdict_char}] VERDICT: {analysis['verdict']} -- {analysis['verdict_desc']}")
    print()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run():
    print("\n  Decile Separation Test v1.0")
    print(f"  Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

    # ---- Load data ----
    if not DATA_IN.exists():
        print(f"  ERROR: {DATA_IN} not found")
        return

    with open(DATA_IN, "r", encoding="utf-8") as f:
        payload = json.load(f)

    # Get closed picks
    closed = payload.get("picks", {}).get("recent_closed", [])
    if not closed:
        print("  ERROR: No recent_closed picks found in payload")
        return

    # Filter to picks that have score and valid outcome
    valid_statuses = {"WON", "LOST"}
    picks = [
        p for p in closed
        if p.get("score") is not None
        and str(p.get("status", "")).upper() in valid_statuses
        and p.get("pnl_pct") is not None
    ]
    print(f"  Loaded {len(closed)} closed picks, {len(picks)} with score + WON/LOST status")

    if len(picks) < 10:
        print("  ERROR: Not enough scored picks for decile analysis (need 10+)")
        return

    # ---- Overall analysis ----
    overall = run_decile_analysis(picks, "ALL PICKS")
    print_decile_table(overall)

    results = {"overall": overall, "segments": {}}

    # ---- By direction ----
    for direction in ("LONG", "SHORT"):
        seg = [p for p in picks if str(p.get("direction", "")).upper() == direction]
        if len(seg) >= 10:
            analysis = run_decile_analysis(seg, f"DIRECTION: {direction}")
            print_decile_table(analysis)
            results["segments"][f"direction_{direction}"] = analysis

    # ---- By asset class ----
    asset_classes = set(str(p.get("asset_class", "UNKNOWN")).upper() for p in picks)
    for ac in sorted(asset_classes):
        seg = [p for p in picks if str(p.get("asset_class", "UNKNOWN")).upper() == ac]
        if len(seg) >= 10:
            analysis = run_decile_analysis(seg, f"ASSET CLASS: {ac}")
            print_decile_table(analysis)
            results["segments"][f"asset_{ac}"] = analysis

    # ---- By source system ----
    source_buckets = {}
    for p in picks:
        src = str(p.get("source_system", "unknown") or "unknown").lower()
        # Normalize to major buckets
        if "alpha" in src:
            bucket = "alpha_engine"
        elif "copy_trader" in src or "clone" in src:
            bucket = "copy_trader"
        elif "kimi" in src:
            bucket = "kimi"
        elif "baby_strats" in src:
            bucket = "baby_strats"
        elif "battleground" in src:
            bucket = "battleground"
        elif "mercury" in src:
            bucket = "mercury"
        else:
            bucket = "other"
        source_buckets.setdefault(bucket, []).append(p)

    for bucket, seg in sorted(source_buckets.items()):
        if len(seg) >= 10:
            analysis = run_decile_analysis(seg, f"SOURCE: {bucket}")
            print_decile_table(analysis)
            results["segments"][f"source_{bucket}"] = analysis

    # ---- Cross-validation vs known numbers ----
    print(f"{'='*80}")
    print("  CROSS-VALIDATION vs Known Benchmarks")
    print(f"{'='*80}")
    qc = overall.get("quartile_comparison", {})
    known_q4_wr = 75.3
    known_q1_wr = 50.7
    actual_q4_wr = qc.get("Q4_wr", 0)
    actual_q1_wr = qc.get("Q1_wr", 0)
    print(f"  Prior analysis:  Q4 WR={known_q4_wr}%, Q1 WR={known_q1_wr}%  (winner_predictor)")
    print(f"  This test:       Q4 WR={actual_q4_wr}%, Q1 WR={actual_q1_wr}%")
    print(f"  Delta from prior: Q4 {actual_q4_wr - known_q4_wr:+.1f}pp,  Q1 {actual_q1_wr - known_q1_wr:+.1f}pp")
    print()

    # Score-PnL correlation
    all_scores = [float(p.get("score", 0) or 0) for p in picks]
    all_pnls = [float(p.get("pnl_pct", 0) or 0) for p in picks]
    r_score_pnl = spearman_rank_correlation(all_scores, all_pnls)
    print(f"  Prior Score-PnL correlation: r=0.0425 (check_active_picks)")
    print(f"  This test (Spearman):        r={r_score_pnl:.4f}")
    print()

    # ---- Actionable recommendations ----
    print(f"{'='*80}")
    print("  ACTIONABLE RECOMMENDATIONS")
    print(f"{'='*80}")
    if overall["verdict"] == "STRONG":
        print("  [+] Score system is working well. Consider tightening thresholds.")
        print("      - Raise minimum score for auto-trade from current level")
        print("      - Weight position sizing by score decile")
    elif overall["verdict"] == "MODERATE":
        print("  [~] Score system has signal but room for improvement.")
        print("      - Investigate which score components drive D10 vs D1 gap")
        print("      - Consider adding/reweighting weak components")
    elif overall["verdict"] == "WEAK":
        print("  [!] Score system has marginal predictive power.")
        print("      - Audit score components for noise contributors")
        print("      - Test removing components one at a time")
        print("      - May need ML-based recalibration")
    else:
        print("  [X] Score system is NOT predictive. Major overhaul needed.")
        print("      - Score is not separating winners from losers")
        print("      - Consider rebuilding from scratch with forward-validated features")
    print()

    # ---- Save JSON ----
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "test": "Decile Separation Test v1.0",
        "total_picks_analyzed": len(picks),
        "overall": overall,
        "segments": results["segments"],
        "cross_validation": {
            "prior_Q4_wr": known_q4_wr,
            "prior_Q1_wr": known_q1_wr,
            "actual_Q4_wr": actual_q4_wr,
            "actual_Q1_wr": actual_q1_wr,
            "prior_score_pnl_r": 0.0425,
            "actual_score_pnl_spearman": r_score_pnl,
        },
    }

    DATA_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_OUT, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"  Results saved to: {DATA_OUT}")
    print()


if __name__ == "__main__":
    run()
