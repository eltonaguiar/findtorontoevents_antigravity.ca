#!/usr/bin/env python3
"""
Mutation Backtest — Deep validation of promoted mutations from strategy_mutator.py.

For each promoted mutation:
1. Loads ALL closed picks from dashboard_payload + universal_resolved_picks
2. Filters to picks from the ORIGINAL strategy
3. Simulates the INVERSE direction (for inverse mutations)
4. Computes: WR, PF, avg PnL, max DD, win streak, loss streak
5. Splits into 3 chronological periods (early/mid/recent) for consistency check
6. Checks by regime (BULLISH/BEARISH/CHOPPY) if available
7. Checks by symbol — which symbols drive the edge

Verdicts:
  PASS  = WR >= 50% AND consistent across 2+ periods AND PF > 1.2
  FAIL  = WR < 40% in any period OR PF < 0.8
  WATCH = between PASS and FAIL

Stdlib only. Saves to alpha_engine/data/mutation_backtest.json.
"""

import sys
import os
import json
import datetime
import math
from collections import defaultdict
from pathlib import Path

# Windows UTF-8 fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
AUDIT_DIR = BASE_DIR.parent / "audit_trail" / "data"

DASHBOARD_PAYLOAD_PATH = AUDIT_DIR / "dashboard_payload.json"
UNIVERSAL_RESOLVED_PATH = AUDIT_DIR / "universal_resolved_picks.json"
MUTATION_RESULTS_PATH = DATA_DIR / "mutation_results.json"
OUTPUT_PATH = DATA_DIR / "mutation_backtest.json"

# Verdict thresholds
PASS_WR_MIN = 0.50
PASS_PF_MIN = 1.2
PASS_CONSISTENT_PERIODS = 2  # must pass WR >= 50% in at least 2 of 3 periods
FAIL_WR_ANY_PERIOD = 0.40
FAIL_PF = 0.8


def _load_json(path):
    """Load JSON file, return None on failure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[WARN] Cannot load {path}: {e}")
        return None


def _save_json(path, data):
    """Save JSON file with UTF-8 encoding."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)


def _load_all_closed_picks():
    """Load closed picks from dashboard_payload and universal_resolved_picks.
    Merges both sources, deduplicating by (strategy, symbol, timestamp).
    """
    picks = []
    seen = set()

    # Source 1: dashboard_payload.json -> picks.recent_closed
    payload = _load_json(DASHBOARD_PAYLOAD_PATH)
    if payload:
        recent_closed = payload.get("picks", {}).get("recent_closed", [])
        for p in recent_closed:
            key = (p.get("strategy", ""), p.get("symbol", ""), p.get("timestamp", ""))
            if key not in seen and p.get("strategy"):
                seen.add(key)
                picks.append(p)

    # Source 2: universal_resolved_picks.json
    universal = _load_json(UNIVERSAL_RESOLVED_PATH)
    if universal and isinstance(universal, list):
        for p in universal:
            key = (p.get("strategy", ""), p.get("symbol", ""), p.get("timestamp", ""))
            if key not in seen and p.get("strategy"):
                seen.add(key)
                picks.append(p)

    return picks


def _is_win(pick):
    """Determine if a pick was a win."""
    status = str(pick.get("status", "")).upper()
    if status == "WON":
        return True
    if status in ("LOST", "STOPPED"):
        return False
    pnl = pick.get("pnl_pct", 0)
    if pnl is None:
        pnl = 0
    return float(pnl) > 0


def _get_pnl(pick):
    """Get PnL percentage from a pick."""
    pnl = pick.get("pnl_pct", 0)
    if pnl is None:
        return 0.0
    return float(pnl)


def _parse_timestamp(pick):
    """Parse timestamp from a pick, return a sortable string or None."""
    for field in ("timestamp", "closed_at", "resolved_at"):
        val = pick.get(field)
        if val and isinstance(val, str) and len(val) >= 10:
            return val
    return None


def _invert_pick(pick):
    """Invert a pick: flip win/loss, negate PnL, flip direction."""
    inv = dict(pick)
    pnl = _get_pnl(pick)
    inv["pnl_pct"] = -pnl
    inv["status"] = "WON" if pnl < 0 else "LOST"
    direction = str(pick.get("direction", "LONG")).upper()
    inv["direction"] = "SHORT" if direction == "LONG" else "LONG"
    return inv


