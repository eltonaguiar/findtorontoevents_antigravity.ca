"""Feature-distribution drift check on closed_picks.json.

Splits picks into 'historical' (older than --window-days, default 30) and
'recent' (within the last --window-days). For each numeric feature, reports
mean/std, 2-sample KS-test p-value, and a histogram-based KL divergence
approximation. Prefers scipy.stats.ks_2samp when available; otherwise uses a
pure-python fallback implementation of the 2-sample KS statistic.

Exits non-zero when any feature has p < --alpha (default 0.01) and n >= --min-n.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from tools.data_integrity._common import (  # noqa: E402
    CLOSED_PICKS,
    load_json_list,
    parse_ts,
)

NUMERIC_FEATURES = [
    "confidence",
    "risk_reward",
    "elite_score",
    "method_a_score",
    "ml_composite_score",
    "consensus_pct",
    "pnl_pct",
    "position_size",
    "hold_bars",
]


def _try_scipy_ks(a: list[float], b: list[float]) -> float | None:
    try:
        from scipy.stats import ks_2samp  # type: ignore

        return float(ks_2samp(a, b).pvalue)
    except Exception:
        return None


def _manual_ks_pvalue(a: list[float], b: list[float]) -> float:
    """Pure-python 2-sample Kolmogorov-Smirnov p-value.

    Uses the asymptotic Kolmogorov distribution (Smirnov formula).
    """
    if not a or not b:
        return 1.0
    a_sorted = sorted(a)
    b_sorted = sorted(b)
    merged = sorted(set(a_sorted) | set(b_sorted))
    n1, n2 = len(a_sorted), len(b_sorted)
    d = 0.0
    i = j = 0
    for x in merged:
        while i < n1 and a_sorted[i] <= x:
            i += 1
        while j < n2 and b_sorted[j] <= x:
            j += 1
        diff = abs(i / n1 - j / n2)
        if diff > d:
            d = diff
    en = math.sqrt(n1 * n2 / (n1 + n2))
    lam = (en + 0.12 + 0.11 / en) * d
    # Smirnov series expansion
    p = 0.0
    for k in range(1, 101):
        term = 2.0 * ((-1) ** (k - 1)) * math.exp(-2.0 * (lam ** 2) * (k ** 2))
        p += term
        if abs(term) < 1e-10:
            break
    return max(0.0, min(1.0, p))


def ks_pvalue(a: list[float], b: list[float]) -> float:
    r = _try_scipy_ks(a, b)
    return r if r is not None else _manual_ks_pvalue(a, b)


def _stats(vals: list[float]) -> tuple[float, float]:
    if not vals:
        return 0.0, 0.0
    m = sum(vals) / len(vals)
    v = sum((x - m) ** 2 for x in vals) / len(vals)
    return m, math.sqrt(v)


def kl_hist(a: list[float], b: list[float], bins: int = 20) -> float:
    if not a or not b:
        return 0.0
    lo = min(min(a), min(b))
    hi = max(max(a), max(b))
    if hi <= lo:
        return 0.0
    width = (hi - lo) / bins
    ha = [0] * bins
    hb = [0] * bins
    for x in a:
        idx = min(int((x - lo) / width), bins - 1)
        ha[idx] += 1
    for x in b:
        idx = min(int((x - lo) / width), bins - 1)
        hb[idx] += 1
    eps = 1e-9
    pa = [(c + eps) / (len(a) + bins * eps) for c in ha]
    pb = [(c + eps) / (len(b) + bins * eps) for c in hb]
    return sum(p * math.log(p / q) for p, q in zip(pa, pb))


def extract(rows: list[dict], feature: str) -> list[float]:
    out = []
    for p in rows:
        v = p.get(feature)
        if v is None:
            continue
        try:
            out.append(float(v))
        except (TypeError, ValueError):
            continue
    return out


def split_rows(rows: list[dict], now: datetime, window_days: int) -> tuple[list[dict], list[dict]]:
    cutoff = now - timedelta(days=window_days)
    hist, recent = [], []
    for p in rows:
        ts = parse_ts(p.get("created_at") or p.get("closed_at") or p.get("opened_at"))
        if ts is None:
            continue
        (recent if ts >= cutoff else hist).append(p)
    return hist, recent


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--closed", default=CLOSED_PICKS)
    ap.add_argument("--window-days", type=int, default=30)
    ap.add_argument("--alpha", type=float, default=0.01)
    ap.add_argument("--min-n", type=int, default=20)
    ap.add_argument("--now", default=None)
    args = ap.parse_args(argv)

    rows = load_json_list(args.closed)
    now = parse_ts(args.now) if args.now else datetime.now(timezone.utc)
    hist, recent = split_rows(rows, now, args.window_days)

    print("=" * 80)
    print("FEATURE DRIFT REPORT")
    print(f"window_days={args.window_days} alpha={args.alpha} min_n={args.min_n}")
    print(f"historical n={len(hist)}  recent n={len(recent)}")
    print("=" * 80)

    results = []
    for feat in NUMERIC_FEATURES:
        a = extract(hist, feat)
        b = extract(recent, feat)
        if len(a) < args.min_n or len(b) < args.min_n:
            results.append({"feature": feat, "skip": True, "n_hist": len(a), "n_recent": len(b)})
            continue
        ma, sa = _stats(a)
        mb, sb = _stats(b)
        p = ks_pvalue(a, b)
        kl = kl_hist(a, b)
        results.append({
            "feature": feat, "n_hist": len(a), "n_recent": len(b),
            "mean_hist": ma, "std_hist": sa, "mean_recent": mb, "std_recent": sb,
            "ks_p": p, "kl": kl,
            "drifted": p < args.alpha,
        })

    results.sort(key=lambda r: -(r.get("kl") or 0.0))
    print(f"{'feature':22s} {'n_h':>6s} {'n_r':>6s} {'m_h':>9s} {'m_r':>9s} {'ks_p':>10s} {'kl':>8s} flag")
    print("-" * 90)
    for r in results:
        if r.get("skip"):
            print(f"{r['feature']:22s} {r['n_hist']:6d} {r['n_recent']:6d}  {'--':>9s} {'--':>9s} {'--':>10s} {'--':>8s} under_sampled")
            continue
        flag = "DRIFT" if r["drifted"] else ""
        print(
            f"{r['feature']:22s} {r['n_hist']:6d} {r['n_recent']:6d} "
            f"{r['mean_hist']:9.3f} {r['mean_recent']:9.3f} "
            f"{r['ks_p']:10.4f} {r['kl']:8.4f} {flag}"
        )

    drifted = [r for r in results if r.get("drifted")]
    if drifted:
        print(f"\nFAIL: {len(drifted)} drifted feature(s): "
              + ", ".join(r["feature"] for r in drifted))
        return 2
    print("\nOK: no drift at alpha threshold.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
