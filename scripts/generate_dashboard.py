#!/usr/bin/env python3
"""
================================================================================
Dashboard Generator for EXTREME Signal Backtests
================================================================================

Generates an HTML dashboard from backtest results.

Usage:
    python generate_dashboard.py --backtest-dir backtest_results/ \
                                  --template-dir templates/dashboard \
                                  --output-dir docs/dashboard \
                                  --date 2026-02-14
================================================================================
"""

import argparse
import json
import glob
from pathlib import Path
from datetime import datetime


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CryptoAlpha Pro - Backtest Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Inter', sans-serif; }}
        .font-mono {{ font-family: 'JetBrains Mono', monospace; }}
    </style>
</head>
<body class="bg-slate-950 text-slate-100">
    <div class="max-w-7xl mx-auto px-4 py-8">
        <!-- Header -->
        <header class="mb-8">
            <div class="flex items-center justify-between">
                <div>
                    <h1 class="text-3xl font-bold">CryptoAlpha Pro</h1>
                    <p class="text-slate-400">EXTREME Signal Backtest Dashboard</p>
                </div>
                <div class="text-right">
                    <p class="text-sm text-slate-500">Generated</p>
                    <p class="text-amber-400 font-mono">{date}</p>
                </div>
            </div>
        </header>

        <!-- Summary Cards -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div class="bg-slate-900 rounded-xl border border-slate-800 p-4">
                <div class="text-sm text-slate-500">Avg Sharpe</div>
                <div class="text-2xl font-bold text-amber-400">{avg_sharpe:.2f}</div>
                <div class="text-xs text-slate-600">vs Swarm 1.0-1.5</div>
            </div>
            <div class="bg-slate-900 rounded-xl border border-slate-800 p-4">
                <div class="text-sm text-slate-500">Avg Win Rate</div>
                <div class="text-2xl font-bold text-green-400">{avg_win_rate:.1f}%</div>
                <div class="text-xs text-slate-600">vs Swarm 60-70%</div>
            </div>
            <div class="bg-slate-900 rounded-xl border border-slate-800 p-4">
                <div class="text-sm text-slate-500">Avg Max DD</div>
                <div class="text-2xl font-bold text-green-400">{avg_max_dd:.1f}%</div>
                <div class="text-xs text-slate-600">vs Swarm 15-20%</div>
            </div>
            <div class="bg-slate-900 rounded-xl border border-slate-800 p-4">
                <div class="text-sm text-slate-500">Total Signals</div>
                <div class="text-2xl font-bold text-white">{total_signals}</div>
                <div class="text-xs text-slate-600">Across all assets</div>
            </div>
        </div>

        <!-- Asset Performance -->
        <div class="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden mb-8">
            <div class="p-6 border-b border-slate-800">
                <h2 class="text-xl font-bold">Asset Performance</h2>
            </div>
            <table class="w-full">
                <thead>
                    <tr class="text-slate-500 border-b border-slate-800 text-sm">
                        <th class="text-left py-4 px-6">Asset</th>
                        <th class="text-left py-4 px-6">Trades</th>
                        <th class="text-left py-4 px-6">Win Rate</th>
                        <th class="text-left py-4 px-6">Sharpe</th>
                        <th class="text-left py-4 px-6">Max DD</th>
                        <th class="text-left py-4 px-6">Return</th>
                        <th class="text-left py-4 px-6">vs Swarm</th>
                    </tr>
                </thead>
                <tbody>
                    {asset_rows}
                </tbody>
            </table>
        </div>

        <!-- Swarm Comparison -->
        <div class="bg-slate-900 rounded-xl border border-slate-800 p-6 mb-8">
            <h2 class="text-xl font-bold mb-4">Comparison to Swarm Research</h2>
            <div class="grid md:grid-cols-3 gap-6">
                <div class="p-4 bg-slate-950 rounded-lg">
                    <div class="text-sm text-slate-500 mb-2">Sharpe Ratio</div>
                    <div class="flex items-center gap-2">
                        <span class="text-amber-400 font-mono">{avg_sharpe:.2f}</span>
                        <span class="text-slate-600">vs</span>
                        <span class="text-slate-400 font-mono">1.0-1.5</span>
                    </div>
                    <div class="text-xs text-green-400 mt-1">{sharpe_status}</div>
                </div>
                <div class="p-4 bg-slate-950 rounded-lg">
                    <div class="text-sm text-slate-500 mb-2">Win Rate</div>
                    <div class="flex items-center gap-2">
                        <span class="text-amber-400 font-mono">{avg_win_rate:.1f}%</span>
                        <span class="text-slate-600">vs</span>
                        <span class="text-slate-400 font-mono">60-70%</span>
                    </div>
                    <div class="text-xs text-green-400 mt-1">{win_rate_status}</div>
                </div>
                <div class="p-4 bg-slate-950 rounded-lg">
                    <div class="text-sm text-slate-500 mb-2">Max Drawdown</div>
                    <div class="flex items-center gap-2">
                        <span class="text-amber-400 font-mono">{avg_max_dd:.1f}%</span>
                        <span class="text-slate-600">vs</span>
                        <span class="text-slate-400 font-mono">15-20%</span>
                    </div>
                    <div class="text-xs text-green-400 mt-1">{max_dd_status}</div>
                </div>
            </div>
        </div>

        <!-- Recent Signals -->
        <div class="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
            <div class="p-6 border-b border-slate-800">
                <h2 class="text-xl font-bold">Recent EXTREME Signals</h2>
            </div>
            <div class="p-6">
                {signals_html}
            </div>
        </div>

        <footer class="mt-8 pt-8 border-t border-slate-800 text-center text-sm text-slate-600">
            <p>CryptoAlpha Pro - Automated Backtest Dashboard</p>
            <p class="mt-1">Generated from Kimi Agent Swarm research integration</p>
        </footer>
    </div>
