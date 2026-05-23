#!/usr/bin/env python3
"""QA Audit of CSV pick exports + TOP_SCORED.MD generation."""
import csv
import json
import sys
import io
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def load_csv(path):
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows

def _f(v):
    try:
        if v is None or v == "" or v == "null":
            return None
        return float(str(v).replace("%", "").replace(",", "").strip())
    except (ValueError, TypeError):
        return None

def qa_audit(rows):
    issues = []
    stats = {
        "total_rows": len(rows),
        "active": 0, "closed": 0,
        "missing_entry_price": 0, "missing_score": 0,
        "missing_tp": 0, "missing_sl": 0,
        "missing_entry_time": 0, "missing_exit_time_closed": 0,
        "exit_before_entry": 0, "negative_rr": 0,
        "score_out_of_range": 0, "trust_out_of_range": 0,
        "duplicate_picks": 0,
        "pnl_outliers": 0,
    }

    # Duplicate detection
    seen = Counter()
    for r in rows:
        key = (r.get("Symbol",""), r.get("Entry Time",""), r.get("Direction",""))
        seen[key] += 1
    stats["duplicate_picks"] = sum(v - 1 for v in seen.values() if v > 1)

    for r in rows:
        typ = r.get("Type", "").strip('"')
        if "ACTIVE" in typ or "OPEN" in typ:
            stats["active"] += 1
        else:
            stats["closed"] += 1

        # Missing critical fields
        entry_price = _f(r.get("Entry Price"))
        if entry_price is None or entry_price <= 0:
            stats["missing_entry_price"] += 1

        score = _f(r.get("Score"))
        if score is None:
            stats["missing_score"] += 1
        elif score < 0 or score > 100:
            stats["score_out_of_range"] += 1

        trust = _f(r.get("Trust Score (0-10)"))
        if trust is not None and (trust < 0 or trust > 10):
            stats["trust_out_of_range"] += 1

        tp = _f(r.get("TP"))
        sl = _f(r.get("SL"))
        if not tp: stats["missing_tp"] += 1
        if not sl: stats["missing_sl"] += 1

        # R:R validation
        rr = _f(r.get("R:R"))
        if rr is not None and rr < 0:
            stats["negative_rr"] += 1

        # Time validation
        entry_time = r.get("Entry Time", "").strip('"')
        exit_time = r.get("Exit Time", "").strip('"')
        if not entry_time:
            stats["missing_entry_time"] += 1

        if "CLOSED" in typ or "CONCLUDED" in typ:
            if not exit_time:
                stats["missing_exit_time_closed"] += 1

        # PnL outliers
        pnl = _f(r.get("PnL%"))
        if pnl is not None and abs(pnl) > 100:
            stats["pnl_outliers"] += 1

    return stats

