"""
Signal Quality Engine - Hedge Fund Quality Signal Validation

Provides comprehensive scoring of trading signals across multiple dimensions
to ensure only high-quality signals are executed.
"""

import json
import math
from datetime import datetime
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


class SignalVerdict(Enum):
    """Trading verdicts based on quality score"""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    MODERATE_BUY = "MODERATE_BUY"
    HOLD = "HOLD"
    MODERATE_SELL = "MODERATE_SELL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"
    REJECT = "REJECT"


@dataclass
class QualityComponents:
    """Individual quality component scores"""
    backtest_validity: float
    statistical_significance: float
    regime_alignment: float
    risk_adjusted_return: float
    consensus_strength: float
    market_structure: float


@dataclass
class QualityScore:
    """Complete quality score result"""
    total_score: float
    components: Dict[str, float]
    grade: str
    verdict: str
    confidence: float
    timestamp: str


class SignalQualityEngine:
    """
    Hedge fund quality signal validation engine.
    
    Scores signals on 6 dimensions:
    - Backtest Validity (25%): Historical performance quality
    - Statistical Significance (20%): Sample size and reliability
    - Regime Alignment (15%): Current market fit
    - Risk-Adjusted Return (20%): Sharpe, Sortino, Calmar ratios
    - Consensus Strength (10%): Multi-system agreement
    - Market Structure (10%): Liquidity, spread, volume
    """
    
    # Component weights (must sum to 1.0)
    WEIGHTS = {
        'backtest_validity': 0.25,
        'statistical_significance': 0.20,
        'regime_alignment': 0.15,
        'risk_adjusted_return': 0.20,
        'consensus_strength': 0.10,
        'market_structure': 0.10
    }
    
    # Minimum thresholds for live trading
    MIN_SCORE_FOR_LIVE = 70.0
    MIN_SCORE_FOR_PAPER = 65.0
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the quality engine.
        
        Args:
            config: Optional configuration overrides
        """
        self.config = config or {}
        self.weights = self.config.get('weights', self.WEIGHTS)
        self.min_live_score = self.config.get('min_live_score', self.MIN_SCORE_FOR_LIVE)
        self.min_paper_score = self.config.get('min_paper_score', self.MIN_SCORE_FOR_PAPER)
    
    # Maximum points for each component (for normalization)
    COMPONENT_MAX = {
        'backtest_validity': 25.0,
        'statistical_significance': 20.0,
        'regime_alignment': 15.0,
        'risk_adjusted_return': 20.0,
        'consensus_strength': 10.0,
        'market_structure': 10.0
    }
    
    def calculate_quality_score(self, signal: Dict) -> QualityScore:
        """
        Calculate composite quality score (0-100).
        
        Args:
            signal: Trading signal dict with backtest data, metrics, etc.
            
        Returns:
            QualityScore with component scores and final verdict
        """
        # Calculate individual components (raw scores)
        raw_components = {
            'backtest_validity': self._score_backtest_metrics(signal),
            'statistical_significance': self._score_sample_size(signal),
            'regime_alignment': self._score_regime_fit(signal),
            'risk_adjusted_return': self._score_risk_adjusted(signal),
            'consensus_strength': self._score_consensus(signal),
            'market_structure': self._score_market_structure(signal)
        }
        
        # Normalize each component to 0-100 scale
        normalized_components = {
            k: (raw_components[k] / self.COMPONENT_MAX[k]) * 100
            for k in raw_components
        }
        
        # Calculate weighted total score (0-100)
        final_score = sum(normalized_components[k] * self.weights[k] for k in normalized_components)
        
        # Round to 2 decimal places
        final_score = round(final_score, 2)
        
        # Determine grade and verdict
        grade = self._score_to_grade(final_score)
        verdict = self._score_to_verdict(final_score, signal)
        confidence = self._calculate_confidence(normalized_components, final_score)
        
        return QualityScore(
            total_score=final_score,
            components=normalized_components,
            grade=grade,
            verdict=verdict,
            confidence=confidence,
            timestamp=datetime.utcnow().isoformat() + 'Z'
        )
    
    def _score_backtest_metrics(self, signal: Dict) -> float:
        """
        Score based on backtest performance (0-25 points).
        
        Scoring:
        - Sharpe > 2.0: 25 pts (exceptional)
        - Sharpe > 1.5: 22 pts (excellent)
        - Sharpe > 1.2: 18 pts (very good)
        - Sharpe > 1.0: 15 pts (good)
        - Sharpe > 0.8: 10 pts (acceptable)
        - Sharpe > 0.5: 5 pts (marginal)
        - Sharpe <= 0.5: 0 pts (poor)
        """
        metrics = signal.get('backtest_metrics', {})
        sharpe = metrics.get('sharpe_ratio', metrics.get('sharpe', 0))
        
        if sharpe > 2.0:
            return 25.0
        elif sharpe > 1.5:
            return 22.0
        elif sharpe > 1.2:
            return 18.0
        elif sharpe > 1.0:
            return 15.0
        elif sharpe > 0.8:
            return 10.0
        elif sharpe > 0.5:
            return 5.0
        else:
            return 0.0
    
    def _score_sample_size(self, signal: Dict) -> float:
        """
        Score based on statistical significance (0-20 points).
        
        Scoring:
        - > 500 trades: 20 pts (highly significant)
        - > 200 trades: 18 pts (very significant)
        - > 100 trades: 15 pts (significant)
        - > 50 trades: 12 pts (moderate)
        - > 30 trades: 10 pts (acceptable)
        - > 20 trades: 7 pts (marginal)
        - <= 20 trades: trades * 0.3 (proportional)
        """
        metrics = signal.get('backtest_metrics', {})
        trades = metrics.get('total_trades', 0)
        
        if trades > 500:
            return 20.0
        elif trades > 200:
            return 18.0
        elif trades > 100:
            return 15.0
        elif trades > 50:
            return 12.0
        elif trades > 30:
            return 10.0
        elif trades > 20:
            return 7.0
        else:
            return max(0, trades * 0.3)
    
    def _score_regime_fit(self, signal: Dict) -> float:
        """
        Score based on current market regime alignment (0-15 points).
        
        Checks if current market regime matches the strategy's best regime.
        """
        current_regime = signal.get('current_regime', 'unknown')
        best_regimes = signal.get('optimal_regimes', [])
        regime_performance = signal.get('regime_performance', {})
        
        if not best_regimes or current_regime == 'unknown':
            return 7.5  # Neutral score if unknown
        
        if current_regime in best_regimes:
            # Strategy is in its optimal regime
            perf = regime_performance.get(current_regime, {})
            sharpe = perf.get('sharpe', 1.5)
            if sharpe > 2.0:
                return 15.0
            elif sharpe > 1.5:
                return 13.0
            else:
                return 11.0
        else:
            # Check how well strategy performs in current regime
            perf = regime_performance.get(current_regime, {})
            sharpe = perf.get('sharpe', 0)
            if sharpe > 1.0:
                return 9.0
            elif sharpe > 0.5:
                return 6.0
            else:
                return 3.0
    
    def _score_risk_adjusted(self, signal: Dict) -> float:
        """
        Score based on risk-adjusted returns (0-20 points).
        
        Uses multiple metrics: Sortino ratio, Calmar ratio, max drawdown.
        """
        metrics = signal.get('backtest_metrics', {})
        
        # Sortino ratio (downside risk adjusted)
        sortino = metrics.get('sortino_ratio', 0)
        
        # Calmar ratio (return / max drawdown)
        calmar = metrics.get('calmar_ratio', 0)
        
        # Max drawdown (lower is better)
        max_dd = abs(metrics.get('max_drawdown', 0.5))
        
        score = 0.0
        
        # Sortino scoring
        if sortino > 2.0:
            score += 8.0
        elif sortino > 1.5:
            score += 7.0
        elif sortino > 1.0:
            score += 5.0
        elif sortino > 0.5:
            score += 3.0
        else:
            score += 1.0
        
        # Calmar scoring
        if calmar > 3.0:
            score += 7.0
        elif calmar > 2.0:
            score += 6.0
        elif calmar > 1.0:
            score += 4.0
        elif calmar > 0.5:
            score += 2.0
        else:
            score += 1.0
        
        # Max drawdown scoring (inverse)
        if max_dd < 0.05:
            score += 5.0
        elif max_dd < 0.10:
            score += 4.0
        elif max_dd < 0.15:
            score += 3.0
        elif max_dd < 0.25:
            score += 2.0
        elif max_dd < 0.35:
            score += 1.0
        else:
            score += 0.0
        
        return min(score, 20.0)
    
    def _score_consensus(self, signal: Dict) -> float:
        """
        Score based on multi-system consensus (0-10 points).
        
        Checks how many independent systems agree on the signal.
        """
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
        """
        Score based on market structure quality (0-10 points).
        
        Evaluates liquidity, spread, volume, and order book depth.
        """
        market_data = signal.get('market_structure', {})
        
        # Liquidity score
        daily_volume = market_data.get('daily_volume_usd', 0)
        if daily_volume > 1_000_000_000:  # $1B+
            liquidity_score = 4.0
        elif daily_volume > 100_000_000:  # $100M+
            liquidity_score = 3.5
        elif daily_volume > 10_000_000:  # $10M+
            liquidity_score = 2.5
        elif daily_volume > 1_000_000:  # $1M+
            liquidity_score = 1.5
        else:
            liquidity_score = 0.5
        
        # Spread score (lower is better)
        spread_pct = market_data.get('spread_pct', 0.01)
        if spread_pct < 0.001:  # < 0.1%
            spread_score = 3.0
        elif spread_pct < 0.005:  # < 0.5%
            spread_score = 2.5
        elif spread_pct < 0.01:  # < 1%
            spread_score = 2.0
        elif spread_pct < 0.02:  # < 2%
            spread_score = 1.0
        else:
            spread_score = 0.0
        
        # Volatility regime score
        volatility = market_data.get('volatility_24h', 0.5)
        if 0.02 <= volatility <= 0.08:  # Moderate volatility
            vol_score = 3.0
        elif 0.01 <= volatility < 0.02 or 0.08 < volatility <= 0.15:
            vol_score = 2.0
        elif volatility > 0.15:  # High volatility
            vol_score = 1.0
        else:  # Very low volatility
            vol_score = 1.5
        
        return min(liquidity_score + spread_score + vol_score, 10.0)
    
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
            verdict = SignalVerdict.STRONG_BUY if direction == 'LONG' else SignalVerdict.STRONG_SELL
        elif score >= 80:
            verdict = SignalVerdict.BUY if direction == 'LONG' else SignalVerdict.SELL
        elif score >= 70:
            verdict = SignalVerdict.MODERATE_BUY if direction == 'LONG' else SignalVerdict.MODERATE_SELL
        elif score >= 50:
            verdict = SignalVerdict.HOLD
        else:
            verdict = SignalVerdict.REJECT
        
        return verdict.value
    
    def _calculate_confidence(self, components: Dict[str, float], total_score: float) -> float:
        """Calculate confidence level based on component consistency."""
        values = list(components.values())
        if not values:
            return 0.5
        
        # Calculate coefficient of variation (CV)
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = math.sqrt(variance)
        
        # Lower CV = higher confidence
        cv = std_dev / mean if mean > 0 else 1.0
        
        # Base confidence on total score, adjusted by consistency
        base_confidence = total_score / 100.0
        consistency_factor = max(0.7, 1.0 - cv)
        
        return round(base_confidence * consistency_factor, 2)
    
    def is_tradeable(self, quality_score: QualityScore) -> bool:
        """Check if signal meets minimum threshold for live trading."""
        return quality_score.total_score >= self.min_live_score
    
    def is_paper_tradeable(self, quality_score: QualityScore) -> bool:
        """Check if signal meets threshold for paper trading."""
        return quality_score.total_score >= self.min_paper_score
    
    def to_dict(self, quality_score: QualityScore) -> Dict:
        """Convert QualityScore to dictionary."""
        return {
            'total_score': quality_score.total_score,
            'components': quality_score.components,
            'grade': quality_score.grade,
            'verdict': quality_score.verdict,
            'confidence': quality_score.confidence,
            'timestamp': quality_score.timestamp,
            'tradeable': self.is_tradeable(quality_score),
            'paper_tradeable': self.is_paper_tradeable(quality_score)
        }


# Example usage and testing
if __name__ == '__main__':
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Signal Quality Engine CLI")
    parser.add_argument("--score-all", action="store_true",
                        help="Score all active strategies from backtest results")
    parser.add_argument("--results-dir", type=str, default="results",
                        help="Directory with backtest results (default: results)")
    args = parser.parse_args()

    engine = SignalQualityEngine()

    if args.score_all:
        # Load backtest results and score them
        backtest_path = os.path.join(args.results_dir, "backtest_results.json")
        if os.path.exists(backtest_path):
            with open(backtest_path, 'r') as f:
                bt_data = json.load(f)
            results = bt_data.get('results', [])
            print(f"[INFO] Scoring {len(results)} backtest results...")

            scored = []
            for r in results:
                signal = {
                    'symbol': r.get('symbol', 'UNKNOWN'),
                    'direction': 'LONG',
                    'backtest_metrics': {
                        'sharpe_ratio': r.get('sharpe_ratio', 0),
                        'sortino_ratio': r.get('sortino_ratio', 0),
                        'calmar_ratio': r.get('calmar_ratio', 0),
                        'max_drawdown': r.get('max_drawdown', 0),
                        'total_trades': r.get('total_trades', 0),
                        'win_rate': r.get('win_rate', 0),
                        'profit_factor': r.get('profit_factor', 0),
                    },
                    'strategy_id': r.get('strategy_id', 'unknown'),
                    'dna_hash': r.get('dna_hash', 'unknown'),
                }
                quality = engine.calculate_quality_score(signal)
                scored.append({
                    'strategy_id': signal['strategy_id'],
                    'dna_hash': signal['dna_hash'],
                    'symbol': signal['symbol'],
                    'quality': engine.to_dict(quality),
                    'backtest_metrics': signal['backtest_metrics'],
                })

            # Save scored results
            os.makedirs(args.results_dir, exist_ok=True)
            scored_path = os.path.join(args.results_dir, "quality_scores.json")
            with open(scored_path, 'w') as f:
                json.dump({
                    'scored_at': datetime.utcnow().isoformat(),
                    'total_scored': len(scored),
                    'scores': scored
                }, f, indent=2)
            print(f"[OK] Saved {len(scored)} quality scores to {scored_path}")

            # Summary
            tradeable = [s for s in scored if s['quality']['tradeable']]
            print(f"[INFO] Tradeable signals (score >= {engine.min_live_score}): {len(tradeable)}")
        else:
            print(f"[WARN] No backtest results found at {backtest_path}")
            print("[INFO] Running demo scoring instead...")
            # Fall through to demo
            args.score_all = False

    if not args.score_all:
        # Demo mode
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
            'optimal_regimes': ['trending_bull', 'volatile_bull'],
            'regime_performance': {
                'trending_bull': {'sharpe': 2.1, 'win_rate': 0.72},
                'volatile_bull': {'sharpe': 1.5, 'win_rate': 0.65}
            },
            'agreeing_systems': ['alpha_engine', 'mercury2', 'dna_genome', 'kimi'],
            'market_structure': {
                'daily_volume_usd': 35_000_000_000,
                'spread_pct': 0.0005,
                'volatility_24h': 0.045
            }
        }

        result = engine.calculate_quality_score(test_signal)
        result_dict = engine.to_dict(result)

        print("=" * 60)
        print("SIGNAL QUALITY SCORE RESULT")
        print("=" * 60)
        print(f"Total Score: {result_dict['total_score']}/100")
        print(f"Grade: {result_dict['grade']}")
        print(f"Verdict: {result_dict['verdict']}")
        print(f"Confidence: {result_dict['confidence']}")
        print(f"Tradeable: {result_dict['tradeable']}")
        print("\nComponent Scores:")
        for component, score in result_dict['components'].items():
            weight = engine.WEIGHTS[component] * 100
            print(f"  {component}: {score:.1f} (weight: {weight:.0f}%)")
        print("=" * 60)
