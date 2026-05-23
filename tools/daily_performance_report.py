#!/usr/bin/env python3
"""
Daily Performance Report Generator (A8.2)
==========================================
Reads audit_dashboard/data/dashboard_data.json and writes a Markdown
performance snapshot to reports/daily_perf_<YYYYMMDD>.md.

Usage
-----
    python tools/daily_performance_report.py [--date YYYYMMDD]

Arguments
---------
--date YYYYMMDD
    Override the report date (default: today UTC).

Output
------
    reports/daily_perf_<YYYYMMDD>.md

Notes
-----
- Any auto-commit this script performs includes ``[skip ci]`` in the message.
- Never modify audit_dashboard/index.html.
- Never run audit_trail/dashboard_generator.py.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DATA = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
REPORTS_DIR = REPO_ROOT / "reports"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(v, default: float = 0.0) -> float:
    if v is None:
        return default
    try:
        f = float(v)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return default


def _pf_bar(pf: float) -> str:
    """Visual bar for profit factor (max 3.0 → 10 chars)."""
    filled = min(int(pf / 3.0 * 10), 10)
    return "[" + "#" * filled + "-" * (10 - filled) + "]"


def _load_dashboard() -> dict:
    if not DASHBOARD_DATA.exists():
        print(f"[daily_perf] ERROR: dashboard data not found at {DASHBOARD_DATA}", file=sys.stderr)
        sys.exit(1)
    with DASHBOARD_DATA.open(encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Report sections
# ---------------------------------------------------------------------------

def _section_header(data: dict, report_date: str) -> str:
    generated_at = data.get("generated_at", "unknown")
    lines = [
        f"# Daily Performance Report — {report_date}",
        "",
        f"_Dashboard data generated: {generated_at}_",
        f"_Report generated: {datetime.now(timezone.utc).isoformat()}_",
        "",
    ]
    return "\n".join(lines)


def _section_pnl_by_class(data: dict) -> str:
    ach = data.get("performance", {}).get("asset_class_health", {})
    if not ach:
        return "## P&L by Asset Class\n\n_No data available._\n\n"

    header = "## P&L by Asset Class\n\n"
    table_header = (
        "| Class     | n    | Win Rate | Profit Factor | Total P&L % | Status        |\n"
        "|-----------|------|----------|---------------|-------------|---------------|\n"
    )
    rows = []
    for cls, info in sorted(ach.items()):
        n = info.get("n", 0)
        wr = _safe_float(info.get("win_rate"))
        pf = _safe_float(info.get("profit_factor"))
        pnl = _safe_float(info.get("total_pnl_pct"))
        status = info.get("status", "unknown")
        rows.append(
            f"| {cls:<9s} | {n:<4d} | {wr:>7.1f}% | {pf:>13.2f} | {pnl:>+11.2f} | {status:<13s} |"
        )

    return header + table_header + "\n".join(rows) + "\n\n"


def _section_sharpe_drawdown(data: dict) -> str:
    hf = data.get("hf_stats", {}).get("hf_metrics", {})
    rolling = data.get("hf_stats", {}).get("rolling_current", {})

    sharpe = _safe_float(hf.get("sharpe_ratio") or rolling.get("sharpe"))
    max_dd = _safe_float(hf.get("max_drawdown") or rolling.get("max_drawdown"))
    calmar = _safe_float(hf.get("calmar_ratio") or rolling.get("calmar"))
    omega = _safe_float(hf.get("omega_ratio") or rolling.get("omega"))
    total_ret = _safe_float(hf.get("total_return"))

    lines = [
        "## Risk / Return Metrics",
        "",
        f"| Metric              | Value     |",
        f"|---------------------|-----------|",
        f"| Sharpe Ratio        | {sharpe:>+9.3f} |",
        f"| Max Drawdown        | {max_dd:>9.2f}% |",
        f"| Calmar Ratio        | {calmar:>+9.3f} |",
        f"| Omega Ratio         | {omega:>+9.3f} |",
        f"| Total Return (all)  | {total_ret:>+9.2f}% |",
        "",
    ]
    return "\n".join(lines) + "\n"


def _section_top_bottom(data: dict, n: int = 5) -> str:
    """Top-N and bottom-N strategies/picks by forward profit factor."""
    lb = data.get("leaderboard", [])
    if not lb:
        return "## Top / Bottom Strategies by Profit Factor\n\n_No leaderboard data._\n\n"

    # Filter entries that have fwd_pf
    valid = [
        e for e in lb
        if isinstance(e, dict) and e.get("fwd_pf") is not None and _safe_float(e.get("fwd_pf")) > 0
    ]
    if not valid:
        return "## Top / Bottom Strategies by Profit Factor\n\n_No entries with fwd_pf._\n\n"

    sorted_by_pf = sorted(valid, key=lambda x: _safe_float(x.get("fwd_pf")), reverse=True)
    top = sorted_by_pf[:n]
    bottom = sorted_by_pf[-n:][::-1]  # worst first

    def _fmt_row(e: dict) -> str:
        strat = str(e.get("strategy", "?"))[:35]
        cls = str(e.get("asset_class", "?"))[:8]
        pf = _safe_float(e.get("fwd_pf"))
        wr = _safe_float(e.get("fwd_wr"))
        trades = e.get("fwd_trades", 0)
        bar = _pf_bar(pf)
        return f"| {strat:<35s} | {cls:<8s} | {pf:>5.2f} {bar} | {wr:>6.1f}% | {trades:>6} |"

    col_header = (
        "| Strategy                            | Class    | Profit Factor         | Win Rate |  Trades |\n"
        "|-------------------------------------|----------|-----------------------|----------|---------|"
    )

    lines = [
        "## Top / Bottom Strategies by Profit Factor",
        "",
        f"### Top {n} (highest PF)",
        "",
        col_header,
    ]
    for e in top:
        lines.append(_fmt_row(e))
    lines += [
        "",
        f"### Bottom {n} (lowest PF)",
        "",
        col_header,
    ]
    for e in bottom:
        lines.append(_fmt_row(e))
    lines.append("")
    return "\n".join(lines) + "\n"


def _section_summary(data: dict) -> str:
    summary = data.get("summary", {})
    if not summary:
        return ""
    total_picks = summary.get("total_picks", "?")
    open_picks = summary.get("open_picks", "?")
    closed_picks = summary.get("closed_picks", "?")
    lines = [
        "## Pick Summary",
        "",
        f"| Metric        | Value |",
        f"|---------------|-------|",
        f"| Total picks   | {total_picks} |",
        f"| Open picks    | {open_picks} |",
        f"| Closed picks  | {closed_picks} |",
        "",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate_report(report_date: str | None = None) -> Path:
    """Generate the daily performance report and return the output path."""
    today = report_date or datetime.now(timezone.utc).strftime("%Y%m%d")
    output_path = REPORTS_DIR / f"daily_perf_{today}.md"

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    data = _load_dashboard()

    sections = [
        _section_header(data, today),
        _section_summary(data),
        _section_pnl_by_class(data),
        _section_sharpe_drawdown(data),
        _section_top_bottom(data, n=5),
        "---\n\n_Generated by `tools/daily_performance_report.py`. "
        "Auto-commits include `[skip ci]`._\n",
    ]

    report_md = "\n".join(sections)
    output_path.write_text(report_md, encoding="utf-8")

    print(f"[daily_perf] Report written to: {output_path}")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate daily performance report from dashboard_data.json"
    )
    parser.add_argument(
        "--date",
        metavar="YYYYMMDD",
        default=None,
        help="Override report date (default: today UTC)",
    )
    args = parser.parse_args()
    output_path = generate_report(report_date=args.date)
    print(f"[daily_perf] Done: {output_path}")


if __name__ == "__main__":
    main()
