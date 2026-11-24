"""H-232 — inverse-volatility POSITION SIZING inside the H-201 top-3 basket (item 15).

Pre-registered in reports/hypothesis_registry.json and committed BEFORE this file was
first executed (commit b9ff7faab3e). Parameters are frozen there; nothing here is
tuned after seeing output.

The question, stated precisely. Item 15 was left PARTIAL because two different claims
were being conflated:

  (a) strategy-to-benchmark VOL MATCHING does not rescue H-201  -> already measured by
      the harness (`matched_ci_lb_bps` = -0.533). That is a leverage question: scale
      the whole strategy to SPY's volatility and the lower bound goes negative.
  (b) position-level INVERSE-VOL SIZING inside the basket         -> measured here.
      Exposure stays at 1.0, the three selected names are the same, only the split
      between them changes. This is a risk-allocation question, not a leverage one.

The registered statistic is the paired difference against H-201 equal weight on the
SAME days. A point estimate is not evidence (standing rule), so the headline is a
paired block-bootstrap CI on (invvol - equal_weight); the strategy-level gates are
reported too, unchanged from every other cell.

Also computed, because a win without it would be unattributable:
  * random top-3 selection with the SAME inverse-vol sizing (2000 draws) — separates
    the effect of SIZING from the effect of SELECTION.
  * DSR against the search including this cell (n_trials 30, not the old 29), so the
    bar is raised rather than lowered by adding a trial.

Usage:
  python3 tools/xsmom_invvol_variant.py --out reports/h232_invvol_2026-11-22.json \
      --md reports/h232_invvol_2026-11-22.md
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from per_class_edge_harness import (  # noqa: E402
    UNIVERSES, block_bootstrap, dsr, expected_max_sr, fetch, matched_vol_block,
    sharpe, xsmom,
)

LOOKBACK = 126
TOP_K = 3
REBAL = 21
COST_BPS = 10            # per side, identical to H-201
N_RANDOM = 2000
N_TRIALS_WITH_H232 = 30  # 29 declared + this one; raised, never lowered


def _weights(mom_row: pd.Series, vol_row: pd.Series, top_k: int) -> tuple[list, np.ndarray]:
    pick = list(mom_row.nlargest(top_k).index)
    sv = vol_row[pick].astype(float).where(lambda s: np.isfinite(s) & (s > 0))
    if sv.notna().sum() < len(pick):
        return pick, np.full(len(pick), 1.0 / len(pick))
    inv = 1.0 / sv.clip(lower=1e-6)
    return pick, (inv / inv.sum()).to_numpy()


def xsmom_invvol(closes: pd.DataFrame, lookback: int = LOOKBACK, top_k: int = TOP_K,
                 cost_bps: float = COST_BPS, rebal_days: int = REBAL
                 ) -> tuple[pd.Series, pd.DataFrame]:
    """Top-k momentum with weights inversely proportional to trailing realised vol.

    Selection is byte-for-byte the H-201 rule: trailing `lookback`-day return, every
    `rebal_days`, take the `top_k` largest. Only the weight vector differs.
    """
    rets = closes.pct_change(fill_method=None)
    mom = closes.pct_change(lookback, fill_method=None)
    vol = rets.rolling(lookback, min_periods=lookback // 2).std(ddof=1)
    w = pd.DataFrame(np.nan, index=closes.index, columns=closes.columns)
    for i in range(lookback + 1, len(closes), rebal_days):
        row = mom.iloc[i].dropna()
        if len(row) < top_k:
            continue
        pick, weight = _weights(row, vol.iloc[i], top_k)
        w.iloc[i, :] = 0.0
        for name, wt in zip(pick, weight):
            w.iloc[i, w.columns.get_loc(name)] = float(wt)
    w = w.ffill().fillna(0.0)
    exposure = w.sum(axis=1)
    if float(exposure.max()) > 1.0001:
        raise AssertionError(f"invvol exposure {float(exposure.max()):.4f} > 1 — weights leaked")
    gross = (w.shift(1) * rets).sum(axis=1)
    turn = (w - w.shift(1)).abs().sum(axis=1)
    return (gross - turn * cost_bps / 1e4).fillna(0.0), w


def turnover_fraction(w: pd.DataFrame) -> pd.Series:
    return (w - w.shift(1)).abs().sum(axis=1)


def random_selection_null(closes: pd.DataFrame, n_draws: int = N_RANDOM,
                          seed: int = 11) -> np.ndarray:
    """Mean daily net return of inverse-vol sizing with RANDOM top-3 selection.

    This is the control that separates sizing from selection: it holds the sizing
    rule, the exposure, the rebalance dates and the cost model fixed and replaces
    only the momentum ranking with a coin flip.
    """
    rets = closes.pct_change(fill_method=None)
    vol = rets.rolling(LOOKBACK, min_periods=LOOKBACK // 2).std(ddof=1)
    names = list(closes.columns)
    rng = np.random.default_rng(seed)
    out = np.empty(n_draws)
    for d in range(n_draws):
        w = pd.DataFrame(np.nan, index=closes.index, columns=closes.columns)
        for i in range(LOOKBACK + 1, len(closes), REBAL):
            pick = list(rng.choice(names, size=TOP_K, replace=False))
            sv = vol.iloc[i][pick].astype(float).clip(lower=1e-6)
            weight = ((1.0 / sv) / (1.0 / sv).sum()).to_numpy()
            w.iloc[i, :] = 0.0
            for name, wt in zip(pick, weight):
                w.iloc[i, w.columns.get_loc(name)] = float(wt)
        w = w.ffill().fillna(0.0)
        gross = (w.shift(1) * rets).sum(axis=1)
        net = (gross - turnover_fraction(w) * COST_BPS / 1e4).fillna(0.0)
        out[d] = float(net.mean())
    return out


def paired_ci(a: np.ndarray, b: np.ndarray, n_boot: int = 5000, seed: int = 11) -> dict:
    """Paired block-bootstrap CI of mean(a - b). Both legs on the same days."""
    d = a - b
    T = len(d)
    rng = np.random.default_rng(seed)
    block = max(2, int(round(T ** (1.0 / 3.0))))
    nb = math.ceil(T / block)
    means = np.empty(n_boot)
    for k in range(n_boot):
        starts = rng.integers(0, T, size=nb)
        idx = np.concatenate([np.arange(s, s + block) % T for s in starts])[:T]
        means[k] = d[idx].mean()
    lo, hi = np.percentile(means, [2.5, 97.5])
    sd = float(d.std(ddof=1))
    return {"mean_bps": round(1e4 * float(d.mean()), 3),
            "ci_lb_bps": round(1e4 * float(lo), 3),
            "ci_ub_bps": round(1e4 * float(hi), 3),
            "t": round(float(d.mean() / (sd / math.sqrt(T))), 3) if sd > 0 else None,
            "excludes_zero": bool(lo > 0 or hi < 0)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reports/h232_invvol_2026-11-22.json")
    ap.add_argument("--md", default="reports/h232_invvol_2026-11-22.md")
    ap.add_argument("--n-trials", type=int, default=N_TRIALS_WITH_H232)
    args = ap.parse_args()

    syms = UNIVERSES["EQUITY"]
    data = {s: fetch(s) for s in syms}
    data = {s: d for s, d in data.items() if d is not None and len(d) > 200}
    closes = pd.concat({s: d["close"] for s, d in data.items()}, axis=1).dropna(how="all")
    print(f"universe {len(data)}/{len(syms)} names, {closes.index.min().date()} -> "
          f"{closes.index.max().date()}, {len(closes)} rows")

    bench_ret = fetch("SPY")["close"].pct_change().fillna(0.0)

    inv, w_inv = xsmom_invvol(closes)                       # the registered variant
    eq, _w_eq = xsmom(closes, LOOKBACK, TOP_K, COST_BPS)    # H-201, same dates
    idx = inv.index.intersection(eq.index)
    inv_a = inv.loc[idx].to_numpy(dtype=float)
    eq_a = eq.loc[idx].to_numpy(dtype=float)
    b_a = bench_ret.reindex(idx).fillna(0.0).to_numpy(dtype=float)

    lo, hi = block_bootstrap(inv_a)
    # net already carries 1x cost, so subtracting the turnover cost once more = 2x
    extra = turnover_fraction(w_inv).reindex(idx).fillna(0.0).to_numpy(dtype=float)
    lo2x, _ = block_bootstrap(inv_a - extra * COST_BPS / 1e4)
    h = len(inv_a) // 2
    mvb = matched_vol_block(inv_a, b_a)
    diff = paired_ci(inv_a, eq_a)

    # Deflation basis: the frozen 39 cells' daily Sharpes plus this cell, so the
    # variance-of-Sharpes is measured, not hand-set.
    frozen = json.loads(Path("reports/per_class_edge_2026-11-22.json").read_text())
    srs = [c["sr_daily"] for c in frozen["cells"] if c.get("sr_daily") is not None]
    srs.append(round(sharpe(inv_a), 5))
    sr0_30 = expected_max_sr(args.n_trials, float(np.var(srs, ddof=1)))
    d30, sr_daily, _sk, _ku = dsr(inv_a, sr0_30)
    d29, _, _, _ = dsr(inv_a, frozen["expected_max_sharpe_daily"])

    null = random_selection_null(closes)
    pct = float((null < inv_a.mean()).mean() * 100)

    gates = {
        "boot_ci_lb_bps": round(1e4 * float(lo), 3),
        "boot_ci_ub_bps": round(1e4 * float(hi), 3),
        "boot_ci_lb_2x_cost_bps": round(1e4 * float(lo2x), 3),
        "split_half_bps": [round(1e4 * float(inv_a[:h].mean()), 3),
                           round(1e4 * float(inv_a[h:].mean()), 3)],
        "dsr_n30": round(d30, 4),
        "dsr_n29_for_comparison": round(d29, 4),
        "expected_max_sr_n30": round(sr0_30, 5),
        "sr_daily": round(sr_daily, 5),
        "excess_vs_spy_bps": round(1e4 * float(np.mean(inv_a - b_a)), 3),
    }
    passes = (gates["boot_ci_lb_bps"] > 0 and gates["boot_ci_lb_2x_cost_bps"] > 0
              and gates["split_half_bps"][0] > 0 and gates["split_half_bps"][1] > 0
              and gates["dsr_n30"] >= 0.95 and gates["excess_vs_spy_bps"] > 0)

    out = {
        "generated_at": pd.Timestamp.utcnow().isoformat(),
        "hypothesis": "H-232", "item": 15,
        "question": "does inverse-vol POSITION SIZING inside the top-3 basket help, "
                    "holding selection, exposure, lookback, rebalance and cost fixed?",
        "params": {"lookback": LOOKBACK, "top_k": TOP_K, "rebal_days": REBAL,
                   "cost_bps_per_side": COST_BPS, "exposure": 1.0,
                   "universe": sorted(data), "n_names": len(data)},
        "window": [str(idx.min().date()), str(idx.max().date())],
        "n_days": int(len(inv_a)),
        "h232_invvol": {**gates,
                        "mean_daily_bps": round(1e4 * float(inv_a.mean()), 3)},
        "h201_equal_weight_same_days": {
            "mean_daily_bps": round(1e4 * float(eq_a.mean()), 3),
            "boot_ci_lb_bps": round(1e4 * float(block_bootstrap(eq_a)[0]), 3),
            "excess_vs_spy_bps": round(1e4 * float(np.mean(eq_a - b_a)), 3),
        },
        "paired_difference_invvol_minus_equal": diff,
        "selection_vs_sizing_control": {
            "random_top3_same_sizing_mean_bps": round(1e4 * float(null.mean()), 3),
            "random_p05_bps": round(1e4 * float(np.percentile(null, 5)), 3),
            "random_p95_bps": round(1e4 * float(np.percentile(null, 95)), 3),
            "observed_percentile": round(pct, 1),
            "n_draws": N_RANDOM,
        },
        "vol_match": mvb,
        "gates_passed": bool(passes),
        "verdict": "PASSES" if passes else "FAILS",
    }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=1))

    L = ["# H-232 — inverse-vol sizing inside the H-201 basket (item 15)", "",
         f"Window **{out['window'][0]} → {out['window'][1]}**, {out['n_days']} days, "
         f"{out['params']['n_names']} names, exposure fixed at 1.0, "
         f"{COST_BPS} bp/side — identical to H-201 apart from the weight split.", "",
         "## Does sizing help? (the registered question)", "",
         "| leg | mean daily (bp) | CI-LB (bp) | excess vs SPY (bp) |", "|---|---|---|---|",
         f"| H-232 inverse-vol | {out['h232_invvol']['mean_daily_bps']} | "
         f"{gates['boot_ci_lb_bps']} | {gates['excess_vs_spy_bps']} |",
         f"| H-201 equal weight, same days | "
         f"{out['h201_equal_weight_same_days']['mean_daily_bps']} | "
         f"{out['h201_equal_weight_same_days']['boot_ci_lb_bps']} | "
         f"{out['h201_equal_weight_same_days']['excess_vs_spy_bps']} |", "",
         f"**Paired difference (invvol − equal), same days: {diff['mean_bps']} bp/day**, "
         f"95% CI **[{diff['ci_lb_bps']}, {diff['ci_ub_bps']}]**, t = {diff['t']} → CI "
         f"{'EXCLUDES' if diff['excludes_zero'] else 'INCLUDES'} zero.", "",
         "## Full gate set (unchanged from every other cell)", "",
         "| gate | value |", "|---|---|",
         f"| boot CI-LB | {gates['boot_ci_lb_bps']} bp |",
         f"| boot CI-LB at 2x cost | {gates['boot_ci_lb_2x_cost_bps']} bp |",
         f"| split halves | {gates['split_half_bps']} bp |",
         f"| DSR (n_trials=30, raised for this cell) | {gates['dsr_n30']} |",
         f"| DSR (n_trials=29, comparison only) | {gates['dsr_n29_for_comparison']} |",
         f"| excess vs SPY | {gates['excess_vs_spy_bps']} bp |",
         f"| vol-matched excess CI-LB | {mvb['matched_ci_lb_bps']} bp |", "",
         "## Selection vs sizing control", "",
         f"Random top-3 with the *same* inverse-vol sizing (n={N_RANDOM}): mean "
         f"{out['selection_vs_sizing_control']['random_top3_same_sizing_mean_bps']} bp/day, "
         f"5–95% [{out['selection_vs_sizing_control']['random_p05_bps']}, "
         f"{out['selection_vs_sizing_control']['random_p95_bps']}]. The observed cell sits at "
         f"the **{pct:.1f}th percentile** of that null.", "",
         f"**Verdict: {out['verdict']}.** The paired difference is what answers the item-15 "
         "question; the gate table is reported unchanged so this cell cannot be judged on "
         "an easier standard than its peers."]
    Path(args.md).write_text("\n".join(L) + "\n")

    print(f"invvol mean {1e4*float(inv_a.mean()):.3f} bp/day, CI-LB {gates['boot_ci_lb_bps']}")
    print(f"equal  mean {1e4*float(eq_a.mean()):.3f} bp/day")
    print(f"paired diff {diff}")
    print(f"null pct {pct:.1f} | DSR30 {gates['dsr_n30']} | DSR29 {d29:.4f}")
    print(f"verdict {out['verdict']}")
    print(f"wrote {args.out} and {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
