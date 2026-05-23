#!/usr/bin/env python3
"""
Deep-dive analysis: per-strategy density check and lb_None trader analysis.
"""
import json
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "alpha_engine"))
sys.path.insert(0, str(ROOT / "tools"))

from edge_stability_harness import _windows, _window_eff, _rdate, _won, _num
from charter_slippage import deduct_slippage

# Load canonical picks
with open(ROOT / "alpha_engine" / "data" / "closed_picks.json") as f:
    raw = json.load(f)

# Load the registry for comparison
with open(ROOT / "audit_dashboard" / "data" / "pf_registry.json") as f:
    registry = json.load(f)

print("=" * 70)
print("STRATEGY DENSITY ANALYSIS - Which strategies can even be tested?")
print("=" * 70)

# Dedup
seen = set()
picks = []
for p in raw:
    strat = p.get("source_system", "") or p.get("strategy", "")
    sym = p.get("symbol", "")
    direction = p.get("direction", "")
    entry_dt = p.get("entry_date", "") or p.get("entry_time", "") or p.get("timestamp", "")
    if isinstance(entry_dt, str) and "T" in entry_dt:
        entry_dt = entry_dt[:10]
    ep = p.get("entry_price")
    ep_rounded = round(float(ep), 2) if ep is not None else None
    key = (strat, sym, direction, entry_dt, ep_rounded)
    if key in seen:
        continue
    seen.add(key)
    picks.append(p)

# Apply policy clean
clean = []
for p in picks:
    if p.get("forward_test_only"):
        continue
    status = str(p.get("status") or "").upper()
    if status not in {"WON", "LOST", "CLOSED"}:
        continue
    if p.get("pnl_pct") is None:
        continue
    ac = (p.get("asset_class") or "").upper()
    if ac in {"UNKNOWN", ""}:
        continue
    p["_pnl_pct_gross"] = float(p["pnl_pct"])
    p["_pnl_pct_net"] = deduct_slippage(float(p["pnl_pct"]), ac)
    clean.append(p)

print(f"After dedup + policy clean: {len(clean)} picks")
print()

# ============================================================
# Per-strategy density
# ============================================================
by_strat = defaultdict(list)
for p in clean:
    strat = p.get("strategy", "unknown")
    ac = (p.get("asset_class") or "").upper()
    key = f"{ac}/{strat}"
    by_strat[key].append(p)

print("Strategies with >=20 total picks (potential harness candidates):")
print(f"{'AssetClass/Strategy':<55} {'N':>5} {'WR':>6} {'PF':>6}")
print("-" * 75)

candidates = []
for key, ps in sorted(by_strat.items(), key=lambda x: -len(x[1])):
    n = len(ps)
    if n < 20:
        continue
    wins = sum(1 for p in ps if p.get("status") == "WON" or (p.get("pnl_pct") or 0) > 0)
    losses = n - wins
    wr = wins / n * 100 if n > 0 else 0
    gross_profit = sum(p.get("_pnl_pct_gross", 0) for p in ps if p.get("_pnl_pct_gross", 0) > 0)
    gross_loss = sum(abs(p.get("_pnl_pct_gross", 0)) for p in ps if p.get("_pnl_pct_gross", 0) < 0)
    pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    print(f"{key:<55} {n:>5} {wr:>5.1f}% {pf:>6.2f}")
    candidates.append((key, ps, n, wr, pf))

# ============================================================
# Try harness on top candidates
# ============================================================
print(f"\n{'='*70}")
print("HARNESS TESTING on strategies with sufficient density (n>=40)")
print(f"{'='*70}")

