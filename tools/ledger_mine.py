#!/usr/bin/env python3
"""Mine the resolved-closed-picks ledger with leakage screening, cluster-robust
statistics, and source-level attribution.

One harness, four sections, so the four answers cannot drift apart by using
different filters. Every section applies the SAME canonical screen.

TODOS 31/33/34/35
  31 leakage audit      -- what in this ledger is structurally untrustworthy
  33 per-class robust   -- PF / expectancy with cluster bootstrap by symbol-day
  34 source attribution -- which emitters actually carry the P&L, BH-corrected
  35 verify 78.9%       -- is the disputed CRYPTO smart-picks claim reproducible

Discipline encoded here
  * net and gross always reported together; the ledger's own `won` flag is on
    GROSS (flat_epsilon 0.01%), so a "win" can be net-negative. We never use it.
  * every mean carries a cluster-robust CI (cluster = symbol|closed-day), not an
    iid one. Picks on the same symbol on the same day are not independent.
  * source attribution discloses n_trials = number of sources screened and
    applies Benjamini-Hochberg. 67 sources scanned for one winner is a search.
  * a number we cannot compute is reported as UNMEASURED, never estimated.

Read-only. No capital. Not investment advice.

Usage:
    python3 tools/ledger_mine.py
    python3 tools/ledger_mine.py --boot 4000 --out reports/ledger_mine
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
OUT = REPO / "reports/ledger_mine"

TRIALS_14D = REPO / "audit_dashboard/data/pick_summary_stats_14d.json"


# ---------------------------------------------------------------- utilities
def parse_dt(s):
    """Parse every closed_at shape the ledger actually emits.

    DEFECT FIXED 2026-11-22: the first version of this parser only accepted
    '%Y-%m-%d %H:%M:%S %Z', so it silently rejected 7,336/10,968 rows (67%) --
    the ISO-with-microseconds form '2026-11-22T10:57:17.123456+00:00' that
    dominates the file. The ledger-wide stats were then computed on the 33% of
    rows that happened to use a legacy format, which is a selection on the data
    generating process. Always print the rejection count next to the kept count
    so a silent 67% loss cannot hide again.
    """
    if not s:
        return None
    s = s.strip()
    # strip a trailing tz abbreviation -- fromisoformat cannot take 'EST'
    for suf in (" EST", " EDT", " UTC", " GMT"):
        if s.endswith(suf):
            s = s[: -len(suf)]
            break
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00") if "Z" in s else s)
        return dt.replace(tzinfo=None) if dt.tzinfo else dt
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M",
                "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def daykey(dt):
    return dt.strftime("%Y-%m-%d") if dt else "?"


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def sd(xs):
    if len(xs) < 2:
        return float("nan")
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def profit_factor(pnls):
    win = sum(p for p in pnls if p > 0)
    loss = -sum(p for p in pnls if p < 0)
    if loss <= 0:
        return float("inf") if win > 0 else float("nan")
    return win / loss


def cluster_bootstrap(pnls_by_cluster, stat_fn, n_boot, seed=20261122):
    """Resample CLUSTERS with replacement. Returns (lo, hi) 2.5/97.5 pct."""
    clusters = list(pnls_by_cluster.values())
    if len(clusters) < 5:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(clusters)
    out = []
    for _ in range(n_boot):
        flat = []
        for _ in range(k):
            flat.extend(clusters[rng.randrange(k)])
        v = stat_fn(flat)
        if v == v and abs(v) != float("inf"):
            out.append(v)
    if not out:
        return (float("nan"), float("nan"))
    out.sort()
    return (out[int(0.025 * len(out))], out[int(0.975 * len(out))])


def tstat(xs):
    n = len(xs)
    if n < 3:
        return float("nan")
    s = sd(xs)
    if s == 0 or s != s:
        return float("nan")
    return mean(xs) / (s / math.sqrt(n))


def norm_sf(z):
    """Upper tail of standard normal via erfc."""
    return 0.5 * math.erfc(z / math.sqrt(2))


def bh_adjust(pvals):
    """Benjamini-Hochberg q-values, order-preserving."""
    n = len(pvals)
    if n == 0:
        return []
    idx = sorted(range(n), key=lambda i: pvals[i])
    q = [1.0] * n
    prev = 1.0
    for rank in range(n, 0, -1):
        i = idx[rank - 1]
        val = pvals[i] * n / rank
        prev = min(prev, val)
        q[i] = min(1.0, prev)
    return q


def fmt(x, nd=2):
    if x is None:
        return "UNMEASURED"
    if isinstance(x, float):
        if x != x:
            return "n/a"
        if abs(x) == float("inf"):
            return "inf"
        return f"{x:,.{nd}f}"
    return str(x)


# ---------------------------------------------------------------- load + screen
def load_rows():
    d = json.loads(LEDGER.read_text())
    return d, d["rows"]


def screen(rows):
    """Canonical screen applied by EVERY section.

    Returns (kept, reject_counts). Rejections are all structural, not
    performance-based -- screening on P&L would be selection on the dependent
    variable, the exact defect tools/integrity_lint.py exists to catch.
    """
    reject = Counter()
    kept = []
    seen_keys = set()
    for r in rows:
        sym = (r.get("symbol") or "").strip().upper()
        if not sym:
            reject["no_symbol"] += 1
            continue
        try:
            net = float(r.get("pnl_net_pct"))
        except (TypeError, ValueError):
            reject["no_net_pnl"] += 1
            continue
        if net != net:
            reject["nan_net_pnl"] += 1
            continue
        try:
            ent = float(r.get("entry_price"))
        except (TypeError, ValueError):
            ent = 0.0
        if ent <= 0:
            reject["no_entry_price"] += 1
            continue
        jk = r.get("join_key") or r.get("id")
        if jk in seen_keys:
            reject["dup_join_key"] += 1
            continue
        seen_keys.add(jk)
        dt = parse_dt(r.get("closed_at"))
        if dt is None:
            reject["unparseable_closed_at"] += 1
            continue
        kept.append({
            "sym": sym,
            "cls": (r.get("asset_class") or "UNKNOWN").upper(),
            "src": r.get("source_system") or "unknown",
            "strat": r.get("strategy") or "unknown",
            "dir": (r.get("direction") or "?").upper(),
            "net": net,
            "gross": float(r.get("pnl_gross_pct") or 0.0),
            "cost": float(r.get("cost_bps") or 0.0),
            "dt": dt,
            "day": daykey(dt),
            "cluster": f"{sym}|{daykey(dt)}",
            "status": (r.get("status") or "").upper(),
            "exit": (r.get("exit_reason") or "").upper(),
            "won_flag": bool(r.get("won")),
        })
    return kept, reject


# ---------------------------------------------------------------- 31: leakage
def section_leakage(raw, kept, reject):
    print("\n" + "=" * 78)
    print("SECTION 31 -- LEDGER LEAKAGE AUDIT")
    print("=" * 78)
    findings = []

    print(f"raw rows              {len(raw):,}")
    print(f"kept after screen     {len(kept):,}")
    print(f"rejected              {len(raw) - len(kept):,}")
    for k, v in reject.most_common():
        print(f"    {k:<24} {v:,}")

    # L1 -- the won flag is defined on GROSS, so it overcounts wins.
    won_gross = sum(1 for r in kept if r["gross"] > 0.01)
    won_net = sum(1 for r in kept if r["net"] > 0)
    net_neg_but_won = sum(1 for r in kept if r["gross"] > 0.01 and r["net"] <= 0)
    print(f"\nL1  won-flag integrity (flag is gross-based, flat_eps 0.01%)")
    print(f"    WON on gross        {won_gross:,}  ({100*won_gross/len(kept):.2f}%)")
    print(f"    WON on net          {won_net:,}  ({100*won_net/len(kept):.2f}%)")
    print(f"    gross-win, net-loss {net_neg_but_won:,}"
          f"  ({100*net_neg_but_won/max(1,won_gross):.2f}% of gross wins)")
    if net_neg_but_won:
        findings.append(f"L1 {net_neg_but_won} rows are WON on gross but LOSS on net "
                        f"({100*net_neg_but_won/max(1,won_gross):.1f}% of gross wins). "
                        f"Any WR computed from the won flag overstates by this much.")

    # L2 -- status/exit-reason consistency.
    mism = Counter()
    for r in kept:
        st, ex = r["status"], r["exit"]
        if st == "WON" and ex in ("LOSS", "SL_HIT", "SL"):
            mism["WON_with_loss_exit"] += 1
        if st == "LOST" and ex in ("WIN", "TP_HIT", "TP"):
            mism["LOST_with_win_exit"] += 1
        if st == "WON" and r["net"] <= 0:
            mism["WON_net_negative"] += 1
        if st == "LOST" and r["net"] > 0:
            mism["LOST_net_positive"] += 1
    print(f"\nL2  status vs exit_reason / net consistency")
    if mism:
        for k, v in mism.most_common():
            print(f"    {k:<24} {v:,}  ({100*v/len(kept):.2f}%)")
        findings.append(f"L2 {sum(mism.values())} status-label conflicts "
                        f"({100*sum(mism.values())/len(kept):.2f}% of rows).")
    else:
        print("    none")

    # L3 -- concentration.
    print(f"\nL3  concentration")
    for field in ("src", "sym", "cls"):
        c = Counter(r[field] for r in kept)
        hhi = sum((v / len(kept)) ** 2 for v in c.values())
        top, topn = c.most_common(1)[0]
        print(f"    {field:<5} distinct={len(c):<5} top={top[:24]:<24} "
              f"{100*topn/len(kept):5.2f}%  HHI={hhi:.3f}")
        if topn / len(kept) > 0.25:
            findings.append(f"L3 {field} '{top}' is {100*topn/len(kept):.1f}% of the "
                            f"ledger; any ledger-wide stat is mostly that one emitter.")

    # L4 -- duplicate signal timestamps (same symbol+day, many rows).
    dup = Counter(r["cluster"] for r in kept)
    multi = {k: v for k, v in dup.items() if v > 2}
    excess = sum(v - 1 for v in multi.values())
    print(f"\nL4  duplicate signal-ts clusters (same symbol, same closed-day)")
    print(f"    clusters with >2 rows  {len(multi):,}")
    print(f"    redundant rows         {excess:,}  "
          f"({100*excess/len(kept):.2f}% of ledger)")
    if excess:
        findings.append(f"L4 {excess} rows are redundant re-emissions of the same "
                        f"symbol-day ({100*excess/len(kept):.1f}%). iid stats "
                        f"treat them as independent evidence; they are not.")

    # L5 -- extreme / suspicious P&L.
    big = [r for r in kept if abs(r["net"]) > 50]
    print(f"\nL5  extreme P&L (|net| > 50%)")
    print(f"    rows  {len(big):,}  ({100*len(big)/len(kept):.2f}%)")
    if big:
        for r in sorted(big, key=lambda z: abs(z["net"]), reverse=True)[:5]:
            print(f"      {r['sym']:<10} {r['src'][:20]:<20} net={r['net']:+.1f}%")
        findings.append(f"L5 {len(big)} rows move >50% net; verify against raw "
                        f"prints before any of them is counted as evidence.")

    # L6 -- cost coverage. A row with cost 0 was never charged.
    zero_cost = sum(1 for r in kept if r["cost"] == 0)
    print(f"\nL6  cost coverage")
    print(f"    rows with cost_bps == 0   {zero_cost:,}  "
          f"({100*zero_cost/len(kept):.2f}%)")
    if zero_cost:
        findings.append(f"L6 {zero_cost} rows carry zero cost; net==gross there, so "
                        f"the ledger's net is a mix of charged and uncharged rows.")

    # L7 -- time coverage.
    days = sorted({r["day"] for r in kept})
    print(f"\nL7  coverage")
    print(f"    closed_at span  {days[0]} .. {days[-1]}  ({len(days)} distinct days)")
    per_month = Counter(d[:7] for d in days)
    print(f"    months          {len(per_month)}")
    span_days = (parse_dt(days[-1]) - parse_dt(days[0])).days + 1
    print(f"    calendar days   {span_days}  "
          f"(ledger covers {100*len(days)/span_days:.1f}% of the span)")

    # L8 -- provenance UNMEASURED.
    print(f"\nL8  provenance (created_at vs closed_at)")
    print("    UNMEASURED -- this artifact ships no created_at field, so the "
          "provenance test\n    (created_at > closed_at) that tools/h119_ledger_audit.py "
          "applies CANNOT run here.\n    A row that was backfilled still looks "
          "identical to a pre-registered one.")

    return findings


# ---------------------------------------------------------------- 33: per class
def section_per_class(kept, n_boot):
    print("\n" + "=" * 78)
    print("SECTION 33 -- PER-CLASS CLUSTER-ROBUST PF AND EXPECTANCY")
    print("=" * 78)
    print("cluster = symbol|closed-day; %d bootstrap resamples; net of ledger cost\n"
          % n_boot)
    by = defaultdict(list)
    by_cluster = defaultdict(lambda: defaultdict(list))
    for r in kept:
        by[r["cls"]].append(r)
        by_cluster[r["cls"]][r["cluster"]].append(r["net"])

    header = (f"{'class':<12}{'n':>7}{'clust':>7}{'gross bp':>11}{'net bp':>10}"
              f"{'WR%':>7}{'PF':>7}{'PF CI-LB':>10}{'t':>7}  verdict")
    print(header)
    print("-" * len(header))
    out = {}
    for cls in sorted(by, key=lambda c: -len(by[c])):
        rows = by[cls]
        nets = [r["net"] * 100 for r in rows]
        gross = [r["gross"] * 100 for r in rows]
        wr = 100 * sum(1 for v in nets if v > 0) / len(nets)
        pf = profit_factor(nets)
        lo, hi = cluster_bootstrap(by_cluster[cls], profit_factor, n_boot)
        t = tstat(nets)
        if len(nets) < 30:
            verdict = "INSUFF-N"
        elif pf != pf or lo != lo:
            verdict = "UNMEASURED"
        elif lo > 1.0:
            verdict = "PF>1 (CI excludes 1)"
        elif pf > 1.0:
            verdict = "pf>1 but CI includes 1"
        else:
            verdict = "FAIL"
        print(f"{cls:<12}{len(nets):>7,}{len(by_cluster[cls]):>7,}"
              f"{mean(gross):>11.2f}{mean(nets):>10.2f}{wr:>7.2f}"
              f"{fmt(pf):>7}{fmt(lo):>10}{fmt(t):>7}  {verdict}")
        out[cls] = {"n": len(nets), "n_clusters": len(by_cluster[cls]),
                    "gross_bp": mean(gross), "net_bp": mean(nets),
                    "wr_pct": wr, "pf": pf, "pf_ci_lo": lo, "pf_ci_hi": hi,
                    "t": t, "verdict": verdict}

    # Portfolio view: equal-weight every closed pick = the honest aggregate.
    allnets = [r["net"] * 100 for r in kept]
    allclust = defaultdict(list)
    for r in kept:
        allclust[r["cluster"]].append(r["net"] * 100)
    lo, hi = cluster_bootstrap(allclust, profit_factor, n_boot)
    print("-" * len(header))
    print(f"{'ALL':<12}{len(allnets):>7,}{len(allclust):>7,}"
          f"{mean([r['gross']*100 for r in kept]):>11.2f}{mean(allnets):>10.2f}"
          f"{100*sum(1 for v in allnets if v>0)/len(allnets):>7.2f}"
          f"{fmt(profit_factor(allnets)):>7}{fmt(lo):>10}{fmt(tstat(allnets)):>7}")
    out["ALL"] = {"n": len(allnets), "net_bp": mean(allnets),
                  "pf": profit_factor(allnets), "pf_ci_lo": lo, "pf_ci_hi": hi,
                  "t": tstat(allnets)}
    return out


# ---------------------------------------------------------------- 34: sources
def section_sources(kept):
    print("\n" + "=" * 78)
    print("SECTION 34 -- SOURCE-LEVEL EXPECTANCY ATTRIBUTION")
    print("=" * 78)
    by = defaultdict(list)
    for r in kept:
        by[r["src"]].append(r["net"] * 100)

    tested = [(s, v) for s, v in by.items() if len(v) >= 30]
    n_trials = len(tested)
    print(f"sources in ledger          {len(by)}")
    print(f"sources with n >= 30       {n_trials}   <-- n_trials for BH correction")
    print("A source is only credible if it survives BH AND has a positive "
          "cluster-robust\nlower bound. Scanning 67 emitters for one winner is a "
          "search, not a discovery.\n")

    # DEFECT FIXED 2026-11-22: the first version computed q-values in `tested`
    # order and then attached them to rows AFTER sorting by net -- so every
    # q-value landed on the wrong source. It printed genetic_programmer
    # (p=0.2932) as "POSITIVE-SURVIVES-BH at q=0.0040" while ml_strategy_reviver
    # (p=0.0000) got q=1.0. Keep a stable key -> q mapping built BEFORE sorting.
    pvals, keyed = [], []
    for s, v in tested:
        t = tstat(v)
        p = norm_sf(t) if t == t else 1.0
        pvals.append(p)
        keyed.append((s, len(v), mean(v), t, p, profit_factor(v)))
    qs = bh_adjust(pvals)
    qmap = {keyed[i][0]: qs[i] for i in range(len(keyed))}
    assert len(qmap) == len(keyed)

    header = (f"{'source':<28}{'n':>7}{'net bp':>10}{'t':>7}{'p':>9}"
              f"{'q(BH)':>9}{'PF':>7}  flag")
    print(header)
    print("-" * len(header))
    rows = sorted(keyed, key=lambda z: -z[2])
    for s, n, m, t, p, pf in rows:
        flag = ""
        if qmap[s] < 0.05 and m > 0:
            flag = "POSITIVE-SURVIVES-BH"
        elif qmap[s] < 0.05 and m < 0:
            flag = "NEGATIVE-SURVIVES-BH"
        print(f"{s[:27]:<28}{n:>7,}{m:>10.2f}{fmt(t):>7}{p:>9.4f}"
              f"{qmap[s]:>9.4f}{fmt(pf):>7}  {flag}")

    netmap = {r[0]: r[2] for r in rows}
    n_pos_raw = sum(1 for r in rows if r[2] > 0)
    n_pos_bh = sum(1 for s, q in qmap.items() if q < 0.05 and netmap[s] > 0)
    print("-" * len(header))
    print(f"positive raw: {n_pos_raw}/{len(rows)}    "
          f"positive after BH: {n_pos_bh}/{len(rows)}")
    print(f"Expected positive-by-chance among {len(rows)} at alpha=.05: "
          f"{0.05*len(rows):.1f}")

    # Concentration of P&L: who supplies the total.
    tot = sum(sum(v) for v in by.values())
    contrib = sorted(((s, sum(v)) for s, v in by.items()),
                     key=lambda z: -abs(z[1]))[:8]
    print(f"\ntotal ledger net P&L = {tot:,.0f} bp-rows")
    print("largest absolute contributors:")
    for s, c in contrib:
        print(f"    {s[:30]:<32}{c:>12,.0f}  {100*c/tot if tot else 0:>7.1f}%")

    return {"n_trials": len(rows), "n_positive_raw": n_pos_raw,
            "n_positive_bh": n_pos_bh,
            "best": rows[0] if rows else None,
            "worst": rows[-1] if rows else None}


# ---------------------------------------------------------------- 35: 78.9%
def section_claim(kept):
    print("\n" + "=" * 78)
    print("SECTION 35 -- VERIFY THE DISPUTED 78.9% CRYPTO SMART-PICKS CLAIM")
    print("=" * 78)
    cr = [r for r in kept if r["cls"] == "CRYPTO"]
    nets = [r["net"] * 100 for r in cr]
    gross = [r["gross"] * 100 for r in cr]
    wr_net = 100 * sum(1 for v in nets if v > 0) / len(nets)
    wr_gross = 100 * sum(1 for v in gross if v > 0.01) / len(gross)
    print(f"CRYPTO rows in ledger      {len(cr):,}")
    print(f"WR on net                  {wr_net:.2f}%")
    print(f"WR on gross (ledger flag)  {wr_gross:.2f}%")
    print(f"mean net                   {mean(nets):+.2f} bp")
    print(f"PF net                     {fmt(profit_factor(nets))}")
    print(f"78.9% claim                 {'REPRODUCED' if abs(wr_gross-78.9)<2 or abs(wr_net-78.9)<2 else 'NOT REPRODUCED'}")

    # Which source could possibly produce 78.9%?
    by = defaultdict(list)
    for r in cr:
        by[r["src"]].append(r)
    print("\nsources able to produce a 78.9% figure (WR_gross desc, n>=20):")
    cand = []
    for s, v in by.items():
        if len(v) < 20:
            continue
        g = [r["gross"] * 100 for r in v]
        n = [r["net"] * 100 for r in v]
        cand.append((s, len(v), 100 * sum(1 for x in g if x > 0.01) / len(g),
                     100 * sum(1 for x in n if x > 0) / len(n),
                     mean(n), profit_factor(n)))
    cand.sort(key=lambda z: -z[2])
    hdr = f"    {'source':<26}{'n':>7}{'WRgr%':>8}{'WRnet%':>8}{'net bp':>10}{'PF':>7}"
    print(hdr)
    for s, n_, wg, wn, m, pf in cand[:10]:
        print(f"    {s[:25]:<26}{n_:>7,}{wg:>8.2f}{wn:>8.2f}{m:>10.2f}{fmt(pf):>7}")

    # The concentration the claim depends on.
    print("\nconcentration of the CRYPTO ledger:")
    cc = Counter(r["src"] for r in cr)
    for s, c in cc.most_common(5):
        print(f"    {s[:30]:<32}{c:>7,}  {100*c/len(cr):>5.1f}%")

    # 14d panel cross-check.
    if TRIALS_14D.exists():
        d = json.loads(TRIALS_14D.read_text())
        print("\n14d panel cross-check (audit_dashboard/data/pick_summary_stats_14d.json):")
        txt = json.dumps(d)[:0]
        def walk(o, path=""):
            if isinstance(o, dict):
                for k, v in o.items():
                    if isinstance(v, (dict, list)):
                        walk(v, f"{path}.{k}")
                    elif isinstance(v, (int, float)) and ("win" in k.lower() or "wr" in k.lower()):
                        print(f"    {path}.{k} = {v}")
            elif isinstance(o, list):
                for i, v in enumerate(o[:3]):
                    walk(v, f"{path}[{i}]")
        walk(d)
    return {"crypto_n": len(cr), "wr_net": wr_net, "wr_gross": wr_gross,
            "net_bp": mean(nets), "pf": profit_factor(nets)}


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if not LEDGER.exists():
        print(f"BLOCKED: ledger not found at {LEDGER}")
        return 2
    d, rows = load_rows()
    print(f"ledger    {LEDGER.relative_to(REPO)}")
    print(f"generated {d.get('generated_at')}")
    print(f"rows      {len(rows):,}")

    kept, reject = screen(rows)
    f31 = section_leakage(rows, kept, reject)
    r33 = section_per_class(kept, a.boot)
    r34 = section_sources(kept)
    r35 = section_claim(kept)

    print("\n" + "=" * 78)
    print("WHAT THIS SECTION ESTABLISHES")
    print("=" * 78)
    for f in f31:
        print(f"  * {f}")
    print(f"  * n_trials for source attribution = {r34['n_trials']}; "
          f"{r34['n_positive_raw']} positive raw -> "
          f"{r34['n_positive_bh']} positive after BH")

    payload = {"ledger": str(LEDGER.relative_to(REPO)),
               "generated_at": d.get("generated_at"),
               "n_raw": len(rows), "n_kept": len(kept),
               "rejections": dict(reject), "leakage_findings": f31,
               "per_class": r33, "sources": r34, "claim_789": r35}
    outdir = Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "ledger_mine.json").write_text(json.dumps(payload, indent=1, default=str))
    (outdir / "ledger_mine.md").write_text(render_md(payload))
    print(f"\nwrote {outdir/ 'ledger_mine.json'}")
    return 0


def render_md(p):
    L = []
    L.append("# Ledger mine -- leakage, per-class robustness, source attribution\n")
    L.append(f"- ledger: `{p['ledger']}` generated `{p['generated_at']}`")
    L.append(f"- rows: {p['n_raw']:,} raw -> {p['n_kept']:,} kept")
    L.append(f"- evidence class: **OBSERVED** (live resolved picks, net of ledger cost)")
    L.append("- n_trials: "
             f"{p['sources']['n_trials']} sources screened for one winner\n")
    L.append("## Leakage findings\n")
    for f in p["leakage_findings"]:
        L.append(f"- {f}")
    L.append("\n## Per-class (cluster-robust by symbol-day)\n")
    L.append("| class | n | clusters | gross bp | net bp | WR% | PF | PF CI-LB | t |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for k, v in p["per_class"].items():
        if k == "ALL":
            continue
        L.append(f"| {k} | {v['n']:,} | {v['n_clusters']:,} | {v['gross_bp']:.2f} | "
                 f"{v['net_bp']:.2f} | {v['wr_pct']:.2f} | {v['pf']:.3f} | "
                 f"{v['pf_ci_lo']:.3f} | {v['t']:.2f} |")
    a = p["per_class"]["ALL"]
    L.append(f"| **ALL** | {a['n']:,} | | | {a['net_bp']:.2f} | | {a['pf']:.3f} | "
             f"{a['pf_ci_lo']:.3f} | {a['t']:.2f} |")
    L.append("\n## Source attribution\n")
    L.append(f"- n_trials = {p['sources']['n_trials']}")
    L.append(f"- positive raw: {p['sources']['n_positive_raw']}, "
             f"positive after Benjamini-Hochberg: {p['sources']['n_positive_bh']}")
    L.append("\n## 78.9% CRYPTO claim\n")
    c = p["claim_789"]
    L.append(f"- CRYPTO n={c['crypto_n']:,}, WR net {c['wr_net']:.2f}%, "
             f"WR gross {c['wr_gross']:.2f}%, net {c['net_bp']:+.2f} bp, PF {c['pf']:.3f}")
    L.append("\n---\nNo capital deployed. Not investment advice. "
             "UNMEASURED means unmeasured, not zero.\n")
    return "\n".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
