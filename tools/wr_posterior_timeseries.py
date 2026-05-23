"""Bayesian decay tracker — Beta-Bernoulli WR posterior over time.

Reads closed picks chronologically and computes the posterior at every
Nth cumulative trade. Surfaces a decay flag when the latest P(WR > 50%)
has dropped >= 0.30 from the rolling-max over the strategy's history,
catching strategies whose posterior is decaying BEFORE their PnL turns.

This is the leading-indicator counterpart to the existing point-estimate
wr_posterior.py: instead of asking "is this strategy net-positive given
ALL history?" it asks "did this strategy used to be a winner and stop?"

Reuses tools/wr_posterior.py:posterior_stats via importlib so we share
the same Jeffreys-prior math.

Wiring status: OPT-IN SIDECAR. No production caller. A follow-up PR will
render decay-flag badges on audit_dashboard/template.html strategy table
sourcing tools/data/wr_posterior_timeseries.json.

Known limitations
-----------------
1. Like every other supplement that reads closed-pick labels, the
   underlying win/loss labels come from outcome_resolver.py — partially
   contaminated for FOREX/COMMODITY pending the cloud agent's Theme B.
2. Picks within a regime are correlated; the independence assumption
   makes credible intervals tighter than reality. Document, defer.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PICKS_PATH = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_JSON = REPO_ROOT / "tools" / "data" / "wr_posterior_timeseries.json"
OUT_MD_DIR = REPO_ROOT / "reports"

DEFAULT_MIN_N = 20
DEFAULT_STEP = 10
DEFAULT_DECAY_DROP = 0.30


def _load_posterior_stats():
    spec = importlib.util.spec_from_file_location(
        "wr_posterior", REPO_ROOT / "tools" / "wr_posterior.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.posterior_stats


def _parse_iso(s: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (TypeError, ValueError, AttributeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def compute_strategy_timeseries(picks: list[dict],
                                step: int = DEFAULT_STEP,
                                min_n: int = DEFAULT_MIN_N,
                                decay_drop: float = DEFAULT_DECAY_DROP,
                                posterior_stats=None) -> dict | None:
    if posterior_stats is None:
        posterior_stats = _load_posterior_stats()

    cleaned: list[tuple[datetime, int]] = []
    skipped = 0
    for p in picks:
        pnl = p.get("pnl_pct")
        if pnl is None:
            skipped += 1
            continue
        try:
            pnl_f = float(pnl)
        except (TypeError, ValueError):
            skipped += 1
            continue
        ts_raw = p.get("closed_at") or p.get("opened_at")
        ts = _parse_iso(ts_raw) if ts_raw else None
        if ts is None:
            skipped += 1
            continue
        win = 1 if pnl_f > 0 else 0
        cleaned.append((ts, win))

    if len(cleaned) < min_n:
        return None

    cleaned.sort(key=lambda x: x[0])

    series: list[dict] = []
    cumulative_wins = 0
    cumulative_n = 0
    for i, (ts, win) in enumerate(cleaned, start=1):
        cumulative_n = i
        cumulative_wins += win
        if i % step == 0 or i == len(cleaned):
            stats = posterior_stats(cumulative_wins, cumulative_n)
            series.append({
                "n": cumulative_n,
                "wins": cumulative_wins,
                "ts": ts.isoformat(),
                "posterior_mean": round(stats["posterior_mean"], 4),
                "ci_low_95": round(stats["ci_low_95"], 4),
                "ci_high_95": round(stats["ci_high_95"], 4),
                "p_above_50": round(stats["p_wr_above_50"], 4),
            })

    if not series:
        return None

    p_above_values = [s["p_above_50"] for s in series]
    rolling_max = max(p_above_values)
    latest = p_above_values[-1]
    decay_amount = rolling_max - latest
    decay_flag = decay_amount >= decay_drop

    return {
        "series": series,
        "rolling_max_p_above_50": round(rolling_max, 4),
        "latest_p_above_50": round(latest, 4),
        "decay_amount": round(decay_amount, 4),
        "decay_flag": decay_flag,
        "n_total": len(cleaned),
        "n_skipped": skipped,
    }


def analyze_all(picks: list[dict],
                step: int = DEFAULT_STEP,
                min_n: int = DEFAULT_MIN_N,
                decay_drop: float = DEFAULT_DECAY_DROP) -> dict:
    posterior_stats = _load_posterior_stats()
    by_strategy: dict[str, list[dict]] = defaultdict(list)
    for p in picks:
        by_strategy[p.get("strategy") or "unknown"].append(p)

    out: list[dict] = []
    for strat, sub in by_strategy.items():
        ts = compute_strategy_timeseries(sub, step, min_n, decay_drop,
                                         posterior_stats=posterior_stats)
        if ts is None:
            continue
        ts["strategy"] = strat
        out.append(ts)

    out.sort(key=lambda x: (-x["decay_amount"], x["strategy"]))
    decay_flagged = [r for r in out if r["decay_flag"]]
    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "config": {"step": step, "min_n": min_n, "decay_drop_threshold": decay_drop},
        "n_strategies": len(out),
        "n_decay_flagged": len(decay_flagged),
        "strategies": out,
    }


def write_markdown(summary: dict, path: Path) -> None:
    cfg = summary["config"]
    n_total = summary["n_strategies"]
    n_flag = summary["n_decay_flagged"]
    lines: list[str] = []
    lines.append(f"# WR Posterior Time-Series — {summary['generated'][:10]}")
    lines.append("")
    lines.append("Generated by `tools/wr_posterior_timeseries.py` — opt-in sidecar.")
    lines.append("")
    lines.append(
        "Bayesian decay tracker. For every strategy with n >= "
        f"{cfg['min_n']}, computes the Beta-Bernoulli posterior at every "
        f"{cfg['step']}th cumulative trade. Flags decay when the latest "
        f"P(WR > 50%) has dropped >= {cfg['decay_drop_threshold']} from the "
        "rolling-max over the strategy's full history."
    )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Strategies analysed: **{n_total}**")
    lines.append(f"- Decay-flagged strategies: **{n_flag}**")
    lines.append(f"- Step: every {cfg['step']}th trade")
    lines.append(f"- Decay threshold: drop in P(WR>50%) >= {cfg['decay_drop_threshold']}")
    lines.append("")

    if n_flag > 0:
        lines.append("## Decay-flagged strategies")
        lines.append("")
        lines.append("| Strategy | n | rolling-max P(>50%) | latest P(>50%) | drop |")
        lines.append("|---|---:|---:|---:|---:|")
        for r in [s for s in summary["strategies"] if s["decay_flag"]][:20]:
            lines.append(
                f"| {r['strategy']} | {r['n_total']} | "
                f"{r['rolling_max_p_above_50']:.3f} | "
                f"{r['latest_p_above_50']:.3f} | "
                f"{r['decay_amount']:.3f} |"
            )
        lines.append("")

    lines.append("## Top 20 by trade volume (latest posterior)")
    lines.append("")
    lines.append("| Strategy | n | last n step | last P(>50%) | flagged? |")
    lines.append("|---|---:|---:|---:|:---:|")
    by_n = sorted(summary["strategies"], key=lambda x: -x["n_total"])
    for r in by_n[:20]:
        flag = "DECAY" if r["decay_flag"] else "ok"
        lines.append(
            f"| {r['strategy']} | {r['n_total']} | "
            f"{r['series'][-1]['n']} | "
            f"{r['latest_p_above_50']:.3f} | {flag} |"
        )
    lines.append("")
    lines.append("## Wiring plan")
    lines.append("")
    lines.append(
        "Sidecar artifact only. Follow-up PR renders a decay badge "
        "next to existing strategy rows on `audit_dashboard/template.html`, "
        "sourcing `tools/data/wr_posterior_timeseries.json`. Combined with "
        "the existing wr_posterior.py + notarizer + anomaly canary + "
        "preregistration verifier, this gives the audit five cooperating "
        "Bayesian credibility supplements."
    )
    lines.append("")
    with path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--step", type=int, default=DEFAULT_STEP)
    ap.add_argument("--min-n", type=int, default=DEFAULT_MIN_N)
    ap.add_argument("--decay-drop", type=float, default=DEFAULT_DECAY_DROP)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    with PICKS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    picks = data.get("picks", {}).get("recent_closed", [])

    summary = analyze_all(picks, args.step, args.min_n, args.decay_drop)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    md_path = OUT_MD_DIR / f"wr_posterior_timeseries_{datetime.now(timezone.utc).strftime('%Y_%m_%d')}.md"
    write_markdown(summary, md_path)

    if not args.quiet:
        print(f"strategies analysed: {summary['n_strategies']}")
        print(f"decay-flagged: {summary['n_decay_flagged']}")
        for r in [s for s in summary["strategies"] if s["decay_flag"]][:10]:
            print(f"  DECAY {r['strategy']:<35} drop={r['decay_amount']:.3f} "
                  f"({r['rolling_max_p_above_50']:.3f} -> "
                  f"{r['latest_p_above_50']:.3f})")
        print(f"JSON: {OUT_JSON}")
        print(f"MD:   {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