for key, ps, n, wr, pf in candidates:
    if n < 40:
        continue

    dated = [(p, _rdate(p)) for p in ps if _rdate(p)]
    if not dated:
        continue

    latest = max(d for _, d in dated)
    wins_list = [w for w in _windows(ps, 14) if len(w) >= 30]

    if len(wins_list) < 3:
        print(f"\n  {key} (n={n}): Only {len(wins_list)} windows with n>=30 - UNTESTABLE")
        continue

    effs_conf = []
    for i, w in enumerate(wins_list):
        e = _window_eff(w, "confidence")
        effs_conf.append({"window": i, "n": len(w), "eff": e})

    scored_conf = [r for r in effs_conf if r["eff"] is not None]
    strong_conf = [r for r in scored_conf if abs(r["eff"]) >= 0.30]
    pos_conf = [r for r in strong_conf if r["eff"] > 0]
    neg_conf = [r for r in strong_conf if r["eff"] < 0]

    ver_c = "PASS" if (len(strong_conf) >= 3 and
                       (len(pos_conf) == len(strong_conf) or len(neg_conf) == len(strong_conf))) else "KILL"

    effs_elite = []
    for i, w in enumerate(wins_list):
        e = _window_eff(w, "elite_score")
        effs_elite.append({"window": i, "n": len(w), "eff": e})

    scored_elite = [r for r in effs_elite if r["eff"] is not None]
    strong_elite = [r for r in scored_elite if abs(r["eff"]) >= 0.30]
    pos_elite = [r for r in strong_elite if r["eff"] > 0]
    neg_elite = [r for r in strong_elite if r["eff"] < 0]

    ver_e = "PASS" if (len(strong_elite) >= 3 and
                       (len(pos_elite) == len(strong_elite) or len(neg_elite) == len(strong_elite))) else "KILL"

    print(f"\n  {key} (n={n}, WR={wr:.1f}%, PF={pf:.2f})")
    print(f"    Windows (n>=30): {len(wins_list)}")
    eff_parts = []
    for e, ec in zip(effs_conf, effs_elite):
        c = f"conf:{e['eff']:+.2f}" if e['eff'] is not None else "conf:n/a"
        el = f"elite:{ec['eff']:+.2f}" if ec['eff'] is not None else "elite:n/a"
        eff_parts.append(f"w{e['window']}(n={e['n']})[{c},{el}]")
    print(f"    Effs: {' '.join(eff_parts)}")
    print(f"    confidence: {ver_c} (strong={len(strong_conf)}/{len(scored_conf)}, pos={len(pos_conf)}, neg={len(neg_conf)})")
    print(f"    elite_score: {ver_e} (strong={len(strong_elite)}/{len(scored_elite)}, pos={len(pos_elite)}, neg={len(neg_elite)})")

# ============================================================
# lb_None trader analysis
# ============================================================
print(f"\n{'='*70}")
print("COPYTRADER: lb_None DEEP DIVE")
print(f"{'='*70}")

with open(ROOT / "copy_trader_intel" / "data" / "closed_trades.json") as f:
    ct_trades = json.load(f)

lb_trades = [t for t in ct_trades if t.get("clone_source_trader") == "lb_None" or
             t.get("strategy", "").startswith("copy_hl_lb_None")]

print(f"lb_None total trades: {len(lb_trades)}")

outcomes = [t for t in lb_trades if t.get("outcome") in ("WON", "LOST")]
print(f"With WON/LOST outcome: {len(outcomes)}")
if outcomes:
    wins = sum(1 for t in outcomes if t["outcome"] == "WON")
    print(f"  WR: {wins}/{len(outcomes)} = {wins/len(outcomes)*100:.1f}%")

with_fw = [t for t in lb_trades if t.get("forward_wr") is not None and t["forward_wr"] > 0]
print(f"With forward_wr populated: {len(with_fw)}")

dates = sorted([t.get("entry_date", t.get("timestamp", "")) for t in lb_trades])
if dates:
    print(f"Date range: {dates[0]} to {dates[-1]}")

symbols = set(t.get("symbol", "") for t in lb_trades)
print(f"Unique symbols: {len(symbols)}")

complete = [t for t in lb_trades if t.get("outcome") in ("WON", "LOST") and t.get("pnl_pct") is not None]
print(f"Complete records (outcome + pnl): {len(complete)}")

print(f"\nlb_None trade sample (first 5):")
for t in lb_trades[:5]:
    print(f"  {t.get('entry_date')} {t.get('symbol'):12s} {t.get('direction'):5s} pnl={t.get('pnl_pct'):+.4f} outcome={t.get('outcome', 'NONE')} fwd_wr={t.get('forward_wr')}")