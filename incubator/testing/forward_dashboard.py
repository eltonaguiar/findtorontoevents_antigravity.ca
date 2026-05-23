"""
Forward Testing Dashboard Generator

Creates comprehensive reports and dashboards for forward testing results.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
import sqlite3


class ForwardTestDashboard:
    """Generate comprehensive forward testing dashboards"""
    
    def __init__(self, db_path: str = "incubator/forward_test.db",
                 output_dir: str = "battleground/data/forward_test"):
        self.db_path = db_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_full_report(self) -> Path:
        """Generate comprehensive forward test report"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all strategies
        cursor.execute('''
            SELECT strategy_name, agent_id, status, created_at,
                   backtest_sharpe, backtest_win_rate, backtest_expectancy,
                   forward_sharpe, forward_win_rate, forward_expectancy,
                   forward_pnl_pct, forward_trades_count, forward_days,
                   graduated_at, graduation_score
            FROM strategies
            ORDER BY forward_sharpe DESC NULLS LAST
        ''')
        
        strategies = []
        for row in cursor.fetchall():
            strategies.append({
                'strategy_name': row[0],
                'agent_id': row[1],
                'status': row[2],
                'created_at': row[3],
                'backtest': {
                    'sharpe': row[4],
                    'win_rate': row[5],
                    'expectancy': row[6]
                },
                'forward': {
                    'sharpe': row[7],
                    'win_rate': row[8],
                    'expectancy': row[9],
                    'pnl_pct': row[10],
                    'trades': row[11],
                    'days': row[12]
                },
                'graduated_at': row[13],
                'graduation_score': row[14],
                'sharpe_decay': self._calc_decay(row[4], row[7]),
                'expectancy_decay': self._calc_decay(row[6], row[9])
            })
            
        # Calculate summary stats
        graduated = [s for s in strategies if s['status'] == 'graduated']
        paper = [s for s in strategies if s['status'] == 'paper_trading']
        failed = [s for s in strategies if s['status'] == 'failed']
        
        summary = {
            'total_strategies': len(strategies),
            'graduated': len(graduated),
            'paper_trading': len(paper),
            'failed': len(failed),
            'graduation_rate': len(graduated) / len(strategies) * 100 if strategies else 0,
            'avg_forward_sharpe': sum(s['forward']['sharpe'] or 0 for s in strategies) / len(strategies) if strategies else 0,
            'avg_backtest_sharpe': sum(s['backtest']['sharpe'] or 0 for s in strategies) / len(strategies) if strategies else 0,
            'backtest_forward_correlation': self._calc_correlation(strategies)
        }
        
        report = {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'summary': summary,
            'tier_s_core': [s for s in graduated if s['graduation_score'] and s['graduation_score'] >= 80],
            'tier_a_viable': [s for s in graduated if s['graduation_score'] and 60 <= s['graduation_score'] < 80],
            'tier_b_conditional': [s for s in paper if s['forward']['sharpe'] and s['forward']['sharpe'] >= 0.8],
            'under_review': [s for s in paper if s['forward']['sharpe'] is None or s['forward']['sharpe'] < 0.8],
            'eliminated': failed[:20],  # Top 20 failed
            'all_strategies': strategies
        }
        
        # Save report
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        report_path = self.output_dir / f"forward_test_report_{timestamp}.json"
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
            
        # Generate Markdown summary
        md_path = self._generate_markdown_summary(report)
        
        conn.close()
        
        print(f"[ForwardDashboard] Report saved: {report_path}")
        print(f"[ForwardDashboard] Summary saved: {md_path}")
        
        return report_path
        
    def _calc_decay(self, backtest: Optional[float], forward: Optional[float]) -> Optional[float]:
        """Calculate performance decay from backtest to forward"""
        if backtest is None or forward is None or backtest == 0:
            return None
        return round((forward - backtest) / abs(backtest) * 100, 2)
        
    def _calc_correlation(self, strategies: List[Dict]) -> float:
        """Calculate correlation between backtest and forward performance"""
        import numpy as np
        
        bt_sharpes = [s['backtest']['sharpe'] for s in strategies if s['backtest']['sharpe'] is not None and s['forward']['sharpe'] is not None]
        fw_sharpes = [s['forward']['sharpe'] for s in strategies if s['backtest']['sharpe'] is not None and s['forward']['sharpe'] is not None]
        
        if len(bt_sharpes) < 2:
            return 0.0
            
        return round(np.corrcoef(bt_sharpes, fw_sharpes)[0, 1], 4)
        
    def _generate_markdown_summary(self, report: Dict) -> Path:
        """Generate human-readable markdown summary"""
        summary = report['summary']
        
        md = f"""# Forward Testing Report
## Live Market Validation Summary

**Generated:** {report['generated_at'][:19]} UTC  
**Analysis Period:** Forward testing in progress

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total Strategies | {summary['total_strategies']} |
| Graduated to Live | {summary['graduated']} ({summary['graduation_rate']:.1f}%) |
| In Paper Trading | {summary['paper_trading']} |
| Failed/Eliminated | {summary['failed']} |
| Backtest/Forward Correlation | {summary['backtest_forward_correlation']:.2f} |

---

## Tier S - Core Live Strategies ({len(report['tier_s_core'])})

These strategies have graduated with scores ≥80 and are approved for live trading.

| Strategy | Agent | Forward Sharpe | Win Rate | P&L % | Trades | Days |
|----------|-------|----------------|----------|-------|--------|------|
"""
        
        for s in report['tier_s_core'][:10]:
            md += f"| {s['strategy_name'][:30]} | {s['agent_id']} | {s['forward']['sharpe']:.2f} | {s['forward']['win_rate']:.1%} | {s['forward']['pnl_pct']:.2f}% | {s['forward']['trades']} | {s['forward']['days']} |\n"
            
        md += f"""
---

## Tier A - Viable Strategies ({len(report['tier_a_viable'])})

These strategies have graduated with scores 60-79 and are approved with reduced allocation.

| Strategy | Agent | Forward Sharpe | Win Rate | P&L % | Trades | Days |
|----------|-------|----------------|----------|-------|--------|------|
"""
        
        for s in report['tier_a_viable'][:10]:
            md += f"| {s['strategy_name'][:30]} | {s['agent_id']} | {s['forward']['sharpe']:.2f} | {s['forward']['win_rate']:.1%} | {s['forward']['pnl_pct']:.2f}% | {s['forward']['trades']} | {s['forward']['days']} |\n"
            
        md += f"""
---

## Tier B - Conditional Paper ({len(report['tier_b_conditional'])})

These strategies show promise (Sharpe ≥0.8) but need more forward data.

| Strategy | Agent | Forward Sharpe | Win Rate | P&L % | Trades | Days |
|----------|-------|----------------|----------|-------|--------|------|
"""
        
        for s in report['tier_b_conditional'][:10]:
            md += f"| {s['strategy_name'][:30]} | {s['agent_id']} | {s['forward']['sharpe']:.2f} | {s['forward']['win_rate']:.1%} | {s['forward']['pnl_pct']:.2f}% | {s['forward']['trades']} | {s['forward']['days']} |\n"
            
        md += f"""
---

## Key Findings

1. **Backtest/Forward Correlation:** {summary['backtest_forward_correlation']:.2f}
   - {'⚠️ Low correlation indicates overfitting risk' if summary['backtest_forward_correlation'] < 0.5 else '✅ Good correlation between backtest and forward'}
   
2. **Graduation Rate:** {summary['graduation_rate']:.1f}%
   - {'⚠️ Low graduation rate - strategies need refinement' if summary['graduation_rate'] < 30 else '✅ Healthy graduation rate'}
   
3. **Performance Decay:**
   - Average backtest Sharpe: {summary['avg_backtest_sharpe']:.2f}
   - Average forward Sharpe: {summary['avg_forward_sharpe']:.2f}
   - Decay: {((summary['avg_forward_sharpe'] - summary['avg_backtest_sharpe']) / summary['avg_backtest_sharpe'] * 100) if summary['avg_backtest_sharpe'] != 0 else 0:.1f}%

---

## Recommendations

1. **Deploy:** {len(report['tier_s_core'])} strategies from Tier S at full allocation
2. **Deploy:** {len(report['tier_a_viable'])} strategies from Tier A at 50% allocation
3. **Continue Testing:** {len(report['tier_b_conditional'])} strategies from Tier B
4. **Review:** {len(report['under_review'])} strategies showing poor forward performance

---

*Report generated by ForwardTestDashboard*
"""
        
        md_path = self.output_dir / f"forward_test_summary_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.md"
        with open(md_path, 'w') as f:
            f.write(md)
            
        return md_path
        
    def generate_graduation_candidates_report(self) -> List[Dict[str, Any]]:
        """Generate list of strategies ready for graduation review"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT strategy_name, agent_id, forward_sharpe, forward_win_rate,
                   forward_max_dd, forward_pnl_pct, forward_trades_count, forward_days
            FROM strategies
            WHERE status = 'paper_trading'
              AND forward_days >= 20
              AND forward_sharpe IS NOT NULL
            ORDER BY forward_sharpe DESC
        ''')
        
        candidates = []
        for row in cursor.fetchall():
            candidates.append({
                'strategy_name': row[0],
                'agent_id': row[1],
                'sharpe': row[2],
                'win_rate': row[3],
                'max_dd': row[4],
                'pnl_pct': row[5],
                'trades': row[6],
                'days': row[7],
                'recommendation': self._graduation_recommendation(row[2], row[3], row[4], row[5], row[6], row[7])
            })
            
        conn.close()
        
        # Save candidates list
        candidates_path = self.output_dir / f"graduation_candidates_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        with open(candidates_path, 'w') as f:
            json.dump({
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'candidate_count': len(candidates),
                'candidates': candidates
            }, f, indent=2)
            
        print(f"[ForwardDashboard] Candidates report: {candidates_path}")
        
        return candidates
        
    def _graduation_recommendation(self, sharpe, win_rate, max_dd, pnl, trades, days) -> str:
        """Generate graduation recommendation based on metrics"""
        score = 0
        
        if sharpe and sharpe >= 1.0: score += 3
        elif sharpe and sharpe >= 0.8: score += 2
        elif sharpe and sharpe >= 0.5: score += 1
        
        if win_rate and win_rate >= 0.50: score += 2
        elif win_rate and win_rate >= 0.45: score += 1
        
        if max_dd and max_dd <= 0.15: score += 2
        elif max_dd and max_dd <= 0.25: score += 1
        
        if pnl and pnl > 0: score += 1
        if trades and trades >= 20: score += 1
        if days and days >= 30: score += 1
        
        if score >= 8: return "STRONG_GRADUATE"
        elif score >= 6: return "GRADUATE"
        elif score >= 4: return "CONTINUE_TESTING"
        else: return "REVIEW"


# Convenience functions
def generate_forward_report() -> Path:
    """Generate full forward testing report"""
    dashboard = ForwardTestDashboard()
    return dashboard.generate_full_report()


def get_graduation_candidates() -> List[Dict[str, Any]]:
    """Get list of strategies ready for graduation review"""
    dashboard = ForwardTestDashboard()
    return dashboard.generate_graduation_candidates_report()
