"""
MFE/MAE Analyzer - Maximum Favorable/Adverse Excursion analysis for TP/SL optimization.

MFE = how far price moved IN YOUR FAVOR before the trade closed
MAE = how far price moved AGAINST YOU before the trade closed

By analyzing MFE/MAE distributions across closed trades, we derive optimal TP/SL
that maximize profit capture while minimizing premature stops.

Usage:
    python mfe_mae_analyzer.py                              # analyze closed_picks.json
    python mfe_mae_analyzer.py --path data/closed_picks.json  # custom path

stdlib only.
"""

import json
import math
import os
import sys
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Asset class caps (same as tp_sl_filler.py for consistency)
# ---------------------------------------------------------------------------

ASSET_CAPS = {
    "crypto":    (15.0, 8.0),
    "forex":     (1.0, 0.5),
    "equity":    (5.0, 3.0),
    "commodity": (5.0, 3.0),
    "stock":     (5.0, 3.0),
    "etf":       (5.0, 3.0),
    "bond":      (2.0, 1.0),
    "futures":   (8.0, 5.0),
    "on-chain":  (15.0, 8.0),
}

# Minimum trades for strategy-specific MFE/MAE to be used
MIN_STRATEGY_TRADES = 10

# Default ATR pct by category (fallback for approximation)
DEFAULT_ATR_PCT = {
    "crypto":    3.0,
    "forex":     0.3,
    "equity":    1.5,
    "stock":     1.5,
    "etf":       1.0,
    "commodity": 2.0,
    "bond":      0.5,
    "futures":   2.5,
    "on-chain":  3.0,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _median(values):
    """Compute median of a sorted-able list. Returns 0.0 if empty."""
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2.0


def _percentile(values, pct):
    """Compute percentile (0-100) of a list. Returns 0.0 if empty."""
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    k = (pct / 100.0) * (n - 1)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] * (c - k) + s[c] * (k - f)


def _normalize_category(cat):
    """Normalize category string to a standard key."""
    cat = (cat or "crypto").lower().strip()
    # Map variants to standard keys
    mapping = {
        "on-chain": "crypto",
        "onchain": "crypto",
        "stock": "equity",
        "etf": "equity",
        "bond": "equity",
        "futures": "commodity",
    }
    return mapping.get(cat, cat)


def _infer_direction(pick):
    """Infer trade direction from pick fields."""
    direction = pick.get("direction", "").upper()
    if direction in ("LONG", "SHORT"):
        return direction
    sig = pick.get("signal_type", "BUY").upper()
    return "SHORT" if sig == "SELL" else "LONG"


# ---------------------------------------------------------------------------
# Core: compute MFE/MAE for each closed pick
# ---------------------------------------------------------------------------

