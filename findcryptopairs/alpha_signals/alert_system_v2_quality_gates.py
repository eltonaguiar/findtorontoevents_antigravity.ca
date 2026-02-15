#!/usr/bin/env python3
"""
Alpha Signal Alert System V2 - Quality Gates Edition
"Are We Sure?" - Only alerts when we have sufficient evidence

INTEGRATION: Replace or extend your existing alert_system.py
QUALITY PRINCIPLE: Suppress "early guesses", only alert when "SURE"
"""

import json
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import os


class ConfidenceTier(Enum):
    """Signal maturity and confidence classification"""
    EARLY_GUESS = "early_guess"      # <30 trades - SUPPRESSED
    EMERGING = "emerging"             # 30-50 trades - MONITOR ONLY
    VALIDATED = "validated"           # 50-100 trades, 55%+ WR - LOW CONFIDENCE
    PROVEN = "proven"                 # 100-250 trades, 60%+ WR - MEDIUM CONFIDENCE
    CERTAIN = "certain"               # 250+ trades, 65%+ WR - HIGH CONFIDENCE
    INSTITUTIONAL = "institutional"   # 500+ trades, 70%+ WR, academic backing - MAX CONFIDENCE


class SignalStatus(Enum):
    """Where the signal is in validation pipeline"""
    RSVE_WEEK_1 = "rsve_week_1"       # Accumulating - DO NOT ALERT
    RSVE_WEEK_2 = "rsve_week_2"       # Paper trading - DO NOT ALERT  
    RSVE_WEEK_3 = "rsve_week_3"       # Live test $100-500 - CAUTION
    PROMOTED = "promoted"             # Validated for live trading - OK TO ALERT
    DEMOTED = "demoted"               # Failed validation - SUPPRESS


@dataclass
class SignalQualityMetrics:
    """Track signal quality over time"""
    strategy_id: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    first_trade_date: Optional[datetime] = None
    last_trade_date: Optional[datetime] = None
    consecutive_losses: int = 0
    consecutive_wins: int = 0
    
    @property
    def confidence_tier(self) -> ConfidenceTier:
        """Calculate confidence tier based on trade history"""
        if self.total_trades < 30:
            return ConfidenceTier.EARLY_GUESS
        elif self.total_trades < 50:
            return ConfidenceTier.EMERGING
        elif self.total_trades < 100:
            return ConfidenceTier.VALIDATED if self.win_rate >= 0.55 else ConfidenceTier.EARLY_GUESS
        elif self.total_trades < 250:
            return ConfidenceTier.PROVEN if self.win_rate >= 0.60 else ConfidenceTier.VALIDATED
        elif self.total_trades < 500:
            return ConfidenceTier.CERTAIN if self.win_rate >= 0.65 else ConfidenceTier.PROVEN
        else:
            return ConfidenceTier.INSTITUTIONAL if self.win_rate >= 0.70 else ConfidenceTier.CERTAIN
    
    @property
    def is_alertable(self) -> bool:
        """Can we alert on this signal?"""
        tier = self.confidence_tier
        return tier in [
            ConfidenceTier.VALIDATED,
            ConfidenceTier.PROVEN, 
            ConfidenceTier.CERTAIN,
            ConfidenceTier.INSTITUTIONAL
        ]
    
    def to_dict(self) -> dict:
        return {
            'strategy_id': self.strategy_id,
            'total_trades': self.total_trades,
            'win_rate': f"{self.win_rate:.1%}",
            'sharpe_ratio': f"{self.sharpe_ratio:.2f}",
            'tier': self.confidence_tier.value,
            'alertable': self.is_alertable
        }


@dataclass
class QualityGateConfig:
    """Configuration for quality gates"""
    # Minimum requirements for alerting
    min_total_trades: int = 50
    min_win_rate: float = 0.55
    min_sharpe_ratio: float = 0.5
    max_consecutive_losses: int = 5
    
    # RSVE timeline (in days from first signal)
    rsve_week_1_days: int = 7      # Accumulation - NO ALERTS
    rsve_week_2_days: int = 14     # Paper trading - NO ALERTS
    rsve_week_3_days: int = 21     # Live testing - CAUTION ALERTS
    
    # Confidence score multipliers by tier
    tier_multipliers: Dict[ConfidenceTier, float] = field(default_factory=lambda: {
        ConfidenceTier.EARLY_GUESS: 0.0,      # Suppressed entirely
        ConfidenceTier.EMERGING: 0.5,         # Halve confidence
        ConfidenceTier.VALIDATED: 0.8,        # Slight discount
        ConfidenceTier.PROVEN: 1.0,           # Full confidence
        ConfidenceTier.CERTAIN: 1.1,          # Boost
        ConfidenceTier.INSTITUTIONAL: 1.2     # Maximum boost
    })


