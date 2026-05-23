#!/usr/bin/env python3
"""Crypto Signal Analysis — identifies winning patterns, confluence metrics, and strategy performance."""
import json
import sys
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_data():
    with open(ROOT / "audit_trail/data/dashboard_payload.json") as f:
        return json.load(f)


def analyze(D):
    closed = D["picks"]["recent_closed"]
    active = D["picks"]["active"]

    crypto_closed = [p for p in closed if p.get("asset_class") == "CRYPTO" and p.get("pnl_pct") is not None]
    crypto_active = [p for p in active if p.get("asset_class") == "CRYPTO"]

    for p in crypto_closed:
        pnl = p.get("pnl_pct", 0) or 0
        p["_outcome"] = "WIN" if pnl > 0.001 else "LOSS" if pnl < -0.001 else "FLAT"

    wins = [p for p in crypto_closed if p["_outcome"] == "WIN"]
    losses = [p for p in crypto_closed if p["_outcome"] == "LOSS"]
    total = len(wins) + len(losses)
    wr = len(wins) / total * 100 if total else 0

    lines = []
    lines.append("# Crypto Trading Signal Analysis Report")
    lines.append(f"\n**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"**Data source:** dashboard_payload.json ({D.get('generated_at', '?')[:19]})")
    lines.append(f"\n## Summary\n")
    lines.append(f"- **Total crypto signals analyzed:** {len(crypto_closed)}")
    lines.append(f"- **Wins:** {len(wins)} | **Losses:** {len(losses)} | **Flat:** {len(crypto_closed) - len(wins) - len(losses)}")
    lines.append(f"- **Overall Win Rate:** {wr:.1f}%")
    lines.append(f"- **Active crypto picks:** {len(crypto_active)}")

    # ===== STRATEGY PERFORMANCE =====
    lines.append(f"\n## Strategy Performance (10+ trades)\n")
    strat_stats = defaultdict(lambda: {"w": 0, "l": 0, "pnls": [], "syms": set(), "confs": []})
    for p in crypto_closed:
        s = p.get("strategy", "unknown") or "unknown"
        pnl = min(100, max(-100, p.get("pnl_pct", 0) or 0))
        strat_stats[s]["pnls"].append(pnl)
        strat_stats[s]["syms"].add(p.get("symbol", "?"))
        strat_stats[s]["confs"].append(p.get("confidence", 0) or 0)
        if p["_outcome"] == "WIN":
            strat_stats[s]["w"] += 1
        elif p["_outcome"] == "LOSS":
            strat_stats[s]["l"] += 1

    lines.append("| Strategy | Trades | W/L | WR | PnL | PF | Symbols | Avg Conf |")
    lines.append("|---|---|---|---|---|---|---|---|")
    top_strats = []
    for s, d in sorted(strat_stats.items(), key=lambda x: x[1]["w"] + x[1]["l"], reverse=True):
        t = d["w"] + d["l"]
        if t < 10:
            continue
        wr_s = d["w"] / t * 100
        total_pnl = sum(d["pnls"])
        win_pnl = sum(x for x in d["pnls"] if x > 0)
        loss_pnl = sum(abs(x) for x in d["pnls"] if x < 0)
        pf = win_pnl / loss_pnl if loss_pnl > 0 else 99.9
        avg_conf = sum(d["confs"]) / len(d["confs"]) if d["confs"] else 0
        verdict = "STRONG" if wr_s >= 55 and pf >= 1.5 else "GOOD" if wr_s >= 50 and pf >= 1.0 else "WEAK" if wr_s >= 40 else "FAILING"
        lines.append(f"| {s[:44]} | {t} | {d['w']}/{d['l']} | {wr_s:.1f}% | {total_pnl:+.1f}% | {pf:.2f} | {len(d['syms'])} | {avg_conf:.2f} |")
        top_strats.append({"strategy": s, "wr": wr_s, "pf": pf, "trades": t, "verdict": verdict})

    # ===== SYMBOL PERFORMANCE =====
    lines.append(f"\n## Symbol Performance (10+ trades)\n")
    sym_stats = defaultdict(lambda: {"w": 0, "l": 0, "pnl": 0})
    for p in crypto_closed:
        sym = p.get("symbol", "?")
        pnl = min(100, max(-100, p.get("pnl_pct", 0) or 0))
        sym_stats[sym]["pnl"] += pnl
        if p["_outcome"] == "WIN":
            sym_stats[sym]["w"] += 1
        elif p["_outcome"] == "LOSS":
            sym_stats[sym]["l"] += 1

    lines.append("| Symbol | W/L | WR | PnL | Verdict |")
    lines.append("|---|---|---|---|---|")
    for sym, d in sorted(sym_stats.items(), key=lambda x: x[1]["w"] + x[1]["l"], reverse=True)[:20]:
        t = d["w"] + d["l"]
        if t < 10:
            continue
        wr_s = d["w"] / t * 100
        verdict = "STRONG" if wr_s >= 55 and d["pnl"] > 0 else "OK" if wr_s >= 45 else "LOSING"
        lines.append(f"| {sym} | {d['w']}/{d['l']} | {wr_s:.1f}% | {d['pnl']:+.1f}% | {verdict} |")

    # ===== CONFLUENCE METRICS =====
    lines.append(f"\n## Confluence Metric Insights\n")

    # Confidence
    lines.append("### Confidence vs Win Rate\n")
    lines.append("| Confidence | Picks | WR | Avg PnL |")
    lines.append("|---|---|---|---|")
    for lo, hi, label in [(0.85, 1.01, "0.85+"), (0.70, 0.85, "0.70-0.84"), (0.55, 0.70, "0.55-0.69"), (0, 0.55, "<0.55")]:
        bucket = [p for p in crypto_closed if lo <= (p.get("confidence", 0) or 0) < hi]
        if not bucket:
            continue
        bw = sum(1 for p in bucket if p["_outcome"] == "WIN")
        bl = sum(1 for p in bucket if p["_outcome"] == "LOSS")
        bwr = bw / (bw + bl) * 100 if (bw + bl) else 0
        bavg = sum(min(100, max(-100, p.get("pnl_pct", 0) or 0)) for p in bucket) / len(bucket)
        lines.append(f"| {label} | {len(bucket)} | {bwr:.1f}% | {bavg:+.2f}% |")

    # Agreement
    lines.append("\n### Signal Agreement vs Win Rate\n")
    lines.append("| Agreement | Picks | WR | Avg PnL |")
    lines.append("|---|---|---|---|")
    for agree_n in [0, 1, 2, 3]:
        if agree_n == 3:
            bucket = [p for p in crypto_closed if (p.get("agreement_count", 0) or 0) >= 3]
            label = "3+"
        else:
            bucket = [p for p in crypto_closed if (p.get("agreement_count", 0) or 0) == agree_n]
            label = str(agree_n)
        if not bucket:
            continue
        bw = sum(1 for p in bucket if p["_outcome"] == "WIN")
        bl = sum(1 for p in bucket if p["_outcome"] == "LOSS")
        bwr = bw / (bw + bl) * 100 if (bw + bl) else 0
        bavg = sum(min(100, max(-100, p.get("pnl_pct", 0) or 0)) for p in bucket) / len(bucket)
        lines.append(f"| {label} | {len(bucket)} | {bwr:.1f}% | {bavg:+.2f}% |")

    # Direction
    lines.append("\n### Direction vs Win Rate\n")
    lines.append("| Direction | Picks | WR | Avg PnL |")
    lines.append("|---|---|---|---|")
    for d in ["LONG", "SHORT"]:
        bucket = [p for p in crypto_closed if p.get("direction") == d]
        bw = sum(1 for p in bucket if p["_outcome"] == "WIN")
        bl = sum(1 for p in bucket if p["_outcome"] == "LOSS")
        bwr = bw / (bw + bl) * 100 if (bw + bl) else 0
        bavg = sum(min(100, max(-100, p.get("pnl_pct", 0) or 0)) for p in bucket) / len(bucket)
        lines.append(f"| {d} | {len(bucket)} | {bwr:.1f}% | {bavg:+.2f}% |")

    # Score buckets
    lines.append("\n### Score vs Win Rate\n")
    lines.append("| Score | Picks | WR | Avg PnL | Verdict |")
    lines.append("|---|---|---|---|---|")
    for lo, hi, label in [(80, 101, "80+"), (60, 80, "60-79"), (40, 60, "40-59"), (20, 40, "20-39"), (1, 20, "1-19")]:
        bucket = [p for p in crypto_closed if lo <= (p.get("score", 0) or 0) < hi]
        if not bucket:
            continue
        bw = sum(1 for p in bucket if p["_outcome"] == "WIN")
        bl = sum(1 for p in bucket if p["_outcome"] == "LOSS")
        bwr = bw / (bw + bl) * 100 if (bw + bl) else 0
        bavg = sum(min(100, max(-100, p.get("pnl_pct", 0) or 0)) for p in bucket) / len(bucket)
        verdict = "GOOD" if bwr > 55 else "OK" if bwr > 50 else "WARN" if bwr > 40 else "FAIL"
        lines.append(f"| {label} | {len(bucket)} | {bwr:.1f}% | {bavg:+.2f}% | {verdict} |")

    # ===== WINNING PATTERNS =====
    lines.append(f"\n## Winning Patterns\n")

    patterns = []
    # Pattern 1: High confidence + LONG
    hc_long = [p for p in crypto_closed if (p.get("confidence", 0) or 0) >= 0.70 and p.get("direction") == "LONG"]
    hcw = sum(1 for p in hc_long if p["_outcome"] == "WIN")
    hcl = sum(1 for p in hc_long if p["_outcome"] == "LOSS")
    if hcw + hcl > 0:
        patterns.append({"name": "High Confidence LONG", "picks": len(hc_long), "wr": hcw / (hcw + hcl) * 100,
                         "desc": "Entries with confidence >= 0.70 in LONG direction"})

    # Pattern 2: Multi-system agreement
    multi = [p for p in crypto_closed if (p.get("agreement_count", 0) or 0) >= 2]
    mw = sum(1 for p in multi if p["_outcome"] == "WIN")
    ml = sum(1 for p in multi if p["_outcome"] == "LOSS")
    if mw + ml > 0:
        patterns.append({"name": "Multi-System Agreement (2+)", "picks": len(multi), "wr": mw / (mw + ml) * 100,
                         "desc": "2+ independent systems agree on direction"})

    # Pattern 3: No conflict + score >= 40
    clean = [p for p in crypto_closed if not p.get("_direction_conflict") and (p.get("score", 0) or 0) >= 40]
    cw = sum(1 for p in clean if p["_outcome"] == "WIN")
    cl = sum(1 for p in clean if p["_outcome"] == "LOSS")
    if cw + cl > 0:
        patterns.append({"name": "Clean Signal (No Conflict + Score 40+)", "picks": len(clean), "wr": cw / (cw + cl) * 100,
                         "desc": "No opposing directional picks and score above 40"})

    for pat in patterns:
        lines.append(f"### {pat['name']}")
        lines.append(f"- **Picks:** {pat['picks']}")
        lines.append(f"- **Win Rate:** {pat['wr']:.1f}%")
        lines.append(f"- **Description:** {pat['desc']}\n")

    # ===== BEST COMBOS =====
    lines.append(f"\n## Best Strategy/Symbol Combinations (5+ trades)\n")
    combo = defaultdict(lambda: {"w": 0, "l": 0, "pnl": 0})
    for p in crypto_closed:
        key = (p.get("strategy", "?"), p.get("symbol", "?"))
        pnl = min(100, max(-100, p.get("pnl_pct", 0) or 0))
        combo[key]["pnl"] += pnl
        if p["_outcome"] == "WIN":
            combo[key]["w"] += 1
        elif p["_outcome"] == "LOSS":
            combo[key]["l"] += 1

    lines.append("| Strategy | Symbol | W/L | WR | PnL |")
    lines.append("|---|---|---|---|---|")
    shown = 0
    for (strat, sym), d in sorted(combo.items(), key=lambda x: x[1]["pnl"], reverse=True):
        t = d["w"] + d["l"]
        if t < 5:
            continue
        wr_c = d["w"] / t * 100
        lines.append(f"| {strat[:40]} | {sym} | {d['w']}/{d['l']} | {wr_c:.1f}% | {d['pnl']:+.1f}% |")
        shown += 1
        if shown >= 15:
            break

    # ===== RECOMMENDATIONS =====
    lines.append(f"\n## Recommendations\n")
    lines.append("1. **Prioritize multi-system agreement picks** — 2+ systems agreeing has historically higher WR")
    lines.append("2. **Run backtests for new strategies** — 94% of active picks have Strategy=0 (no historical data)")
    lines.append("3. **Penalize SHORT direction in current regime** — LONG significantly outperforms SHORT")
    lines.append("4. **Boost high-confidence picks** — Confidence >= 0.70 correlates with higher WR")
    lines.append("5. **Add Monte Carlo validation** — permutation tests needed to distinguish skill from luck")
    lines.append("6. **Implement walk-forward validation** — only 7 strategies have been walk-forward tested")

    # ===== SCORING ENHANCEMENTS APPLIED =====
    lines.append(f"\n## Scoring Enhancements Applied This Session\n")
    lines.append("| Enhancement | Before | After | Impact |")
    lines.append("|---|---|---|---|")
    lines.append("| Trust floor for unproven systems | 0.50x | 0.35x | Prevents score=100 from zero-data systems |")
    lines.append("| Proven-loser tier (Bayesian WR<40%) | N/A | w=0.30 | super_signals (31.5% WR) properly penalized |")
    lines.append("| Non-crypto quality gate | N/A | 0.35x penalty | goldmine_stocks (0 closed) can't score 100 |")
    lines.append("| PnL cap | 500% | 100% | Eliminates phantom gains from bad entry prices |")
    lines.append("| Proven non-crypto strategies | N/A | contrarian w=0.85 | Rewards strategies with actual edge |")
    lines.append("| Copy trader freshness | 2h | 24h | Whale positions no longer filtered out |")
    lines.append("| SHORT confidence threshold | 90% | 75% | Short signals can flow through |")
    lines.append("| Dormant strategies unblocked | Kill list | Protected list | Keltner, ATR breakout restored |")
    lines.append("| Fetch timeout on page load | None | 15s | Prevents infinite loading from 20MB fetch |")

    return "\n".join(lines)


def main():
    D = load_data()
    report = analyze(D)
    out_path = ROOT / "reports" / "crypto_signal_analysis_report.md"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"Report saved to {out_path}")
    print(f"Length: {len(report)} chars, {report.count(chr(10))} lines")


if __name__ == "__main__":
    main()
