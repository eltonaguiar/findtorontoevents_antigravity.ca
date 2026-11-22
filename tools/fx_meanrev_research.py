#!/usr/bin/env python3
"""R22 - FOREX cross-sectional short-horizon MEAN-REVERSION (5d formation / 5d hold).

OPT-IN RESEARCH SIDECAR. No production wiring, no pick generation, no scoring
path. Reads only the on-disk FX spot cache (data/forex_rate_cache/*.csv) and
prints a JSON stat block. Importing this module has no side effects.

Pre-registered hypothesis (verbatim, do not edit after seeing results):

    "A daily cross-sectional FX strategy that goes long the worst-performing
     quintile and short the best-performing quintile by 5-day return, held 5
     days, earns a positive net return after 2x realistic costs."

Pre-registered parameters (NOT tuned; reported even if the result is bad):
    LOOKBACK = 5 trading days   (formation)
    HOLD     = 5 trading days
    REBALANCE= every 5 trading days (adjacent, non-overlapping windows)
    LONG/SHORT = bottom / top quintile (20%) of the cross-section, equal weight

This is NOT a re-tune of R21 (63d momentum / 21d hold). It tests the opposite
economic claim: that FX at short horizons overreacts and mean-reverts
(liquidity provision), rather than trends. A pass here and a fail in R21 would
be two different mechanisms, not two settings of one knob.

Construction (no look-ahead):
  * At rebalance date D the signal is close(D)/close(D-5) - 1, known at the
    close of D.
  * The position is established at close(D) and the realised return is
    close(D+5)/close(D) - 1, signed +1 for the long leg and -1 for the short.
  * Every window is a full round trip per position, so the cost charged per
    pair-rebalance is one round trip (see COST_BP below).

Universe:
  * PRIMARY ("dedup"): one orientation per unordered currency pair -- the
    alphabetically canonical direction (e.g. AUDCAD kept, CADAUD dropped).
    11 currencies -> C(11,2) = 55 independent crosses. The 110 ordered pairs
    are exact inverses pairwise, so ranking all 110 double-counts every bet.
  * SECONDARY ("full"): all 110 ordered pairs, as R21 used, so the effect of
    the inverse-pair doubling is visible. Gate G6 requires the two to agree in
    sign; if they do not, the effect is a double-counting artefact.

Data: ECB reference-rate derived daily spot fixes (Frankfurter), 110 ordered
pairs over 11 currencies. They are mid/fix rates, not executable quotes, so the
cost assumption is the only place a spread enters.

Usage:
    python3 tools/fx_meanrev_research.py
    python3 tools/fx_meanrev_research.py --json
    python3 tools/fx_meanrev_research.py --shuffles 1000 --cost-bp 10 --out reports/fx_meanrev_20261122.json
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "forex_rate_cache"

# ---------------------------------------------------------------------------
# Pre-registered parameters. Do not change after seeing results.
# ---------------------------------------------------------------------------
LOOKBACK = 5           # trading days of formation (short-horizon reversal)
HOLD = 5               # trading days held
REBALANCE = 5          # trading days between rebalances (= HOLD: no overlap)
QUINTILE = 0.20        # long bottom 20%, short top 20%

# Cost per position round trip, in basis points of notional.
#
# Justification: the panel is ECB fix (mid) rates, so no spread is embedded.
# G10 spot round trip is ~2-5bp institutional and ~10-20bp retail. This
# universe is 11 currencies including thin crosses with DKK/SEK/NOK legs,
# priced at a daily fix with no tick data to estimate a real spread. 10bp is
# the retail midpoint and the conservative choice for a non-institutional
# participant; the 2x case (20bp) covers the retail upper bound. A uniform
# per-position cost is correct here because every position is held a full
# window and closed at the next rebalance (one round trip each).
#
# This is DELIBERATELY the same cost model as R21 so the two rounds are
# directly comparable rather than each arguing its own number.
COST_BP = 10.0
COST_BP_2X = 20.0

SEED = 42              # house default
N_BOOTSTRAP = 10_000
N_SHUFFLES = 1_000
CI = 95.0
MIN_WINDOWS = 200      # below this the verdict is INSUFFICIENT_N


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


def dedup_indices(pairs: list[str]) -> list[int]:
    """Indices of one orientation per unordered currency pair.

    Canonical orientation = the alphabetical order of the two 3-letter codes
    (AUDCAD kept, CADAUD dropped). With 11 currencies this leaves 55 crosses.
    """
    seen: dict[tuple[str, str], int] = {}
    for j, p in enumerate(pairs):
        a, b = p[:3], p[3:]
        key = (a, b) if a < b else (b, a)
        if key not in seen:
            seen[key] = j
    return [seen[k] for k in sorted(seen)]


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------
def formation(px: np.ndarray, i: int, lookback: int = LOOKBACK) -> np.ndarray:
    """5-day total return at index i (uses only closes through i)."""
    prev = px[i - lookback]
    with np.errstate(divide="ignore", invalid="ignore"):
        m = px[i] / prev - 1.0
    m[~np.isfinite(m)] = np.nan
    return m


def run_windows(px: np.ndarray, dates: list[str], pairs: list[str],
                ranks_fn=None) -> list[dict]:
    """Non-overlapping 5-day windows, mean-reversion legs.

    longs = worst quintile (lowest 5d return), shorts = best quintile.
    ranks_fn(idx, n_pairs) -> permuted order, used for the null.
    """
    n_dates, n_pairs = px.shape
    k = max(1, int(round(QUINTILE * n_pairs)))
    recs: list[dict] = []
    wi = 0
    for i in range(LOOKBACK, n_dates - HOLD, REBALANCE):
        mom = formation(px, i)
        valid = np.isfinite(mom) & (px[i] > 0) & (px[i + HOLD] > 0)
        idx = np.flatnonzero(valid)
        if idx.size < 2 * k:
            continue
        if ranks_fn is None:
            # ascending: worst performers first
            order = idx[np.argsort(mom[idx], kind="stable")]
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
    """Null: replace the formation ranking with a random cross-sectional rank."""
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
    # Always-defined concentration: share of gross absolute P&L.
    abs_total = sum(abs(v) for v in pair_sum.values())
    abs_share = (abs(pair_sum[best_pair]) / abs_total
                 if best_pair and abs_total > 0 else None)
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
        "positions_per_window": 2 * max(1, int(round(QUINTILE * len(set(pairs))))),
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
        "best_pair_share_of_abs_pnl": abs_share,
        "best_pair_share_note": ("undefined: total net return is negative, so a "
                                 "share of the total is not interpretable"
                                 if pair_share is None else ""),
        "n_pairs_traded": len(pair_sum),
        "top_pair_window_share": (float((pairs == best_pair).mean())
                                  if best_pair else None),
    }


def null_distribution(px: np.ndarray, dates: list[str], pairs: list[str],
                      cost_bp: float, n_shuffles: int, seed: int = SEED) -> dict:
    """Same procedure with random cross-sectional ranks instead of the 5d signal."""
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


def run_universe(px: np.ndarray, dates: list[str], pairs: list[str],
                 label: str, cost_bp: float, n_shuffles: int,
                 seed: int) -> dict:
    """One full measurement pass on a given universe."""
    rng = np.random.default_rng(seed)
    recs = run_windows(px, dates, pairs)
    stats = summarise(recs, cost_bp, rng)
    null = null_distribution(px, dates, pairs, cost_bp, n_shuffles, seed)
    net_null, gross_null = null["net_means"], null["gross_means"]
    p_net = (1 + int((net_null >= stats["mean_net_bp"]).sum())) / (1 + n_shuffles)
    p_gross = (1 + int((gross_null >= stats["mean_gross_bp"]).sum())) / (1 + n_shuffles)
    return {
        "universe": label,
        "n_pairs": len(pairs),
        "pairs": pairs,
        "stats": stats,
        "null": {"n_shuffles": n_shuffles, "seed": seed,
                 "mean_net_bp": float(net_null.mean()),
                 "sd_net_bp": float(net_null.std(ddof=1)),
                 "p05_net_bp": float(np.percentile(net_null, 5)),
                 "p95_net_bp": float(np.percentile(net_null, 95)),
                 "max_net_bp": float(net_null.max()),
                 "mean_gross_bp": float(gross_null.mean()),
                 "observed_percentile_net": percentile_of(stats["mean_net_bp"],
                                                          net_null),
                 "observed_percentile_gross": percentile_of(stats["mean_gross_bp"],
                                                            gross_null),
                 "empirical_p_net": p_net, "empirical_p_gross": p_gross},
    }


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
def run(cost_bp: float = COST_BP, n_shuffles: int = N_SHUFFLES,
        seed: int = SEED) -> dict:
    all_pairs, dates, px = load_panel()
    keep = dedup_indices(all_pairs)
    dedup_pairs = [all_pairs[j] for j in keep]
    px_dedup = px[:, keep]

    dedup = run_universe(px_dedup, dates, dedup_pairs, "dedup_55", cost_bp,
                         n_shuffles, seed)
    full = run_universe(px, dates, all_pairs, "full_110", cost_bp,
                        n_shuffles, seed)

    s = dedup["stats"]
    n = dedup["null"]
    sign_agree = bool(np.sign(s["mean_net_bp"]) == np.sign(full["stats"]["mean_net_bp"])
                      and s["mean_net_bp"] != 0)
    gates = {
        "G1_ci_lower_gt_0_at_1x": s["ci95_net_bp"][0] > 0,
        "G2_mean_gt_0_at_2x": s["mean_net_bp_2x"] > 0,
        "G3_both_halves_positive": s["halves_both_positive"],
        "G4_above_null_p95": s["mean_net_bp"] > n["p95_net_bp"],
        # None = not evaluable (negative total net: a share of the total is
        # meaningless). Reported as n/a, not as a pass.
        "G5_no_pair_over_30pct": (None if s["best_pair_share_of_total_net"] is None
                                  else s["best_pair_share_of_total_net"] <= 0.30),
        "G6_dedup_full_same_sign": sign_agree,
    }
    if s["n_rebalance_windows"] < MIN_WINDOWS:
        verdict = "INSUFFICIENT_N"
    elif all(v is True for v in gates.values()):
        verdict = "CANDIDATE"
    elif gates["G1_ci_lower_gt_0_at_1x"] and gates["G4_above_null_p95"]:
        verdict = "WEAK"
    else:
        verdict = "KILL"

    return {
        "round": "R22",
        "class": "FOREX",
        "mechanism": "FX cross-sectional short-horizon mean-reversion "
                     "(5d formation, 5d hold, quintile long worst / short "
                     "best), net of spot round-trip cost",
        "hypothesis": "A daily cross-sectional FX strategy that goes long the "
                      "worst-performing quintile and short the best-performing "
                      "quintile by 5-day return, held 5 days, earns a positive "
                      "net return after 2x realistic costs.",
        "relationship_to_r21": "R21 tested FX momentum (63d lookback, 21d hold) "
                               "and killed it (mean net -36.88bp, 0.0 percentile "
                               "of null). R22 tests the opposite economic claim "
                               "at a short horizon: overreaction / liquidity "
                               "provision. Different mechanism, not a re-tune: "
                               "the sign of the expected edge is inverted and "
                               "the horizon is 12x shorter, both fixed a priori.",
        "preregistered": {"lookback_days": LOOKBACK, "hold_days": HOLD,
                          "rebalance_days": REBALANCE, "quintile": QUINTILE,
                          "seed": seed, "n_bootstrap": N_BOOTSTRAP,
                          "n_shuffles": n_shuffles, "cost_bp_1x": cost_bp},
        "panel": {"n_pairs_full": len(all_pairs), "n_pairs_dedup": len(dedup_pairs),
                  "n_dates": len(dates), "first_date": dates[0],
                  "last_date": dates[-1],
                  "source": "data/forex_rate_cache/*.csv (ECB fix via Frankfurter)",
                  "missing_values_filled": 0,
                  "dedup_rule": "keep the alphabetically canonical orientation of "
                                "each unordered currency pair (AUDCAD kept, "
                                "CADAUD dropped); 11 currencies -> 55 crosses"},
        "cost": {"bp_round_trip_1x": cost_bp, "bp_round_trip_2x": 2 * cost_bp,
                 "justification": "ECB fix is a mid rate; G10 spot round trip is "
                                  "2-5bp institutional / 10-20bp retail. Pairs "
                                  "include thin DKK/SEK/NOK crosses, priced at a "
                                  "daily fix with no tick data. 10bp = retail "
                                  "midpoint, conservative for a non-institutional "
                                  "participant; 20bp covers the retail upper "
                                  "bound. Deliberately identical to R21 so the "
                                  "rounds are comparable."},
        "universes": {"primary": dedup, "secondary": full},
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