def _compute_stats(picks):
    """Compute comprehensive stats for a list of picks."""
    if not picks:
        return {
            "count": 0, "wr": 0.0, "pf": 0.0, "avg_pnl": 0.0,
            "max_dd": 0.0, "max_win_streak": 0, "max_loss_streak": 0,
            "total_wins": 0, "total_losses": 0,
            "avg_win": 0.0, "avg_loss": 0.0,
        }

    wins = 0
    losses = 0
    win_pnls = []
    loss_pnls = []
    all_pnls = []

    # Streaks
    max_win_streak = 0
    max_loss_streak = 0
    cur_win_streak = 0
    cur_loss_streak = 0

    # Drawdown tracking (cumulative PnL)
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0

    for p in picks:
        pnl = _get_pnl(p)
        all_pnls.append(pnl)
        is_w = _is_win(p)

        if is_w:
            wins += 1
            win_pnls.append(pnl)
            cur_win_streak += 1
            cur_loss_streak = 0
            max_win_streak = max(max_win_streak, cur_win_streak)
        else:
            losses += 1
            loss_pnls.append(pnl)
            cur_loss_streak += 1
            cur_win_streak = 0
            max_loss_streak = max(max_loss_streak, cur_loss_streak)

        cumulative += pnl
        peak = max(peak, cumulative)
        dd = peak - cumulative
        max_dd = max(max_dd, dd)

    total = wins + losses
    wr = wins / total if total > 0 else 0.0

    # Profit factor = gross wins / abs(gross losses)
    gross_wins = sum(win_pnls) if win_pnls else 0.0
    gross_losses = abs(sum(loss_pnls)) if loss_pnls else 0.0
    pf = gross_wins / gross_losses if gross_losses > 0 else (999.0 if gross_wins > 0 else 0.0)

    avg_pnl = sum(all_pnls) / len(all_pnls) if all_pnls else 0.0
    avg_win = sum(win_pnls) / len(win_pnls) if win_pnls else 0.0
    avg_loss = sum(loss_pnls) / len(loss_pnls) if loss_pnls else 0.0

    return {
        "count": total,
        "wr": round(wr, 4),
        "pf": round(pf, 4),
        "avg_pnl": round(avg_pnl, 4),
        "max_dd": round(max_dd, 4),
        "max_win_streak": max_win_streak,
        "max_loss_streak": max_loss_streak,
        "total_wins": wins,
        "total_losses": losses,
        "avg_win": round(avg_win, 4),
        "avg_loss": round(avg_loss, 4),
    }


def _split_periods(picks, n=3):
    """Split picks into n chronological periods.
    Sort by timestamp, then split into roughly equal chunks.
    """
    # Sort by timestamp
    def sort_key(p):
        ts = _parse_timestamp(p)
        return ts if ts else ""

    sorted_picks = sorted(picks, key=sort_key)
    if len(sorted_picks) < n:
        # Not enough picks for n periods — return what we have
        return [sorted_picks] if sorted_picks else []

    chunk_size = len(sorted_picks) // n
    periods = []
    for i in range(n):
        start = i * chunk_size
        end = start + chunk_size if i < n - 1 else len(sorted_picks)
        periods.append(sorted_picks[start:end])
    return periods


def _detect_regime(pick):
    """Detect market regime from pick metadata.
    Tries explicit regime fields, then infers from PnL direction patterns.
    """
    # Check explicit regime fields
    for field in ("regime", "market_regime", "market_condition"):
        val = pick.get(field)
        if val and isinstance(val, str):
            val_upper = val.upper()
            if "BULL" in val_upper:
                return "BULLISH"
            elif "BEAR" in val_upper:
                return "BEARISH"
            elif "CHOP" in val_upper or "RANGE" in val_upper or "SIDEWAYS" in val_upper:
                return "CHOPPY"
            return val_upper

    # Infer from notes/reason if available
    for field in ("notes", "reason"):
        val = str(pick.get(field, "")).upper()
        if "BULL" in val:
            return "BULLISH"
        elif "BEAR" in val:
            return "BEARISH"
        elif "CHOP" in val or "RANGE" in val:
            return "CHOPPY"

    return "UNKNOWN"


def _classify_regime_by_period(picks):
    """Classify regime for a group of picks based on aggregate PnL direction.
    If most picks in the period are positive on LONG, market was likely BULLISH.
    """
    if not picks:
        return "UNKNOWN"

    long_picks = [p for p in picks if str(p.get("direction", "")).upper() == "LONG"]
    if not long_picks:
        return "UNKNOWN"

    long_wins = sum(1 for p in long_picks if _get_pnl(p) > 0)
    long_wr = long_wins / len(long_picks) if long_picks else 0.5

    if long_wr > 0.55:
        return "BULLISH"
    elif long_wr < 0.35:
        return "BEARISH"
    else:
        return "CHOPPY"


