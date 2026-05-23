#!/usr/bin/env python3
"""
Walk-forward backtest with confidence calibration.
Rolling train/test windows, per-window OOS metrics, 0.1% RT fee, Brier score.
Uses dashboard_data.json closed picks only (no external OHLCV dependency).
"""
import json, pathlib, math, argparse
from datetime import datetime, timedelta

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
OUT  = ROOT / "tools" / "walk_forward_results.json"

FEE_RT = 0.001  # 0.1% round-trip fee

# -- helpers ----------------------------------------------------------------

def load_picks():
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
    return [p for p in picks
            if (p.get("confidence") or 0) >= conf_t
            and (p.get("ml_composite_score") or p.get("score") or 0) >= ml_t
            and (p.get("trust_score") or 0) >= trust_t]


def compute_metrics(picks):
    n = len(picks)
    if n < 2:
        return {"n": n, "wr": 0, "pf": 0, "sharpe": -999, "sortino": -999, "max_dd": 0}
    pnls = np.array([p["_pnl"] / 100 - FEE_RT for p in picks])
    wins  = pnls[pnls > 0]
    losses = pnls[pnls <= 0]
    wr = len(wins) / n * 100
    gross_win  = float(wins.sum())  if len(wins)  else 0
    gross_loss = float(-losses.sum()) if len(losses) else 0.001
    pf = gross_win / gross_loss if gross_loss > 0 else 99
    mu, sigma = float(pnls.mean()), float(pnls.std())
    sharpe  = (mu / sigma) * math.sqrt(252) if sigma > 0 else -999
    down    = pnls[pnls < 0]
    down_std = float(down.std()) if len(down) > 1 else 0.001
    sortino = (mu / down_std) * math.sqrt(252) if down_std > 0 else -999
    cum = np.cumsum(pnls)
    peak = np.maximum.accumulate(cum)
    dd = peak - cum
    max_dd = float(dd.max()) * 100 if len(dd) else 0
    return {"n": n, "wr": round(wr, 1), "pf": round(pf, 2),
            "sharpe": round(sharpe, 2), "sortino": round(sortino, 2),
            "max_dd": round(max_dd, 2)}


def brier_score(picks):
    """Brier score: mean( (confidence - outcome)^2 ). Lower = better."""
    valid = [(p.get("confidence") or 0, 1 if p["_pnl"] > 0 else 0) for p in picks]
    if not valid:
        return 1.0
    arr = np.array(valid)
    probs = np.clip(arr[:, 0], 0, 1)
    return float(np.mean((probs - arr[:, 1]) ** 2))


def isotonic_calibrate(train_picks, test_picks):
    """Bin training conf into deciles, map to observed WR."""
    if len(train_picks) < 20:
        return test_picks
    confs = np.array([p.get("confidence") or 0 for p in train_picks])
    outcomes = np.array([1 if p["_pnl"] > 0 else 0 for p in train_picks])
    edges = np.linspace(0, 1, 11)
    cal_map = {}
    for i in range(10):
        lo, hi = edges[i], edges[i + 1]
        mask = (confs >= lo) & (confs < hi + (1e-9 if i == 9 else 0))
        cal_map[i] = float(outcomes[mask].mean()) if mask.sum() > 0 else 0.5
    for p in test_picks:
        c = min(max(p.get("confidence") or 0, 0), 0.999)
        p["_calibrated_conf"] = cal_map[min(int(c * 10), 9)]
    return test_picks

# -- walk-forward engine ----------------------------------------------------

