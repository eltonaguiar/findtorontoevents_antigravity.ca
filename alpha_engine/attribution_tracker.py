"""
Performance Attribution Tracker
================================

Decomposes closed-pick PnL into regime, temporal, and source factors to
identify WHICH conditions drove each strategy's edge. Output informs
dynamic scoring weights (instead of static penalties in quality_gates.py).

Key questions answered:
  1. Regime: does strategy X edge come from bull, bear, or range regimes?
  2. Time: which hour of day / day of week drives the edge?
  3. Source: which upstream systems contribute the most to PnL?
  4. Symbol: is edge concentrated or distributed across symbols?

Input: alpha_engine/data/closed_picks.json OR
       audit_trail/data/dashboard_payload.json picks.recent_closed

Output: alpha_engine/data/attribution_report.json
        Schema: {
          "generated_at": ISO8601,
          "total_closed": int,
          "by_strategy": { strategy_name: { edge_factors } },
          "by_source": { source_name: { edge_factors } },
          "global_factors": { regime, time, symbol edges },
          "actionable_insights": [{finding, evidence, recommended_action}]
        }

Usage:
    python -m alpha_engine.attribution_tracker
    # or
    from alpha_engine.attribution_tracker import build_attribution_report
    report = build_attribution_report()

Author: claude-opus-scoring (2026-04-04)
Bridges #1 architectural gap per bus debate with claude-bus-setup.
"""
from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────
# Data paths
# ──────────────────────────────────────────────────────────────────────────
_REPO = Path(__file__).resolve().parent.parent
_CLOSED_PICKS_PATH = _REPO / "alpha_engine" / "data" / "closed_picks.json"
_DASHBOARD_PAYLOAD_PATH = _REPO / "audit_trail" / "data" / "dashboard_payload.json"
_OUTPUT_PATH = _REPO / "alpha_engine" / "data" / "attribution_report.json"

# Minimum sample sizes for statistical claims
MIN_TRADES_STRATEGY = 10
MIN_TRADES_SOURCE = 10
MIN_TRADES_FACTOR = 20


# ──────────────────────────────────────────────────────────────────────────
# Load data
# ──────────────────────────────────────────────────────────────────────────
def _load_closed_picks() -> List[Dict[str, Any]]:
    """Load closed picks from the richest available source."""
    picks: List[Dict[str, Any]] = []

    # Prefer dashboard payload (has scoring metadata)
    if _DASHBOARD_PAYLOAD_PATH.exists():
        try:
            with open(_DASHBOARD_PAYLOAD_PATH, encoding="utf-8") as f:
                payload = json.load(f)
            dash_closed = payload.get("picks", {}).get("recent_closed", [])
            if dash_closed:
                picks.extend(dash_closed)
                logger.info("Loaded %d closed picks from dashboard_payload.json", len(dash_closed))
        except Exception as e:
            logger.warning("Failed to load dashboard payload: %s", e)

    # Fallback: alpha_engine closed picks
    if not picks and _CLOSED_PICKS_PATH.exists():
        try:
            with open(_CLOSED_PICKS_PATH, encoding="utf-8") as f:
                picks = json.load(f)
            logger.info("Loaded %d closed picks from closed_picks.json", len(picks))
        except Exception as e:
            logger.warning("Failed to load closed_picks.json: %s", e)

    return picks