def _analyze_by_symbol(picks):
    """Break down stats by symbol."""
    by_sym = defaultdict(list)
    for p in picks:
        sym = p.get("symbol", "UNKNOWN")
        by_sym[sym].append(p)

    results = {}
    for sym, sym_picks in sorted(by_sym.items(), key=lambda x: -len(x[1])):
        stats = _compute_stats(sym_picks)
        results[sym] = {
            "count": stats["count"],
            "wr": stats["wr"],
            "pf": stats["pf"],
            "avg_pnl": stats["avg_pnl"],
        }
    return results


def _determine_verdict(overall_stats, period_stats, symbol_stats):
    """Determine PASS/FAIL/WATCH verdict based on criteria.

    PASS = WR >= 50% AND consistent across 2+ periods AND PF > 1.2
    FAIL = WR < 40% in any period OR PF < 0.8
    WATCH = between PASS and FAIL
    """
    reasons = []

    # Check overall WR
    overall_wr = overall_stats.get("wr", 0)
    overall_pf = overall_stats.get("pf", 0)

    # FAIL checks first
    # Check if WR < 40% in any period
    fail_period = False
    for i, ps in enumerate(period_stats):
        if ps.get("count", 0) >= 3:  # need minimum trades in period
            if ps.get("wr", 0) < FAIL_WR_ANY_PERIOD:
                fail_period = True
                reasons.append(f"Period {i+1} WR={ps['wr']*100:.1f}% < 40%")

    if overall_pf < FAIL_PF:
        reasons.append(f"PF={overall_pf:.2f} < {FAIL_PF}")
        return "FAIL", reasons

    if fail_period:
        # If WR < 40% in ANY period but PF is ok, check if it's really bad
        if overall_wr < FAIL_WR_ANY_PERIOD:
            reasons.append(f"Overall WR={overall_wr*100:.1f}% < 40%")
            return "FAIL", reasons

    # PASS checks
    # Count periods with WR >= 50%
    passing_periods = 0
    for ps in period_stats:
        if ps.get("count", 0) >= 3 and ps.get("wr", 0) >= PASS_WR_MIN:
            passing_periods += 1

    if overall_wr >= PASS_WR_MIN and passing_periods >= PASS_CONSISTENT_PERIODS and overall_pf >= PASS_PF_MIN:
        reasons.append(f"WR={overall_wr*100:.1f}%, PF={overall_pf:.2f}, {passing_periods}/3 periods pass")
        return "PASS", reasons

    # WATCH — between PASS and FAIL
    if fail_period:
        reasons.append(f"WR inconsistent across periods (but overall {overall_wr*100:.1f}%)")
    elif overall_wr < PASS_WR_MIN:
        reasons.append(f"Overall WR={overall_wr*100:.1f}% < 50%")
    elif overall_pf < PASS_PF_MIN:
        reasons.append(f"PF={overall_pf:.2f} < {PASS_PF_MIN}")
    elif passing_periods < PASS_CONSISTENT_PERIODS:
        reasons.append(f"Only {passing_periods}/{PASS_CONSISTENT_PERIODS} periods consistent")
    else:
        reasons.append("Marginal metrics")

    return "WATCH", reasons


