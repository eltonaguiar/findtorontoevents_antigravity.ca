#!/usr/bin/env python3
"""Correlation-regime-shift early-warning sidecar (master-plan Action #5).

Per Citadel R3 blind-spot: every persona scoped edge inside one asset class
and one regime; nobody modeled the inter-class correlation matrix re-pricing
during a macro-stress event. When SPY/BTC/GLD/TLT all become positively
correlated, "diversified" sleeve allocations stop diversifying — drawdowns
stack instead of cancel.

Implementation:
  1. Pull daily closes for one representative ticker per asset class:
     - EQUITY:    SPY
     - ETF:       IWM (small-cap, distinct factor exposure from SPY)
     - BOND:      TLT
     - CRYPTO:    BTC-USD
     - COMMODITY: GLD
     - FOREX:     UUP (USD index ETF proxy; DX-Y.NYB fails on some yfinance)
     - FUTURES:   CT=F
  2. Compute 30d rolling correlation matrix on log-returns.
  3. Compare current matrix vs baseline (avg of t-90..t-30 windows).
  4. Flag pairs crossing 0.5 (alert threshold) from <0.3 (baseline normal).
  5. Compute mean(|correlation|) for inverse-volatility sizing scalar.

Output: audit_dashboard/data/correlation_regime.json
  - per-pair current/baseline/delta/flagged
  - mean_abs_correlation (sizing-scalar input)
  - regime_state (NORMAL / ELEVATED / CRISIS)
  - alerts (list of pairs that just crossed)

NFA: diagnostic only. Sizing-scalar consumption belongs in a separate
sleeve-allocation gate (out of scope for this PR).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import numpy as np
    import yfinance as yf
except ImportError as e:
    print(f"ERROR: missing dependency: {e}", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent

# One representative ticker per asset class for cross-class correlation.
# Designed to be liquid, daily-resolvable on yfinance, and a reasonable
# proxy for the class's overall return character.
CLASS_TICKERS = {
    "EQUITY": "SPY",
    "ETF_SMALLCAP": "IWM",
    "BOND": "TLT",
    "CRYPTO": "BTC-USD",
    "COMMODITY_GOLD": "GLD",
    "FOREX_USD": "UUP",
    "FUTURES_COT": "CT=F",
}

# Regime thresholds (master-plan spec)
PAIR_ALERT_THRESHOLD = 0.5  # |corr| crossing this from baseline = alert
PAIR_BASELINE_CEILING = 0.3  # baseline expected to be <0.3 for true diversification
ELEVATED_MEAN_ABS = 0.35
CRISIS_MEAN_ABS = 0.55


def fetch_returns(tickers: dict, lookback_days: int = 150) -> dict:
    """Pull daily log-returns for each ticker. Returns dict[class] = list[float]."""
    out: dict = {}
    failed: list = []
    for cls, ticker in tickers.items():
        try:
            df = yf.download(ticker, period=f"{lookback_days}d",
                             interval="1d", progress=False, auto_adjust=True)
            if df is None or len(df) == 0:
                failed.append((cls, ticker, "empty"))
                continue
            closes = df["Close"].dropna().values.flatten()
            if len(closes) < 60:
                failed.append((cls, ticker, f"only {len(closes)} bars"))
                continue
            logret = np.diff(np.log(closes))
            out[cls] = logret.tolist()
        except Exception as exc:
            failed.append((cls, ticker, str(exc)[:80]))
    if failed:
        print(f"# fetch_returns: {len(failed)} fetch(es) failed:",
              file=sys.stderr)
        for cls, t, why in failed:
            print(f"#   {cls} ({t}): {why}", file=sys.stderr)
    return out


def _align(series: dict) -> tuple[list[str], np.ndarray]:
    """Align all series to the shortest length, return (class_order, matrix).

    Matrix shape: (T, K) where T = min length, K = num classes.
    """
    classes = sorted(series.keys())
    if not classes:
        return [], np.empty((0, 0))
    min_len = min(len(series[c]) for c in classes)
    # Take trailing min_len entries
    mat = np.column_stack([series[c][-min_len:] for c in classes])
    return classes, mat


def correlation_matrix(returns_mat: np.ndarray) -> np.ndarray:
    """Pearson correlation matrix. Returns K x K."""
    if returns_mat.shape[0] < 2 or returns_mat.shape[1] < 2:
        return np.zeros((returns_mat.shape[1], returns_mat.shape[1]))
    return np.corrcoef(returns_mat, rowvar=False)


def pair_summary(classes: list[str], M_curr: np.ndarray, M_base: np.ndarray) -> list[dict]:
    """For each unique pair, return current corr, baseline corr, delta, flagged."""
    out = []
    K = len(classes)
    for i in range(K):
        for j in range(i + 1, K):
            curr = float(M_curr[i, j])
            base = float(M_base[i, j])
            delta = curr - base
            flagged_curr = abs(curr) >= PAIR_ALERT_THRESHOLD
            baseline_normal = abs(base) <= PAIR_BASELINE_CEILING
            just_crossed = flagged_curr and baseline_normal
            out.append({
                "pair": f"{classes[i]}__{classes[j]}",
                "current_corr": round(curr, 4),
                "baseline_corr": round(base, 4),
                "delta": round(delta, 4),
                "abs_current": round(abs(curr), 4),
                "flagged": flagged_curr,
                "just_crossed": just_crossed,
            })
    out.sort(key=lambda r: r["abs_current"], reverse=True)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--current-window", type=int, default=30,
                   help="Days for current correlation window (default 30)")
    p.add_argument("--baseline-start", type=int, default=90,
                   help="Baseline starts this many days back (default 90)")
    p.add_argument("--baseline-end", type=int, default=30,
                   help="Baseline ends this many days back (default 30)")
    p.add_argument("--lookback-days", type=int, default=500,
                   help="Total yfinance lookback (default 500 — per swarm Q8 "
                        "consensus, 250-day floor needed before sizing on the "
                        "diversifier-intact claim; default raised from 150 -> 500 "
                        "to make 252-day rolling correlations the default, not "
                        "the exception. ~2 trading years.)")
    p.add_argument("--out", default="audit_dashboard/data/correlation_regime.json")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    print(f"# correlation-regime sidecar — current={args.current_window}d "
          f"baseline=[{args.baseline_start}d, {args.baseline_end}d]",
          file=sys.stderr)

    series = fetch_returns(CLASS_TICKERS, lookback_days=args.lookback_days)
    if len(series) < 3:
        print(f"# ERROR: only {len(series)} classes resolved; need >= 3",
              file=sys.stderr)
        sys.exit(1)

    classes, mat = _align(series)
    T = mat.shape[0]
    print(f"# aligned {len(classes)} classes x {T} obs", file=sys.stderr)

    if T < max(args.current_window, args.baseline_start):
        print(f"# WARN: T={T} < required for windows; clipping",
              file=sys.stderr)

    # Current window = trailing N days
    curr_slice = mat[-args.current_window:] if T >= args.current_window else mat
    # Baseline window = days [baseline_start, baseline_end) ago
    if T >= args.baseline_start:
        base_slice = mat[-args.baseline_start:-args.baseline_end] if args.baseline_end > 0 else mat[-args.baseline_start:]
    else:
        # Fallback: use the first half if not enough data
        half = T // 2
        base_slice = mat[:half] if half >= 5 else mat

    M_curr = correlation_matrix(curr_slice)
    M_base = correlation_matrix(base_slice)

    pairs = pair_summary(classes, M_curr, M_base)

    # Mean(|correlation|) excluding diagonal
    K = len(classes)
    if K >= 2:
        off_diag = []
        for i in range(K):
            for j in range(i + 1, K):
                off_diag.append(abs(M_curr[i, j]))
        mean_abs_curr = float(np.mean(off_diag)) if off_diag else 0.0
    else:
        mean_abs_curr = 0.0

    if mean_abs_curr >= CRISIS_MEAN_ABS:
        regime_state = "CRISIS"
    elif mean_abs_curr >= ELEVATED_MEAN_ABS:
        regime_state = "ELEVATED"
    else:
        regime_state = "NORMAL"

    alerts = [p for p in pairs if p["just_crossed"]]

    # Sleeve sizing scalar: inverse to mean_abs_correlation, clamped [0.4, 1.0]
    # so we never zero-out exposure entirely on a single signal.
    sizing_scalar = max(0.4, min(1.0, 1.0 - mean_abs_curr))

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "master-plan Action #5; Citadel R3 blind-spot",
        "config": {
            "current_window_days": args.current_window,
            "baseline_window_days": args.baseline_start - args.baseline_end,
            "pair_alert_threshold": PAIR_ALERT_THRESHOLD,
            "pair_baseline_ceiling": PAIR_BASELINE_CEILING,
            "regime_thresholds": {
                "elevated_mean_abs": ELEVATED_MEAN_ABS,
                "crisis_mean_abs": CRISIS_MEAN_ABS,
            },
        },
        "classes_resolved": classes,
        "class_to_ticker": {c: CLASS_TICKERS.get(c, "?") for c in classes},
        "n_observations_total": int(T),
        "current_correlation_matrix": [
            [round(float(M_curr[i, j]), 4) for j in range(K)]
            for i in range(K)
        ],
        "baseline_correlation_matrix": [
            [round(float(M_base[i, j]), 4) for j in range(K)]
            for i in range(K)
        ],
        "pairs": pairs,
        "summary": {
            "mean_abs_current": round(mean_abs_curr, 4),
            "regime_state": regime_state,
            "n_pairs_flagged": sum(1 for p in pairs if p["flagged"]),
            "n_pairs_just_crossed": len(alerts),
            "sleeve_sizing_scalar": round(sizing_scalar, 4),
        },
        "alerts": alerts,
        "consumption_notes": (
            "Multiply per-sleeve target allocation by `sleeve_sizing_scalar` "
            "before submission to the execution layer. A CRISIS regime "
            "should ALSO trigger the master HALT flag per memory "
            "feedback_halt_flag_must_be_hardcoded.md (refuse fills, not "
            "just log)."
        ),
        "nfa": "Diagnostic only. No automatic sizing change; consumer wiring deferred.",
    }

    if args.dry_run:
        print(json.dumps(payload, indent=2))
        return

    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"# wrote {out_path} ({out_path.stat().st_size:,} bytes)",
          file=sys.stderr)
    print(f"# regime={regime_state}  mean_abs={mean_abs_curr:.4f}  "
          f"sizing_scalar={sizing_scalar:.4f}  alerts={len(alerts)}",
          file=sys.stderr)
    if alerts:
        for a in alerts[:5]:
            print(f"#   ALERT {a['pair']}: {a['baseline_corr']:+.3f} -> "
                  f"{a['current_corr']:+.3f} (Δ={a['delta']:+.3f})",
                  file=sys.stderr)


if __name__ == "__main__":
    main()