def walk_forward(picks, train_days=None, test_days=None,
                 conf_t=0.0, ml_t=0, trust_t=0, calibrate=False):
    if not picks:
        return [], {}
    start, end = picks[0]["_dt"], picks[-1]["_dt"]
    span = (end - start).days
    # auto-size windows if not specified: train=60% of span, test=~1/5 of train
    if train_days is None:
        train_days = max(int(span * 0.6), 7)
    if test_days is None:
        test_days = max(int(train_days / 5), 3)
    windows = []
    cursor = start
    while True:
        train_end = cursor + timedelta(days=train_days)
        test_end  = train_end + timedelta(days=test_days)
        if test_end > end + timedelta(days=1):
            break
        train = [p for p in picks if cursor <= p["_dt"] < train_end]
        test  = [p for p in picks if train_end <= p["_dt"] < test_end]
        train_f = filter_picks(train, conf_t, ml_t, trust_t)
        test_f  = filter_picks(test,  conf_t, ml_t, trust_t)
        if calibrate:
            test_f = isotonic_calibrate(train_f, test_f)
        m = compute_metrics(test_f)
        m["window"] = f"{cursor.strftime('%Y-%m-%d')} -> {test_end.strftime('%Y-%m-%d')}"
        m["train_n"] = len(train_f)
        m["brier"] = round(brier_score(test_f), 4)
        windows.append(m)
        cursor += timedelta(days=test_days)  # slide by test window

    # aggregate OOS (trade-count-weighted means)
    if windows:
        ns = [w["n"] for w in windows if w["n"] > 0]
        total_n = sum(ns)
        if total_n > 0:
            def wavg(key, exclude=-900):
                valid = [(w[key], w["n"]) for w in windows if w["n"] > 0 and w[key] > exclude]
                s = sum(v * n for v, n in valid)
                return s / sum(n for _, n in valid) if valid else 0
            agg_wr     = wavg("wr")
            agg_pf     = wavg("pf")
            agg_sharpe = wavg("sharpe")
            agg_brier  = wavg("brier", exclude=-1)
        else:
            agg_wr = agg_pf = agg_sharpe = agg_brier = 0
        agg = {"n": total_n, "wr": round(agg_wr, 1), "pf": round(agg_pf, 2),
               "sharpe": round(agg_sharpe, 2), "brier": round(agg_brier, 4),
               "max_dd": round(max((w["max_dd"] for w in windows), default=0), 2),
               "windows": len(windows)}
    else:
        agg = {"n": 0, "wr": 0, "pf": 0, "sharpe": 0, "brier": 1, "max_dd": 0, "windows": 0}
    return windows, agg

# -- CLI --------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Walk-forward backtest on closed picks")
    ap.add_argument("--conf",   type=float, default=0.0,  help="Min confidence threshold")
    ap.add_argument("--ml",     type=float, default=0,    help="Min ml_composite_score")
    ap.add_argument("--trust",  type=float, default=0,    help="Min trust_score")
    ap.add_argument("--train",  type=int,   default=0,    help="Train window days (0=auto)")
    ap.add_argument("--test",   type=int,   default=0,    help="Test window days (0=auto)")
    ap.add_argument("--calibrate", action="store_true",    help="Isotonic confidence calibration")
    args = ap.parse_args()

    picks = load_picks()
    print(f"Loaded {len(picks)} closed picks  "
          f"[{picks[0]['_dt'].date()} .. {picks[-1]['_dt'].date()}]")

    train_d = args.train if args.train > 0 else None
    test_d  = args.test  if args.test  > 0 else None
    windows, agg = walk_forward(
        picks, train_d, test_d, args.conf, args.ml, args.trust, args.calibrate)

    hdr = (f"{'Window':<28} {'n':>5} {'WR%':>6} {'PF':>6} "
           f"{'Sharpe':>7} {'Sortino':>8} {'MaxDD%':>7} {'Brier':>7}")
    sep = "=" * len(hdr)
    print(f"\n{sep}\n{hdr}\n{'-'*len(hdr)}")
    for w in windows:
        print(f"{w['window']:<28} {w['n']:>5} {w['wr']:>6.1f} {w['pf']:>6.2f} "
              f"{w['sharpe']:>7.2f} {w['sortino']:>8.2f} "
              f"{w['max_dd']:>7.2f} {w['brier']:>7.4f}")
    print(f"{'-'*len(hdr)}")
    print(f"{'AGGREGATE OOS':<28} {agg['n']:>5} {agg['wr']:>6.1f} {agg['pf']:>6.2f} "
          f"{agg['sharpe']:>7.2f} {'':>8} {agg['max_dd']:>7.2f} {agg['brier']:>7.4f}")
    print(sep)
    print(f"  Fee: {FEE_RT*100:.1f}% RT | Calibration: {'ON' if args.calibrate else 'OFF'}"
          f" | Filters: conf>={args.conf} ml>={args.ml} trust>={args.trust}")

    result = {"params": vars(args), "aggregate": agg, "windows": windows}
    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"\nResults -> {OUT.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
