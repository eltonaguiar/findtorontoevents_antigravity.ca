#!/usr/bin/env python3
"""
Unified Signal Aggregation Layer
Phase 1 Implementation: Signal Quality Enhancement

Aggregates signals from 15+ trading systems with:
- Confidence-weighted voting
- Bayesian updating
- Real-time regime detection
"""

import json
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SignalDirection(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class SignalConfidence(Enum):
    HIGH = "high"      # >70% consensus
    MEDIUM = "medium"  # 50-70% consensus
    LOW = "low"        # <50% consensus


@dataclass
class Signal:
    symbol: str
    direction: SignalDirection
    confidence: float  # 0.0 to 1.0
    system: str
    timestamp: datetime
    entry_price: Optional[float] = None
    tp_price: Optional[float] = None
    sl_price: Optional[float] = None
    timeframe: str = "1h"
    strategy_dna: Optional[str] = None
    strategy: str = ""
    quality_score: float = 0.0
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self):
        return {
            'symbol': self.symbol,
            'direction': self.direction.value,
            'confidence': self.confidence,
            'system': self.system,
            'timestamp': self.timestamp.isoformat(),
            'entry_price': self.entry_price,
            'tp_price': self.tp_price,
            'sl_price': self.sl_price,
            'timeframe': self.timeframe,
            'strategy_dna': self.strategy_dna,
            'strategy': self.strategy,
            'quality_score': self.quality_score,
            'metadata': self.metadata
        }


@dataclass
class ConsensusSignal:
    symbol: str
    direction: SignalDirection
    consensus_score: float
    agreeing_systems: List[str]
    total_systems: int
    average_confidence: float
    confidence_tier: SignalConfidence
    timestamp: datetime
    signals: List[Signal]
    
    def to_dict(self):
        return {
            'symbol': self.symbol,
            'direction': self.direction.value,
            'consensus_score': self.consensus_score,
            'agreeing_systems': self.agreeing_systems,
            'total_systems': self.total_systems,
            'average_confidence': self.average_confidence,
            'confidence_tier': self.confidence_tier.value,
            'timestamp': self.timestamp.isoformat(),
            'signals': [s.to_dict() for s in self.signals]
        }


class MarketRegimeDetector:
    """Detect current market regime for weight adjustment."""
    
    def __init__(self):
        self.regime_weights = {
            'bull_low_vol': {
                'momentum': 1.3,
                'trend_following': 1.2,
                'mean_reversion': 0.7,
                'breakout': 1.1
            },
            'bull_high_vol': {
                'momentum': 1.0,
                'trend_following': 1.0,
                'mean_reversion': 0.9,
                'breakout': 1.2
            },
            'bear_low_vol': {
                'momentum': 0.6,
                'trend_following': 0.7,
                'mean_reversion': 1.2,
                'breakout': 0.8
            },
            'bear_high_vol': {
                'momentum': 0.5,
                'trend_following': 0.6,
                'mean_reversion': 1.3,
                'breakout': 1.0
            },
            'sideways': {
                'momentum': 0.7,
                'trend_following': 0.5,
                'mean_reversion': 1.4,
                'breakout': 1.2
            }
        }
    
    def detect_regime(self, market_data: Dict) -> str:
        """Detect current market regime from data."""
        trend = market_data.get('trend', 0)
        volatility = market_data.get('volatility', 0.5)
        
        if abs(trend) < 0.1:
            return 'sideways'
        elif trend > 0:
            return 'bull_low_vol' if volatility < 0.5 else 'bull_high_vol'
        else:
            return 'bear_low_vol' if volatility < 0.5 else 'bear_high_vol'
    
    def get_system_weight(self, regime: str, system_type: str) -> float:
        """Get weight multiplier for system type in current regime."""
        weights = self.regime_weights.get(regime, {})
        return weights.get(system_type, 1.0)


