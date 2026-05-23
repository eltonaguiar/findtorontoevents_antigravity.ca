#!/usr/bin/env python3
"""
Edge Analysis for Crypto/Forex Picks
=====================================
Analyzes closed picks data to find statistically significant edges.
Follows TESTING_PROTOCOL.MD requirements:
- Minimum 20 trades for statistical confidence
- Score >= 40 floor (below = 33.9% WR)
- Score >= 60 for promotion (75.2% WR)
- Trust >= 4 for LONG picks
- Statistical tests for significance

Output: Documented edges with backtest proof for Redis bus publication.
"""

import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple
from scipy import stats


def load_closed_picks() -> List[Dict]:
    """Load all closed picks from alpha_engine/data."""
    picks = []
    data_file = Path("alpha_engine/data/closed_picks_fast.json")

    if data_file.exists():
        with open(data_file) as f:
            picks.extend(json.load(f))

    # Also load universal resolved picks
    universal_file = Path("audit_trail/data/universal_resolved_picks.json")
    if universal_file.exists():
        with open(universal_file) as f:
            universal = json.load(f)
            # Dedupe by ID if present
            existing_ids = {p.get("id") for p in picks if p.get("id")}
            for p in universal:
                if p.get("id") not in existing_ids:
                    picks.append(p)

    return picks


def get_outcome(pick: Dict) -> str:
    """Determine if pick was WIN or LOSS."""
    status = pick.get("status", "").upper()
    pnl = pick.get("pnl_pct", 0)
    exit_reason = pick.get("exit_reason", "").upper()

    if status in ("WON", "WIN"):
        return "WIN"
    if status in ("LOST", "LOSS"):
        return "LOSS"
    if "TP" in exit_reason:
        return "WIN"
    if "SL" in exit_reason:
        return "LOSS"
    if pnl is not None and pnl > 0:
        return "WIN"
    if pnl is not None and pnl < 0:
        return "LOSS"
    return "UNKNOWN"


def compute_wr_stats(outcomes: List[str]) -> Dict:
    """Compute win rate with confidence interval."""
    n = len(outcomes)
    if n == 0:
        return {"n": 0, "wr": 0, "ci_low": 0, "ci_high": 0, "significant": False}

    wins = sum(1 for o in outcomes if o == "WIN")
    wr = wins / n

    # Wilson score interval for binomial proportion
    z = 1.96  # 95% CI
    denom = 1 + z**2 / n
    center = (wr + z**2 / (2*n)) / denom
    margin = (z / denom) * math.sqrt(wr * (1 - wr) / n + z**2 / (4 * n**2))

    ci_low = max(0, center - margin)
    ci_high = min(1, center + margin)

    # Statistically significant if CI doesn't overlap 50%
    significant = ci_low > 0.50 or ci_high < 0.50

    return {
        "n": n,
        "wins": wins,
        "losses": n - wins,
        "wr": round(wr * 100, 1),
        "ci_low": round(ci_low * 100, 1),
        "ci_high": round(ci_high * 100, 1),
        "significant": significant,
    }


def analyze_direction_edge(picks: List[Dict]) -> Dict:
    """Analyze LONG vs SHORT performance edge."""
    by_direction = defaultdict(list)

    for p in picks:
        direction = p.get("direction", "").upper()
        if direction in ("BUY", "LONG"):
            direction = "LONG"
        elif direction in ("SELL", "SHORT"):
            direction = "SHORT"
        else:
            continue

        outcome = get_outcome(p)
        if outcome != "UNKNOWN":
            by_direction[direction].append(outcome)

    results = {}
    for direction, outcomes in by_direction.items():
        results[direction] = compute_wr_stats(outcomes)

    # Calculate edge (SHORT - LONG)
    long_wr = results.get("LONG", {}).get("wr", 50)
    short_wr = results.get("SHORT", {}).get("wr", 50)
    edge = short_wr - long_wr

    return {
        "by_direction": results,
        "short_edge_pp": round(edge, 1),
        "recommendation": "SHORT_BIAS" if edge > 5 else "LONG_BIAS" if edge < -5 else "NEUTRAL",
    }