def compute_mfe_mae(closed_picks):
    """
    For each closed pick, compute MFE and MAE as percentages of entry price.

    Returns list of dicts with original pick data plus:
        mfe_pct, mae_pct, pnl_pct, strategy, category, direction, is_winner
    """
    results = []

    for pick in closed_picks:
        entry = pick.get("entry_price", 0)
        if not entry or entry <= 0:
            continue

        exit_price = pick.get("exit_price", 0)
        pnl_pct = pick.get("pnl_pct", 0) or 0
        status = pick.get("status", "").upper()
        direction = _infer_direction(pick)
        category = pick.get("category", "crypto")
        strategy = pick.get("strategy", "unknown")
        exit_reason = pick.get("exit_reason", "")
        hold_days = pick.get("hold_days", 0) or 0

        # Determine if winner
        is_winner = status == "WON" or pnl_pct > 0

        # Get ATR at entry for approximation (many picks have this)
        atr_at_entry = pick.get("atr_at_entry")
        if atr_at_entry and atr_at_entry > 0:
            atr_pct = (atr_at_entry / entry) * 100.0
        else:
            # Fallback to category default
            norm_cat = _normalize_category(category)
            atr_pct = DEFAULT_ATR_PCT.get(norm_cat, 3.0)

        # high_water_mark: the peak favorable price during hold
        # In our data, this seems to be entry price itself (not very useful),
        # so we rely on approximation logic below.
        hwm = pick.get("high_water_mark", 0)

        # Compute MFE and MAE
        # We have: entry_price, exit_price, pnl_pct, atr_at_entry, hold_days
        # We do NOT have intra-trade high/low for most picks.

        tp = pick.get("take_profit", 0)
        sl = pick.get("stop_loss", 0)

        if is_winner:
            # Winner: MFE >= pnl_pct (price reached at least exit_price)
            if exit_reason == "TP_HIT" and tp and tp > 0:
                # TP was hit, so price reached TP level
                if direction == "LONG":
                    mfe_pct = max(((tp - entry) / entry) * 100.0, abs(pnl_pct) * 100.0)
                else:
                    mfe_pct = max(((entry - tp) / entry) * 100.0, abs(pnl_pct) * 100.0)
            else:
                # Not TP hit (trailing stop, time expiry) - MFE likely exceeded pnl
                # Approximate: MFE = pnl + some extra based on hold time
                extra = atr_pct * max(hold_days, 0.5) * 0.2
                mfe_pct = abs(pnl_pct) * 100.0 + extra

            # MAE for winners: approximated as fraction of ATR * hold time
            # Winners that hit TP quickly had small MAE
            mae_pct = atr_pct * max(hold_days, 0.5) * 0.3

        else:
            # Loser: MAE >= abs(pnl_pct)
            if exit_reason == "SL_HIT" and sl and sl > 0:
                # SL was hit, MAE reached at least SL level
                if direction == "LONG":
                    mae_pct = max(((entry - sl) / entry) * 100.0, abs(pnl_pct) * 100.0)
                else:
                    mae_pct = max(((sl - entry) / entry) * 100.0, abs(pnl_pct) * 100.0)
            else:
                # Force closed or expired - MAE is at least the loss
                mae_pct = abs(pnl_pct) * 100.0

            # MFE for losers: some favorable move happened before reversal
            mfe_pct = atr_pct * max(hold_days, 0.5) * 0.2

        # Floor at 0
        mfe_pct = max(mfe_pct, 0.0)
        mae_pct = max(mae_pct, 0.0)

        results.append({
            "id": pick.get("id", ""),
            "strategy": strategy,
            "symbol": pick.get("symbol", ""),
            "category": category,
            "norm_category": _normalize_category(category),
            "direction": direction,
            "entry_price": entry,
            "exit_price": exit_price,
            "pnl_pct": pnl_pct,
            "mfe_pct": round(mfe_pct, 4),
            "mae_pct": round(mae_pct, 4),
            "is_winner": is_winner,
            "exit_reason": exit_reason,
            "hold_days": hold_days,
            "tp": tp,
            "sl": sl,
        })

    return results


# ---------------------------------------------------------------------------
# Analyze TP/SL efficiency
# ---------------------------------------------------------------------------

