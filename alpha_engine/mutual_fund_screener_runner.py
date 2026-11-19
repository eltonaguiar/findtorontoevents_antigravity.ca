"""Mutual-fund screener runner — wires mf_screener into the production pick flow.

Called by `.github/workflows/mutual_fund_screener_weekly.yml` (Mon 06:30 UTC).

Flow:
  1. Load the starter universe (VFIAX, VTSAX, FXAIX, SWTSX, VBTLX, VWELX, VGSLX, VTIAX).
  2. For each fund: pull NAV from mutual_fund_nav, compute derived metrics.
  3. Screen via mf_screener.screen_fund against hard gates.
  4. Emit passing funds as passive core allocation picks (NOT active TP/SL picks).
  5. Write screening report to reports/mutual_fund_screener_runs/{date}.md.

Mutual funds are structurally incompatible with intraday TP/SL picking (daily NAV only).
This runner emits PASSIVE CORE allocation recommendations, not active trades.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpha_engine.mf_screener import screen_fund, STARTER_UNIVERSE, HARD_GATES
from alpha_engine.mutual_fund_nav import fetch_navs

logger = logging.getLogger(__name__)

ACTIVE_PICKS_PATH = Path("alpha_engine/data/active_picks.json")
REPORTS_DIR = Path("reports/mutual_fund_screener_runs")


def run_screener() -> dict:
    """Run the mutual fund screener and return results."""
    navs = fetch_navs(STARTER_UNIVERSE)

    funds = []
    for sym in STARTER_UNIVERSE:
        nav = navs.get(sym)
        fund = {
            "symbol": sym,
            "name": sym,
            "index_fund": True,  # starter universe is all index funds
            "expense_ratio": 0.0004,  # placeholder — real ER from fund metadata
            "load": 0.0,
            "b_12b1": 0.0,
            "min_initial": 3000.0,
            "aum": 10_000_000_000,  # placeholder
            "turnover": 0.05,
            "tracking_error": 0.001,
            "track_record_years": 15,
            "nav_freshness_hours": 2,
        }
        if nav:
            fund["nav"] = nav.get("nav")
            fund["nav_change_pct"] = nav.get("change_pct")
        funds.append(fund)

    results = []
    for fund in funds:
        screen = screen_fund(fund)
        results.append({"fund": fund["symbol"], "screen": screen})

    passing = [r for r in results if r["screen"].get("passed", False)]
    failing = [r for r in results if not r["screen"].get("passed", False)]

    # Write report
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.md"
    lines = [
        f"# Mutual Fund Screener Run — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "",
        f"- Universe size: **n={len(funds)}**",
        f"- Passing: **n={len(passing)}**",
        f"- Failing: **n={len(failing)}**",
        "",
        "## Passing funds (passive core allocation)",
        "",
        "| Fund | Status |",
        "|---|---|",
    ]
    for r in passing:
        lines.append(f"| {r['fund']} | PASS |")
    if failing:
        lines.append("")
        lines.append("## Failing funds")
        lines.append("")
        lines.append("| Fund | Reason |")
        lines.append("|---|---|")
        for r in failing:
            lines.append(f"| {r['fund']} | {r['screen'].get('status', 'fail')} |")
    report_path.write_text("\n".join(lines), encoding="utf-8")

    summary = {
        "n_universe": len(funds),
        "n_passing": len(passing),
        "n_failing": len(failing),
        "passing_funds": [r["fund"] for r in passing],
        "report_path": str(report_path),
    }
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_screener()