def generate_top_scored_md(rows):
    """Generate TOP_SCORED.MD with top picks analysis."""
    lines = []
    lines.append("# Top-Scored Picks Analysis & Evidence")
    lines.append(f"\n**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"**Source:** antigravity_all_picks_2026-03-29.csv ({len(rows)} total picks)")

    # Separate active and closed
    active = [r for r in rows if "ACTIVE" in r.get("Type","") or "OPEN" in r.get("Type","")]
    closed = [r for r in rows if r not in active]

    lines.append(f"\n**Active:** {len(active)} | **Closed:** {len(closed)}")

    # Top scored active picks
    active_scored = sorted(active, key=lambda r: _f(r.get("Score")) or 0, reverse=True)
    lines.append("\n## Top 25 Active Picks by Score\n")
    lines.append("| # | Symbol | Dir | Score | Trust | System | Strategy | Entry Price | Unrealized PnL% | Conf | R:R | Entry Time (EST) | Age |")
    lines.append("|---|--------|-----|-------|-------|--------|----------|-------------|-----------------|------|-----|-------------------|-----|")

    for i, r in enumerate(active_scored[:25], 1):
        sym = r.get("Symbol","?").strip('"')
        dir_ = r.get("Direction","?").strip('"')
        score = r.get("Score","?").strip('"')
        trust = r.get("Trust Score (0-10)","?").strip('"')
        sys_ = r.get("System","?").strip('"')[:20]
        strat = r.get("Strategy","?").strip('"')[:25]
        entry = r.get("Entry Price","?").strip('"')
        pnl = r.get("PnL%","?").strip('"')
        conf = r.get("Confidence","?").strip('"')
        rr = r.get("R:R","?").strip('"')
        et = r.get("Entry Time","").strip('"')
        age = r.get("Age (hours)","?").strip('"')
        lines.append(f"| {i} | {sym} | {dir_} | {score} | {trust} | {sys_} | {strat} | {entry} | {pnl}% | {conf} | {rr} | {et} | {age}h |")

    # Top scored closed picks (evidence of scoring accuracy)
    lines.append("\n## Top 25 Closed Picks by Score (Evidence)\n")
    lines.append("| # | Symbol | Dir | Score | PnL% | Result | System | Strategy | Entry Time (EST) | Exit Time (EST) | Exit Reason |")
    lines.append("|---|--------|-----|-------|------|--------|--------|----------|-------------------|-----------------|-------------|")

    closed_scored = sorted(closed, key=lambda r: _f(r.get("Score")) or 0, reverse=True)
    for i, r in enumerate(closed_scored[:25], 1):
        sym = r.get("Symbol","?").strip('"')
        dir_ = r.get("Direction","?").strip('"')
        score = r.get("Score","?").strip('"')
        pnl = _f(r.get("PnL%"))
        pnl_str = f"{pnl:+.2f}" if pnl is not None else "?"
        result = "WIN" if pnl and pnl > 0 else "LOSS" if pnl and pnl < 0 else "FLAT"
        sys_ = r.get("System","?").strip('"')[:20]
        strat = r.get("Strategy","?").strip('"')[:25]
        et = r.get("Entry Time","").strip('"')
        xt = r.get("Exit Time","").strip('"')
        ex_reason = r.get("Exit Reason","").strip('"')[:20]
        lines.append(f"| {i} | {sym} | {dir_} | {score} | {pnl_str}% | {result} | {sys_} | {strat} | {et} | {xt} | {ex_reason} |")

    # Unrealized PnL breakdown
    lines.append("\n## Unrealized PnL Breakdown (Active Picks)\n")

    # By asset class
    ac_pnl = defaultdict(lambda: {"count": 0, "pnl": 0, "wins": 0, "losses": 0})
    for r in active:
        ac = r.get("Asset Class","?").strip('"')
        pnl = _f(r.get("PnL%"))
        if pnl is None: continue
        ac_pnl[ac]["count"] += 1
        ac_pnl[ac]["pnl"] += min(100, max(-100, pnl))
        if pnl > 0: ac_pnl[ac]["wins"] += 1
        elif pnl < 0: ac_pnl[ac]["losses"] += 1

    lines.append("### By Asset Class\n")
    lines.append("| Asset Class | Picks | Total uPnL% | Avg uPnL% | In Profit | In Loss |")
    lines.append("|-------------|-------|-------------|-----------|-----------|---------|")
    for ac, d in sorted(ac_pnl.items()):
        avg = d["pnl"] / d["count"] if d["count"] else 0
        lines.append(f"| {ac} | {d['count']} | {d['pnl']:+.2f}% | {avg:+.2f}% | {d['wins']} | {d['losses']} |")

    # By system
    sys_pnl = defaultdict(lambda: {"count": 0, "pnl": 0, "avg_score": 0, "scores": []})
    for r in active:
        sys_ = r.get("System","?").strip('"')
        pnl = _f(r.get("PnL%"))
        score = _f(r.get("Score"))
        if pnl is None: continue
        sys_pnl[sys_]["count"] += 1
        sys_pnl[sys_]["pnl"] += min(100, max(-100, pnl))
        if score: sys_pnl[sys_]["scores"].append(score)

    lines.append("\n### By System (Top 15)\n")
    lines.append("| System | Picks | Total uPnL% | Avg uPnL% | Avg Score |")
    lines.append("|--------|-------|-------------|-----------|-----------|")
    for sys_, d in sorted(sys_pnl.items(), key=lambda x: -x[1]["pnl"])[:15]:
        avg_pnl = d["pnl"] / d["count"] if d["count"] else 0
        avg_sc = sum(d["scores"]) / len(d["scores"]) if d["scores"] else 0
        lines.append(f"| {sys_[:25]} | {d['count']} | {d['pnl']:+.2f}% | {avg_pnl:+.2f}% | {avg_sc:.0f} |")

    # By direction
    lines.append("\n### By Direction\n")
    lines.append("| Direction | Picks | Total uPnL% | Avg uPnL% | In Profit | In Loss |")
    lines.append("|-----------|-------|-------------|-----------|-----------|---------|")
    for dir_ in ["LONG", "SHORT"]:
        picks = [r for r in active if r.get("Direction","").strip('"') == dir_]
        pnls = [_f(r.get("PnL%")) for r in picks if _f(r.get("PnL%")) is not None]
        total = sum(min(100, max(-100, p)) for p in pnls)
        avg = total / len(pnls) if pnls else 0
        wins = sum(1 for p in pnls if p > 0)
        losses = sum(1 for p in pnls if p < 0)
        lines.append(f"| {dir_} | {len(picks)} | {total:+.2f}% | {avg:+.2f}% | {wins} | {losses} |")

    # Score vs PnL correlation
    lines.append("\n### Score vs Unrealized PnL (Active)\n")
    lines.append("| Score Range | Picks | Avg uPnL% | In Profit | In Loss | Hit Rate |")
    lines.append("|-------------|-------|-----------|-----------|---------|----------|")
    for lo, hi, label in [(80,101,"80+"),(60,80,"60-79"),(40,60,"40-59"),(20,40,"20-39"),(1,20,"1-19")]:
        bucket = [r for r in active if lo <= (_f(r.get("Score")) or 0) < hi]
        pnls = [_f(r.get("PnL%")) for r in bucket if _f(r.get("PnL%")) is not None]
        if not pnls: continue
        avg = sum(pnls) / len(pnls)
        wins = sum(1 for p in pnls if p > 0)
        losses = sum(1 for p in pnls if p < 0)
        hr = wins / (wins + losses) * 100 if (wins + losses) else 0
        lines.append(f"| {label} | {len(bucket)} | {avg:+.2f}% | {wins} | {losses} | {hr:.1f}% |")

    # QA issues
    qa = qa_audit(rows)
    lines.append("\n## QA Audit Results\n")
    lines.append("| Check | Count | Status |")
    lines.append("|-------|-------|--------|")
    for key, val in qa.items():
        if key == "total_rows": continue
        status = "PASS" if val == 0 else "WARN" if val < 10 else "FAIL"
        lines.append(f"| {key} | {val} | {status} |")

    return "\n".join(lines)


def main():
    csv_path = Path(r"c:\Users\zerou\Downloads\antigravity_all_picks_2026-03-29.csv")
    if not csv_path.exists():
        print(f"CSV not found at {csv_path}")
        return

    rows = load_csv(csv_path)
    print(f"Loaded {len(rows)} rows")

    # Generate TOP_SCORED.MD
    md = generate_top_scored_md(rows)
    out = ROOT / "TOP_SCORED.MD"
    out.write_text(md, encoding="utf-8")
    print(f"Written {out} ({len(md)} chars)")

    # Print QA summary
    qa = qa_audit(rows)
    print(f"\nQA SUMMARY:")
    for k, v in qa.items():
        flag = " *** FIX" if v > 10 and k != "total_rows" and k != "active" and k != "closed" else ""
        print(f"  {k}: {v}{flag}")


if __name__ == "__main__":
    main()
