import json

with open("alpha_engine/data/closed_picks.json") as f:
    closed = json.load(f)

strat_perf = {}
for p in closed:
    strat = p.get("strategy", "unknown")
    pnl = p.get("pnl_pct", 0) or 0
    status = p.get("status", "")
    if strat not in strat_perf:
        strat_perf[strat] = {"won": 0, "lost": 0, "total_pnl": 0, "trades": 0}
    strat_perf[strat]["trades"] += 1
    strat_perf[strat]["total_pnl"] += float(pnl)
    if status == "WON":
        strat_perf[strat]["won"] += 1
    elif status == "LOST":
        strat_perf[strat]["lost"] += 1

print(f"Total closed: {len(closed)}")
print()
print(f"{'Strategy':<48} {'Trades':>6} {'Won':>5} {'WR%':>6} {'PnL%':>8}")
print("=" * 78)
for s, d in sorted(strat_perf.items(), key=lambda x: -x[1]["trades"])[:30]:
    wr = (d["won"] / d["trades"] * 100) if d["trades"] > 0 else 0
    pnl = d["total_pnl"]
    print(f"{s[:47]:<48} {d['trades']:>6} {d['won']:>5} {wr:>5.1f}% {pnl:>+7.1f}%")

print()
print("=== ML ENHANCED STRATEGIES ===")
for s, d in sorted(strat_perf.items()):
    if "ml_enhanced" in s.lower():
        wr = (d["won"] / d["trades"] * 100) if d["trades"] > 0 else 0
        print(f"  {s:<55} {d['trades']:>3}T {d['won']:>3}W {wr:>5.1f}% {d['total_pnl']:>+7.2f}%")

# Check what yahoo_analyst actually does
print()
print("=== YAHOO ANALYST ===")
for s, d in sorted(strat_perf.items()):
    if "yahoo" in s.lower():
        wr = (d["won"] / d["trades"] * 100) if d["trades"] > 0 else 0
        print(f"  {s}: {d['trades']}T {d['won']}W {wr:.1f}% {d['total_pnl']:+.2f}%")

# Check cta strategies
print()
print("=== CTA STRATEGIES ===")
for s, d in sorted(strat_perf.items()):
    if "cta_" in s.lower():
        wr = (d["won"] / d["trades"] * 100) if d["trades"] > 0 else 0
        print(f"  {s}: {d['trades']}T {d['won']}W {wr:.1f}% {d['total_pnl']:+.2f}%")