</body>
</html>
"""


def load_backtest_results(backtest_dir: str) -> list:
    """Load all backtest JSON files"""
    results = []
    pattern = Path(backtest_dir) / "*_backtest.json"
    
    for file_path in glob.glob(str(pattern)):
        with open(file_path) as f:
            data = json.load(f)
            results.append(data)
    
    return results


def generate_asset_rows(results: list) -> str:
    """Generate table rows for each asset"""
    rows = []
    
    for result in results:
        asset = result.get('asset', 'Unknown')
        metrics = result.get('metrics', {})
        comparison = result.get('swarm_comparison', {})
        
        trades = metrics.get('total_trades', 0)
        win_rate = metrics.get('win_rate', 0) * 100
        sharpe = metrics.get('sharpe_ratio', 0)
        max_dd = metrics.get('max_drawdown_pct', 0)
        return_pct = metrics.get('total_return_pct', 0)
        
        # Determine overall status
        statuses = [v.get('status', 'UNKNOWN') for v in comparison.values()]
        if all(s == 'EXCEED' for s in statuses):
            status_color = 'text-green-400'
            status_text = '✓ EXCEEDS'
        elif all(s in ['EXCEED', 'MEET'] for s in statuses):
            status_color = 'text-amber-400'
            status_text = '✓ MEETS'
        else:
            status_color = 'text-red-400'
            status_text = '✗ BELOW'
        
        row = f"""
                    <tr class="border-b border-slate-800/50">
                        <td class="py-4 px-6 font-semibold">{asset}</td>
                        <td class="py-4 px-6">{trades}</td>
                        <td class="py-4 px-6">{win_rate:.1f}%</td>
                        <td class="py-4 px-6 font-mono">{sharpe:.2f}</td>
                        <td class="py-4 px-6 text-red-400">{max_dd:.1f}%</td>
                        <td class="py-4 px-6 text-green-400">+{return_pct:.1f}%</td>
                        <td class="py-4 px-6 {status_color}">{status_text}</td>
                    </tr>
        """
        rows.append(row)
    
    return ''.join(rows)


def generate_signals_html(results: list) -> str:
    """Generate HTML for recent signals"""
    all_signals = []
    
    for result in results:
        asset = result.get('asset', 'Unknown')
        for signal in result.get('signals', [])[-3:]:  # Last 3 signals per asset
            signal['asset'] = asset
            all_signals.append(signal)
    
    # Sort by timestamp (most recent first)
    all_signals.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    if not all_signals:
        return "<p class='text-slate-500'>No EXTREME signals generated in backtest period.</p>"
    
    html_parts = []
    for signal in all_signals[:10]:  # Show top 10
        asset = signal.get('asset', 'Unknown')
        timestamp = signal.get('timestamp', 'Unknown')[:10]
        entry = signal.get('entry_price', 0)
        tp1 = signal.get('take_profit_1', 0)
        tp3 = signal.get('take_profit_3', 0)
        conviction = signal.get('conviction_score', 0)
        
        html_parts.append(f"""
            <div class="flex items-center justify-between p-4 bg-slate-950 rounded-lg mb-2">
                <div class="flex items-center gap-4">
                    <div class="w-12 h-12 rounded-lg bg-amber-500/20 flex items-center justify-center text-amber-400 font-bold">
                        {asset[0]}
                    </div>
                    <div>
                        <div class="font-semibold">{asset} <span class="text-amber-400">EXTREME</span></div>
                        <div class="text-sm text-slate-500">{timestamp} • Score: {conviction:.0f}/100</div>
                    </div>
                </div>
                <div class="text-right">
                    <div class="font-mono text-sm">${entry:,.0f} → ${tp3:,.0f}</div>
                    <div class="text-xs text-green-400">+{((tp3/entry)-1)*100:.1f}% potential</div>
                </div>
            </div>
        """)
    
    return ''.join(html_parts)


def calculate_summary_stats(results: list) -> dict:
    """Calculate aggregate statistics"""
    sharpes = []
    win_rates = []
    max_dds = []
    total_signals = 0
    
    for result in results:
        metrics = result.get('metrics', {})
        if 'sharpe_ratio' in metrics:
            sharpes.append(metrics['sharpe_ratio'])
        if 'win_rate' in metrics:
            win_rates.append(metrics['win_rate'] * 100)
        if 'max_drawdown_pct' in metrics:
            max_dds.append(abs(metrics['max_drawdown_pct']))
        total_signals += len(result.get('signals', []))
    
    return {
        'avg_sharpe': sum(sharpes) / len(sharpes) if sharpes else 0,
        'avg_win_rate': sum(win_rates) / len(win_rates) if win_rates else 0,
        'avg_max_dd': sum(max_dds) / len(max_dds) if max_dds else 0,
        'total_signals': total_signals
    }


def get_status_text(avg_sharpe: float, avg_win_rate: float, avg_max_dd: float) -> dict:
    """Determine status text for each metric"""
    return {
        'sharpe': 'EXCEEDS expectations' if avg_sharpe > 1.5 else 'MEETS expectations' if avg_sharpe >= 1.0 else 'Below expectations',
        'win_rate': 'EXCEEDS expectations' if avg_win_rate > 70 else 'MEETS expectations' if avg_win_rate >= 60 else 'Below expectations',
        'max_dd': 'EXCEEDS expectations' if avg_max_dd < 15 else 'MEETS expectations' if avg_max_dd <= 20 else 'Below expectations'
    }


def main():
    parser = argparse.ArgumentParser(description='Generate backtest dashboard')
    parser.add_argument('--backtest-dir', required=True, help='Directory containing backtest JSON files')
    parser.add_argument('--template-dir', required=True, help='Directory containing HTML templates')
    parser.add_argument('--output-dir', required=True, help='Output directory for dashboard')
    parser.add_argument('--date', default=datetime.now().strftime('%Y-%m-%d'), help='Dashboard date')
    
    args = parser.parse_args()
    
    print(f"Generating dashboard from {args.backtest_dir}...")
    
    # Load backtest results
    results = load_backtest_results(args.backtest_dir)
    print(f"Loaded {len(results)} backtest results")
    
    if not results:
        print("No backtest results found!")
        return
    
    # Calculate stats
    stats = calculate_summary_stats(results)
    status_texts = get_status_text(stats['avg_sharpe'], stats['avg_win_rate'], stats['avg_max_dd'])
    
    # Generate HTML
    html = HTML_TEMPLATE.format(
        date=args.date,
        avg_sharpe=stats['avg_sharpe'],
        avg_win_rate=stats['avg_win_rate'],
        avg_max_dd=stats['avg_max_dd'],
        total_signals=stats['total_signals'],
        asset_rows=generate_asset_rows(results),
        signals_html=generate_signals_html(results),
        sharpe_status=status_texts['sharpe'],
        win_rate_status=status_texts['win_rate'],
        max_dd_status=status_texts['max_dd']
    )
    
    # Save dashboard
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    dashboard_file = output_path / 'index.html'
    with open(dashboard_file, 'w') as f:
        f.write(html)
    
    print(f"Dashboard saved to: {dashboard_file}")
    print(f"\nSummary:")
    print(f"  Avg Sharpe: {stats['avg_sharpe']:.2f}")
    print(f"  Avg Win Rate: {stats['avg_win_rate']:.1f}%")
    print(f"  Avg Max DD: {stats['avg_max_dd']:.1f}%")
    print(f"  Total Signals: {stats['total_signals']}")


if __name__ == '__main__':
    main()