def analyze_tp_sl_efficiency(closed_picks):
    """
    Analyze how well current TP/SL are placed relative to MFE/MAE.

    Returns dict with efficiency metrics.
    """
    mfe_mae_data = compute_mfe_mae(closed_picks)
    if not mfe_mae_data:
        return {"error": "No analyzable picks"}

    winners = [d for d in mfe_mae_data if d["is_winner"]]
    losers = [d for d in mfe_mae_data if not d["is_winner"]]

    # TP efficiency: how many picks' TP was within 80% of MFE?
    # i.e., TP was well-placed if the pick's MFE was close to TP distance
    tp_efficient_count = 0
    tp_total = 0
    for d in winners:
        if d["tp"] and d["entry_price"] > 0 and d["tp"] > 0:
            if d["direction"] == "LONG":
                tp_dist_pct = ((d["tp"] - d["entry_price"]) / d["entry_price"]) * 100.0
            else:
                tp_dist_pct = ((d["entry_price"] - d["tp"]) / d["entry_price"]) * 100.0

            if tp_dist_pct > 0:
                tp_total += 1
                # TP is efficient if MFE reached >= 80% of TP distance
                if d["mfe_pct"] >= tp_dist_pct * 0.8:
                    tp_efficient_count += 1

    tp_efficiency = round(tp_efficient_count / tp_total, 4) if tp_total > 0 else 0.0

    # SL efficiency: how many losers exceeded SL by > 50%?
    # If many exceeded SL significantly, SL was too wide
    sl_overshot_count = 0
    sl_total = 0
    for d in losers:
        if d["sl"] and d["entry_price"] > 0 and d["sl"] > 0:
            if d["direction"] == "LONG":
                sl_dist_pct = ((d["entry_price"] - d["sl"]) / d["entry_price"]) * 100.0
            else:
                sl_dist_pct = ((d["sl"] - d["entry_price"]) / d["entry_price"]) * 100.0

            if sl_dist_pct > 0:
                sl_total += 1
                # SL too wide if MAE exceeded SL by > 50%
                if d["mae_pct"] > sl_dist_pct * 1.5:
                    sl_overshot_count += 1

    sl_efficiency = round(1.0 - (sl_overshot_count / sl_total), 4) if sl_total > 0 else 0.0

    # Optimal TP: median MFE of winners
    winner_mfes = [d["mfe_pct"] for d in winners]
    optimal_tp = round(_median(winner_mfes), 4)

    # Optimal SL: 75th percentile MAE of winners (catches most winners)
    winner_maes = [d["mae_pct"] for d in winners]
    optimal_sl = round(_percentile(winner_maes, 75), 4)

    # Current average TP/SL distances
    current_tp_dists = []
    current_sl_dists = []
    for d in mfe_mae_data:
        ep = d["entry_price"]
        if ep <= 0:
            continue
        if d["tp"] and d["tp"] > 0:
            if d["direction"] == "LONG":
                current_tp_dists.append(((d["tp"] - ep) / ep) * 100.0)
            else:
                current_tp_dists.append(((ep - d["tp"]) / ep) * 100.0)
        if d["sl"] and d["sl"] > 0:
            if d["direction"] == "LONG":
                current_sl_dists.append(((ep - d["sl"]) / ep) * 100.0)
            else:
                current_sl_dists.append(((d["sl"] - ep) / ep) * 100.0)

    current_avg_tp = round(_median(current_tp_dists), 4) if current_tp_dists else 0.0
    current_avg_sl = round(_median(current_sl_dists), 4) if current_sl_dists else 0.0

    # Risk:reward
    optimal_rr = round(optimal_tp / optimal_sl, 2) if optimal_sl > 0 else 0.0

    return {
        "total_analyzed": len(mfe_mae_data),
        "winners": len(winners),
        "losers": len(losers),
        "tp_efficiency": tp_efficiency,
        "sl_efficiency": sl_efficiency,
        "optimal_tp_pct": optimal_tp,
        "optimal_sl_pct": optimal_sl,
        "optimal_rr": optimal_rr,
        "current_avg_tp": current_avg_tp,
        "current_avg_sl": current_avg_sl,
        "median_mfe_winners": round(_median(winner_mfes), 4),
        "median_mae_winners": round(_median([d["mae_pct"] for d in winners]), 4),
        "median_mfe_losers": round(_median([d["mfe_pct"] for d in losers]), 4),
        "median_mae_losers": round(_median([d["mae_pct"] for d in losers]), 4),
        "p25_mfe_winners": round(_percentile(winner_mfes, 25), 4),
        "p75_mfe_winners": round(_percentile(winner_mfes, 75), 4),
        "p25_mae_winners": round(_percentile(winner_maes, 25), 4),
        "p75_mae_winners": round(_percentile(winner_maes, 75), 4),
        "_mfe_mae_data": mfe_mae_data,
    }


