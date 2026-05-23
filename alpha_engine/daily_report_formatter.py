"""
daily_report_formatter.py — Render daily_report dicts as Markdown, HTML, or plain text.

Stdlib only: json, datetime.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pct(v: float) -> str:
    """Format float as percentage string."""
    return f"{v * 100:.2f}%"


def _pnl_arrow(v: float) -> str:
    return "▲" if v > 0 else ("▼" if v < 0 else "—")


def _severity_icon(level: str) -> str:
    return {"CRITICAL": "🔴", "WARNING": "🟡", "INFO": "🔵"}.get(level, "⚪")


# ===========================================================================
#  MARKDOWN  (Slack / Discord friendly)
# ===========================================================================

def format_markdown(report: Dict[str, Any]) -> str:
    """Format report as Markdown suitable for Slack."""
    lines: List[str] = []
    d = report.get("date", "?")

    lines.append(f"📊 *Alpha Engine Daily Report — {d}*")
    lines.append("")

    # --- Overall ---
    o = report.get("overall", {})
    lines.append("*Overall Performance*")
    lines.append(f"  Win Rate: {_pct(o.get('win_rate', 0))}  |  "
                 f"Profit Factor: {o.get('profit_factor', 0):.2f}  |  "
                 f"Avg PnL: {_pct(o.get('avg_pnl', 0))}")
    lines.append(f"  Median PnL: {_pct(o.get('median_pnl', 0))}  |  "
                 f"Trades Today: {o.get('trades_today', 0)}  |  "
                 f"Trades 7d: {o.get('trades_7d', 0)}")
    lines.append("")

    # --- By Asset Class ---
    bac = report.get("by_asset_class", {})
    if bac:
        lines.append("*By Asset Class*")
        for ac, m in bac.items():
            lines.append(f"  `{ac}`  n={m['n']}  WR={_pct(m['win_rate'])}  "
                         f"PF={m['profit_factor']:.2f}  Avg={_pct(m['avg_pnl'])}")
        lines.append("")

    # --- Top Systems ---
    systems = report.get("by_system", [])
    if systems:
        lines.append(f"*Top {len(systems)} Systems*")
        for i, s in enumerate(systems, 1):
            lines.append(f"  {i}. `{s['system']}`  n={s['n']}  "
                         f"WR={_pct(s['win_rate'])}  PF={s['profit_factor']:.2f}  "
                         f"Avg={_pct(s['avg_pnl'])}")
        lines.append("")

    # --- Big Movers ---
    movers = report.get("big_movers", [])
    if movers:
        lines.append(f"*Big Movers* (|PnL| > 3%)")
        for m in movers[:10]:
            arrow = _pnl_arrow(m["pnl"])
            lines.append(f"  {arrow} `{m['symbol']}` ({m['system']})  "
                         f"PnL: {m['pnl_pct']:+.2f}%  at {m['closed_at']}")
        lines.append("")

    # --- Kill Candidates ---
    kills = report.get("kill_candidates", [])
    if kills:
        lines.append(f"*⚠️ Kill Candidates* ({len(kills)})")
        for k in kills:
            lines.append(f"  🔴 `{k['system']}`  n={k['n']}  "
                         f"WR={_pct(k['win_rate'])}  PF={k['profit_factor']:.2f}")
            lines.append(f"     Reason: {k['reason']}")
        lines.append("")

    # --- Exposure Warnings ---
    expos = report.get("exposure_warnings", [])
    if expos:
        lines.append(f"*⚠️ Exposure Warnings* ({len(expos)})")
        for w in expos:
            lines.append(f"  🟡 `{w['symbol']}` at {w['weight_pct']:.1f}% "
                         f"(limit {w['limit_pct']:.1f}%) — {w['action']}")
        lines.append("")

    # --- HF Tier Summary ---
    hf = report.get("hf_tier_summary", {})
    if hf:
        lines.append("*HF Tier Summary*")
        lines.append(f"  S: {hf.get('S', 0)}  |  A: {hf.get('A', 0)}  |  "
                     f"B: {hf.get('B', 0)}  |  non-HF: {hf.get('non_hf', 0)}")
        lines.append("")

    # --- Data Lag ---
    lag = report.get("data_lag_hours")
    if lag is not None:
        lag_icon = "🟢" if lag < 1 else ("🟡" if lag < 4 else "🔴")
        lines.append(f"{lag_icon} Data Lag: {lag:.1f}h")
        lines.append("")

    # --- Policy Status ---
    ps = report.get("policy_status", {})
    if ps:
        lines.append(f"*Policy*  v={ps.get('version', '?')}  "
                     f"last_change={ps.get('last_change', '?')}")
        lines.append("")

    lines.append(f"_Generated at {report.get('generated_at', '?')}_")
    return "\n".join(lines)


# ===========================================================================
#  HTML
# ===========================================================================

def format_html(report: Dict[str, Any]) -> str:
    """Format report as a self-contained HTML document."""
    d = report.get("date", "?")
    o = report.get("overall", {})

    parts: List[str] = []
    parts.append(f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Alpha Engine Daily Report — {d}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         max-width: 860px; margin: 2rem auto; color: #1a1a2e; background: #f8f9fa; }}
  h1 {{ color: #16213e; border-bottom: 2px solid #0f3460; padding-bottom: .5rem; }}
  h2 {{ color: #0f3460; margin-top: 1.8rem; }}
  table {{ border-collapse: collapse; width: 100%; margin: .5rem 0 1rem; }}
  th, td {{ border: 1px solid #dee2e6; padding: 6px 10px; text-align: right; }}
  th {{ background: #0f3460; color: #fff; }}
  tr:nth-child(even) {{ background: #e9ecef; }}
  .alert {{ padding: 8px 12px; border-radius: 4px; margin: 4px 0; }}
  .critical {{ background: #f8d7da; color: #721c24; }}
  .warning  {{ background: #fff3cd; color: #856404; }}
  .ok       {{ background: #d4edda; color: #155724; }}
  .tag {{ display: inline-block; padding: 2px 8px; border-radius: 3px;
          font-size: .85rem; margin-right: 4px; }}
  .tag-s {{ background: #ffd700; color: #333; }}
  .tag-a {{ background: #c0c0c0; color: #333; }}
  .tag-b {{ background: #cd7f32; color: #fff; }}
  code {{ background: #e9ecef; padding: 1px 4px; border-radius: 3px; }}
  footer {{ margin-top: 2rem; font-size: .85rem; color: #6c757d; }}
</style></head><body>""")

    parts.append(f"<h1>📊 Alpha Engine Daily Report — {d}</h1>")

    # Overall
    parts.append("<h2>Overall Performance</h2><table>")
    for label, key in [("Win Rate", "win_rate"), ("Profit Factor", "profit_factor"),
                       ("Avg PnL", "avg_pnl"), ("Median PnL", "median_pnl"),
                       ("Trades Today", "trades_today"), ("Trades 7d", "trades_7d")]:
        val = o.get(key, 0)
        if key in ("win_rate", "avg_pnl", "median_pnl"):
            val = _pct(val)
        elif key == "profit_factor":
            val = f"{val:.2f}"
        parts.append(f"<tr><td style='text-align:left;font-weight:bold'>{label}</td>"
                     f"<td>{val}</td></tr>")
    parts.append("</table>")

    # By Asset Class
    bac = report.get("by_asset_class", {})
    if bac:
        parts.append("<h2>By Asset Class</h2><table>"
                     "<tr><th>Class</th><th>N</th><th>Win Rate</th>"
                     "<th>Profit Factor</th><th>Avg PnL</th></tr>")
        for ac, m in bac.items():
            parts.append(f"<tr><td style='text-align:left'><code>{ac}</code></td>"
                         f"<td>{m['n']}</td><td>{_pct(m['win_rate'])}</td>"
                         f"<td>{m['profit_factor']:.2f}</td>"
                         f"<td>{_pct(m['avg_pnl'])}</td></tr>")
        parts.append("</table>")

    # Top Systems
    systems = report.get("by_system", [])
    if systems:
        parts.append(f"<h2>Top {len(systems)} Systems</h2><table>"
                     "<tr><th>#</th><th>System</th><th>N</th><th>Win Rate</th>"
                     "<th>Profit Factor</th><th>Avg PnL</th></tr>")
        for i, s in enumerate(systems, 1):
            parts.append(f"<tr><td>{i}</td><td style='text-align:left'>"
                         f"<code>{s['system']}</code></td><td>{s['n']}</td>"
                         f"<td>{_pct(s['win_rate'])}</td>"
                         f"<td>{s['profit_factor']:.2f}</td>"
                         f"<td>{_pct(s['avg_pnl'])}</td></tr>")
        parts.append("</table>")

    # Big Movers
    movers = report.get("big_movers", [])
    if movers:
        parts.append(f"<h2>Big Movers (|PnL| &gt; 3%)</h2><table>"
                     "<tr><th>Symbol</th><th>System</th><th>PnL %</th><th>Closed At</th></tr>")
        for m in movers[:10]:
            cls = "ok" if m["pnl"] > 0 else "critical"
            parts.append(f"<tr class='{cls}'><td style='text-align:left'>"
                         f"<code>{m['symbol']}</code></td>"
                         f"<td style='text-align:left'>{m['system']}</td>"
                         f"<td>{m['pnl_pct']:+.2f}%</td>"
                         f"<td>{m['closed_at']}</td></tr>")
        parts.append("</table>")

    # Kill Candidates
    kills = report.get("kill_candidates", [])
    if kills:
        parts.append(f"<h2>⚠️ Kill Candidates ({len(kills)})</h2>")
        for k in kills:
            parts.append(f"<div class='alert critical'>"
                         f"<strong>{k['system']}</strong> — n={k['n']}, "
                         f"WR={_pct(k['win_rate'])}, PF={k['profit_factor']:.2f}<br>"
                         f"<small>{k['reason']}</small></div>")

    # Exposure Warnings
    expos = report.get("exposure_warnings", [])
    if expos:
        parts.append(f"<h2>⚠️ Exposure Warnings ({len(expos)})</h2>")
        for w in expos:
            parts.append(f"<div class='alert warning'>"
                         f"<strong>{w['symbol']}</strong> at {w['weight_pct']:.1f}% "
                         f"(limit {w['limit_pct']:.1f}%) — {w['action']}</div>")

    # HF Tier
    hf = report.get("hf_tier_summary", {})
    if hf:
        parts.append("<h2>HF Tier Summary</h2><table>"
                     "<tr><th>S</th><th>A</th><th>B</th><th>Non-HF</th></tr>")
        parts.append(f"<tr><td><span class='tag tag-s'>{hf.get('S',0)}</span></td>"
                     f"<td><span class='tag tag-a'>{hf.get('A',0)}</span></td>"
                     f"<td><span class='tag tag-b'>{hf.get('B',0)}</span></td>"
                     f"<td>{hf.get('non_hf',0)}</td></tr></table>")

    # Data Lag
    lag = report.get("data_lag_hours")
    if lag is not None:
        lag_cls = "ok" if lag < 1 else ("warning" if lag < 4 else "critical")
        parts.append(f"<div class='alert {lag_cls}'>Data Lag: {lag:.1f}h</div>")

    # Policy
    ps = report.get("policy_status", {})
    if ps:
        parts.append(f"<h2>Policy</h2><p>Version: <code>{ps.get('version','?')}</code>"
                     f" &nbsp;|&nbsp; Last change: {ps.get('last_change','?')}</p>")

    parts.append(f"<footer>Generated at {report.get('generated_at', '?')}</footer>")
    parts.append("</body></html>")
    return "\n".join(parts)


