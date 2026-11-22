#!/usr/bin/env python3
"""Reverse-engineer what distinguishes "skyrocketing" outcomes from ordinary ones.

This is the discovery arm of the audit stack. The tribunal asks "is this strategy
real?"; this asks "what do the winners have in common, and is that lift bigger
than chance?" It proposes candidates and refuses to declare an edge:

  * the event must be defined up front (`--field` + `--threshold`),
  * every feature is tested, so p-values are reported raw and BH-adjusted,
  * lift is always measured against the base rate,
  * winners are compared to matched controls (same class, similar hold),
  * nothing here is a verdict — survivors go to the audit3 forward gate.

Input: a JSON payload — a list of row dicts, or a dashboard-style object with the
rows under one of picks / trades / rows / closed.

Usage
    python3 tools/skyrocket_reverse_eng.py --picks audit_dashboard/data/dashboard_data.json
    python3 tools/skyrocket_reverse_eng.py --picks rows.json --field pnl_pct --threshold 20
    python3 tools/skyrocket_reverse_eng.py --picks rows.json --json-out /tmp/sky.json
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from pathlib import Path

# Identifiers and outcome/price fields are never features.
NON_FEATURE = {
    "id", "pick_id", "symbol", "strategy", "asset_class", "direction", "status",
    "outcome", "closed_at", "entry_date", "exit_date", "entry_time", "exit_time",
    "entry_px", "exit_px", "entry_price", "exit_price", "tp", "sl",
    "pnl_pct", "pnl", "profit_pct", "mfe_pct", "mae_pct", "hold_days",
}
MATCH_KEYS = ("asset_class", "direction")
MIN_PAIR_N = 10


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson interval for a proportion — honest at small n, unlike normal approx."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - r) / d), min(1.0, (c + r) / d))


def load_rows(payload) -> list[dict]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("picks", "trades", "rows", "closed", "closed_picks"):
            if isinstance(payload.get(key), list):
                return [r for r in payload[key] if isinstance(r, dict)]
    raise ValueError("payload has no list of rows")


def _num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)) and math.isfinite(v):
        return float(v)
    return None


def labels(rows: list[dict], field: str, threshold: float) -> list[int | None]:
    """1 if the row's `field` reached `threshold`, 0 if it has the field, None otherwise."""
    out: list[int | None] = []
    for r in rows:
        v = _num(r.get(field))
        out.append(None if v is None else int(v >= threshold))
    return out


def numeric_features(rows: list[dict], min_cov: float = 0.8) -> list[str]:
    n = len(rows)
    if n == 0:
        return []
    counts: dict[str, int] = {}
    for r in rows:
        for k, v in r.items():
            if k not in NON_FEATURE and _num(v) is not None:
                counts[k] = counts.get(k, 0) + 1
    return sorted(k for k, c in counts.items() if c / n >= min_cov)


def _pairs(rows, ys, feature):
    xs, ls = [], []
    for r, y in zip(rows, ys):
        if y is None:
            continue
        x = _num(r.get(feature))
        if x is None:
            continue
        xs.append(x)
        ls.append(y)
    return xs, ls


def _ranks(vals: list[float]) -> list[float]:
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    ranks = [0.0] * len(vals)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _pearson(a: list[float], b: list[float]) -> float:
    n = len(a)
    if n < 3:
        return 0.0
    ma, mb = sum(a) / n, sum(b) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = math.sqrt(sum((x - ma) ** 2 for x in a))
    db = math.sqrt(sum((y - mb) ** 2 for y in b))
    return num / (da * db) if da and db else 0.0


def spearman(xs: list[float], ys: list[float]) -> float:
    return _pearson(_ranks(xs), _ranks([float(y) for y in ys]))


def permutation_p(xs: list[float], ys: list[int], b: int = 1000, seed: int = 0) -> float:
    """Two-sided permutation p for |rho| under a random relabeling of outcomes."""
    rng = random.Random(seed)
    rho = abs(spearman(xs, ys))
    hits = 0
    ys_work = list(ys)
    for _ in range(b):
        rng.shuffle(ys_work)
        if abs(spearman(xs, ys_work)) >= rho:
            hits += 1
    return (1 + hits) / (b + 1)


def bh_adjust(pvals: list[float]) -> list[float]:
    """Benjamini–Hochberg q-values, same order as input."""
    m = len(pvals)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: pvals[i])
    q = [1.0] * m
    prev = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        val = min(prev, pvals[i] * m / rank)
        q[i] = val
        prev = val
    return q


