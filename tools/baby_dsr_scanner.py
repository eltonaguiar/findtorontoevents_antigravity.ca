#!/usr/bin/env python3
"""baby_dsr_scanner.py — per-strategy Deflated Sharpe Ratio scan of the baby
strategy forward ledger.

The multi-AI consensus (2026-05-17) asked to "batch-DSR-scan the ~213
baby_strategies; wire the top three that hit DSR>=0.95". This is the scanner
(part (b) of the feasibility plan). It is READ-ONLY and runs zero-config.

DATA REALITY (verified 2026-05-17): the baby strategies are data-starved —
the forward ledger `battleground/data/closed_picks.json` holds ~126 closed
picks across ~7 strategies, and only the strategies with n >= MIN_TRADES are
DSR-eligible. So today this scanner reports mostly INSUFFICIENT_DATA; it
becomes meaningful as the `baby-strat-forward-paper` workflow accumulates
forward picks. Build the tool now, let the verdict ripen with the data.

DSR multiple-testing burden: nb_trials = the count of baby strategy
definitions in `baby_strategies/` (each is a trial in the Bailey/Lopez de
Prado sense). More trials => larger Sharpe haircut => stricter DSR.

USAGE
-----
    python tools/baby_dsr_scanner.py [--dsr-threshold 0.95] [--quiet]

Writes `reports/baby_dsr_scan_<UTC>.md`. Exit 0 always (read-only report).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from datetime import datetime, timezone

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from alpha_engine.money_ready_verdict import _dsr_gate  # noqa: E402
from tools.dsr_audit import group_returns  # noqa: E402

# _dsr_gate returns dsr_score=None for n < this (too small for DSR at all).
MIN_TRADES = 10
# A true wire candidate also needs the charter n>=100 floor. A DSR>=0.95 on a
# handful of trades is small-sample saturation (the annualisation blows the
# Sharpe up), NOT a real edge — so DSR-pass at n<100 is only "provisional".
MIN_N_WIRE = 100

# The baby-strategy FORWARD ledger (paper outcomes), distinct from the
# production alpha_engine ledger.
LEDGER = os.path.join(REPO_ROOT, "battleground", "data", "closed_picks.json")
BABY_DIR = os.path.join(REPO_ROOT, "baby_strategies")
OUT_DIR = os.path.join(REPO_ROOT, "reports")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _baby_strategy_count() -> int:
    """nb_trials for the DSR haircut — one per baby strategy definition."""
    n = len(glob.glob(os.path.join(BABY_DIR, "*.py")))
    return max(n, 1)


def _load_ledger() -> list[dict]:
    if not os.path.isfile(LEDGER):
        return []
    try:
        with open(LEDGER, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(data, dict):
        data = list(data.values())
    return [r for r in data if isinstance(r, dict)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dsr-threshold", type=float, default=0.95,
                    help="DSR flag threshold (default 0.95)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    picks = _load_ledger()
    by_strategy, _ = group_returns(picks)
    nb_trials = _baby_strategy_count()

    # Per-strategy DSR via the canonical _dsr_gate (probability in [0,1];
    # nb_trials applies the Bailey/Lopez de Prado multiple-testing haircut).
    # n < MIN_TRADES -> dsr_score None -> surfaced as INSUFFICIENT_DATA so the
    # data gap is visible, not hidden.
    rows: list[dict] = []
    insufficient: list[tuple[str, int]] = []
    for strat, rets in by_strategy.items():
        n = len(rets)
        gate = _dsr_gate(rets, nb_trials=nb_trials)
        dsr = gate.get("dsr_score")
        if dsr is None:
            insufficient.append((strat, n))
            continue
        wins = sum(1 for r in rets if r > 0)
        rows.append({
            "key": strat,
            "trades": n,
            "win_rate_pct": round(100.0 * wins / n, 1) if n else 0.0,
            "avg_pnl_pct": round(sum(rets) / n, 4) if n else 0.0,
            "dsr": dsr,
        })
    rows.sort(key=lambda r: r["dsr"], reverse=True)
    insufficient.sort(key=lambda kv: -kv[1])

    # A wire candidate must clear DSR AND the n>=100 charter floor.
    winners = [r for r in rows
               if r["dsr"] >= args.dsr_threshold and r["trades"] >= MIN_N_WIRE]
    provisional = [r for r in rows
                   if r["dsr"] >= args.dsr_threshold and r["trades"] < MIN_N_WIRE]

    lines = [
        "# Baby Strategy DSR Scan",
        "",
        f"- generated: {_now()}",
        f"- ledger: battleground/data/closed_picks.json ({len(picks)} picks)",
        f"- baby strategy definitions (nb_trials): {nb_trials}",
        f"- strategies with realized picks: {len(by_strategy)}",
        f"- DSR-eligible (n >= {MIN_TRADES}): {len(rows)}",
        f"- DSR >= {args.dsr_threshold} AND n >= {MIN_N_WIRE} "
        f"(true wire candidates): {len(winners)}",
        f"- DSR >= {args.dsr_threshold} but n < {MIN_N_WIRE} "
        f"(provisional — small-sample): {len(provisional)}",
        "",
    ]
    if rows:
        lines += ["## DSR-eligible strategies (ranked by DSR)", "",
                  "| strategy | n | WR% | avg pnl% | DSR | flag |",
                  "|---|---|---|---|---|---|"]
        for r in rows:
            if r["dsr"] >= args.dsr_threshold and r["trades"] >= MIN_N_WIRE:
                flag = "WIRE-CANDIDATE"
            elif r["dsr"] >= args.dsr_threshold:
                flag = "provisional (n<%d)" % MIN_N_WIRE
            else:
                flag = "below threshold"
            lines.append(
                f"| {r['key']} | {r['trades']} | {r['win_rate_pct']} | "
                f"{r['avg_pnl_pct']} | {r['dsr']} | {flag} |")
        lines.append("")
    if insufficient:
        lines += [f"## INSUFFICIENT_DATA (n < {MIN_TRADES} — not DSR-testable)",
                  ""]
        for s, n in insufficient:
            lines.append(f"- {s}: n={n}")
        lines.append("")
    if winners:
        lines += ["## Wire candidates (DSR >= threshold AND n >= %d)" %
                  MIN_N_WIRE, ""]
        for r in winners[:3]:
            lines.append(f"- **{r['key']}** — DSR {r['dsr']}, n={r['trades']}, "
                          f"WR {r['win_rate_pct']}%")
    else:
        lines.append("## Verdict: NO wire candidates")
        lines.append("")
        if provisional:
            lines.append(
                "%d strateg%s clear DSR >= %.2f but ALL have n < %d — that is "
                "small-sample DSR saturation (the annualisation inflates the "
                "Sharpe), not a real edge. Per the §26 plan + investigator "
                "verdict, the baby strategies are data-starved: re-run this "
                "scan as the baby-strat-forward-paper workflow accumulates "
                "picks toward the n>=100 floor." % (
                    len(provisional), "y" if len(provisional) == 1 else "ies",
                    args.dsr_threshold, MIN_N_WIRE))
        else:
            lines.append("No baby strategy clears DSR >= %.2f on current "
                          "forward data." % args.dsr_threshold)
    report = "\n".join(lines) + "\n"

    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = os.path.join(OUT_DIR, f"baby_dsr_scan_{stamp}.md")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(report)

    if not args.quiet:
        print(report)
    print(f"baby DSR scan written -> reports/baby_dsr_scan_{stamp}.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
