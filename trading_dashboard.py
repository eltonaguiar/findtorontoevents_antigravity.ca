#!/usr/bin/env python3
"""
SPIKE TRADING DASHBOARD - Real-time Performance Monitor
Tracks and displays live trading results
"""

import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List
import os

class TradingDashboard:
    """Generates trading performance dashboard"""
    
    def __init__(self, results_file: str = "spike_trading_results.json"):
        self.results_file = results_file
        self.data = self.load_results()
    
    def load_results(self) -> Dict:
        """Load trading results"""
        if os.path.exists(self.results_file):
            with open(self.results_file, 'r') as f:
                return json.load(f)
        return {'signal_history': [], 'active_signals': []}
    
    def generate_dashboard(self) -> str:
        """Generate markdown dashboard"""
        history = self.data.get('signal_history', [])
        active = self.data.get('active_signals', [])
        
        # Calculate metrics
        closed_trades = [s for s in history if s.get('status') == 'CLOSED']
        
        dashboard = []
        dashboard.append("# 🔴 LIVE SPIKE TRADING DASHBOARD")
        dashboard.append(f"\n**Last Updated:** {datetime.utcnow().isoformat()} UTC")
        dashboard.append(f"\n## 📊 Performance Summary")
        
        if closed_trades:
            pnls = [s.get('pnl', 0) for s in closed_trades]
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p <= 0]
            
            total_pnl = sum(pnls)
            win_rate = len(wins) / len(pnls) if pnls else 0
            
            dashboard.append(f"\n| Metric | Value |")
            dashboard.append(f"|--------|-------|")
            dashboard.append(f"| Total Trades | {len(closed_trades)} |")
            dashboard.append(f"| Win Rate | {win_rate:.1%} |")
            dashboard.append(f"| Total P&L | {total_pnl:.2%} |")
            dashboard.append(f"| Avg Win | {sum(wins)/len(wins):.2%} |" if wins else "| Avg Win | N/A |")
            dashboard.append(f"| Avg Loss | {sum(losses)/len(losses):.2%} |" if losses else "| Avg Loss | N/A |")
            
            # Profit factor
            if losses and sum(losses) != 0:
                pf = abs(sum(wins) / sum(losses))
                dashboard.append(f"| Profit Factor | {pf:.2f} |")
            
            # Sharpe (simplified)
            if len(pnls) > 1:
                import numpy as np
                sharpe = np.mean(pnls) / np.std(pnls) * np.sqrt(252) if np.std(pnls) > 0 else 0
                dashboard.append(f"| Sharpe Ratio | {sharpe:.2f} |")
        else:
            dashboard.append("\n*No completed trades yet*")
        
        # Active signals
        dashboard.append(f"\n## 🎯 Active Signals ({len(active)})")
        if active:
            dashboard.append("\n| Asset | Direction | Confidence | Entry | Current | Age |")
            dashboard.append("|-------|-----------|------------|-------|---------|-----|")
            for s in active:
                age = (datetime.utcnow() - datetime.fromisoformat(s['entry_time'])).total_seconds() / 60
                dashboard.append(f"| {s['asset']} | {s['direction']} | {s['confidence']:.0f}% | ${s['entry_price']:,.2f} | ${s.get('current_price', s['entry_price']):,.2f} | {age:.0f}m |")
        else:
            dashboard.append("\n*No active signals*")
        
        # Recent closed trades
        dashboard.append(f"\n## 📈 Recent Closed Trades")
        recent = sorted(closed_trades, key=lambda x: x.get('exit_time', ''), reverse=True)[:10]
        if recent:
            dashboard.append("\n| Asset | Direction | Exit Reason | P&L |")
            dashboard.append("|-------|-----------|-------------|-----|")
            for t in recent:
                emoji = "🟢" if t.get('pnl', 0) > 0 else "🔴"
                dashboard.append(f"| {t['asset']} | {t['direction']} | {t.get('exit_reason', 'N/A')} | {emoji} {t.get('pnl', 0):.2%} |")
        
        # Asset breakdown
        if closed_trades:
            dashboard.append(f"\n## 📊 Performance by Asset")
            assets = {}
            for t in closed_trades:
                asset = t['asset']
                if asset not in assets:
                    assets[asset] = {'trades': 0, 'wins': 0, 'pnl': 0}
                assets[asset]['trades'] += 1
                assets[asset]['wins'] += 1 if t.get('pnl', 0) > 0 else 0
                assets[asset]['pnl'] += t.get('pnl', 0)
            
            dashboard.append("\n| Asset | Trades | Win Rate | Total P&L |")
            dashboard.append("|-------|--------|----------|-----------|")
            for asset, stats in sorted(assets.items(), key=lambda x: x[1]['pnl'], reverse=True):
                wr = stats['wins'] / stats['trades'] if stats['trades'] > 0 else 0
                dashboard.append(f"| {asset} | {stats['trades']} | {wr:.1%} | {stats['pnl']:.2%} |")
        
        # Signal rationale breakdown
        if closed_trades:
            dashboard.append(f"\n## 🧠 Signal Rationale Analysis")
            rationales = {}
            for t in closed_trades:
                # Simplify rationale to main factor
                main_factor = t.get('rationale', 'UNKNOWN').split('|')[0].strip()
                if main_factor not in rationales:
                    rationales[main_factor] = {'trades': 0, 'wins': 0, 'pnl': 0}
                rationales[main_factor]['trades'] += 1
                rationales[main_factor]['wins'] += 1 if t.get('pnl', 0) > 0 else 0
                rationales[main_factor]['pnl'] += t.get('pnl', 0)
            
            dashboard.append("\n| Factor | Trades | Win Rate | Avg P&L |")
            dashboard.append("|--------|--------|----------|---------|")
            for factor, stats in sorted(rationales.items(), key=lambda x: x[1]['pnl'], reverse=True):
                wr = stats['wins'] / stats['trades'] if stats['trades'] > 0 else 0
                avg = stats['pnl'] / stats['trades'] if stats['trades'] > 0 else 0
                dashboard.append(f"| {factor} | {stats['trades']} | {wr:.1%} | {avg:.2%} |")
        
        # Goals and progress
        dashboard.append(f"\n## 🎯 Statistical Validation Progress")
        total_signals = len(closed_trades)
        dashboard.append(f"\n- **Current Sample Size:** {total_signals} signals")
        dashboard.append(f"- **Target for Validation:** 1,000 signals")
        dashboard.append(f"- **Progress:** {total_signals/10:.1f}%")
        
        if total_signals > 0:
            dashboard.append(f"\n### Confidence Intervals (Bootstrap)")
            import numpy as np
            pnls = [s.get('pnl', 0) for s in closed_trades]
            
            # Simple bootstrap
            if len(pnls) >= 30:
                bootstraps = []
                for _ in range(1000):
                    sample = np.random.choice(pnls, size=len(pnls), replace=True)
                    bootstraps.append(np.mean(sample))
                
                ci_lower = np.percentile(bootstraps, 2.5)
                ci_upper = np.percentile(bootstraps, 97.5)
                
                dashboard.append(f"\n- **Mean Return:** {np.mean(pnls):.2%}")
                dashboard.append(f"- **95% CI:** [{ci_lower:.2%}, {ci_upper:.2%}]")
                
                if ci_lower > 0:
                    dashboard.append(f"\n✅ **STATISTICALLY SIGNIFICANT EDGE DETECTED**")
                elif ci_upper < 0:
                    dashboard.append(f"\n❌ **NO EDGE - STRATEGY FAILS**")
                else:
                    dashboard.append(f"\n⏳ **INCONCLUSIVE - NEED MORE DATA**")
        
        dashboard.append(f"\n---")
        dashboard.append(f"\n*This dashboard updates automatically every 15 minutes*")
        dashboard.append(f"\n*All signals are true forward tests - no backtesting*")
        
        return "\n".join(dashboard)
    
    def save_dashboard(self, filename: str = "SPIKE_TRADING_DASHBOARD.md"):
        """Save dashboard to file"""
        dashboard = self.generate_dashboard()
        with open(filename, 'w') as f:
            f.write(dashboard)
        print(f"Dashboard saved to {filename}")

def main():
    """Generate dashboard"""
    dashboard = TradingDashboard()
    dashboard.save_dashboard()
    print(dashboard.generate_dashboard())

if __name__ == "__main__":
    main()
