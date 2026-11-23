#!/usr/bin/env python3
"""two_hurdle_kill.py — adopt copilot's TWO-hurdle kill rule (correction #2).

A single cash hurdle is insufficient: a rule that is long SPY 90% of the time
clears a cash hurdle on BETA alone while its signal contributes nothing.

Hurdle 1: net return > TBIL (4.32%/yr, copilot's measured hurdle)
Hurdle 2: paired bootstrap 95% CI on (strategy_net - benchmark_leg) EXCLUDES zero

Benchmark leg comes from forward_observations.jsonl `benchmark_leg_ret` (the
direction-adjusted buy-and-hold return over the same window). If that leg is
missing the row cannot be paired and is excluded (and counted).

Cost: measured 12.87 bp round trip at a $25k ticket (spread 12.07 + IBKR 0.8).
"""
import argparse, json, random, statistics as st
from datetime import datetime
from pathlib import Path

TBIL_PCT = 4.32
COST_RT_BP = 12.87


def _dt(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def _gross_ret(r):
    try:
        e, x = float(r["entry_px"]), float(r["exit_px"])
    except Exception:
        return None
    if e <= 0:
        return None
    return (x / e - 1.0) if str(r.get("side", "LONG")).upper() == "LONG" else (1.0 - x / e)


def paired_bootstrap_ci(diffs, n_boot=4000, seed=7):
    if len(diffs) < 2:
        return None
    rng = random.Random(seed)
    n = len(diffs)
    means = []
    for _ in range(n_boot):
        means.append(sum(diffs[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    return {
        "mean": sum(diffs) / n,
        "ci_lo": means[int(0.025 * n_boot)],
        "ci_hi": means[int(0.975 * n_boot) - 1],
        "n": n,
    }


def boot_median_ci(x, n_boot=4000, seed=11):
    if len(x) < 2:
        return None
    rng = random.Random(seed); m = []
    n = len(x)
    for _ in range(n_boot):
        s = sorted(x[rng.randrange(n)] for _ in range(n))
        m.append(s[n // 2])
    m.sort()
    return [m[int(0.025 * n_boot)], m[int(0.975 * n_boot) - 1]]


def sign_test_p(diffs):
    """Two-sided sign test that P(net > benchmark) = 0.5."""
    from math import comb
    n = len(diffs); w = sum(1 for d in diffs if d > 0)
    if n == 0:
        return None
    upper = sum(comb(n, k) for k in range(w, n + 1)) / 2 ** n
    lower = sum(comb(n, k) for k in range(0, w + 1)) / 2 ** n
    return min(1.0, 2 * min(upper, lower))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--forward", default="reports/forward_observations.jsonl")
    ap.add_argument("--out", default="reports/two_hurdle_kill.json")
    args = ap.parse_args()

    by_hyp = {}
    unmatched = 0
    rows = 0
    for line in open(args.forward):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        rows += 1
        g = _gross_ret(r)
        b = r.get("benchmark_leg_ret")
        if g is None or b is None:
            unmatched += 1
            continue
        net = g - COST_RT_BP / 10000.0
        o, c = _dt(r.get("opened_at")), _dt(r.get("closed_at"))
        hold_days = ((c - o).total_seconds() / 86400.0) if (o and c) else None
        rec = {"net_ret": net, "diff": net - float(b), "hold_days": hold_days,
               "asset_class": r.get("asset_class"), "symbol": r.get("symbol")}
        by_hyp.setdefault(r.get("hypothesis_id") or "UNKNOWN", []).append(rec)

    out = {"generated_at": datetime.now(__import__("datetime").UTC).isoformat(),
           "rule": {"hurdle1": f"net annualised > {TBIL_PCT}%",
                    "hurdle2": "paired bootstrap 95% CI on (net - benchmark_leg) excludes 0",
                    "cost_rt_bp": COST_RT_BP},
           "rows_total": rows, "rows_unpaired_excluded": unmatched, "by_hypothesis": {}}

    for hyp, recs in sorted(by_hyp.items()):
        diffs = [r["diff"] for r in recs]
        nets = [r["net_ret"] for r in recs]
        hold = [r["hold_days"] for r in recs if r["hold_days"]]
        ci = paired_bootstrap_ci(diffs)
        mean_hold = st.mean(hold) if hold else None
        # annualise the mean net using mean hold (only if hold >= 1d; else not annualisable)
        ann = None
        if mean_hold and mean_hold > 0:
            ann = (st.mean(nets) * (365.0 / mean_hold)) * 100.0
        med_ci = boot_median_ci(diffs)
        sign_p = sign_test_p(diffs)
        frac_beat = (sum(1 for d in diffs if d > 0) / len(diffs)) if diffs else None
        h1 = bool(ann is not None and ann > TBIL_PCT)
        # Hurdle 2 must survive BOTH the mean CI and the median CI; a mean-only
        # pass is an outlier artifact (fat benchmark left tail), which is exactly
        # how a losing strategy can look like it beats buy-and-hold.
        h2_mean = bool(ci and ci["ci_lo"] > 0)
        h2_med = bool(med_ci and med_ci[0] > 0)
        h2 = h2_mean and h2_med
        out["by_hypothesis"][hyp] = {
            "n_paired": len(recs), "mean_hold_days": round(mean_hold, 4) if mean_hold else None,
            "net_mean_ret": round(st.mean(nets), 6), "net_annualised_pct": round(ann, 4) if ann is not None else None,
            "paired_diff_mean": round(ci["mean"], 6) if ci else None,
            "paired_diff_ci": [round(ci["ci_lo"], 6), round(ci["ci_hi"], 6)] if ci else None,
            "median_paired_diff": round(st.median(diffs), 6) if diffs else None,
            "median_paired_ci": [round(x, 6) for x in med_ci] if med_ci else None,
            "frac_beat_benchmark": round(frac_beat, 4) if frac_beat is not None else None,
            "sign_test_p_two_sided": round(sign_p, 4) if sign_p is not None else None,
            "HURDLE_1_net_gt_tbil": h1,
            "HURDLE_2_mean_ci_excludes_zero": h2_mean,
            "HURDLE_2_median_ci_excludes_zero": h2_med,
            "HURDLE_2_robust_pass": h2,
            "KILL": (not (h1 and h2)),
        }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out["by_hypothesis"], indent=2))
    print(f"rows_total={rows} unpaired_excluded={unmatched}")


if __name__ == "__main__":
    main()
