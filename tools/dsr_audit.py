#!/usr/bin/env python3
"""Deflated Sharpe Ratio with the *true* trial count from the mutation engine.

The existing tools/deflated_sharpe.py uses N = number of strategies that
emitted picks (~50). That undercounts the multiple-testing burden because
the DNA mutation engine spawns thousands of variants that never make the
audit page. Using the larger N inflates the haircut and deflates "winners"
to their honest level.

Reads:
  - alpha_engine/data/dna_mutations.json -> summary.total_active_mutations
  - audit_dashboard/data/dashboard_data.json -> picks.recent_closed

Writes:
  - tools/data/dsr_audit_results.json (sidecar artifact)
  - reports/dsr_audit_with_real_N_<date>.md (human-readable summary)

Wiring status: OPT-IN SIDECAR. No production caller. A future PR may render
a "DSR (real N)" badge on the audit dashboard once these numbers stabilise.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from tools.deflated_sharpe import (  # noqa: E402
    ANNUAL_TRADES,
    MIN_TRADES,
    _compute_moments,
    _deflated_sharpe,
    _sharpe_se,
    _sr_haircut,
)

PICKS_PATH = os.path.join(REPO_ROOT, "audit_dashboard", "data", "dashboard_data.json")
MUTATIONS_PATH = os.path.join(REPO_ROOT, "alpha_engine", "data", "dna_mutations.json")
OUT_JSON = os.path.join(REPO_ROOT, "tools", "data", "dsr_audit_results.json")
OUT_MD_DIR = os.path.join(REPO_ROOT, "reports")


def load_true_trial_count(extra_sources: list[str] | None = None) -> tuple[int, dict]:
    """Compose the true N from documented trial sources.

    Currently only DNA mutations is wired. Other sources to add later
    (each ships its own counter): genetic_programmer, parameter sweeps,
    walk-forward grid search.
    """
    breakdown: dict[str, int] = {}
    with open(MUTATIONS_PATH, "r", encoding="utf-8") as f:
        mut = json.load(f)
    breakdown["dna_mutations_active"] = int(mut["summary"]["total_active_mutations"])
    for src in extra_sources or []:
        # Reserved for future counters; ignore unknown for MVP
        breakdown[src] = 0
    total = sum(breakdown.values())
    return total, breakdown


def group_returns(picks: list[dict]) -> tuple[dict, dict]:
    by_strategy: dict[str, list[float]] = defaultdict(list)
    by_class_strategy: dict[tuple[str, str], list[float]] = defaultdict(list)
    for p in picks:
        pnl = p.get("pnl_pct")
        if pnl is None:
            continue
        try:
            pnl = float(pnl)
        except (TypeError, ValueError):
            continue
        strat = p.get("strategy") or "unknown"
        klass = (p.get("asset_class") or "UNKNOWN").upper()
        by_strategy[strat].append(pnl)
        by_class_strategy[(klass, strat)].append(pnl)
    return by_strategy, by_class_strategy


def analyse(returns_by_key: dict, n_trials: int, key_format) -> list[dict]:
    sr_star = _sr_haircut(n_trials)
    rows: list[dict] = []
    for key, rets in returns_by_key.items():
        T = len(rets)
        if T < MIN_TRADES:
            continue
        mu, std, skew, kurt = _compute_moments(rets)
        sr_trade = mu / std if std > 1e-12 else 0.0
        sr_ann = sr_trade * math.sqrt(ANNUAL_TRADES)
        se = _sharpe_se(sr_ann, skew, kurt, T)
        dsr = _deflated_sharpe(sr_ann, sr_star, se)
        wr = sum(1 for r in rets if r > 0) / T * 100
        rows.append({
            "key": key_format(key),
            "trades": T,
            "win_rate_pct": round(wr, 1),
            "avg_pnl_pct": round(mu, 4),
            "sharpe_annual": round(sr_ann, 4),
            "sr_haircut": round(sr_star, 4),
            "se_sr": round(se, 4),
            "dsr": round(dsr, 4),
            "survives_real_N": dsr > 0,
        })
    rows.sort(key=lambda r: r["dsr"], reverse=True)
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n-override", type=int, default=None,
                    help="Override the true trial count for sensitivity analysis")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    n_true, breakdown = load_true_trial_count()
    if args.n_override is not None:
        n_true = args.n_override
        breakdown["override"] = args.n_override

    with open(PICKS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    picks = data.get("picks", {}).get("recent_closed", [])
    by_strategy, by_class_strategy = group_returns(picks)

    n_naive = len(by_strategy)
    sr_star_naive = _sr_haircut(n_naive)
    sr_star_true = _sr_haircut(n_true)

    strat_rows = analyse(by_strategy, n_true, key_format=lambda k: k)
    classstrat_rows = analyse(by_class_strategy, n_true,
                              key_format=lambda k: f"{k[0]}::{k[1]}")

    survivors_naive = sum(
        1 for k, rets in by_strategy.items()
        if len(rets) >= MIN_TRADES and (
            (lambda mu, std, T:
             ((mu / std if std > 1e-12 else 0.0) * math.sqrt(ANNUAL_TRADES) - sr_star_naive)
             / max(_sharpe_se(
                 (mu / std if std > 1e-12 else 0.0) * math.sqrt(ANNUAL_TRADES),
                 _compute_moments(rets)[2], _compute_moments(rets)[3], T), 1e-12)
             > 0)(_compute_moments(rets)[0], _compute_moments(rets)[1], len(rets))
        )
    )
    survivors_true = sum(1 for r in strat_rows if r["survives_real_N"])

    summary = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "trial_count": {
            "naive_N_strategies_with_picks": n_naive,
            "true_N_components": breakdown,
            "true_N_total": n_true,
            "naive_haircut": round(sr_star_naive, 4),
            "true_haircut": round(sr_star_true, 4),
            "haircut_inflation": round(sr_star_true - sr_star_naive, 4),
        },
        "strategy_summary": {
            "analysed": len(strat_rows),
            "survivors_naive_N": survivors_naive,
            "survivors_true_N": survivors_true,
            "deflation": survivors_naive - survivors_true,
        },
        "by_strategy": strat_rows,
        "by_asset_class_strategy": classstrat_rows,
    }

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    md_path = os.path.join(
        OUT_MD_DIR,
        f"dsr_audit_with_real_N_{datetime.now(timezone.utc).strftime('%Y_%m_%d')}.md",
    )
    write_markdown(summary, md_path)

    if not args.quiet:
        print(f"naive N = {n_naive} strategies, haircut = {sr_star_naive:.4f}")
        print(f"true N  = {n_true} (DNA mutations: {breakdown['dna_mutations_active']}), "
              f"haircut = {sr_star_true:.4f}")
        print(f"survivors: naive {survivors_naive} -> true {survivors_true} "
              f"({survivors_naive - survivors_true} deflated)")
        print(f"JSON: {OUT_JSON}")
        print(f"MD:   {md_path}")

    return 0


def write_markdown(summary: dict, path: str) -> None:
    tc = summary["trial_count"]
    ss = summary["strategy_summary"]
    lines: list[str] = []
    lines.append(f"# DSR Audit with Real Trial Count — {summary['generated'][:10]}")
    lines.append("")
    lines.append("Generated by `tools/dsr_audit.py` — opt-in sidecar.")
    lines.append("")
    lines.append("## Why this exists")
    lines.append("")
    lines.append(
        "`tools/deflated_sharpe.py` uses N = number of strategies that emitted "
        "picks. The DNA mutation engine spawns thousands of variants that never "
        "make the audit page. Using their true count inflates the Harvey-Liu "
        "haircut and deflates audit winners to their honest level."
    )
    lines.append("")
    lines.append("## Trial-count reconciliation")
    lines.append("")
    lines.append(f"- Naive N (strategies with picks): **{tc['naive_N_strategies_with_picks']}**")
    lines.append(f"- True N components: `{tc['true_N_components']}`")
    lines.append(f"- True N total: **{tc['true_N_total']}**")
    lines.append(f"- Naive haircut: **{tc['naive_haircut']}** SR units")
    lines.append(f"- True haircut: **{tc['true_haircut']}** SR units")
    lines.append(f"- Inflation: **+{tc['haircut_inflation']}** SR units")
    lines.append("")
    lines.append("## Survivor deflation")
    lines.append("")
    lines.append(f"- Strategies analysed (n>={MIN_TRADES}): **{ss['analysed']}**")
    lines.append(f"- Survivors at naive N: **{ss['survivors_naive_N']}**")
    lines.append(f"- Survivors at true N: **{ss['survivors_true_N']}**")
    lines.append(f"- Deflated by real N: **{ss['deflation']}**")
    lines.append("")
    lines.append("## Top 20 by DSR (real N)")
    lines.append("")
    lines.append("| Strategy | n | WR% | SR_ann | DSR | Survives |")
    lines.append("|---|---:|---:|---:|---:|:---:|")
    for r in summary["by_strategy"][:20]:
        flag = "OK" if r["survives_real_N"] else "X"
        lines.append(
            f"| {r['key']} | {r['trades']} | {r['win_rate_pct']} | "
            f"{r['sharpe_annual']} | {r['dsr']} | {flag} |"
        )
    lines.append("")
    lines.append("## What's NOT in N (yet)")
    lines.append("")
    lines.append(
        "- `genetic_programmer` evaluations\n"
        "- Parameter-sweep / walk-forward grid trials\n"
        "- Killed-but-tested historical strategies (no surviving counter)\n\n"
        "Adding any of these only makes the haircut larger and deflates more. "
        "Treat current results as a *lower bound* on the multiple-testing penalty."
    )
    lines.append("")
    lines.append("## Wiring plan")
    lines.append("")
    lines.append(
        "Sidecar artifact only. A follow-up PR will render a `DSR-real-N` badge "
        "in `audit_dashboard/template.html` strategy table, sourcing the JSON "
        "at `tools/data/dsr_audit_results.json`. Caller will be "
        "`audit_dashboard/dashboard_generator.py` (or whichever generator is "
        "canonical at the time)."
    )
    lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())
