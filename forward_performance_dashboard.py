#!/usr/bin/env python3
"""
Forward Performance Dashboard

Shows real-time comparison of backtest vs forward performance for Tier 1 strategies.
Answers the question: "If I traded these signals, would I be making money?"

Key Metrics:
- Backtest vs Forward Win Rate
- Backtest vs Forward Sharpe
- Realized P&L (closed trades)
- Unrealized P&L (open positions)
- Drawdown tracking
- Signal accuracy
"""

import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

DB_PATH = Path("incubator/forward_test.db")
TIERED_RESULTS = Path("battleground/data/tiered_backtest_results_20260227_160805.json")
DASHBOARD_FILE = Path("battleground/data/forward_performance_dashboard.json")


class ForwardPerformanceDashboard:
    """Tracks and displays forward vs backtest performance"""
    
    def __init__(self):
        self.db_path = DB_PATH
        self.tiered_results = TIERED_RESULTS
        self.dashboard_file = DASHBOARD_FILE
    
    def get_tier1_backtest_data(self) -> Dict[str, Dict]:
        """Get backtest performance for Tier 1 strategies"""
        if not self.tiered_results.exists():
            return {}
        
        with open(self.tiered_results, 'r') as f:
            data = json.load(f)
        
        backtest_data = {}
        for name, result in data['results']['tier_1'].items():
            if result.get('passed') and result.get('best_result'):
                br = result['best_result']
                backtest_data[name] = {
                    'sharpe': br.get('sharpe_ratio', 0),
                    'win_rate': br.get('win_rate', 0),
                    'max_dd': br.get('max_drawdown', 0),
                    'trades': br.get('trades', 0),
                    'total_return': br.get('total_return', 0),
                    'pair': br.get('pair', 'N/A'),
                    'direction': br.get('direction', 'LONG'),
                    'agent_id': result.get('source', 'unknown')
                }
        
        return backtest_data
    
    def get_forward_performance(self, strategy_name: str) -> Dict:
        """Get forward test performance for a strategy"""
        if not self.db_path.exists():
            return {}
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get live trades
        cursor.execute('''
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN status = 'CLOSED' AND realized_pnl_pct > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN status = 'CLOSED' THEN 1 ELSE 0 END) as closed_trades,
                SUM(CASE WHEN status = 'CLOSED' THEN realized_pnl_pct ELSE 0 END) as realized_pnl,
                SUM(CASE WHEN status = 'OPEN' THEN unrealized_pnl_pct ELSE 0 END) as unrealized_pnl,
                AVG(CASE WHEN status = 'CLOSED' THEN realized_pnl_pct END) as avg_trade_pnl,
                MAX(CASE WHEN status = 'CLOSED' THEN realized_pnl_pct END) as best_trade,
                MIN(CASE WHEN status = 'CLOSED' THEN realized_pnl_pct END) as worst_trade
            FROM live_trades
            WHERE strategy_name = ?
        ''', (strategy_name,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row or row[0] == 0:
            return {'has_data': False}
        
        total, wins, closed, realized, unrealized, avg_pnl, best, worst = row
        
        return {
            'has_data': True,
            'total_trades': total,
            'closed_trades': closed or 0,
            'open_trades': total - (closed or 0),
            'wins': wins or 0,
            'losses': (closed or 0) - (wins or 0),
            'win_rate': (wins / closed * 100) if closed else 0,
            'realized_pnl': realized or 0,
            'unrealized_pnl': unrealized or 0,
            'total_pnl': (realized or 0) + (unrealized or 0),
            'avg_trade_pnl': avg_pnl or 0,
            'best_trade': best or 0,
            'worst_trade': worst or 0
        }
    
    def calculate_sharpe_decay(self, backtest_sharpe: float, forward_trades: List[float]) -> float:
        """Calculate Sharpe ratio decay from backtest to forward"""
        if not forward_trades or backtest_sharpe == 0:
            return 0
        
        import numpy as np
        
        returns = np.array(forward_trades)
        if len(returns) < 5 or np.std(returns) == 0:
            return 0
        
        forward_sharpe = np.mean(returns) / np.std(returns) * np.sqrt(52)
        decay = ((forward_sharpe - backtest_sharpe) / backtest_sharpe) * 100
        
        return decay
    
    def generate_comparison(self) -> List[Dict]:
        """Generate backtest vs forward comparison for all Tier 1 strategies"""
        backtest = self.get_tier1_backtest_data()
        
        comparisons = []
        for name, bt_data in backtest.items():
            fw_data = self.get_forward_performance(name)
            
            comparison = {
                'strategy_name': name,
                'agent_id': bt_data['agent_id'],
                'best_pair': bt_data['pair'],
                'backtest': {
                    'sharpe': bt_data['sharpe'],
                    'win_rate': bt_data['win_rate'],
                    'max_dd': bt_data['max_dd'],
                    'trades': bt_data['trades'],
                    'total_return': bt_data['total_return']
                },
                'forward': fw_data if fw_data.get('has_data') else {
                    'has_data': False,
                    'status': 'WAITING_FOR_TRADES'
                }
            }
            
            # Calculate decay if we have forward data
            if fw_data.get('has_data'):
                bt_wr = bt_data['win_rate']
                fw_wr = fw_data['win_rate']
                comparison['win_rate_decay'] = fw_wr - bt_wr
                comparison['performance_verdict'] = self._get_verdict(bt_data, fw_data)
            else:
                comparison['win_rate_decay'] = None
                comparison['performance_verdict'] = 'NO_FORWARD_DATA'
            
            comparisons.append(comparison)
        
        # Sort by those with forward data first, then by forward P&L
        comparisons.sort(key=lambda x: (
            x['forward'].get('has_data', False),
            x['forward'].get('total_pnl', 0) if x['forward'].get('has_data') else 0
        ), reverse=True)
        
        return comparisons
    
    def _get_verdict(self, backtest: Dict, forward: Dict) -> str:
        """Generate performance verdict"""
        if not forward.get('has_data'):
            return 'NO_DATA'
        
        if forward['total_trades'] < 5:
            return 'INSUFFICIENT_DATA'
        
        fw_wr = forward['win_rate']
        bt_wr = backtest['win_rate']
        fw_pnl = forward['total_pnl']
        
        # Win rate within 10% of backtest
        wr_diff = fw_wr - bt_wr
        
        if fw_wr >= 50 and fw_pnl > 0:
            if wr_diff >= -5:
                return 'PERFORMING_AS_EXPECTED'
            else:
                return 'PERFORMING_BUT_DECAYED'
        elif fw_wr >= 40 and fw_pnl > -5:
            return 'MARGINAL'
        elif fw_pnl < -10:
            return 'UNDERPERFORMING'
        else:
            return 'EARLY_DAYS'
    
    def generate_dashboard(self) -> Dict:
        """Generate full dashboard data"""
        comparisons = self.generate_comparison()
        
        # Calculate overall stats
        with_forward = [c for c in comparisons if c['forward'].get('has_data')]
        making_money = [c for c in with_forward if (c['forward'].get('total_pnl') or 0) > 0]
        
        total_realized = sum(c['forward'].get('realized_pnl', 0) for c in with_forward)
        total_unrealized = sum(c['forward'].get('unrealized_pnl', 0) for c in with_forward)
        
        avg_wr_decay = sum(c.get('win_rate_decay', 0) for c in with_forward) / len(with_forward) if with_forward else 0
        
        dashboard = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'summary': {
                'tier1_strategies': len(comparisons),
                'with_forward_data': len(with_forward),
                'making_money': len(making_money),
                'losing_money': len(with_forward) - len(making_money),
                'total_realized_pnl': round(total_realized, 2),
                'total_unrealized_pnl': round(total_unrealized, 2),
                'avg_win_rate_decay': round(avg_wr_decay, 1)
            },
            'verdict_counts': {},
            'top_performers': [],
            'strategies': comparisons
        }
        
        # Count verdicts
        for c in comparisons:
            verdict = c.get('performance_verdict', 'UNKNOWN')
            dashboard['verdict_counts'][verdict] = dashboard['verdict_counts'].get(verdict, 0) + 1
        
        # Top performers
        sorted_by_pnl = sorted(
            [c for c in with_forward],
            key=lambda x: x['forward'].get('total_pnl', 0),
            reverse=True
        )[:5]
        
        dashboard['top_performers'] = [
            {
                'name': c['strategy_name'],
                'forward_pnl': round(c['forward'].get('total_pnl', 0), 2),
                'forward_wr': round(c['forward'].get('win_rate', 0), 1),
                'win_rate_decay': round(c.get('win_rate_decay', 0), 1),
                'verdict': c['performance_verdict']
            }
            for c in sorted_by_pnl
        ]
        
        # Save
        self.dashboard_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.dashboard_file, 'w') as f:
            json.dump(dashboard, f, indent=2)
        
        return dashboard
    
    def print_report(self):
        """Print human-readable report"""
        dashboard = self.generate_dashboard()
        
        print("="*80)
        print("FORWARD PERFORMANCE DASHBOARD")
        print(f"Generated: {dashboard['timestamp'][:19]} UTC")
        print("="*80)
        
        s = dashboard['summary']
        print(f"\n[SUMMARY]")
        print(f"  Tier 1 Strategies: {s['tier1_strategies']}")
        print(f"  With Forward Data: {s['with_forward_data']}")
        print(f"  Making Money: {s['making_money']} | Losing Money: {s['losing_money']}")
        print(f"  Total Realized P&L: {s['total_realized_pnl']:+.2f}%")
        print(f"  Total Unrealized P&L: {s['total_unrealized_pnl']:+.2f}%")
        print(f"  Avg Win Rate Decay: {s['avg_win_rate_decay']:+.1f}%")
        
        print(f"\n[TOP PERFORMERS]")
        for i, p in enumerate(dashboard['top_performers'], 1):
            status = "+" if p['forward_pnl'] > 0 else "-"
            print(f"  {status} {i}. {p['name'][:35]:<35} | "
                  f"P&L: {p['forward_pnl']:>+6.2f}% | "
                  f"WR: {p['forward_wr']:>5.1f}% | "
                  f"Decay: {p['win_rate_decay']:>+5.1f}%")
        
        print(f"\n[VERDICT BREAKDOWN]")
        for verdict, count in sorted(dashboard['verdict_counts'].items()):
            print(f"  {verdict}: {count}")
        
        print(f"\n[STRATEGY DETAILS]")
        print("-"*80)
        print(f"{'Strategy':<35} {'BT WR':>8} {'FW WR':>8} {'Decay':>8} {'P&L':>8} {'Verdict':<20}")
        print("-"*80)
        
        for c in dashboard['strategies'][:15]:
            name = c['strategy_name'][:34]
            bt_wr = c['backtest']['win_rate']
            
            if c['forward'].get('has_data'):
                fw = c['forward']
                fw_wr = fw['win_rate']
                decay = c.get('win_rate_decay', 0)
                pnl = fw['total_pnl']
                verdict = c['performance_verdict'][:18]
                print(f"{name:<35} {bt_wr:>7.1f}% {fw_wr:>7.1f}% {decay:>+7.1f}% {pnl:>+7.2f}% {verdict:<20}")
            else:
                print(f"{name:<35} {bt_wr:>7.1f}% {'--':>8} {'--':>8} {'--':>8} {'WAITING FOR DATA':<20}")
        
        print("\n" + "="*80)
        print("BACKTEST vs FORWARD: Are we making money?")
        print("="*80)
        print("\n+ = Strategy is profitable in forward testing")
        print("- = Strategy is losing money in forward testing")
        print("-- = Not enough forward trades yet")
        print("\nVerdict Legend:")
        print("  PERFORMING_AS_EXPECTED = Backtest results holding up")
        print("  PERFORMING_BUT_DECAYED = Profitable but lower win rate")
        print("  MARGINAL = Breaking even, needs more data")
        print("  UNDERPERFORMING = Significant losses vs backtest")
        print("  EARLY_DAYS = Not enough trades to evaluate")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Forward Performance Dashboard')
    parser.add_argument('--update', action='store_true', help='Update dashboard data')
    parser.add_argument('--report', action='store_true', help='Print report')
    
    args = parser.parse_args()
    
    dashboard = ForwardPerformanceDashboard()
    
    if args.update:
        data = dashboard.generate_dashboard()
        print(f"Dashboard updated: {dashboard.dashboard_file}")
        print(f"Summary: {data['summary']}")
    
    if args.report or not args.update:
        dashboard.print_report()
