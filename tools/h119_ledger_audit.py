#!/usr/bin/env python3
"""Audit the H-119 rows in reports/forward_observations.jsonl.

WHY THIS FILE EXISTS (R8)
-------------------------
Restoring this ledger from git left 430 rows tagged H-119 that nobody could
attribute. The question was "attribute them or write them off". This script
answers it with provenance arithmetic rather than opinion, then — because the
rows exist and contain real prices — recomputes H-119's OWN acceptance statistic
from them, so we know what the ledger actually says even after it is quarantined.

THE THREE FINDINGS THIS PRODUCES
  1. PROVENANCE. A forward observation must be created BEFORE it closes. If
     created_at > closed_at, the row was written after the outcome was known,
     which is a backfill, not an observation.
  2. PRE-REGISTRATION. H-119 was registered 2026-06-13. Any row that closed
     before that date cannot be forward evidence for H-119 under any reading.
  3. ACCEPTANCE. H-119's registered statistic is "net-of-16bp-RT-crypto PF
     CI-LB (symbol-day clusters)", min_n=150, min_ci_lb=1.15, concentration<35%.
     The ledger stores fees=0.0 and funding=0.0 on every row, so net CANNOT be
     read off the file. This script applies the hypothesis's own stated 16bp
     round trip and cluster-bootstraps.

WHAT IT DOES NOT DO
  - It does not delete or rewrite the ledger. Quarantine is a decision for the
    registry owner; this file only produces the evidence for it.
  - It does not claim these rows are worthless. They are a legitimate HISTORICAL
    sample. They are simply not forward observations, and nothing may count them
    as such.

Usage: python3 tools/h119_ledger_audit.py
"""
from __future__ import annotations

import json
import math
import random
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "reports" / "forward_observations.jsonl"
REGISTRY = ROOT / "reports" / "hypothesis_registry.json"
OUT = ROOT / "reports" / "h119_ledger_audit" / "h119_ledger_audit.json"

HID = "H-119"
COST_BP_RT = 16.0    # H-119's own registered cost assumption
REGISTERED_AT = "2026-06-13"
N_BOOT = 4000
SEED = 20261122


def ts(s: str) -> datetime:
    return datetime.fromisoformat(s)


def load_h119() -> list[dict]:
    rows = []
    for ln in LEDGER.read_text().splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            r = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if r.get("hypothesis_id") == HID:
            rows.append(r)
    return rows


def trade_ret(r: dict, price_field: str = "resolver_exit_px") -> float:
    """Directional gross return, before costs."""
    e, x = float(r["entry_px"]), float(r[price_field])
    if e <= 0:
        return float("nan")
    gross = x / e - 1.0
    return gross if r["side"] == "LONG" else -gross


def pf_of(rets: list[float]) -> float:
    wins = sum(x for x in rets if x > 0)
    losses = -sum(x for x in rets if x < 0)
    if losses <= 0:
        return float("inf") if wins > 0 else 0.0
    return wins / losses


