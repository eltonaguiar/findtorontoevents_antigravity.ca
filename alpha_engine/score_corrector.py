#!/usr/bin/env python3
"""
Score Corrector — Detects and fixes scoring inversions
======================================================
Reads closed trade data to find where low-score picks outperform high-score
picks. Generates correction maps (global + per-strategy) so that future
scoring is calibrated to real-world outcomes.

Usage:
    python -m alpha_engine.score_corrector          # standalone
    python alpha_engine/score_corrector.py          # from repo root

Called automatically from production_scanner.py each cycle.
"""
from __future__ import annotations

import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ── Windows UTF-8 fix ─────────────────────────────────────────────────────
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DATA_DIR = Path(__file__).resolve().parent / "data"

# Score buckets: (low_inclusive, high_exclusive)
BUCKETS = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 101)]
BUCKET_LABELS = {(0, 20): "0-19", (20, 40): "20-39", (40, 60): "40-59",
                 (60, 80): "60-79", (80, 101): "80-100"}

# Minimum trades in a bucket before we trust the stats
MIN_TRADES_FOR_CORRECTION = 5
MIN_TRADES_PER_STRATEGY = 8


def _safe_json_load(path: Path) -> list | dict:
    """Load JSON, returning [] or {} on failure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _get_score(trade: dict) -> float | None:
    """Extract score from a trade record (different sources use different keys)."""
    for key in ("score", "dashboard_score", "ml_score", "confidence"):
        val = trade.get(key)
        if val is not None:
            s = float(val)
            # confidence/ml_score are 0-1, scale to 0-100
            if key in ("confidence", "ml_score") and 0 < s <= 1.0:
                s *= 100
            return s
    return None


def _is_win(trade: dict) -> bool | None:
    """Determine if trade was a win. Returns None if indeterminate."""
    status = (trade.get("status") or "").upper()
    if status in ("WON", "WIN", "TP_HIT"):
        return True
    if status in ("LOST", "LOSS", "SL_HIT"):
        return False
    # Portfolio closed_positions use close_reason
    reason = (trade.get("close_reason") or "").upper()
    if "TP" in reason:
        return True
    if "SL" in reason:
        return False
    # Fall back to pnl_pct
    pnl = trade.get("pnl_pct")
    if pnl is not None:
        return pnl > 0
    return None


def _get_pnl(trade: dict) -> float:
    """Get pnl_pct, normalizing to fractional (e.g. 0.03 = 3%)."""
    pnl = trade.get("pnl_pct", 0) or 0
    # Some sources store as percentage already (>1 or <-1)
    if abs(pnl) > 5:  # Clearly stored as percentage (e.g. -18.6)
        pnl /= 100
    return pnl


def _bucket_for_score(score: float) -> tuple[int, int] | None:
    for lo, hi in BUCKETS:
        if lo <= score < hi:
            return (lo, hi)
    return None


# ─── Core: Collect all closed trades ──────────────────────────────────────

def collect_closed_trades() -> list[dict]:
    """Gather closed trades from all data sources, normalized."""
    trades = []

    # 1. closed_picks.json (backtest + forward validated)
    closed = _safe_json_load(DATA_DIR / "closed_picks.json")
    if isinstance(closed, list):
        for t in closed:
            score = _get_score(t)
            win = _is_win(t)
            if score is None or win is None:
                continue
            trades.append({
                "source": "closed_picks",
                "symbol": t.get("symbol", "?"),
                "strategy": t.get("strategy", "unknown"),
                "score": score,
                "win": win,
                "pnl_pct": _get_pnl(t),
            })

    # 2. portfolio_1x.json closed_positions
    p1x = _safe_json_load(DATA_DIR / "portfolio_1x.json")
    if isinstance(p1x, dict):
        for t in p1x.get("closed_positions", []):
            score = _get_score(t)
            win = _is_win(t)
            if score is None or win is None:
                continue
            trades.append({
                "source": "portfolio_1x",
                "symbol": t.get("symbol", "?"),
                "strategy": t.get("strategy", "unknown"),
                "score": score,
                "win": win,
                "pnl_pct": _get_pnl(t),
            })

    # 3. portfolio_copytrader.json closed_positions
    pct = _safe_json_load(DATA_DIR / "portfolio_copytrader.json")
    if isinstance(pct, dict):
        for t in pct.get("closed_positions", []):
            score = _get_score(t)
            win = _is_win(t)
            if score is None or win is None:
                continue
            trades.append({
                "source": "portfolio_copytrader",
                "symbol": t.get("symbol", "?"),
                "strategy": t.get("strategy", "unknown"),
                "score": score,
                "win": win,
                "pnl_pct": _get_pnl(t),
            })

    # 4. portfolio_20x.json closed_positions
    p20 = _safe_json_load(DATA_DIR / "portfolio_20x.json")
    if isinstance(p20, dict):
        for t in p20.get("closed_positions", []):
            score = _get_score(t)
            win = _is_win(t)
            if score is None or win is None:
                continue
            trades.append({
                "source": "portfolio_20x",
                "symbol": t.get("symbol", "?"),
                "strategy": t.get("strategy", "unknown"),
                "score": score,
                "win": win,
                "pnl_pct": _get_pnl(t),
            })

    return trades


# ─── Bucket Analysis ─────────────────────────────────────────────────────

def compute_bucket_stats(trades: list[dict]) -> dict:
    """Compute win rate and avg PnL per score bucket."""
    buckets = {b: {"trades": 0, "wins": 0, "total_pnl": 0.0, "pnls": []}
               for b in BUCKETS}

    for t in trades:
        b = _bucket_for_score(t["score"])
        if b is None:
            continue
        buckets[b]["trades"] += 1
        if t["win"]:
            buckets[b]["wins"] += 1
        buckets[b]["total_pnl"] += t["pnl_pct"]
        buckets[b]["pnls"].append(t["pnl_pct"])

    result = {}
    for b in BUCKETS:
        info = buckets[b]
        n = info["trades"]
        label = BUCKET_LABELS[b]
        wr = (info["wins"] / n * 100) if n > 0 else 0
        avg_pnl = (info["total_pnl"] / n) if n > 0 else 0
        result[label] = {
            "bucket": list(b),
            "trades": n,
            "wins": info["wins"],
            "losses": n - info["wins"],
            "win_rate": round(wr, 1),
            "avg_pnl_pct": round(avg_pnl * 100, 2),  # as percentage
            "total_pnl_pct": round(info["total_pnl"] * 100, 2),
        }
    return result


# ─── Inversion Detection ─────────────────────────────────────────────────

def detect_inversions(bucket_stats: dict) -> list[dict]:
    """Find score inversions: lower-score buckets outperforming higher ones."""
    inversions = []
    labels = list(bucket_stats.keys())

    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            lo_label = labels[i]
            hi_label = labels[j]
            lo = bucket_stats[lo_label]
            hi = bucket_stats[hi_label]

            # Need minimum trades in both buckets
            if lo["trades"] < MIN_TRADES_FOR_CORRECTION or hi["trades"] < MIN_TRADES_FOR_CORRECTION:
                continue

            # Inversion: lower-score bucket has higher win rate
            if lo["win_rate"] > hi["win_rate"] + 5:  # 5% margin to avoid noise
                inversions.append({
                    "type": "win_rate_inversion",
                    "lower_bucket": lo_label,
                    "higher_bucket": hi_label,
                    "lower_wr": lo["win_rate"],
                    "higher_wr": hi["win_rate"],
                    "delta": round(lo["win_rate"] - hi["win_rate"], 1),
                    "severity": "HIGH" if lo["win_rate"] - hi["win_rate"] > 15 else "MEDIUM",
                })

            # Inversion: lower-score bucket has better avg PnL
            if lo["avg_pnl_pct"] > hi["avg_pnl_pct"] + 0.5:
                inversions.append({
                    "type": "pnl_inversion",
                    "lower_bucket": lo_label,
                    "higher_bucket": hi_label,
                    "lower_avg_pnl": lo["avg_pnl_pct"],
                    "higher_avg_pnl": hi["avg_pnl_pct"],
                    "delta": round(lo["avg_pnl_pct"] - hi["avg_pnl_pct"], 2),
                    "severity": "HIGH" if lo["avg_pnl_pct"] - hi["avg_pnl_pct"] > 2 else "MEDIUM",
                })

    return inversions


# ─── Correction Map ──────────────────────────────────────────────────────

def generate_correction_map(bucket_stats: dict) -> dict:
    """
    Generate score corrections per bucket.

    Logic: compute "expected" WR for each bucket (linear from 0-100 mapping
    to 30-70% WR). If actual WR deviates, apply proportional correction.
    """
    correction_map = {}

    # Compute overall average WR to use as baseline
    total_trades = sum(b["trades"] for b in bucket_stats.values())
    total_wins = sum(b["wins"] for b in bucket_stats.values())
    baseline_wr = (total_wins / total_trades * 100) if total_trades > 0 else 50

    for label, stats in bucket_stats.items():
        if stats["trades"] < MIN_TRADES_FOR_CORRECTION:
            correction_map[label] = {
                "adjustment": 0,
                "reason": f"insufficient data ({stats['trades']} trades, need {MIN_TRADES_FOR_CORRECTION})",
                "confidence": "LOW",
            }
            continue

        bucket_mid = (stats["bucket"][0] + stats["bucket"][1]) / 2
        # Expected WR: linearly scale from baseline-15 to baseline+15
        expected_wr = baseline_wr + (bucket_mid - 50) * 0.3
        actual_wr = stats["win_rate"]
        deviation = actual_wr - expected_wr

        # Correction: if actual WR is higher than expected, boost score; if lower, penalize
        # Scale: 10% WR deviation = ~8 point score adjustment, capped at +/-20
        adjustment = round(max(-20, min(20, deviation * 0.8)), 1)

        confidence = "HIGH" if stats["trades"] >= 20 else "MEDIUM"

        correction_map[label] = {
            "adjustment": adjustment,
            "expected_wr": round(expected_wr, 1),
            "actual_wr": actual_wr,
            "deviation": round(deviation, 1),
            "reason": (
                f"WR {actual_wr:.0f}% vs expected {expected_wr:.0f}% "
                f"({'outperforming' if deviation > 0 else 'underperforming'})"
            ),
            "confidence": confidence,
            "trades_sampled": stats["trades"],
        }

    return correction_map


# ─── Per-Strategy Corrections ────────────────────────────────────────────

def compute_strategy_corrections(trades: list[dict]) -> dict:
    """Compute per-strategy score adjustments."""
    strat_stats = defaultdict(lambda: {"trades": 0, "wins": 0, "total_pnl": 0.0,
                                        "scores": [], "pnls": []})
    for t in trades:
        s = t["strategy"]
        strat_stats[s]["trades"] += 1
        if t["win"]:
            strat_stats[s]["wins"] += 1
        strat_stats[s]["total_pnl"] += t["pnl_pct"]
        strat_stats[s]["scores"].append(t["score"])
        strat_stats[s]["pnls"].append(t["pnl_pct"])

    # Overall baseline
    total_t = sum(v["trades"] for v in strat_stats.values())
    total_w = sum(v["wins"] for v in strat_stats.values())
    baseline_wr = (total_w / total_t * 100) if total_t > 0 else 50

    corrections = {}
    for strat, info in strat_stats.items():
        if info["trades"] < MIN_TRADES_PER_STRATEGY:
            continue

        wr = info["wins"] / info["trades"] * 100
        avg_score = sum(info["scores"]) / len(info["scores"])
        avg_pnl = info["total_pnl"] / info["trades"]

        # Deviation from baseline
        wr_deviation = wr - baseline_wr

        # Compute adjustment: if strategy's WR deviates significantly
        adjustment = round(max(-15, min(15, wr_deviation * 0.6)), 1)

        # Detect "inflated scores" — high avg score but low WR
        inflated = avg_score > 65 and wr < baseline_wr - 5
        deflated = avg_score < 45 and wr > baseline_wr + 5

        corrections[strat] = {
            "trades": info["trades"],
            "wins": info["wins"],
            "win_rate": round(wr, 1),
            "avg_score": round(avg_score, 1),
            "avg_pnl_pct": round(avg_pnl * 100, 2),
            "adjustment": adjustment,
            "inflated": inflated,
            "deflated": deflated,
            "flag": ("INFLATED_SCORE" if inflated else
                     "DEFLATED_SCORE" if deflated else "OK"),
        }

    return corrections


# ─── Apply Correction ────────────────────────────────────────────────────

def load_corrections() -> dict:
    """Load saved correction data."""
    path = DATA_DIR / "score_corrections.json"
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def correct_score(pick: dict, corrections: dict | None = None) -> float:
    """
    Apply score correction to a pick.

    Args:
        pick: A pick/trade dict with 'score' and 'strategy' keys
        corrections: Pre-loaded corrections dict (loads from file if None)

    Returns:
        Corrected score (clamped to 1-100)
    """
    if corrections is None:
        corrections = load_corrections()

    original_score = _get_score(pick)
    if original_score is None:
        return 50.0  # default

    score = original_score

    # 1. Apply bucket-level correction
    bucket_map = corrections.get("correction_map", {})
    bucket = _bucket_for_score(score)
    if bucket:
        label = BUCKET_LABELS.get(bucket)
        if label and label in bucket_map:
            adj = bucket_map[label].get("adjustment", 0)
            if bucket_map[label].get("confidence") != "LOW":
                score += adj

    # 2. Apply strategy-level correction
    strategy = pick.get("strategy", "")
    strat_map = corrections.get("strategy_corrections", {})
    if strategy in strat_map:
        adj = strat_map[strategy].get("adjustment", 0)
        score += adj

    # Clamp to 1-100
    score = max(1, min(100, round(score, 1)))
    return score


# ─── Save & Report ───────────────────────────────────────────────────────

def save_corrections(result: dict):
    """Save correction data to JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / "score_corrections.json"

    # Sanitize NaN/Inf
    def _sanitize(obj):
        if isinstance(obj, dict):
            return {k: _sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_sanitize(v) for v in obj]
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        return obj

    with open(path, "w", encoding="utf-8") as f:
        json.dump(_sanitize(result), f, indent=2)
    print(f"  Saved score corrections to {path}")


