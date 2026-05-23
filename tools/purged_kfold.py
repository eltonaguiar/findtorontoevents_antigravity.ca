#!/usr/bin/env python3
"""
Purged K-Fold cross-validation with configurable embargo gap.

Replaces naive rolling-window backtest with proper time-series CV that
excludes picks falling within a purge window between train/test splits,
preventing look-ahead bias from overlapping trades.

Mercury recommendation: 1-2 week embargo for crypto trading signals.
"""
import json, math, argparse, pathlib
from datetime import datetime, timedelta

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
OUT  = ROOT / "tools" / "purged_kfold_results.json"

FEE_RT = 0.001  # 0.1% round-trip fee


# -- data loading ------------------------------------------------------------

def load_picks():
    """Load closed picks from dashboard_data.json, sorted by timestamp."""
    with DATA.open("r", encoding="utf-8") as f:
        d = json.load(f)
    picks = []
    for p in d["picks"].get("recent_closed", []):
        pnl = p.get("pnl_pct")
        ts  = p.get("timestamp", "")
        if pnl is None or not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
        except Exception:
            continue
        picks.append({**p, "_dt": dt, "_pnl": float(pnl)})
    picks.sort(key=lambda x: x["_dt"])
    return picks


def filter_picks(picks, conf_t, ml_t, trust_t):
    """Filter picks by confidence, ML score, and trust thresholds."""
    return [p for p in picks
            if (p.get("confidence") or 0) >= conf_t
            and (p.get("ml_composite_score") or p.get("score") or 0) >= ml_t
            and (p.get("trust_score") or 0) >= trust_t]


# -- metrics -----------------------------------------------------------------

def compute_metrics(picks):
    """Compute WR, PF, Sharpe, n for a set of picks."""
    n = len(picks)
    if n < 2:
        return {"n": n, "wr": 0.0, "pf": 0.0, "sharpe": -999.0}
    pnls = np.array([p["_pnl"] / 100 - FEE_RT for p in picks])
    wins = pnls[pnls > 0]
    losses = pnls[pnls <= 0]
    wr = len(wins) / n * 100
    gross_win  = float(wins.sum()) if len(wins) else 0.0
    gross_loss = float(-losses.sum()) if len(losses) else 0.001
    pf = gross_win / gross_loss if gross_loss > 0 else 99.0
    mu, sigma = float(pnls.mean()), float(pnls.std())
    sharpe = (mu / sigma) * math.sqrt(252) if sigma > 0 else -999.0
    return {"n": n, "wr": round(wr, 2), "pf": round(pf, 3), "sharpe": round(sharpe, 2)}


# -- purged K-Fold engine ----------------------------------------------------

def purged_kfold_split(picks, n_folds=5, embargo_days=7):
    """
    Generate purged K-Fold splits on time-sorted picks.

    Standard purged K-Fold (de Prado, 2018):
      - Split sorted picks into n_folds contiguous groups
      - For each fold k used as test set, train = all other folds
      - Remove from TRAIN any pick whose timestamp is within embargo_days
        of the test set boundaries (before test start or after test end)
      - Test set is never reduced — only train is purged

    This prevents information leakage from overlapping trades near the
    train/test boundary.
    """
    n = len(picks)
    fold_size = n // n_folds
    if fold_size < 5:
        raise ValueError(f"Too few picks ({n}) for {n_folds} folds")

    embargo = timedelta(days=embargo_days)

    for k in range(n_folds):
        test_start = k * fold_size
        test_end = (k + 1) * fold_size if k < n_folds - 1 else n

        test_picks = picks[test_start:test_end]
        if not test_picks:
            continue

        test_dt_lo = test_picks[0]["_dt"]
        test_dt_hi = test_picks[-1]["_dt"]

        train_picks = []
        purged_count = 0
        for i, p in enumerate(picks):
            if test_start <= i < test_end:
                continue  # skip test fold
            dt = p["_dt"]
            # Purge train picks within embargo of test boundaries
            too_close_before = (test_dt_lo - embargo) <= dt < test_dt_lo
            too_close_after  = test_dt_hi < dt <= (test_dt_hi + embargo)
            if too_close_before or too_close_after:
                purged_count += 1
                continue
            train_picks.append(p)

        yield {
            "fold": k,
            "train": train_picks,
            "test": test_picks,
            "purged": purged_count,
        }


