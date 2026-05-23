"""Factor attribution — per-strategy alpha-vs-beta decomposition.

Why this exists
---------------
Cross-AI institutional reviewer (2026-05-02): "Allocators' first
question is always 'is this alpha or repackaged beta?' — an alpha-share
column directly answers the dispositive due-diligence question and
reframes the page from marketing to tearsheet."

This first-cut Fama-MacBeth-style attribution decomposes each
strategy's daily realized return into:

    pnl_t = alpha + b_mom * F_mom_t + b_qual * F_qual_t
                  + b_vol * F_vol_t + epsilon_t

Factors are simple in-sample proxies built from the BENCHMARK strategy
(equal-weight average across all strategies' picks per day):
  - F_mom  = 5-day rolling mean of benchmark daily return
  - F_qual = inverse 5-day rolling vol (1/std)
  - F_vol  = sign of today's benchmark return (+1 / -1 / 0)

`alpha_share_pct` = 100 * |alpha| / (|alpha| + sum |b_i * mean(F_i)|)

Caveats
-------
1. First cut. Canonical institutional Fama-MacBeth uses external
   long-short factor returns (Ken French / dollar-block momentum /
   term-structure roll). In-sample proxy here is enough to surface
   obviously-beta strategies.
2. Closed-pick labels come from outcome_resolver.py — Theme B
   contamination on FOREX/COMMODITY pending the cloud agent's fix.
3. Daily aggregation: equal-weighted mean of pnl_pct when a strategy
   emits multiple picks on the same UTC day.

Wiring status: OPT-IN SIDECAR. Follow-up PR renders an
alpha_share_pct column on audit_dashboard/template.html.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
PICKS_PATH = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_JSON = REPO_ROOT / "tools" / "data" / "factor_attribution_results.json"
OUT_MD_DIR = REPO_ROOT / "reports"

DEFAULT_MIN_N = 20
DEFAULT_MOM_WINDOW = 5
DEFAULT_QUAL_WINDOW = 5


def _parse_iso_date(s: str) -> str | None:
    if not isinstance(s, str):
        return None
    try:
        ts = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return ts.astimezone(timezone.utc).strftime("%Y-%m-%d")


def _aggregate_daily(picks: list[dict]) -> dict[str, float]:
    by_day: dict[str, list[float]] = defaultdict(list)
    for p in picks:
        pnl = p.get("pnl_pct")
        if pnl is None:
            continue
        try:
            pnl_f = float(pnl)
        except (TypeError, ValueError):
            continue
        ts_raw = p.get("closed_at") or p.get("opened_at")
        d = _parse_iso_date(ts_raw)
        if d is None:
            continue
        by_day[d].append(pnl_f)
    return {d: float(np.mean(v)) for d, v in by_day.items()}


def _rolling(arr: np.ndarray, window: int, fn) -> np.ndarray:
    out = np.full_like(arr, np.nan, dtype=float)
    for i in range(len(arr)):
        if i + 1 < window:
            continue
        out[i] = fn(arr[i + 1 - window:i + 1])
    return out


def build_factors(benchmark_daily: dict[str, float],
                  mom_window: int = DEFAULT_MOM_WINDOW,
                  qual_window: int = DEFAULT_QUAL_WINDOW) -> dict[str, dict[str, float]]:
    if not benchmark_daily:
        return {}
    dates = sorted(benchmark_daily.keys())
    rets = np.array([benchmark_daily[d] for d in dates], dtype=float)
    f_mom = _rolling(rets, mom_window, np.mean)
    f_qual_std = _rolling(rets, qual_window, np.std)
    with np.errstate(divide="ignore", invalid="ignore"):
        f_qual = np.where(f_qual_std > 1e-9, 1.0 / f_qual_std, np.nan)
    f_vol = np.sign(rets)
    out: dict[str, dict[str, float]] = {}
    for i, d in enumerate(dates):
        out[d] = {"mom": f_mom[i], "qual": f_qual[i], "vol": f_vol[i]}
    return out


def attribute_strategy(strategy_daily: dict[str, float],
                       factors: dict[str, dict[str, float]],
                       min_n: int = DEFAULT_MIN_N) -> dict | None:
    rows: list[tuple[float, float, float, float]] = []
    for d, ret in sorted(strategy_daily.items()):
        f = factors.get(d)
        if not f:
            continue
        if any(not np.isfinite(f[k]) for k in ("mom", "qual", "vol")):
            continue
        if not np.isfinite(ret):
            continue
        rows.append((ret, f["mom"], f["qual"], f["vol"]))
    if len(rows) < min_n:
        return None

    arr = np.array(rows, dtype=float)
    y = arr[:, 0]
    X = np.column_stack([np.ones(len(arr)), arr[:, 1], arr[:, 2], arr[:, 3]])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    alpha = float(coef[0])
    b_mom, b_qual, b_vol = float(coef[1]), float(coef[2]), float(coef[3])
    y_hat = X @ coef
    resid_std = float(np.std(y - y_hat))

    f_mean_mom = float(np.mean(arr[:, 1]))
    f_mean_qual = float(np.mean(arr[:, 2]))
    f_mean_vol = float(np.mean(arr[:, 3]))
    beta_contrib = (abs(b_mom * f_mean_mom)
                    + abs(b_qual * f_mean_qual)
                    + abs(b_vol * f_mean_vol))
    denom = abs(alpha) + beta_contrib
    alpha_share = (abs(alpha) / denom) if denom > 1e-12 else 0.0

    return {
        "n": int(len(rows)),
        "alpha_pct": round(alpha, 6),
        "alpha_pct_annualised_252d": round(alpha * 252.0, 6),
        "beta_mom": round(b_mom, 6),
        "beta_qual": round(b_qual, 6),
        "beta_vol": round(b_vol, 6),
        "factor_means": {
            "mom": round(f_mean_mom, 6),
            "qual": round(f_mean_qual, 6),
            "vol": round(f_mean_vol, 6),
        },
        "beta_contrib_abs": round(beta_contrib, 6),
        "alpha_share_pct": round(100.0 * alpha_share, 2),
        "residual_std_pct": round(resid_std, 6),
    }


def analyze_all(picks: list[dict],
                min_n: int = DEFAULT_MIN_N,
                mom_window: int = DEFAULT_MOM_WINDOW,
                qual_window: int = DEFAULT_QUAL_WINDOW) -> dict:
    by_strategy: dict[str, list[dict]] = defaultdict(list)
    for p in picks:
        by_strategy[p.get("strategy") or "unknown"].append(p)
    benchmark_daily = _aggregate_daily(picks)
    factors = build_factors(benchmark_daily, mom_window, qual_window)
    out: list[dict] = []
    for strat, sub in by_strategy.items():
        daily = _aggregate_daily(sub)
        attr = attribute_strategy(daily, factors, min_n)
        if attr is None:
            continue
        attr["strategy"] = strat
        out.append(attr)
    out.sort(key=lambda r: -r["alpha_share_pct"])
    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "config": {"min_n": min_n, "mom_window": mom_window,
                   "qual_window": qual_window},
        "n_strategies_analysed": len(out),
        "n_benchmark_days": len(benchmark_daily),
        "strategies": out,
    }


def write_markdown(summary: dict, path: Path) -> None:
    cfg = summary["config"]
    rows = summary["strategies"]
    lines: list[str] = []
    lines.append(f"# Factor Attribution — {summary['generated'][:10]}")
    lines.append("")
    lines.append("Generated by `tools/factor_attribution.py` — opt-in sidecar.")
    lines.append("")
    lines.append(
        "First-cut Fama-MacBeth-style decomposition. For each strategy with "
        f"n >= {cfg['min_n']} trading days, regresses daily PnL on three "
        "in-sample factor proxies (5d momentum, inverse vol, sign-of-day) "
        "built from the equal-weight benchmark. `alpha_share_pct` = 100 * "
        "|alpha| / (|alpha| + sum |beta_i * mean(F_i)|)."
    )
    lines.append("")
    lines.append("## Top 20 by alpha-share %")
    lines.append("")
    lines.append("| Strategy | n | alpha_pct | alpha-share % | b_mom | b_qual | b_vol |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for r in rows[:20]:
        lines.append(
            f"| {r['strategy']} | {r['n']} | {r['alpha_pct']:.4f} | "
            f"{r['alpha_share_pct']:.1f} | {r['beta_mom']:.3f} | "
            f"{r['beta_qual']:.3f} | {r['beta_vol']:.3f} |"
        )
    lines.append("")
    lines.append("## Wiring plan")
    lines.append("")
    lines.append(
        "Sidecar artifact only. Follow-up PR adds `alpha_share %` column to "
        "`audit_dashboard/template.html` strategy table."
    )
    lines.append("")
    with path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--min-n", type=int, default=DEFAULT_MIN_N)
    ap.add_argument("--mom-window", type=int, default=DEFAULT_MOM_WINDOW)
    ap.add_argument("--qual-window", type=int, default=DEFAULT_QUAL_WINDOW)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    with PICKS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    picks = data.get("picks", {}).get("recent_closed", [])

    summary = analyze_all(picks, args.min_n, args.mom_window, args.qual_window)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    md_path = OUT_MD_DIR / f"factor_attribution_{datetime.now(timezone.utc).strftime('%Y_%m_%d')}.md"
    write_markdown(summary, md_path)
    if not args.quiet:
        print(f"strategies: {summary['n_strategies_analysed']}")
        print(f"benchmark days: {summary['n_benchmark_days']}")
        for r in summary["strategies"][:10]:
            print(f"  {r['strategy']:<35} n={r['n']:>4} "
                  f"alpha_share={r['alpha_share_pct']:.1f}%  "
                  f"alpha={r['alpha_pct']:.4f}")
        print(f"JSON: {OUT_JSON}")
        print(f"MD:   {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