# ---------------------------------------------------------------------------
# Adaptive TP/SL getter
# ---------------------------------------------------------------------------

# Module-level cache for analysis results
_analysis_cache = {
    "data": None,
    "loaded_at": None,
    "path": None,
}


def _load_analysis(analysis_path=None):
    """Load or return cached MFE/MAE analysis from disk."""
    if analysis_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        analysis_path = os.path.join(script_dir, "data", "mfe_mae_analysis.json")

    # Return cache if fresh (within 5 minutes)
    if (_analysis_cache["data"] is not None
            and _analysis_cache["path"] == analysis_path
            and _analysis_cache["loaded_at"] is not None):
        import time as _time
        age = _time.time() - _analysis_cache["loaded_at"]
        if age < 300:
            return _analysis_cache["data"]

    if not os.path.exists(analysis_path):
        return None

    try:
        with open(analysis_path, "r") as f:
            data = json.load(f)
        import time as _time
        _analysis_cache["data"] = data
        _analysis_cache["loaded_at"] = _time.time()
        _analysis_cache["path"] = analysis_path
        return data
    except (json.JSONDecodeError, OSError):
        return None


def get_adaptive_tp_sl(strategy, direction, symbol_category="crypto"):
    """
    Get MFE/MAE-derived adaptive TP/SL for a strategy.

    Args:
        strategy: strategy name (e.g., 'binance_smart_money')
        direction: 'LONG' or 'SHORT'
        symbol_category: 'crypto', 'forex', 'equity', etc.

    Returns:
        (tp_pct, sl_pct, rr_ratio) or None if no analysis available.
    """
    analysis = _load_analysis()
    if analysis is None:
        return None

    norm_cat = _normalize_category(symbol_category)
    tp_cap, sl_cap = ASSET_CAPS.get(norm_cat, ASSET_CAPS.get(symbol_category, (15.0, 8.0)))

    # Try strategy-specific first
    by_strategy = analysis.get("by_strategy", {})
    strat_data = by_strategy.get(strategy)

    if strat_data and strat_data.get("trade_count", 0) >= MIN_STRATEGY_TRADES:
        tp_pct = strat_data.get("optimal_tp_pct", 0)
        sl_pct = strat_data.get("optimal_sl_pct", 0)
    else:
        # Fall back to category-level
        by_category = analysis.get("by_category", {})
        cat_data = by_category.get(norm_cat) or by_category.get(symbol_category)

        if cat_data:
            tp_pct = cat_data.get("optimal_tp_pct", 0)
            sl_pct = cat_data.get("optimal_sl_pct", 0)
        else:
            # Fall back to overall
            overall = analysis.get("overall", {})
            tp_pct = overall.get("optimal_tp_pct", 0)
            sl_pct = overall.get("optimal_sl_pct", 0)

    if tp_pct <= 0 or sl_pct <= 0:
        return None

    # Apply asset class caps
    tp_pct = min(tp_pct, tp_cap)
    sl_pct = min(sl_pct, sl_cap)

    # Ensure minimum SL (avoid 0)
    sl_pct = max(sl_pct, 0.1)

    rr = round(tp_pct / sl_pct, 2)

    return (round(tp_pct, 4), round(sl_pct, 4), rr)


# ---------------------------------------------------------------------------
# Report generator
# ---------------------------------------------------------------------------