def deciles(xs: list[float], ys: list[int]) -> list[dict]:
    """Skyrocket rate per decile of a feature, with Wilson CI."""
    n = len(xs)
    if n < 10:
        return []
    order = sorted(range(n), key=lambda i: xs[i])
    out = []
    for d in range(10):
        idx = order[d * n // 10:(d + 1) * n // 10]
        if not idx:
            continue
        vals = [xs[i] for i in idx]
        k = sum(ys[i] for i in idx)
        lo, hi = wilson(k, len(idx))
        out.append({"decile": d + 1, "n": len(idx),
                    "mean_x": round(statistics.fmean(vals), 6),
                    "rate": round(k / len(idx), 4),
                    "lo": round(lo, 4), "hi": round(hi, 4)})
    return out


def matched_diff(rows, ys, feature, b: int = 500, seed: int = 0) -> dict | None:
    """Mean feature difference between winners and same-class controls.

    Each winner is paired with the nearest non-winner in the same
    asset_class/direction by hold length (or by index of the row when no hold
    is available). Naive winner-vs-rest means are also reported so a
    class-wide effect can be seen to inflate them.
    """
    winners = [i for i, y in enumerate(ys) if y == 1 and _num(rows[i].get(feature)) is not None]
    others = [i for i, y in enumerate(ys) if y == 0 and _num(rows[i].get(feature)) is not None]
    if len(winners) < MIN_PAIR_N or len(others) < MIN_PAIR_N:
        return None
    hold = lambda i: _num(rows[i].get("hold_days")) or 0.0
    naive = statistics.fmean(_num(rows[i][feature]) for i in winners) - \
        statistics.fmean(_num(rows[i][feature]) for i in others)
    pairs = []
    for w in winners:
        same = [o for o in others
                if all(rows[o].get(k) == rows[w].get(k) for k in MATCH_KEYS)] or others
        best = min(same, key=lambda o: abs(hold(o) - hold(w)))
        pairs.append(_num(rows[w][feature]) - _num(rows[best][feature]))
    rng = random.Random(seed)
    boots = []
    for _ in range(b):
        sample = [pairs[rng.randrange(len(pairs))] for _ in range(len(pairs))]
        boots.append(statistics.fmean(sample))
    boots.sort()
    return {
        "n_pairs": len(pairs),
        "naive_diff": round(naive, 6),
        "matched_diff": round(statistics.fmean(pairs), 6),
        "ci": [round(boots[int(0.025 * b)], 6), round(boots[int(0.975 * b)], 6)],
        "cancels_zero": boots[int(0.025 * b)] <= 0 <= boots[int(0.975 * b)],
    }


NET_FIELDS = ("pnl_net_pct", "net_pnl_pct")


def resolve_objective(rows: list[dict], field: str) -> tuple[str, str | None]:
    """Prefer a net-of-cost outcome field over the gross one.

    Searching against gross return finds features that predict *gross* winners —
    which is how a high-turnover signal with a real edge and a bigger cost bill
    gets promoted. Returns (field_to_use, explanation_or_None).
    """
    if field in NET_FIELDS:
        return field, None
    for alt in NET_FIELDS:
        if any(_num(r.get(alt)) is not None for r in rows):
            return alt, (f"'{field}' is gross; using '{alt}' — a discovery objective "
                         "that ignores costs selects for turnover")
    return field, (f"no net field present; '{field}' is the only objective available, "
                   "so survivors must be cost-checked downstream")


def direction_check(rho: float, lift: float | None,
                    matched: dict | None) -> str:
    """Do the rank correlation, the decile spread and the matched diff agree?

    Three independent views of the same feature with different failure modes.
    If their signs disagree, at least one is measuring something other than a
    monotone effect — usually a class-wide confound that matched_diff removes.
    """
    if lift is None:
        return "unknown"
    signs = {(1 if rho > 0 else -1), (1 if lift > 0 else -1)}
    md = (matched or {}).get("matched_diff")
    if md:
        signs.add(1 if md > 0 else -1)
    return "consistent" if len(signs) == 1 else "inconsistent"


def load_trial_counter(path: str) -> int:
    try:
        return int(json.loads(Path(path).read_text(encoding="utf-8"))["trials"])
    except Exception:
        return 0


def bump_trial_counter(path: str, k: int) -> int:
    """Persist the cumulative trial count so multiple-testing debt survives runs.

    A per-run count resets every invocation, which is exactly how the same
    feature gets 'discovered' twice on overlapping data and looks independent.
    """
    total = load_trial_counter(path) + k
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"trials": total}), encoding="utf-8")
    return total