class SignalAggregator:
    """
    Unified signal aggregation from 15+ trading systems.
    """
    
    # System registry with endpoints and types
    SYSTEMS = {
        'mercury2': {
            'url': 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/mercury2/data/active_picks.json',
            'type': 'momentum',
            'weight': 1.0,
            'reliability': 0.85
        },
        'claws_of_doom': {
            'url': 'https://raw.githubusercontent.com/eltonaguiar/CLAWSOFDOOM/main/docs/active_picks.json',
            'type': 'momentum',
            'weight': 1.0,
            'reliability': 0.80
        },
        'alpha_engine': {
            'url': 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/alpha_engine/data/active_picks.json',
            'type': 'trend_following',
            'weight': 1.2,
            'reliability': 0.90
        },
        'kimi': {
            'url': 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/KIMI_RISEOFTHECLAW/data/active_picks.json',
            'type': 'trend_following',
            'weight': 1.1,
            'reliability': 0.82
        },
        'crypto_ml_edge': {
            'url': 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/crypto_ml_edge/data/active_picks.json',
            'type': 'momentum',
            'weight': 1.0,
            'reliability': 0.78
        },
        'claude_gainer': {
            'url': 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/claude_gainer_ml/tracker/claude_live_picks.json',
            'type': 'momentum',
            'weight': 0.9,
            'reliability': 0.75
        },
        'dna_genome': {
            'url': 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/genome/active_picks.json',
            'type': 'mean_reversion',
            'weight': 1.1,
            'reliability': 0.88
        },
        'quantum_fusion': {
            'url': 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/quantum_fusion_report.json',
            'type': 'breakout',
            'weight': 1.0,
            'reliability': 0.72
        }
    }
    
    def __init__(self):
        self.signals: Dict[str, List[Signal]] = defaultdict(list)
        self.consensus_signals: Dict[str, ConsensusSignal] = {}
        self.regime_detector = MarketRegimeDetector()
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Bayesian tracking
        self.system_performance = defaultdict(lambda: {'wins': 0, 'losses': 0})
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_system_signals(self, system_name: str) -> List[Signal]:
        """Fetch signals from a single system."""
        config = self.SYSTEMS.get(system_name)
        if not config:
            logger.error(f"Unknown system: {system_name}")
            return []
        
        try:
            async with self.session.get(config['url'], timeout=10) as response:
                if response.status != 200:
                    logger.warning(f"{system_name}: HTTP {response.status}")
                    return []
                
                data = await response.json()
                signals = self._parse_signals(data, system_name, config)
                logger.info(f"{system_name}: Fetched {len(signals)} signals")
                return signals
                
        except Exception as e:
            logger.error(f"{system_name}: Fetch error - {e}")
            return []
    
    # ── Signal Quality Gates ────────────────────────────────────────────────
    # Minimum reward:risk below which a signal is rejected outright.
    # At 0.40% round-trip commission (IBKR crypto) a 1:1 R:R trade has negative EV.
    MIN_RR = 1.2
    # Minimum confidence (0–1) required to enter signal processing.
    MIN_CONFIDENCE = 0.40

    @staticmethod
    def _compute_rr(direction: SignalDirection, entry: Optional[float],
                    tp: Optional[float], sl: Optional[float]) -> Optional[float]:
        """Return reward:risk ratio, or None when prices are missing/invalid."""
        if not (entry and tp and sl):
            return None
        # Validate TP/SL orientation — malformed levels produce nonsense R:R values.
        if direction == SignalDirection.LONG:
            if tp <= entry or sl >= entry:
                return None  # malformed LONG: TP must be above entry, SL must be below
        elif direction == SignalDirection.SHORT:
            if tp >= entry or sl <= entry:
                return None  # malformed SHORT: TP must be below entry, SL must be above
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        if risk <= 0:
            return None
        return round(reward / risk, 2)

    def _validate_signal_quality(self, signal: 'Signal') -> tuple[bool, str, Optional[str]]:
        """
        Gate every incoming signal against minimum quality thresholds.

        Returns (accepted: bool, reason: str, rejection_type: Optional[str]).
        rejection_type is 'rr', 'confidence', or None when accepted.
        Rules applied in order — first failure short-circuits.
        """
        # 1. Confidence gate
        if signal.confidence < self.MIN_CONFIDENCE:
            return False, f"confidence {signal.confidence:.0%} < {self.MIN_CONFIDENCE:.0%}", "confidence"

        # 2. R:R gate — requires entry, TP, and SL all present
        rr = self._compute_rr(signal.direction, signal.entry_price, signal.tp_price, signal.sl_price)
        if rr is not None and rr < self.MIN_RR:
            return False, f"R:R {rr:.2f} < minimum {self.MIN_RR}", "rr"

        return True, "ok", None

    def _parse_signals(self, data: Dict, system: str, config: Dict) -> List[Signal]:
        """Parse system-specific response format, applying quality gates."""
        signals = []
        rejected_rr = 0
        rejected_conf = 0

        # Handle different response formats
        picks = data.get('picks', data.get('signals', data.get('active_picks', [])))

        for raw_pick in picks:
            try:
                direction_str = raw_pick.get('direction', raw_pick.get('signal', 'NEUTRAL')).upper()
                direction = SignalDirection(direction_str) if direction_str in ['LONG', 'SHORT', 'BUY', 'SELL'] else SignalDirection.NEUTRAL

                if direction == SignalDirection.NEUTRAL:
                    continue

                raw_conf = raw_pick.get('confidence', raw_pick.get('quality_score', 50))
                # Auto-detect scale: if > 1, it's 0-100 scale; if <= 1, it's already 0-1
                confidence = raw_conf / 100.0 if raw_conf > 1 else float(raw_conf)

                # Preserve original entry timestamp — don't overwrite with now()
                _orig_ts = (raw_pick.get('entryDate') or raw_pick.get('entry_time')
                            or raw_pick.get('timestamp') or raw_pick.get('picked_at'))
                try:
                    _pick_ts = datetime.fromisoformat(str(_orig_ts).replace('Z', '+00:00')) if _orig_ts else datetime.now()
                except (ValueError, TypeError):
                    _pick_ts = datetime.now()
                signal = Signal(
                    symbol=raw_pick.get('symbol', raw_pick.get('pair', 'UNKNOWN')),
                    direction=direction,
                    confidence=confidence,
                    system=system,
                    timestamp=_pick_ts,
                    entry_price=raw_pick.get('entry_price'),
                    tp_price=raw_pick.get('take_profit', raw_pick.get('tp_price')),
                    sl_price=raw_pick.get('stop_loss', raw_pick.get('sl_price')),
                    timeframe=raw_pick.get('timeframe', '1h'),
                    strategy_dna=raw_pick.get('strategy_dna'),
                    strategy=raw_pick.get('strategy', raw_pick.get('algorithmName', raw_pick.get('algorithm', ''))),
                    quality_score=raw_pick.get('quality_score', 0.0),
                    metadata={
                        'system_type': config['type'],
                        'system_weight': config['weight'],
                        'system_reliability': config['reliability'],
                        'rr': self._compute_rr(direction, raw_pick.get('entry_price'),
                                               raw_pick.get('take_profit', raw_pick.get('tp_price')),
                                               raw_pick.get('stop_loss', raw_pick.get('sl_price'))),
                    }
                )

                accepted, reason, rejection_type = self._validate_signal_quality(signal)
                if not accepted:
                    if rejection_type == 'rr':
                        rejected_rr += 1
                    elif rejection_type == 'confidence':
                        rejected_conf += 1
                    logger.debug(f"[{system}] Rejected {signal.symbol}: {reason}")
                    continue

                signals.append(signal)
            except Exception as e:
                logger.warning(f"Parse error for {system}: {e}")
                continue

        if rejected_rr or rejected_conf:
            logger.info(
                f"[{system}] Quality gate: {len(signals)} accepted, "
                f"{rejected_rr} rejected (low R:R), {rejected_conf} rejected (low confidence)"
            )

        return signals
    
    async def aggregate_all_signals(self) -> Dict[str, ConsensusSignal]:
        """Fetch and aggregate signals from all systems."""
        logger.info("Starting signal aggregation from all systems...")
        
        # Fetch all systems concurrently
        tasks = [
            self.fetch_system_signals(name)
            for name in self.SYSTEMS.keys()
        ]
        
        all_signals = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect signals by symbol
        symbol_signals = defaultdict(list)
        for system_name, signals in zip(self.SYSTEMS.keys(), all_signals):
            if isinstance(signals, Exception):
                logger.error(f"{system_name} failed: {signals}")
                continue
            
            for signal in signals:
                symbol_signals[signal.symbol].append(signal)
        
        # Calculate consensus for each symbol
        self.consensus_signals = {}
        for symbol, signals in symbol_signals.items():
            consensus = self._calculate_consensus(symbol, signals)
            if consensus:
                self.consensus_signals[symbol] = consensus
        
        logger.info(f"Aggregation complete: {len(self.consensus_signals)} consensus signals")
        return self.consensus_signals
    
    def _calculate_consensus(self, symbol: str, signals: List[Signal]) -> Optional[ConsensusSignal]:
        """Calculate consensus using weighted voting."""
        if not signals:
            return None
        
        # Count by direction with weights
        direction_weights = defaultdict(float)
        direction_confidence = defaultdict(list)
        
        for signal in signals:
            # Get Bayesian-updated system weight
            bayesian_weight = self._get_bayesian_weight(signal.system)
            
            # Apply regime-based adjustment
            # (In production, would get actual regime from market data)
            regime_weight = 1.0  # Simplified
            
            # Combined weight
            total_weight = (
                signal.confidence * 
                signal.metadata.get('system_weight', 1.0) *
                signal.metadata.get('system_reliability', 0.8) *
                bayesian_weight *
                regime_weight
            )
            
            direction_weights[signal.direction] += total_weight
            direction_confidence[signal.direction].append(signal.confidence)
        
        # Find consensus direction
        if not direction_weights:
            return None
        
        total_weight = sum(direction_weights.values())
        consensus_direction = max(direction_weights.items(), key=lambda x: x[1])
        
        consensus_score = consensus_direction[1] / total_weight
        
        # Determine confidence tier
        if consensus_score > 0.7:
            confidence_tier = SignalConfidence.HIGH
        elif consensus_score > 0.5:
            confidence_tier = SignalConfidence.MEDIUM
        else:
            confidence_tier = SignalConfidence.LOW
        
        # Get agreeing systems
        agreeing_systems = sorted({
            s.system for s in signals
            if s.direction == consensus_direction[0]
        })
        
        # Calculate average confidence
        avg_confidence = np.mean(direction_confidence[consensus_direction[0]])
        
        return ConsensusSignal(
            symbol=symbol,
            direction=consensus_direction[0],
            consensus_score=consensus_score,
            agreeing_systems=agreeing_systems,
            total_systems=len(set(s.system for s in signals)),
            average_confidence=avg_confidence,
            confidence_tier=confidence_tier,
            # Use earliest signal timestamp to preserve original entry time
            timestamp=min((s.timestamp for s in signals), default=datetime.now()),
            signals=signals
        )
    
    def _get_bayesian_weight(self, system: str) -> float:
        """Get Bayesian-updated weight based on historical performance."""
        perf = self.system_performance[system]
        total = perf['wins'] + perf['losses']
        
        if total < 10:
            return 1.0  # Neutral until enough data
        
        # Bayesian update: wins / total with prior
        win_rate = (perf['wins'] + 5) / (total + 10)  # Beta(5,5) prior
        return 0.5 + win_rate  # Scale to 0.5-1.5
    
    def update_system_performance(self, system: str, result: str):
        """Update Bayesian tracking with new result."""
        if result == 'win':
            self.system_performance[system]['wins'] += 1
        else:
            self.system_performance[system]['losses'] += 1
    
    def get_super_signals(self, min_consensus: float = 0.7) -> List[ConsensusSignal]:
        """Get high-confidence consensus signals."""
        return [
            cs for cs in self.consensus_signals.values()
            if cs.consensus_score >= min_consensus
        ]
    
    def export_consensus(self, filepath: str):
        """Export consensus signals to JSON."""
        data = {
            'generated_at': datetime.now().isoformat(),
            'total_consensus': len(self.consensus_signals),
            'super_signals': len(self.get_super_signals()),
            'signals': {
                symbol: cs.to_dict()
                for symbol, cs in self.consensus_signals.items()
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Exported consensus to {filepath}")


async def main():
    """Test the signal aggregator."""
    async with SignalAggregator() as aggregator:
        consensus = await aggregator.aggregate_all_signals()
        
        print("\n" + "="*60)
        print("SIGNAL AGGREGATION RESULTS")
        print("="*60)
        
        # Show super signals
        super_signals = aggregator.get_super_signals(min_consensus=0.7)
        print(f"\nSuper Signals (>=70% consensus): {len(super_signals)}")
        
        for cs in sorted(super_signals, key=lambda x: x.consensus_score, reverse=True):
            print(f"\n  {cs.symbol}: {cs.direction.value}")
            print(f"    Consensus: {cs.consensus_score:.1%}")
            print(f"    Systems: {', '.join(cs.agreeing_systems)}")
            print(f"    Confidence: {cs.confidence_tier.value}")
        
        # Export
        aggregator.export_consensus('signal_aggregator/consensus_output.json')


if __name__ == "__main__":
    asyncio.run(main())
