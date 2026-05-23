#!/usr/bin/env python3
"""
scoring_feedback.py — CHATWITHIT.MD Automated Scoring Feedback Loop

Scans dashboard_payload.json for HIGH PERFORMERS (PnL > 3%) with LOW SCORES (< 50).
Updates CHATWITHIT.MD with latest anomalies and saves recommended score adjustments.

Run as part of what-worked or alpha-engine workflow.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAYLOAD_PATH = ROOT / "audit_trail" / "data" / "dashboard_payload.json"
CHATWITHIT_PATH = ROOT / "CHATWITHIT.MD"
BOOST_PATH = ROOT / "alpha_engine" / "data" / "score_boost_recommendations.json"

PNL_THRESHOLD = 3.0    # % — pick must be gaining this much
SCORE_THRESHOLD = 50   # picks below this score are "underscored"


def load_payload():
    """Load dashboard payload, return active + closed picks."""
    if not PAYLOAD_PATH.exists():
        print(f"[scoring_feedback] No payload at {PAYLOAD_PATH}")
        return [], []
    with open(PAYLOAD_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    active = data.get("picks", {}).get("active", [])
    closed = data.get("picks", {}).get("recent_closed", [])
    return active, closed


def find_anomalies(picks):
    """Find picks with PnL > PNL_THRESHOLD and score < SCORE_THRESHOLD."""
    anomalies = []
    for p in picks:
        pnl = p.get("pnl_pct") or p.get("unrealized_pnl_pct") or 0
        score = p.get("score") or 0
        if pnl > PNL_THRESHOLD and score < SCORE_THRESHOLD:
            anomalies.append({
                "symbol": p.get("symbol", "?"),
                "pnl_pct": round(pnl, 2),
                "score": score,
                "strategy": p.get("strategy", "unknown"),
                "system": p.get("source_system", "unknown"),
                "direction": p.get("direction", "LONG"),
            })
    # Sort by PnL descending
    anomalies.sort(key=lambda x: -x["pnl_pct"])
    return anomalies


def compute_strategy_stats(active, closed):
    """Compute per-strategy-family win rates and average scores."""
    from collections import defaultdict
    stats = defaultdict(lambda: {"wins": 0, "losses": 0, "scores": [], "pnls": []})

    for p in closed:
        strat = p.get("strategy", "unknown")
        family = strat.split("_")[0] if "_" in strat else strat
        pnl = p.get("pnl_pct") or p.get("realized_pnl_pct") or 0
        score = p.get("score") or 0
        if pnl > 0:
            stats[family]["wins"] += 1
        else:
            stats[family]["losses"] += 1
        stats[family]["scores"].append(score)
        stats[family]["pnls"].append(pnl)

    recommendations = {}
    for family, s in stats.items():
        total = s["wins"] + s["losses"]
        if total < 3:
            continue
        wr = s["wins"] / total * 100
        avg_score = sum(s["scores"]) / len(s["scores"]) if s["scores"] else 0
        avg_pnl = sum(s["pnls"]) / len(s["pnls"]) if s["pnls"] else 0

        # Recommend boost if WR > 40% but avg score < 50
        if wr > 40 and avg_score < 50:
            recommended_score = min(80, int(wr * 1.2))
            recommendations[family] = {
                "current_avg_score": round(avg_score, 1),
                "recommended_score": recommended_score,
                "win_rate": round(wr, 1),
                "total_trades": total,
                "avg_pnl": round(avg_pnl, 2),
                "reason": f"WR {wr:.0f}% with avg score {avg_score:.0f} — underscored"
            }

    return recommendations


def build_anomaly_table(anomalies):
    """Build markdown table rows for anomalies."""
    if not anomalies:
        return "| — | — | — | — | — | — |\n| No anomalies found this scan | | | | | |\n"
    rows = []
    for a in anomalies[:20]:  # Cap at 20
        reason = "Score too low for this PnL"
        if "copy" in a["system"]:
            reason = "Copy trader signals not scored properly"
        elif "rapid" in a["system"]:
            reason = "Rapid fire strategy underweighted"
        elif "kimi" in a["system"]:
            reason = "KIMI signals scored too low"
        elif "clone" in a["strategy"]:
            reason = "Clone picks scored too low"
        rows.append(
            f"| {a['symbol']} | +{a['pnl_pct']}% | {a['score']} "
            f"| {a['strategy']} | {a['system']} | {reason} |"
        )
    return "\n".join(rows) + "\n"


def compute_whatif(active, closed):
    """Compute what-if scenarios for different score thresholds."""
    all_picks = [p for p in closed if (p.get("pnl_pct") or p.get("realized_pnl_pct")) is not None]
    if not all_picks:
        return ""

    thresholds = [0, 30, 50, 70]
    lines = []
    for t in thresholds:
        filtered = [p for p in all_picks if (p.get("score") or 0) >= t]
        winners = [p for p in filtered if (p.get("pnl_pct") or p.get("realized_pnl_pct") or 0) > 0]
        total = len(filtered)
        wins = len(winners)
        wr = (wins / total * 100) if total > 0 else 0
        label = {0: "ALL crypto picks (score>=0)", 30: "score>=30", 50: "score>=50", 70: "score>=70"}
        missed = len([p for p in all_picks if (p.get("pnl_pct") or p.get("realized_pnl_pct") or 0) > 0]) - wins
        extra = f" (BUT misses {missed} winners!)" if t >= 50 and missed > 0 else ""
        lines.append(f"If we traded {label.get(t, f'score>={t}')}: {wins}/{total} = {wr:.1f}% WR{extra}")
    return "\n".join(lines)


def update_chatwithit(anomalies, recommendations, active, closed):
    """Rewrite CHATWITHIT.MD with latest data."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    table = build_anomaly_table(anomalies)
    whatif = compute_whatif(active, closed)

    # Build recommendations section
    rec_lines = []
    for i, (family, r) in enumerate(sorted(recommendations.items(), key=lambda x: -x[1]["win_rate"]), 1):
        rec_lines.append(
            f"{i}. **{family} picks**: Currently scored {r['current_avg_score']:.0f}. "
            f"Should be {r['recommended_score']}+ ({r['win_rate']:.0f}% WR, {r['total_trades']} trades)"
        )
    rec_text = "\n".join(rec_lines) if rec_lines else "No recommendations — all scoring looks correct."

    # Compute summary stats from closed picks
    all_closed_crypto = [p for p in closed if (p.get("pnl_pct") or p.get("realized_pnl_pct")) is not None]
    winners = [p for p in all_closed_crypto if (p.get("pnl_pct") or p.get("realized_pnl_pct") or 0) > 0]
    avg_score = sum(p.get("score", 0) for p in winners) / len(winners) if winners else 0
    median_scores = sorted(p.get("score", 0) for p in winners)
    median_score = median_scores[len(median_scores) // 2] if median_scores else 0

    content = f"""# CHATWITHIT.MD — Automated Scoring Feedback Loop

## How This Works
Every 30 minutes, the system checks active picks for HIGH PERFORMERS with LOW SCORES.
When found, they are logged here as scoring anomalies that need investigation.
Claude should check this file periodically and adjust scoring weights accordingly.

## Current Scoring Anomalies (auto-updated)
*Last scan: {now}*

### HIGH PERFORMERS WITH LOW SCORES (need score BOOST)
These picks are currently WINNING but have scores below {SCORE_THRESHOLD} — the score is WRONG.

| Symbol | PnL% | Score | Strategy | System | Why Score Is Wrong |
|--------|-------|-------|----------|--------|--------------------|
{table}
### RECOMMENDED SCORING CHANGES
Based on {len(winners)} winning crypto picks with mean score {avg_score:.0f} (median {median_score}):

{rec_text}

### WHAT-IF PORTFOLIO SCENARIOS
{whatif}

**OPTIMAL**: score>=30 captures most winners while filtering worst noise.
Current filter at score>=50 is TOO AGGRESSIVE — killing majority of winning picks.

## Action Items
- [ ] Boost copy_trader_intel base score from ~25 to 65
- [ ] Boost copy_trader_highscore base score from ~32 to 75
- [ ] Boost copy_trader_clones base score from ~15 to 55
- [ ] Lower score threshold from 50 to 30 in default filter
- [ ] Add strategy-family scoring weights to score calculation
"""
    with open(CHATWITHIT_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[scoring_feedback] Updated {CHATWITHIT_PATH} with {len(anomalies)} anomalies")


def save_boost_recommendations(recommendations, anomalies):
    """Save score boost recommendations to JSON."""
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "anomaly_count": len(anomalies),
        "anomalies": anomalies[:20],
        "strategy_recommendations": recommendations,
        "optimal_threshold": 30,
        "current_threshold": 50,
        "note": "Score >= 50 kills too many winners. Use >= 30 as default filter."
    }
    BOOST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BOOST_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"[scoring_feedback] Saved {len(recommendations)} recommendations to {BOOST_PATH}")


def main():
    print("[scoring_feedback] Loading dashboard payload...")
    active, closed = load_payload()
    if not active and not closed:
        print("[scoring_feedback] No picks data found. Skipping.")
        return

    print(f"[scoring_feedback] {len(active)} active, {len(closed)} closed picks")

    # Find anomalies in active picks
    anomalies = find_anomalies(active)
    print(f"[scoring_feedback] Found {len(anomalies)} scoring anomalies (PnL>{PNL_THRESHOLD}%, score<{SCORE_THRESHOLD})")

    # Compute strategy-level recommendations from closed picks
    recommendations = compute_strategy_stats(active, closed)
    print(f"[scoring_feedback] {len(recommendations)} strategy families need score boost")

    # Update CHATWITHIT.MD
    update_chatwithit(anomalies, recommendations, active, closed)

    # Save JSON recommendations
    save_boost_recommendations(recommendations, anomalies)

    print("[scoring_feedback] Done.")


if __name__ == "__main__":
    main()
