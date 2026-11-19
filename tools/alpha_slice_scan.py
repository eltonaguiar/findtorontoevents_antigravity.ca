"""alpha_slice_scan.py — which slice, if any, beats matched exposure?

The per-class alpha headline ("CRYPTO -0.162%/pick") is true and useless: it
cannot be acted on. This scans the per-pick rows from
`alpha_engine/audit3_selection_alpha.py --rows-out` for slices that survive a
multiplicity correction, so a class verdict can be traced to a decision.

Slices tested (n >= --min-n): class, class/direction, exit reason,
class/exit reason, score band, rr band, timeframe, trust tier, strategy,
source. Every slice is one hypothesis, so BH is applied across the whole batch
of slices examined — scanning 40 slices and reporting the best one at p<0.05 is
exactly the mistake this file exists to prevent.

Input: JSONL, one pick per line, each with alpha, class, dir + the slice fields.
Output: --out JSON + a ranked table on stdout.

Exit codes: 0 ok, 2 unusable input, 4 nothing survives.

Not investment advice; a slice that survives is a hypothesis to pre-register.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

MODULE = Path(__file__).resolve()
ROOT = MODULE.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpha_engine.audit3_tribunal import bootstrap_mean_ci  # noqa: E402

MIN_N_DEFAULT = 30
Q_MAX = 0.10


def _p_two_sided(mean: float, sd: float, n: int) -> float:
    """Normal-approximation p-value for mean != 0 (CLT at n >= min_n)."""
    if n < 2 or sd <= 0:
        return 1.0
    se = sd / math.sqrt(n)
    if se <= 0:
        return 1.0
    z = abs(mean) / se
    return math.erfc(z / math.sqrt(2.0))


def _bh(pvals: list[float]) -> list[float]:
    """Benjamini-Hochberg q-values, order preserved."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    q = [1.0] * m
    prev = 1.0
    for rank, i in enumerate(reversed(order), start=1):
        k = m - rank + 1
        val = min(prev, pvals[i] * m / k)
        q[i] = val
        prev = val
    return q


def _band(v, edges):
    if v is None:
        return None
    for lo, label in edges:
        if v >= lo:
            return label
    return None


def _exit_bucket(reason: str) -> str:
    r = (reason or "").lower()
    for key in ("take", "tp", "target", "profit"):
        if key in r:
            return "exit:TP"
    for key in ("stop", "sl", "liquidat"):
        if key in r:
            return "exit:SL"
    for key in ("time", "expire", "stale", "horizon", "age"):
        if key in r:
            return "exit:TIME"
    return "exit:OTHER" if r else "exit:NONE"


def slices_for(rec: dict) -> list[str]:
    cls, d = rec.get("class") or "?", rec.get("dir") or "?"
    ex = _exit_bucket(rec.get("exit_reason") or "")
    out = [f"class:{cls}", f"class_dir:{cls}/{d}", ex, f"class_{ex}:{cls}",
           f"class_dir_{ex}:{cls}/{d}"]
    sb = _band(rec.get("score"), [(np_, f"score>={np_}") for np_ in (80, 60, 40)])
    if sb:
        out.append(f"score:{sb}")
        out.append(f"class_{sb}:{cls}")
    rb = _band(rec.get("rr_ratio"), [(2.5, "rr>=2.5"), (2.0, "rr>=2.0"), (1.5, "rr>=1.5")])
    if rb:
        out.append(f"rr:{rb}")
    tf = (rec.get("timeframe") or "").strip()
    if tf:
        out.append(f"tf:{tf}")
        out.append(f"class_tf:{cls}/{tf}")
    tier = (rec.get("trust_tier") or "").strip()
    if tier:
        out.append(f"tier:{tier}")
    strat = (rec.get("strategy") or "").strip()
    if strat:
        out.append(f"strategy:{strat}")
    src = (rec.get("source") or "").strip()
    if src:
        out.append(f"source:{src}")
    return out


def _class_of(name: str) -> str | None:
    """Extract the class a slice name is about, or None if it is class-less.

    Substring matching is wrong here: 'CRYPTO' occurs in slices about a
    strategy that happens to trade crypto, which would then be reported as the
    class's best/worst slice. Only `class...:` slices are class-scoped.
    """
    if not name.startswith("class"):
        return None
    _, _, rest = name.partition(":")
    head = rest.split("/")[0]
    return head.split(":")[-1] or None


