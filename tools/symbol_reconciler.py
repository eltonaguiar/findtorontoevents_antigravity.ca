"""
Symbol Reconciler — cross-check `quality_gates.py::BLOCKED_SYMBOLS`
performance against current `alpha_engine/data/closed_picks.json`.

Identifies blocked symbols that may have regained their edge and are suitable
for unblocking (RESURRECTION_CANDIDATE).

Output: `audit_dashboard/data/symbol_reconciliation.json`
"""

import json
import re
import os
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parents[1]
QG_PATH = REPO_ROOT / "audit_trail" / "quality_gates.py"
DASHBOARD_DATA_PATH = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
UNIVERSAL_PICKS_PATH = REPO_ROOT / "audit_trail" / "data" / "universal_resolved_picks.json"
OUT_PATH = REPO_ROOT / "audit_dashboard" / "data" / "symbol_reconciliation.json"

# Resurrection criteria (matching REHAB_CRITERIA.md)
SHADOW_N = 10
SHADOW_WR = 50.0
SHADOW_PF = 1.3

PROBATION_N = 20
PROBATION_WR = 52.0
PROBATION_PF = 1.3

FULL_UNBLOCK_N = 30
FULL_UNBLOCK_WR = 52.0
FULL_UNBLOCK_PF = 1.5

def parse_blocked_symbols() -> list[dict]:
    """Parse BLOCKED_SYMBOLS set in quality_gates.py."""
    if not QG_PATH.exists():
        return []
    src = QG_PATH.read_text(encoding="utf-8")
    
    # Try multiple ways to capture the block
    symbols = []
    
    # Method 1: Explicit BLOCKED_SYMBOLS block
    m = re.search(r"BLOCKED_SYMBOLS\s*=\s*\{(.*?)\}", src, re.MULTILINE | re.DOTALL)
    if m:
        block = m.group(1)
        for line in block.splitlines():
            line = line.strip()
            # Match "SYMBOL", # comment
            entry_m = re.match(r'["\']([^"\']+)["\']\s*,?\s*(#\s*(.*))?', line)
            if entry_m:
                symbols.append({"symbol": entry_m.group(1), "comment": entry_m.group(3) or "", "source": "BLOCKED_SYMBOLS"})
    
    # Method 2: EQUITY_BLOCKED_SYMBOLS
    m = re.search(r"EQUITY_BLOCKED_SYMBOLS\s*=\s*\{(.*?)\}", src, re.MULTILINE | re.DOTALL)
    if m:
        block = m.group(1)
        for line in block.splitlines():
            line = line.strip()
            entry_m = re.match(r'["\']([^"\']+)["\']\s*,?\s*(#\s*(.*))?', line)
            if entry_m:
                symbols.append({"symbol": entry_m.group(1), "comment": entry_m.group(3) or "", "source": "EQUITY_BLOCKED_SYMBOLS"})

    # Method 3: PENDING_UNBLOCK_REVIEW
    m = re.search(r"PENDING_UNBLOCK_REVIEW:\s*dict\[str,\s*str\]\s*=\s*\{(.*?)\}", src, re.MULTILINE | re.DOTALL)
    if m:
        block = m.group(1)
        for line in block.splitlines():
            line = line.strip()
            # Match "SYMBOL": "DATE", # comment
            entry_m = re.match(r'["\']([^"\']+)["\']\s*:\s*["\']([^"\']+)["\']\s*,?\s*(#\s*(.*))?', line)
            if entry_m:
                symbols.append({"symbol": entry_m.group(1), "comment": f"Review due {entry_m.group(2)}. {entry_m.group(4) or ''}", "source": "PENDING_REVIEW"})

    return symbols

