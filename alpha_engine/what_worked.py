#!/usr/bin/env python3
"""
What Worked — Live Active Picks Pattern Analyzer

Analyzes CURRENT active picks by their unrealized PnL to find
patterns among winners vs losers RIGHT NOW. Runs every 4 hours.

Output: alpha_engine/data/what_worked.json
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Windows UTF-8 fix
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
PAYLOAD_PATH = ROOT / "audit_trail" / "data" / "dashboard_payload.json"
OUTPUT_PATH = ROOT / "alpha_engine" / "data" / "what_worked.json"


def strat_family(strategy: str) -> str:
    """Group individual strategies into families for pattern analysis."""
    s = (strategy or "").lower().strip()
    if not s:
        return "unknown"

    # Copy trader families
    if s.startswith("copy_hl_") or s.startswith("clone_hl_"):
        return "copy_trader"
    if s.startswith("bitget_copy_"):
        return "bitget_copy"
    if s.startswith("bingx_copy_"):
        return "bingx_copy"

    # ML-enhanced
    if s.startswith("ml_enhanced_") or s.startswith("ml_"):
        return "ml_enhanced"

    # DNA / mutation families
    if "_mut" in s or s.startswith("dna_"):
        return "dna_mutation"
    if "gainer_compression" in s:
        return "gainer_compression"

    # RSI family
    if "rsi" in s and "stoch" not in s:
        return "rsi_strategies"
    if "stochrsi" in s or "stoch_rsi" in s:
        return "stochrsi"

    # MACD
    if "macd" in s:
        return "macd"

    # Bollinger / BB
    if "bb" in s or "bollinger" in s:
        return "bollinger"

    # Keltner
    if "keltner" in s:
        return "keltner"

    # Coinglass
    if s.startswith("coinglass_"):
        return "coinglass"

    # Ensemble / consensus
    if "ensemble" in s or "consensus" in s or "goldmine" in s:
        return "ensemble"

    # Fear/greed / sentiment
    if "fear" in s or "sentiment" in s or "contrarian" in s:
        return "sentiment"

    # Breakout
    if "breakout" in s:
        return "breakout"

    # VWAP
    if "vwap" in s:
        return "vwap"

    # Whale / smart money
    if "whale" in s or "smart_money" in s or "binance_smart" in s:
        return "smart_money"

    # Super signals
    if "super" in s:
        return "super_signals"

    # Funding rate
    if "funding" in s:
        return "funding_rate"

    # Drawdown recovery
    if "drawdown" in s or "recovery" in s:
        return "drawdown_recovery"

    # Volume
    if "volume" in s or "vol_" in s:
        return "volume"

    # Trend / ADX
    if "adx" in s or "trend" in s:
        return "trend"

    # EMA / moving average
    if "ema" in s or "sma" in s or "moving_avg" in s:
        return "moving_average"

    # Rapid fire
    if "rapid" in s:
        return "rapid_fire"

    # Scalp
    if "scalp" in s:
        return "scalp"

    # Multi-period / confluence
    if "multi_period" in s or "confluence" in s:
        return "confluence"

    # Leverage / liquidation
    if "leverage" in s or "liquidation" in s:
        return "leverage_signals"

    return s.split("_")[0] if "_" in s else s


def analyze_picks(picks: list) -> dict:
    """Analyze active picks and find patterns."""
    if not picks:
        return {
            "error": "No active picks found",
            "overall": {"winners": 0, "losers": 0, "flat": 0, "wr": 0.0, "total_pnl": 0.0, "avg_pnl": 0.0},
            "patterns": {},
            "winner_vs_loser": {},
            "system_ranking": [],
            "tldr": "No active picks to analyze.",
            "trust_ranking": [],
            "avoid_list": [],
        }

    now = datetime.now(timezone.utc)

    # Classify winners/losers
    winners = [p for p in picks if (p.get("pnl_pct") or 0) > 0]
    losers = [p for p in picks if (p.get("pnl_pct") or 0) < 0]
    flat = [p for p in picks if (p.get("pnl_pct") or 0) == 0]

    total = len(picks)
    total_pnl = sum(p.get("pnl_pct", 0) or 0 for p in picks)
    wr = round(len(winners) / max(total - len(flat), 1) * 100, 1)

    # ── Direction analysis ──
    direction_stats = {}
    for d in ["LONG", "SHORT"]:
        d_picks = [p for p in picks if p.get("direction") == d]
        d_winners = [p for p in d_picks if (p.get("pnl_pct") or 0) > 0]
        d_losers = [p for p in d_picks if (p.get("pnl_pct") or 0) < 0]
        d_total_nonflat = len(d_winners) + len(d_losers)
        d_pnl = sum(p.get("pnl_pct", 0) or 0 for p in d_picks)
        direction_stats[d] = {
            "count": len(d_picks),
            "winners": len(d_winners),
            "losers": len(d_losers),
            "wr": round(len(d_winners) / max(d_total_nonflat, 1) * 100, 1),
            "pnl": round(d_pnl, 2),
            "avg_pnl": round(d_pnl / max(len(d_picks), 1), 2),
        }

    # ── Strategy family analysis ──
    family_stats = {}
    for p in picks:
        fam = strat_family(p.get("strategy", ""))
        if fam not in family_stats:
            family_stats[fam] = {"picks": 0, "winners": 0, "losers": 0, "pnl": 0.0}
        family_stats[fam]["picks"] += 1
        pnl = p.get("pnl_pct", 0) or 0
        family_stats[fam]["pnl"] += pnl
        if pnl > 0:
            family_stats[fam]["winners"] += 1
        elif pnl < 0:
            family_stats[fam]["losers"] += 1

    for fam, s in family_stats.items():
        nonflat = s["winners"] + s["losers"]
        s["wr"] = round(s["winners"] / max(nonflat, 1) * 100, 1)
        s["pnl"] = round(s["pnl"], 2)
        s["avg_pnl"] = round(s["pnl"] / max(s["picks"], 1), 2)

    # Sort by WR (min 3 picks to qualify)
    qualified = {k: v for k, v in family_stats.items() if v["picks"] >= 3}
    best_strats = sorted(qualified.items(), key=lambda x: (-x[1]["wr"], -x[1]["pnl"]))[:8]
    worst_strats = sorted(qualified.items(), key=lambda x: (x[1]["wr"], x[1]["pnl"]))[:8]

    # ── Score analysis ──
    score_buckets = {"<30": [], "30-49": [], "50-69": [], ">=70": []}
    for p in picks:
        sc = p.get("score")
        if sc is None:
            continue
        if sc >= 70:
            score_buckets[">=70"].append(p)
        elif sc >= 50:
            score_buckets["50-69"].append(p)
        elif sc >= 30:
            score_buckets["30-49"].append(p)
        else:
            score_buckets["<30"].append(p)

    score_analysis = {}
    best_score_bucket = None
    best_score_wr = -1
    for bucket, bpicks in score_buckets.items():
        if not bpicks:
            continue
        bw = len([p for p in bpicks if (p.get("pnl_pct") or 0) > 0])
        bl = len([p for p in bpicks if (p.get("pnl_pct") or 0) < 0])
        bwr = round(bw / max(bw + bl, 1) * 100, 1)
        bpnl = sum(p.get("pnl_pct", 0) or 0 for p in bpicks)
        score_analysis[bucket] = {
            "count": len(bpicks), "wr": bwr, "pnl": round(bpnl, 2),
            "avg_pnl": round(bpnl / max(len(bpicks), 1), 2)
        }
        if bwr > best_score_wr and len(bpicks) >= 3:
            best_score_wr = bwr
            best_score_bucket = bucket

    # Score matters if there's a >10% WR spread between best and worst bucket
    score_wrs = [v["wr"] for v in score_analysis.values()]
    score_matters = (max(score_wrs) - min(score_wrs)) > 10 if len(score_wrs) >= 2 else False

    # ── Confidence analysis ──
    conf_buckets = {"<0.5": [], "0.5-0.69": [], "0.7-0.84": [], ">=0.85": []}
    for p in picks:
        c = p.get("confidence")
        if c is None:
            continue
        if c >= 0.85:
            conf_buckets[">=0.85"].append(p)
        elif c >= 0.7:
            conf_buckets["0.7-0.84"].append(p)
        elif c >= 0.5:
            conf_buckets["0.5-0.69"].append(p)
        else:
            conf_buckets["<0.5"].append(p)

    best_conf_bucket = None
    best_conf_wr = -1
    for bucket, bpicks in conf_buckets.items():
        if len(bpicks) < 3:
            continue
        bw = len([p for p in bpicks if (p.get("pnl_pct") or 0) > 0])
        bl = len([p for p in bpicks if (p.get("pnl_pct") or 0) < 0])
        bwr = round(bw / max(bw + bl, 1) * 100, 1)
        if bwr > best_conf_wr:
            best_conf_wr = bwr
            best_conf_bucket = bucket

    # ── Trust tier analysis ──
    tier_stats = {}
    for p in picks:
        tier = p.get("trust_tier") or p.get("source_system") or "unknown"
        if tier not in tier_stats:
            tier_stats[tier] = {"picks": 0, "winners": 0, "pnl": 0.0}
        tier_stats[tier]["picks"] += 1
        pnl = p.get("pnl_pct", 0) or 0
        tier_stats[tier]["pnl"] += pnl
        if pnl > 0:
            tier_stats[tier]["winners"] += 1

    # ── Source system analysis ──
    system_stats = {}
    for p in picks:
        sys_name = p.get("source_system") or "unknown"
        if sys_name not in system_stats:
            system_stats[sys_name] = {"picks": 0, "winners": 0, "losers": 0, "pnl": 0.0}
        system_stats[sys_name]["picks"] += 1
        pnl = p.get("pnl_pct", 0) or 0
        system_stats[sys_name]["pnl"] += pnl
        if pnl > 0:
            system_stats[sys_name]["winners"] += 1
        elif pnl < 0:
            system_stats[sys_name]["losers"] += 1

    for sys_name, s in system_stats.items():
        nonflat = s["winners"] + s["losers"]
        s["wr"] = round(s["winners"] / max(nonflat, 1) * 100, 1)
        s["pnl"] = round(s["pnl"], 2)

    # Winner/loser comparison
    w_scores = [p.get("score", 0) or 0 for p in winners if p.get("score") is not None]
    l_scores = [p.get("score", 0) or 0 for p in losers if p.get("score") is not None]
    w_confs = [p.get("confidence", 0) or 0 for p in winners if p.get("confidence") is not None]
    l_confs = [p.get("confidence", 0) or 0 for p in losers if p.get("confidence") is not None]
    w_long_pct = round(len([p for p in winners if p.get("direction") == "LONG"]) / max(len(winners), 1) * 100, 1)
    l_long_pct = round(len([p for p in losers if p.get("direction") == "LONG"]) / max(len(losers), 1) * 100, 1)

    winner_profile = {
        "avg_score": round(sum(w_scores) / max(len(w_scores), 1), 1),
        "avg_confidence": round(sum(w_confs) / max(len(w_confs), 1), 2),
        "pct_long": w_long_pct,
    }
    loser_profile = {
        "avg_score": round(sum(l_scores) / max(len(l_scores), 1), 1),
        "avg_confidence": round(sum(l_confs) / max(len(l_confs), 1), 2),
        "pct_long": l_long_pct,
    }

    # Trust ranking: systems sorted by WR (min 5 picks)
    trust_ranking = sorted(
        [(k, v) for k, v in system_stats.items() if v["picks"] >= 5],
        key=lambda x: -x[1]["wr"]
    )
    trust_list = [k for k, v in trust_ranking if v["wr"] >= 50][:10]

    # Avoid list: strategy families with <40% WR and >=5 picks
    avoid_list = [k for k, v in family_stats.items() if v["wr"] < 40 and v["picks"] >= 5]

    # ── Build TLDR ──
    tldr_parts = []
    long_wr = direction_stats.get("LONG", {}).get("wr", 0)
    short_wr = direction_stats.get("SHORT", {}).get("wr", 0)
    if abs(long_wr - short_wr) > 5:
        better = "LONG" if long_wr > short_wr else "SHORT"
        tldr_parts.append(f"{better} picks winning {max(long_wr, short_wr)}%")

    if best_strats:
        top2 = " + ".join(s[0].replace("_", " ") for s in best_strats[:2])
        tldr_parts.append(f"{top2} dominate")

    if worst_strats:
        bot1 = worst_strats[0]
        tldr_parts.append(f"Avoid {bot1[0].replace('_', ' ')} ({bot1[1]['pnl']:+.0f}%)")

    if best_score_bucket:
        sc_data = score_analysis.get(best_score_bucket, {})
        tldr_parts.append(f"Score {best_score_bucket} avg {sc_data.get('avg_pnl', 0):+.2f}%")

    tldr = ". ".join(tldr_parts) + "." if tldr_parts else "Insufficient data for patterns."

    # ── Age-window analysis ──
    age_windows = {}
    for label, max_age in [("1h", 1), ("4h", 4), ("8h", 8)]:
        aged = [p for p in picks if (p.get("age_hours") or 999) <= max_age]
        if not aged:
            continue
        aw = len([p for p in aged if (p.get("pnl_pct") or 0) > 0])
        al = len([p for p in aged if (p.get("pnl_pct") or 0) < 0])
        age_windows[label] = {
            "count": len(aged),
            "wr": round(aw / max(aw + al, 1) * 100, 1),
            "pnl": round(sum(p.get("pnl_pct", 0) or 0 for p in aged), 2),
        }

    result = {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "active_picks_analyzed": total,
        "overall": {
            "winners": len(winners),
            "losers": len(losers),
            "flat": len(flat),
            "wr": wr,
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(total_pnl / max(total, 1), 2),
        },
        "patterns": {
            "direction": direction_stats,
            "best_strategies": [
                {"name": k, "wr": v["wr"], "pnl": v["pnl"], "avg_pnl": v["avg_pnl"], "picks": v["picks"]}
                for k, v in best_strats
            ],
            "worst_strategies": [
                {"name": k, "wr": v["wr"], "pnl": v["pnl"], "avg_pnl": v["avg_pnl"], "picks": v["picks"]}
                for k, v in worst_strats
            ],
            "all_families": {
                k: {"wr": v["wr"], "pnl": v["pnl"], "picks": v["picks"], "avg_pnl": v["avg_pnl"]}
                for k, v in sorted(family_stats.items(), key=lambda x: -x[1]["picks"])
            },
            "score_matters": score_matters,
            "score_best_bucket": best_score_bucket,
            "score_buckets": score_analysis,
            "confidence_best_bucket": best_conf_bucket,
            "age_windows": age_windows,
        },
        "winner_vs_loser": {
            "winners": winner_profile,
            "losers": loser_profile,
        },
        "system_ranking": [
            {"name": k, "wr": v["wr"], "pnl": round(v["pnl"], 2), "picks": v["picks"]}
            for k, v in trust_ranking
        ],
        "tldr": tldr,
        "trust_ranking": trust_list,
        "avoid_list": avoid_list,
    }

    return result


def main():
    print("[what_worked] Loading dashboard payload...")
    if not PAYLOAD_PATH.exists():
        print(f"[what_worked] ERROR: {PAYLOAD_PATH} not found")
        sys.exit(1)

    with open(PAYLOAD_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    active_picks = data.get("picks", {}).get("active", [])
    print(f"[what_worked] Analyzing {len(active_picks)} active picks...")

    result = analyze_picks(active_picks)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"[what_worked] Saved to {OUTPUT_PATH}")
    print(f"[what_worked] TLDR: {result.get('tldr', 'N/A')}")
    ov = result.get("overall", {})
    print(f"[what_worked] Overall WR: {ov.get('wr', 0)}% | Winners: {ov.get('winners', 0)} | Losers: {ov.get('losers', 0)}")

    if result.get("patterns", {}).get("best_strategies"):
        top = result["patterns"]["best_strategies"][0]
        print(f"[what_worked] Best strategy: {top['name']} ({top['wr']}% WR, {top['pnl']:+.1f}% PnL)")


if __name__ == "__main__":
    main()
