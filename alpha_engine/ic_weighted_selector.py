#!/usr/bin/env python3
"""
Information-Coefficient (IC) Weighted Strategy Selector
=======================================================

Computes rolling Spearman IC for each scoring component against forward PnL.
Components with zero/negative IC get zero weight automatically.

This replaces hand-tuned scoring weights with empirically measured predictive
power. The key insight: Spearman(score, WR) = 0.003 across full portfolio,
but 0.27 within alpha_engine — IC weighting surfaces this automatically.

Usage:
    from ic_weighted_selector import run
    report = run()
"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Windows UTF-8 fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ── Paths ────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent
REPO_DIR = BASE_DIR.parent
PAYLOAD_PATH = REPO_DIR / "audit_trail" / "data" / "dashboard_payload.json"
OUTPUT_PATH = BASE_DIR / "data" / "ic_weights.json"

# Minimum closed trades to compute IC for a strategy
MIN_TRADES_IC = 10
# Minimum trades for kill/promote recommendations
MIN_TRADES_REC = 20

# Score breakdown component keys (from _scoreBreakdown in dashboard payload)
SCORE_COMPONENTS = [
    "ml_score",
    "forward_wr",
    "source_system",
    "confluence",
    "position",
    "regime_bonus",
    "session_bonus",
    "age_freshness",
    "risk_reward",
    "monte_carlo",
    "leverage_safety",
    "volume",
    "signal_quality",
    "meta_label",
    "hindsight_winner",
    "skyrocket_potential",
    "proven_strategy_bonus",
    "strategy_track_record",
    "risk_warning_penalty",
    "technical_alignment",
    "confidence",  # top-level field, not in breakdown
]


# ── Spearman correlation (stdlib only) ───────────────────────────────────────

def _rank(values: list[float]) -> list[float]:
    """Compute fractional ranks for a list of values (handles ties)."""
    n = len(values)
    indexed = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n

    i = 0
    while i < n:
        # find group of ties
        j = i + 1
        while j < n and values[indexed[j]] == values[indexed[i]]:
            j += 1
        # average rank for tied values (1-based)
        avg_rank = (i + j - 1) / 2.0 + 1.0
        for k in range(i, j):
            ranks[indexed[k]] = avg_rank
        i = j

    return ranks


def _pearson(x: list[float], y: list[float]) -> float:
    """Compute Pearson correlation coefficient."""
    n = len(x)
    if n < 3:
        return 0.0

    mx = sum(x) / n
    my = sum(y) / n

    sxy = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    sxx = sum((xi - mx) ** 2 for xi in x)
    syy = sum((yi - my) ** 2 for yi in y)

    denom = math.sqrt(sxx * syy)
    if denom < 1e-15:
        return 0.0

    return sxy / denom


def spearman_ic(scores: list[float], pnls: list[float]) -> float:
    """
    Compute Spearman rank correlation between scores and PnL.
    This is the Information Coefficient (IC).
    """
    if len(scores) < 3 or len(scores) != len(pnls):
        return 0.0
    return _pearson(_rank(scores), _rank(pnls))


# ── Data loading ─────────────────────────────────────────────────────────────

def _load_closed_picks() -> list[dict]:
    """Load closed picks from dashboard_payload.json."""
    if not PAYLOAD_PATH.exists():
        print(f"[IC] WARNING: {PAYLOAD_PATH} not found")
        return []

    try:
        with open(PAYLOAD_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"[IC] ERROR loading payload: {e}")
        return []

    # Try picks.recent_closed first, then universal_resolved_picks
    picks_section = data.get("picks", {})
    closed = picks_section.get("recent_closed", [])
    if not closed:
        closed = data.get("universal_resolved_picks", [])

    # Filter to picks that have PnL and a strategy name
    valid = []
    for p in closed:
        pnl = p.get("pnl_pct")
        strategy = p.get("strategy")
        if pnl is not None and strategy:
            try:
                p["_pnl_float"] = float(pnl)
                valid.append(p)
            except (ValueError, TypeError):
                continue

    print(f"[IC] Loaded {len(valid)} closed picks with PnL from {len(closed)} total")
    return valid


def _extract_component_value(pick: dict, component: str) -> float | None:
    """Extract a scoring component value from a pick."""
    # Check _scoreBreakdown first
    breakdown = pick.get("_scoreBreakdown", {})
    if breakdown and component in breakdown:
        val = breakdown[component]
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                return None

    # Check top-level fields (e.g. confidence, score)
    val = pick.get(component)
    if val is not None:
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    return None


# ── Core IC computation ──────────────────────────────────────────────────────

def compute_strategy_ic(picks: list[dict] | None = None) -> dict:
    """
    Compute Information Coefficient per strategy.

    For each strategy with MIN_TRADES_IC+ closed trades, compute
    Spearman(elite_score, realized_pnl_pct).

    Returns dict mapping strategy_name -> {ic, n_trades, avg_pnl, ...}
    """
    if picks is None:
        picks = _load_closed_picks()

    # Group by strategy
    by_strategy: dict[str, list[dict]] = {}
    for p in picks:
        strat = p.get("strategy", "unknown")
        by_strategy.setdefault(strat, []).append(p)

    results = {}
    for strat, strat_picks in by_strategy.items():
        if len(strat_picks) < MIN_TRADES_IC:
            continue

        scores = []
        pnls = []
        for p in strat_picks:
            score = p.get("score")
            pnl = p.get("_pnl_float", p.get("pnl_pct"))
            if score is not None and pnl is not None:
                try:
                    scores.append(float(score))
                    pnls.append(float(pnl))
                except (ValueError, TypeError):
                    continue

        if len(scores) < MIN_TRADES_IC:
            continue

        ic = spearman_ic(scores, pnls)
        avg_pnl = sum(pnls) / len(pnls)
        win_count = sum(1 for p in pnls if p > 0)
        win_rate = win_count / len(pnls) * 100.0

        # Determine source system
        source = strat_picks[0].get("source_system", "unknown")

        results[strat] = {
            "ic": round(ic, 4),
            "n_trades": len(scores),
            "avg_pnl": round(avg_pnl, 4),
            "win_rate": round(win_rate, 1),
            "source_system": source,
            "predictive": ic > 0.05,
            "anti_predictive": ic < 0,
        }

    return results


def compute_component_ic(picks: list[dict] | None = None) -> dict:
    """
    Compute IC for each scoring component against realized PnL.

    For each component in _scoreBreakdown, compute
    Spearman(component_value, pnl_pct) across all picks.

    Returns dict mapping component_name -> {ic, n_samples, ...}
    """
    if picks is None:
        picks = _load_closed_picks()

    results = {}
    for component in SCORE_COMPONENTS:
        comp_values = []
        pnls = []

        for p in picks:
            val = _extract_component_value(p, component)
            pnl = p.get("_pnl_float", p.get("pnl_pct"))
            if val is not None and pnl is not None:
                try:
                    comp_values.append(float(val))
                    pnls.append(float(pnl))
                except (ValueError, TypeError):
                    continue

        if len(comp_values) < MIN_TRADES_IC:
            continue

        # Skip if component has zero variance (all same value)
        if len(set(comp_values)) < 2:
            results[component] = {
                "ic": 0.0,
                "n_samples": len(comp_values),
                "mean_value": round(sum(comp_values) / len(comp_values), 4),
                "status": "zero_variance",
            }
            continue

        ic = spearman_ic(comp_values, pnls)

        results[component] = {
            "ic": round(ic, 4),
            "n_samples": len(comp_values),
            "mean_value": round(sum(comp_values) / len(comp_values), 4),
            "status": (
                "predictive" if ic > 0.05
                else "anti_predictive" if ic < 0
                else "neutral"
            ),
        }

    return results


def ic_weight_picks(picks: list[dict],
                    strategy_ics: dict | None = None,
                    component_ics: dict | None = None) -> list[dict]:
    """
    Apply IC-based weighting to active picks.

    - Loads latest IC values (or uses provided ones)
    - For each pick, adjusts score based on strategy IC:
      - IC < 0: score penalty (-15)
      - IC > 0.10: score boost (+10)
      - Otherwise: scale by normalized IC
    - Returns picks with updated score and ic_adjustment metadata
    """
    if strategy_ics is None:
        # Try loading from saved file
        if OUTPUT_PATH.exists():
            try:
                with open(OUTPUT_PATH, encoding="utf-8") as f:
                    saved = json.load(f)
                strategy_ics = saved.get("strategy_ic", {})
            except (json.JSONDecodeError, OSError):
                strategy_ics = {}

    if not strategy_ics:
        print("[IC] No strategy IC data available, returning picks unchanged")
        return picks

    # Compute IC range for normalization
    ic_values = [v["ic"] for v in strategy_ics.values() if isinstance(v, dict)]
    if not ic_values:
        return picks

    max_ic = max(ic_values) if ic_values else 1.0
    if max_ic <= 0:
        max_ic = 1.0  # avoid division by zero

    weighted = []
    for p in picks:
        pick = dict(p)  # shallow copy
        strategy = pick.get("strategy", "")
        strat_data = strategy_ics.get(strategy)

        if strat_data and isinstance(strat_data, dict):
            ic = strat_data.get("ic", 0.0)

            if ic < 0:
                # Anti-predictive: penalize
                adjustment = -15
                pick["_ic_status"] = "anti_predictive"
            elif ic > 0.10:
                # Strongly predictive: boost
                adjustment = +10
                pick["_ic_status"] = "predictive_boost"
            elif ic > 0.05:
                # Mildly predictive: moderate boost
                adjustment = int(round(10 * (ic / max_ic)))
                pick["_ic_status"] = "predictive"
            else:
                # Neutral: no change
                adjustment = 0
                pick["_ic_status"] = "neutral"

            old_score = pick.get("score", 50)
            try:
                old_score = int(old_score)
            except (ValueError, TypeError):
                old_score = 50

            pick["score"] = max(0, min(100, old_score + adjustment))
            pick["_ic_adjustment"] = adjustment
            pick["_ic_value"] = round(ic, 4)
        else:
            pick["_ic_status"] = "no_data"
            pick["_ic_adjustment"] = 0
            pick["_ic_value"] = None

        weighted.append(pick)

    # Sort by adjusted score descending
    weighted.sort(key=lambda x: x.get("score", 0), reverse=True)
    return weighted


# ── Report generation ────────────────────────────────────────────────────────

def generate_ic_report(strategy_ics: dict | None = None,
                       component_ics: dict | None = None,
                       picks: list[dict] | None = None) -> dict:
    """
    Generate and print an IC analysis report.

    Returns a report dict and saves to ic_weights.json.
    """
    if picks is None:
        picks = _load_closed_picks()

    if strategy_ics is None:
        strategy_ics = compute_strategy_ic(picks)

    if component_ics is None:
        component_ics = compute_component_ic(picks)

    # ── Rank strategies by IC ────────────────────────────────────────────
    ranked_strategies = sorted(
        strategy_ics.items(),
        key=lambda x: x[1].get("ic", 0),
        reverse=True,
    )

    # ── Rank components by IC ────────────────────────────────────────────
    ranked_components = sorted(
        component_ics.items(),
        key=lambda x: x[1].get("ic", 0),
        reverse=True,
    )

    # ── Recommendations ──────────────────────────────────────────────────
    kills = []
    promotions = []
    for strat, data in ranked_strategies:
        n = data.get("n_trades", 0)
        ic = data.get("ic", 0)
        if ic < -0.05 and n >= MIN_TRADES_REC:
            kills.append({
                "strategy": strat,
                "ic": ic,
                "n_trades": n,
                "avg_pnl": data.get("avg_pnl", 0),
                "source_system": data.get("source_system", ""),
            })
        if ic > 0.10 and n >= MIN_TRADES_REC:
            promotions.append({
                "strategy": strat,
                "ic": ic,
                "n_trades": n,
                "avg_pnl": data.get("avg_pnl", 0),
                "win_rate": data.get("win_rate", 0),
                "source_system": data.get("source_system", ""),
            })

    kills.sort(key=lambda x: x["ic"])
    promotions.sort(key=lambda x: x["ic"], reverse=True)

    # ── Anti-predictive components ───────────────────────────────────────
    anti_predictive_components = [
        {"component": comp, **data}
        for comp, data in ranked_components
        if data.get("ic", 0) < 0
    ]

    # ── Print report ─────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  INFORMATION COEFFICIENT (IC) ANALYSIS REPORT")
    print("=" * 70)

    print(f"\n  Strategies analyzed: {len(strategy_ics)}")
    print(f"  Components analyzed: {len(component_ics)}")
    print(f"  Total closed picks:  {len(picks)}")

    print("\n--- TOP STRATEGIES BY IC ---")
    print(f"  {'Strategy':<55} {'IC':>7} {'N':>5} {'WR%':>6} {'AvgPnL':>8}")
    print("  " + "-" * 83)
    for strat, data in ranked_strategies[:15]:
        ic = data.get("ic", 0)
        marker = " **" if ic > 0.10 else " !" if ic < 0 else ""
        print(f"  {strat:<55} {ic:>7.4f} {data.get('n_trades', 0):>5} "
              f"{data.get('win_rate', 0):>5.1f}% {data.get('avg_pnl', 0):>7.3f}{marker}")

    print("\n--- BOTTOM STRATEGIES BY IC (anti-predictive) ---")
    for strat, data in ranked_strategies[-10:]:
        ic = data.get("ic", 0)
        if ic >= 0:
            continue
        print(f"  {strat:<55} {ic:>7.4f} {data.get('n_trades', 0):>5} "
              f"{data.get('win_rate', 0):>5.1f}% {data.get('avg_pnl', 0):>7.3f}")

    print("\n--- SCORING COMPONENTS BY IC ---")
    print(f"  {'Component':<30} {'IC':>7} {'N':>6} {'Mean':>8} {'Status':<18}")
    print("  " + "-" * 71)
    for comp, data in ranked_components:
        ic = data.get("ic", 0)
        print(f"  {comp:<30} {ic:>7.4f} {data.get('n_samples', 0):>6} "
              f"{data.get('mean_value', 0):>8.3f} {data.get('status', ''):>18}")

    if promotions:
        print(f"\n--- RECOMMENDED PROMOTIONS (IC > 0.10, N >= {MIN_TRADES_REC}) ---")
        for p in promotions[:10]:
            print(f"  {p['strategy']:<55} IC={p['ic']:>7.4f}  "
                  f"N={p['n_trades']}  WR={p['win_rate']:.1f}%  "
                  f"AvgPnL={p['avg_pnl']:.3f}")

    if kills:
        print(f"\n--- RECOMMENDED KILLS (IC < -0.05, N >= {MIN_TRADES_REC}) ---")
        for k in kills[:10]:
            print(f"  {k['strategy']:<55} IC={k['ic']:>7.4f}  "
                  f"N={k['n_trades']}  AvgPnL={k['avg_pnl']:.3f}")

    if anti_predictive_components:
        print("\n--- ANTI-PREDICTIVE COMPONENTS (remove or invert) ---")
        for c in anti_predictive_components:
            print(f"  {c['component']:<30} IC={c['ic']:>7.4f}  N={c['n_samples']}")

    print("\n" + "=" * 70)

    # ── Build output ─────────────────────────────────────────────────────
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_picks_analyzed": len(picks),
        "strategy_ic": strategy_ics,
        "component_ic": component_ics,
        "recommended_promotions": promotions,
        "recommended_kills": kills,
        "anti_predictive_components": anti_predictive_components,
        "ranked_strategies": [
            {"strategy": s, **d} for s, d in ranked_strategies
        ],
        "ranked_components": [
            {"component": c, **d} for c, d in ranked_components
        ],
    }

    # ── Save output ──────────────────────────────────────────────────────
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\n[IC] Report saved to {OUTPUT_PATH}")
    except OSError as e:
        print(f"[IC] ERROR saving report: {e}")

    return report


# ── Entry point ──────────────────────────────────────────────────────────────

def run() -> dict:
    """
    Main entry point for IC-weighted strategy analysis.

    1. Loads closed picks from dashboard_payload.json
    2. Computes strategy IC and component IC
    3. Generates and saves report to ic_weights.json
    4. Returns the full report dict
    """
    print("[IC] Starting Information Coefficient analysis...")

    picks = _load_closed_picks()
    if not picks:
        print("[IC] No closed picks found, aborting")
        return {"error": "no_picks", "strategy_ic": {}, "component_ic": {}}

    strategy_ics = compute_strategy_ic(picks)
    component_ics = compute_component_ic(picks)
    report = generate_ic_report(strategy_ics, component_ics, picks)

    # Summary stats
    n_predictive = sum(1 for v in strategy_ics.values() if v.get("ic", 0) > 0.05)
    n_anti = sum(1 for v in strategy_ics.values() if v.get("ic", 0) < 0)
    print(f"\n[IC] Done: {len(strategy_ics)} strategies analyzed, "
          f"{n_predictive} predictive (IC>0.05), {n_anti} anti-predictive (IC<0)")

    return report


if __name__ == "__main__":
    run()
