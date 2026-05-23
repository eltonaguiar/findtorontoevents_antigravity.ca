#!/usr/bin/env python3
"""
Final targeted analysis: map edge_analysis cohorts to canonical data,
check direction naming, and attempt harness with relaxed thresholds.
"""
import json
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "alpha_engine"))
sys.path.insert(0, str(ROOT / "tools"))

from edge_stability_harness import _windows, _window_eff, _rdate, _won, _num, evaluate
from charter_slippage import deduct_slippage

# Load canonical picks
with open(ROOT / "alpha_engine" / "data" / "closed_picks.json") as f:
    raw = json.load(f)

with open(ROOT / "audit_dashboard" / "data" / "pf_registry.json") as f:
    registry = json.load(f)

# ============================================================
# Dedup + policy clean
# ============================================================
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

print(f"Canonical clean picks: {len(clean)}")
print()

# ============================================================
# 1. Check direction naming conventions
# ============================================================
print("=" * 70)
print("DIRECTION NAMING CONVENTIONS")
print("=" * 70)
for ac in ["COMMODITY", "CRYPTO", "EQUITY", "FOREX"]:
    subset = [p for p in clean if (p.get("asset_class") or "").upper() == ac]
    directions = defaultdict(int)
    for p in subset:
        d = p.get("direction", "NONE")
        directions[d] += 1
    print(f"  {ac}: {dict(directions)} (total={len(subset)})")

# ============================================================
# 2. Map the edge_analysis cohorts properly
# ============================================================
print(f"\n{'='*70}")
print("EDGE ANALYSIS COHORT MAPPING")
print("=" * 70)

# From edge_analysis_2026-05-17.md:
# CRYPTO: direction=LONG, strategies=7 families, n=372
#   But pf_registry CRYPTO total = 1949
#   The "7 families" refers to specific crypto strategy families

# Let's find all crypto strategies with LONG direction
crypto_long = [p for p in clean if (p.get("asset_class") or "").upper() == "CRYPTO" and p.get("direction") == "LONG"]
crypto_strats_long = defaultdict(int)
for p in crypto_long:
    s = p.get("strategy", "unknown")
    crypto_strats_long[s] += 1

print(f"\nCRYPTO LONG strategies ({len(crypto_long)} total picks):")
for s, n in sorted(crypto_strats_long.items(), key=lambda x: -x[1])[:20]:
    print(f"  {s}: {n}")

# COT COMMODITY (direction=SELL not SHORT?)
commodity_sell = [p for p in clean if (p.get("asset_class") or "").upper() == "COMMODITY" and p.get("direction") in ("SHORT", "SELL")]
commodity_strats = defaultdict(int)
for p in commodity_sell:
    s = p.get("strategy", "unknown")
    commodity_strats[s] += 1

print(f"\nCOMMODITY SHORT/SELL strategies ({len(commodity_sell)} total picks):")
for s, n in sorted(commodity_strats.items(), key=lambda x: -x[1]):
    print(f"  {s}: {n}")

# EQUITY with elite_score >= 60
equity_elite = [p for p in clean if (p.get("asset_class") or "").upper() == "EQUITY" and (p.get("elite_score") or 0) >= 60]
print(f"\nEQUITY elite>=60: {len(equity_elite)} picks")
for p in equity_elite[:5]:
    print(f"  {p.get('strategy')}: elite={p.get('elite_score')}, sym={p.get('symbol')}, date={p.get('entry_date')}")

# FOREX rsi-ema-scout
forex_rsi = [p for p in clean if (p.get("asset_class") or "").upper() == "FOREX"]
forex_strats = defaultdict(int)
for p in forex_rsi:
    s = p.get("strategy", "unknown")
    forex_strats[s] += 1

print(f"\nFOREX strategies ({len(forex_rsi)} total picks):")
for s, n in sorted(forex_strats.items(), key=lambda x: -x[1]):
    print(f"  {s}: {n}")

# ============================================================
# 3. Attempt is_admissible on best-available data
# ============================================================
print(f"\n{'='*70}")
print("HARNESS ATTEMPT: Best available per-asset-class data")
print("=" * 70)

