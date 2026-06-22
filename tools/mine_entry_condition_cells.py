#!/usr/bin/env python3
"""Systematic honest sub-condition edge-miner (READ-ONLY, EXPLORATORY).

Why
---
crypto_rsi5070_us (net PF ~1.34) is a winning *sub-condition* inside a *losing* class
(CRYPTO overall intrabar PF ~0.79). That pattern — a profitable pocket hidden in a
class baseline — is exactly what we want to find more of. Instead of hand-guessing one
predicate at a time (variant-fishing), enumerate ALL cells at once and FDR-correct.

Pre-registration (M-107)
------------------------
Family = every (class x RSI-band x session x direction) cell over the honest intrabar
cohort with n >= MIN_N, plus the coarser (class x dir x RSI) and (class x dir x session)
roll-ups. Ranked by net_PF. Benjamini-Hochberg FDR at q=0.10 on the per-cell two-sided
binomial p (realized WR vs 0.5). Hypothesis: at least one cell beyond crypto_rsi5070_us
shows a real net edge worth FORWARD pre-registration.

Discipline
----------
- Output is EXPLORATORY: candidates for forward pre-registration, NEVER for sizing.
- Cells at different granularities OVERLAP (same picks counted in roll-ups) -> FDR here is
  a screening heuristic, not a clean independent test. A surfaced cell must still pass a
  fresh single-hypothesis forward gate (n>=80 fwd, net-PF CI-LB>1.15, time-split, conc<35%).
- Reuses fetch_cohort/fetch_bars/features/stats from stamp_entry_conditions.py verbatim
  (the validated honest-intrabar code) — no re-implementation of resolution or features.
"""
from __future__ import annotations
import sys, os, json, math, datetime as dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.stamp_entry_conditions import fetch_cohort, fetch_bars, features, stats  # noqa: E402

MIN_N = 30
Q = 0.10


def _norm_dir(p: dict) -> str:
    return "LONG" if str(p.get("direction", "")).upper() in ("LONG", "BUY") else "SHORT"


def build_stamped(limit: int = 4000):
    cohort = fetch_cohort(limit)
    by_table = {"crypto_ohlcv": {}, "stock_ohlcv": {}}
    for p in cohort:
        p["_cls"] = (p["asset_class"] or "UNKNOWN").upper()
        is_crypto = p["_cls"] in ("CRYPTO", "MEMECOIN")
        tbl = "crypto_ohlcv" if is_crypto else "stock_ohlcv"
        cands = [p["symbol"]]
        if is_crypto:
            alt = p["symbol"].upper().replace("-", "").replace("/", "")
            if alt.endswith("USD") and not alt.endswith("USDT"):
                alt += "T"
            if alt != p["symbol"]:
                cands.append(alt)
        p["_barsyms"] = cands
        entry_ms = int(p["opened_at"].replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
        for s in cands:
            lo, hi = by_table[tbl].get(s, (entry_ms, entry_ms))
            by_table[tbl][s] = (min(lo, entry_ms), max(hi, entry_ms))
    bars = fetch_bars(by_table)
    skips: dict[str, int] = {}
    stamped = []
    for p in cohort:
        sym_bars = next((bars[s] for s in p["_barsyms"] if bars.get(s)), [])
        f = features(p, sym_bars, skips)
        if f is not None:
            stamped.append((p, f))
    return cohort, stamped, skips


def binom_p_two_sided(wins: int, n: int, p0: float = 0.5) -> float:
    if n == 0:
        return 1.0
    mu = p0 * n
    sd = math.sqrt(n * p0 * (1 - p0))
    if sd == 0:
        return 1.0
    z = abs(wins - mu) / sd
    return max(0.0, min(1.0, 2 * (1 - 0.5 * (1 + math.erf(z / math.sqrt(2))))))


def main() -> int:
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 4000
    cohort, stamped, skips = build_stamped(limit)

    cells: dict[str, list] = {}
    for p, f in stamped:
        cls, F3, F5, d = p["_cls"], f["F3"], f["F5"], _norm_dir(p)
        for k in (f"{cls}|{d}|RSI{F3}|{F5}", f"{cls}|{d}|RSI{F3}", f"{cls}|{d}|{F5}"):
            cells.setdefault(k, []).append(p)

    results = []
    for k, rows in cells.items():
        if len(rows) < MIN_N:
            continue
        s = stats(rows)
        n = s["n"]
        wr = s["wr"] or 0.0
        wins = int(round(wr / 100.0 * n))
        results.append({
            "cell": k, "n": n, "wr": wr, "pf": s["pf"], "net_pf": s.get("net_pf"),
            "avg_pnl": s.get("avg_pnl"), "p": binom_p_two_sided(wins, n),
        })

    # Benjamini-Hochberg
    results.sort(key=lambda r: r["p"])
    m = len(results)
    max_k = 0
    for i, r in enumerate(results, 1):
        r["bh_thresh"] = round(i / m * Q, 5) if m else 1.0
        if r["p"] <= r["bh_thresh"]:
            max_k = i
    for i, r in enumerate(results, 1):
        r["fdr_pass"] = i <= max_k

    winners = [r for r in results if (r["net_pf"] or 0) >= 1.5 and r["fdr_pass"] and r["n"] >= MIN_N]
    winners.sort(key=lambda r: (-(r["net_pf"] or 0), -r["n"]))

    print(f"cohort={len(cohort)} stamped={len(stamped)} cells_tested={m} bh_rejected={max_k} skips={skips}", file=sys.stderr)
    print(f"\n=== TOP CELLS by net_PF (n>={MIN_N}); FDR q={Q} two-sided binomial vs 0.5 ===", file=sys.stderr)
    hdr = f"{'cell':<30}{'n':>5}{'WR%':>7}{'PF':>7}{'netPF':>7}{'binom_p':>9}{'FDR':>5}"
    print(hdr, file=sys.stderr)
    print("-" * len(hdr), file=sys.stderr)
    for r in sorted(results, key=lambda x: -(x["net_pf"] or 0))[:25]:
        print(f"{r['cell']:<30}{r['n']:>5}{r['wr']:>7}{str(r['pf']):>7}{str(r['net_pf']):>7}"
              f"{r['p']:>9.4f}{'YES' if r['fdr_pass'] else '·':>5}", file=sys.stderr)

    doc = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "read_only": True, "exploratory": True, "min_n": MIN_N, "fdr_q": Q,
        "preregistration": "all (class x dir x RSI-band x session) cells + roll-ups; BH-FDR; "
                           "hypothesis: a cell beyond crypto_rsi5070_us has a real net edge",
        "caveat": "overlapping cells -> FDR is a screen; survivors need a fresh forward gate "
                  "(n>=80 fwd, net-PF CI-LB>1.15, time-split, concentration<35%)",
        "cohort_n": len(cohort), "stamped_n": len(stamped),
        "cells_tested": m, "bh_rejected": max_k,
        "fdr_passing_net_pf_ge_1_5": winners,
        "all_cells_ranked": sorted(results, key=lambda x: -(x["net_pf"] or 0)),
    }
    print(json.dumps(doc, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