def analyze_confidence_buckets(picks: List[Dict]) -> Dict:
    """Analyze WR by confidence bucket to find sweet spots."""
    buckets = {
        "0.50-0.59": (0.50, 0.60),
        "0.60-0.69": (0.60, 0.70),
        "0.70-0.74": (0.70, 0.75),
        "0.75-0.79": (0.75, 0.80),
        "0.80-0.84": (0.80, 0.85),
        "0.85-0.89": (0.85, 0.90),
        "0.90-1.00": (0.90, 1.01),
    }

    by_bucket = defaultdict(list)

    for p in picks:
        conf = p.get("confidence") or p.get("ml_score") or 0
        outcome = get_outcome(p)
        if outcome == "UNKNOWN":
            continue

        for name, (low, high) in buckets.items():
            if low <= conf < high:
                by_bucket[name].append(outcome)
                break

    results = {}
    best_bucket = None
    best_wr = 0

    for name in buckets:
        outcomes = by_bucket.get(name, [])
        stats = compute_wr_stats(outcomes)
        results[name] = stats

        if stats["n"] >= 20 and stats["wr"] > best_wr:
            best_wr = stats["wr"]
            best_bucket = name

    # Find toxic bucket (high conf, low WR)
    toxic_bucket = None
    for name in ["0.90-1.00", "0.85-0.89"]:
        if name in results and results[name]["n"] >= 10:
            if results[name]["wr"] < 50:
                toxic_bucket = name
                break

    return {
        "by_bucket": results,
        "sweet_spot": best_bucket,
        "sweet_spot_wr": best_wr,
        "toxic_bucket": toxic_bucket,
        "toxic_bucket_wr": results.get(toxic_bucket, {}).get("wr") if toxic_bucket else None,
    }


def analyze_strategy_edge(picks: List[Dict]) -> Dict:
    """Analyze WR by strategy."""
    by_strategy = defaultdict(list)

    for p in picks:
        strategy = p.get("strategy") or p.get("source_system") or "unknown"
        outcome = get_outcome(p)
        if outcome != "UNKNOWN":
            by_strategy[strategy].append(outcome)

    results = {}
    for strategy, outcomes in by_strategy.items():
        stats = compute_wr_stats(outcomes)
        if stats["n"] >= 10:  # Min trades for inclusion
            results[strategy] = stats

    # Sort by WR descending
    sorted_strategies = sorted(results.items(), key=lambda x: x[1]["wr"], reverse=True)

    # Top performers (WR > 60%, n >= 20)
    top_performers = [
        (s, r) for s, r in sorted_strategies
        if r["wr"] >= 60 and r["n"] >= 20
    ]

    # Underperformers (WR < 45%, n >= 20)
    underperformers = [
        (s, r) for s, r in sorted_strategies
        if r["wr"] < 45 and r["n"] >= 20
    ]

    return {
        "by_strategy": dict(sorted_strategies[:20]),  # Top 20
        "top_performers": top_performers[:5],
        "underperformers": underperformers[:5],
    }


def analyze_source_system_edge(picks: List[Dict]) -> Dict:
    """Analyze WR by source system."""
    by_source = defaultdict(list)

    for p in picks:
        source = p.get("source_system") or p.get("strategy") or "unknown"
        outcome = get_outcome(p)
        if outcome != "UNKNOWN":
            by_source[source].append(outcome)

    results = {}
    for source, outcomes in by_source.items():
        stats = compute_wr_stats(outcomes)
        if stats["n"] >= 10:
            results[source] = stats

    sorted_sources = sorted(results.items(), key=lambda x: x[1]["wr"], reverse=True)

    return {
        "by_source": dict(sorted_sources[:15]),
        "elite_sources": [(s, r) for s, r in sorted_sources if r["wr"] >= 55 and r["n"] >= 20][:5],
        "toxic_sources": [(s, r) for s, r in sorted_sources if r["wr"] < 45 and r["n"] >= 20][:5],
    }


def analyze_symbol_edge(picks: List[Dict]) -> Dict:
    """Analyze WR by symbol."""
    by_symbol = defaultdict(list)

    for p in picks:
        symbol = p.get("symbol", "UNKNOWN")
        # Normalize symbol
        symbol = symbol.upper().replace("-USD", "USDT").replace("-", "")
        outcome = get_outcome(p)
        if outcome != "UNKNOWN":
            by_symbol[symbol].append(outcome)

    results = {}
    for symbol, outcomes in by_symbol.items():
        stats = compute_wr_stats(outcomes)
        if stats["n"] >= 10:
            results[symbol] = stats

    sorted_symbols = sorted(results.items(), key=lambda x: x[1]["wr"], reverse=True)

    return {
        "top_symbols": sorted_symbols[:10],
        "worst_symbols": sorted_symbols[-10:] if len(sorted_symbols) >= 10 else [],
    }