def run_purged_kfold(picks, n_folds=5, embargo_days=7,
                     conf_t=0.0, ml_t=0.0, trust_t=0.0):
    """Run purged K-Fold CV and return per-fold + aggregate metrics."""
    folds = []
    for split in purged_kfold_split(picks, n_folds, embargo_days):
        train_f = filter_picks(split["train"], conf_t, ml_t, trust_t)
        test_f  = filter_picks(split["test"],  conf_t, ml_t, trust_t)
        m = compute_metrics(test_f)
        m["fold"] = split["fold"]
        m["train_n"] = len(train_f)
        m["purged"] = split["purged"]
        folds.append(m)

    # Weighted aggregate (by n trades)
    total_n = sum(f["n"] for f in folds if f["n"] > 0)
    if total_n > 0:
        def wavg(key, exclude=-900):
            valid = [(f[key], f["n"]) for f in folds if f["n"] > 0 and f[key] > exclude]
            if not valid:
                return 0.0
            return sum(v * n for v, n in valid) / sum(n for _, n in valid)
        agg = {
            "n": total_n,
            "wr": round(wavg("wr"), 2),
            "pf": round(wavg("pf"), 3),
            "sharpe": round(wavg("sharpe"), 2),
            "folds": len(folds),
            "total_purged": sum(f["purged"] for f in folds),
        }
    else:
        agg = {"n": 0, "wr": 0, "pf": 0, "sharpe": 0, "folds": len(folds), "total_purged": 0}
    return folds, agg


# -- CLI ---------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Purged K-Fold CV on closed picks")
    ap.add_argument("--folds",   type=int,   default=5,   help="Number of folds (default 5)")
    ap.add_argument("--embargo", type=int,   default=7,   help="Embargo/purge gap in days (default 7)")
    ap.add_argument("--conf",    type=float, default=0.0, help="Min confidence threshold")
    ap.add_argument("--ml",      type=float, default=0.0, help="Min ml_composite_score")
    ap.add_argument("--trust",   type=float, default=0.0, help="Min trust_score")
    args = ap.parse_args()

    picks = load_picks()
    print(f"Loaded {len(picks)} closed picks "
          f"[{picks[0]['_dt'].date()} .. {picks[-1]['_dt'].date()}]")

    # Run WITHOUT purge (embargo=0) for comparison
    folds_no_purge, agg_no_purge = run_purged_kfold(
        picks, args.folds, embargo_days=0,
        conf_t=args.conf, ml_t=args.ml, trust_t=args.trust)

    # Run WITH purge
    folds_purged, agg_purged = run_purged_kfold(
        picks, args.folds, embargo_days=args.embargo,
        conf_t=args.conf, ml_t=args.ml, trust_t=args.trust)

    # Print per-fold results
    hdr = f"{'Fold':>5} {'n':>6} {'WR%':>7} {'PF':>7} {'Sharpe':>8} {'Train':>7} {'Purged':>7}"
    sep = "=" * len(hdr)

    print(f"\n{sep}")
    print(f"  WITHOUT purge (embargo=0 days)")
    print(f"{sep}\n{hdr}\n{'-' * len(hdr)}")
    for f in folds_no_purge:
        print(f"{f['fold']:>5} {f['n']:>6} {f['wr']:>7.2f} {f['pf']:>7.3f} "
              f"{f['sharpe']:>8.2f} {f['train_n']:>7} {f['purged']:>7}")
    print(f"{'-' * len(hdr)}")
    print(f"{'AGG':>5} {agg_no_purge['n']:>6} {agg_no_purge['wr']:>7.2f} "
          f"{agg_no_purge['pf']:>7.3f} {agg_no_purge['sharpe']:>8.2f}")
    print(sep)

    print(f"\n{sep}")
    print(f"  WITH {args.embargo}-day purge (embargo={args.embargo} days)")
    print(f"{sep}\n{hdr}\n{'-' * len(hdr)}")
    for f in folds_purged:
        print(f"{f['fold']:>5} {f['n']:>6} {f['wr']:>7.2f} {f['pf']:>7.3f} "
              f"{f['sharpe']:>8.2f} {f['train_n']:>7} {f['purged']:>7}")
    print(f"{'-' * len(hdr)}")
    print(f"{'AGG':>5} {agg_purged['n']:>6} {agg_purged['wr']:>7.2f} "
          f"{agg_purged['pf']:>7.3f} {agg_purged['sharpe']:>8.2f}")
    print(sep)

    # Leakage summary
    leakage = agg_no_purge["wr"] - agg_purged["wr"]
    print(f"\n  Without purge: {agg_no_purge['wr']:.2f}% WR.  "
          f"With {args.embargo}-day purge: {agg_purged['wr']:.2f}% WR.  "
          f"Leakage: {leakage:+.2f}%")
    print(f"  Total picks purged across folds: {agg_purged['total_purged']}")
    print(f"  Filters: conf>={args.conf}  ml>={args.ml}  trust>={args.trust}")

    # Save results
    result = {
        "params": vars(args),
        "no_purge": {"aggregate": agg_no_purge, "folds": folds_no_purge},
        "purged":   {"aggregate": agg_purged,   "folds": folds_purged},
        "leakage_wr_pct": round(leakage, 2),
    }
    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"\n  Results -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
