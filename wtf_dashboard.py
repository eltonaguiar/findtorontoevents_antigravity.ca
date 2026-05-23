"""
WTF Dashboard - "Why The Failure" Signal Debugging
==================================================
Shows why trades were rejected, signal divergence, and pipeline issues.

Key Views:
- Rejection reasons breakdown
- Signal diff (raw vs final)
- Pipeline bottleneck detection
- Data quality issues

Based on feedback: "Make it observable for humans"

Usage:
    from wtf_dashboard import WTFDashboard
    
    wtf = WTFDashboard()
    
    # Log a rejection
    wtf.log_rejection('hurst_regime', 'high_volatility regime blocked', signal_data)
    
    # Generate daily report
    report = wtf.generate_daily_report()
    print(report['top_rejection_reasons'])
"""

import json
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('WTFDashboard')


@dataclass
class RejectionEvent:
    """A signal rejection event"""
    timestamp: datetime
    strategy_id: str
    reason: str
    reason_category: str  # regime, cost, rr, consensus, etc.
    signal_data: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp.isoformat(),
            'strategy_id': self.strategy_id,
            'reason': self.reason,
            'category': self.reason_category,
            'signal': self.signal_data
        }


@dataclass
class SignalDiff:
    """Difference between raw signal and final pick"""
    timestamp: datetime
    strategy_id: str
    symbol: str
    
    # Raw signal
    raw_direction: str
    raw_entry: float
    raw_stop: float
    raw_target: float
    raw_rr: float
    
    # Final (after processing)
    final_direction: Optional[str]
    final_entry: Optional[float]
    final_stop: Optional[float]
    final_target: Optional[float]
    final_rr: Optional[float]
    
    # What changed
    changes: List[str] = field(default_factory=list)
    rejection_reason: Optional[str] = None