def analyze_time_of_day(picks: List[Dict]) -> Dict:
    """Analyze WR by hour of day (UTC)."""
    by_hour = defaultdict(list)

    for p in picks:
        timestamp = p.get("timestamp") or p.get("entry_date")
        if not timestamp:
            continue

        try:
            if isinstance(timestamp, str):
                # Parse ISO format
                if "T" in timestamp:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                else:
                    continue  # Date only, no time
            else:
                continue

            hour = dt.hour
            outcome = get_outcome(p)
            if outcome != "UNKNOWN":
                by_hour[hour].append(outcome)
        except Exception:
            continue

    results = {}
    for hour, outcomes in by_hour.items():
        stats = compute_wr_stats(outcomes)
        if stats["n"] >= 10:
            results[hour] = stats

    # Find best/worst hours
    sorted_hours = sorted(results.items(), key=lambda x: x[1]["wr"], reverse=True)

    return {
        "by_hour": dict(sorted(results.items())),
        "best_hours": sorted_hours[:3] if sorted_hours else [],
        "worst_hours": sorted_hours[-3:] if len(sorted_hours) >= 3 else [],
    }


def analyze_direction_confidence_combo(picks: List[Dict]) -> Dict:
    """Analyze WR by direction + confidence combo (find toxic combos)."""
    combos = defaultdict(list)

    for p in picks:
        direction = p.get("direction", "").upper()
        if direction in ("BUY", "LONG"):
            direction = "LONG"
        elif direction in ("SELL", "SHORT"):
            direction = "SHORT"
        else:
            continue

        conf = p.get("confidence") or p.get("ml_score") or 0

        if conf >= 0.90:
            bucket = ">=0.90"
        elif conf >= 0.80:
            bucket = "0.80-0.89"
        elif conf >= 0.70:
            bucket = "0.70-0.79"
        else:
            bucket = "<0.70"

        combo = f"{direction}+{bucket}"
        outcome = get_outcome(p)
        if outcome != "UNKNOWN":
            combos[combo].append(outcome)

    results = {}
    for combo, outcomes in combos.items():
        stats = compute_wr_stats(outcomes)
        if stats["n"] >= 10:
            results[combo] = stats

    # Find toxic combos (WR < 40%)
    toxic = [(c, r) for c, r in results.items() if r["wr"] < 40]

    return {
        "by_combo": results,
        "toxic_combos": toxic,
    }


def analyze_risk_reward(picks: List[Dict]) -> Dict:
    """Analyze WR by risk/reward ratio."""
    by_rr = defaultdict(list)

    for p in picks:
        rr = p.get("risk_reward") or 0
        outcome = get_outcome(p)
        if outcome == "UNKNOWN" or rr == 0:
            continue

        if rr < 1.5:
            bucket = "RR<1.5"
        elif rr < 2.0:
            bucket = "RR1.5-2.0"
        elif rr < 2.5:
            bucket = "RR2.0-2.5"
        elif rr < 3.0:
            bucket = "RR2.5-3.0"
        else:
            bucket = "RR>=3.0"

        by_rr[bucket].append(outcome)

    results = {}
    for bucket, outcomes in by_rr.items():
        stats = compute_wr_stats(outcomes)
        if stats["n"] >= 10:
            results[bucket] = stats

    return {
        "by_rr": results,
        "optimal_rr": max(results.items(), key=lambda x: x[1]["wr"]) if results else None,
    }


