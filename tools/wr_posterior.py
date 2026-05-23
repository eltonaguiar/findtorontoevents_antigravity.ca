"""Bayesian Beta-Bernoulli posterior on per-strategy win-rate.

Why this exists
---------------
The audit page currently displays point-estimate WR. A small-n strategy
showing 80% WR (n=10) and a large-n strategy showing 55% WR (n=400) look
comparable in a flat table — but they aren't, because the small-n number
has a 95% credible interval roughly [49%, 95%] while the large-n number
has [50%, 60%]. The institutional reviewer (cross-AI synthesis 2026-05-02)
ranked this the cheapest single signal that the operator understands
sampling error.

This tool fits a Beta posterior per strategy:
    prior    ~ Beta(α₀, β₀)   (default Jeffreys: α₀=β₀=0.5)
    likelihood ~ Bernoulli(WR) per closed pick (win = pnl_pct > 0)
    posterior ~ Beta(α₀ + wins, β₀ + losses)

Outputs:
    - posterior mean (Bayesian point estimate)
    - 95% credible interval [2.5th, 97.5th percentile]
    - P(WR > 0.50)  — action-relevant: probability of break-even-or-better
    - P(WR > 0.55)  — Tier 2 candidate threshold per
      reports/hedge_fund_performance_review_summary_2026_04_27.md

Wiring status: OPT-IN SIDECAR. No production caller. Future PR will add
a "credible interval" column to audit_dashboard/template.html strategy
table sourcing tools/data/wr_posterior_results.json.

Known limitations
-----------------
1. Like the calibrator and DSR audit, this fits on closed-pick labels
   produced by outcome_resolver.py. While the resolver bug is in flight,
   the FOREX/COMMODITY posteriors are partially based on 1bp-flicker
   "wins". CRYPTO posteriors are cleaner but not perfectly clean either.
2. Independence assumption: each pick is treated as an independent
   Bernoulli trial. In reality, picks within a single regime are
   correlated, so true credible intervals are wider than reported.
   A per-regime hierarchical model (Gelman 2014 ch. 5) would correct
   this; deferred.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scipy.stats import beta as _beta  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
PICKS_PATH = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_JSON = REPO_ROOT / "tools" / "data" / "wr_posterior_results.json"
OUT_MD_DIR = REPO_ROOT / "reports"

# Jeffreys prior — minimum-information for a binomial; uniform Beta(1,1) is
# also defensible. Jeffreys avoids the "100% WR on n=2 looks like 0.75 mean"
# pull-toward-50% that uniform produces for tiny samples.
DEFAULT_ALPHA0 = 0.5
DEFAULT_BETA0 = 0.5
MIN_N = 10  # below this, posterior is dominated by prior; don't bother


def posterior_stats(wins: int, n: int,
                    alpha0: float = DEFAULT_ALPHA0,
                    beta0: float = DEFAULT_BETA0) -> dict[str, float]:
    """Compute Beta posterior summary statistics.

    Returns dict with: mean, ci_low, ci_high, p_above_50, p_above_55,
    posterior_alpha, posterior_beta.
    """
    losses = n - wins
    a = alpha0 + wins
    b = beta0 + losses
    mean = a / (a + b)
    ci_low, ci_high = _beta.ppf([0.025, 0.975], a, b)
    p_above_50 = 1.0 - _beta.cdf(0.50, a, b)
    p_above_55 = 1.0 - _beta.cdf(0.55, a, b)
    return {
        "posterior_mean": float(mean),
        "ci_low_95": float(ci_low),
        "ci_high_95": float(ci_high),
        "ci_width": float(ci_high - ci_low),
        "p_wr_above_50": float(p_above_50),
        "p_wr_above_55": float(p_above_55),
        "posterior_alpha": float(a),
        "posterior_beta": float(b),
    }


def analyze_strategies(picks: list[dict],
                       alpha0: float = DEFAULT_ALPHA0,
                       beta0: float = DEFAULT_BETA0,
                       min_n: int = MIN_N) -> list[dict]:
    """Group closed picks by strategy and compute posteriors."""
    by_strategy: dict[str, list[int]] = defaultdict(list)
    by_class_strategy: dict[tuple[str, str], list[int]] = defaultdict(list)
    for p in picks:
        pnl = p.get("pnl_pct")
        if pnl is None:
            continue
        try:
            pnl_f = float(pnl)
        except (TypeError, ValueError):
            continue
        strat = p.get("strategy") or "unknown"
        klass = (p.get("asset_class") or "UNKNOWN").upper()
        win = 1 if pnl_f > 0 else 0
        by_strategy[strat].append(win)
        by_class_strategy[(klass, strat)].append(win)

    rows: list[dict] = []
    for strat, outcomes in by_strategy.items():
        n = len(outcomes)
        if n < min_n:
            continue
        wins = sum(outcomes)
        stats = posterior_stats(wins, n, alpha0, beta0)
        rows.append({
            "strategy": strat,
            "n": n,
            "wins": wins,
            "wr_point": round(wins / n, 4),
            **{k: round(v, 4) for k, v in stats.items()},
        })
    rows.sort(key=lambda r: r["p_wr_above_50"], reverse=True)

    class_rows: list[dict] = []
    for (klass, strat), outcomes in by_class_strategy.items():
        n = len(outcomes)
        if n < min_n:
            continue
        wins = sum(outcomes)
        stats = posterior_stats(wins, n, alpha0, beta0)
        class_rows.append({
            "asset_class": klass,
            "strategy": strat,
            "n": n,
            "wins": wins,
            "wr_point": round(wins / n, 4),
            **{k: round(v, 4) for k, v in stats.items()},
        })
    class_rows.sort(key=lambda r: r["p_wr_above_50"], reverse=True)

    return rows, class_rows


def write_markdown(summary: dict, path: Path) -> None:
    rows = summary["by_strategy"]
    n_total = len(rows)
    n_above_50 = sum(1 for r in rows if r["p_wr_above_50"] > 0.95)
    n_below_50 = sum(1 for r in rows if r["p_wr_above_50"] < 0.05)

    lines: list[str] = []
    lines.append(f"# WR Posterior — {summary['generated'][:10]}")
    lines.append("")
    lines.append("Generated by `tools/wr_posterior.py` — opt-in sidecar.")
    lines.append("")
    lines.append("Bayesian Beta-Bernoulli posterior on per-strategy win-rate. "
                 "Replaces the audit page's point-estimate WR with a credible "
                 "interval and an action-relevant probability of beating "
                 "break-even, so small-n and large-n strategies can be compared "
                 "honestly.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Strategies analysed (n>={MIN_N}): **{n_total}**")
    lines.append(f"- P(WR > 50%) > 0.95 (high-confidence winners): **{n_above_50}**")
    lines.append(f"- P(WR > 50%) < 0.05 (high-confidence losers): **{n_below_50}**")
    lines.append(f"- Prior: Beta({summary['prior']['alpha0']}, "
                 f"{summary['prior']['beta0']}) [Jeffreys]")
    lines.append("")
    lines.append("## Top 20 by P(WR > 50%)")
    lines.append("")
    lines.append("| Strategy | n | WR point | Posterior mean | 95% CI | P(>50%) | P(>55%) |")
    lines.append("|---|---:|---:|---:|---|---:|---:|")
    for r in rows[:20]:
        ci = f"[{r['ci_low_95']:.3f}, {r['ci_high_95']:.3f}]"
        lines.append(
            f"| {r['strategy']} | {r['n']} | {r['wr_point']:.3f} | "
            f"{r['posterior_mean']:.3f} | {ci} | "
            f"{r['p_wr_above_50']:.3f} | {r['p_wr_above_55']:.3f} |"
        )
    lines.append("")
    lines.append("## Bottom 10 (least likely to be net-positive)")
    lines.append("")
    lines.append("| Strategy | n | WR point | Posterior mean | 95% CI | P(>50%) |")
    lines.append("|---|---:|---:|---:|---|---:|")
    for r in rows[-10:]:
        ci = f"[{r['ci_low_95']:.3f}, {r['ci_high_95']:.3f}]"
        lines.append(
            f"| {r['strategy']} | {r['n']} | {r['wr_point']:.3f} | "
            f"{r['posterior_mean']:.3f} | {ci} | "
            f"{r['p_wr_above_50']:.3f} |"
        )
    lines.append("")
    lines.append("## How to read these numbers")
    lines.append("")
    lines.append(
        "- `wr_point` = simple wins/n. The audit page uses this today.\n"
        "- `posterior_mean` = Bayesian point estimate after Jeffreys-prior "
        "regularization. For large n it equals wr_point; for small n it "
        "shrinks toward 0.5.\n"
        "- `95% CI` = 2.5th to 97.5th percentile of the posterior. The "
        "actual range of plausible WR values given the data observed.\n"
        "- `P(>50%)` = posterior probability that true WR is above 50%. "
        "This is what an allocator actually wants to know. >0.95 = strong "
        "evidence of break-even-or-better; <0.05 = strong evidence the "
        "strategy is below break-even.\n"
        "- `P(>55%)` = analog for Tier 2 threshold "
        "(`reports/hedge_fund_performance_review_summary_2026_04_27.md`)."
    )
    lines.append("")
    lines.append("## Wiring plan")
    lines.append("")
    lines.append(
        "Sidecar artifact only. A follow-up PR will render a "
        "`P(>50%)` and `95% CI` column on `audit_dashboard/template.html` "
        "strategy table sourcing `tools/data/wr_posterior_results.json`. "
        "Combined with the existing notarizer + DSR-with-real-N + "
        "calibrator suite, this gives the audit page three "
        "honest-statistics columns the GH Actions cloud agent's plan "
        "doesn't have."
    )
    lines.append("")
    with path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--alpha0", type=float, default=DEFAULT_ALPHA0)
    ap.add_argument("--beta0", type=float, default=DEFAULT_BETA0)
    ap.add_argument("--min-n", type=int, default=MIN_N)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    with PICKS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    picks = data.get("picks", {}).get("recent_closed", [])

    rows, class_rows = analyze_strategies(picks, args.alpha0, args.beta0, args.min_n)

    summary = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "prior": {"alpha0": args.alpha0, "beta0": args.beta0,
                  "name": "Jeffreys" if (args.alpha0 == 0.5 and args.beta0 == 0.5)
                          else "custom"},
        "min_n": args.min_n,
        "n_strategies": len(rows),
        "n_class_strategies": len(class_rows),
        "by_strategy": rows,
        "by_asset_class_strategy": class_rows,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    md_path = OUT_MD_DIR / f"wr_posterior_{datetime.now(timezone.utc).strftime('%Y_%m_%d')}.md"
    write_markdown(summary, md_path)

    if not args.quiet:
        n_high = sum(1 for r in rows if r["p_wr_above_50"] > 0.95)
        n_low = sum(1 for r in rows if r["p_wr_above_50"] < 0.05)
        print(f"strategies: {len(rows)} (n>={args.min_n})")
        print(f"  P(WR>50%) > 0.95 (winners): {n_high}")
        print(f"  P(WR>50%) < 0.05 (losers):  {n_low}")
        print(f"JSON: {OUT_JSON}")
        print(f"MD:   {md_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