def scan(records: list[dict], min_n: int = MIN_N_DEFAULT) -> dict:
    buckets: dict[str, list[float]] = defaultdict(list)
    for rec in records:
        a = rec.get("alpha")
        if a is None:
            continue
        for name in slices_for(rec):
            buckets[name].append(float(a))

    rows = []
    for name, vals in sorted(buckets.items()):
        n = len(vals)
        if n < min_n:
            continue
        mean = statistics.mean(vals)
        sd = statistics.pstdev(vals) if n > 1 else 0.0
        ci = bootstrap_mean_ci(vals) if n >= 5 else {"ci_lo": None, "ci_hi": None}
        rows.append({
            "slice": name, "n": n,
            "alpha_pct": round(mean, 4),
            "ci": [round(ci["ci_lo"], 4) if ci["ci_lo"] is not None else None,
                   round(ci["ci_hi"], 4) if ci["ci_hi"] is not None else None],
            "wr": round(sum(1 for v in vals if v > 0) / n, 4),
            "p": round(_p_two_sided(mean, sd, n), 6),
        })

    qs = _bh([r["p"] for r in rows])
    for r, q in zip(rows, qs):
        r["q"] = round(q, 6)
        ci_lo = r["ci"][0]
        r["survives"] = bool(q <= Q_MAX and r["alpha_pct"] > 0
                             and ci_lo is not None and ci_lo > 0)
        r["hurts"] = bool(q <= Q_MAX and r["alpha_pct"] < 0
                          and r["ci"][1] is not None and r["ci"][1] < 0)

    rows.sort(key=lambda r: (-r["alpha_pct"], r["n"]))
    per_class = {}
    for cls in sorted({c for c in (_class_of(r["slice"]) for r in rows) if c}):
        scoped = [r for r in rows if _class_of(r["slice"]) == cls]
        base = next((r for r in scoped if r["slice"] == f"class:{cls}"), None)
        best = next((r for r in scoped if r["survives"]), None)
        worst = next((r for r in scoped if r["hurts"]), None)
        per_class[cls] = {
            "n": base["n"] if base else None,
            "alpha_pct": base["alpha_pct"] if base else None,
            "best_surviving_slice": best["slice"] if best else None,
            "best_slice_alpha_pct": best["alpha_pct"] if best else None,
            "worst_harmful_slice": worst["slice"] if worst else None,
            "worst_slice_alpha_pct": worst["alpha_pct"] if worst else None,
        }
    return {
        "schema": "audit3.alpha_slice_scan.v1",
        "n_picks": len(records),
        "n_slices_tested": len(rows),
        "min_n": min_n,
        "q_max": Q_MAX,
        "calibration": "BH over every slice examined; a slice must clear q<=0.10 "
                       "with a positive mean and a CI lower bound above zero to count",
        "per_class": per_class,
        "slices": rows,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True, help="JSONL from --rows-out")
    ap.add_argument("--out")
    ap.add_argument("--min-n", type=int, default=MIN_N_DEFAULT)
    args = ap.parse_args(argv)

    records = []
    with open(args.rows, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if not records:
        print("ERROR: no rows", file=sys.stderr)
        return 2

    res = scan(records, args.min_n)
    if args.out:
        Path(args.out).write_text(json.dumps(res, indent=1), encoding="utf-8")

    print(f"{res['n_picks']} picks, {res['n_slices_tested']} slices at n>={args.min_n}; "
          f"{sum(1 for r in res['slices'] if r['survives'])} survive q<={Q_MAX}")
    print(f"{'slice':<44}{'n':>6}{'alpha%':>10}{'CI':>22}{'wr':>7}{'q':>8}")
    for r in res["slices"][:25]:
        ci = f"[{r['ci'][0]:+.3f},{r['ci'][1]:+.3f}]" if r["ci"][0] is not None else "n/a"
        flag = " *" if r["survives"] else (" !" if r["hurts"] else "")
        print(f"{r['slice'][:43]:<44}{r['n']:>6}{r['alpha_pct']:>+10.3f}{ci:>22}"
              f"{r['wr']:>7.1%}{r['q']:>8.3f}{flag}")
    for cls, v in res["per_class"].items():
        print(f"  {cls:<10} n={v['n']:<5} alpha={v['alpha_pct']:+.3f}% "
              f"best_surviving={v['best_surviving_slice']} "
              f"most_harmful={v['worst_harmful_slice']}")
    return 0 if any(r["survives"] for r in res["slices"]) else 4


if __name__ == "__main__":
    raise SystemExit(main())
