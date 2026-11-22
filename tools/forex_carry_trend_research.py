#!/usr/bin/env python3
"""R21 - FOREX cross-sectional momentum (63d lookback / 21d hold) full stats.

OPT-IN RESEARCH SIDECAR. No production wiring, no pick generation, no scoring
path. Reads only the on-disk FX spot cache (data/forex_rate_cache/*.csv) and
prints a JSON stat block. Importing this module has no side effects.

Pre-registered hypothesis (verbatim, do not edit after seeing results):

    "A daily cross-sectional FX strategy that goes long the top-quintile and
     short the bottom-quintile of pairs ranked by 63-day momentum, held 21 days,
     earns a positive net return after 2x realistic costs."

Pre-registered parameters (NOT tuned; reported even if the result is bad):
    LOOKBACK = 63 trading days
    HOLD     = 21 trading days
    REBALANCE= every 21 trading days (adjacent, non-overlapping windows)
    LONG/SHORT = top / bottom quintile (20%) of the cross-section, equal weight

Construction (no look-ahead):
  * At rebalance date D the signal is close(D)/close(D-63) - 1, known at the
    close of D.
  * The position is established at close(D) and the realised return is
    close(D+21)/close(D) - 1, signed +1 for the long leg and -1 for the short.
  * Every window is a full round trip per position, so the cost charged per
    pair-rebalance is one round trip (see COST_BP below).

Data: ECB reference-rate derived daily spot fixes (Frankfurter), 110 ordered
pairs over 11 currencies. They are mid/fix rates, not executable quotes, so the
cost assumption is the only place a spread enters.

Carry is NOT tested here: carry needs interest-rate differentials and no yield
curve exists on disk (data/rate_curve_cache does not exist - the same gap that
keeps BOND BLOCKED_DATA). Spot alone cannot price it. The verdict covers the
momentum leg only.

Usage:
    python3 tools/forex_carry_trend_research.py
    python3 tools/forex_carry_trend_research.py --json
    python3 tools/forex_carry_trend_research.py --shuffles 1000 --cost-bp 10
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "forex_rate_cache"

# ---------------------------------------------------------------------------
# Pre-registered parameters. Do not change after seeing results.
# ---------------------------------------------------------------------------
LOOKBACK = 63          # trading days of momentum
HOLD = 21              # trading days held
REBALANCE = 21         # trading days between rebalances (= HOLD: no overlap)
QUINTILE = 0.20        # long top 20%, short bottom 20%

# Cost per position round trip, in basis points of notional.
#
# Justification: the panel is ECB fix (mid) rates, so no spread is embedded.
# G10 spot round trip is ~2-5bp institutional and ~10-20bp retail. This
# universe is 110 ordered pairs over 11 currencies, including thin crosses
# with DKK/SEK/NOK legs, priced at a daily fix with no tick data to estimate a
# real spread. 10bp is the retail midpoint and the conservative choice for a
# non-institutional participant; the 2x case (20bp) covers the retail upper
# bound. A uniform per-position cost is correct here because every position is
# held a full window and closed at the next rebalance (one round trip each).
COST_BP = 10.0
COST_BP_2X = 20.0

SEED = 42              # house default
N_BOOTSTRAP = 10_000
N_SHUFFLES = 1_000     # spec asks >= 200
CI = 95.0


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------
def load_panel() -> tuple[list[str], list[str], np.ndarray]:
    """Load every CSV into a rectangular (dates x pairs) close matrix.

    Only rows actually present in the files are used - nothing is filled,
    interpolated, or forward-filled. A pair is kept only if its date list
    matches the common calendar exactly; otherwise it is dropped and reported.
    """
    files = sorted(DATA.glob("*.csv"))
    if not files:
        raise SystemExit(f"no CSVs in {DATA}")
    series: dict[str, dict[str, float]] = {}
    for f in files:
        with f.open() as fh:
            for row in csv.DictReader(fh):
                try:
                    v = float(row["close"])
                except (TypeError, ValueError):
                    continue
                if v > 0 and math.isfinite(v):
                    series.setdefault(f.stem, {})[row["date"]] = v
    # Common calendar = dates present in every pair (keeps the panel rectangular
    # without inventing a single value).
    common = set.intersection(*(set(d) for d in series.values()))
    dates = sorted(common)
    pairs = sorted(p for p, d in series.items() if all(x in d for x in dates))
    mat = np.array([[series[p][d] for p in pairs] for d in dates], dtype=float)
    return pairs, dates, mat


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------
def momentum(px: np.ndarray, i: int, lookback: int = LOOKBACK) -> np.ndarray:
    """63-day total return at index i (uses only closes through i)."""
    prev = px[i - lookback]
    with np.errstate(divide="ignore", invalid="ignore"):
        m = px[i] / prev - 1.0
    m[~np.isfinite(m)] = np.nan
    return m


def run_windows(px: np.ndarray, dates: list[str], pairs: list[str],
                ranks_fn=None) -> list[dict]:
    """Non-overlapping 21-day windows. ranks_fn(mom, valid, rng) -> order."""
    n_dates, n_pairs = px.shape
    k = max(1, int(round(QUINTILE * n_pairs)))
    recs: list[dict] = []
    wi = 0
    for i in range(LOOKBACK, n_dates - HOLD, REBALANCE):
        mom = momentum(px, i)
        valid = np.isfinite(mom) & (px[i] > 0) & (px[i + HOLD] > 0)
        idx = np.flatnonzero(valid)
        if idx.size < 2 * k:
            continue
        if ranks_fn is None:
            order = idx[np.argsort(-mom[idx], kind="stable")]
        else:
            order = ranks_fn(idx, n_pairs)
        longs, shorts = order[:k], order[-k:]
        fwd = px[i + HOLD] / px[i] - 1.0
        for p in longs:
            recs.append({"window": wi, "date": dates[i], "pair": pairs[p],
                         "side": 1, "gross_bp": float(fwd[p]) * 1e4})
        for p in shorts:
            recs.append({"window": wi, "date": dates[i], "pair": pairs[p],
                         "side": -1, "gross_bp": -float(fwd[p]) * 1e4})
        wi += 1
    return recs


def _random_ranks(rng: np.random.Generator):
    """Null: replace the momentum ranking with a random cross-sectional rank."""
    def fn(idx: np.ndarray, n_pairs: int) -> np.ndarray:
        return rng.permutation(idx)
    return fn


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------
def _mean_bp(vals: np.ndarray) -> float:
    return float(vals.mean()) if vals.size else float("nan")


def bootstrap_ci(vals: np.ndarray, rng: np.random.Generator,
                 n_boot: int = N_BOOTSTRAP) -> tuple[float, float]:
    """Percentile bootstrap CI on the mean (resamples pair-rebalances)."""
    if vals.size == 0:
        return (float("nan"), float("nan"))
    draws = rng.choice(vals, size=(n_boot, vals.size), replace=True).mean(axis=1)
    lo, hi = np.percentile(draws, [(100 - CI) / 2, 100 - (100 - CI) / 2])
    return float(lo), float(hi)


def cluster_bootstrap_ci(by_window: dict[int, np.ndarray],
                        rng: np.random.Generator, n_boot: int = N_BOOTSTRAP
                        ) -> tuple[float, float]:
    """Window-clustered bootstrap: resample whole windows (respects the shared
    market move inside a window, which the plain bootstrap ignores)."""
    wids = list(by_window)
    if not wids:
        return (float("nan"), float("nan"))
    sums = np.array([by_window[w].sum() for w in wids])
    cnts = np.array([by_window[w].size for w in wids])
    picks = rng.integers(0, len(wids), size=(n_boot, len(wids)))
    means = sums[picks].sum(axis=1) / cnts[picks].sum(axis=1)
    lo, hi = np.percentile(means, [(100 - CI) / 2, 100 - (100 - CI) / 2])
    return float(lo), float(hi)


def summarise(recs: list[dict], cost_bp: float, rng: np.random.Generator) -> dict:
    gross = np.array([r["gross_bp"] for r in recs])
    net = gross - cost_bp
    windows = np.array([r["window"] for r in recs])
    pairs = np.array([r["pair"] for r in recs])
    sides = np.array([r["side"] for r in recs])
    by_window = {w: net[windows == w] for w in np.unique(windows)}
    win_means = np.array([v.mean() for v in by_window.values()])
    pair_sum = defaultdict(float)
    for p, v in zip(pairs, net):
        pair_sum[p] += float(v)
    total_net = float(net.sum())
    total_gross = float(gross.sum())
    best_pair = max(pair_sum, key=pair_sum.get) if pair_sum else None
    # Share of total return from the single best pair. Only meaningful when the
    # total is positive; otherwise the ratio is not interpretable and is nulled.
    pair_share = (pair_sum[best_pair] / total_net
                  if best_pair and total_net > 0 else None)
    half = len(by_window) // 2
    ordered = [by_window[w] for w in sorted(by_window)]
    h1 = np.concatenate(ordered[:half]) if half else np.array([])
    h2 = np.concatenate(ordered[half:]) if ordered[half:] else np.array([])
    lo, hi = bootstrap_ci(net, rng)
    clo, chi = cluster_bootstrap_ci(by_window, rng)
    return {
        "n_pair_rebalances": int(net.size),
        "n_rebalance_windows": int(len(by_window)),
        "n_windows_positive": int((win_means > 0).sum()),
        "long_leg_mean_net_bp": _mean_bp(net[sides > 0]),
        "short_leg_mean_net_bp": _mean_bp(net[sides < 0]),
        "mean_gross_bp": _mean_bp(gross),
        "mean_net_bp": _mean_bp(net),
        "median_net_bp": float(np.median(net)),
        "ci95_net_bp": [lo, hi],
        "ci95_net_bp_window_clustered": [clo, chi],
        "ci_method": f"percentile bootstrap, {N_BOOTSTRAP} resamples, seed {SEED}",
        "cost_bp_1x": cost_bp,
        "mean_net_bp_1x": _mean_bp(net),
        "mean_net_bp_2x": _mean_bp(gross - 2 * cost_bp),
        "win_rate_net": float((net > 0).mean()),
        "win_rate_gross": float((gross > 0).mean()),
        "half_1_mean_net_bp": _mean_bp(h1),
        "half_2_mean_net_bp": _mean_bp(h2),
        "halves_both_positive": bool(h1.size and h2.size
                                    and h1.mean() > 0 and h2.mean() > 0),
        "worst_window_mean_net_bp": float(win_means.min()),
        "best_window_mean_net_bp": float(win_means.max()),
        "worst_pair_rebalance_net_bp": float(net.min()),
        "best_pair_rebalance_net_bp": float(net.max()),
        "total_gross_bp": total_gross,
        "total_net_bp": total_net,
        "cost_haircut_bp": total_gross - total_net,
        "best_pair": best_pair,
        "best_pair_sum_net_bp": pair_sum[best_pair] if best_pair else None,
        "best_pair_share_of_total_net": pair_share,
        "best_pair_share_note": ("undefined: total net return is negative, so a "
                                 "share of the total is not interpretable"
                                 if pair_share is None else ""),
        "n_pairs_traded": len(pair_sum),
        "top_pair_window_share": (float((pairs == best_pair).mean())
                                  if best_pair else None),
    }


def null_distribution(px: np.ndarray, dates: list[str], pairs: list[str],
                      cost_bp: float, n_shuffles: int, seed: int = SEED) -> dict:
    """Same procedure with random cross-sectional ranks instead of momentum."""
    rng = np.random.default_rng(seed)
    net_means, gross_means = [], []
    for _ in range(n_shuffles):
        recs = run_windows(px, dates, pairs, ranks_fn=_random_ranks(rng))
        g = np.array([r["gross_bp"] for r in recs])
        gross_means.append(float(g.mean()))
        net_means.append(float(g.mean()) - cost_bp)
    return {"gross_means": np.array(gross_means),
            "net_means": np.array(net_means), "n_shuffles": n_shuffles}


def percentile_of(value: float, dist: np.ndarray) -> float:
    return float((dist < value).mean() * 100.0)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
def run(cost_bp: float = COST_BP, n_shuffles: int = N_SHUFFLES,
        seed: int = SEED) -> dict:
    pairs, dates, px = load_panel()
    rng = np.random.default_rng(seed)
    recs = run_windows(px, dates, pairs)
    stats = summarise(recs, cost_bp, rng)

    null = null_distribution(px, dates, pairs, cost_bp, n_shuffles, seed)
    net_null = null["net_means"]
    gross_null = null["gross_means"]
    p_net = (1 + int((net_null >= stats["mean_net_bp"]).sum())) / (1 + n_shuffles)
    p_gross = (1 + int((gross_null >= stats["mean_gross_bp"]).sum())) / (1 + n_shuffles)

    gates = {
        "G1_ci_lower_gt_0_at_1x": stats["ci95_net_bp"][0] > 0,
        "G2_mean_gt_0_at_2x": stats["mean_net_bp_2x"] > 0,
        "G3_both_halves_positive": stats["halves_both_positive"],
        "G4_above_null_p95": stats["mean_net_bp"] > float(np.percentile(net_null, 95)),
        # None = not evaluable. With a negative total net return a share of the
        # total is meaningless, so this is reported as null, not as a pass or a
        # fail of the concentration check.
        "G5_no_pair_over_30pct": (None if stats["best_pair_share_of_total_net"] is None
                                  else stats["best_pair_share_of_total_net"] <= 0.30),
    }
    if stats["n_pair_rebalances"] < 200:
        verdict = "INSUFFICIENT_N"
    elif all(gates.values()):
        verdict = "CANDIDATE"
    elif gates["G1_ci_lower_gt_0_at_1x"] and gates["G4_above_null_p95"]:
        verdict = "WEAK"
    else:
        verdict = "KILL"

    return {
        "round": "R21",
        "class": "FOREX",
        "mechanism": "FX cross-sectional momentum (63d lookback, 21d hold, "
                     "quintile long/short), net of spot round-trip cost",
        "hypothesis": "A daily cross-sectional FX strategy that goes long the "
                      "top-quintile and short the bottom-quintile of pairs "
                      "ranked by 63-day momentum, held 21 days, earns a "
                      "positive net return after 2x realistic costs.",
        "carry_note": "Carry is not tested: it needs interest-rate differentials "
                      "and no yield curve exists on disk (data/rate_curve_cache "
                      "is absent - the same gap that blocks BOND).",
        "preregistered": {"lookback_days": LOOKBACK, "hold_days": HOLD,
                          "rebalance_days": REBALANCE, "quintile": QUINTILE,
                          "seed": seed, "n_bootstrap": N_BOOTSTRAP,
                          "n_shuffles": n_shuffles},
        "panel": {"n_pairs": len(pairs), "n_dates": len(dates),
                  "first_date": dates[0], "last_date": dates[-1],
                  "source": "data/forex_rate_cache/*.csv (ECB fix via Frankfurter)",
                  "missing_values_filled": 0,
                  "caveat": "110 ordered pairs over 11 currencies means every "
                            "currency appears in both directions (EURUSD and "
                            "USDEUR are exact inverses), so breadth is 55 "
                            "independent crosses, not 110. The pre-registered "
                            "test uses all 110 as instructed; leg breakdown "
                            "shows what that does to exposure."},
        "cost": {"bp_round_trip_1x": cost_bp, "bp_round_trip_2x": 2 * cost_bp,
                 "justification": "ECB fix is a mid rate; G10 spot round trip is "
                                  "2-5bp institutional / 10-20bp retail. 110 "
                                  "pairs over 11 currencies include thin "
                                  "DKK/SEK/NOK crosses, priced at a daily fix "
                                  "with no tick data. 10bp = retail midpoint, "
                                  "conservative for a non-institutional "
                                  "participant; 20bp covers the retail upper "
                                  "bound. One round trip per position per window."},
        "stats": stats,
        "null": {"n_shuffles": n_shuffles, "seed": seed,
                 "mean_net_bp": float(net_null.mean()),
                 "sd_net_bp": float(net_null.std(ddof=1)),
                 "p05_net_bp": float(np.percentile(net_null, 5)),
                 "p95_net_bp": float(np.percentile(net_null, 95)),
                 "max_net_bp": float(net_null.max()),
                 "mean_gross_bp": float(gross_null.mean()),
                 "observed_percentile_net": percentile_of(stats["mean_net_bp"], net_null),
                 "observed_percentile_gross": percentile_of(stats["mean_gross_bp"],
                                                            gross_null),
                 "empirical_p_net": p_net, "empirical_p_gross": p_gross},
        "gates": gates,
        "verdict": verdict,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", dest="as_json", action="store_true")
    ap.add_argument("--cost-bp", type=float, default=COST_BP)
    ap.add_argument("--shuffles", type=int, default=N_SHUFFLES)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", type=str, default="")
    args = ap.parse_args()
    res = run(args.cost_bp, args.shuffles, args.seed)
    text = json.dumps(res, indent=2)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