class QualityGatedAlertSystem:
    """
    Enhanced alert system with "Are We Sure?" quality gates
    
    KEY PRINCIPLE: Only alert when we have statistical evidence
    SUPPRESS: Early guesses, unvalidated strategies, failing systems
    """
    
    def __init__(self, config: QualityGateConfig = None):
        self.config = config or QualityGateConfig()
        self.strategy_metrics: Dict[str, SignalQualityMetrics] = {}
        self.alert_history: List[dict] = []
        self.suppressed_count = 0
        self.alerted_count = 0
        
        # Load existing metrics if available
        self._load_metrics()
    
    def _load_metrics(self):
        """Load strategy metrics from disk"""
        try:
            if os.path.exists('strategy_metrics.json'):
                with open('strategy_metrics.json', 'r') as f:
                    data = json.load(f)
                    for sid, metrics in data.items():
                        self.strategy_metrics[sid] = SignalQualityMetrics(
                            strategy_id=sid,
                            total_trades=metrics.get('total_trades', 0),
                            winning_trades=metrics.get('winning_trades', 0),
                            losing_trades=metrics.get('losing_trades', 0),
                            win_rate=metrics.get('win_rate', 0.0),
                            sharpe_ratio=metrics.get('sharpe_ratio', 0.0),
                            max_drawdown=metrics.get('max_drawdown', 0.0)
                        )
        except Exception as e:
            print(f"Could not load metrics: {e}")
    
    def _save_metrics(self):
        """Save strategy metrics to disk"""
        try:
            data = {sid: m.to_dict() for sid, m in self.strategy_metrics.items()}
            with open('strategy_metrics.json', 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Could not save metrics: {e}")
    
    def update_strategy_metrics(self, strategy_id: str, 
                                won: bool, 
                                profit: float,
                                trade_date: datetime = None):
        """Update metrics after trade resolution"""
        if strategy_id not in self.strategy_metrics:
            self.strategy_metrics[strategy_id] = SignalQualityMetrics(
                strategy_id=strategy_id,
                first_trade_date=trade_date or datetime.now(timezone.utc)
            )
        
        metrics = self.strategy_metrics[strategy_id]
        metrics.total_trades += 1
        metrics.last_trade_date = trade_date or datetime.now(timezone.utc)
        
        if won:
            metrics.winning_trades += 1
            metrics.consecutive_wins += 1
            metrics.consecutive_losses = 0
        else:
            metrics.losing_trades += 1
            metrics.consecutive_losses += 1
            metrics.consecutive_wins = 0
        
        # Recalculate win rate
        metrics.win_rate = metrics.winning_trades / metrics.total_trades
        
        self._save_metrics()
        return metrics
    
    def evaluate_signal_quality(self, 
                                strategy_id: str,
                                base_confidence: float,
                                signal_age_days: int = 0) -> Tuple[bool, float, str]:
        """
        Evaluate if signal passes quality gates
        
        Returns:
            (should_alert: bool, adjusted_confidence: float, reason: str)
        """
        metrics = self.strategy_metrics.get(strategy_id)
        
        # NEW STRATEGY - RSVE PIPELINE CHECK
        if not metrics or metrics.total_trades < 30:
            self.suppressed_count += 1
            return False, 0.0, f"🚫 SUPPRESSED: Strategy '{strategy_id}' in RSVE Week 1 (<30 trades). Early guess - not enough data."
        
        tier = metrics.confidence_tier
        
        # CHECK 1: Minimum trade count
        if metrics.total_trades < self.config.min_total_trades:
            self.suppressed_count += 1
            return False, 0.0, f"🚫 SUPPRESSED: Only {metrics.total_trades} trades (need {self.config.min_total_trades}+). Emerging strategy - monitoring only."
        
        # CHECK 2: Win rate threshold
        if metrics.win_rate < self.config.min_win_rate:
            self.suppressed_count += 1
            return False, 0.0, f"🚫 SUPPRESSED: Win rate {metrics.win_rate:.1%} below {self.config.min_win_rate:.0%} threshold. Strategy underperforming."
        
        # CHECK 3: Consecutive losses (strategy might be broken)
        if metrics.consecutive_losses >= self.config.max_consecutive_losses:
            self.suppressed_count += 1
            return False, 0.0, f"🚫 SUPPRESSED: {metrics.consecutive_losses} consecutive losses. Possible regime change or broken strategy."
        
        # CHECK 4: Sharpe ratio (risk-adjusted returns)
        if metrics.sharpe_ratio < self.config.min_sharpe_ratio and metrics.total_trades > 100:
            self.suppressed_count += 1
            return False, 0.0, f"🚫 SUPPRESSED: Sharpe {metrics.sharpe_ratio:.2f} below {self.config.min_sharpe_ratio}. Poor risk-adjusted returns."
        
        # PASSED ALL GATES - Calculate adjusted confidence
        multiplier = self.config.tier_multipliers.get(tier, 1.0)
        adjusted_confidence = min(100, base_confidence * multiplier)
        
        # Determine "how sure" language
        sureness = self._get_sureness_language(tier, metrics)
        
        self.alerted_count += 1
        return True, adjusted_confidence, sureness
    
    def _get_sureness_language(self, tier: ConfidenceTier, metrics: SignalQualityMetrics) -> str:
        """Generate human-readable sureness statement"""
        
        if tier == ConfidenceTier.INSTITUTIONAL:
            return (
                f"✅ CERTAIN: {metrics.total_trades}+ trades, {metrics.win_rate:.1%} WR, "
                f"Sharpe {metrics.sharpe_ratio:.2f}. Institutional-grade signal with extensive validation. "
                f"This is as sure as we get in trading."
            )
        elif tier == ConfidenceTier.CERTAIN:
            return (
                f"✅ HIGH CONFIDENCE: {metrics.total_trades} trades, {metrics.win_rate:.1%} WR. "
                f"Well-validated strategy with proven edge. Solid alert."
            )
        elif tier == ConfidenceTier.PROVEN:
            return (
                f"✅ MODERATE CONFIDENCE: {metrics.total_trades} trades, {metrics.win_rate:.1%} WR. "
                f"Strategy has demonstrated consistent performance. Good alert."
            )
        elif tier == ConfidenceTier.VALIDATED:
            return (
                f"⚠️ CAUTION - VALIDATING: {metrics.total_trades} trades, {metrics.win_rate:.1%} WR. "
                f"Minimum viability met but still building track record. Smaller position size recommended."
            )
        else:
            return f"❓ UNKNOWN TIER: {tier.value}"
    
    def format_quality_alert(self,
                            symbol: str,
                            signal_type: str,
                            entry_price: float,
                            stop_loss: float,
                            take_profit: float,
                            strategy_id: str,
                            base_confidence: float,
                            sureness_statement: str,
                            adjusted_confidence: float,
                            factors: Dict = None) -> str:
        """Format alert with quality indicators"""
        
        metrics = self.strategy_metrics.get(strategy_id)
        tier = metrics.confidence_tier if metrics else ConfidenceTier.EARLY_GUESS
        
        # Emoji based on tier
        tier_emoji = {
            ConfidenceTier.INSTITUTIONAL: "🏆",
            ConfidenceTier.CERTAIN: "🎯",
            ConfidenceTier.PROVEN: "✅",
            ConfidenceTier.VALIDATED: "⚠️",
            ConfidenceTier.EMERGING: "🔍",
            ConfidenceTier.EARLY_GUESS: "❌"
        }.get(tier, "❓")
        
        # Calculate R:R
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        rr_ratio = reward / risk if risk > 0 else 0
        
        alert = f"""
{'='*70}
{tier_emoji} QUALITY-GATED ALERT - {tier.value.upper().replace('_', ' ')}
{'='*70}

🎯 {symbol} {signal_type.upper()} SIGNAL

📊 CONFIDENCE ASSESSMENT:
   Base Confidence: {base_confidence:.0f}/100
   Adjusted Confidence: {adjusted_confidence:.0f}/100 (after quality gates)
   
   {sureness_statement}

📈 STRATEGY VALIDATION:
   Strategy ID: {strategy_id}
   Total Trades: {metrics.total_trades if metrics else 'N/A'}
   Win Rate: {metrics.win_rate:.1% if metrics else 'N/A'}
   Sharpe Ratio: {metrics.sharpe_ratio:.2f if metrics else 'N/A'}
   Consecutive Losses: {metrics.consecutive_losses if metrics else 'N/A'}

💰 TRADE DETAILS:
   Entry: ${entry_price:,.8f}
   Stop:  ${stop_loss:,.8f} ({((stop_loss/entry_price)-1)*100:.1f}%)
   Target: ${take_profit:,.8f} ({((take_profit/entry_price)-1)*100:.1f}%)
   R:R Ratio: 1:{rr_ratio:.1f}

🛡️ POSITION SIZING RECOMMENDATION:
"""
        
        # Position sizing based on tier
        if tier == ConfidenceTier.INSTITUTIONAL:
            alert += """   ✅ FULL SIZE: 2-3% risk (institutional grade)
   ✅ Standard stop placement
   ✅ Full target expectation"""
        elif tier == ConfidenceTier.CERTAIN:
            alert += """   ✅ NORMAL SIZE: 1.5-2% risk (high confidence)
   ✅ Standard stop placement
   ✅ Full target expectation"""
        elif tier == ConfidenceTier.PROVEN:
            alert += """   ⚠️ REDUCED SIZE: 1-1.5% risk (proven but watchful)
   ✅ Standard stop placement
   ⚠️ Consider 75% target"""
        elif tier == ConfidenceTier.VALIDATED:
            alert += """   🔍 TEST SIZE: 0.5-1% risk (still validating)
   ⚠️ Tighter stop recommended
   ⚠️ Scale 50% at first target"""
        else:
            alert += """   ❌ PAPER ONLY: Do not trade (insufficient data)"""
        
        alert += f"""

🔍 SETUP FACTORS:
"""
        if factors:
            for key, value in factors.items():
                alert += f"   • {key}: {value}\n"
        else:
            alert += "   • Standard setup\n"
        
        alert += f"""
⚠️  RISK MANAGEMENT:
   • Set alerts at entry, stop, 50% target, full target
   • If not triggered within 4 hours, reassess
   • Market conditions can change - use stops religiously
   
📊 QUALITY GATE STATS:
   Alerts Sent: {self.alerted_count}
   Suppressed (Early Guesses): {self.suppressed_count}
   Quality Rate: {self.alerted_count/(self.alerted_count + self.suppressed_count)*100:.1f}%

{'='*70}
        """
        
        return alert
    
    def should_alert(self, 
                     strategy_id: str,
                     base_confidence: float,
                     **kwargs) -> Tuple[bool, Optional[str]]:
        """
        Main entry point: Should we send this alert?
        
        Returns: (should_send: bool, formatted_alert_or_reason: str)
        """
        should_alert, adjusted_confidence, reason = self.evaluate_signal_quality(
            strategy_id, base_confidence
        )
        
        if not should_alert:
            # Return the suppression reason
            return False, reason
        
        # Generate the quality alert
        alert_text = self.format_quality_alert(
            strategy_id=strategy_id,
            base_confidence=base_confidence,
            adjusted_confidence=adjusted_confidence,
            sureness_statement=reason,
            **kwargs
        )
        
        return True, alert_text
    
    def get_quality_summary(self) -> str:
        """Get summary of all strategy quality metrics"""
        
        summary = """
{'='*70}
📊 STRATEGY QUALITY SUMMARY - "ARE WE SURE?"
{'='*70}

"""
        
        # Group by tier
        by_tier = {}
        for sid, metrics in self.strategy_metrics.items():
            tier = metrics.confidence_tier
            if tier not in by_tier:
                by_tier[tier] = []
            by_tier[tier].append((sid, metrics))
        
        # Output by tier
        for tier in [ConfidenceTier.INSTITUTIONAL, ConfidenceTier.CERTAIN, 
                     ConfidenceTier.PROVEN, ConfidenceTier.VALIDATED,
                     ConfidenceTier.EMERGING, ConfidenceTier.EARLY_GUESS]:
            if tier in by_tier:
                emoji = {
                    ConfidenceTier.INSTITUTIONAL: "🏆",
                    ConfidenceTier.CERTAIN: "🎯",
                    ConfidenceTier.PROVEN: "✅",
                    ConfidenceTier.VALIDATED: "⚠️",
                    ConfidenceTier.EMERGING: "🔍",
                    ConfidenceTier.EARLY_GUESS: "❌"
                }.get(tier, "❓")
                
                summary += f"\n{emoji} {tier.value.upper().replace('_', ' ')} ({len(by_tier[tier])} strategies)\n"
                summary += "-" * 50 + "\n"
                
                for sid, m in sorted(by_tier[tier], key=lambda x: x[1].win_rate, reverse=True):
                    alert_status = "✅ ALERT" if m.is_alertable else "🚫 SUPPRESS"
                    summary += f"   {alert_status} {sid}: {m.total_trades} trades, {m.win_rate:.1%} WR\n"
        
        summary += f"""
{'='*70}
SUMMARY:
   Total Strategies: {len(self.strategy_metrics)}
   Alertable: {sum(1 for m in self.strategy_metrics.values() if m.is_alertable)}
   Suppressed: {sum(1 for m in self.strategy_metrics.values() if not m.is_alertable)}
   
   Alerts Sent: {self.alerted_count}
   Suppressed (Quality Gates): {self.suppressed_count}
{'='*70}
"""
        return summary


# Example usage and testing
if __name__ == "__main__":
    
    # Initialize system
    alert_system = QualityGatedAlertSystem()
    
    print("🎯 Quality-Gated Alert System - 'Are We Sure?' Edition")
    print("="*70)
    
    # Simulate some strategy history
    print("\n📊 Simulating strategy validation history...\n")
    
    # Strategy 1: Brand new (should be suppressed)
    print("Strategy A: Brand new, 5 trades, 60% WR")
    for i in range(5):
        alert_system.update_strategy_metrics("STRAT_NEW_5", won=i<3, profit=100 if i<3 else -50)
    
    # Strategy 2: Emerging (should be suppressed)
    print("Strategy B: Emerging, 35 trades, 57% WR")
    for i in range(35):
        alert_system.update_strategy_metrics("STRAT_EMERGING_35", won=i<20, profit=100 if i<20 else -50)
    
    # Strategy 3: Validated (should alert with caution)
    wins = [True] * 30 + [False] * 20  # 60% WR
    print("Strategy C: Validated, 50 trades, 60% WR")
    for i, won in enumerate(wins):
        alert_system.update_strategy_metrics("STRAT_VALIDATED_50", won=won, profit=100 if won else -50)
    
    # Strategy 4: Proven (should alert normally)
    wins = [True] * 120 + [False] * 80  # 60% WR
    print("Strategy D: Proven, 200 trades, 60% WR")
    for i, won in enumerate(wins):
        alert_system.update_strategy_metrics("STRAT_PROVEN_200", won=won, profit=100 if won else -50)
    
    # Strategy 5: Institutional (should alert with high confidence)
    wins = [True] * 350 + [False] * 150  # 70% WR
    print("Strategy E: Institutional, 500 trades, 70% WR")
    for i, won in enumerate(wins):
        alert_system.update_strategy_metrics("STRAT_INSTITUTIONAL_500", won=won, profit=100 if won else -50)
    
    # Strategy 6: Broken (should be suppressed due to consecutive losses)
    print("Strategy F: Broken, 100 trades, 50% WR, 5 consecutive losses")
    for i in range(95):
        alert_system.update_strategy_metrics("STRAT_BROKEN", won=i<50, profit=100 if i<50 else -50)
    for i in range(5):  # Add 5 consecutive losses
        alert_system.update_strategy_metrics("STRAT_BROKEN", won=False, profit=-50)
    
    print("\n" + "="*70)
    print("\n🧪 TESTING ALERT QUALITY GATES:\n")
    
    test_cases = [
        ("STRAT_NEW_5", 85, "Brand new strategy"),
        ("STRAT_EMERGING_35", 82, "Emerging strategy"),
        ("STRAT_VALIDATED_50", 80, "Validated strategy"),
        ("STRAT_PROVEN_200", 85, "Proven strategy"),
        ("STRAT_INSTITUTIONAL_500", 92, "Institutional strategy"),
        ("STRAT_BROKEN", 75, "Broken strategy (consecutive losses)"),
        ("STRAT_UNKNOWN", 90, "Unknown strategy (no history)"),
    ]
    
    for strategy_id, confidence, description in test_cases:
        print(f"\n{'='*70}")
        print(f"TEST: {description}")
        print(f"Strategy: {strategy_id}, Base Confidence: {confidence}")
        print("-"*70)
        
        should_alert, result = alert_system.should_alert(
            strategy_id=strategy_id,
            base_confidence=confidence,
            symbol="BTCUSDT",
            signal_type="buy",
            entry_price=50000,
            stop_loss=49000,
            take_profit=52000
        )
        
        if should_alert:
            print("✅ ALERT APPROVED - See formatted alert below:")
            print(result)
        else:
            print("🚫 ALERT SUPPRESSED")
            print(result)
    
    # Print quality summary
    print(alert_system.get_quality_summary())
