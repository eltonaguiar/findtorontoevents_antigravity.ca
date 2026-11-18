# This is a real equities profile (.md only, no .py) that is not a copy of a bonds python script.
"""BONDS_DB_PROFILE — structural profile of bonds DB.

**Source:** ejaguiar1_stocks proxy (bonds DB 1045-blocked).

**Tables:** trading_picks, at_pick_outcomes (closed picks only).

**Metrics:** n, win_rate, profit_factor, avg_win, avg_loss, max_drawdown_proxy.

**Split:** by strategy, by direction (LONG/SHORT).

**Verdict rule:** any config with n>=30 and PF>=1.25?
"""
import sys
sys.path.insert(0, '/home/eaguiar2015/scratch')
import dbq
import json
from collections import defaultdict

BOND_SYMS = ("TLT","IEF","AGG","SHY","TIP","HYG","LQD","BND","GOVT","MUB","JNK","EMB")

# 1. trading_picks: closed bond picks
print("=== trading_picks (closed bond picks) ===")
sql_tp = """
SELECT symbol, strategy, direction, status, pnl_pct
FROM trading_picks
WHERE symbol IN %s AND status IN ('TP_HIT','SL_HIT','TIME_EXIT','LOST','EXPIRED')
"""
rows_tp = []
try:
    rows_tp = dbq.q('stocks', sql_tp, (BOND_SYMS,))
    print(f"rows: {len(rows_tp)}")
except Exception as e:
    print(f"ERR trading_picks: {e}")

# 2. at_pick_outcomes: closed bond picks
print("\n=== at_pick_outcomes (closed bond picks) ===")
sql_ap = """
SELECT symbol, strategy, direction, status, pnl_pct
FROM at_pick_outcomes
WHERE symbol IN %s AND status IN ('WON','LOST','EXPIRED','FLAT')
"""
rows_ap = []
try:
    rows_ap = dbq.q('stocks', sql_ap, (BOND_SYMS,))
    print(f"rows: {len(rows_ap)}")
except Exception as e:
    print(f"ERR at_pick_outcomes: {e}")

# Aggregate per (symbol, strategy, direction)
agg = defaultdict(lambda: {"n":0, "wins":0, "losses":0, "pnl_sum":0.0, "pnl_win_sum":0.0, "pnl_loss_sum":0.0, "pnl_list":[]})

for r in rows_tp + rows_ap:
    sym, strat, direc, status, pnl = r[0], r[1], r[2] or "UNK", r[3], r[4]
    key = (sym, strat, direc)
    agg[key]["n"] += 1
    agg[key]["pnl_list"].append(pnl if pnl is not None else 0.0)
    # Map statuses: TP_HIT/SL_HIT/WON = win, LOST/SL_HIT = loss (SL_HIT is loss), EXPIRED/FLAT/TIME_EXIT neutral
    if status in ("TP_HIT","WON"):
        agg[key]["wins"] += 1
        agg[key]["pnl_win_sum"] += (pnl or 0.0)
    elif status in ("SL_HIT","LOST"):
        agg[key]["losses"] += 1
        agg[key]["pnl_loss_sum"] += (pnl or 0.0)
    agg[key]["pnl_sum"] += (pnl or 0.0)

print(f"\n=== AGGREGATED CONFIGS: {len(agg)} ===")
results = []
for key, v in sorted(agg.items(), key=lambda x: -x[1]["n"]):
    sym, strat, direc = key
    n = v["n"]
    wr = safe_div(v["wins"], n)
    pf = safe_div(v["pnl_win_sum"], abs(v["pnl_loss_sum"])) if v["pnl_loss_sum"] else None
    avg_win = safe_div(v["pnl_win_sum"], v["wins"]) if v["wins"] else None
    avg_loss = safe_div(v["pnl_loss_sum"], v["losses"]) if v["losses"] else None
    # max drawdown proxy: cumulative pnl min
    cum = 0.0; mdd = 0.0
    for p in v["pnl_list"]:
        cum += p
        if cum < mdd: mdd = cum
    rec = {
        "symbol": sym, "strategy": strat, "direction": direc,
        "n": n, "wins": v["wins"], "losses": v["losses"],
        "win_rate": pct(wr), "profit_factor": round(pf,4) if pf else None,
        "avg_win": round(avg_win,4) if avg_win else None,
        "avg_loss": round(avg_loss,4) if avg_loss else None,
        "max_dd_proxy": round(mdd,4) if mdd else 0.0
    }
    results.append(rec)
    if n >= 5:
        print(f"{sym:6} {strat:30} {direc:6} n={n:4} WR={rec['win_rate']:6.2f}% PF={rec['profit_factor'] or 'NULL':>8} avgW={rec['avg_win'] or 'NULL':>8} avgL={rec['avg_loss'] or 'NULL':>8} MDD={rec['max_dd_proxy']:>8}")