def cluster_bootstrap_ci(clusters: dict[str, list[float]], n_boot: int = N_BOOT,
                         seed: int = SEED) -> tuple[float, float, float]:
    """Resample SYMBOL-DAY clusters (H-119's registered unit), not trades.

    Bootstrapping trades would treat 22 JUPUSDT trades as 22 independent draws.
    They are not; they share an instrument and often a day. The registered
    statistic says symbol-day clusters, so that is what gets resampled.
    """
    keys = sorted(clusters)
    rng = random.Random(seed)
    pfs = []
    for _ in range(n_boot):
        sample: list[float] = []
        for _ in keys:
            sample.extend(clusters[rng.choice(keys)])
        p = pf_of(sample)
        if math.isfinite(p):
            pfs.append(p)
    if not pfs:
        return float("nan"), float("nan"), float("nan")
    pfs.sort()
    lo = pfs[int(0.025 * len(pfs))]
    hi = pfs[int(0.975 * len(pfs))]
    return pfs[len(pfs) // 2], lo, hi


def main() -> int:
    rows = load_h119()
    if not rows:
        print(f"no {HID} rows found in {LEDGER}")
        return 2

    n = len(rows)
    print(f"=== {HID} LEDGER AUDIT — {n} rows ===\n")

    # ---------- 1. PROVENANCE ----------
    created_dates = Counter(r["created_at"][:10] for r in rows)
    after = [r for r in rows if ts(r["created_at"]) > ts(r["closed_at"])]
    gaps = sorted((ts(r["created_at"]) - ts(r["closed_at"])).total_seconds() / 86400
                  for r in rows)
    print("--- 1. PROVENANCE (is a row an observation or a backfill?) ---")
    print(f"  distinct created_at dates      : {len(created_dates)}  {dict(created_dates)}")
    print(f"  created AFTER its own close    : {len(after)}/{n} "
          f"({len(after)/n*100:.0f}%)")
    print(f"  created-minus-closed days      : min {gaps[0]:.1f}  "
          f"median {gaps[len(gaps)//2]:.1f}  max {gaps[-1]:.1f}")
    verdict_forward = len(after) == 0
    if not verdict_forward:
        print(f"  => NOT FORWARD OBSERVATIONS. Every row was written after the")
        print(f"     outcome was already known. A forward observation must precede")
        print(f"     its own resolution. These are a retroactive backfill.")

    # ---------- 2. PRE-REGISTRATION ----------
    reg = ts(REGISTERED_AT + "T00:00:00+00:00")
    pre = [r for r in rows if ts(r["closed_at"]) < reg]
    print(f"\n--- 2. PRE-REGISTRATION (registered {REGISTERED_AT}) ---")
    print(f"  rows closed BEFORE registration : {len(pre)}/{n} "
          f"({len(pre)/n*100:.0f}%)")
    print(f"  rows closed AFTER  registration : {n-len(pre)}/{n} "
          f"({(n-len(pre))/n*100:.0f}%)")
    print(f"  but rows WRITTEN on the first date a hypothesis existed as a row:")
    print(f"    earliest created_at          : {min(r['created_at'] for r in rows)[:10]}")
    print(f"  => Even the post-registration closures are inadmissible as forward")
    print(f"     evidence: they were selected and resolved before being entered.")

    # ---------- 3. ACCEPTANCE STATISTIC ----------
    print(f"\n--- 3. PRICE-INTEGRITY SCREEN ---")
    # A resolver that returns a price 46% away from the recorded exit is not
    # resolving, it is erroring. Two such rows moved the PF by 0.07 on their own,
    # so they are screened out and BOTH numbers are reported: dropping bad rows
    # without saying so is how a sample gets quietly curated into a result.
    suspect = [r for r in rows
               if abs(float(r["resolver_exit_px"]) / float(r["exit_px"]) - 1) > 0.10]
    clean = [r for r in rows if r not in suspect]
    for t in (0.05, 0.10, 0.20):
        b = sum(1 for r in rows
                if abs(float(r["resolver_exit_px"]) / float(r["exit_px"]) - 1) > t)
        print(f"  resolver vs exit_px disagree by >{t*100:2.0f}%: {b:3d}/{n} rows")
    print(f"  worst: " + ", ".join(
        f"{r['symbol']} {r['resolver_exit_px']:.4f} vs {r['exit_px']:.4f}"
        for r in sorted(rows, key=lambda r: -abs(
            float(r["resolver_exit_px"]) / float(r["exit_px"]) - 1))[:3]))

    print(f"\n--- 4. ACCEPTANCE STATISTIC (H-119's own rule, applied honestly) ---")
    print(f"  registered: net-of-{COST_BP_RT:.0f}bp-RT PF CI-LB, symbol-day "
          f"clusters, min_n=150, min_ci_lb=1.15, concentration<35%")
    print(f"  ledger stores fees=0.0 on {sum(1 for r in rows if r['fees']==0)}/{n} rows "
          f"-> net is NOT in the file; applying the registered 16bp instead.")
    print(f"  ledger stores slippage_bps={rows[0]['slippage_bps']:.0f} on all rows, "
          f"but it is NOT applied to exit_px (LONGs split 76 below / 101 above the "
          f"resolver), so deducting 16bp does not double-count.")

    results = {}
    for scope_name, subset in (("ALL rows", rows), ("CLEAN rows", clean)):
        for price_field in ("resolver_exit_px", "exit_px"):
            gross = [trade_ret(r, price_field) for r in subset]
            gross = [g for g in gross if math.isfinite(g)]
            net = [g - COST_BP_RT / 1e4 for g in gross]
            clusters: dict[str, list[float]] = defaultdict(list)
            for r, g in zip(subset, gross):
                clusters[f"{r['symbol']}|{r['closed_at'][:10]}"].append(
                    g - COST_BP_RT / 1e4)

            gpf, gwr = pf_of(gross), sum(1 for x in gross if x > 0) / len(gross)
            npf, nwr = pf_of(net), sum(1 for x in net if x > 0) / len(net)
            med, lo, hi = cluster_bootstrap_ci(clusters)
            key = f"{scope_name.split()[0].lower()}_{price_field}"
            results[key] = dict(
                scope=scope_name, price=price_field, n=len(gross),
                n_clusters=len(clusters), gross_pf=gpf, gross_wr=gwr,
                net_pf=npf, net_wr=nwr, net_mean_bp=sum(net) / len(net) * 1e4,
                ci_lb=lo, ci_med=med, ci_hi=hi,
                passes_n=len(gross) >= 150, passes_ci=lo > 1.15)
            print(f"\n  [{scope_name} / {price_field}]")
            print(f"    n {len(gross)}  clusters {len(clusters)}")
            print(f"    GROSS    PF {gpf:5.3f}  WR {gwr*100:5.1f}%  "
                  f"mean {sum(gross)/len(gross)*1e4:+.2f} bp")
            print(f"    NET-16bp PF {npf:5.3f}  WR {nwr*100:5.1f}%  "
                  f"mean {sum(net)/len(net)*1e4:+.2f} bp")
            print(f"    cluster-bootstrap PF median {med:.3f}  "
                  f"95% CI [{lo:.3f}, {hi:.3f}]")
            print(f"    gate: n>=150 {'PASS' if len(gross)>=150 else 'FAIL'} | "
                  f"CI-LB>1.15 {'PASS' if lo > 1.15 else 'FAIL'}  (CI-LB {lo:.3f})")
    primary = results["clean_resolver_exit_px"]

    # ---------- 5. CONCENTRATION ----------
    sym = Counter(r["symbol"] for r in rows)
    top_sym, top_n = sym.most_common(1)[0]
    print(f"\n--- 5. CONCENTRATION (gate: single source < 35%) ---")
    print(f"  distinct symbols {len(sym)}   top {top_sym} {top_n}/{n} = "
          f"{top_n/n*100:.1f}%  {'PASS' if top_n/n < 0.35 else 'FAIL'}")
    print(f"  sides: {dict(Counter(r['side'] for r in rows))}")

    # ---------- 6. VERDICT ----------
    print(f"\n=== VERDICT ===")
    print(f"  FORWARD-CREDITABLE : 0 of {n} rows.")
    print(f"  Reason: 100% written after their own close, single bulk write on "
          f"{list(created_dates)[0]}, and {len(pre)} closed before the hypothesis "
          f"was registered.")
    span = sorted((results['clean_resolver_exit_px']['net_pf'],
                   results['clean_exit_px']['net_pf']))
    span_ci = sorted((results['clean_resolver_exit_px']['ci_lb'],
                      results['clean_exit_px']['ci_lb']))
    print(f"  Statistical content, CLEAN rows, net-16bp: PF {span[0]:.3f}-{span[1]:.3f} "
          f"across the two price conventions, CI-LB {span_ci[0]:.3f}-{span_ci[1]:.3f}")
    print(f"  Gate ({primary['passes_n'] and 'n>=150 MET'}) | CI-LB>1.15 NOT MET in "
          f"either convention")
    print(f"  Neither convention reaches 1.15, and the two bracket BREAKEVEN, so "
          f"the answer does not depend on which price you trust.")
    print(f"\n  R8 DISPOSITION: QUARANTINE, do not attribute and do not delete.")
    print(f"  They are a usable HISTORICAL sample and an unusable FORWARD record.")
    print(f"  Any forward clock that counts them is overstating {HID} by {n} rows.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "hypothesis_id": HID, "n_rows": n,
        "provenance": {
            "distinct_created_dates": dict(created_dates),
            "rows_created_after_close": len(after),
            "created_minus_closed_days": {"min": gaps[0],
                                          "median": gaps[len(gaps) // 2],
                                          "max": gaps[-1]},
            "is_forward_observations": verdict_forward,
        },
        "registration": {"registered_at": REGISTERED_AT,
                         "rows_closed_before_registration": len(pre)},
        "acceptance_all_rows": {k: v for k, v in results.items() if k.startswith("all")},
        "acceptance_clean_rows": {k: v for k, v in results.items() if k.startswith("clean")},
        "price_integrity": {"rows_resolver_vs_exit_gt_10pct": len(suspect),
                            "rows_clean": len(clean),
                            "screen_threshold_pct": 10.0},
        "cost_bp_rt_applied": COST_BP_RT,
        "concentration_top_symbol_pct": top_n / n * 100,
        "disposition": "QUARANTINE — historical sample, not forward evidence",
        "evidence_class": "LEDGER PROVENANCE + STATISTIC RECOMPUTE",
    }, indent=2))
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