# ──────────────────────────────────────────────────────────────────────────
# Factor extraction
# ──────────────────────────────────────────────────────────────────────────
def _extract_factors(pick: Dict[str, Any]) -> Dict[str, Any]:
    """Extract all factors for a pick: regime, time, source, symbol."""
    factors: Dict[str, Any] = {}

    # PnL (the dependent variable)
    pnl = pick.get("pnl_pct", 0) or 0
    factors["pnl"] = float(pnl)
    factors["win"] = pnl > 0

    # Source factors
    factors["strategy"] = str(pick.get("strategy", "unknown"))
    factors["source"] = str(pick.get("source_system", pick.get("source", "unknown")))
    factors["symbol"] = str(pick.get("symbol", "unknown"))
    factors["direction"] = str(pick.get("direction", "LONG")).upper()
    factors["asset_class"] = str(pick.get("asset_class", "CRYPTO")).upper()

    # Regime factors
    fgi = pick.get("fear_greed")
    if fgi is not None:
        fgi_val = int(fgi)
        factors["fgi"] = fgi_val
        if fgi_val < 20:
            factors["fgi_regime"] = "extreme_fear"
        elif fgi_val < 40:
            factors["fgi_regime"] = "fear"
        elif fgi_val < 60:
            factors["fgi_regime"] = "neutral"
        elif fgi_val < 80:
            factors["fgi_regime"] = "greed"
        else:
            factors["fgi_regime"] = "extreme_greed"
    else:
        factors["fgi_regime"] = "unknown"

    # BTC regime (if stored)
    btc_regime = str(pick.get("btc_regime", pick.get("regime_at_entry", "")) or "").upper()
    if "BULL" in btc_regime or "UP" in btc_regime:
        factors["trend_regime"] = "bull"
    elif "BEAR" in btc_regime or "DOWN" in btc_regime:
        factors["trend_regime"] = "bear"
    elif "RANG" in btc_regime or "SIDE" in btc_regime or "NEUTRAL" in btc_regime:
        factors["trend_regime"] = "range"
    else:
        factors["trend_regime"] = "unknown"

    # Time factors
    entry_ts = pick.get("entry_date") or pick.get("opened_at") or pick.get("timestamp")
    if entry_ts:
        try:
            dt = datetime.fromisoformat(str(entry_ts).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            factors["hour_utc"] = dt.hour
            factors["dow"] = dt.weekday()  # 0=Mon, 6=Sun
            factors["dow_name"] = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()]
            factors["month"] = dt.month
            # Time-of-day bucket
            h = dt.hour
            if h < 6:
                factors["time_bucket"] = "night_00_06"
            elif h < 12:
                factors["time_bucket"] = "morning_06_12"
            elif h < 18:
                factors["time_bucket"] = "afternoon_12_18"
            else:
                factors["time_bucket"] = "evening_18_24"
        except (ValueError, TypeError, AttributeError):
            factors["hour_utc"] = None
            factors["dow"] = None

    # Score bucket
    score = pick.get("score", 0) or 0
    if score >= 80:
        factors["score_tier"] = "elite_80+"
    elif score >= 60:
        factors["score_tier"] = "strong_60_79"
    elif score >= 40:
        factors["score_tier"] = "viable_40_59"
    elif score >= 20:
        factors["score_tier"] = "weak_20_39"
    else:
        factors["score_tier"] = "reject_<20"

    # Confidence bucket
    conf = pick.get("confidence", 0) or 0
    if conf >= 0.90:
        factors["conf_bucket"] = "overconf_0.90+"
    elif conf >= 0.80:
        factors["conf_bucket"] = "high_0.80_89"
    elif conf >= 0.75:
        factors["conf_bucket"] = "sweet_0.75_79"
    elif conf >= 0.70:
        factors["conf_bucket"] = "good_0.70_74"
    elif conf >= 0.60:
        factors["conf_bucket"] = "mid_0.60_69"
    else:
        factors["conf_bucket"] = "low_<0.60"

    return factors


# ──────────────────────────────────────────────────────────────────────────
# Attribution calculation
# ──────────────────────────────────────────────────────────────────────────
def _aggregate_by(picks_factors: List[Dict[str, Any]], group_key: str,
                  min_trades: int = MIN_TRADES_FACTOR) -> Dict[str, Dict[str, Any]]:
    """Group picks by a factor key, compute WR/PnL/contribution per group."""
    groups: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"trades": 0, "wins": 0, "losses": 0, "pnl": 0.0, "pnl_pos": 0.0, "pnl_neg": 0.0}
    )
    for f in picks_factors:
        val = f.get(group_key)
        if val is None or val == "" or val == "unknown":
            continue
        g = groups[str(val)]
        g["trades"] += 1
        pnl = f["pnl"]
        g["pnl"] += pnl
        if f["win"]:
            g["wins"] += 1
            g["pnl_pos"] += pnl
        else:
            g["losses"] += 1
            g["pnl_neg"] += pnl

    # Filter by min_trades and add derived metrics
    result: Dict[str, Dict[str, Any]] = {}
    for key, g in groups.items():
        if g["trades"] < min_trades:
            continue
        wr = g["wins"] / g["trades"] if g["trades"] > 0 else 0
        pf = (g["pnl_pos"] / abs(g["pnl_neg"])) if g["pnl_neg"] < 0 else float("inf")
        avg_pnl = g["pnl"] / g["trades"] if g["trades"] > 0 else 0
        result[key] = {
            "trades": g["trades"],
            "wins": g["wins"],
            "losses": g["losses"],
            "wr": round(wr, 4),
            "total_pnl": round(g["pnl"], 2),
            "avg_pnl": round(avg_pnl, 4),
            "profit_factor": round(pf, 2) if pf != float("inf") else None,
        }
    return result


