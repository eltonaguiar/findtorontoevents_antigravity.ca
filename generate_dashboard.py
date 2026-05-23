#!/usr/bin/env python3
"""Generate HTML dashboard from live_picks.json."""

import json
from pathlib import Path


def generate():
    with open("dashboard/live_picks.json") as f:
        data = json.load(f)

    rows = ""
    for pick in data["active_picks"]:
        side_class = "long" if pick["side"] == "LONG" else "short"
        pnl_class = "positive" if pick["unrealized_pnl_pct"] > 0 else "negative"
        rows += f"""
        <tr>
            <td>{pick['symbol']}</td>
            <td>{pick['strategy']}</td>
            <td>{pick['system']}</td>
            <td><span class="badge {side_class}">{pick['side']}</span></td>
            <td>${pick['entry_price']:.4f}</td>
            <td>${pick['current_price']:.4f}</td>
            <td class="{pnl_class}">{pick['unrealized_pnl_pct']:+.2f}%</td>
            <td>{pick['bars_held']}</td>
        </tr>"""

    active = data["summary"]["active"]
    closed = data["summary"]["closed_today"]
    pnl_unreal_class = "positive" if active["total_unrealized_pnl"] > 0 else "negative"
    pnl_real_class = "positive" if closed["total_realized_pnl"] > 0 else "negative"

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Live Picks Dashboard</title>
    <meta http-equiv="refresh" content="60">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }}
        .header {{ background: #16213e; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .metric {{ display: inline-block; margin: 10px 20px; }}
        .metric-value {{ font-size: 32px; font-weight: bold; }}
        .positive {{ color: #4caf50; }}
        .negative {{ color: #f44336; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #333; }}
        th {{ background: #0f3460; }}
        tr:hover {{ background: #1a1a2e; }}
        .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; }}
        .long {{ background: #4caf50; }}
        .short {{ background: #f44336; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Live Picks Dashboard</h1>
        <p>Last updated: {data['generated_at']}</p>
        <div class="metric">
            <div>Active Picks</div>
            <div class="metric-value">{active['total_active']}</div>
        </div>
        <div class="metric">
            <div>Unrealized P/L</div>
            <div class="metric-value {pnl_unreal_class}">
                {active['total_unrealized_pnl']:+.2f}%
            </div>
        </div>
        <div class="metric">
            <div>Closed Today</div>
            <div class="metric-value">{closed['total_closed']}</div>
        </div>
        <div class="metric">
            <div>Realized Today</div>
            <div class="metric-value {pnl_real_class}">
                {closed['total_realized_pnl']:+.2f}%
            </div>
        </div>
    </div>

    <h2>Active Picks</h2>
    <table>
        <tr>
            <th>Symbol</th>
            <th>Strategy</th>
            <th>System</th>
            <th>Side</th>
            <th>Entry</th>
            <th>Current</th>
            <th>P/L %</th>
            <th>Bars</th>
        </tr>
        {rows}
    </table>
</body>
</html>"""

    Path("dashboard/index.html").write_text(html)
    print("Dashboard updated: dashboard/index.html")


if __name__ == "__main__":
    generate()
