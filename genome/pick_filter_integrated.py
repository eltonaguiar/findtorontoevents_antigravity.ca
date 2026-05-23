"""
Integrated Pick Filter - Combines all fixes

This module provides a unified interface for:
1. Conflict detection (LONG/SHORT on same symbol)
2. Duplicate removal
3. Calibrated scoring (V2)
4. ATR-scaled TP/SL (V2)
"""

import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Import our new modules
try:
    from conflict_detector import ConflictDetector, DuplicateDetector, filter_picks_with_conflict_detection
    from quality_engine_v2 import SignalQualityEngineV2
    from tp_sl_calculator_v2 import TPSLCalculatorV2, TPSLConfig
except ImportError:
    from .conflict_detector import ConflictDetector, DuplicateDetector, filter_picks_with_conflict_detection
    from .quality_engine_v2 import SignalQualityEngineV2
    from .tp_sl_calculator_v2 import TPSLCalculatorV2, TPSLConfig


class IntegratedPickFilter:
    """
    Unified pick filtering with all V2 improvements.
    
    Usage:
        filter = IntegratedPickFilter()
        result = filter.process_picks(raw_picks, live_performance_data)
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize with configuration."""
        self.config = config if config is not None else {}
        
        # Initialize components
        self.conflict_detector = ConflictDetector(config)
        self.duplicate_detector = DuplicateDetector()
        self.quality_engine = SignalQualityEngineV2(config)
        self.tpsl_calculator = TPSLCalculatorV2(
            TPSLConfig(
                atr_tp_mult=self.config.get('atr_tp_mult', 2.5),
                atr_sl_mult=self.config.get('atr_sl_mult', 1.5),
                min_rr_ratio=self.config.get('min_rr_ratio', 1.5),
                use_hma_filter=self.config.get('use_hma_filter', True),
                regime_adjust=self.config.get('regime_adjust', True)
            )
        )
        
        # Thresholds
        self.min_score = self.config.get('min_score', 70.0)
        self.min_confidence = self.config.get('min_confidence', 0.60)
        self.max_picks_per_symbol = self.config.get('max_picks_per_symbol', 2)
        self.max_total_picks = self.config.get('max_total_picks', 20)
    
    def process_picks(
        self,
        picks: List[Dict],
        live_performance: Optional[Dict[str, Dict]] = None,
        portfolio_state: Optional[Dict] = None
    ) -> Dict:
        """
        Process picks through complete filtering pipeline.
        
        Args:
            picks: Raw picks from various systems
            live_performance: Dict mapping strategy_id -> live performance metrics
            portfolio_state: Current portfolio for correlation checks
            
        Returns:
            Dict with filtered picks and processing report
        """
        report = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'original_count': len(picks),
            'stages': []
        }
        
        # Stage 1: Remove duplicates
        picks, dup_count = self.duplicate_detector.remove_duplicates(picks)
        report['stages'].append({
            'name': 'duplicate_removal',
            'removed': dup_count,
            'remaining': len(picks)
        })
        
        # Stage 2: Recalculate scores with V2 engine
        rescored_picks = []
        for pick in picks:
            strategy_id = pick.get('strategy_dna', pick.get('strategy', 'unknown'))
            live_perf = live_performance.get(strategy_id) if live_performance else None
            
            # Recalculate quality score
            quality = self.quality_engine.calculate_quality_score(pick, live_perf)
            pick['quality_score_v2'] = quality.total_score
            pick['grade_v2'] = quality.grade
            pick['verdict_v2'] = quality.verdict
            pick['score_components'] = quality.components
            pick['calibration_note'] = quality.calibration_note
            
            # Use V2 score if available
            pick['quality_score'] = quality.total_score
            pick['grade'] = quality.grade
            pick['verdict'] = quality.verdict
            
            rescored_picks.append(pick)
        
        # Filter by minimum score
        picks = [p for p in rescored_picks if p['quality_score'] >= self.min_score]
        report['stages'].append({
            'name': 'score_filtering',
            'min_score': self.min_score,
            'removed': len(rescored_picks) - len(picks),
            'remaining': len(picks)
        })
        
        # Stage 3: Recalculate TP/SL with V2 calculator
        recalculated_picks = []
        for pick in picks:
            # Get market data if available
            market_data = pick.get('market_structure', {})
            hma_slope = pick.get('hma_slope')  # May be None
            
            # Get strategy DNA
            strategy_dna = {
                'win_rate': pick.get('backtest_metrics', {}).get('win_rate', 0.55),
                'avg_win_pct': pick.get('expected_return_pct', 5.0),
                'avg_loss_pct': pick.get('max_risk_pct', 2.5),
                'risk_profile': pick.get('risk_profile', 'medium')
            }
            
            # Calculate new TP/SL
            levels = self.tpsl_calculator.calculate_levels(
                symbol=pick['symbol'],
                entry_price=pick['entry_price'],
                direction=pick['direction'],
                strategy_dna=strategy_dna,
                market_data=market_data,
                hma_slope=hma_slope
            )
            
            # Update pick with new levels
            pick['take_profit_v2'] = levels['take_profit']
            pick['stop_loss_v2'] = levels['stop_loss']
            pick['risk_reward_v2'] = levels['risk_reward']
            pick['atr_used'] = levels['atr_used']
            pick['atr_tp_mult'] = levels['atr_tp_mult']
            pick['atr_sl_mult'] = levels['atr_sl_mult']
            pick['regime'] = levels['regime']
            pick['position_size_pct'] = levels['position_size_pct']
            
            # Use V2 levels
            pick['take_profit'] = levels['take_profit']
            pick['stop_loss'] = levels['stop_loss']
            pick['risk_reward'] = levels['risk_reward']
            pick['confidence'] = levels['confidence']
            
            recalculated_picks.append(pick)
        
        picks = recalculated_picks
        report['stages'].append({
            'name': 'tpsl_recalculation',
            'recalculated': len(picks),
            'remaining': len(picks)
        })
        
        # Stage 4: Detect and resolve conflicts
        conflicts = self.conflict_detector.detect_conflicts(picks)
        picks = self.conflict_detector.resolve_conflicts(picks, conflicts)
        report['stages'].append({
            'name': 'conflict_resolution',
            'conflicts_detected': len(conflicts),
            'conflicts': [self.conflict_detector.to_dict(c) for c in conflicts],
            'remaining': len(picks)
        })
        
        # Stage 5: Diversify (limit per symbol)
        picks = self._diversify_picks(picks)
        report['stages'].append({
            'name': 'diversification',
            'max_per_symbol': self.max_picks_per_symbol,
            'remaining': len(picks)
        })
        
        # Stage 6: Final quality gates
        final_picks = []
        for pick in picks:
            if pick['confidence'] < self.min_confidence:
                continue
            if pick['risk_reward'] < 1.3:  # Hard minimum R:R
                continue
            final_picks.append(pick)
        
        report['stages'].append({
            'name': 'quality_gates',
            'min_confidence': self.min_confidence,
            'min_rr': 1.3,
            'removed': len(picks) - len(final_picks),
            'remaining': len(final_picks)
        })
        
        # Build summary
        report['final_count'] = len(final_picks)
        report['reduction_pct'] = (1 - len(final_picks) / report['original_count']) * 100 if report['original_count'] > 0 else 0
        
        # Calculate statistics
        if final_picks:
            scores = [p['quality_score'] for p in final_picks]
            rr_ratios = [p['risk_reward'] for p in final_picks]
            long_count = sum(1 for p in final_picks if p['direction'] == 'LONG')
            short_count = len(final_picks) - long_count
            
            report['statistics'] = {
                'avg_score': sum(scores) / len(scores),
                'min_score': min(scores),
                'max_score': max(scores),
                'avg_rr': sum(rr_ratios) / len(rr_ratios),
                'long_count': long_count,
                'short_count': short_count,
                'direction_balance': long_count / len(final_picks) if final_picks else 0.5
            }
        
        return {
            'report': report,
            'picks': final_picks
        }
    
    def _diversify_picks(self, picks: List[Dict]) -> List[Dict]:
        """Limit picks per symbol and total."""
        # Sort by quality score
        sorted_picks = sorted(picks, key=lambda x: x['quality_score'], reverse=True)
        
        selected = []
        symbol_counts = {}
        
        for pick in sorted_picks:
            symbol = pick['symbol']
            
            if symbol_counts.get(symbol, 0) >= self.max_picks_per_symbol:
                continue
            
            if len(selected) >= self.max_total_picks:
                break
            
            selected.append(pick)
            symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
        
        return selected


