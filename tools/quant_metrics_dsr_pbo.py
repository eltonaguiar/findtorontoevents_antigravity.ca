#!/usr/bin/env python3
"""Block 3: deflate the block-2 cross-class results with DSR and PBO.

WHY THIS BLOCK EXISTS
    Block 2 produced EQUITY OOS Sharpe 1.40 and ETF 1.21 on 15 configs each,
    selected by in-sample Sharpe. Those numbers are exactly what a search over
    configurations manufactures. Before anything is called an edge it must survive
    two independent deflations:

      DSR (Deflated Sharpe Ratio, Bailey & Lopez de Prado 2014)
          P(the observed Sharpe is not the best-of-N fluke), given the number of
          trials and the observed dispersion of trial Sharpes. Needs > 0.95.

      PBO (Probability of Backtest Overfitting, CSCV - Bailey, Borwein, LdP, Zhu)
          Split the return matrix into S contiguous blocks; for every way of
          choosing S/2 blocks as in-sample, pick the IS-best config and see where
          it ranks OOS. PBO is the fraction of splits where the IS winner lands
          BELOW the OOS median. Needs < 0.50 to mean selection generalises.

MATHS IS REUSED, NOT RE-DERIVED
    The DSR helpers are imported from tools/deflated_sharpe.py by explicit path.
    That module's four historical defects (z-score published as a probability,
    50% gate, hardcoded trade rate, annualised SR against per-trade T) were fixed
    earlier; re-implementing the formula here would fork it. All maths is
    PER-PERIOD because that is what makes the standard error correct.

Read-only. Not investment advice.

Usage:
    python3 tools/quant_metrics_dsr_pbo.py
"""
from __future__ import annotations

import importlib.util
import itertools
import json
import math
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RETDIR = ROOT / "reports" / "cross_class_returns"
BACKTEST = ROOT / "reports" / "cross_class_backtest.json"
OUT = ROOT / "reports" / "quant_metrics_dsr_pbo.json"

DSR_THRESHOLD = 0.95
PBO_THRESHOLD = 0.50
N_BLOCKS = 8            # CSCV: must be even; C(8,4)=70 splits