# ===========================================================================
#  PLAIN TEXT
# ===========================================================================

def format_text(report: Dict[str, Any]) -> str:
    """Format report as plain text for CLI output."""
    lines: List[str] = []
    d = report.get("date", "?")
    sep = "=" * 60

    lines.append(sep)
    lines.append(f"  Alpha Engine Daily Report — {d}")
    lines.append(sep)

    # Overall
    o = report.get("overall", {})
    lines.append("")
    lines.append("OVERALL PERFORMANCE")
    lines.append(f"  Win Rate     : {_pct(o.get('win_rate', 0))}")
    lines.append(f"  Profit Factor: {o.get('profit_factor', 0):.2f}")
    lines.append(f"  Avg PnL      : {_pct(o.get('avg_pnl', 0))}")
    lines.append(f"  Median PnL   : {_pct(o.get('median_pnl', 0))}")
    lines.append(f"  Trades Today : {o.get('trades_today', 0)}")
    lines.append(f"  Trades 7d    : {o.get('trades_7d', 0)}")

    # By Asset Class
    bac = report.get("by_asset_class", {})
    if bac:
        lines.append("")
        lines.append("BY ASSET CLASS")
        lines.append(f"  {'Class':<12} {'N':>5} {'WR':>8} {'PF':>8} {'Avg PnL':>10}")
        lines.append(f"  {'-'*12} {'-'*5} {'-'*8} {'-'*8} {'-'*10}")
        for ac, m in bac.items():
            lines.append(f"  {ac:<12} {m['n']:>5} {_pct(m['win_rate']):>8} "
                         f"{m['profit_factor']:>8.2f} {_pct(m['avg_pnl']):>10}")

    # Top Systems
    systems = report.get("by_system", [])
    if systems:
        lines.append("")
        lines.append(f"TOP {len(systems)} SYSTEMS")
        lines.append(f"  {'#':>3} {'System':<20} {'N':>5} {'WR':>8} {'PF':>8} {'Avg':>10}")
        lines.append(f"  {'-'*3} {'-'*20} {'-'*5} {'-'*8} {'-'*8} {'-'*10}")
        for i, s in enumerate(systems, 1):
            lines.append(f"  {i:>3} {s['system']:<20} {s['n']:>5} "
                         f"{_pct(s['win_rate']):>8} {s['profit_factor']:>8.2f} "
                         f"{_pct(s['avg_pnl']):>10}")

    # Big Movers
    movers = report.get("big_movers", [])
    if movers:
        lines.append("")
        lines.append("BIG MOVERS (|PnL| > 3%)")
        for m in movers[:10]:
            arrow = _pnl_arrow(m["pnl"])
            lines.append(f"  {arrow} {m['symbol']:<12} {m['system']:<15} "
                         f"{m['pnl_pct']:>+8.2f}%  {m['closed_at']}")

    # Kill Candidates
    kills = report.get("kill_candidates", [])
    if kills:
        lines.append("")
        lines.append(f"KILL CANDIDATES ({len(kills)})")
        for k in kills:
            lines.append(f"  [X] {k['system']:<20} n={k['n']:<4} "
                         f"WR={_pct(k['win_rate']):<8} PF={k['profit_factor']:.2f}")
            lines.append(f"      {k['reason']}")

    # Exposure Warnings
    expos = report.get("exposure_warnings", [])
    if expos:
        lines.append("")
        lines.append(f"EXPOSURE WARNINGS ({len(expos)})")
        for w in expos:
            lines.append(f"  [!] {w['symbol']:<12} {w['weight_pct']:.1f}% "
                         f"(limit {w['limit_pct']:.1f}%) — {w['action']}")

    # HF Tier
    hf = report.get("hf_tier_summary", {})
    if hf:
        lines.append("")
        lines.append("HF TIER SUMMARY")
        lines.append(f"  S={hf.get('S',0)}  A={hf.get('A',0)}  "
                     f"B={hf.get('B',0)}  non-HF={hf.get('non_hf',0)}")

    # Data Lag
    lag = report.get("data_lag_hours")
    if lag is not None:
        lines.append("")
        status = "OK" if lag < 1 else ("WARN" if lag < 4 else "CRITICAL")
        lines.append(f"DATA LAG: {lag:.1f}h [{status}]")

    # Policy
    ps = report.get("policy_status", {})
    if ps:
        lines.append("")
        lines.append(f"POLICY: v={ps.get('version','?')}  "
                     f"last_change={ps.get('last_change','?')}")

    lines.append("")
    lines.append(sep)
    lines.append(f"Generated at {report.get('generated_at', '?')}")
    return "\n".join(lines)


# ===========================================================================
#  Dispatcher
# ===========================================================================

_FORMATTERS = {
    "markdown": format_markdown,
    "md": format_markdown,
    "html": format_html,
    "text": format_text,
    "txt": format_text,
    "plain": format_text,
}


def format_report(report: Dict[str, Any], fmt: str = "markdown") -> str:
    """Format a daily report dict.  fmt ∈ {markdown, html, text}."""
    fn = _FORMATTERS.get(fmt.lower())
    if fn is None:
        raise ValueError(f"Unknown format '{fmt}'. Choose from: {', '.join(_FORMATTERS)}")
    return fn(report)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Format a daily report JSON")
    parser.add_argument("input", nargs="?", default=None,
                        help="Path to report JSON (default: stdin)")
    parser.add_argument("--format", "-f", default="markdown",
                        choices=["markdown", "html", "text"],
                        help="Output format")
    parser.add_argument("--output", "-o", default=None,
                        help="Write to file (default: stdout)")
    args = parser.parse_args()

    if args.input:
        with open(args.input, "r") as f:
            report = json.load(f)
    else:
        report = json.load(sys.stdin)

    result = format_report(report, args.format)

    if args.output:
        with open(args.output, "w") as f:
            f.write(result)
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(result)