def _attribute_strategy_edges(picks_factors: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """For each strategy, decompose its edge by regime/time/symbol factors."""
    # Group picks by strategy
    by_strategy: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for f in picks_factors:
        by_strategy[f["strategy"]].append(f)

    attribution: Dict[str, Dict[str, Any]] = {}
    for strat, strat_picks in by_strategy.items():
        if len(strat_picks) < MIN_TRADES_STRATEGY:
            continue

        overall_wr = sum(1 for p in strat_picks if p["win"]) / len(strat_picks)
        overall_pnl = sum(p["pnl"] for p in strat_picks)

        # Decompose by each factor
        factor_breakdown: Dict[str, Any] = {}
        for factor_key in ("fgi_regime", "trend_regime", "time_bucket", "dow_name",
                           "direction", "symbol", "conf_bucket"):
            sub = _aggregate_by(strat_picks, factor_key, min_trades=3)
            if sub:
                # Find the bucket with highest deviation from overall WR
                best = max(sub.items(), key=lambda kv: kv[1]["wr"])
                worst = min(sub.items(), key=lambda kv: kv[1]["wr"])
                factor_breakdown[factor_key] = {
                    "best": {"bucket": best[0], **best[1], "wr_delta": round(best[1]["wr"] - overall_wr, 4)},
                    "worst": {"bucket": worst[0], **worst[1], "wr_delta": round(worst[1]["wr"] - overall_wr, 4)},
                }

        attribution[strat] = {
            "trades": len(strat_picks),
            "overall_wr": round(overall_wr, 4),
            "overall_pnl": round(overall_pnl, 2),
            "factor_breakdown": factor_breakdown,
        }
    return attribution


def _find_actionable_insights(
    global_factors: Dict[str, Dict[str, Dict[str, Any]]],
    strategy_attribution: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Generate actionable insights from attribution data."""
    insights: List[Dict[str, Any]] = []

    # Insight 1: Global factor extremes (WR spread > 15pp)
    for factor_key, buckets in global_factors.items():
        if len(buckets) < 2:
            continue
        sorted_buckets = sorted(buckets.items(), key=lambda kv: kv[1]["wr"], reverse=True)
        top_bucket, top_data = sorted_buckets[0]
        bottom_bucket, bottom_data = sorted_buckets[-1]
        spread = top_data["wr"] - bottom_data["wr"]
        if spread >= 0.15 and top_data["trades"] >= 20 and bottom_data["trades"] >= 20:
            insights.append({
                "finding": f"Global {factor_key} edge: {top_bucket} vs {bottom_bucket}",
                "evidence": {
                    "top": {"bucket": top_bucket, "wr": top_data["wr"], "trades": top_data["trades"]},
                    "bottom": {"bucket": bottom_bucket, "wr": bottom_data["wr"], "trades": bottom_data["trades"]},
                    "spread_pp": round(spread * 100, 1),
                },
                "recommended_action": (
                    f"Add scoring weight: +{int(spread * 50)} for {factor_key}={top_bucket}, "
                    f"-{int(spread * 50)} for {factor_key}={bottom_bucket}"
                ),
            })

    # Insight 2: Strategies with regime-dependent edge (could become variants)
    for strat, attr in strategy_attribution.items():
        fgi_bd = attr.get("factor_breakdown", {}).get("fgi_regime")
        trend_bd = attr.get("factor_breakdown", {}).get("trend_regime")
        for bd_name, bd in [("fgi_regime", fgi_bd), ("trend_regime", trend_bd)]:
            if not bd:
                continue
            best_delta = bd["best"]["wr_delta"]
            worst_delta = bd["worst"]["wr_delta"]
            if best_delta > 0.15 and bd["best"]["trades"] >= 5:
                insights.append({
                    "finding": (
                        f"{strat} has regime-specific edge on {bd_name}={bd['best']['bucket']} "
                        f"(WR delta: +{round(best_delta*100, 1)}pp)"
                    ),
                    "evidence": bd["best"],
                    "recommended_action": (
                        f"Consider creating variant: {strat}_{bd_name}_{bd['best']['bucket']} "
                        f"that only fires in this regime"
                    ),
                })

    # Insight 3: Direction asymmetries
    for strat, attr in strategy_attribution.items():
        dir_bd = attr.get("factor_breakdown", {}).get("direction")
        if dir_bd and dir_bd["best"]["trades"] >= 5 and dir_bd["worst"]["trades"] >= 5:
            spread = dir_bd["best"]["wr"] - dir_bd["worst"]["wr"]
            if spread > 0.20:
                insights.append({
                    "finding": (
                        f"{strat} direction asymmetry: {dir_bd['best']['bucket']} wins "
                        f"{round(spread*100,1)}pp more than {dir_bd['worst']['bucket']}"
                    ),
                    "evidence": {"best_dir": dir_bd["best"], "worst_dir": dir_bd["worst"]},
                    "recommended_action": (
                        f"Direction-filter: deploy {strat}_{dir_bd['best']['bucket'].lower()}_only mutation"
                    ),
                })

    return insights


# ──────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────
def build_attribution_report() -> Dict[str, Any]:
    """Build full attribution report and save to JSON."""
    picks = _load_closed_picks()
    if not picks:
        logger.warning("No closed picks loaded; skipping attribution report")
        return {}

    # Extract factors for each pick
    picks_factors = [_extract_factors(p) for p in picks]

    # Global factor aggregations
    global_factors = {
        "fgi_regime": _aggregate_by(picks_factors, "fgi_regime"),
        "trend_regime": _aggregate_by(picks_factors, "trend_regime"),
        "time_bucket": _aggregate_by(picks_factors, "time_bucket"),
        "dow_name": _aggregate_by(picks_factors, "dow_name"),
        "direction": _aggregate_by(picks_factors, "direction"),
        "conf_bucket": _aggregate_by(picks_factors, "conf_bucket"),
        "score_tier": _aggregate_by(picks_factors, "score_tier"),
        "asset_class": _aggregate_by(picks_factors, "asset_class"),
    }

    # Source system attribution
    by_source = _aggregate_by(picks_factors, "source", min_trades=MIN_TRADES_SOURCE)

    # Strategy-level attribution with factor breakdown
    by_strategy = _attribute_strategy_edges(picks_factors)

    # Generate insights
    insights = _find_actionable_insights(global_factors, by_strategy)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_closed": len(picks),
        "global_factors": global_factors,
        "by_source": by_source,
        "by_strategy": by_strategy,
        "actionable_insights": insights,
        "meta": {
            "min_trades_strategy": MIN_TRADES_STRATEGY,
            "min_trades_source": MIN_TRADES_SOURCE,
            "min_trades_factor": MIN_TRADES_FACTOR,
        },
    }

    # Save
    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    logger.info("Attribution report written to %s", _OUTPUT_PATH)
    return report


def print_summary(report: Dict[str, Any]) -> None:
    """Print a human-readable summary of the report."""
    if not report:
        print("No report generated (no closed picks)")
        return

    print(f"\n=== PERFORMANCE ATTRIBUTION REPORT ===")
    print(f"Total closed picks: {report['total_closed']}")
    print(f"Generated: {report['generated_at']}")

    print(f"\n=== GLOBAL FACTOR EDGES (min 20 trades) ===")
    for factor_key, buckets in report["global_factors"].items():
        if not buckets:
            continue
        print(f"\n  {factor_key}:")
        for bucket, data in sorted(buckets.items(), key=lambda kv: -kv[1]["wr"])[:5]:
            print(f"    {bucket:<22s} WR={data['wr']*100:5.1f}%  n={data['trades']:>4}  PnL={data['total_pnl']:+7.1f}%")

    print(f"\n=== TOP STRATEGIES BY EDGE ===")
    strats = sorted(report["by_strategy"].items(),
                    key=lambda kv: kv[1]["overall_wr"], reverse=True)[:10]
    for strat, attr in strats:
        print(f"  {strat[:40]:<40s} WR={attr['overall_wr']*100:5.1f}%  n={attr['trades']}  PnL={attr['overall_pnl']:+7.1f}%")

    print(f"\n=== TOP SOURCES BY EDGE ===")
    sources = sorted(report["by_source"].items(),
                     key=lambda kv: kv[1]["wr"], reverse=True)[:10]
    for src, data in sources:
        print(f"  {src[:40]:<40s} WR={data['wr']*100:5.1f}%  n={data['trades']}  PnL={data['total_pnl']:+7.1f}%")

    print(f"\n=== ACTIONABLE INSIGHTS ({len(report['actionable_insights'])} found) ===")
    for i, insight in enumerate(report["actionable_insights"][:10], 1):
        print(f"\n{i}. {insight['finding']}")
        print(f"   → {insight['recommended_action']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    report = build_attribution_report()
    print_summary(report)