def generate_fix_report(original_picks: List[Dict], filtered_result: Dict) -> str:
    """Generate human-readable report of fixes applied."""
    report = filtered_result['report']
    
    lines = [
        "=" * 70,
        "INTEGRATED PICK FILTER - PROCESSING REPORT",
        "=" * 70,
        f"Timestamp: {report['timestamp']}",
        f"Original picks: {report['original_count']}",
        f"Final picks: {report['final_count']}",
        f"Reduction: {report['reduction_pct']:.1f}%",
        "",
        "STAGES:",
        "-" * 70
    ]
    
    for stage in report['stages']:
        lines.append(f"  {stage['name'].upper()}:")
        for key, val in stage.items():
            if key != 'name':
                if isinstance(val, list):
                    lines.append(f"    - {key}: {len(val)} items")
                else:
                    lines.append(f"    - {key}: {val}")
    
    if 'statistics' in report:
        stats = report['statistics']
        lines.extend([
            "",
            "FINAL STATISTICS:",
            "-" * 70,
            f"  Average Score: {stats['avg_score']:.1f}",
            f"  Score Range: {stats['min_score']:.0f} - {stats['max_score']:.0f}",
            f"  Average R:R: 1:{stats['avg_rr']:.2f}",
            f"  Direction: {stats['long_count']} LONG / {stats['short_count']} SHORT",
            f"  Balance: {stats['direction_balance']*100:.1f}% long-biased"
        ])
    
    # Conflict summary
    conflict_stage = next((s for s in report['stages'] if s['name'] == 'conflict_resolution'), {})
    if conflict_stage.get('conflicts'):
        lines.extend([
            "",
            "CONFLICTS DETECTED:",
            "-" * 70
        ])
        for conflict in conflict_stage['conflicts']:
            lines.append(f"  {conflict['symbol']}: {conflict['long_count']} LONG vs {conflict['short_count']} SHORT")
            lines.append(f"    Severity: {conflict['severity']}, Net: {conflict['net_exposure']}")
    
    lines.append("=" * 70)
    
    return "\n".join(lines)