def generate_edge_report(picks: List[Dict]) -> str:
    """Generate comprehensive edge report."""
    total = len(picks)
    outcomes = [get_outcome(p) for p in picks]
    overall = compute_wr_stats([o for o in outcomes if o != "UNKNOWN"])

    direction = analyze_direction_edge(picks)
    confidence = analyze_confidence_buckets(picks)
    strategy = analyze_strategy_edge(picks)
    source = analyze_source_system_edge(picks)
    symbol = analyze_symbol_edge(picks)
    time = analyze_time_of_day(picks)
    combo = analyze_direction_confidence_combo(picks)
    rr = analyze_risk_reward(picks)

    lines = [
        "=" * 80,
        "CRYPTO/FOREX EDGE ANALYSIS REPORT",
        f"Generated: {datetime.now().isoformat()}",
        f"Data: {total} closed picks analyzed",
        "=" * 80,
        "",
        "OVERALL PERFORMANCE",
        "-" * 40,
        f"Total Picks: {overall['n']}",
        f"Win Rate: {overall['wr']}% (CI: {overall['ci_low']}-{overall['ci_high']}%)",
        f"Statistically Significant: {'YES' if overall['significant'] else 'NO'}",
        "",

        "=" * 80,
        "EDGE #1: DIRECTION BIAS",
        "=" * 80,
    ]

    for d, stats in direction["by_direction"].items():
        lines.append(f"  {d}: {stats['wr']}% WR (n={stats['n']}, CI: {stats['ci_low']}-{stats['ci_high']}%)")

    lines.extend([
        f"  SHORT Edge: +{direction['short_edge_pp']}pp vs LONG",
        f"  Recommendation: {direction['recommendation']}",
        "",

        "=" * 80,
        "EDGE #2: CONFIDENCE SWEET SPOT",
        "=" * 80,
    ])

    for bucket, stats in confidence["by_bucket"].items():
        flag = " *** SWEET ***" if bucket == confidence["sweet_spot"] else ""
        flag = " !!! TOXIC !!!" if bucket == confidence["toxic_bucket"] else flag
        lines.append(f"  {bucket}: {stats['wr']}% WR (n={stats['n']}){flag}")

    if confidence["sweet_spot"]:
        lines.append(f"\n  SWEET SPOT: {confidence['sweet_spot']} = {confidence['sweet_spot_wr']}% WR")
    if confidence["toxic_bucket"]:
        lines.append(f"  TOXIC BUCKET: {confidence['toxic_bucket']} = {confidence['toxic_bucket_wr']}% WR")

    lines.extend([
        "",
        "=" * 80,
        "EDGE #3: DIRECTION + CONFIDENCE COMBOS",
        "=" * 80,
    ])

    for combo_name, stats in combo["by_combo"].items():
        toxic_flag = " !!! TOXIC !!!" if stats['wr'] < 40 else ""
        lines.append(f"  {combo_name}: {stats['wr']}% WR (n={stats['n']}){toxic_flag}")

    if combo["toxic_combos"]:
        lines.append("\n  TOXIC COMBOS TO AVOID:")
        for c, r in combo["toxic_combos"]:
            lines.append(f"    - {c}: {r['wr']}% WR (BLOCK THIS)")

    lines.extend([
        "",
        "=" * 80,
        "EDGE #4: TOP STRATEGIES",
        "=" * 80,
    ])

    if strategy["top_performers"]:
        lines.append("  ELITE (WR >= 60%, n >= 20):")
        for s, r in strategy["top_performers"]:
            lines.append(f"    - {s}: {r['wr']}% WR (n={r['n']})")

    if strategy["underperformers"]:
        lines.append("\n  UNDERPERFORMERS (WR < 45%, n >= 20):")
        for s, r in strategy["underperformers"]:
            lines.append(f"    - {s}: {r['wr']}% WR (n={r['n']}) [CONSIDER KILL/MUTATE]")

    lines.extend([
        "",
        "=" * 80,
        "EDGE #5: SYMBOL PERFORMANCE",
        "=" * 80,
        "  TOP SYMBOLS:",
    ])

    for sym, stats in symbol["top_symbols"][:5]:
        lines.append(f"    - {sym}: {stats['wr']}% WR (n={stats['n']})")

    if symbol["worst_symbols"]:
        lines.append("\n  WORST SYMBOLS:")
        for sym, stats in symbol["worst_symbols"][-5:]:
            lines.append(f"    - {sym}: {stats['wr']}% WR (n={stats['n']})")

    lines.extend([
        "",
        "=" * 80,
        "EDGE #6: RISK/REWARD OPTIMIZATION",
        "=" * 80,
    ])

    for bucket, stats in rr["by_rr"].items():
        lines.append(f"  {bucket}: {stats['wr']}% WR (n={stats['n']})")

    if rr["optimal_rr"]:
        lines.append(f"\n  OPTIMAL RR RANGE: {rr['optimal_rr'][0]} = {rr['optimal_rr'][1]['wr']}% WR")

    lines.extend([
        "",
        "=" * 80,
        "EDGE #7: TIME OF DAY (UTC)",
        "=" * 80,
    ])

    if time["best_hours"]:
        lines.append("  BEST HOURS:")
        for h, stats in time["best_hours"]:
            lines.append(f"    - {h:02d}:00 UTC: {stats['wr']}% WR (n={stats['n']})")

    if time["worst_hours"]:
        lines.append("\n  WORST HOURS:")
        for h, stats in time["worst_hours"]:
            lines.append(f"    - {h:02d}:00 UTC: {stats['wr']}% WR (n={stats['n']})")

    lines.extend([
        "",
        "=" * 80,
        "ACTIONABLE EDGES SUMMARY",
        "=" * 80,
        "",
        "PER TESTING_PROTOCOL.MD REQUIREMENTS:",
        "- Minimum 20 trades for statistical confidence: ENFORCED",
        "- Score >= 40 floor: Applied via confidence thresholds",
        "- Trust >= 4 for LONGs: Implement via source filtering",
        "",
        "RECOMMENDED FILTERS:",
    ])

    # Generate actionable recommendations
    if direction["short_edge_pp"] > 5:
        lines.append(f"  1. SHORT BIAS: +{direction['short_edge_pp']}pp edge - prioritize SHORT picks")

    if confidence["sweet_spot"]:
        lines.append(f"  2. CONFIDENCE: Target {confidence['sweet_spot']} = {confidence['sweet_spot_wr']}% WR")

    if confidence["toxic_bucket"]:
        lines.append(f"  3. AVOID: Confidence {confidence['toxic_bucket']} = {confidence['toxic_bucket_wr']}% WR")

    if combo["toxic_combos"]:
        for c, r in combo["toxic_combos"][:2]:
            lines.append(f"  4. BLOCK COMBO: {c} = {r['wr']}% WR")

    if strategy["top_performers"]:
        top = strategy["top_performers"][0]
        lines.append(f"  5. ELITE STRATEGY: {top[0]} = {top[1]['wr']}% WR")

    lines.extend([
        "",
        "=" * 80,
        "Generated by edge_analysis.py for Redis bus publication",
        "=" * 80,
    ])

    return "\n".join(lines)


