#!/usr/bin/env python3
"""
Score-vs-Performance Validator
================================
Analyzes dashboard_payload.json to verify that higher-scored picks
actually perform better than lower-scored picks. Identifies outliers
and score miscalibrations.
"""
import json, sys, os
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path("e:/findtorontoevents_antigravity.ca")
PAYLOAD = ROOT / "audit_trail/data/dashboard_payload.json"

def load_json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def safe_float(v, default=0.0):
    try:
        return float(v or default)
    except (ValueError, TypeError):
        return default

def main():
    d = load_json(PAYLOAD)
    
    active_picks = d.get("picks", {}).get("active", [])
    closed_picks = d.get("picks", {}).get("recent_closed", [])
    
    print("=" * 80)
    print("  SCORE-vs-PERFORMANCE VALIDATION")
    print("  " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    print("=" * 80)
    print("  Active picks:", len(active_picks))
    print("  Closed picks:", len(closed_picks))
    
    # ============================================================
    # 1. ACTIVE PICKS: Score → PnL correlation
    # ============================================================
    print("\n" + "=" * 60)
    print("  1. ACTIVE PICKS: Score-to-PnL Correlation")
    print("=" * 60)
    
    buckets = {
        "90-100": {"picks": [], "label": "A+ (90-100)"},
        "70-89":  {"picks": [], "label": "A/B (70-89)"},
        "50-69":  {"picks": [], "label": "C (50-69)"},
        "30-49":  {"picks": [], "label": "D (30-49)"},
        "0-29":   {"picks": [], "label": "F (<30)"},
    }
    
    no_score = 0
    for p in active_picks:
        score = safe_float(p.get("score"))
        if score == 0 and not p.get("score"):
            no_score += 1
            continue
        if score >= 90: buckets["90-100"]["picks"].append(p)
        elif score >= 70: buckets["70-89"]["picks"].append(p)
        elif score >= 50: buckets["50-69"]["picks"].append(p)
        elif score >= 30: buckets["30-49"]["picks"].append(p)
        else: buckets["0-29"]["picks"].append(p)
    
    print("\n  {:20s} {:>6s} {:>8s} {:>8s} {:>8s} {:>8s} {:>7s}".format(
        "Bucket", "Count", "AvgPnL%", "MedPnL%", "WR", "AvgScr", "Boosted"))
    print("  " + "-" * 75)
    
    for bkey in ["90-100", "70-89", "50-69", "30-49", "0-29"]:
        bdata = buckets[bkey]
        picks = bdata["picks"]
        if not picks:
            print("  {:20s} {:>6d}   (empty)".format(bdata["label"], 0))
            continue
        
        pnls = [safe_float(p.get("pnl_pct")) for p in picks]
        pnls_nonzero = [x for x in pnls if x != 0]
        winners = sum(1 for x in pnls_nonzero if x > 0) if pnls_nonzero else 0
        wr = winners / len(pnls_nonzero) * 100 if pnls_nonzero else 0
        avg_pnl = sum(pnls) / len(pnls) if pnls else 0
        avg_score = sum(safe_float(p.get("score")) for p in picks) / len(picks)
        boosted = sum(1 for p in picks if p.get("_score_boosted"))
        
        sorted_pnls = sorted(pnls)
        median_pnl = sorted_pnls[len(sorted_pnls)//2] if sorted_pnls else 0
        
        print("  {:20s} {:>6d} {:>+8.2f} {:>+8.2f} {:>7.1f}% {:>8.1f} {:>7d}".format(
            bdata["label"], len(picks), avg_pnl, median_pnl, wr, avg_score, boosted))
    
    if no_score:
        print("  (No score: {} picks)".format(no_score))
    
    # ============================================================
    # 2. CLOSED PICKS: Score → Outcome
    # ============================================================
    print("\n" + "=" * 60)
    print("  2. CLOSED PICKS: Score-to-Outcome")
    print("=" * 60)
    
    if closed_picks:
        closed_buckets = defaultdict(list)
        for p in closed_picks:
            score = safe_float(p.get("score"))
            if score >= 70: closed_buckets["70+"].append(p)
            elif score >= 50: closed_buckets["50-69"].append(p)
            elif score >= 30: closed_buckets["30-49"].append(p)
            else: closed_buckets["<30"].append(p)
        
        print("\n  {:15s} {:>6s} {:>7s} {:>8s} {:>10s}".format(
            "Bucket", "Count", "WR", "AvgPnL%", "TotalPnL%"))
        print("  " + "-" * 50)
        
        for label in ["70+", "50-69", "30-49", "<30"]:
            picks = closed_buckets.get(label, [])
            if not picks:
                continue
            pnls = [safe_float(p.get("pnl_pct")) for p in picks]
            winners = sum(1 for x in pnls if x > 0)
            wr = winners / len(picks) * 100 if picks else 0
            avg = sum(pnls) / len(pnls) if pnls else 0
            total = sum(pnls)
            print("  {:15s} {:>6d} {:>6.1f}% {:>+8.2f} {:>+10.2f}".format(
                label, len(picks), wr, avg, total))
    else:
        print("  No closed picks available")
    
    # ============================================================
    # 3. COPY TRADER FAMILY PERFORMANCE
    # ============================================================
    print("\n" + "=" * 60)
    print("  3. COPY TRADER FAMILY PERFORMANCE (Active + Closed)")
    print("=" * 60)
    
    ct_families = ["copy_trader_intel", "copy_trader_clones", "copy_trader_highscore",
                    "copy_trader_variations", "copy_trader_consensus"]
    
    all_picks = active_picks + closed_picks
    
    for fam in ct_families:
        fam_picks = [p for p in all_picks 
                     if (p.get("source_system", "") == fam or 
                         fam in (p.get("strategy", "") or "").lower())]
        if not fam_picks:
            continue
        
        pnls = [safe_float(p.get("pnl_pct")) for p in fam_picks]
        pnls_with_data = [x for x in pnls if x != 0]
        winners = sum(1 for x in pnls_with_data if x > 0)
        wr = winners / len(pnls_with_data) * 100 if pnls_with_data else 0
        avg_score = sum(safe_float(p.get("score")) for p in fam_picks) / len(fam_picks)
        
        print("\n  {} ({} picks, avg score: {:.1f})".format(fam, len(fam_picks), avg_score))
        print("    WR: {:.1f}% ({}/{} with PnL data)".format(
            wr, winners, len(pnls_with_data)))
        print("    Total PnL: {:+.2f}%, Avg PnL: {:+.2f}%".format(
            sum(pnls), sum(pnls)/len(pnls) if pnls else 0))
        
        # By symbol
        by_sym = defaultdict(list)
        for p in fam_picks:
            by_sym[p.get("symbol", "?")].append(safe_float(p.get("pnl_pct")))
        
        print("    Top symbols:")
        for sym, sym_pnls in sorted(by_sym.items(), key=lambda x: -len(x[1]))[:5]:
            sym_wr = sum(1 for x in sym_pnls if x > 0) / max(1, sum(1 for x in sym_pnls if x != 0)) * 100
            print("      {}: {} picks, WR {:.0f}%, PnL {:+.2f}%".format(
                sym, len(sym_pnls), sym_wr, sum(sym_pnls)))
    
    # ============================================================
    # 4. OUTLIER DETECTION
    # ============================================================
    print("\n" + "=" * 60)
    print("  4. OUTLIER DETECTION")
    print("=" * 60)
    
    # High-score big losers
    print("\n  HIGH-SCORE LOSERS (score >= 70, PnL < -5%):")
    bad_high = [p for p in active_picks 
                if safe_float(p.get("score")) >= 70 and safe_float(p.get("pnl_pct")) < -5]
    bad_high.sort(key=lambda x: safe_float(x.get("pnl_pct")))
    for p in bad_high[:10]:
        print("    {} {} score={} pnl={:+.2f}% [{}] boosted={}".format(
            p.get("symbol", "?"), p.get("direction", "?"),
            p.get("score"), safe_float(p.get("pnl_pct")),
            p.get("source_system", "?"), p.get("_score_boosted", False)))
    if not bad_high:
        print("    None found - scoring looks healthy!")
    
    # Low-score big winners 
    print("\n  LOW-SCORE WINNERS (score < 40, PnL > +5%):")
    good_low = [p for p in active_picks
                if safe_float(p.get("score")) < 40 and safe_float(p.get("pnl_pct")) > 5]
    good_low.sort(key=lambda x: -safe_float(x.get("pnl_pct")))
    for p in good_low[:10]:
        print("    {} {} score={} pnl={:+.2f}% [{}]".format(
            p.get("symbol", "?"), p.get("direction", "?"),
            p.get("score"), safe_float(p.get("pnl_pct")),
            p.get("source_system", "?")))
    if not good_low:
        print("    None found - no hidden winners!")
    
    # ============================================================
    # 5. SOURCE SYSTEM PERFORMANCE RANKING  
    # ============================================================
    print("\n" + "=" * 60)
    print("  5. ALL SOURCE SYSTEMS RANKED BY WR")
    print("=" * 60)
    
    by_source = defaultdict(list)
    for p in all_picks:
        src = p.get("source_system", "?")
        pnl = safe_float(p.get("pnl_pct"))
        by_source[src].append(pnl)
    
    ranked = []
    for src, pnls in by_source.items():
        with_data = [x for x in pnls if x != 0]
        wins = sum(1 for x in with_data if x > 0)
        wr = wins / len(with_data) * 100 if with_data else 0
        ranked.append((src, len(pnls), wr, sum(pnls), len(with_data)))
    
    ranked.sort(key=lambda x: (-x[2], -x[1]))
    
    print("\n  {:35s} {:>6s} {:>7s} {:>9s} {:>7s}".format(
        "Source System", "Total", "WR", "TotalPnL", "w/Data"))
    print("  " + "-" * 70)
    for src, total, wr, total_pnl, w_data in ranked[:25]:
        print("  {:35s} {:>6d} {:>6.1f}% {:>+9.2f} {:>7d}".format(
            src[:35], total, wr, total_pnl, w_data))
    
    # ============================================================
    # 6. CONSENSUS OPPORTUNITY ANALYSIS
    # ============================================================
    print("\n" + "=" * 60)
    print("  6. COPY TRADER CONSENSUS (Same symbol + direction)")  
    print("=" * 60)
    
    ct_active = [p for p in active_picks
                 if "copy_trader" in (p.get("source_system", "") or "").lower() or
                    "copy_hl" in (p.get("strategy", "") or "").lower()]
    
    consensus = defaultdict(lambda: {"traders": [], "picks": []})
    for p in ct_active:
        key = (p.get("symbol", "?"), (p.get("direction", "LONG") or "LONG").upper())
        trader = p.get("strategy", p.get("source_system", "?"))
        consensus[key]["traders"].append(trader)
        consensus[key]["picks"].append(p)
    
    multi_agree = {k: v for k, v in consensus.items() if len(set(v["traders"])) >= 2}
    
    if multi_agree:
        print("\n  FOUND {} consensus targets (2+ traders agree):".format(len(multi_agree)))
        for (sym, direction), data in sorted(multi_agree.items(), key=lambda x: -len(x[1]["traders"])):
            unique_traders = set(data["traders"])
            avg_conf = sum(safe_float(p.get("confidence", 0.5)) for p in data["picks"]) / len(data["picks"])
            print("    {} {}: {} traders agree (confidence avg: {:.2f})".format(
                sym, direction, len(unique_traders), avg_conf))
            for t in unique_traders:
                print("      - {}".format(t[:60]))
    else:
        print("  No multi-trader consensus found in current CT picks")
        print("  (all {} CT picks from different traders)".format(len(ct_active)))
    
    # Summary
    print("\n" + "=" * 80)
    print("  VALIDATION SUMMARY")
    print("=" * 80)
    print("  Active picks: {}".format(len(active_picks)))
    print("  Closed picks: {}".format(len(closed_picks)))
    print("  Copy trader picks: {}".format(
        len([p for p in all_picks if "copy_trader" in (p.get("source_system","") or "")])))
    print("  High-score losers: {}".format(len(bad_high)))
    print("  Low-score winners: {}".format(len(good_low)))
    print("  Consensus targets: {}".format(len(multi_agree)))
    print("=" * 80)

if __name__ == "__main__":
    main()
