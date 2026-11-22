#!/usr/bin/env python3
"""Try to destroy mega_mutation -- the only surviving source in the programme.

WHY
    tools/ledger_mine.py leaves exactly one emitter standing: mega_mutation,
    +135 bp/trade, n=105, 67 days, 55L/50S, split-half +83.6 -> +196.0 bp,
    best-day removal costs 8%. Before that gets any label above CANDIDATE it has
    to survive a null distribution, a cluster bootstrap, an out-of-sample clock,
    and a cost test on the instruments it actually trades.

    A +135 bp mean found by scanning 67 emitters is exactly the shape of a false
    positive. The question is not "is it large" but "is it larger than the
    largest thing chance would produce across 67 searches".

TESTS, IN ORDER OF HOW LIKELY THEY ARE TO KILL IT
  1. RANDOM-SOURCE NULL   Draw 67 random "sources" of the same size from the
                          ledger, record the BEST mean in each draw. The observed
                          result must beat that max-statistic distribution, not a
                          single-source one. This is the check the fleet is
                          documented as missing.
  2. CLUSTER BOOTSTRAP    Resample symbol-days, not rows.
  3. OUT-OF-SAMPLE CLOCK  Walk forward: at each month, a source only "exists" if
                          it has >=20 prior closed picks. Measure what you would
                          actually have earned, not what it earned in hindsight.
  4. COST FLOOR           mega_mutation trades AVAX/JUP/WIF/DOT -- wide-spread
                          alts. Compute the round-trip spread at which the edge
                          dies, and compare with a plausible alt-perp cost.

Read-only. No capital. Not investment advice.

Usage:
    python3 tools/mega_mutation_falsification.py --draws 4000
"""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LEDGER = REPO / "audit_dashboard/data/resolved_closed_picks_net.json"
OUT = REPO / "reports/mega_mutation"
TARGET = "mega_mutation"
MIN_N = 30


def pdt(s):
    if not s:
        return None
    s = str(s).strip().replace("Z", "+00:00")
    for suf in (" EST", " EDT", " UTC", " GMT"):
        if s.endswith(suf):
            s = s[: -len(suf)]
            break
    try:
        dt = datetime.fromisoformat(s)
        return dt.replace(tzinfo=None) if dt.tzinfo else dt
    except ValueError:
        return None


def mean(x):
    return sum(x) / len(x) if x else float("nan")


def sd(x):
    if len(x) < 2:
        return float("nan")
    m = mean(x)
    return math.sqrt(sum((v - m) ** 2 for v in x) / (len(x) - 1))


def tstat(x):
    s = sd(x)
    return mean(x) / (s / math.sqrt(len(x))) if s and s == s else float("nan")


def load():
    d = json.loads(LEDGER.read_text())
    rows = []
    for r in d["rows"]:
        dt = pdt(r.get("closed_at"))
        try:
            net = float(r["pnl_net_pct"]) * 100
        except (TypeError, ValueError):
            continue
        if dt is None:
            continue
        rows.append({
            "src": r.get("source_system") or "unknown",
            "net": net,
            "sym": (r.get("symbol") or "?"),
            "day": dt.strftime("%Y-%m-%d"),
            "month": dt.strftime("%Y-%m"),
            "dt": dt,
            "side": (r.get("direction") or "?").upper(),
            "_entry": r.get("entry_price"),
            "exit": (r.get("exit_reason") or "").upper(),
            "cluster": f"{r.get('symbol')}|{dt:%Y-%m-%d}",
        })
    return d, rows