def analyze(payload, field: str = "pnl_pct", threshold: float = 20.0,
            perm: int = 1000, seed: int = 0, trial_counter: str | None = None) -> dict:
    rows = load_rows(payload)
    requested = field
    field, objective_note = resolve_objective(rows, field)
    ys = labels(rows, field, threshold)
    n_labelled = sum(1 for y in ys if y is not None)
    n_hit = sum(1 for y in ys if y == 1)
    lo, hi = wilson(n_hit, n_labelled)
    feats = numeric_features(rows)
    results = []
    # A feature that could not be tested is not a feature that failed. Record it
    # with a reason, or "0 features tested" silently reads as "nothing here".
    skipped: list[dict] = []
    for f in feats:
        xs, ls = _pairs(rows, ys, f)
        cov = round(len(xs) / len(rows), 4) if rows else 0.0
        if len(ls) < 30 or len(set(xs)) < 3:
            skipped.append({
                "feature": f, "coverage": cov, "n": len(ls),
                "distinct": len(set(xs)),
                "reason": (f"n={len(ls)} < 30" if len(ls) < 30
                           else f"only {len(set(xs))} distinct values"),
            })
            continue
        rho = spearman(xs, ls)
        p = permutation_p(xs, ls, b=perm, seed=seed)
        dec = deciles(xs, ls)
        lift = None
        if len(dec) >= 2 and dec[0]["n"] and dec[-1]["n"]:
            lift = round(dec[-1]["rate"] - dec[0]["rate"], 4)
        md = matched_diff(rows, ys, f, seed=seed)
        results.append({"feature": f, "n": len(ls), "coverage": cov,
                        "rho": round(rho, 4), "p": round(p, 4),
                        "top_minus_bottom_rate": lift,
                        "direction": direction_check(rho, lift, md),
                        "matched": md, "deciles": dec})
    qs = bh_adjust([r["p"] for r in results])
    for r, q in zip(results, qs):
        r["q"] = round(q, 4)
    results.sort(key=lambda r: r["p"])
    trials = None
    if trial_counter:
        trials = {"path": trial_counter, "this_run": len(results),
                  "cumulative": bump_trial_counter(trial_counter, len(results))}
    return {
        "event": {"field": field, "requested_field": requested,
                  "threshold": threshold, "objective_note": objective_note,
                  "n_labelled": n_labelled, "n_hit": n_hit,
                  "base_rate": round(n_hit / n_labelled, 4) if n_labelled else None,
                  "wilson_ci": [round(lo, 4), round(hi, 4)]},
        "n_rows": len(rows),
        "features_tested": len(results),
        "features_skipped": len(skipped),
        "skipped": skipped,
        "direction_inconsistent": sorted(
            r["feature"] for r in results if r["direction"] == "inconsistent"),
        "trials": trials,
        "features": results,
        "inconclusive": (not results and bool(skipped)),
        "doctrine": "discovery only — no verdict; survivors must clear the audit3 forward gate",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--picks", required=True, help="JSON payload with the rows")
    ap.add_argument("--field", default="pnl_pct", help="outcome field defining the event")
    ap.add_argument("--threshold", type=float, default=20.0, help="event threshold (percent)")
    ap.add_argument("--perm", type=int, default=1000, help="permutation draws")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--json-out")
    ap.add_argument("--trial-counter", default=None,
                    help="JSON file accumulating the trial count across runs")
    a = ap.parse_args(argv)
    payload = json.loads(Path(a.picks).read_text(encoding="utf-8"))
    rep = analyze(payload, a.field, a.threshold, a.perm, a.seed,
                  trial_counter=a.trial_counter)
    if a.json_out:
        Path(a.json_out).write_text(json.dumps(rep, indent=1), encoding="utf-8")
    e = rep["event"]
    print(f"event {e['field']} >= {e['threshold']}: {e['n_hit']}/{e['n_labelled']} "
          f"= {e['base_rate']} (95% CI {e['wilson_ci'][0]}..{e['wilson_ci'][1]})")
    print(f"{rep['features_tested']} features tested on {rep['n_rows']} rows")
    for r in rep["features"][:15]:
        m = r["matched"] or {}
        print(f"  {r['feature']:<28} rho {r['rho']:+.3f}  p {r['p']:.4f}  q {r['q']:.4f}"
              f"  top-bottom {r['top_minus_bottom_rate']}"
              f"  matched {m.get('matched_diff')} {m.get('ci')}")
    print(rep["doctrine"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
