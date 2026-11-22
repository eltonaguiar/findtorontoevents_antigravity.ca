#!/usr/bin/env python3
"""Item 33 -- commodity futures momentum, cross-sectional, pre-registered.

PRE-DECLARED RULE (fixed before any run; copied verbatim from
docs/edge_research/16_COMMODITY_AND_BOND_MOMENTUM_2026-11-22.md section 0.1):

  Universe = the 7 commodity futures with continuous front-month daily closes in
  data/cache/asset_class_review: CL_F, GC_F, HG_F, NG_F, SI_F, ZC_F, ZS_F.
  Formation = trailing 252-trading-day return ending at each month-end close.
  Rank cross-sectionally at each month-end; with 7 symbols the terciles are the
  top 3 (long) and bottom 3 (short), equal weight 1/3 each, the middle symbol
  unheld. Hold one month, rebalance at month-end. Cost is charged on traded
  notional: bp/side * sum|delta_w|. Variants: V1 long/short (base), V2 long-only
  top 3 (cash earns the 4.32% risk-free rate), V3 long-only with absolute filter
  (hold a top-3 name only if its trailing 252-day return is > 0, else cash).
  Sign-skip: V1 shorts a negative-momentum name because it is rank-selected, not
  sign-selected; V2/V3 go flat, never short. Cost sweep 2/5/10/20 bp per side;
  base 5 bp/side. Kill: Sharpe-vs-rf < 0.5 at 10 bp/side, OR (null percentile < 95
  AND the excess-vs-SPY 95% CI includes 0). MARGINAL: null >= 95 with CI including
  0. EDGE: null >= 95 and CI lower bound > 0.

COST BASIS: bp/side is an ASSUMPTION, not a measurement -- commodity futures cost is
UNMEASURED in this programme. The sweep exists precisely because of that.

NO-LOOKAHEAD: shared primitives live in tools/momentum_core.py, where the monthly
return is forward-looking and labelled by period start. Every monthly return in the
JSON is traceable to `monthly_detail`.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

# Run as a script (`python tools/commodity_momentum.py`) the repo root is NOT on
# sys.path -- only tools/ is -- so the package import below would fail. Put the root
# on the path first; this also works unchanged under pytest.
if __package__ in (None, ""):
    _ROOT = Path(__file__).resolve().parent.parent
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))

from tools.momentum_core import (
    BASE_COST_BP, COST_SWEEP_BP, DATA_DIR, N_BOOT, N_NULL, REPO_ROOT, RF_ANNUAL, SEED,
    bootstrap_excess_cagr, formation_return, load_close_series, load_panel,
    month_end_index, monthly_returns, profit_factor, sanitize, summarize,
)

REPORTS_DIR = REPO_ROOT / "reports"

COMMODITY_SYMBOLS = ["CL_F", "GC_F", "HG_F", "NG_F", "SI_F", "ZC_F", "ZS_F"]
FORMATION_DAYS = 252


# --------------------------------------------------------------------------- #
# Rank -> weights
# --------------------------------------------------------------------------- #
@dataclass
class WeightRule:
    variant: str          # "V1" | "V2" | "V3"
    n_symbols: int = 7
    rf_annual: float = RF_ANNUAL

    def weights(self, scores: Dict[str, float]) -> Tuple[Dict[str, float], float]:
        """Return ({symbol: weight}, cash_weight). Weights sum to 1 in abs terms.

        NaN scores are dropped before ranking -- a symbol with no formation history
        is 'not available', never 'worst' (that would fabricate a short).
        """
        scores = {s: v for s, v in scores.items() if v is not None and np.isfinite(v)}
        n = len(scores)
        if n == 0:
            return {}, 1.0
        k = max(1, (n + 2) // 3)  # ceil(n/3): 7 -> 3, 10 -> 4
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        longs = [s for s, _ in ranked[:k]]
        shorts = [s for s, _ in ranked[-k:]]
        if set(longs) & set(shorts):  # tiny universes: never double-hold
            shorts = [s for s in shorts if s not in longs]
        w: Dict[str, float] = {}
        if self.variant == "V1":
            for s in longs:
                w[s] = w.get(s, 0.0) + 1.0 / k
            for s in shorts:
                w[s] = w.get(s, 0.0) - 1.0 / k
            return w, 0.0
        if self.variant == "V2":
            for s in longs:
                w[s] = 1.0 / k
            return w, 1.0 - len(longs) / k
        if self.variant == "V3":
            kept = [s for s in longs if scores[s] > 0.0]  # absolute filter: sign-skip -> flat
            for s in kept:
                w[s] = 1.0 / k
            return w, 1.0 - len(kept) / k
        raise ValueError(f"unknown variant {self.variant!r}")


# --------------------------------------------------------------------------- #
# Backtest
# --------------------------------------------------------------------------- #
def backtest(prices: pd.DataFrame, me: Sequence[pd.Timestamp], variant: str,
             cost_bp_per_side: float, rf_annual: float = RF_ANNUAL,
             formation_days: int = FORMATION_DAYS,
             rank_override: Optional[np.ndarray] = None,
             collect_rows: bool = True) -> Dict:
    """Monthly-rebalanced cross-sectional momentum backtest.

    rank_override: optional (n_periods, n_symbols) array of *scores* used instead of
    the real formation returns -- this is how the random null shuffles the
    rank->symbol mapping while keeping universe, count, hold period and cost.
    """
    mrets = monthly_returns(prices, me).loc[:, prices.columns]
    periods: List[pd.Timestamp] = list(mrets.index)
    rule = WeightRule(variant=variant, n_symbols=prices.shape[1], rf_annual=rf_annual)
    cost = cost_bp_per_side / 10_000.0

    prev_w: Dict[str, float] = {}
    rows: List[Dict] = []
    nets: List[float] = []
    for i, t in enumerate(periods):
        if rank_override is not None:
            scores = {s: float(rank_override[i, j]) for j, s in enumerate(prices.columns)}
        else:
            scores = formation_return(prices, t, formation_days)
        w, cash_w = rule.weights(scores)
        gross = sum(abs(v) for v in w.values()) + cash_w
        gross = gross if gross > 0 else 1.0
        w = {k: v / gross for k, v in w.items()}
        cash_w = cash_w / gross

        turnover = sum(abs(w.get(s, 0.0) - prev_w.get(s, 0.0))
                       for s in set(w) | set(prev_w))
        gross_ret = sum(wt * float(mrets.loc[t, s]) for s, wt in w.items())
        rf_m = rf_annual / 12.0
        net = gross_ret + cash_w * rf_m - cost * turnover
        nets.append(net)
        if collect_rows:
            rows.append({
                "period_start": t.strftime("%Y-%m-%d"),
                "net_return": net, "gross_return": gross_ret,
                "cash_return": cash_w * rf_m, "turnover": turnover,
                "cost_drag": cost * turnover,
                "n_long": sum(1 for v in w.values() if v > 0),
                "n_short": sum(1 for v in w.values() if v < 0),
                "weights": {k: round(v, 6) for k, v in sorted(w.items())},
            })
        prev_w = w

    return {"variant": variant, "cost_bp_per_side": cost_bp_per_side,
            "n_periods": len(nets), "monthly": np.array(nets), "rows": rows}


# --------------------------------------------------------------------------- #
# Attribution
# --------------------------------------------------------------------------- #
def per_symbol_contribution(rows: List[Dict]) -> Dict[str, Dict]:
    """Exposure summary: how often and how heavily each symbol was held."""
    held: Dict[str, List[float]] = {}
    for r in rows:
        for s, wt in r["weights"].items():
            held.setdefault(s, []).append(wt)
    return {s: {"months_held": len(v), "avg_weight": round(float(np.mean(v)), 5),
                "mean_abs_weight": round(float(np.mean(np.abs(v))), 5)}
            for s, v in sorted(held.items())}


def per_symbol_pnl(prices: pd.DataFrame, me: Sequence[pd.Timestamp], variant: str,
                   cost_bp_per_side: float) -> Dict[str, float]:
    """Exact per-symbol GROSS P&L attribution (return points, before cost)."""
    mrets = monthly_returns(prices, me).loc[:, prices.columns]
    rule = WeightRule(variant=variant, n_symbols=prices.shape[1])
    contrib: Dict[str, float] = {s: 0.0 for s in prices.columns}
    for t in mrets.index:
        w, cash_w = rule.weights(formation_return(prices, t))
        gross = sum(abs(v) for v in w.values()) + cash_w
        gross = gross if gross > 0 else 1.0
        for s, wt in w.items():
            contrib[s] += (wt / gross) * float(mrets.loc[t, s])
    return {s: round(v, 6) for s, v in contrib.items()}


# --------------------------------------------------------------------------- #
# Null
# --------------------------------------------------------------------------- #
def random_rank_null(prices: pd.DataFrame, me: Sequence[pd.Timestamp], variant: str,
                     cost_bp_per_side: float, n_shuffles: int = N_NULL,
                     seed: int = SEED) -> Dict:
    """Shuffle the rank->symbol assignment each month; keep universe, count, hold, cost."""
    rng = np.random.default_rng(seed)
    mrets = monthly_returns(prices, me).loc[:, prices.columns]
    n_p, n_s = mrets.shape
    real = summarize(backtest(prices, me, variant, cost_bp_per_side)["monthly"])
    base_scores = np.array([[formation_return(prices, t).get(s, np.nan)
                             for s in prices.columns] for t in mrets.index])
    null_sh = []
    for _ in range(n_shuffles):
        shuffled = np.full_like(base_scores, np.nan)
        for i in range(n_p):
            row = base_scores[i]
            idx = np.where(~np.isnan(row))[0]
            if len(idx) == 0:
                continue  # warm-up month: no scores, portfolio sits in cash (same as real)
            shuffled[i, idx] = rng.permutation(row[idx])
        st = summarize(backtest(prices, me, variant, cost_bp_per_side,
                                rank_override=shuffled, collect_rows=False)["monthly"])
        null_sh.append(st["sharpe_vs_rf"])
    null_sh = np.array([x for x in null_sh if np.isfinite(x)])
    pct = float((null_sh < real["sharpe_vs_rf"]).mean() * 100) if len(null_sh) else float("nan")
    return {"n_shuffles": n_shuffles, "real_sharpe": real["sharpe_vs_rf"],
            "null_sharpe_mean": float(null_sh.mean()) if len(null_sh) else float("nan"),
            "null_sharpe_p05": float(np.percentile(null_sh, 5)) if len(null_sh) else float("nan"),
            "null_sharpe_p95": float(np.percentile(null_sh, 95)) if len(null_sh) else float("nan"),
            "percentile": pct,
            "beats_random_95": bool(pct >= 95.0) if np.isfinite(pct) else False}


# --------------------------------------------------------------------------- #
# Break-even cost
# --------------------------------------------------------------------------- #
def breakeven_cost_bp(prices: pd.DataFrame, me: Sequence[pd.Timestamp], variant: str,
                      target: str = "sharpe_zero", rf_annual: float = RF_ANNUAL,
                      hi: float = 500.0) -> Optional[float]:
    """Cost (bp/side) at which Sharpe-vs-rf (or CAGR-rf) hits zero. Bisection, cost only."""
    def value(cost_bp: float) -> float:
        st = summarize(backtest(prices, me, variant, cost_bp, collect_rows=False)["monthly"], rf_annual)
        return st["sharpe_vs_rf"] if target == "sharpe_zero" else st["cagr"] - rf_annual

    if value(0.0) <= 0:
        return 0.0
    if value(hi) > 0:
        return None  # still positive at 500 bp/side -- not meaningful
    lo = 0.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if value(mid) > 0:
            lo = mid
        else:
            hi = mid
    return float((lo + hi) / 2)


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
def run(data_dir: Path = DATA_DIR, n_null: int = N_NULL, n_boot: int = N_BOOT) -> Dict:
    prices = load_panel(COMMODITY_SYMBOLS, data_dir)
    # Trim to month-ends where a full formation window already exists: the strategy
    # does not exist before that, and padding with cash months would inflate Sharpe.
    me = [t for t in month_end_index(prices) if len(prices.loc[:t]) > FORMATION_DAYS]
    spy = load_close_series("SPY", data_dir).to_frame()
    spy_me = [t for t in month_end_index(spy) if me[0] <= t <= me[-1]]
    spy_m = monthly_returns(spy, spy_me).iloc[:, 0].to_numpy()
    spy_st = summarize(spy_m)

    inventory = {
        "symbols": COMMODITY_SYMBOLS, "n_symbols": len(COMMODITY_SYMBOLS),
        "rows": int(len(prices)), "first_date": prices.index[0].strftime("%Y-%m-%d"),
        "last_date": prices.index[-1].strftime("%Y-%m-%d"),
        "files": {s: f"data/cache/asset_class_review/{s}_5y.csv" for s in COMMODITY_SYMBOLS},
        "commodity_price_cache": "does not exist in this workspace (nothing to read)",
    }
    first_me = me[0]

    results: Dict[str, Dict] = {}
    for variant in ("V1", "V2", "V3"):
        base = backtest(prices, me, variant, BASE_COST_BP)
        sweep = {}
        for bp in COST_SWEEP_BP:
            m = backtest(prices, me, variant, bp, collect_rows=False)["monthly"]
            s = summarize(m)
            sweep[f"{bp:g}bp"] = {"cost_basis": f"{bp:g} bp/side ASSUMED",
                                  "cagr": s["cagr"], "sharpe_vs_rf": s["sharpe_vs_rf"],
                                  "maxdd": s["maxdd"], "pf": profit_factor(m)}
        null = random_rank_null(prices, me, variant, BASE_COST_BP, n_shuffles=n_null)
        boot = bootstrap_excess_cagr(base["monthly"], spy_m, n_boot=n_boot)

        sh10 = sweep["10bp"]["sharpe_vs_rf"]
        pct, ci = null["percentile"], boot["ci95"]
        ci_incl0 = not (ci[0] > 0 or ci[1] < 0)
        if not np.isfinite(sh10) or sh10 < 0.5:
            verdict = "KILL"
        elif pct >= 95 and ci[0] > 0:
            verdict = "EDGE"
        elif pct >= 95 and ci_incl0:
            verdict = "MARGINAL"
        else:
            verdict = "KILL"

        results[variant] = {
            "cost_basis": f"base {BASE_COST_BP:g} bp/side ASSUMED (commodity futures cost UNMEASURED)",
            "n_periods": base["n_periods"], "n_rebalances": base["n_periods"],
            "metrics": summarize(base["monthly"]),
            "pf_base": profit_factor(base["monthly"]),
            "cost_sweep": sweep,
            "breakeven_bp_per_side_sharpe_zero": breakeven_cost_bp(prices, me, variant),
            "breakeven_bp_per_side_cagr_eq_rf": breakeven_cost_bp(prices, me, variant,
                                                                 target="cagr_rf"),
            "null": null, "bootstrap_excess_vs_spy": boot,
            "per_symbol_pnl_gross_return_points": per_symbol_pnl(prices, me, variant,
                                                                 BASE_COST_BP),
            "per_symbol_exposure": per_symbol_contribution(base["rows"]),
            "monthly_detail": [{"period": r["period_start"], "net": round(r["net_return"], 6),
                                "turnover": round(r["turnover"], 4),
                                "cost_drag": round(r["cost_drag"], 6)} for r in base["rows"]],
            "verdict": verdict,
            "verdict_conditional_on": ("cost assumption (commodity futures cost UNMEASURED); "
                                       "5-year sample with 252-day formation"),
        }

    return sanitize({
        "item": 33,
        "title": "Commodity futures momentum (cross-sectional)",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "data_inventory": inventory,
        "first_usable_rebalance": first_me.strftime("%Y-%m-%d"),
        "risk_free_annual": RF_ANNUAL,
        "spy_buy_hold": {"cost_basis": "zero (buy-and-hold benchmark)",
                         "cagr": spy_st["cagr"], "sharpe_vs_rf": spy_st["sharpe_vs_rf"],
                         "vol": spy_st["vol"], "maxdd": spy_st["maxdd"],
                         "n_periods": spy_st["n"]},
        "results": results,
    })


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--null", type=int, default=N_NULL)
    ap.add_argument("--boot", type=int, default=N_BOOT)
    ap.add_argument("--out", type=Path, default=REPORTS_DIR / "commodity_momentum_20261122.json")
    args = ap.parse_args(argv)
    res = run(n_null=args.null, n_boot=args.boot)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(res, indent=2))
    for v, r in res["results"].items():
        m = r["metrics"]
        print(f"{v}: n={r['n_periods']} CAGR={m['cagr']:.4f} Sharpe={m['sharpe_vs_rf']:.3f} "
              f"maxDD={m['maxdd']:.3f} skew={m['skew']:.3f} worst={m['worst_month']:.4f} "
              f"null_pct={r['null']['percentile']:.1f} "
              f"excessCI=[{r['bootstrap_excess_vs_spy']['ci95'][0]:.4f},"
              f"{r['bootstrap_excess_vs_spy']['ci95'][1]:.4f}] "
              f"BE_bp={r['breakeven_bp_per_side_sharpe_zero']} verdict={r['verdict']}")
    print(f"written: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
