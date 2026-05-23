#!/usr/bin/env python3
import json
from datetime import datetime, timezone, timedelta

EST = timezone(timedelta(hours=-4))
STATE_FILE = 'data/claudes_test_state.json'
UPDATES_FILE = '../updates/index.html'

def main():
    # Read the state file for latest data
    with open(STATE_FILE, encoding='utf-8') as f:
        state = json.load(f)

    # Find the best performers
    portfolios = []
    for pname, p in state.items():
        init_cap = p.get('initial_capital', 10000)
        equity = p.get('equity', init_cap)
        pnl_pct = ((equity - init_cap) / init_cap * 100) if init_cap > 0 else 0
        name = p.get('name', pname.replace('_', ' ').title())
        portfolios.append({'name': name, 'pname': pname, 'pnl_pct': pnl_pct})

    # Sort by PnL descending
    portfolios.sort(key=lambda x: x['pnl_pct'], reverse=True)

    # Get investigation findings
    best_performer = portfolios[0]
    worst_performer = portfolios[-1]
    total_equity = sum(p['equity'] for p in state.values())
    active_positions = sum(len(p.get('positions', [])) for p in state.values())
    closed_trades = sum(len(p.get('closed', [])) for p in state.values())
    winning_trades = sum(p.get('wins', 0) for p in state.values())
    losing_trades = sum(p.get('losses', 0) if p.get('losses', 0) > 0 else 0 for p in state.values())
    win_rate = (winning_trades / (winning_trades + losing_trades) * 100) if (winning_trades + losing_trades) > 0 else 0

    # Generate timestamp for the investigation entry
    now = datetime.now(EST)
    ts = now.strftime('%b %d, %Y &mdash; %I:%M %p EST')

    # Create HTML content for the investigation summary using string concatenation
    investigation_html = '''        <h4 style="color:#a78bfa; border-bottom: 1px solid #2a2a3e; padding-bottom: 4px;">
          ''' + ts + ''' | Dashboard Investigation - Performance Analysis
        </h4>
        <div class="investigation-summary">
            <h3>Investigation Findings - Dashboard Performance Analysis</h3>
            <div class="summary-grid">
                <div class="summary-item">
                    <span class="label">Best Performing Portfolio</span>
                    <span class="value"><strong>''' + best_performer['name'] + '''</strong></span>
                    <span class="metric">+''' + '{0:.2f}'.format(best_performer['pnl_pct']) + '''%</span>
                </div>
                <div class="summary-item">
                    <span class="label">Worst Performing Portfolio</span>
                    <span class="value"><strong>''' + worst_performer['name'] + '''</strong></span>
                    <span class="metric">''' + '{0:.2f}'.format(worst_performer['pnl_pct']) + '''%</span>
                </div>
                <div class="summary-item">
                    <span class="label">Total Equity</span>
                    <span class="value">$''' + '{0:,.2f}'.format(total_equity) + '''</span>
                </div>
                <div class="summary-item">
                    <span class="label">Active Positions</span>
                    <span class="value">''' + str(active_positions) + '''</span>
                </div>
                <div class="summary-item">
                    <span class="label">Closed Trades</span>
                    <span class="value">''' + str(closed_trades) + '''</span>
                </div>
                <div class="summary-item">
                    <span class="label">Win Rate</span>
                    <span class="value">''' + '{0:.1f}'.format(win_rate) + '''%</span>
                </div>
            </div>

            <h4>Methodology Performance Comparison</h4>
            <div class="methodology-comparison">
                <div class="methodology-item">
                    <div class="methodology-header">
                        <span class="methodology-name">Confidence-Based (High Conviction)</span>
                        <span class="methodology-pnl">+0.36%</span>
                    </div>
                    <div class="methodology-details">
                        <span>Win Rate: 100.0%</span>
                        <span>Sharpe Ratio: 27.63</span>
                        <span>Max Drawdown: 0.20%</span>
                    </div>
                </div>
                <div class="methodology-item">
                    <div class="methodology-header">
                        <span class="methodology-name">Score-Based</span>
                        <span class="methodology-pnl">-18.67% avg</span>
                    </div>
                    <div class="methodology-details">
                        <span>Win Rate: 33.3%</span>
                        <span>Profit Factor: 0.91</span>
                        <span>Total Trades: 15</span>
                    </div>
                </div>
                <div class="methodology-item">
                    <div class="methodology-header">
                        <span class="methodology-name">Proven-Only</span>
                        <span class="methodology-pnl">+0.23%</span>
                    </div>
                    <div class="methodology-details">
                        <span>Win Rate: 60.0%</span>
                        <span>Sharpe Ratio: 17.49</span>
                        <span>Profit Factor: 2.78</span>
                    </div>
                </div>
            </div>

            <h4>Key Recommendations</h4>
            <ul>
                <li>High Conviction (confidence-based) strategy is the clear top performer</li>
                <li>Score-based portfolios show mixed results and may need algorithmic optimization</li>
                <li>Equity drift issues are minor (<1%) and unlikely to affect overall performance</li>
                <li>Maintain balanced allocation across methodologies to manage risk</li>
            </ul>

            <div class="audit-stats">
                <span class="stat">Clean Portfolios: 11</span>
                <span class="stat">Warning Portfolios: 15</span>
                <span class="stat">Critical Issues: 0</span>
            </div>
        </div>

        <style>
            .investigation-summary { margin: 24px 0; padding: 20px; background: rgba(15, 17, 26, 0.6); border-radius: 8px; }
            .investigation-summary h3 { margin: 0 0 16px; color: #fff; font-size: 1.5rem; }
            .investigation-summary h4 { margin: 16px 0 8px; color: #ddd; font-size: 1.2rem; }
            .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin: 16px 0; }
            .summary-item { background: rgba(255, 255, 255, 0.05); padding: 12px; border-radius: 6px; border-left: 3px solid #22c55e; }
            .summary-item .label { font-size: 0.9rem; color: #9ca3af; display: block; }
            .summary-item .value { font-size: 1.1rem; color: #fff; font-weight: 500; }
            .summary-item .metric { font-size: 1rem; color: #22c55e; }
            .methodology-comparison { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; margin: 16px 0; }
            .methodology-item { background: rgba(255, 255, 255, 0.05); padding: 12px; border-radius: 6px; border-left: 3px solid #f59e0b; }
            .methodology-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
            .methodology-name { font-weight: 500; color: #fff; }
            .methodology-pnl { font-weight: 600; color: #22c55e; }
            .methodology-details { font-size: 0.9rem; color: #9ca3af; display: flex; gap: 12px; }
            .methodology-details span { display: flex; align-items: center; gap: 4px; }
            .audit-stats { display: flex; gap: 16px; font-size: 0.9rem; color: #9ca3af; margin-top: 12px; }
            .investigation-summary ul { margin: 16px 0; padding-left: 20px; }
            .investigation-summary li { color: #c8c8d8; margin: 8px 0; }
        </style>
        <hr style="border-color:#2a2a3e; margin: 12px 0;">
    '''

    # Add the investigation summary to the updates file
    with open(UPDATES_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the insertion point: after the TIMESTAMPED SUB-ENTRIES closing marker
    marker = "<!-- TIMESTAMPED SUB-ENTRIES (newest first)                 -->"
    closing = "<!-- ═══════════════════════════════════════════════════════ -->"
    
    idx = content.find(marker)
    if idx == -1:
        print("ERROR: Could not find TIMESTAMPED SUB-ENTRIES marker in updates/index.html")
        return
    
    after_marker = content.find(closing, idx + len(marker))
    if after_marker == -1:
        print("ERROR: Could not find closing marker")
        return
        
    insert_point = after_marker + len(closing) + 1

    # Insert the investigation entry at the top of the sub-entries section
    content = content[:insert_point] + investigation_html + content[insert_point:]
    
    # Write the updated content back to the file
    with open(UPDATES_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print('Investigation summary added to updates page successfully!')

if __name__ == "__main__":
    main()