def _backtest_mutation(mutation_info, all_picks):
    """Run deep backtest for a single promoted mutation."""
    strategy_name = mutation_info["strategy"]
    mutation_name = mutation_info["mutation"]
    mutation_type = mutation_info["type"]

    print(f"\n--- Backtesting: {mutation_name} ---")
    print(f"    Original strategy: {strategy_name}")
    print(f"    Mutation type: {mutation_type}")

    # Filter picks for this strategy
    strategy_picks = [p for p in all_picks if p.get("strategy") == strategy_name]
    print(f"    Found {len(strategy_picks)} closed picks for strategy")

    if len(strategy_picks) < 5:
        print(f"    SKIP: Insufficient data ({len(strategy_picks)} picks)")
        return {
            "mutation": mutation_name,
            "strategy": strategy_name,
            "mutation_type": mutation_type,
            "verdict": "FAIL",
            "verdict_reasons": [f"Insufficient data: only {len(strategy_picks)} picks"],
            "overall_stats": _compute_stats([]),
            "period_analysis": [],
            "regime_analysis": {},
            "symbol_analysis": {},
            "rank_score": 0,
        }

    # Apply mutation
    if mutation_type == "inverse":
        mutated_picks = [_invert_pick(p) for p in strategy_picks]
    else:
        # For non-inverse mutations, use picks as-is (tight/symbol_rotation)
        mutated_picks = list(strategy_picks)

    # Sort by timestamp for chronological analysis
    def sort_key(p):
        ts = _parse_timestamp(p)
        return ts if ts else ""
    mutated_picks.sort(key=sort_key)

    # 1. Overall stats
    overall_stats = _compute_stats(mutated_picks)
    print(f"    Overall: WR={overall_stats['wr']*100:.1f}%, PF={overall_stats['pf']:.2f}, "
          f"AvgPnL={overall_stats['avg_pnl']:.2f}%, MaxDD={overall_stats['max_dd']:.2f}%")

    # 2. Period analysis (split into 3 chronological periods)
    periods = _split_periods(mutated_picks, n=3)
    period_labels = ["early", "mid", "recent"]
    period_analysis = []

    for i, period_picks in enumerate(periods):
        label = period_labels[i] if i < len(period_labels) else f"period_{i+1}"
        stats = _compute_stats(period_picks)
        regime = _classify_regime_by_period(period_picks)

        # Get date range for the period
        timestamps = [_parse_timestamp(p) for p in period_picks]
        timestamps = [t for t in timestamps if t]
        date_start = timestamps[0][:10] if timestamps else "?"
        date_end = timestamps[-1][:10] if timestamps else "?"

        period_info = {
            "period": label,
            "date_range": f"{date_start} to {date_end}",
            "inferred_regime": regime,
            **stats,
        }
        period_analysis.append(period_info)
        print(f"    {label.upper()}: WR={stats['wr']*100:.1f}% ({stats['count']} trades) "
              f"PF={stats['pf']:.2f} [{date_start} to {date_end}] regime={regime}")

    # 3. Regime analysis
    regime_groups = defaultdict(list)
    for p in mutated_picks:
        regime = _detect_regime(p)
        regime_groups[regime].append(p)

    # If all UNKNOWN, infer regime from period classification
    if len(regime_groups) == 1 and "UNKNOWN" in regime_groups:
        # Re-classify using period-based regime detection
        regime_groups = defaultdict(list)
        for i, period_picks in enumerate(periods):
            regime = _classify_regime_by_period(period_picks)
            for p in period_picks:
                regime_groups[regime].append(p)

    regime_analysis = {}
    for regime, rpicks in sorted(regime_groups.items()):
        stats = _compute_stats(rpicks)
        regime_analysis[regime] = {
            "count": stats["count"],
            "wr": stats["wr"],
            "pf": stats["pf"],
            "avg_pnl": stats["avg_pnl"],
        }
        print(f"    Regime {regime}: WR={stats['wr']*100:.1f}% ({stats['count']} trades) PF={stats['pf']:.2f}")

    # 4. Symbol analysis
    symbol_analysis = _analyze_by_symbol(mutated_picks)
    top_symbols = sorted(symbol_analysis.items(), key=lambda x: -x[1]["count"])[:10]
    for sym, stats in top_symbols:
        print(f"    Symbol {sym}: WR={stats['wr']*100:.1f}% ({stats['count']} trades) PF={stats['pf']:.2f}")

    # 5. Determine verdict
    period_stats_list = period_analysis if period_analysis else [overall_stats]
    verdict, reasons = _determine_verdict(overall_stats, period_stats_list, symbol_analysis)

    # 6. Compute rank score (for sorting)
    # Score = WR*40 + min(PF,3)*20 + consistency_bonus + regime_bonus
    consistency_bonus = 0
    for ps in period_analysis:
        if ps.get("count", 0) >= 3 and ps.get("wr", 0) >= 0.50:
            consistency_bonus += 5
    regime_pass_count = sum(
        1 for r, rs in regime_analysis.items()
        if rs.get("count", 0) >= 3 and rs.get("wr", 0) >= 0.50
    )
    regime_bonus = regime_pass_count * 3

    rank_score = (
        overall_stats["wr"] * 40
        + min(overall_stats["pf"], 3.0) * 20
        + consistency_bonus
        + regime_bonus
        - overall_stats["max_dd"] * 0.5
    )

    print(f"    VERDICT: {verdict} (score={rank_score:.1f})")
    print(f"    Reasons: {'; '.join(reasons)}")

    return {
        "mutation": mutation_name,
        "strategy": strategy_name,
        "mutation_type": mutation_type,
        "original_wr": mutation_info.get("original_wr", 0),
        "mutation_wr_simple": mutation_info.get("mutation_wr", 0),
        "verdict": verdict,
        "verdict_reasons": reasons,
        "rank_score": round(rank_score, 2),
        "overall_stats": overall_stats,
        "period_analysis": period_analysis,
        "regime_analysis": regime_analysis,
        "symbol_analysis": symbol_analysis,
    }