# For each asset class, test all picks together to see if density is sufficient
for ac_name in ["CRYPTO", "EQUITY", "COMMODITY", "FOREX"]:
    subset = [p for p in clean if (p.get("asset_class") or "").upper() == ac_name]
    n = len(subset)

    print(f"\n  {ac_name} (n={n}):")

    if n < 100:
        print(f"    SKIP: Less than 100 picks total")
        continue

    # Try to bucket
    dated = [(p, _rdate(p)) for p in subset if _rdate(p)]
    if not dated:
        print(f"    SKIP: No dated picks")
        continue

    # Count windows with n>=80
    wins_80 = [w for w in _windows(subset, 14) if len(w) >= 80]
    wins_30 = [w for w in _windows(subset, 14) if len(w) >= 30]
    print(f"    Windows with n>=80: {len(wins_80)}")
    print(f"    Windows with n>=30: {len(wins_30)}")

    if len(wins_80) < 5:
        print(f"    SKIP: Not enough windows at n>=80 threshold (need >=5)")
        if len(wins_30) >= 5:
            print(f"    NOTE: Would have {len(wins_30)} windows at n>=30 (below harness min_window_n=80)")
        continue

    # Test confidence
    effs = []
    for i, w in enumerate(wins_80):
        e = _window_eff(w, "confidence")
        effs.append({"window": i, "n": len(w), "eff": e})

    scored = [r for r in effs if r["eff"] is not None]
    strong = [r for r in scored if abs(r["eff"]) >= 0.30]
    pos = [r for r in strong if r["eff"] > 0]
    neg = [r for r in strong if r["eff"] < 0]

    print(f"    [confidence] scored={len(scored)}, strong={len(strong)}, pos={len(pos)}, neg={len(neg)}")
    if len(strong) >= 3 and len(pos) == len(strong):
        print(f"    [confidence] WOULD PASS (all positive)")
    elif len(strong) >= 3 and len(neg) == len(strong):
        print(f"    [confidence] WOULD PASS (all negative)")
    elif len(strong) >= 3:
        print(f"    [confidence] WOULD FAIL (sign split)")
    else:
        print(f"    [confidence] INSUFFICIENT strong windows")

    # Try using evaluate() directly
    try:
        result = evaluate("confidence", window_days=14)
        print(f"    [confidence] evaluate() result: admissible={result.get('admissible')}, sign={result.get('sign')}, reason={result.get('reason', '')[:100]}")
    except Exception as e:
        print(f"    [confidence] evaluate() error: {e}")

    # Test elite_score if available
    has_elite = sum(1 for p in subset if _num(p.get("elite_score")) is not None)
    print(f"    elite_score available: {has_elite}/{n}")
    if has_elite >= 100:
        try:
            result = evaluate("elite_score", window_days=14)
            print(f"    [elite_score] evaluate() result: admissible={result.get('admissible')}, sign={result.get('sign')}, reason={result.get('reason', '')[:100]}")
        except Exception as e:
            print(f"    [elite_score] evaluate() error: {e}")

# ============================================================
# 4. The quan_engine strategies (ONLY high-density crypto)
# ============================================================
print(f"\n{'='*70}")
print("QUAN ENGINE STRATEGIES (only crypto with real density)")
print("=" * 70)

for strat_name in ["quan_engine_scalp", "quan_engine_swing", "quan_engine_position"]:
    subset = [p for p in clean if p.get("strategy", "") == strat_name]
    n = len(subset)
    if n == 0:
        continue

    wins = sum(1 for p in subset if (p.get("pnl_pct") or 0) > 0)
    wr = wins / n * 100
    print(f"  {strat_name}: n={n}, WR={wr:.1f}%")

    if n >= 100:
        try:
            result = evaluate("confidence", window_days=14)
            print(f"    confidence evaluate() result: admissible={result.get('admissible')}, sign={result.get('sign')}")
        except Exception as e:
            print(f"    confidence evaluate() error: {e}")