if __name__ == '__main__':
    # Test with sample data
    test_picks = [
        {
            'id': 'pick_001',
            'symbol': 'BTCUSDT',
            'direction': 'LONG',
            'entry_price': 85000,
            'take_profit': 93500,
            'stop_loss': 80750,
            'quality_score': 85,
            'grade': 'B+',
            'system': 'alpha_engine',
            'strategy_dna': 'ema_cross_btc',
            'backtest_metrics': {'win_rate': 0.65, 'sharpe_ratio': 1.5, 'total_trades': 100},
            'consensus_count': 3,
            'market_structure': {'volatility_24h': 0.04, 'adx': 35}
        },
        {
            'id': 'pick_002',
            'symbol': 'BTCUSDT',
            'direction': 'SHORT',
            'entry_price': 84800,
            'take_profit': 78000,
            'stop_loss': 89000,
            'quality_score': 75,
            'grade': 'B',
            'system': 'battleground',
            'strategy_dna': 'momentum_btc',
            'backtest_metrics': {'win_rate': 0.58, 'sharpe_ratio': 1.2, 'total_trades': 80},
            'consensus_count': 2,
            'market_structure': {'volatility_24h': 0.04, 'adx': 35}
        },
        {
            'id': 'pick_003',  # Duplicate of 001
            'symbol': 'BTCUSDT',
            'direction': 'LONG',
            'entry_price': 85000,
            'take_profit': 93500,
            'stop_loss': 80750,
            'quality_score': 82,
            'grade': 'B+',
            'system': 'alpha_engine',
            'strategy_dna': 'ema_cross_btc',
            'backtest_metrics': {'win_rate': 0.65, 'sharpe_ratio': 1.5, 'total_trades': 100},
            'consensus_count': 3,
            'market_structure': {'volatility_24h': 0.04, 'adx': 35}
        },
        {
            'id': 'pick_004',
            'symbol': 'ETHUSDT',
            'direction': 'LONG',
            'entry_price': 3200,
            'take_profit': 3520,
            'stop_loss': 3040,
            'quality_score': 88,
            'grade': 'A-',
            'system': 'mercury2',
            'strategy_dna': 'breakout_eth',
            'backtest_metrics': {'win_rate': 0.68, 'sharpe_ratio': 1.8, 'total_trades': 120},
            'consensus_count': 4,
            'market_structure': {'volatility_24h': 0.05, 'adx': 32},
            'hma_slope': 1
        }
    ]
    
    # Live performance data (simulating poor performance for one strategy)
    live_perf = {
        'ema_cross_btc': {
            'recent_trades': 30,
            'recent_win_rate': 0.35,  # Poor live performance
            'recent_pnl_pct': -8.5
        },
        'momentum_btc': {
            'recent_trades': 25,
            'recent_win_rate': 0.62,  # Good performance
            'recent_pnl_pct': 12.0
        },
        'breakout_eth': {
            'recent_trades': 40,
            'recent_win_rate': 0.65,
            'recent_pnl_pct': 15.2
        }
    }
    
    # Run filter
    filter_engine = IntegratedPickFilter()
    result = filter_engine.process_picks(test_picks, live_perf)
    
    # Generate report
    print(generate_fix_report(test_picks, result))
    
    print("\nFINAL PICKS:")
    for pick in result['picks']:
        note = f" [{pick.get('calibration_note')}]" if pick.get('calibration_note') else ""
        print(f"  {pick['symbol']} {pick['direction']}: Score {pick['quality_score']:.0f} -> {pick['quality_score_v2']:.0f}{note}")
        print(f"    TP: ${pick['take_profit']:,.2f} | SL: ${pick['stop_loss']:,.2f} | R:R 1:{pick['risk_reward']:.2f}")
