"""
scoring_ab_test.py — A/B/C test for alternative pick-scoring methods.

Loads active and closed picks, scores each pick 3 ways, and compares
how well each method separates winners from losers.

Usage:
    python -m alpha_engine.scoring_ab_test
    python alpha_engine/scoring_ab_test.py
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
_DATA = _HERE / "data"
_ACTIVE_PATH = _DATA / "active_picks.json"
_CLOSED_PATH = _DATA / "closed_picks.json"
_RESULTS_PATH = _DATA / "scoring_ab_results.json"

# Allow importing elite_scorer from same package
sys.path.insert(0, str(_HERE.parent))

from alpha_engine.elite_scorer import compute_elite_score, compute_method_c_score  # noqa: E402

# ---------------------------------------------------------------------------
# Proven strategies for Method C
# ---------------------------------------------------------------------------
PROVEN_LIST = [
    "keltner_compression_btc",
    "keltner_compression_sol",
    "rsi5_momentum_btc",
    "funding_rate_carry",
    "copy_hl_",
    "hs_NMTD",
]


def _load_json(path: Path) -> list:
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Scoring methods
# ---------------------------------------------------------------------------

def score_method_a(pick: dict) -> float:
    """Method A — current elite_scorer."""
    try:
        result = compute_elite_score(pick)
        return float(result.get("elite_score", 0))
    except Exception:
        return 0.0


def score_method_b(pick: dict) -> float:
    """Method B — simplified weighted formula."""
    confidence = float(pick.get("confidence", 0) or 0)
    forward_wr = float(pick.get("forward_wr", 0) or 0)
    forward_trades = int(pick.get("forward_trades", 0) or 0)

    # risk/reward ratio from TP/SL
    entry = float(pick.get("entry_price", 0) or 0)
    tp = float(pick.get("take_profit", 0) or 0)
    sl = float(pick.get("stop_loss", 0) or 0)
    if entry and sl and abs(entry - sl) > 0:
        rr = abs(tp - entry) / abs(entry - sl)
    else:
        rr = 1.0
    risk_reward_pts = min(1.0, rr / 3.0)

    regime = str(pick.get("regime_at_entry", "") or "").lower()
    if "trend" in regime:
        regime_bonus = 1.0
    elif "bear" in regime or "crash" in regime:
        regime_bonus = 0.0
    else:
        regime_bonus = 0.5

    forward_component = (forward_wr * 30) if forward_trades >= 5 else 0
    score = (confidence * 30) + forward_component + (risk_reward_pts * 20) + (regime_bonus * 20)
    return round(score, 2)


def score_method_c(pick: dict) -> float:
    """Method C — ML-first scoring (production compute_method_c_score)."""
    try:
        result = compute_method_c_score(pick)
        return float(result.get("ml_composite_score", 0))
    except Exception:
        # Fallback to original heuristic if production scorer fails
        ml_score = float(pick.get("ml_score", 0) or 0)
        strategy = str(pick.get("strategy", "") or "")
        proven_match = any(p in strategy for p in PROVEN_LIST)
        volume_ratio = float(pick.get("volume_ratio", 0) or 0)
        score = (ml_score * 50) + (30 if proven_match else 0) + (20 if volume_ratio > 1.5 else 0)
        return round(score, 2)


# ---------------------------------------------------------------------------
# Stats computation
# ---------------------------------------------------------------------------

def _compute_bucket_stats(scored_picks: list[tuple[float, dict]]) -> dict:
    """Given list of (score, pick) sorted desc, compute top/bottom 20% stats."""
    n = len(scored_picks)
    if n < 5:
        return {
            "top20_wr": 0, "top20_avg_pnl": 0, "top20_pf": 0,
            "bot20_wr": 0, "separation": 0, "sample_size": n,
        }

    top_n = max(1, n // 5)
    bot_n = max(1, n // 5)

    top_picks = [p for _, p in scored_picks[:top_n]]
    bot_picks = [p for _, p in scored_picks[-bot_n:]]

    def _bucket_stats(picks):
        pnls = []
        wins = 0
        for p in picks:
            pnl = float(p.get("pnl_pct", 0) or 0)
            pnls.append(pnl)
            if pnl > 0:
                wins += 1
        wr = wins / len(picks) if picks else 0
        avg_pnl = sum(pnls) / len(pnls) if pnls else 0
        gross_profit = sum(p for p in pnls if p > 0)
        gross_loss = abs(sum(p for p in pnls if p < 0))
        pf = gross_profit / gross_loss if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)
        return wr, avg_pnl, pf

    top_wr, top_pnl, top_pf = _bucket_stats(top_picks)
    bot_wr, _, _ = _bucket_stats(bot_picks)
    separation = top_wr - bot_wr

    return {
        "top20_wr": round(top_wr * 100, 1),
        "top20_avg_pnl": round(top_pnl * 100, 2),
        "top20_pf": round(top_pf, 2),
        "bot20_wr": round(bot_wr * 100, 1),
        "separation": round(separation * 100, 1),
        "sample_size": n,
        "top_n": top_n,
        "bot_n": bot_n,
    }


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_ab_test() -> dict:
    """Run the A/B/C scoring comparison and return results dict."""
    active = _load_json(_ACTIVE_PATH)
    closed = _load_json(_CLOSED_PATH)

    print(f"Loaded {len(active)} active picks, {len(closed)} closed picks")

    if not closed:
        print("No closed picks — nothing to compare.")
        return {}

    # Score every closed pick with all 3 methods
    methods = {
        "A (Current Elite)": score_method_a,
        "B (Simplified)": score_method_b,
        "C (ML-First)": score_method_c,
    }

    results = {}
    for name, scorer in methods.items():
        scored = []
        for pick in closed:
            s = scorer(pick)
            scored.append((s, pick))
        # Sort descending by score
        scored.sort(key=lambda x: x[0], reverse=True)
        stats = _compute_bucket_stats(scored)
        results[name] = stats

    # Save to JSON
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "closed_picks_count": len(closed),
        "active_picks_count": len(active),
        "methods": results,
    }
    _DATA.mkdir(parents=True, exist_ok=True)
    with open(_RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {_RESULTS_PATH}")

    return output


def print_table(output: dict) -> None:
    """Print a formatted comparison table."""
    if not output or "methods" not in output:
        return

    print(f"\nScoring A/B/C Test — {output['closed_picks_count']} closed picks")
    print(f"Timestamp: {output['timestamp']}")
    print()
    header = f"{'Method':<22} | {'Top20% WR':>9} | {'Top20% PnL':>10} | {'Top20% PF':>9} | {'Bot20% WR':>9} | {'Separation':>10}"
    print(header)
    print("-" * len(header))

    for name, stats in output["methods"].items():
        wr = f"{stats['top20_wr']:.0f}%"
        pnl = f"{stats['top20_avg_pnl']:+.2f}%"
        pf = f"{stats['top20_pf']:.2f}"
        bwr = f"{stats['bot20_wr']:.0f}%"
        sep = f"{stats['separation']:.0f}%"
        print(f"{name:<22} | {wr:>9} | {pnl:>10} | {pf:>9} | {bwr:>9} | {sep:>10}")

    # Identify best method by separation
    best = max(output["methods"].items(), key=lambda x: x[1]["separation"])
    print(f"\nBest discrimination: {best[0]} (separation = {best[1]['separation']:.0f}%)")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    result = run_ab_test()
    print_table(result)