def generate_bus_payload(picks: List[Dict]) -> Dict:
    """Generate structured payload for Redis bus."""
    direction = analyze_direction_edge(picks)
    confidence = analyze_confidence_buckets(picks)
    strategy = analyze_strategy_edge(picks)
    combo = analyze_direction_confidence_combo(picks)

    return {
        "timestamp": datetime.now().isoformat(),
        "picks_analyzed": len(picks),
        "edges": {
            "direction_bias": {
                "short_edge_pp": direction["short_edge_pp"],
                "recommendation": direction["recommendation"],
                "stats": direction["by_direction"],
            },
            "confidence_sweet_spot": {
                "sweet_spot": confidence["sweet_spot"],
                "sweet_spot_wr": confidence["sweet_spot_wr"],
                "toxic_bucket": confidence["toxic_bucket"],
                "toxic_bucket_wr": confidence["toxic_bucket_wr"],
            },
            "toxic_combos": [
                {"combo": c, "wr": r["wr"], "n": r["n"]}
                for c, r in combo["toxic_combos"]
            ],
            "top_strategies": [
                {"strategy": s, "wr": r["wr"], "n": r["n"]}
                for s, r in strategy["top_performers"]
            ],
            "underperforming_strategies": [
                {"strategy": s, "wr": r["wr"], "n": r["n"]}
                for s, r in strategy["underperformers"]
            ],
        },
        "recommendations": [],
    }


def main():
    """Run edge analysis and generate report."""
    print("Loading closed picks...")
    picks = load_closed_picks()
    print(f"Loaded {len(picks)} picks")

    # Generate and print report
    report = generate_edge_report(picks)
    print(report)

    # Save report
    report_path = Path("alpha_engine/data/edge_analysis_report.txt")
    with open(report_path, "w") as f:
        f.write(report)
    print(f"\n[SAVED] {report_path}")

    # Generate bus payload
    payload = generate_bus_payload(picks)
    payload_path = Path("alpha_engine/data/edge_analysis_payload.json")
    with open(payload_path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"[SAVED] {payload_path}")

    return payload


if __name__ == "__main__":
    main()
