#!/usr/bin/env python3
"""Daily per-sleeve summary for the $2k paper plan.

Reads the committed sleeve state + the latest daily report, computes n / net / CI /
drawdown / gate status per sleeve, and writes audit_dashboard/data/sleeve_summary.json.
Prints a short human table so a workflow step summary (or an agent) can post it to COMS.

No DB access: everything comes from committed JSON, so the summary is reproducible from
the repo alone. A sleeve's "forward n" is its number of *distinct daily marks*; that is
the clock this job reports, not a substitute for audit3's forward gate.
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STATE = REPO / "paper_trading" / "data" / "sleeves_state.json"
DAILY = REPO / "audit_dashboard" / "data" / "sleeve_daily.json"
OUT = REPO / "audit_dashboard" / "data" / "sleeve_summary.json"

#: paper-sleeve tiers; deliberately looser labels than audit3 so nobody confuses them
COLLECTING_N = 30
OBSERVING_N = 100


def _returns(history: list[dict]) -> list[float]:
    eq = [float(h["equity"]) for h in history if h.get("equity")]
    return [(eq[i] / eq[i - 1] - 1.0) * 100.0 for i in range(1, len(eq)) if eq[i - 1]]


def _mean_ci(rs: list[float]) -> tuple[float | None, list[float] | None]:
    if len(rs) < 2:
        return None, None
    mean = sum(rs) / len(rs)
    var = sum((r - mean) ** 2 for r in rs) / (len(rs) - 1)
    se = math.sqrt(var / len(rs))
    return round(mean, 5), [round(mean - 1.96 * se, 5), round(mean + 1.96 * se, 5)]


def summarise(state: dict, daily: dict) -> dict:
    rows = []
    for s in daily.get("sleeves", []):
        sid = s["id"]
        hist = ((state.get("sleeves") or {}).get(sid) or {}).get("history") or []
        rs = _returns(hist)
        mean, ci = _mean_ci(rs)
        n = len({h["date"] for h in hist})
        if n < COLLECTING_N:
            status = "collecting"
        elif n < OBSERVING_N:
            status = "observing"
        else:
            status = "eligible_for_review" if (ci and ci[0] > 0) else "observing_no_edge"
        rows.append({
            **{k: s.get(k) for k in ("id", "kind", "symbol", "asset_class", "capital",
                                     "equity", "return_pct", "drawdown_pct",
                                     "last_rebalance", "picks", "positions")},
            "n_marks": n,
            "daily_mean_pct": mean,
            "daily_ci_pct": ci,
            "status": status,
        })
    return {
        "schema": "paper.sleeve_summary.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "as_of": daily.get("as_of"),
        "tiers": {"collecting_n": COLLECTING_N, "observing_n": OBSERVING_N},
        "sleeves": rows,
        "note": "Paper clock only. audit3's forward gate (n>=100, net CI>0 at 2x cost, "
                "DSR>=0.95) remains the only promotion path.",
    }


def render(summary: dict) -> str:
    lines = [f"sleeves as of {summary['as_of']}"]
    for r in summary["sleeves"]:
        eq = r.get("equity") or 0
        lines.append(
            f"  {r['id']:22} {r['status']:18} n={r['n_marks']:<3} "
            f"eq=${eq:,.2f} ret={r.get('return_pct') or 0:+.2f}% "
            f"dd={r.get('drawdown_pct') or 0:+.2f}% "
            f"picks={','.join(r.get('picks') or []) or '-'}")
    return "\n".join(lines)


def main() -> int:
    if not STATE.exists() or not DAILY.exists():
        print("ERROR: missing sleeve state or daily report; run paper_trading.sleeves first",
              file=sys.stderr)
        return 2
    summary = summarise(json.loads(STATE.read_text()), json.loads(DAILY.read_text()))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=1) + "\n")
    print(render(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