def generate_mfe_mae_report(closed_picks_path=None):
    """
    Main entry point. Analyzes closed picks and saves MFE/MAE report.

    Args:
        closed_picks_path: path to closed_picks.json

    Returns:
        dict with full analysis results, also saved to data/mfe_mae_analysis.json
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))

    if closed_picks_path is None:
        closed_picks_path = os.path.join(script_dir, "data", "closed_picks.json")

    if not os.path.exists(closed_picks_path):
        print(f"[mfe_mae] File not found: {closed_picks_path}")
        return None

    with open(closed_picks_path, "r") as f:
        closed_picks = json.load(f)

    if not isinstance(closed_picks, list) or len(closed_picks) == 0:
        print("[mfe_mae] No closed picks to analyze")
        return None

    print(f"[mfe_mae] Analyzing {len(closed_picks)} closed picks...")

    # Run overall analysis
    analysis = analyze_tp_sl_efficiency(closed_picks)
    mfe_mae_data = analysis.pop("_mfe_mae_data", [])

    # Per-strategy breakdown
    by_strategy = {}
    strategy_groups = {}
    for d in mfe_mae_data:
        s = d["strategy"]
        if s not in strategy_groups:
            strategy_groups[s] = []
        strategy_groups[s].append(d)

    for strat, items in strategy_groups.items():
        winners = [d for d in items if d["is_winner"]]
        losers = [d for d in items if not d["is_winner"]]
        winner_mfes = [d["mfe_pct"] for d in winners]
        winner_maes = [d["mae_pct"] for d in winners]

        median_mfe = round(_median(winner_mfes), 4) if winner_mfes else 0.0
        p75_mae = round(_percentile(winner_maes, 75), 4) if winner_maes else 0.0

        by_strategy[strat] = {
            "trade_count": len(items),
            "win_count": len(winners),
            "loss_count": len(losers),
            "win_rate": round(len(winners) / len(items), 4) if items else 0.0,
            "median_mfe": median_mfe,
            "median_mae": round(_median([d["mae_pct"] for d in winners]), 4),
            "optimal_tp_pct": median_mfe,
            "optimal_sl_pct": max(p75_mae, 0.1),
            "rr_ratio": round(median_mfe / max(p75_mae, 0.1), 2),
        }

    # Per-category breakdown
    by_category = {}
    cat_groups = {}
    for d in mfe_mae_data:
        c = d["norm_category"]
        if c not in cat_groups:
            cat_groups[c] = []
        cat_groups[c].append(d)

    for cat, items in cat_groups.items():
        winners = [d for d in items if d["is_winner"]]
        losers = [d for d in items if not d["is_winner"]]
        winner_mfes = [d["mfe_pct"] for d in winners]
        winner_maes = [d["mae_pct"] for d in winners]

        median_mfe = round(_median(winner_mfes), 4) if winner_mfes else 0.0
        p75_mae = round(_percentile(winner_maes, 75), 4) if winner_maes else 0.0

        by_category[cat] = {
            "trade_count": len(items),
            "win_count": len(winners),
            "loss_count": len(losers),
            "win_rate": round(len(winners) / len(items), 4) if items else 0.0,
            "median_mfe_winners": median_mfe,
            "median_mae_winners": round(_median([d["mae_pct"] for d in winners]), 4),
            "median_mfe_losers": round(_median([d["mfe_pct"] for d in losers]), 4) if losers else 0.0,
            "median_mae_losers": round(_median([d["mae_pct"] for d in losers]), 4) if losers else 0.0,
            "optimal_tp_pct": median_mfe,
            "optimal_sl_pct": max(p75_mae, 0.1),
            "rr_ratio": round(median_mfe / max(p75_mae, 0.1), 2),
        }

    # Generate recommendations
    recommendations = []

    current_avg_tp = analysis.get("current_avg_tp", 0)
    optimal_tp = analysis.get("optimal_tp_pct", 0)
    if current_avg_tp > 0 and optimal_tp > 0:
        if current_avg_tp > optimal_tp * 1.2:
            recommendations.append(
                f"Tighten TP from {current_avg_tp:.1f}% to {optimal_tp:.1f}% "
                f"(median MFE of winners)"
            )
        elif current_avg_tp < optimal_tp * 0.8:
            recommendations.append(
                f"Widen TP from {current_avg_tp:.1f}% to {optimal_tp:.1f}% "
                f"(median MFE of winners - leaving money on the table)"
            )

    current_avg_sl = analysis.get("current_avg_sl", 0)
    optimal_sl = analysis.get("optimal_sl_pct", 0)
    if current_avg_sl > 0 and optimal_sl > 0:
        if current_avg_sl > optimal_sl * 1.2:
            recommendations.append(
                f"Tighten SL from {current_avg_sl:.1f}% to {optimal_sl:.1f}% "
                f"(75th percentile MAE of winners)"
            )
        elif current_avg_sl < optimal_sl * 0.8:
            recommendations.append(
                f"Widen SL from {current_avg_sl:.1f}% to {optimal_sl:.1f}% "
                f"(75th percentile MAE of winners - getting stopped out too early)"
            )

    tp_eff = analysis.get("tp_efficiency", 0)
    if tp_eff < 0.5:
        recommendations.append(
            f"TP efficiency is low ({tp_eff:.0%}). "
            f"Many winners close below 80% of TP. Consider tighter TP."
        )

    sl_eff = analysis.get("sl_efficiency", 0)
    if sl_eff < 0.6:
        recommendations.append(
            f"SL efficiency is low ({sl_eff:.0%}). "
            f"Many losers overshoot SL by >50%. Consider tighter SL."
        )

    if not recommendations:
        recommendations.append("Current TP/SL placement is well-calibrated to MFE/MAE distributions.")

    # Build output
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_analyzed": analysis["total_analyzed"],
        "winners": analysis["winners"],
        "losers": analysis["losers"],
        "overall": {
            "median_mfe_winners": analysis["median_mfe_winners"],
            "median_mae_winners": analysis["median_mae_winners"],
            "median_mfe_losers": analysis["median_mfe_losers"],
            "median_mae_losers": analysis["median_mae_losers"],
            "optimal_tp_pct": analysis["optimal_tp_pct"],
            "optimal_sl_pct": analysis["optimal_sl_pct"],
            "optimal_rr": analysis["optimal_rr"],
            "current_avg_tp": current_avg_tp,
            "current_avg_sl": current_avg_sl,
            "tp_efficiency": tp_eff,
            "sl_efficiency": sl_eff,
            "p25_mfe_winners": analysis.get("p25_mfe_winners", 0),
            "p75_mfe_winners": analysis.get("p75_mfe_winners", 0),
            "p25_mae_winners": analysis.get("p25_mae_winners", 0),
            "p75_mae_winners": analysis.get("p75_mae_winners", 0),
        },
        "by_strategy": by_strategy,
        "by_category": by_category,
        "recommendations": recommendations,
    }

    # Save report
    output_path = os.path.join(script_dir, "data", "mfe_mae_analysis.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"[mfe_mae] Report saved to {output_path}")

    # Print summary
    print(f"\n[mfe_mae] === MFE/MAE Analysis Summary ===")
    print(f"  Total analyzed: {report['total_analyzed']}")
    print(f"  Winners: {report['winners']}, Losers: {report['losers']}")
    print(f"  Median MFE (winners): {analysis['median_mfe_winners']:.2f}%")
    print(f"  Median MAE (winners): {analysis['median_mae_winners']:.2f}%")
    print(f"  Optimal TP: {analysis['optimal_tp_pct']:.2f}%")
    print(f"  Optimal SL: {analysis['optimal_sl_pct']:.2f}%")
    print(f"  Optimal R:R: {analysis['optimal_rr']:.2f}")
    print(f"  TP efficiency: {tp_eff:.0%}")
    print(f"  SL efficiency: {sl_eff:.0%}")
    print(f"\n  Recommendations:")
    for r in recommendations:
        print(f"    - {r}")

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    path = None
    for i, arg in enumerate(sys.argv):
        if arg == "--path" and i + 1 < len(sys.argv):
            path = sys.argv[i + 1]

    report = generate_mfe_mae_report(closed_picks_path=path)
    if report is None:
        print("[mfe_mae] Analysis failed.")
        sys.exit(1)
    sys.exit(0)
