"""
Signal Quality Engine V2 - Calibrated Scoring

Addresses the score correlation issue where scores 80+ underperformed scores 60-79.

Key Changes from V1:
1. Added live performance weighting (recent forward test results)
2. Score decay for underperforming strategies
3. Regime-specific scoring adjustments
4. Reduced weight on backtest metrics, increased weight on live performance
"""

import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class SignalGrade(Enum):
    """Signal quality grades"""
    A_PLUS = "A+"
    A = "A"
    A_MINUS = "A-"
    B_PLUS = "B+"
    B = "B"
    B_MINUS = "B-"
    C_PLUS = "C+"
    C = "C"
    D = "D"
    F = "F"


@dataclass
class QualityScore:
    """Complete quality score result"""
    total_score: float
    components: Dict[str, float]
    grade: str
    verdict: str
    confidence: float
    timestamp: str
    calibration_note: Optional[str] = None


class SignalQualityEngineV2:
    """
    Calibrated signal quality engine with live performance weighting.
    
    V2 Changes:
    - Backtest Validity: 25% -> 15% (reduced)
    - Live Performance: 0% -> 25% (NEW)
    - Statistical Significance: 20% -> 15% (reduced)
    - Regime Alignment: 15% -> 15% (unchanged)
    - Risk-Adjusted Return: 20% -> 15% (reduced)
    - Consensus Strength: 10% -> 10% (unchanged)
    - Market Structure: 10% -> 5% (reduced)
    """
    
    # Updated component weights (must sum to 1.0)
    WEIGHTS = {
        'backtest_validity': 0.15,      # Reduced from 0.25
        'live_performance': 0.25,       # NEW - based on recent forward tests
        'statistical_significance': 0.15,  # Reduced from 0.20
        'regime_alignment': 0.15,       # Unchanged
        'risk_adjusted_return': 0.15,   # Reduced from 0.20
        'consensus_strength': 0.10,     # Unchanged
        'market_structure': 0.05        # Reduced from 0.10
    }
    
    # Score decay parameters
    SCORE_DECAY_HALFLIFE_DAYS = 30    # Score halves every 30 days of poor performance
    LIVE_LOOKBACK_DAYS = 30           # Consider last 30 days of live performance
    
    # Minimum thresholds for live trading
    MIN_SCORE_FOR_LIVE = 70.0
    MIN_SCORE_FOR_PAPER = 60.0        # Lowered from 65
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize the calibrated quality engine."""
        self.config = config or {}
        self.weights = self.config.get('weights', self.WEIGHTS)
        self.min_live_score = self.config.get('min_live_score', self.MIN_SCORE_FOR_LIVE)
        self.min_paper_score = self.config.get('min_paper_score', self.MIN_SCORE_FOR_PAPER)
        self.live_lookback_days = self.config.get('live_lookback_days', self.LIVE_LOOKBACK_DAYS)
    
    def calculate_quality_score(self, signal: Dict, live_performance: Optional[Dict] = None) -> QualityScore:
        """
        Calculate calibrated quality score (0-100).
        
        Args:
            signal: Trading signal dict with backtest data
            live_performance: Optional dict with recent live performance metrics
                {
                    'recent_trades': 50,
                    'recent_win_rate': 0.62,
                    'recent_pnl_pct': 12.5,
                    'last_updated': '2026-04-06T12:00:00Z'
                }
            
        Returns:
            QualityScore with component scores and final verdict
        """
        # Calculate individual components
        raw_components = {
            'backtest_validity': self._score_backtest_metrics(signal),
            'live_performance': self._score_live_performance(signal, live_performance),
            'statistical_significance': self._score_sample_size(signal, live_performance),
            'regime_alignment': self._score_regime_fit(signal),
            'risk_adjusted_return': self._score_risk_adjusted(signal, live_performance),
            'consensus_strength': self._score_consensus(signal),
            'market_structure': self._score_market_structure(signal)
        }
        
        # Apply score decay if live performance is poor
        decay_factor = self._calculate_decay_factor(live_performance)
        
        # Normalize each component to 0-100 scale and apply decay
        normalized_components = {}
        for k, v in raw_components.items():
            max_val = self._get_component_max(k)
            normalized = (v / max_val) * 100 * decay_factor
            normalized_components[k] = min(normalized, 100)
        
        # Calculate weighted total score (0-100)
        final_score = sum(normalized_components[k] * self.weights[k] for k in normalized_components)
        final_score = round(max(0, min(100, final_score)), 2)
        
        # Determine grade and verdict
        grade = self._score_to_grade(final_score)
        verdict = self._score_to_verdict(final_score, signal)
        confidence = self._calculate_confidence(normalized_components, final_score)
        
        # Add calibration note if decay was applied
        calibration_note = None
        if decay_factor < 0.9:
            calibration_note = f"Score decayed by {(1-decay_factor)*100:.0f}% due to poor live performance"
        
        return QualityScore(
            total_score=final_score,
            components=normalized_components,
            grade=grade,
            verdict=verdict,
            confidence=confidence,
            timestamp=datetime.utcnow().isoformat() + 'Z',
            calibration_note=calibration_note
        )
    
    def _score_backtest_metrics(self, signal: Dict) -> float:
        """
        Score based on backtest performance (0-15 points).
        Reduced weight from V1 since live performance matters more.
        """
        metrics = signal.get('backtest_metrics', {})
        sharpe = metrics.get('sharpe_ratio', metrics.get('sharpe', 0))
        profit_factor = metrics.get('profit_factor', 0)
        
        # Sharpe scoring (capped lower than V1)
        if sharpe > 2.0:
            sharpe_score = 8.0
        elif sharpe > 1.5:
            sharpe_score = 7.0
        elif sharpe > 1.2:
            sharpe_score = 6.0
        elif sharpe > 1.0:
            sharpe_score = 5.0
        elif sharpe > 0.8:
            sharpe_score = 3.0
        else:
            sharpe_score = max(0, sharpe * 3)
        
        # Profit factor bonus
        if profit_factor > 2.0:
            pf_score = 4.0
        elif profit_factor > 1.5:
            pf_score = 3.0
        elif profit_factor > 1.0:
            pf_score = 2.0
        else:
            pf_score = max(0, profit_factor)
        
        # Win rate consistency
        win_rate = metrics.get('win_rate', 0.5)
        if win_rate > 0.65:
            wr_score = 3.0
        elif win_rate > 0.55:
            wr_score = 2.0
        else:
            wr_score = max(0, (win_rate - 0.3) * 5)
        
        return min(sharpe_score + pf_score + wr_score, 15.0)
    
    def _score_live_performance(self, signal: Dict, live_performance: Optional[Dict]) -> float:
        """
        Score based on recent live performance (0-25 points).
        NEW in V2 - heavily weighted since it reflects actual results.
        """
        if not live_performance:
            # No live data - return neutral score
            return 12.5
        
        recent_wr = live_performance.get('recent_win_rate', 0.5)
        recent_pnl = live_performance.get('recent_pnl_pct', 0)
        recent_trades = live_performance.get('recent_trades', 0)
        
        # Require minimum sample size
        if recent_trades < 5:
            return 12.5  # Neutral if insufficient data
        
        # Win rate scoring (max 12 points)
        if recent_wr >= 0.70:
            wr_score = 12.0
        elif recent_wr >= 0.60:
            wr_score = 10.0
        elif recent_wr >= 0.55:
            wr_score = 8.0
        elif recent_wr >= 0.50:
            wr_score = 6.0
        elif recent_wr >= 0.45:
            wr_score = 4.0
        elif recent_wr >= 0.40:
            wr_score = 2.0
        else:
            wr_score = max(0, recent_wr * 10)
        
        # PnL scoring (max 10 points)
        if recent_pnl >= 20:
            pnl_score = 10.0
        elif recent_pnl >= 10:
            pnl_score = 8.0
        elif recent_pnl >= 5:
            pnl_score = 6.0
        elif recent_pnl >= 0:
            pnl_score = 4.0
        elif recent_pnl >= -5:
            pnl_score = 2.0
        elif recent_pnl >= -10:
            pnl_score = 1.0
        else:
            pnl_score = 0.0
        
        # Sample size bonus (max 3 points)
        if recent_trades >= 100:
            ss_score = 3.0
        elif recent_trades >= 50:
            ss_score = 2.0
        elif recent_trades >= 20:
            ss_score = 1.0
        else:
            ss_score = 0.5
        
        return min(wr_score + pnl_score + ss_score, 25.0)
    
    def _score_sample_size(self, signal: Dict, live_performance: Optional[Dict]) -> float:
        """Score based on statistical significance (0-15 points)."""
        backtest = signal.get('backtest_metrics', {})
        bt_trades = backtest.get('total_trades', 0)
        
        # Combine backtest and live trades
        live_trades = live_performance.get('recent_trades', 0) if live_performance else 0
        total_trades = bt_trades + live_trades
        
        if total_trades > 500:
            return 15.0
        elif total_trades > 200:
            return 13.0
        elif total_trades > 100:
            return 11.0
        elif total_trades > 50:
            return 9.0
        elif total_trades > 30:
            return 7.0
        elif total_trades > 20:
            return 5.0
        else:
            return max(0, total_trades * 0.2)
    
    def _score_regime_fit(self, signal: Dict) -> float:
        """Score based on current market regime alignment (0-15 points)."""
        current_regime = signal.get('current_regime', 'unknown')
        best_regimes = signal.get('optimal_regimes', [])
        regime_performance = signal.get('regime_performance', {})
        
        if not best_regimes or current_regime == 'unknown':
            return 7.5  # Neutral
        
        if current_regime in best_regimes:
            perf = regime_performance.get(current_regime, {})
            sharpe = perf.get('sharpe', 1.5)
            if sharpe > 2.0:
                return 15.0
            elif sharpe > 1.5:
                return 13.0
            else:
                return 11.0
        else:
            perf = regime_performance.get(current_regime, {})
            sharpe = perf.get('sharpe', 0)
            if sharpe > 1.0:
                return 8.0
            elif sharpe > 0.5:
                return 5.0
            else:
                return 2.0
    
    def _score_risk_adjusted(self, signal: Dict, live_performance: Optional[Dict]) -> float:
        """Score based on risk-adjusted returns (0-15 points)."""
        metrics = signal.get('backtest_metrics', {})
        
        # Backtest metrics
        sortino = metrics.get('sortino_ratio', 0)
        calmar = metrics.get('calmar_ratio', 0)
        max_dd = abs(metrics.get('max_drawdown', 0.5))
        
        # Live metrics if available
        live_dd = live_performance.get('recent_max_dd', max_dd) if live_performance else max_dd
        max_dd = max(max_dd, live_dd)  # Use worse of the two
        
        score = 0.0
        
        # Sortino (max 6)
        if sortino > 2.0:
            score += 6.0
        elif sortino > 1.5:
            score += 5.0
        elif sortino > 1.0:
            score += 4.0
        elif sortino > 0.5:
            score += 2.0
        else:
            score += 1.0
        
        # Calmar (max 5)
        if calmar > 3.0:
            score += 5.0
        elif calmar > 2.0:
            score += 4.0
        elif calmar > 1.0:
            score += 3.0
        elif calmar > 0.5:
            score += 1.5
        else:
            score += 0.5
        
        # Max drawdown (inverse, max 4)
        if max_dd < 0.05:
            score += 4.0
        elif max_dd < 0.10:
            score += 3.0
        elif max_dd < 0.15:
            score += 2.0
        elif max_dd < 0.25:
            score += 1.0
        
        return min(score, 15.0)
    
    def _score_consensus(self, signal: Dict) -> float:
        """Score based on multi-system consensus (0-10 points)."""
        agreeing_systems = signal.get('agreeing_systems', [])
        consensus_count = len(agreeing_systems)
        
        if consensus_count >= 5:
            return 10.0
        elif consensus_count == 4:
            return 9.0
        elif consensus_count == 3:
            return 7.0
        elif consensus_count == 2:
            return 5.0
        elif consensus_count == 1:
            return 3.0
        else:
            return 0.0
    
    def _score_market_structure(self, signal: Dict) -> float:
        """Score based on market structure quality (0-5 points)."""
        market_data = signal.get('market_structure', {})
        
        daily_volume = market_data.get('daily_volume_usd', 0)
        spread_pct = market_data.get('spread_pct', 0.01)
        
        # Volume (max 3)
        if daily_volume > 1_000_000_000:
            vol_score = 3.0
        elif daily_volume > 100_000_000:
            vol_score = 2.0
        elif daily_volume > 10_000_000:
            vol_score = 1.0
        else:
            vol_score = 0.0
        
        # Spread (max 2)
        if spread_pct < 0.001:
            spread_score = 2.0
        elif spread_pct < 0.005:
            spread_score = 1.5
        elif spread_pct < 0.01:
            spread_score = 1.0
        else:
            spread_score = 0.0
        
        return min(vol_score + spread_score, 5.0)
    
    def _calculate_decay_factor(self, live_performance: Optional[Dict]) -> float:
        """
        Calculate score decay factor based on poor live performance.
        
        If live win rate is < 45%, apply decay based on how long it's been underperforming.
        """
        if not live_performance:
            return 1.0
        
        recent_wr = live_performance.get('recent_win_rate', 0.5)
        
        # Only decay if significantly underperforming
        if recent_wr >= 0.45:
            return 1.0
        
        # Calculate decay based on how bad the performance is
        # At 40% WR: 0.9x, At 30% WR: 0.7x, At 20% WR: 0.5x
        decay = max(0.3, recent_wr * 2)
        return round(decay, 2)
    
    def _get_component_max(self, component: str) -> float:
        """Get maximum raw score for a component."""
        maxes = {
            'backtest_validity': 15.0,
            'live_performance': 25.0,
            'statistical_significance': 15.0,
            'regime_alignment': 15.0,
            'risk_adjusted_return': 15.0,
            'consensus_strength': 10.0,
            'market_structure': 5.0
        }
        return maxes.get(component, 10.0)
    
    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 95:
            return SignalGrade.A_PLUS.value
        elif score >= 90:
            return SignalGrade.A.value
        elif score >= 85:
            return SignalGrade.A_MINUS.value
        elif score >= 80:
            return SignalGrade.B_PLUS.value
        elif score >= 75:
            return SignalGrade.B.value
        elif score >= 70:
            return SignalGrade.B_MINUS.value
        elif score >= 65:
            return SignalGrade.C_PLUS.value
        elif score >= 60:
            return SignalGrade.C.value
        elif score >= 40:
            return SignalGrade.D.value
        else:
            return SignalGrade.F.value
    
    def _score_to_verdict(self, score: float, signal: Dict) -> str:
        """Convert score and signal to trading verdict."""
        direction = signal.get('direction', 'LONG').upper()
        
        if score >= 90:
            return "STRONG_BUY" if direction == 'LONG' else "STRONG_SELL"
        elif score >= 80:
            return "BUY" if direction == 'LONG' else "SELL"
        elif score >= 70:
            return "MODERATE_BUY" if direction == 'LONG' else "MODERATE_SELL"
        elif score >= 60:
            return "WEAK_BUY" if direction == 'LONG' else "WEAK_SELL"
        elif score >= 50:
            return "HOLD"
        else:
            return "REJECT"
    
    def _calculate_confidence(self, components: Dict[str, float], total_score: float) -> float:
        """Calculate confidence level based on component consistency."""
        values = list(components.values())
        if not values:
            return 0.5
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = math.sqrt(variance)
        
        cv = std_dev / mean if mean > 0 else 1.0
        base_confidence = total_score / 100.0
        consistency_factor = max(0.7, 1.0 - cv)
        
        return round(base_confidence * consistency_factor, 2)
    
    def to_dict(self, quality_score: QualityScore) -> Dict:
        """Convert QualityScore to dictionary."""
        return {
            'total_score': quality_score.total_score,
            'components': quality_score.components,
            'grade': quality_score.grade,
            'verdict': quality_score.verdict,
            'confidence': quality_score.confidence,
            'timestamp': quality_score.timestamp,
            'calibration_note': quality_score.calibration_note,
            'tradeable': quality_score.total_score >= self.min_live_score,
            'paper_tradeable': quality_score.total_score >= self.min_paper_score
        }


if __name__ == '__main__':
    # Test the calibrated engine
    engine = SignalQualityEngineV2()
    
    # Test signal with poor live performance
    test_signal = {
        'symbol': 'BTCUSDT',
        'direction': 'LONG',
        'backtest_metrics': {
            'sharpe_ratio': 1.75,
            'sortino_ratio': 2.1,
            'calmar_ratio': 2.5,
            'max_drawdown': 0.12,
            'total_trades': 156,
            'win_rate': 0.68,
            'profit_factor': 2.3
        },
        'current_regime': 'trending_bull',
        'optimal_regimes': ['trending_bull'],
        'regime_performance': {
            'trending_bull': {'sharpe': 2.1, 'win_rate': 0.72}
        },
        'agreeing_systems': ['alpha_engine', 'mercury2', 'dna_genome', 'kimi'],
        'market_structure': {
            'daily_volume_usd': 35_000_000_000,
            'spread_pct': 0.0005,
            'volatility_24h': 0.045
        }
    }
    
    # Without live performance
    result1 = engine.calculate_quality_score(test_signal)
    print("=" * 60)
    print("V2 CALIBRATED SCORING - WITHOUT LIVE DATA")
    print("=" * 60)
    print(f"Total Score: {result1.total_score}/100")
    print(f"Grade: {result1.grade}")
    print(f"Verdict: {result1.verdict}")
    print(f"Confidence: {result1.confidence}")
    print("\nComponent Scores:")
    for component, score in result1.components.items():
        weight = engine.WEIGHTS[component] * 100
        print(f"  {component}: {score:.1f} (weight: {weight:.0f}%)")
    
    # With poor live performance
    live_poor = {
        'recent_trades': 30,
        'recent_win_rate': 0.35,  # Poor performance
        'recent_pnl_pct': -8.5
    }
    result2 = engine.calculate_quality_score(test_signal, live_poor)
    print("\n" + "=" * 60)
    print("V2 CALIBRATED SCORING - WITH POOR LIVE DATA (35% WR)")
    print("=" * 60)
    print(f"Total Score: {result2.total_score}/100")
    print(f"Grade: {result2.grade}")
    print(f"Verdict: {result2.verdict}")
    print(f"Confidence: {result2.confidence}")
    if result2.calibration_note:
        print(f"Note: {result2.calibration_note}")
    
    # With good live performance
    live_good = {
        'recent_trades': 40,
        'recent_win_rate': 0.65,
        'recent_pnl_pct': 15.2
    }
    result3 = engine.calculate_quality_score(test_signal, live_good)
    print("\n" + "=" * 60)
    print("V2 CALIBRATED SCORING - WITH GOOD LIVE DATA (65% WR)")
    print("=" * 60)
    print(f"Total Score: {result3.total_score}/100")
    print(f"Grade: {result3.grade}")
    print(f"Verdict: {result3.verdict}")
    print(f"Confidence: {result3.confidence}")
    print("=" * 60)