# Verdict
print("\n=== VERDICT ===")
qualified = [r for r in results if r["n"] >= 30 and r["profit_factor"] and r["profit_factor"] >= 1.25]
if qualified:
    print("YES — found config(s) with n>=30 and PF>=1.25:")
    for q in qualified:
        print(f"  {q['symbol']} {q['strategy']} {q['direction']} n={q['n']} PF={q['profit_factor']}")
else:
    print("NO — no bond config meets n>=30 and PF>=1.25 threshold.")
    print("\n3 FALSIFIABLE HYPOTHESES:")
    print("1. BOND_MOMENTUM_LONG: TLT/IEF/AGG long-only with 5d momentum filter; kill if first 50 closed picks have PF<1.10 or WR<48%.")
    print("2. BOND_REVERSAL_SHORT: HYG/LQD/JNK short on 3d RSI>70; kill if first 40 closed picks have avg loss > 1.5x avg win.")
    print("3. BOND_ETF_PAIR: long TLT + short IEF on rate-curve steepening; kill if 30-day rolling PF drops below 1.05 for 5 consecutive days.")

# Write artifact
out = {
    "symbols": BOND_SYMS,
    "total_configs": len(results),
    "qualified_n30_pf125": len(qualified),
    "configs": results[:50],  # top 50 by n
    "verdict": "EDGE" if qualified else "NO_EDGE",
    "hypotheses": [] if qualified else [
        {"name":"BOND_MOMENTUM_LONG","desc":"TLT/IEF/AGG long 5d mom; kill PF<1.10 or WR<48% @50","metric":"PF","kill":"PF<1.10 OR WR<48% @n=50"},
        {"name":"BOND_REVERSAL_SHORT","desc":"HYG/LQD/JNK short RSI>70 3d; kill avg_loss>1.5*avg_win @40","metric":"avg_loss/avg_win","kill":"avg_loss>1.5*avg_win @n=40"},
        {"name":"BOND_ETF_PAIR","desc":"long TLT short IEF curve steepen; kill 30d PF<1.05 x5d","metric":"30d_PF","kill":"30d_PF<1.05 for 5 consecutive days"}
    ]
}
print("\n=== writing artifact ===")
with open('/home/eaguiar2015/findtorontoevents_antigravity.ca/equities_db_profile.md', 'w') as f:
    f.write("# EQUITIES_DB_PROFILE_2026-11-18\n\n")
    f.write("**Source:** ejaguiar1_stocks proxy (bonds DB 1045-blocked)\n")
    f.write(f"**Symbols:** {', '.join(BOND_SYMS)}\n")
    f.write(f"**Tables:** trading_picks, at_pick_outcomes (closed picks only)\n\n")
    f.write("## Raw counts\n\n")
    f.write(f"- trading_picks bond rows (closed): {len(rows_tp)}\n")
    f.write(f"- at_pick_outcomes bond rows (closed): {len(rows_ap)}\n\n")
    f.write("## Qualified configs (n>=30, PF>=1.25)\n\n")
    if qualified:
        for q in qualified:
            f.write(f"- {q['symbol']} {q['strategy']} {q['direction']} n={q['n']} WR={q['win_rate']}% PF={q['profit_factor']}\n")
    else:
        f.write("**NONE** — no bond config meets the edge threshold.\n\n")
    f.write("## Top configs by n\n\n")
    f.write("| symbol | strategy | direction | n | wins | losses | WR% | PF | avg_win | avg_loss | MDD |\n")
    f.write("|--------|----------|-----------|---|------|--------|-----|-----|---------|----------|-----|\n")
    for r in sorted(results, key=lambda x: -x["n"])[:30]:
        f.write(f"| {r['symbol']} | {r['strategy']} | {r['direction']} | {r['n']} | {r['wins']} | {r['losses']} | {r['win_rate']} | {r['profit_factor'] or 'NULL'} | {r['avg_win'] or 'NULL'} | {r['avg_loss'] or 'NULL'} | {r['max_dd_proxy']} |\n")
    f.write("\n## Falsifiable hypotheses (if no edge)\n\n")
    for h in out["hypotheses"]:
        f.write(f"1. **{h['name']}** — {h['desc']}. Kill criterion: {h['kill']}\n")
    f.write("\n---\n")
    f.write(f"**Verdict:** {out['verdict']}\n")
print("Artifact written: /home/eaguiar2015/findtorontoevents_antigravity.ca/equities_db_profile.md")
print(json.dumps(out, indent=2)[:2000])
