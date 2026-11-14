#!/usr/bin/env python3
"""
Fundamental/Earnings Walk-Forward Ranker — MINIMAL, HONEST scaffold.

The ML audit found no *proven* fundamental methodology in this repo. This tool
is a deliberately small, correct-by-construction scaffold for validating the
*idea* of a cross-sectional fundamental ranker. It is a tool for truth-seeking,
not for producing a profitable strategy: when the data has no real signal, it
reports that instead of forcing a positive result.

Core guarantees
---------------
1. Correct by construction (no leakage):
   - Every row is a *decision point* (date, ticker) with fundamental features
     known AT that date, plus the realized ``forward_return`` label (the outcome
     over the next horizon, never used as an input feature).
   - Feature standardization (z-score) is fitted on the TRAINING window only and
     applied to OOS, so the OOS scores never borrow statistics from the future.
   - Chronological walk-forward: training is strictly BEFORE every OOS window.

2. Chronological walk-forward with true OOS:
   - Unique dates are split into an expanding train plus ``n_windows`` contiguous,
     disjoint OOS windows. For each window the composite score model is calibrated
     on data strictly before the window, then evaluated on the window.

3. Honest reporting:
   - Wilson binomial 95% CI for the top-quantile win rate. If the CI contains
     0.50 (or the lower bound is <= 0.50) the harness says "no edge detected".

Data
----
By default a SMALL SYNTHETIC MOCK dataset is generated (clearly labeled below).
No real market data is invented. To supply your own data, pass a CSV with at
least the columns: date, ticker, forward_return, plus one or more fundamental
feature columns (those starting with ``f_`` are treated as features; a
``--features`` list may be given explicitly).
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path

FEATURE_COLS = ["f_pe", "f_eps_growth", "f_roic", "f_d2e", "f_momentum"]
HORIZON_DAYS = 21
INIT_TRAIN_FRAC = 0.4
N_WINDOWS = 4
N_QUANTILES = 5
MIN_TOP_N = 20


def _wilson_ci(k: int, n: int, z: float = 1.96):
    """Wilson score interval for a binomial proportion."""
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (centre - half, centre + half)


def _fit_zscaler(train_df, features):
    """Fit per-feature mean/std on the TRAINING frame only."""
    means = {c: float(train_df[c].mean()) for c in features}
    stds = {c: float(train_df[c].std(ddof=0)) for c in features}
    stds = {c: (s if s and s > 1e-12 else 1.0) for c, s in stds.items()}
    return means, stds


def _score(df, means, stds, weights, features):
    """Apply train-fitted z-transform + composite weights (no future stats)."""
    total = 0.0
    for c in features:
        z = (df[c].astype(float) - means[c]) / stds[c]
        total = total + weights[c] * z
    return total


@dataclass
class WindowReport:
    start: str
    end: str
    n_dates: int
    n_obs: int
    top_n: int
    top_wr: float
    mean_fwd_top: float
    mean_fwd_bottom: float
    spread: float


@dataclass
class OverallReport:
    top_n: int
    top_wins: int
    top_wr: float
    ci_lo: float
    ci_hi: float
    ci_includes_050: bool
    edge_detected: bool
    windows: list
    verdict: str


def build_mock_dataset(n_tickers: int = 40, n_dates: int = 120,
                       seed: int = 0, signal: bool = False):
    """
    SMALL SYNTHETIC MOCK dataset (clearly labeled, no real market data).

    Features are iid ~ N(0,1). When ``signal=False`` (the honest default)
    ``forward_return`` is pure noise ~ N(0, 0.03), independent of every feature,
    so there is genuinely no edge. When ``signal=True`` a linear combination of
    the features is planted into forward_return so the harness *should* detect
    an edge (used only to prove the harness isn't broken).
    """
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n_dates, freq="D")
    rows = []
    for date in dates:
        n = n_tickers
        feats = {c: rng.normal(0, 1, n) for c in FEATURE_COLS}
        if signal:
            z = (sum(feats[c] for c in FEATURE_COLS) / math.sqrt(len(FEATURE_COLS)))
            fwd = 0.02 * z + rng.normal(0, 0.02, n)
        else:
            fwd = rng.normal(0, 0.03, n)
        for i in range(n):
            row = {"date": date.strftime("%Y-%m-%d"),
                   "ticker": f"T{i:03d}"}
            for c in FEATURE_COLS:
                row[c] = float(feats[c][i])
            row["forward_return"] = float(fwd[i])
            rows.append(row)
    return pd.DataFrame(rows)


def _chronological_splits(df, n_windows: int = N_WINDOWS,
                          init_train_frac: float = INIT_TRAIN_FRAC,
                          features=FEATURE_COLS):
    """
    Return list of (train_df, oos_df) walk-forward splits.

    Training for each OOS window is STRICTLY before the window start: the train
    set never contains a row whose date is >= the window's first date. Windows
    are contiguous and disjoint; training expands as the origin moves forward.
    """
    import numpy as np

    dates = sorted(df["date"].unique())
    n = len(dates)
    init_train = max(1, int(n * init_train_frac))
    oos_dates = dates[init_train:]
    windows = np.array_split(oos_dates, n_windows)
    splits = []
    for w in windows:
        if len(w) == 0:
            continue
        start = w[0]
        train_mask = df["date"] < start
        oos_mask = df["date"].isin(list(w))
        splits.append((df.loc[train_mask].copy(), df.loc[oos_mask].copy()))
    return splits


def _rank_window(oos_df, means, stds, weights, features, n_quantiles):
    """Per-rebalance-date cross-sectional sort; pool top-quantile outcomes."""
    oos = oos_df.copy()
    oos["_score"] = _score(oos, means, stds, weights, features)
    top = []
    bottom = []
    for date, grp in oos.groupby("date"):
        grp = grp.sort_values("_score", ascending=False).reset_index(drop=True)
        cut = max(1, int(math.ceil(len(grp) / n_quantiles)))
        top.append(grp.iloc[:cut])
        bottom.append(grp.iloc[-cut:])
    top = __concat(top)
    bottom = __concat(bottom)
    if len(top) == 0 or len(bottom) == 0:
        return None
    fwd_top = top["forward_return"].to_numpy()
    fwd_bottom = bottom["forward_return"].to_numpy()
    return WindowReport(
        start=str(oos["date"].min()),
        end=str(oos["date"].max()),
        n_dates=int(oos["date"].nunique()),
        n_obs=int(len(oos)),
        top_n=int(len(fwd_top)),
        top_wr=float((fwd_top > 0).mean()),
        mean_fwd_top=float(fwd_top.mean()),
        mean_fwd_bottom=float(fwd_bottom.mean()),
        spread=float(fwd_top.mean() - fwd_bottom.mean()),
    )


def __concat(frames):
    import pandas as pd

    if frames:
        return pd.concat(frames)
    return pd.DataFrame(columns=["date", "ticker", "forward_return"])


def run(df, features=FEATURE_COLS, n_windows: int = N_WINDOWS,
        n_quantiles: int = N_QUANTILES, weights=None, min_top_n: int = MIN_TOP_N):
    """Full walk-forward pipeline -> OverallReport with honest verdict."""
    import numpy as np

    if weights is None:
        weights = {c: 1.0 for c in features}

    splits = _chronological_splits(df, n_windows=n_windows)
    reports = []
    top_wins = 0
    top_n = 0
    for train, oos in splits:
        if len(train) == 0 or len(oos) == 0:
            continue
        means, stds = _fit_zscaler(train, features)
        rep = _rank_window(oos, means, stds, weights, features, n_quantiles)
        if rep is None:
            continue
        reports.append(rep)
        top_wins += int(round(rep.top_wr * rep.top_n))
        top_n += rep.top_n

    if top_n == 0:
        ci_lo, ci_hi = 0.0, 1.0
    else:
        ci_lo, ci_hi = _wilson_ci(top_wins, top_n)
    ci_includes_050 = ci_lo <= 0.50 <= ci_hi
    edge = (top_n >= min_top_n) and (ci_lo > 0.50)

    if edge:
        verdict = ("EDGE DETECTED: top-quantile WR lower bound exceeds 50% "
                   "(binomial 95% CI excludes coin-flip).")
    else:
        verdict = ("NO EDGE DETECTED: the binomial 95% CI for the top-quantile "
                   "win rate includes 50% (or sample too small). The mock/feature "
                   "set carries no proven signal; do not trade on it.")

    return OverallReport(
        top_n=top_n,
        top_wins=top_wins,
        top_wr=(top_wins / top_n) if top_n else 0.0,
        ci_lo=ci_lo,
        ci_hi=ci_hi,
        ci_includes_050=ci_includes_050,
        edge_detected=edge,
        windows=reports,
        verdict=verdict,
    )


def format_report(rep: OverallReport) -> str:
    lines = []
    lines.append("=" * 72)
    lines.append("FUNDAMENTAL RANKER — WALK-FORWARD OOS REPORT")
    lines.append("=" * 72)
    lines.append("")
    lines.append("Per-window OOS (chronological, training strictly before each window):")
    lines.append(f"  {'window':>14} {'n_dates':>8} {'n_obs':>7} "
                 f"{'top_n':>6} {'top_WR':>7} {'fwd_top':>9} "
                 f"{'fwd_bot':>9} {'spread':>8}")
    for w in rep.windows:
        lines.append(f"  {w.start}..{w.end:>14} {w.n_dates:>8} {w.n_obs:>7} "
                     f"{w.top_n:>6} {w.top_wr:>7.3f} {w.mean_fwd_top:>9.4f} "
                     f"{w.mean_fwd_bottom:>9.4f} {w.spread:>8.4f}")
    lines.append("")
    lines.append("Aggregate (all OOS windows combined):")
    lines.append(f"  top-quantile positions   : {rep.top_n}")
    lines.append(f"  top-quantile wins        : {rep.top_wins}")
    lines.append(f"  top-quantile WR          : {rep.top_wr:.3f}")
    lines.append(f"  binomial 95% CI          : [{rep.ci_lo:.3f}, {rep.ci_hi:.3f}]")
    lines.append(f"  CI includes 50% ?        : {rep.ci_includes_050}")
    lines.append("")
    lines.append(f"VERDICT: {rep.verdict}")
    lines.append("=" * 72)
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--csv", help="Optional path to your own CSV (date, ticker, "
                                   "forward_return, plus feature columns).")
    ap.add_argument("--features", nargs="*", default=FEATURE_COLS,
                    help="Fundamental feature column names (default built-in mock).")
    ap.add_argument("--signal", action="store_true",
                    help="Plant a synthetic signal in the mock (testing only).")
    ap.add_argument("--windows", type=int, default=N_WINDOWS)
    ap.add_argument("--quantiles", type=int, default=N_QUANTILES)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)

    if args.csv:
        import pandas as pd

        df = pd.read_csv(args.csv)
    else:
        df = build_mock_dataset(seed=args.seed, signal=args.signal)

    rep = run(df, features=args.features, n_windows=args.windows,
              n_quantiles=args.quantiles)
    print(format_report(rep))
    if args.csv:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