def wilson(k, n, z=1.96):
    if not n:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=4000)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()

    d, rows = load()
    print("=" * 78)
    print(f"FALSIFICATION -- {TARGET}")
    print("=" * 78)
    tgt = [r for r in rows if r["src"] == TARGET]
    if len(tgt) < 20:
        print(f"BLOCKED: only {len(tgt)} rows for {TARGET}.")
        return 3
    nets = [r["net"] for r in tgt]
    print(f"ledger {len(rows):,} rows | {TARGET}: n={len(nets)}, "
          f"mean {mean(nets):+.2f} bp, median "
          f"{sorted(nets)[len(nets)//2]:+.2f} bp")
    print(f"days {len({r['day'] for r in tgt})}  symbols "
          f"{len({r['sym'] for r in tgt})}  "
          f"window {min(r['day'] for r in tgt)}..{max(r['day'] for r in tgt)}")

    # ---------------------------------------------------------------- 0
    print("\n0. WHAT IT ACTUALLY TRADES (the cost question lives here)")
    sc = Counter(r["sym"] for r in tgt).most_common(8)
    print(f"   {'symbol':<12}{'n':>5}{'mean bp':>10}")
    for s, k in sc:
        v = [r["net"] for r in tgt if r["sym"] == s]
        print(f"   {s:<12}{k:>5}{mean(v):>10.2f}")
    print(f"   sides: {dict(Counter(r['side'] for r in tgt))}")
    print(f"   exits: {dict(Counter(r['exit'] for r in tgt).most_common(5))}")

    # ---------------------------------------------------------------- 1
    print("\n1. RANDOM-SOURCE NULL -- max-statistic across the same search size")
    bysrc = defaultdict(list)
    for r in rows:
        bysrc[r["src"]].append(r["net"])
    big = {s: v for s, v in bysrc.items() if len(v) >= MIN_N}
    print(f"   sources with n>={MIN_N}: {len(big)}  (this is the search size)")
    rng = random.Random(20261122)
    allnets = [r["net"] for r in rows]
    n_t = len(nets)
    maxes = []
    for _ in range(a.draws):
        best = -1e9
        for _ in range(len(big)):
            s = rng.sample(allnets, n_t)
            m = mean(s)
            if m > best:
                best = m
        maxes.append(best)
    maxes.sort()
    obs = mean(nets)
    p_max = sum(1 for m in maxes if m >= obs) / len(maxes)
    def q(p):
        return maxes[min(len(maxes) - 1, int(p * (len(maxes) - 1)))]
    print(f"   observed best mean        {obs:+.2f} bp")
    print(f"   null max-of-{len(big)} median  {q(0.50):+.2f} bp")
    print(f"   null max-of-{len(big)} p95     {q(0.95):+.2f} bp")
    print(f"   null max-of-{len(big)} p99     {q(0.99):+.2f} bp")
    print(f"   P(best of {len(big)} random sources >= observed) = {p_max:.4f}")
    survives_null = p_max < 0.05
    print(f"   -> {'SURVIVES' if survives_null else 'FAILS'} the max-statistic null")

    # ---------------------------------------------------------------- 2
    print("\n2. CLUSTER BOOTSTRAP (resample symbol-days)")
    byc = defaultdict(list)
    for r in tgt:
        byc[r["cluster"]].append(r["net"])
    cl = list(byc.values())
    boot = []
    rng2 = random.Random(20261122)
    for _ in range(a.draws):
        f = []
        for _ in range(len(cl)):
            f.extend(cl[rng2.randrange(len(cl))])
        boot.append(mean(f))
    boot.sort()
    lo, hi = boot[int(0.025 * len(boot))], boot[int(0.975 * len(boot))]
    print(f"   clusters {len(cl)}   boot mean 95% CI [{lo:+.2f}, {hi:+.2f}] bp")
    print(f"   -> CI {'excludes' if lo > 0 else 'INCLUDES'} zero")
    ci_ok = lo > 0

    # ---------------------------------------------------------------- 3
    print("\n3. OUT-OF-SAMPLE CLOCK -- only picks you could have taken")
    print("   rule: a source qualifies for month M only if it had >=20 closed")
    print("   picks BEFORE M. Then measure month M's realised mean.")
    months = sorted({r["month"] for r in rows})
    oos = []
    for m in months:
        prior = [r["net"] for r in tgt if r["month"] < m]
        cur = [r["net"] for r in tgt if r["month"] == m]
        if len(prior) >= 20 and cur:
            oos.extend(cur)
    if oos:
        print(f"   eligible months' picks n={len(oos)}   mean {mean(oos):+.2f} bp")
        print(f"   vs full-sample mean {mean(nets):+.2f} bp")
        loh, hih = wilson(sum(1 for v in oos if v > 0), len(oos))
        print(f"   OOS WR {100*sum(1 for v in oos if v>0)/len(oos):.2f}% "
              f"[{100*loh:.1f},{100*hih:.1f}]")
    else:
        print("   BLOCKED: never accumulates 20 prior picks before a month with")
        print("   its own activity. The edge is therefore NOT reachable in")
        print("   real time -- every pick is inside the window used to find it.")

    # ---------------------------------------------------------------- 4
    print("\n4. COST FLOOR -- at what round-trip spread does the edge die?")
    print(f"   gross mean {obs:+.2f} bp/trade")
    be = obs
    print(f"   breakeven round-trip cost = {be:.2f} bp of notional")
    print("   reference round-trip costs (from this programme's own measurements):")
    print("     BTC/ETH/SOL perp, $25k/leg     ~42 bp  (tools/carry_execution_cost)")
    print("     majors at VIP0 taker, 2 fills  10 bp  (fee only, no spread)")
    print("     wide alt perps                 UNMEASURED")
    if be < 42:
        print(f"   -> a 42 bp round trip EXCEEDS breakeven by {42-be:.1f} bp, so on")
        print("      the instruments this programme has actually measured, the")
        print("      edge is consumed by cost.")
    else:
        print(f"   -> breakeven {be:.0f} bp is wide enough to survive a 42 bp RT.")

    # ---------------------------------------------------------------- 5
    print("\n5. CONCENTRATION -- is it a few days doing all the work?")
    byday = defaultdict(list)
    for r in tgt:
        byday[r["day"]].append(r["net"])
    dm = sorted(((k, mean(v), len(v)) for k, v in byday.items()),
                key=lambda z: -z[1])
    tot = sum(nets)
    top3 = sum(m * k for _, m, k in dm[:3])
    print(f"   total {tot:,.0f} bp over {len(dm)} days")
    print(f"   best 3 days contribute {100*top3/tot if tot else 0:.0f}% of it")
    for k, m, n in dm[:3]:
        print(f"     {k}  n={n:<3} mean {m:+.1f} bp")
    pos_days = sum(1 for _, m, _ in dm if m > 0)
    print(f"   positive days {pos_days}/{len(dm)} ({100*pos_days/len(dm):.0f}%)")

    # ---------------------------------------------------------------- 6
    print("\n6. MEAN vs MEDIAN -- is the point estimate carrying the result?")
    srt = sorted(nets)
    med_obs = srt[len(srt) // 2]
    rng3 = random.Random(7)
    meds = []
    for _ in range(a.draws):
        smp = [nets[rng3.randrange(n_t)] for _ in range(n_t)]
        meds.append(sorted(smp)[len(smp) // 2])
    meds.sort()
    mlo, mhi = meds[int(0.025 * len(meds))], meds[int(0.975 * len(meds))]
    print(f"   mean {obs:+.2f} bp   median {med_obs:+.2f} bp   sd {sd(nets):.2f}")
    print(f"   median 95% CI [{mlo:+.2f}, {mhi:+.2f}] bp")
    med_ok = mlo > 0
    print(f"   -> median CI {'excludes' if med_ok else 'INCLUDES'} zero")

    # ---------------------------------------------------------------- 7
    print("\n7. DUPLICATE RE-EMISSIONS -- same symbol+side+entry, different days")
    seen = defaultdict(list)
    for r in tgt:
        key = (r["sym"], r["side"], round(float(r.get("_entry") or 0), 8))
        seen[key].append(r["day"])
    dups = {k: v for k, v in seen.items() if len(v) > 1}
    dup_rows = sum(len(v) for v in dups.values())
    print(f"   duplicate groups {len(dups)}  rows involved {dup_rows}/{n_t}")
    for k, v in list(dups.items())[:4]:
        print(f"     {k[0]} {k[1]} entry {k[2]} on {sorted(v)}")
    no_dup = dup_rows == 0
    print(f"   -> {'clean' if no_dup else 'CONTAINS re-emissions that inflate n and mean'}")

    # ---------------------------------------------------------------- 8
    print("\n8. TP-FIRST RATE vs A DRIFTLESS RANDOM WALK")
    tps = [r for r in tgt if r["exit"] == "TP_HIT"]
    sls = [r for r in tgt if r["exit"] == "SL_HIT"]
    decided = len(tps) + len(sls)
    if decided >= 20:
        # implied TP / SL distances from the realised moves
        tp_mv = mean([abs(r["net"]) for r in tps]) if tps else float("nan")
        sl_mv = mean([abs(r["net"]) for r in sls]) if sls else float("nan")
        p_rw = sl_mv / (tp_mv + sl_mv) if tp_mv and sl_mv else float("nan")
        p_obs = len(tps) / decided
        # binomial tail P(X >= observed | n=decided, p=p_rw)
        tail = 0.0
        for k in range(len(tps), decided + 1):
            tail += math.comb(decided, k) * p_rw ** k * (1 - p_rw) ** (decided - k)
        print(f"   decided trades (TP or SL only)   {decided}")
        print(f"   mean |move| on TP {tp_mv:.0f} bp, on SL {sl_mv:.0f} bp")
        print(f"   random-walk P(TP first)          {100*p_rw:.1f}%")
        print(f"   observed TP-first rate           {100*p_obs:.1f}%")
        print(f"   binomial P(>= {len(tps)} of {decided} at p={p_rw:.3f}) = {tail:.2e}")
        print(f"   -> {100*p_obs:.0f}% vs {100*p_rw:.0f}% expected. This is EITHER")
        print(f"      genuine directional skill OR TP/SL placed with hindsight. This")
        print(f"      ledger has no created_at, so it CANNOT distinguish the two.")
        tp_flag = p_obs < p_rw + 0.10
    else:
        tp_flag = True
        print("   INSUFFICIENT decided trades")

    # ---------------------------------------------------------------- verdict
    print("\n" + "=" * 78)
    print("VERDICT")
    print("=" * 78)
    # The gate is deliberately conjunctive and includes the tests that can FAIL
    # for reasons other than "the number is small".
    tests = {"max-statistic null": survives_null,
             "cluster CI > 0 (mean)": ci_ok,
             "median CI > 0": med_ok,
             "no duplicate re-emissions": no_dup,
             "OOS reachable": bool(oos),
             "breakeven > measured cost": be >= 42}
    for k, v in tests.items():
        print(f"   {'PASS' if v else 'FAIL'}  {k}")
    npass = sum(tests.values())
    failed = [k for k, v in tests.items() if not v]
    if npass == len(tests):
        print(f"\n   {npass}/{len(tests)} -- holds. Still CANDIDATE, not an edge:")
        print("   no forward clock, and the instruments' real spread is unmeasured.")
    else:
        print(f"\n   {npass}/{len(tests)} -- DOES NOT HOLD.")
        print(f"   failed: {failed}")
        print("\n   QUARANTINE, not CANDIDATE. The mean-based tests passing does")
        print("   not rescue a result whose own point estimates disagree.")
    print("\n   INDEPENDENT OF ALL OF THE ABOVE: provenance is UNMEASURED for this")
    print("   artifact (no created_at), so even a full pass could only ever reach")
    print("   CANDIDATE. Rows backfilled after the outcome are indistinguishable")
    print("   from pre-registered ones here.")

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "falsification.json").write_text(json.dumps({
        "target": TARGET, "n": len(nets), "mean_bp": obs, "median_bp": med_obs,
        "max_stat_p": p_max, "null_p95": q(0.95), "cluster_ci": [lo, hi],
        "median_ci": [mlo, mhi], "duplicate_groups": len(dups),
        "duplicate_rows": dup_rows,
        "oos_n": len(oos), "oos_mean_bp": mean(oos) if oos else None,
        "breakeven_rt_bp": be, "tests": tests, "n_tests_passed": npass,
        "failed": failed,
    }, indent=1))
    print(f"\nwrote {out/'falsification.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