def run():
    """Main entry point for mutation backtesting."""
    print("=" * 70)
    print("MUTATION BACKTEST - Deep Validation of Promoted Mutations")
    print("=" * 70)

    # Load mutation results to get promoted mutations
    mutation_results = _load_json(MUTATION_RESULTS_PATH)
    if not mutation_results:
        print("[ERROR] Cannot load mutation_results.json")
        return None

    promotions = mutation_results.get("promotions", [])
    if not promotions:
        print("[WARN] No promoted mutations found to backtest")
        result = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "promotions_tested": 0,
            "results": [],
            "ranked_table": [],
        }
        _save_json(OUTPUT_PATH, result)
        return result

    print(f"\nFound {len(promotions)} promoted mutations to deep-test")

    # Load all closed picks
    all_picks = _load_all_closed_picks()
    print(f"Loaded {len(all_picks)} total closed picks across all strategies")

    # Backtest each promoted mutation
    results = []
    for promo in promotions:
        bt = _backtest_mutation(promo, all_picks)
        results.append(bt)

    # Sort by rank score descending
    results.sort(key=lambda x: -x.get("rank_score", 0))

    # Build ranked table summary
    ranked_table = []
    for i, r in enumerate(results, 1):
        ranked_table.append({
            "rank": i,
            "mutation": r["mutation"],
            "verdict": r["verdict"],
            "wr": r["overall_stats"]["wr"],
            "pf": r["overall_stats"]["pf"],
            "avg_pnl": r["overall_stats"]["avg_pnl"],
            "max_dd": r["overall_stats"]["max_dd"],
            "trades": r["overall_stats"]["count"],
            "win_streak": r["overall_stats"]["max_win_streak"],
            "loss_streak": r["overall_stats"]["max_loss_streak"],
            "rank_score": r["rank_score"],
            "reasons": r["verdict_reasons"],
        })

    # Print ranked table
    print("\n" + "=" * 70)
    print("RANKED MUTATION TABLE")
    print("=" * 70)
    print(f"{'#':>2} {'Verdict':<6} {'Mutation':<50} {'WR':>6} {'PF':>6} {'AvgPnL':>8} {'MaxDD':>7} {'Trades':>6} {'Score':>6}")
    print("-" * 100)
    for rt in ranked_table:
        v_marker = {"PASS": "+", "FAIL": "X", "WATCH": "?"}
        marker = v_marker.get(rt["verdict"], " ")
        print(
            f"{rt['rank']:>2} [{marker}] {rt['mutation']:<48} "
            f"{rt['wr']*100:>5.1f}% "
            f"{rt['pf']:>5.2f} "
            f"{rt['avg_pnl']:>7.2f}% "
            f"{rt['max_dd']:>6.2f}% "
            f"{rt['trades']:>5} "
            f"{rt['rank_score']:>5.1f}"
        )
    print("-" * 100)

    # Summary counts
    pass_count = sum(1 for r in results if r["verdict"] == "PASS")
    fail_count = sum(1 for r in results if r["verdict"] == "FAIL")
    watch_count = sum(1 for r in results if r["verdict"] == "WATCH")
    print(f"\nSummary: {pass_count} PASS, {watch_count} WATCH, {fail_count} FAIL out of {len(results)} tested")

    # Edge decay warnings
    print("\nEdge Consistency Check:")
    for r in results:
        periods = r.get("period_analysis", [])
        if len(periods) >= 3:
            early_wr = periods[0].get("wr", 0)
            recent_wr = periods[-1].get("wr", 0)
            if recent_wr < early_wr - 0.10:
                print(f"  WARNING: {r['mutation']} shows DECAYING edge "
                      f"(early={early_wr*100:.1f}% -> recent={recent_wr*100:.1f}%)")
            elif recent_wr > early_wr + 0.10:
                print(f"  POSITIVE: {r['mutation']} shows IMPROVING edge "
                      f"(early={early_wr*100:.1f}% -> recent={recent_wr*100:.1f}%)")
            else:
                print(f"  STABLE: {r['mutation']} edge is consistent "
                      f"(early={early_wr*100:.1f}% -> recent={recent_wr*100:.1f}%)")

    # Build output
    output = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "promotions_tested": len(promotions),
        "total_picks_loaded": len(all_picks),
        "verdicts": {
            "PASS": pass_count,
            "WATCH": watch_count,
            "FAIL": fail_count,
        },
        "ranked_table": ranked_table,
        "detailed_results": results,
    }

    _save_json(OUTPUT_PATH, output)
    print(f"\nResults saved to {OUTPUT_PATH}")
    print("=" * 70)

    return output


if __name__ == "__main__":
    run()
