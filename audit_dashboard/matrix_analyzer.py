import json
import os
import math
import numpy as np
from pathlib import Path
import re

DATA_DIR = Path(__file__).parent / "data"
STATE_FILE = DATA_DIR / "claudes_test_state.json"
UPDATES_FILE = Path(__file__).parent.parent / "updates" / "index.html"

def calculate_sharpe(returns, risk_free_rate=0.0):
    if len(returns) < 2:
        return 0.0
    mean_ret = np.mean(returns)
    std_dev = np.std(returns, ddof=1)
    if std_dev == 0:
        return 0.0
    # Annualizing assuming Returns are per trade, but let's just use standard Sharpe
    return (mean_ret - risk_free_rate) / std_dev

def calculate_sortino(returns, risk_free_rate=0.0):
    if len(returns) < 2:
        return 0.0
    mean_ret = np.mean(returns)
    downside_returns = [r for r in returns if r < 0]
    if not downside_returns:
        return 99.0 # Arbitrary high number if no downside
    downside_dev = np.sqrt(np.mean(np.square(downside_returns)))
    if downside_dev == 0:
        return 99.0
    return (mean_ret - risk_free_rate) / downside_dev

def generate_matrix():
    if not os.path.exists(STATE_FILE):
        print(f"State file not found at {STATE_FILE}")
        return
        
    with open(STATE_FILE, 'r') as f:
        state = json.load(f)

    # Aggregate trades by strategy
    strategy_trades = {}
    
    for _, portfolio in state.items():
        if "closed" in portfolio:
            for trade in portfolio["closed"]:
                strat = trade.get("strategy", "unknown")
                if strat not in strategy_trades:
                    strategy_trades[strat] = {"returns": [], "wins": 0, "losses": 0, "pnl": 0.0}
                
                ret = trade.get("pnl_pct", 0)
                strategy_trades[strat]["returns"].append(ret)
                strategy_trades[strat]["pnl"] += ret
                if ret > 0:
                    strategy_trades[strat]["wins"] += 1
                else:
                    strategy_trades[strat]["losses"] += 1

    # Calculate metrics
    results = []
    for strat, data in strategy_trades.items():
        trades = data["wins"] + data["losses"]
        if trades == 0:
            continue
        wr = (data["wins"] / trades) * 100
        returns_arr = np.array(data["returns"])
        sharpe = calculate_sharpe(returns_arr)
        sortino = calculate_sortino(returns_arr)
        
        results.append({
            "strategy": strat,
            "trades": trades,
            "wr": wr,
            "pnl": data["pnl"],
            "sharpe": sharpe,
            "sortino": sortino
        })

    # Sort by Net PnL descending
    results.sort(key=lambda x: x["pnl"], reverse=True)
    
    return results

def patch_html(matrix_results):
    if not os.path.exists(UPDATES_FILE):
        print(f"Updates html not found at {UPDATES_FILE}")
        return

    with open(UPDATES_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the Strategy table marker
    marker = '<h4 style="color:#a78bfa; margin-top:12px;">By Strategy (ranked by P&amp;L)</h4>'
    idx = content.find(marker)
    if idx == -1:
        print("Marker not found in html.")
        return

    table_start = content.find('<table', idx)
    table_end = content.find('</table>', table_start) + len('</table>')
    
    # Build new table
    new_table = [
        '<table style="width:100%; border-collapse:collapse; margin:8px 0; font-size:0.85em;">',
        '  <tr style="border-bottom:1px solid #2a2a3e; background:#1a1a2e;">',
        '    <th style="text-align:left; padding:4px;">Strategy</th>',
        '    <th style="text-align:center; padding:4px;">Trades</th>',
        '    <th style="text-align:center; padding:4px;">WR</th>',
        '    <th style="text-align:right; padding:4px;">Net PnL</th>',
        '    <th style="text-align:right; padding:4px;">Sharpe</th>',
        '    <th style="text-align:right; padding:4px;">Sortino</th>',
        '  </tr>'
    ]
    
    for row in matrix_results[:20]: # Only show top 20
        pnl_color = "#22c55e" if row["pnl"] > 0 else ("#ef4444" if row["pnl"] < 0 else "inherit")
        pnl_str = f'+${row["pnl"]:.2f}' if row["pnl"] >= 0 else f'-${abs(row["pnl"]):.2f}'
        wr_str = f'{row["wr"]:.0f}%'
        
        sharpe_color = "#22c55e" if row["sharpe"] > 1 else ("#ef4444" if row["sharpe"] < 0 else "inherit")
        sortino_color = "#22c55e" if row["sortino"] > 1.5 else ("#ef4444" if row["sortino"] < 0 else "inherit")
        
        new_table.append(f'  <tr style="border-bottom:1px solid #1a1a2e; color:{pnl_color};">')
        new_table.append(f'    <td style="padding:3px;"><code>{row["strategy"]}</code></td>')
        new_table.append(f'    <td style="text-align:center; padding:3px;">{row["trades"]}</td>')
        new_table.append(f'    <td style="text-align:center; padding:3px;">{wr_str}</td>')
        new_table.append(f'    <td style="text-align:right; padding:3px;">{pnl_str}</td>')
        new_table.append(f'    <td style="text-align:right; padding:3px; color:{sharpe_color};">{row["sharpe"]:.2f}</td>')
        new_table.append(f'    <td style="text-align:right; padding:3px; color:{sortino_color};">{row["sortino"]:.2f}</td>')
        new_table.append('  </tr>')
        
    new_table.append('</table>')
    
    new_content = content[:table_start] + '\n'.join(new_table) + content[table_end:]
    
    with open(UPDATES_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Matrix successfully updated in index.html")

if __name__ == "__main__":
    matrix = generate_matrix()
    if matrix:
        patch_html(matrix)
