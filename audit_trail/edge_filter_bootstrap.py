"""
Bootstrap PF significance testing + Deflated Sharpe Ratio for OOS-validated edge filters.

Pre-registered split: IS=2026-02-20 to 2026-03-31, OOS=2026-04-01 to 2026-05-16
All claims use the OOS period only. IS is for development only.

Usage:
    python audit_trail/edge_filter_bootstrap.py
    python audit_trail/edge_filter_bootstrap.py --system aggregated_picks
    python audit_trail/edge_filter_bootstrap.py --save reports/oos_validation_2026-05-16.md
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OOS_CUTOFF = "2026-04-01"
N_BOOTSTRAP = 5000
RANDOM_SEED = 42

# Significance thresholds
PF_FLOOR_TIER1 = 2.0
PF_FLOOR_TIER2 = 1.5
CI_SIGNIFICANCE_THRESHOLD = 1.0  # CI-lower must exceed this for "significant"


def load_picks() -> list[dict]:
    path = ROOT / "audit_trail" / "data" / "universal_resolved_picks.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, list) else raw.get("picks", [])


def get_ts(pick: dict) -> str:
    ts = pick.get("timestamp") or pick.get("created_at") or ""
    return ts[:10] if ts else ""


def split_picks(picks: list[dict]) -> tuple[list[dict], list[dict]]:
    is_picks = [p for p in picks if get_ts(p) < OOS_CUTOFF]
    oos_picks = [p for p in picks if get_ts(p) >= OOS_CUTOFF]
    return is_picks, oos_picks


def closed_pnls(picks: list[dict]) -> list[float]:
    return [p["pnl_pct"] for p in picks if p.get("pnl_pct", 0) != 0]


def compute_pf(pnls: list[float]) -> float:
    gross_profit = sum(x for x in pnls if x > 0)
    gross_loss = abs(sum(x for x in pnls if x < 0))
    return gross_profit / gross_loss if gross_loss > 0 else float("inf")


def bootstrap_pf(pnls: list[float], n_iter: int = N_BOOTSTRAP, seed: int = RANDOM_SEED) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    arr = np.array(pnls)
    n = len(arr)
    pf_samples = np.empty(n_iter)
    for i in range(n_iter):
        sample = rng.choice(arr, size=n, replace=True)
        gp = sample[sample > 0].sum()
        gl = abs(sample[sample <= 0].sum())
        pf_samples[i] = gp / gl if gl > 0 else 9999.0
    return {
        "n": n,
        "pf_point": float(compute_pf(pnls)),
        "pf_median": float(np.median(pf_samples)),
        "ci_lower_90": float(np.percentile(pf_samples, 10)),
        "ci_lower_95": float(np.percentile(pf_samples, 5)),
        "ci_upper_95": float(np.percentile(pf_samples, 95)),
        "p_above_1_0": float((pf_samples > 1.0).mean()),
        "p_above_1_5": float((pf_samples > 1.5).mean()),
        "p_above_2_0": float((pf_samples > 2.0).mean()),
        "significant_edge": bool(np.percentile(pf_samples, 5) > CI_SIGNIFICANCE_THRESHOLD),
        "tier": _classify_tier(pf_samples),
    }


def _classify_tier(pf_samples: np.ndarray) -> str:
    ci_lower = float(np.percentile(pf_samples, 5))
    p_above_2 = float((pf_samples > 2.0).mean())
    p_above_1_5 = float((pf_samples > 1.5).mean())
    if ci_lower >= PF_FLOOR_TIER1 and p_above_2 >= 0.90:
        return "TIER_1"
    if ci_lower >= CI_SIGNIFICANCE_THRESHOLD and p_above_1_5 >= 0.80:
        return "TIER_2"
    if ci_lower >= CI_SIGNIFICANCE_THRESHOLD:
        return "MONITORING"
    return "SUB_FLOOR"


def deflated_sharpe(returns: list[float], n_trials: int = 1) -> dict[str, float]:
    """
    Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014).
    Adjusts for multiple testing: the more systems tested, the higher the bar.
    """
    arr = np.array(returns)
    n = len(arr)
    if n < 10:
        return {"dsr": float("nan"), "sharpe": float("nan"), "min_sr": float("nan")}
    mu = float(arr.mean())
    sigma = float(arr.std(ddof=1))
    if sigma == 0:
        return {"dsr": 1.0, "sharpe": float("inf"), "min_sr": 0.0}
    sharpe = mu / sigma * math.sqrt(252)  # annualized (daily returns assumed)
    # Minimum Sharpe needed to beat multiple testing at 5% significance
    # Euler-Mascheroni approximation for expected max of n_trials standard normals
    gamma = 0.5772156649
    expected_max = (1 - gamma) * math.sqrt(2 * math.log(n_trials)) + gamma * math.sqrt(2 * math.log(n_trials))
    min_sr = expected_max if n_trials > 1 else 0.0
    # Skewness and kurtosis adjustment
    skew = float(((arr - arr.mean()) ** 3).mean() / sigma ** 3) if sigma > 0 else 0
    excess_kurt = float(((arr - arr.mean()) ** 4).mean() / sigma ** 4 - 3) if sigma > 0 else 0
    sharpe_adj = sharpe * (1 - skew * sharpe / 6 + (excess_kurt - 1) * sharpe ** 2 / 24)
    # DSR: probability that true SR > min_sr
    z = (sharpe_adj - min_sr) * math.sqrt(n - 1)
    try:
        from math import erfc
        dsr = 0.5 * erfc(-z / math.sqrt(2))
    except Exception:
        dsr = float("nan")
    return {"dsr": round(dsr, 4), "sharpe_annualized": round(sharpe, 3), "min_sr_threshold": round(min_sr, 3)}


def analyze_system(
    system_name: str,
    oos_picks: list[dict],
    n_trials: int = 1,
) -> dict[str, Any] | None:
    sys_picks = [p for p in oos_picks if p.get("source_system") == system_name]
    pnls = closed_pnls(sys_picks)
    if not pnls:
        return None
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x < 0]
    wr = len(wins) / len(pnls)
    bs = bootstrap_pf(pnls)
    dsr_result = deflated_sharpe(pnls, n_trials=n_trials)
    # Newey-West autocorrelation check (lag-1)
    arr = np.array(pnls)
    if len(arr) > 2:
        ac1 = float(np.corrcoef(arr[:-1], arr[1:])[0, 1])
    else:
        ac1 = 0.0
    return {
        "system": system_name,
        "n_closed": len(pnls),
        "n_open": len(sys_picks) - len(pnls),
        "wr_pct": round(wr * 100, 1),
        "avg_win_pct": round(sum(wins) / len(wins), 3) if wins else 0,
        "avg_loss_pct": round(sum(losses) / len(losses), 3) if losses else 0,
        "bootstrap": bs,
        "dsr": dsr_result,
        "lag1_autocorr": round(ac1, 3),
        "serial_correlation_flag": abs(ac1) > 0.2,
    }


def run_full_analysis(system_filter: str | None = None) -> dict[str, Any]:
    picks = load_picks()
    is_picks, oos_picks = split_picks(picks)

    # Get all systems present in OOS
    all_systems = sorted(set(p.get("source_system", "") for p in oos_picks if p.get("source_system")))
    if system_filter:
        all_systems = [s for s in all_systems if s == system_filter]

    n_trials = len(all_systems)  # for DSR multiple-testing adjustment
    results = {}
    for sys_name in all_systems:
        r = analyze_system(sys_name, oos_picks, n_trials=n_trials)
        if r:
            results[sys_name] = r

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "oos_cutoff": OOS_CUTOFF,
        "is_n": len(is_picks),
        "oos_n": len(oos_picks),
        "n_systems_tested": n_trials,
        "n_bootstrap_iterations": N_BOOTSTRAP,
        "systems": results,
    }


def format_report(analysis: dict) -> str:
    lines = [
        "# OOS Validation Report — Pre-Registered Split",
        f"**Generated:** {analysis['generated_at'][:19]}Z",
        f"**IS period:** pre-{analysis['oos_cutoff']} (n={analysis['is_n']:,})",
        f"**OOS period:** {analysis['oos_cutoff']} onward (n={analysis['oos_n']:,} total, closed picks only for metrics)",
        f"**Bootstrap:** {analysis['n_bootstrap_iterations']:,} iterations, seed=42",
        f"**Multiple-testing correction:** DSR adjusted for n={analysis['n_systems_tested']} systems tested",
        "",
        "## System Rankings (OOS, closed picks only)",
        "",
        f"| {'System':<28} | {'n':>5} | {'WR':>6} | {'OOS PF':>7} | {'CI-95-lo':>8} | {'CI-95-hi':>8} | {'P(PF>1.5)':>9} | {'DSR':>5} | {'AC1':>5} | Tier |",
        f"|{'-'*29}|{'-'*7}|{'-'*8}|{'-'*9}|{'-'*10}|{'-'*10}|{'-'*11}|{'-'*7}|{'-'*7}|{'-'*8}|",
    ]

    # Sort by OOS PF descending, only show systems with n >= 5
    ranked = sorted(
        [(s, r) for s, r in analysis["systems"].items() if r["n_closed"] >= 5],
        key=lambda x: -x[1]["bootstrap"]["pf_point"],
    )
    for sys_name, r in ranked:
        bs = r["bootstrap"]
        dsr = r["dsr"].get("dsr", float("nan"))
        ac1 = r["lag1_autocorr"]
        ac_flag = "⚠" if r["serial_correlation_flag"] else ""
        dsr_str = f"{dsr:.2f}" if not math.isnan(dsr) else "N/A"
        tier_icon = {"TIER_1": "✅T1", "TIER_2": "✅T2", "MONITORING": "⚠️Mon", "SUB_FLOOR": "❌Sub"}.get(bs["tier"], "?")
        lines.append(
            f"| {sys_name:<28} | {r['n_closed']:>5} | {r['wr_pct']:>5.1f}% | {bs['pf_point']:>7.2f} | "
            f"{bs['ci_lower_95']:>8.2f} | {bs['ci_upper_95']:>8.2f} | {bs['p_above_1_5']*100:>8.1f}% | "
            f"{dsr_str:>5} | {ac1:>4.2f}{ac_flag} | {tier_icon} |"
        )

    lines += [
        "",
        "## Key Findings",
        "",
        "### Tier 1 (CI-lower ≥ 2.0, P(PF>1.5) ≥ 90%)",
    ]
    tier1 = [(s, r) for s, r in ranked if r["bootstrap"]["tier"] == "TIER_1"]
    if tier1:
        for sys_name, r in tier1:
            bs = r["bootstrap"]
            lines.append(f"- **{sys_name}**: OOS PF={bs['pf_point']:.2f}, WR={r['wr_pct']:.1f}%, n={r['n_closed']}, CI=[{bs['ci_lower_95']:.2f}, {bs['ci_upper_95']:.2f}]")
    else:
        lines.append("- None")

    lines += ["", "### Tier 2 (CI-lower ≥ 1.0, P(PF>1.5) ≥ 80%)"]
    tier2 = [(s, r) for s, r in ranked if r["bootstrap"]["tier"] == "TIER_2"]
    if tier2:
        for sys_name, r in tier2:
            bs = r["bootstrap"]
            lines.append(f"- **{sys_name}**: OOS PF={bs['pf_point']:.2f}, WR={r['wr_pct']:.1f}%, n={r['n_closed']}, CI=[{bs['ci_lower_95']:.2f}, {bs['ci_upper_95']:.2f}]")
    else:
        lines.append("- None")

    lines += ["", "### Monitoring (CI-lower ≥ 1.0 but P(PF>1.5) < 80%)"]
    mon = [(s, r) for s, r in ranked if r["bootstrap"]["tier"] == "MONITORING"]
    for sys_name, r in mon:
        bs = r["bootstrap"]
        lines.append(f"- **{sys_name}**: OOS PF={bs['pf_point']:.2f}, n={r['n_closed']}, CI-lower={bs['ci_lower_95']:.2f}")

    lines += ["", "### Sub-floor (CI-lower < 1.0 — do not size)"]
    sub = [(s, r) for s, r in ranked if r["bootstrap"]["tier"] == "SUB_FLOOR"]
    for sys_name, r in sub:
        bs = r["bootstrap"]
        lines.append(f"- **{sys_name}**: OOS PF={bs['pf_point']:.2f}, n={r['n_closed']}")

    lines += [
        "",
        "## Serial Correlation Warnings",
        "Systems with lag-1 autocorrelation |AC1| > 0.2 have correlated returns —",
        "effective sample size is smaller than n. Bootstrap CI may be too optimistic.",
        "",
    ]
    ac_flagged = [(s, r) for s, r in ranked if r["serial_correlation_flag"]]
    if ac_flagged:
        for sys_name, r in ac_flagged:
            lines.append(f"- **{sys_name}**: AC1={r['lag1_autocorr']:.3f} — reduce effective n by ~{int(100*(1-abs(r['lag1_autocorr'])))}%")
    else:
        lines.append("- No systems flagged (|AC1| ≤ 0.2 for all)")

    lines += [
        "",
        "---",
        "*NOT FINANCIAL ADVICE. All figures from OOS period only.*",
        f"*Split pre-registered at {OOS_CUTOFF} before examining system performance.*",
    ]
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description="Bootstrap OOS validation for edge filter systems")
    p.add_argument("--system", help="Analyze a specific system only")
    p.add_argument("--save", help="Save markdown report to this path")
    p.add_argument("--json", dest="json_out", help="Save raw JSON to this path")
    args = p.parse_args()

    print(f"Running OOS validation (pre-registered cutoff: {OOS_CUTOFF})...")
    analysis = run_full_analysis(system_filter=args.system)

    report = format_report(analysis)
    print(report)

    if args.save:
        Path(args.save).write_text(report, encoding="utf-8")
        print(f"\nReport saved to {args.save}")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(analysis, indent=2, default=str), encoding="utf-8")
        print(f"JSON saved to {args.json_out}")


if __name__ == "__main__":
    main()
