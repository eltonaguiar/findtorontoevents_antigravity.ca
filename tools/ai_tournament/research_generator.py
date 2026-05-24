"""
AI Tournament Research Generator — creates research topics from model-persona performance data.

Analyzes pick performance per model×persona×asset_class and generates structured
research topics for the research_index pipeline. Identifies gaps, improvement areas,
and validation results.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PICKS_DIR = REPO_ROOT / "data" / "ai_tournament"
RESEARCH_DIR = REPO_ROOT / "audit_dashboard" / "data" / "research"
RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

# ── Research topic severity levels ──

SEVERITY_CRITICAL = "CRITICAL"    # Performance < threshold, needs immediate attention
SEVERITY_IMPROVE = "IMPROVE"      # Below median, room for improvement
SEVERITY_VALIDATE = "VALIDATE"    # Needs more data before conclusion
SEVERITY_CONFIRMED = "CONFIRMED"  # Strategy performing well, confirm effectiveness


def load_latest_picks() -> list[dict]:
    """Load the most recent picks file."""
    if PICKS_DIR.exists():
        files = sorted(PICKS_DIR.glob("picks_*.json"), reverse=True)
        if files:
            data = json.loads(files[0].read_text())
            if isinstance(data, list):
                return data
    return []


def load_historical_picks(days: int = 7) -> list[dict]:
    """Load picks from the last N days."""
    picks = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    if PICKS_DIR.exists():
        for f in sorted(PICKS_DIR.glob("picks_*.json"), reverse=True):
            data = json.loads(f.read_text())
            if isinstance(data, list):
                picks.extend(data)
    return picks


def generate_research_topics(picks: list[dict]) -> list[dict[str, Any]]:
    """Analyze picks and generate research topics per model×persona×asset_class."""
    topics = []

    if not picks:
        topics.append({
            "topic_id": "no_data",
            "title": "Initialize tournament pipeline",
            "severity": SEVERITY_CRITICAL,
            "asset_class": "ALL",
            "description": "No tournament picks found. Pipeline needs to generate initial picks.",
            "recommendation": "Run the AI Tournament Pipeline to generate the first batch of picks.",
            "suggested_experiment": "Generate picks via fallback (local persona engine) to establish baseline, then iterate with API models.",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        })
        return topics

    # Group by model×persona×asset_class
    groups: dict[str, list[dict]] = {}
    for p in picks:
        key = f"{p.get('model_id','?')}|{p.get('persona_id','?')}|{p.get('asset_class','?')}"
        groups.setdefault(key, []).append(p)

    # Analyze each group
    for key, group_picks in groups.items():
        model_id, persona_id, asset_class = key.split("|")

        n_picks = len(group_picks)

        # Confidence stats
        confidences = []
        for p in group_picks:
            v = p.get("confidence", 0.5)
            if isinstance(v, str):
                confidences.append({"HIGH": 0.8, "MEDIUM": 0.5, "LOW": 0.2}.get(v, 0.5))
            else:
                confidences.append(float(v))
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.5

        # Direction split
        longs = sum(1 for p in group_picks if p.get("direction") == "LONG")
        shorts = sum(1 for p in group_picks if p.get("direction") == "SHORT")
        long_pct = longs / n_picks * 100 if n_picks else 0

        # Thesis quality (check if picks have detailed reason/thesis)
        with_reason = sum(1 for p in group_picks if p.get("reason") or (p.get("thesis") and len(p.get("thesis", "")) > 20))
        reason_pct = with_reason / n_picks * 100 if n_picks else 0

        # Generate topics based on analysis
        label = f"{model_id}/{persona_id}/{asset_class}"

        # Topic 1: Confidence calibration
        if avg_conf > 0.8 and n_picks < 20:
            topics.append({
                "topic_id": f"conf_cal_{label}",
                "title": f"Overconfidence risk: {label}",
                "severity": SEVERITY_IMPROVE,
                "asset_class": asset_class,
                "model_id": model_id,
                "persona_id": persona_id,
                "description": f"Average confidence ({avg_conf:.0%}) is high but only {n_picks} picks generated. High confidence with low sample suggests calibration may be unreliable.",
                "recommendation": "Generate more picks (target 50+) before evaluating confidence calibration. Consider applying confidence penalty for samples < 30.",
                "suggested_experiment": "Compare win rate by confidence decile. Good calibration means confident picks (>80%) should win >60% of the time.",
                "metric_current": f"avg_conf={avg_conf:.0%}",
                "metric_target": "conf_score > 0.6 when n > 30",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            })

        # Topic 2: Directional bias
        if long_pct > 90 or long_pct < 10:
            direction = "long" if long_pct > 90 else "short"
            topics.append({
                "topic_id": f"dir_bias_{label}",
                "title": f"Directional bias detected: {label} ({long_pct:.0f}% {direction})",
                "severity": SEVERITY_VALIDATE,
                "asset_class": asset_class,
                "model_id": model_id,
                "persona_id": persona_id,
                "description": f"{long_pct:.0f}% of picks are {direction} — potential uni-directional bias. This may indicate the persona is not adapting to market regime, or the current market favors this direction.",
                "recommendation": "Add market regime filter. In downtrends, bias should shift to short entries. Track directional win rate separately.",
                "suggested_experiment": "Split picks by market regime (trending up, trending down, ranging). Compare directional win rates per regime. Target: <20pp gap between long and short WR.",
                "metric_current": f"{long_pct:.0f}% {direction}",
                "metric_target": "balanced or regime-adaptive",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            })

        # Topic 3: Reason/thesis quality
        if reason_pct < 50:
            topics.append({
                "topic_id": f"reason_quality_{label}",
                "title": f"Incomplete rationale: {label} ({reason_pct:.0f}% with thesis)",
                "severity": SEVERITY_IMPROVE,
                "asset_class": asset_class,
                "model_id": model_id,
                "persona_id": persona_id,
                "description": f"Only {reason_pct:.0f}% of picks include a detailed thesis or reason. Without reasoning, post-hoc analysis cannot distinguish good judgment from luck.",
                "recommendation": "Enforce the 'reason' field in pick generation. Each pick must include at least 1-2 specific entry triggers that justify the trade.",
                "suggested_experiment": "Compare win rate of picks WITH detailed reasoning vs. without. Expect picks with specific catalyst/trigger thesis to outperform generic picks.",
                "metric_current": f"{reason_pct:.0f}% with thesis",
                "metric_target": "100% with detailed entry criteria",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            })

    # Cross-model analysis
    models = set(p.get("model_id", "?") for p in picks)
    personas = set(p.get("persona_id", "?") for p in picks)

    if len(set(p.get("persona_id", "?") for p in picks)) < 5:
        topics.append({
            "topic_id": "persona_diversity",
            "title": "Low persona diversity — expand strategy coverage",
            "severity": SEVERITY_IMPROVE,
            "asset_class": "ALL",
            "description": f"Only {len(personas)} unique personas found across {len(models)} models. Diverse strategy approaches are needed for robust ensemble performance.",
            "recommendation": "Add 5-10 new personas covering different strategy families (technical, fundamental, macro, event-driven, quant).",
            "suggested_experiment": "Add pairs of inversely-correlated personas (momentum + mean reversion). Track ensemble performance vs. individual persona performance.",
            "metric_current": f"{len(personas)} personas",
            "metric_target": "15+ personas across 5+ strategy families",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        })

    return topics


def generate_portfolio_analytics_leaderboard(picks: list[dict]) -> list[dict[str, Any]]:
    """Generate portfolio-level analytics for the AI leaderboard — shows before picks resolve."""
    if not picks:
        return []

    groups: dict[str, dict] = {}
    for p in picks:
        key = f"{p.get('model_id','?')}|{p.get('persona_id','?')}"
        if key not in groups:
            groups[key] = {"picks": [], "model_id": p.get("model_id","?"), "persona_id": p.get("persona_id","?"), "provider": p.get("provider","")}
        groups[key]["picks"].append(p)

    entries = []
    for key, g in groups.items():
        g_picks = g["picks"]
        n = len(g_picks)

        # Confidence stats
        confs = []
        for p in g_picks:
            v = p.get("confidence", 0.5)
            if isinstance(v, str):
                confs.append({"HIGH": 0.8, "MEDIUM": 0.5, "LOW": 0.2}.get(v, 0.5))
            else:
                confs.append(float(v))
        avg_conf = sum(confs) / len(confs) if confs else 0

        # Asset class coverage
        acs = set(p.get("asset_class", "?") for p in g_picks)

        # Thesis quality
        with_reason = sum(1 for p in g_picks if p.get("reason") or (p.get("thesis") and len(p.get("thesis", "")) > 20))

        # Direction diversity
        longs = sum(1 for p in g_picks if p.get("direction") == "LONG")
        short_pct = (n - longs) / n * 100 if n else 0

        entries.append({
            "model_id": g["model_id"],
            "persona_id": g["persona_id"],
            "provider": g["provider"],
            "n_picks": n,
            "avg_confidence": round(avg_conf, 3),
            "asset_class_coverage": list(acs),
            "n_asset_classes": len(acs),
            "thesis_rate_pct": round(with_reason / n * 100, 1) if n else 0,
            "short_pct": round(short_pct, 1),
            "status": "BUILDING" if n < 15 else "ACTIVE" if n < 30 else "RANKING",
        })

    entries.sort(key=lambda e: e["n_picks"], reverse=True)
    return entries


def write_leaderboard_data(picks: list[dict]) -> None:
    """Write portfolio analytics data that the leaderboard page can display."""
    lb = generate_portfolio_analytics_leaderboard(picks)
    topics = generate_research_topics(picks)

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "2.0",
        "min_n_to_rank": 30,
        "leaderboard_entries": lb,
        "research_topics": topics,
        "n_picks_total": len(picks),
        "n_models": len(set(p.get("model_id", "?") for p in picks)),
        "n_personas": len(set(p.get("persona_id", "?") for p in picks)),
        "n_asset_classes": len(set(p.get("asset_class", "?") for p in picks)),
        "note": "Leaderboard will rank by resolved pick performance once n>=30 per engine. Until then, portfolio analytics show build status.",
    }

    path = RESEARCH_DIR / "ai_leaderboard_data.json"
    path.write_text(json.dumps(data, indent=2))
    print(f"[research_generator] Wrote {len(lb)} leaderboard entries + {len(topics)} research topics to {path.name}")


def write_research_index(picks: list[dict], extra_topics: list[dict] | None = None) -> None:
    """Write structured research index entries for the research page."""
    topics = generate_research_topics(picks)
    if extra_topics:
        topics = extra_topics

    index = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": "tournament_research_generator",
        "n_topics": len(topics),
        "topics": topics,
        "summary": {
            "critical": sum(1 for t in topics if t["severity"] == SEVERITY_CRITICAL),
            "improve": sum(1 for t in topics if t["severity"] == SEVERITY_IMPROVE),
            "validate": sum(1 for t in topics if t["severity"] == SEVERITY_VALIDATE),
            "confirmed": sum(1 for t in topics if t["severity"] == SEVERITY_CONFIRMED),
        },
    }

    path = RESEARCH_DIR / "research_index_data.json"
    path.write_text(json.dumps(index, indent=2))
    print(f"[research_generator] Wrote {len(topics)} research topics to {path.name}")


def load_macro_data() -> dict[str, Any]:
    """Load FRED/Kalshi/Polymarket macro data for context enrichment."""
    macro = {"fred": None, "kalshi": None, "polymarket": None}
    
    fred_path = REPO_ROOT / "tools" / "data" / "fred_macro_context.json"
    if fred_path.exists():
        try:
            macro["fred"] = json.loads(fred_path.read_text())
            print(f"[research_generator] Loaded FRED macro context")
        except Exception as e:
            print(f"[research_generator] FRED load failed: {e}")
    
    kalshi_path = REPO_ROOT / "alpha_engine" / "data" / "kalshi_signals.json"
    if kalshi_path.exists():
        try:
            macro["kalshi"] = json.loads(kalshi_path.read_text())
            print(f"[research_generator] Loaded Kalshi signals")
        except Exception as e:
            print(f"[research_generator] Kalshi load failed: {e}")
    
    polymarket_path = REPO_ROOT / "alpha_engine" / "data" / "polymarket_signals.json"
    if polymarket_path.exists():
        try:
            macro["polymarket"] = json.loads(polymarket_path.read_text())
            print(f"[research_generator] Loaded Polymarket signals")
        except Exception as e:
            print(f"[research_generator] Polymarket load failed: {e}")
    
    return macro


def enrich_with_macro(topics: list[dict], macro: dict[str, Any]) -> list[dict]:
    """Add macro regime context to research topics."""
    if macro.get("fred"):
        fred = macro["fred"]
        regime = fred.get("macro_regime", {})
        if regime:
            topics.append({
                "topic_id": "macro_regime",
                "title": f"Macro Regime: {regime.get('label', 'Unknown')}",
                "severity": SEVERITY_VALIDATE,
                "asset_class": "ALL",
                "description": f"Current macro regime: {regime.get('label', 'N/A')}. "
                               f"Confidence: {regime.get('confidence', 'N/A')}. "
                               f"Affects all asset class correlations.",
                "recommendation": "Adjust portfolio beta and cross-asset correlation targets based on regime.",
                "suggested_experiment": "Compare tournament pick performance across macro regime changes. "
                                       "Split backtest by expansion vs contraction phases.",
                "metric_current": regime.get("label", "?"),
                "metric_target": "regime-consistent performance",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            })
    
    if macro.get("kalshi"):
        ks = macro["kalshi"]
        kalshi_picks = ks.get("picks", [])
        if kalshi_picks:
            topics.append({
                "topic_id": "kalshi_signals",
                "title": f"Kalshi Prediction Markets: {len(kalshi_picks)} active signals",
                "severity": SEVERITY_VALIDATE,
                "asset_class": "ALL",
                "description": f"Kalshi prediction markets show {len(kalshi_picks)} active signals "
                               f"across election, economic, and event contracts.",
                "recommendation": "Cross-reference Kalshi implied probabilities with tournament pick directions.",
                "metric_current": f"{len(kalshi_picks)} signals",
                "metric_target": "correlation between market-implied and model-implied probabilities",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            })
    
    return topics


if __name__ == "__main__":
    print(f"[research_generator] Generating research topics and leaderboard data — {datetime.now(timezone.utc).isoformat()}")
    picks = load_latest_picks()
    if not picks:
        picks = load_historical_picks(7)
    print(f"[research_generator] Loaded {len(picks)} picks")
    
    # Enrich with macro data
    macro = load_macro_data()
    topics = generate_research_topics(picks)
    topics = enrich_with_macro(topics, macro)
    
    write_leaderboard_data(picks)
    write_research_index(picks, topics)
    print(f"[research_generator] Done — {len(topics)} topics including macro")
