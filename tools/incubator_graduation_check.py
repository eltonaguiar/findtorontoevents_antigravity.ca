#!/usr/bin/env python3
"""Incubator graduation bridge — run the graduation gate against the live data.

The incubator has TWO disconnected forward-test systems sharing
`incubator/forward_test.db`:
  - the signal scanner writes `forward_summary` (189 strategies: win_rate,
    sharpe, total_pnl_pct, max_drawdown_pct, total_closed, ...);
  - `forward_test_tracker.py`'s graduation gate reads its OWN `strategies` /
    `forward_trades` tables — which were never created in this DB. So the gate
    has never evaluated a single real strategy.

This bridge maps each `forward_summary` row to the `metrics` dict
`StrategyGraduationCriteria.check()` consumes and reports which strategies
actually clear the gate. It answers the real question — "does the incubator
hold any graduate-ready signal source?" — with live data.

Caveat: `forward_summary` is aggregate-only; it has no test-start date, so the
`min_forward_days` criterion cannot be evaluated here (reported as UNKNOWN,
not failed). The walk-forward stability sub-gate is skipped — `forward_summary`
carries no per-window pnl.

    python tools/incubator_graduation_check.py [--db PATH] [--out report.md]
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "incubator" / "testing"))
DB = ROOT / "incubator" / "forward_test.db"

try:
    from forward_test_tracker import StrategyGraduationCriteria, EarlyHatchCriteria
except Exception as exc:  # noqa: BLE001
    print(f"ERROR: cannot import graduation criteria: {exc}", file=sys.stderr)
    raise SystemExit(2)


def _metrics_from_summary(row: dict) -> dict:
    """Map a forward_summary row to the graduation `metrics` dict.

    forward_summary stores win_rate / max_drawdown as 0-100 or 0-1? It is
    written by the scanner as a fraction for win_rate and a percent for
    max_drawdown_pct. Normalise: win_rate -> [0,1]; max_drawdown -> [0,1].
    """
    wr = float(row.get("win_rate") or 0)
    if wr > 1.5:                       # stored as percent
        wr /= 100.0
    mdd = float(row.get("max_drawdown_pct") or 0)
    if mdd > 1.5:
        mdd /= 100.0
    return {
        "win_rate": wr,
        "sharpe": float(row.get("sharpe") or 0),
        "max_drawdown": abs(mdd),
        "pnl_pct": float(row.get("total_pnl_pct") or 0),
        "trades_count": int(row.get("total_closed") or 0),
        # no test-start date in forward_summary -> days check cannot run;
        # set high so the days criterion does not false-fail the quality screen.
        "days_in_test": 9999,
    }


def run(db_path: Path) -> dict:
    if not db_path.exists():
        sys.exit(f"ERROR: {db_path} not found")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute("SELECT * FROM forward_summary")]
    conn.close()
    std = StrategyGraduationCriteria()
    hatch = EarlyHatchCriteria()
    results = []
    for r in rows:
        m = _metrics_from_summary(r)
        std_pass, std_reasons = std.check(m)
        # EarlyHatch.check signature mirrors Standard; guard if it differs.
        try:
            hatch_pass, hatch_reasons = hatch.check(m)
        except Exception:  # noqa: BLE001
            hatch_pass, hatch_reasons = None, ["hatch check unavailable"]
        results.append({
            "strategy": r.get("strategy_name"),
            "wr": m["win_rate"], "sharpe": m["sharpe"], "mdd": m["max_drawdown"],
            "pnl": m["pnl_pct"], "trades": m["trades_count"],
            "std_pass": std_pass, "std_reasons": std_reasons,
            "hatch_pass": hatch_pass,
        })
    return {"n": len(rows), "results": results}


def render(r: dict) -> str:
    res = r["results"]
    std_grads = [x for x in res if x["std_pass"]]
    hatch_grads = [x for x in res if x["hatch_pass"] and not x["std_pass"]]
    out = [
        "# Incubator Graduation Check — live forward_summary data",
        "",
        f"Bridged {r['n']} forward-tested strategies from "
        f"`incubator/forward_test.db::forward_summary` through the graduation "
        f"gate (`StrategyGraduationCriteria` + `EarlyHatchCriteria`).",
        "",
        f"- **Standard-graduation passes: {len(std_grads)} / {r['n']}**",
        f"- Early-hatch-only passes: {len(hatch_grads)}",
        "",
        "`min_forward_days` is not evaluated (forward_summary has no start "
        "date); these are *quality-bar* passes — WR / Sharpe / MDD / PnL / "
        "trades only.",
        "",
    ]
    if std_grads:
        out += ["## Standard-graduation candidates", "",
                "| strategy | WR | Sharpe | MDD | PnL% | trades |",
                "|---|---|---|---|---|---|"]
        for x in sorted(std_grads, key=lambda z: -z["sharpe"]):
            out.append(f"| {x['strategy']} | {x['wr']*100:.1f}% | {x['sharpe']:.2f} "
                       f"| {x['mdd']*100:.1f}% | {x['pnl']:+.1f}% | {x['trades']} |")
    else:
        out.append("**No strategy clears the standard graduation quality bar.**")
    out.append("")
    if hatch_grads:
        out += ["## Early-hatch-only candidates", "",
                "| strategy | WR | Sharpe | MDD | PnL% | trades |",
                "|---|---|---|---|---|---|"]
        for x in sorted(hatch_grads, key=lambda z: -z["sharpe"]):
            out.append(f"| {x['strategy']} | {x['wr']*100:.1f}% | {x['sharpe']:.2f} "
                       f"| {x['mdd']*100:.1f}% | {x['pnl']:+.1f}% | {x['trades']} |")
        out.append("")
    # top failers by why
    from collections import Counter
    fail_reasons = Counter()
    for x in res:
        if not x["std_pass"]:
            for rsn in x["std_reasons"]:
                fail_reasons[rsn.split(":")[0]] += 1
    out += ["## Why strategies fail the standard bar (n)", ""]
    for rsn, n in fail_reasons.most_common():
        out.append(f"- {rsn}: {n}")
    out += ["",
            "## Verdict",
            "",
            (f"{len(std_grads)} of {r['n']} forward-tested strategies clear the "
             "graduation quality bar — these are the incubator's graduate-ready "
             "signal-source candidates. Next: run each through "
             "`tools/edge_stability_harness.py` for walk-forward confirmation "
             "before live sizing."
             if std_grads else
             "No forward-tested strategy clears the graduation quality bar. The "
             "incubator currently holds no graduate-ready signal source — "
             "consistent with reports/EDGE_VERDICT_2026-05-18.md.")]
    return "\n".join(out)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=DB)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    report = render(run(args.db))
    if args.out:
        args.out.write_text(report, encoding="utf-8")
        print(f"# wrote {args.out}", file=sys.stderr)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