def load_all_picks() -> list:
    picks = []
    # Try dashboard data first
    if DASHBOARD_DATA_PATH.exists():
        try:
            with open(DASHBOARD_DATA_PATH, "r", encoding="utf-8") as f:
                d = json.load(f)
                picks.extend(d.get("picks", {}).get("recent_closed", []))
                # Also check systems
                for s in d.get("systems", []):
                    picks.extend(s.get("closed", []))
        except Exception: pass
    
    # Try universal data
    if UNIVERSAL_PICKS_PATH.exists():
        try:
            with open(UNIVERSAL_PICKS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                picks.extend(data if isinstance(data, list) else data.get("picks", []))
        except Exception: pass
        
    return picks

def analyze_symbol_performance(picks: list) -> dict:
    perf = defaultdict(lambda: {"closed": 0, "wins": 0, "losses": 0, "total_pnl": 0.0, "pnl_list": []})
    for p in picks:
        sym = p.get("symbol")
        if not sym: continue
        pnl = float(p.get("pnl_pct") or 0)
        perf[sym]["closed"] += 1
        perf[sym]["total_pnl"] += pnl
        perf[sym]["pnl_list"].append(pnl)
        if pnl > 0: perf[sym]["wins"] += 1
        elif pnl < 0: perf[sym]["losses"] += 1
    
    # Calculate metrics
    results = {}
    for sym, stats in perf.items():
        n = stats["closed"]
        wr = (stats["wins"] / n * 100) if n > 0 else 0
        
        # Profit Factor
        gross_profit = sum(x for x in stats["pnl_list"] if x > 0)
        gross_loss = abs(sum(x for x in stats["pnl_list"] if x < 0))
        pf = gross_profit / gross_loss if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)
        
        results[sym] = {
            "n": n,
            "wr": wr,
            "pf": pf,
            "total_pnl": stats["total_pnl"]
        }
    return results

def reconcile():
    blocked = parse_blocked_symbols()
    all_picks = load_all_picks()
    perf_data = analyze_symbol_performance(all_picks)
    
    rows = []
    counts = {"KEEP_BLOCKED": 0, "SHADOW": 0, "PROBATION": 0, "FULL_UNBLOCK_CANDIDATE": 0, "NO_DATA": 0}
    
    for b in blocked:
        sym = b["symbol"]
        live = perf_data.get(sym)
        
        verdict = "KEEP_BLOCKED"
        if not live:
            verdict = "NO_DATA"
        else:
            n, wr, pf = live["n"], live["wr"], live["pf"]
            
            if n >= FULL_UNBLOCK_N and wr >= FULL_UNBLOCK_WR and pf >= FULL_UNBLOCK_PF:
                verdict = "FULL_UNBLOCK_CANDIDATE"
            elif n >= PROBATION_N and wr >= PROBATION_WR and pf >= PROBATION_PF:
                verdict = "PROBATION"
            elif n >= SHADOW_N and wr >= SHADOW_WR and pf >= SHADOW_PF:
                verdict = "SHADOW"
        
        counts[verdict] += 1
        rows.append({
            "symbol": sym,
            "source": b["source"],
            "comment": b["comment"],
            "live_n": live["n"] if live else 0,
            "live_wr": live["wr"] if live else 0,
            "live_pf": live["pf"] if live else 0,
            "live_pnl": live["total_pnl"] if live else 0,
            "verdict": verdict
        })
    
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": counts,
        "rows": rows
    }

def main():
    result = reconcile()
    print(f"Reconciled {len(result['rows'])} blocked/pending symbols:")
    for k, v in result["summary"].items():
        print(f"  {k}: {v}")
    
    for stage in ["FULL_UNBLOCK_CANDIDATE", "PROBATION", "SHADOW"]:
        print(f"\n{stage}:")
        for r in result["rows"]:
            if r["verdict"] == stage:
                print(f"  * {r['symbol']:15} WR: {r['live_wr']:.1f}% | PF: {r['live_pf']:.2f} | n: {r['live_n']} ({r['source']})")
    
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\nWrote {OUT_PATH}")

if __name__ == "__main__":
    main()