def _load_dsr_module():
    spec = importlib.util.spec_from_file_location(
        "dsr_tool", ROOT / "tools" / "deflated_sharpe.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["dsr_tool"] = mod
    spec.loader.exec_module(mod)
    return mod


DSR = _load_dsr_module()


def sr_per_period(rets: list[float]) -> float | None:
    if len(rets) < 30:
        return None
    m = statistics.mean(rets)
    sd = statistics.stdev(rets)
    return (m / sd) if sd > 0 else None


def sharpe_on(rets: list[float]) -> float:
    s = sr_per_period(rets)
    return s if s is not None else -9.99


def cscv_pbo(series: dict[str, list[float]], n_blocks: int = N_BLOCKS) -> dict:
    """Probability of Backtest Overfitting via combinatorially symmetric CV."""
    keys = sorted(series)
    T = min(len(v) for v in series.values())
    if len(keys) < 2 or T < n_blocks * 10:
        return {"pbo": None, "reason": f"insufficient data T={T} N={len(keys)}"}
    block = T // n_blocks
    idx_blocks = [list(range(i * block, (i + 1) * block)) for i in range(n_blocks)]
    half = n_blocks // 2
    logits = []
    n_splits = 0
    for combo in itertools.combinations(range(n_blocks), half):
        is_idx = [i for b in combo for i in idx_blocks[b]]
        oos_idx = [i for b in range(n_blocks) if b not in combo
                   for i in idx_blocks[b]]
        is_sr, oos_sr = [], []
        for k in keys:
            v = series[k][:T]
            is_sr.append(sharpe_on([v[i] for i in is_idx]))
            oos_sr.append(sharpe_on([v[i] for i in oos_idx]))
        best = max(range(len(keys)), key=lambda i: is_sr[i])
        # rank of the IS winner among OOS performances (1 = worst)
        order = sorted(range(len(keys)), key=lambda i: oos_sr[i])
        rank = order.index(best) + 1
        omega = rank / (len(keys) + 1.0)
        omega = min(max(omega, 1e-6), 1 - 1e-6)
        logits.append(math.log(omega / (1 - omega)))
        n_splits += 1
    if not logits:
        return {"pbo": None, "reason": "no splits"}
    pbo = sum(1 for l in logits if l < 0) / len(logits)
    return {"pbo": round(pbo, 4), "n_splits": n_splits,
            "mean_logit": round(statistics.mean(logits), 4),
            "n_configs": len(keys), "T": T}


def main() -> int:
    if not RETDIR.is_dir():
        print(f"::error:: no return matrices at {RETDIR} -- run block 2 first")
        return 2
    bt = json.loads(BACKTEST.read_text()) if BACKTEST.exists() else {"classes": {}}
    results = {}
    for f in sorted(RETDIR.glob("*.json")):
        cls = f.stem
        d = json.loads(f.read_text())
        series = d["results"]
        keys = sorted(series)
        n_trials = len(keys)

        # per-period Sharpe for every trial -> empirical dispersion + SR*
        trial_sr = [sr_per_period(series[k]) for k in keys]
        trial_sr = [s for s in trial_sr if s is not None]
        if not trial_sr:
            results[cls] = {"status": "NO_VALID_TRIALS"}
            continue
        sigma_sr = statistics.stdev(trial_sr) if len(trial_sr) > 1 else 0.0
        sr_star = DSR._sr_haircut(n_trials, sigma_sr)

        pick = bt.get("classes", {}).get(cls, {}).get("top_pick")
        if not pick:
            results[cls] = {"status": "NO_TOP_PICK"}
            continue
        key = f"L{pick['lookback']}_H{pick['hold']}"
        rets = series.get(key)
        if not rets:
            results[cls] = {"status": f"TOP_PICK_SERIES_MISSING {key}"}
            continue

        mu, sd, skew, kurt = DSR._compute_moments(rets)
        sr_pp = mu / sd if sd > 0 else 0.0
        se = DSR._sharpe_se(sr_pp, skew, kurt, len(rets))
        dsr = DSR._deflated_sharpe(sr_pp, sr_star, se)

        pbo = cscv_pbo(series)
        survives = (dsr > DSR_THRESHOLD
                    and pbo.get("pbo") is not None
                    and pbo["pbo"] < PBO_THRESHOLD)

        results[cls] = {
            "instrument": d.get("instrument"),
            "top_pick": key,
            "n_trials": n_trials,
            "T": len(rets),
            "sharpe_annualised": round(sr_pp * math.sqrt(252), 4),
            "sr_per_period": round(sr_pp, 6),
            "sigma_sr_across_trials": round(sigma_sr, 6),
            "sr_star_expected_max": round(sr_star, 6),
            "sr_star_annualised": round(sr_star * math.sqrt(252), 4),
            "se_sr": round(se, 6),
            "skew": round(skew, 3), "kurtosis": round(kurt, 3),
            "dsr": round(dsr, 6),
            "dsr_pass": dsr > DSR_THRESHOLD,
            "pbo": pbo.get("pbo"),
            "pbo_pass": (pbo.get("pbo") is not None
                         and pbo["pbo"] < PBO_THRESHOLD),
            "pbo_detail": pbo,
            "survives_both": survives,
            "cost_provenance": bt.get("classes", {}).get(cls, {}).get("cost_provenance"),
        }

    n_surv = sum(1 for r in results.values() if r.get("survives_both"))

    # ---- programme-level deflation ---------------------------------------
    # Each class was deflated at N=15. But we ran SIX classes, so the honest
    # trial count for "is any of this real" is 6 x 15 = 90. Deflating at N=15
    # while having searched 90 configurations is the same multiple-testing error
    # the rest of this programme has been fighting. So recompute the survivor at
    # the pooled trial count, using the pooled SR dispersion.
    pooled = {}
    for f in sorted(RETDIR.glob("*.json")):
        pooled[f.stem] = json.loads(f.read_text())["results"]
    all_sr = []
    for cls, ser in pooled.items():
        for k, v in ser.items():
            s = sr_per_period(v)
            if s is not None:
                all_sr.append(s)
    pooled_block = {}
    if all_sr:
        n_pooled = len(all_sr)
        sigma_pooled = statistics.stdev(all_sr) if n_pooled > 1 else 0.0
        sr_star_pooled = DSR._sr_haircut(n_pooled, sigma_pooled)
        for cls, r in results.items():
            if "dsr" not in r:
                continue
            rets = pooled[cls][r["top_pick"]]
            mu, sd, skew, kurt = DSR._compute_moments(rets)
            sr_pp = mu / sd if sd > 0 else 0.0
            se = DSR._sharpe_se(sr_pp, skew, kurt, len(rets))
            dsr_p = DSR._deflated_sharpe(sr_pp, sr_star_pooled, se)
            r["dsr_programme_level"] = round(dsr_p, 6)
            r["dsr_programme_pass"] = dsr_p > DSR_THRESHOLD
            pooled_block[cls] = {"dsr_programme_level": round(dsr_p, 6),
                                 "dsr_programme_pass": dsr_p > DSR_THRESHOLD}
        pooled_block["_pooled"] = {
            "n_trials": n_pooled,
            "sigma_sr_pooled": round(sigma_pooled, 6),
            "sr_star_expected_max": round(sr_star_pooled, 6),
            "sr_star_annualised": round(sr_star_pooled * math.sqrt(252), 4),
        }

    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "thresholds": {"dsr": DSR_THRESHOLD, "pbo": PBO_THRESHOLD},
        "method": {
            "dsr": "Bailey-LdP 2014, per-period Sharpe, helper module "
                   "tools/deflated_sharpe.py (corrected)",
            "pbo": f"CSCV, {N_BLOCKS} contiguous blocks, all C(S,S/2) splits",
            "per_class_trials": "N=15 (the grid within one class)",
            "programme_trials": "N=90 (6 classes x 15) -- the honest count",
        },
        "n_classes": len(results),
        "n_surviving_both": n_surv,
        "programme_level_deflation": pooled_block,
        "classes": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))

    print(f"{'CLASS':10} {'pick':>10} {'SRann':>7} {'SR*ann':>7} {'DSR':>7} "
          f"{'DSR?':>5} {'PBO':>6} {'PBO?':>5} {'SURVIVES':>9}")
    for cls, r in results.items():
        if "dsr" not in r:
            print(f"{cls:10} {r.get('status','')}")
            continue
        print(f"{cls:10} {r['top_pick']:>10} {r['sharpe_annualised']:>7.2f} "
              f"{r['sr_star_annualised']:>7.2f} {r['dsr']:>7.4f} "
              f"{('Y' if r['dsr_pass'] else 'n'):>5} "
              f"{(r['pbo'] if r['pbo'] is not None else -1):>6.3f} "
              f"{('Y' if r['pbo_pass'] else 'n'):>5} "
              f"{('YES' if r['survives_both'] else 'no'):>9}")
    print()
    print(f"classes evaluated        : {out['n_classes']}")
    print(f"surviving BOTH DSR and PBO : {n_surv}")
    print(f"written: {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
