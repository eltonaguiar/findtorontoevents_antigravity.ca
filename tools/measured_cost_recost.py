#!/usr/bin/env python3
"""Re-cost the per-class ledger using MEASURED costs where they exist.

The ledger's own cost model is an assumption, not a measurement:

    class_cost_bps = {BOND 5.0, COMMODITY 15.0, CRYPTO 9.97, EQUITY 5.0,
                      ETF 5.0, FOREX 2.0, FUTURES 15.0, MUTUAL_FUND 8.0}

This programme has since MEASURED round-trip cost for two of those classes, and in
both cases the assumption is too low:

    FOREX   2.00 bp assumed   vs  7.53 bp measured round trip
            (subq-savant, live Tiingo top-of-book at the Sunday reopen, 48 polls,
             six USD majors; explicitly an UPPER BOUND on a thin book)
    CRYPTO  9.97 bp assumed   vs ~12.6 bp implied
            (tools/carry_execution_cost.py: 42.64 bp round trip for a 4-leg,
             2-venue carry position = ~10.7 bp per leg-side fee+slip; a single
             venue round trip is 2 fills -> fee 10 bp + measured slippage 2.6 bp)

A cost model that under-charges makes every loss look smaller than it is. This
recomputes per-class expectancy at measured cost and reports whether ANY verdict
changes. It will almost certainly not change any -- every class already fails --
but the size of the error is worth knowing, and an assumption left unexamined is
how the programme got into trouble before.

Read-only. No capital. Not investment advice.

Usage:
    python3 tools/measured_cost_recost.py
"""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LEDGER = REPO / "audit_dashboard/data/resolved_closed_picks_net.json"
OUT = REPO / "reports/measured_cost_recost"

# Assumed (what the ledger charges)
ASSUMED = {"BOND": 5.0, "COMMODITY": 15.0, "CRYPTO": 9.97, "EQUITY": 5.0,
           "ETF": 5.0, "FOREX": 2.0, "FUTURES": 15.0}

# Measured, with provenance. No value is entered without a source.
MEASURED = {
    "FOREX": (7.53, "subq-savant live Tiingo top-of-book, 6 USD majors, "
                     "Sunday reopen, UPPER BOUND on a thin book"),
    "CRYPTO": (12.60, "carry_execution_cost.py: 10bp fee/side + 2.6bp measured "
                      "slippage, single-venue round trip"),
}
UNMEASURED = {"BOND", "COMMODITY", "EQUITY", "ETF", "FUTURES"}


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


def pf(xs):
    w = sum(v for v in xs if v > 0)
    l = -sum(v for v in xs if v < 0)
    return (w / l) if l > 0 else (float("inf") if w > 0 else float("nan"))


def load_dedup():
    d = json.loads(LEDGER.read_text())
    seen, rows = set(), []
    for r in d["rows"]:
        dt = pdt(r.get("closed_at"))
        try:
            net = float(r["pnl_net_pct"]) * 100
            ent = float(r.get("entry_price"))
        except (TypeError, ValueError):
            continue
        if dt is None or ent <= 0:
            continue
        key = (r.get("source_system"), (r.get("symbol") or "").upper(),
               (r.get("direction") or "").upper(), round(ent, 8))
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "cls": (r.get("asset_class") or "?").upper(),
            "net": net,
            "gross": float(r.get("pnl_gross_pct") or 0.0) * 100,
            "charged": float(r.get("cost_bps") or 0.0),
            "cluster": f"{r.get('symbol')}|{dt:%Y-%m-%d}",
        })
    return rows