def print_report(result: dict):
    """Print a human-readable correction report."""
    print()
    print("=" * 60)
    print("  SCORE CORRECTOR - Calibration Report")
    print("=" * 60)

    bs = result.get("bucket_stats", {})
    print(f"\n  Total closed trades analyzed: {result.get('total_trades', 0)}")
    print(f"\n  {'Bucket':<10} {'Trades':>7} {'Wins':>6} {'WR%':>7} {'AvgPnL':>8}")
    print(f"  {'-'*10} {'-'*7} {'-'*6} {'-'*7} {'-'*8}")
    for label in ["0-19", "20-39", "40-59", "60-79", "80-100"]:
        if label in bs:
            b = bs[label]
            print(f"  {label:<10} {b['trades']:>7} {b['wins']:>6} "
                  f"{b['win_rate']:>6.1f}% {b['avg_pnl_pct']:>+7.2f}%")

    inv = result.get("inversions", [])
    if inv:
        print(f"\n  INVERSIONS DETECTED: {len(inv)}")
        for i in inv:
            print(f"    [{i['severity']}] {i['type']}: "
                  f"{i['lower_bucket']} > {i['higher_bucket']} "
                  f"(delta: {i.get('delta', '?')})")
    else:
        print("\n  No inversions detected (scoring appears calibrated)")

    cm = result.get("correction_map", {})
    print(f"\n  Score Corrections:")
    for label in ["0-19", "20-39", "40-59", "60-79", "80-100"]:
        if label in cm:
            c = cm[label]
            adj = c["adjustment"]
            marker = " <<" if abs(adj) >= 8 else ""
            print(f"    {label:<10} {adj:>+6.1f} pts  ({c.get('reason', '')}){marker}")

    sc = result.get("strategy_corrections", {})
    flagged = {k: v for k, v in sc.items() if v.get("flag") != "OK"}
    if flagged:
        print(f"\n  Flagged Strategies ({len(flagged)}):")
        for name, info in sorted(flagged.items(), key=lambda x: x[1]["adjustment"]):
            print(f"    {name[:40]:<40s} WR={info['win_rate']:>5.1f}%  "
                  f"adj={info['adjustment']:>+5.1f}  [{info['flag']}]")

    top_strats = sorted(sc.items(), key=lambda x: x[1].get("win_rate", 0), reverse=True)[:5]
    if top_strats:
        print(f"\n  Top 5 Strategies by WR:")
        for name, info in top_strats:
            print(f"    {name[:40]:<40s} WR={info['win_rate']:>5.1f}%  "
                  f"trades={info['trades']}  avg_pnl={info['avg_pnl_pct']:>+.2f}%")

    print("=" * 60)


# ─── Main ─────────────────────────────────────────────────────────────────

def run_score_correction() -> dict:
    """Run the full score correction pipeline. Returns the result dict."""
    print("\n[SCORE CORRECTOR] Analyzing closed trades for scoring inversions...")

    trades = collect_closed_trades()
    if not trades:
        print("  No closed trades found -- skipping score correction")
        return {}

    print(f"  Collected {len(trades)} closed trades from all sources")

    bucket_stats = compute_bucket_stats(trades)
    inversions = detect_inversions(bucket_stats)
    correction_map = generate_correction_map(bucket_stats)
    strategy_corrections = compute_strategy_corrections(trades)

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_trades": len(trades),
        "bucket_stats": bucket_stats,
        "inversions": inversions,
        "correction_map": correction_map,
        "strategy_corrections": strategy_corrections,
    }

    save_corrections(result)
    print_report(result)

    return result


if __name__ == "__main__":
    run_score_correction()