class WTFDashboard:
    """
    Why-The-Failure debugging dashboard
    
    Tracks every step of signal processing to identify
    where and why good signals get lost.
    """
    
    def __init__(self, retention_days: int = 30):
        self.retention_days = retention_days
        self.rejections: List[RejectionEvent] = []
        self.signal_diffs: List[SignalDiff] = []
        self.pipeline_stats = {
            'signals_received': 0,
            'after_regime_gate': 0,
            'after_cost_gate': 0,
            'after_rr_gate': 0,
            'after_consensus_gate': 0,
            'final_approved': 0
        }
        
        # Load existing
        self._load_data()
    
    def _load_data(self):
        """Load historical WTF data"""
        try:
            with open('wtf_dashboard_data.json', 'r') as f:
                data = json.load(f)
                # Load recent rejections only
                cutoff = (datetime.now() - timedelta(days=self.retention_days)).isoformat()
                for r in data.get('rejections', []):
                    if r['timestamp'] > cutoff:
                        self.rejections.append(RejectionEvent(
                            timestamp=datetime.fromisoformat(r['timestamp']),
                            strategy_id=r['strategy_id'],
                            reason=r['reason'],
                            reason_category=r['category'],
                            signal_data=r['signal']
                        ))
        except FileNotFoundError:
            pass
    
    def _save_data(self):
        """Save WTF data"""
        data = {
            'rejections': [r.to_dict() for r in self.rejections[-1000:]],  # Keep last 1000
            'last_update': datetime.now().isoformat()
        }
        with open('wtf_dashboard_data.json', 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def log_rejection(
        self,
        strategy_id: str,
        reason: str,
        signal_data: Dict[str, Any],
        category: str = "other"
    ):
        """Log a signal rejection"""
        event = RejectionEvent(
            timestamp=datetime.now(),
            strategy_id=strategy_id,
            reason=reason,
            reason_category=category,
            signal_data=signal_data
        )
        self.rejections.append(event)
        
        # Save periodically
        if len(self.rejections) % 10 == 0:
            self._save_data()
        
        logger.info(f"[WTF] Rejected {strategy_id}: {reason}")
    
    def log_signal_diff(
        self,
        strategy_id: str,
        symbol: str,
        raw_signal: Dict,
        final_signal: Optional[Dict],
        changes: List[str],
        rejection_reason: Optional[str] = None
    ):
        """Log difference between raw and final signal"""
        diff = SignalDiff(
            timestamp=datetime.now(),
            strategy_id=strategy_id,
            symbol=symbol,
            raw_direction=raw_signal.get('direction', 'unknown'),
            raw_entry=raw_signal.get('entry', 0),
            raw_stop=raw_signal.get('stop', 0),
            raw_target=raw_signal.get('target', 0),
            raw_rr=raw_signal.get('rr', 0),
            final_direction=final_signal.get('direction') if final_signal else None,
            final_entry=final_signal.get('entry') if final_signal else None,
            final_stop=final_signal.get('stop') if final_signal else None,
            final_target=final_signal.get('target') if final_signal else None,
            final_rr=final_signal.get('rr') if final_signal else None,
            changes=changes,
            rejection_reason=rejection_reason
        )
        self.signal_diffs.append(diff)
    
    def update_pipeline_stats(self, stage: str, count: int):
        """Update pipeline stage counts"""
        self.pipeline_stats[stage] = count
    
    def get_rejection_breakdown(self, days: int = 7) -> Dict[str, Any]:
        """Get rejection reasons breakdown"""
        cutoff = datetime.now() - timedelta(days=days)
        recent = [r for r in self.rejections if r.timestamp > cutoff]
        
        if not recent:
            return {'message': 'No rejections in period'}
        
        # By category
        by_category = Counter(r.reason_category for r in recent)
        
        # By strategy
        by_strategy = Counter(r.strategy_id for r in recent)
        
        # By specific reason
        by_reason = Counter(r.reason for r in recent)
        
        return {
            'period_days': days,
            'total_rejections': len(recent),
            'by_category': dict(by_category.most_common(10)),
            'by_strategy': dict(by_strategy.most_common(10)),
            'top_reasons': [
                {'reason': reason, 'count': count}
                for reason, count in by_reason.most_common(10)
            ]
        }
    
    def get_signal_divergence(self, days: int = 1) -> Dict[str, Any]:
        """Get signal divergence report"""
        cutoff = datetime.now() - timedelta(days=days)
        recent = [s for s in self.signal_diffs if s.timestamp > cutoff]
        
        if not recent:
            return {'message': 'No signal diffs in period'}
        
        # Find biggest divergences
        divergences = []
        for diff in recent:
            if diff.rejection_reason:
                divergences.append({
                    'strategy': diff.strategy_id,
                    'symbol': diff.symbol,
                    'raw_rr': diff.raw_rr,
                    'final_rr': diff.final_rr,
                    'changes': diff.changes,
                    'reason': diff.rejection_reason
                })
        
        return {
            'period_days': days,
            'total_processed': len(recent),
            'rejected_count': len(divergences),
            'approval_rate': (len(recent) - len(divergences)) / len(recent) if recent else 0,
            'divergences': divergences[:20]  # Top 20
        }
    
    def get_pipeline_health(self) -> Dict[str, Any]:
        """Get pipeline health metrics"""
        stats = self.pipeline_stats
        
        # Calculate drop-off at each stage
        drops = {}
        prev = stats['signals_received']
        for stage, count in [
            ('regime_gate', stats['after_regime_gate']),
            ('cost_gate', stats['after_cost_gate']),
            ('rr_gate', stats['after_rr_gate']),
            ('consensus_gate', stats['after_consensus_gate']),
            ('final', stats['final_approved'])
        ]:
            if prev > 0:
                drops[stage] = {
                    'remaining': count,
                    'dropped': prev - count,
                    'drop_rate': round((prev - count) / prev, 3)
                }
            prev = count
        
        # Identify bottlenecks
        bottlenecks = []
        for stage, data in drops.items():
            if data['drop_rate'] > 0.5:
                bottlenecks.append({
                    'stage': stage,
                    'drop_rate': data['drop_rate'],
                    'severity': 'critical' if data['drop_rate'] > 0.8 else 'high'
                })
        
        return {
            'pipeline_stats': stats,
            'stage_drops': drops,
            'bottlenecks': bottlenecks,
            'funnel_efficiency': stats['final_approved'] / max(stats['signals_received'], 1)
        }
    
    def identify_data_quality_issues(self) -> List[Dict[str, Any]]:
        """Identify potential data quality issues"""
        issues = []
        
        cutoff = datetime.now() - timedelta(days=1)
        recent = [r for r in self.rejections if r.timestamp > cutoff]
        
        # Check for suspicious patterns
        
        # 1. All signals from one strategy rejected
        by_strategy = defaultdict(int)
        for r in recent:
            by_strategy[r.strategy_id] += 1
        
        for strat, count in by_strategy.items():
            if count > 10:
                issues.append({
                    'type': 'strategy_blocked',
                    'strategy': strat,
                    'count': count,
                    'severity': 'high',
                    'suggestion': f'Check if {strat} is on kill list or has config issues'
                })
        
        # 2. High slippage in rejections
        high_slippage = [
            r for r in recent
            if 'slippage' in r.reason.lower() or 'cost' in r.reason.lower()
        ]
        if len(high_slippage) > 5:
            issues.append({
                'type': 'execution_costs',
                'count': len(high_slippage),
                'severity': 'medium',
                'suggestion': 'Review transaction cost model calibration'
            })
        
        # 3. Regime mismatches
        regime_blocks = [r for r in recent if r.reason_category == 'regime']
        if len(regime_blocks) > 10:
            issues.append({
                'type': 'regime_mismatch',
                'count': len(regime_blocks),
                'severity': 'info',
                'suggestion': 'Consider adjusting regime thresholds if too strict'
            })
        
        return issues
    
    def generate_daily_report(self) -> Dict[str, Any]:
        """Generate comprehensive daily WTF report"""
        return {
            'report_date': datetime.now().isoformat(),
            'rejection_breakdown': self.get_rejection_breakdown(days=1),
            'signal_divergence': self.get_signal_divergence(days=1),
            'pipeline_health': self.get_pipeline_health(),
            'data_quality_issues': self.identify_data_quality_issues(),
            'recommendations': self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate action recommendations based on WTF data"""
        recs = []
        
        # Check rejection patterns
        breakdown = self.get_rejection_breakdown(days=7)
        if breakdown.get('total_rejections', 0) > 50:
            top_cat = list(breakdown.get('by_category', {}).keys())[0] if breakdown.get('by_category') else None
            if top_cat:
                recs.append(f"High rejection rate: Review {top_cat} gate settings")
        
        # Check pipeline
        health = self.get_pipeline_health()
        if health.get('funnel_efficiency', 1) < 0.1:
            recs.append("Pipeline efficiency < 10%: Consider relaxing some gates")
        
        # Check data quality
        issues = self.identify_data_quality_issues()
        for issue in issues:
            if issue['severity'] == 'high':
                recs.append(f"[URGENT] {issue['suggestion']}")
        
        if not recs:
            recs.append("No major issues detected - system healthy")
        
        return recs
    
    def print_console_report(self, report: Dict[str, Any]):
        """Print formatted report to console"""
        print("\n" + "=" * 80)
        print("WTF DASHBOARD - Daily Signal Debugging Report")
        print(f"Generated: {report['report_date'][:19]}")
        print("=" * 80)
        
        # Pipeline health
        print("\n[PIPELINE HEALTH]")
        print("-" * 80)
        health = report['pipeline_health']
        print(f"Signals Received: {health['pipeline_stats']['signals_received']}")
        print(f"Final Approved: {health['pipeline_stats']['final_approved']}")
        print(f"Funnel Efficiency: {health['funnel_efficiency']:.1%}")
        
        if health['bottlenecks']:
            print("\n[BOTTLENECKS DETECTED]")
            for b in health['bottlenecks']:
                print(f"  {b['stage']}: {b['drop_rate']:.1%} drop ({b['severity']})")
        
        # Rejection breakdown
        print("\n[REJECTION BREAKDOWN - Last 24h]")
        print("-" * 80)
        rej = report['rejection_breakdown']
        if 'message' in rej:
            print(rej['message'])
        else:
            print(f"Total Rejections: {rej['total_rejections']}")
            print("\nBy Category:")
            for cat, count in rej['by_category'].items():
                print(f"  {cat}: {count}")
            print("\nTop Reasons:")
            for item in rej['top_reasons'][:5]:
                print(f"  {item['count']}x: {item['reason'][:60]}")
        
        # Data quality
        print("\n[DATA QUALITY ISSUES]")
        print("-" * 80)
        issues = report['data_quality_issues']
        if issues:
            for issue in issues:
                print(f"[{issue['severity'].upper()}] {issue['type']}: {issue['suggestion']}")
        else:
            print("No data quality issues detected")
        
        # Recommendations
        print("\n[RECOMMENDATIONS]")
        print("-" * 80)
        for rec in report['recommendations']:
            print(f"  • {rec}")
        
        print("\n" + "=" * 80)


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("WTF DASHBOARD - Demo")
    print("=" * 80)
    
    wtf = WTFDashboard()
    
    # Simulate some rejections
    for i in range(20):
        wtf.log_rejection(
            'hurst_regime_adaptive',
            'Regime high_volatility not in preferred list',
            {'symbol': 'BTC', 'rr': 1.8},
            'regime'
        )
    
    for i in range(15):
        wtf.log_rejection(
            'baby_battleground',
            'Cost block: Edge (0.53%) consumed by costs (0.65%)',
            {'symbol': 'ETH', 'rr': 1.4},
            'cost'
        )
    
    for i in range(5):
        wtf.log_rejection(
            'smart_money_fvg',
            'Strategy on kill list',
            {'symbol': 'SOL', 'rr': 2.0},
            'kill_list'
        )
    
    # Update pipeline stats
    wtf.update_pipeline_stats('signals_received', 100)
    wtf.update_pipeline_stats('after_regime_gate', 60)
    wtf.update_pipeline_stats('after_cost_gate', 40)
    wtf.update_pipeline_stats('after_rr_gate', 35)
    wtf.update_pipeline_stats('after_consensus_gate', 30)
    wtf.update_pipeline_stats('final_approved', 25)
    
    # Generate and print report
    report = wtf.generate_daily_report()
    wtf.print_console_report(report)