def cboot(byc, fn, draws, seed=20261122):
    cl = list(byc.values())
    if len(cl) < 5:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    out = []
    for _ in range(draws):
        f = []
        for _ in range(len(cl)):
            f.extend(cl[rng.randrange(len(cl))])
        v = fn(f)
        if v == v and abs(v) != float("inf"):
            out.append(v)
    if not out:
        return (float("nan"), float("nan"))
    out.sort()
    return out[int(0.025 * len(out))], out[int(0.975 * len(out))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=1500)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()

    print("=" * 78)
    print("RE-COST AT MEASURED COST -- does any verdict change?")
    print("=" * 78)
    rows = load_dedup()
    print(f"ledger rows after dedup: {len(rows):,}")

    print("\nCOST MODEL, assumed vs measured")
    print(f"    {'class':<11}{'assumed':>9}{'measured':>10}{'delta':>8}  provenance")
    for cls in sorted(ASSUMED):
        if cls in MEASURED:
            m, src = MEASURED[cls]
            print(f"    {cls:<11}{ASSUMED[cls]:>9.2f}{m:>10.2f}"
                  f"{m-ASSUMED[cls]:>+8.2f}  {src[:52]}")
        else:
            print(f"    {cls:<11}{ASSUMED[cls]:>9.2f}{'UNMEASURED':>10}"
                  f"{'—':>8}  no measurement exists in this programme")

    by = defaultdict(list)
    for r in rows:
        by[r["cls"]].append(r)

    print(f"\nPER-CLASS: gross is IDENTICAL in both columns -- only the cost changes")
    hdr = (f"    {'class':<11}{'n':>7}{'gross bp':>10}{'net@assumed':>13}"
           f"{'net@measured':>14}{'delta':>9}{'PF meas':>9}{'PF LB':>8}  verdict")
    print(hdr)
    print("    " + "-" * (len(hdr) - 4))
    results = {}
    for cls in sorted(by, key=lambda c: -len(by[c])):
        v = by[cls]
        if len(v) < 10:
            continue
        gross = mean([r["gross"] for r in v])
        # the ledger charged `charged` per row; recompute at measured or assumed
        target = MEASURED[cls][0] if cls in MEASURED else ASSUMED.get(cls, 10.0)
        # net_at_measured = gross - measured_cost ; rows carry the charged cost
        nets_m = [r["gross"] - target for r in v]
        # keep the ledger's own net for the "assumed" column
        nets_a = [r["net"] for r in v]
        byc = defaultdict(list)
        for r, nm in zip(v, nets_m):
            byc[r["cluster"]].append(nm)
        lo, hi = cboot(byc, pf, a.draws)
        pfm = pf(nets_m)
        if len(v) < 30:
            verdict = "INSUFF-N"
        elif lo == lo and lo > 1.0:
            verdict = "PF>1 (CI excl 1)"
        elif pfm > 1.0:
            verdict = "pf>1 but CI incl 1"
        else:
            verdict = "FAIL"
        print(f"    {cls:<11}{len(v):>7,}{gross:>10.2f}{mean(nets_a):>13.2f}"
              f"{mean(nets_m):>14.2f}{mean(nets_m)-mean(nets_a):>+9.2f}"
              f"{pfm:>9.3f}{lo:>8.3f}  {verdict}")
        results[cls] = {"n": len(v), "gross_bp": gross,
                        "net_assumed_bp": mean(nets_a),
                        "net_measured_bp": mean(nets_m),
                        "delta_bp": mean(nets_m) - mean(nets_a),
                        "pf_measured": pfm, "pf_ci_lo": lo, "verdict": verdict}

    print("\n" + "=" * 78)
    print("VERDICT")
    print("=" * 78)
    changed = [c for c, r in results.items()
               if r["net_assumed_bp"] > 0 >= r["net_measured_bp"]
               or r["net_assumed_bp"] <= 0 < r["net_measured_bp"]]
    flips = [c for c, r in results.items()
             if r["pf_measured"] > 1 and r["net_assumed_bp"] <= 0]
    print(f"    classes whose NET changed SIGN: {changed or 'none'}")
    print(f"    classes that would look profitable at measured cost but not "
          f"assumed: {flips or 'none'}")
    understated = {c: r["delta_bp"] for c, r in results.items() if r["delta_bp"] < 0}
    print(f"\n    cost understated for: "
          f"{ {c: round(v,2) for c, v in understated.items()} or 'none'}")
    if not changed:
        print("\n    No verdict changes. Every class that failed at the ledger's")
        print("    assumed cost still fails at measured cost, and gets worse where")
        print("    the assumption was too low. The refutations are robust to the")
        print("    cost model -- which is the property you want from a refutation")
        print("    and did not necessarily expect.")
    print("\n    STILL UNMEASURED and therefore still blocking any promotion:")
    for c in sorted(UNMEASURED):
        print(f"      {c}")

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "recost.json").write_text(json.dumps({
        "assumed": ASSUMED,
        "measured": {k: {"bp": v[0], "source": v[1]} for k, v in MEASURED.items()},
        "unmeasured": sorted(UNMEASURED),
        "per_class": results, "sign_changes": changed,
    }, indent=1))
    print(f"\nwrote {out/'recost.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
