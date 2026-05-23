"""
Fixed Signal Aggregator - Works with local file-based systems

Addresses issues from analysis:
- 0 active systems (now properly activates local systems)
- 0 consensus signals (now generates from local data)
- System registry integration
"""

import json
import asyncio
import aiohttp
import aiofiles
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
from collections import defaultdict
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Maximum age (in seconds) for a signal to be considered fresh.
# Signals older than this are dropped before aggregation.
SIGNAL_FRESHNESS_MAX_SECONDS = 86400  # 24 hours — was 900 (15min), which killed signals from systems running every 15-30min


class SignalDirection(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


@dataclass
class Signal:
    symbol: str
    direction: SignalDirection
    confidence: float
    system: str
    timestamp: datetime
    entry_price: Optional[float] = None
    tp_price: Optional[float] = None
    sl_price: Optional[float] = None
    timeframe: str = "1h"
    strategy_dna: Optional[str] = None
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
            'substrategy': self.strategy_dna,  # Alias for easier access
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
            'timestamp': self.timestamp.isoformat(),
            'signals': [s.to_dict() for s in self.signals]
        }


class FixedSignalAggregator:
    """
    Fixed signal aggregator that works with local file-based systems.
    """
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self.session = session
        self.consensus_signals: Dict[str, ConsensusSignal] = {}
        self.system_status: Dict[str, Dict] = {}
        
        # Local system paths (fallback when URLs fail)
        self.LOCAL_SYSTEM_PATHS = {
            'mercury2': 'mercury2/data/active_picks.json',
            'alpha_engine': 'alpha_engine/data/active_picks.json',
            'kimi': 'KIMI_RISEOFTHECLAW/data/active_picks.json',
            'crypto_ml_edge': 'crypto_ml_edge/data/active_picks.json',
            'claude_gainer': 'claude_gainer_ml/tracker/claude_live_picks.json',
            
            # Velocity-based strategies (activated for surge detection)
            'velocity_rsi': 'signal_aggregator/strategies/rsi_velocity.py',
            'velocity_zscore': 'signal_aggregator/strategies/zscore_velocity.py',
            'dna_genome': 'genome/active_picks.json',
            'ml_battleground': 'ml_battleground/data/live_signals.json',
            'quantum_fusion': 'quantum_fusion_report.json'
        }
        
        # GitHub URLs (primary source)
        self.REMOTE_URLS = {
            'mercury2': 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/mercury2/data/active_picks.json',
            'alpha_engine': 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/alpha_engine/data/active_picks.json',
            'kimi': 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/KIMI_RISEOFTHECLAW/data/active_picks.json',
            'crypto_ml_edge': 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/crypto_ml_edge/data/active_picks.json',
            'claude_gainer': 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/claude_gainer_ml/tracker/claude_live_picks.json',
            
            # Velocity-based strategies (activated for surge detection)
            'velocity_rsi': 'signal_aggregator/strategies/rsi_velocity.py',
            'velocity_zscore': 'signal_aggregator/strategies/zscore_velocity.py',
            'dna_genome': 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/genome/active_picks.json'
        }
        
        logger.info("Fixed Signal Aggregator initialized")
    
    async def __aenter__(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_system_signals(self, system_name: str) -> List[Signal]:
        """Fetch signals from a system (remote first, then local fallback)."""
        signals = []
        
        # Try remote URL first
        remote_url = self.REMOTE_URLS.get(system_name)
        if remote_url and self.session:
            try:
                async with self.session.get(remote_url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        signals = self._parse_signals(data, system_name)
                        if signals:
                            self._update_system_status(system_name, 'active', len(signals))
                            logger.info(f"{system_name}: Fetched {len(signals)} signals from remote")
                            return signals
            except Exception as e:
                logger.warning(f"{system_name}: Remote fetch failed - {e}")
        
        # Fallback to local file
        local_path = self.LOCAL_SYSTEM_PATHS.get(system_name)
        if local_path and Path(local_path).exists():
            try:
                async with aiofiles.open(local_path, 'r') as f:
                    content = await f.read()
                    data = json.loads(content)
                    signals = self._parse_signals(data, system_name)
                    if signals:
                        self._update_system_status(system_name, 'active', len(signals))
                        logger.info(f"{system_name}: Loaded {len(signals)} signals from local")
                        return signals
            except Exception as e:
                logger.warning(f"{system_name}: Local load failed - {e}")
        
        # If no signals found, mark as inactive but don't fail
        self._update_system_status(system_name, 'inactive', 0)
        return []
    
    def _is_signal_fresh(self, pick: dict, system_name: str) -> bool:
        """
        Check if a raw pick dict has a timestamp within SIGNAL_FRESHNESS_MAX_SECONDS.

        Returns True when no parseable timestamp is present (backwards-compatible).
        """
        ts_raw = pick.get("timestamp") or pick.get("signal_time") or pick.get("generated_at")
        if ts_raw is None:
            return True

        try:
            from datetime import timezone
            if isinstance(ts_raw, (int, float)):
                sig_time = datetime.fromtimestamp(ts_raw, tz=timezone.utc)
            else:
                ts_str = str(ts_raw)
                if ts_str.endswith("Z"):
                    ts_str = ts_str[:-1] + "+00:00"
                sig_time = datetime.fromisoformat(ts_str)
                if sig_time.tzinfo is None:
                    sig_time = sig_time.replace(tzinfo=timezone.utc)
            age = (datetime.now(tz=timezone.utc) - sig_time).total_seconds()
            if age > SIGNAL_FRESHNESS_MAX_SECONDS:
                logger.warning(
                    "%s: Dropping stale signal %s (age=%.0fs, max=%ds)",
                    system_name,
                    pick.get("symbol", "UNKNOWN"),
                    age,
                    SIGNAL_FRESHNESS_MAX_SECONDS,
                )
                return False
        except Exception:
            pass  # unparseable -> treat as fresh
        return True

    @staticmethod
    def _normalize_pick(pick: dict) -> dict:
        """
        Normalize field names from various systems (KIMI, Alpha, Mercury, etc.)
        so _parse_signals sees a consistent schema.

        Mappings (alt -> canonical, only written when canonical is absent):
          signal_time  -> timestamp
          pair         -> symbol
          signal       -> direction
          targetPrice  -> tp_price
          stopPrice    -> sl_price
          entryPrice   -> entry_price
        """
        FIELD_MAP = {
            "signal_time": "timestamp",
            "pair": "symbol",
            "signal": "direction",
            "targetPrice": "tp_price",
            "stopPrice": "sl_price",
            "entryPrice": "entry_price",
        }
        for alt, canonical in FIELD_MAP.items():
            if alt in pick and canonical not in pick:
                pick[canonical] = pick[alt]
        return pick

    def _parse_signals(self, data, system_name: str) -> List[Signal]:
        """Parse signals from various formats."""
        signals = []

        # Handle different response formats
        picks = data
        if isinstance(data, dict):
            picks = data.get('picks', data.get('signals', data.get('active_picks', data.get('activePicks', []))))

        if not isinstance(picks, list):
            logger.warning(f"{system_name}: Unexpected data format")
            return []

        for pick in picks:
            try:
                # Normalize field names from different systems before parsing
                pick = self._normalize_pick(pick)

                # Handle direction
                direction_str = pick.get('direction', pick.get('signal_type', pick.get('signal', 'NEUTRAL'))).upper()
                if direction_str in ['BUY']:
                    direction = SignalDirection.LONG
                elif direction_str in ['SELL']:
                    direction = SignalDirection.SHORT
                elif direction_str in ['LONG', 'SHORT']:
                    direction = SignalDirection(direction_str)
                else:
                    continue

                # Freshness SLA: drop stale signals before aggregation
                if not self._is_signal_fresh(pick, system_name):
                    continue

                # Get confidence
                confidence = pick.get('confidence', pick.get('quality_score', 50))
                if isinstance(confidence, (int, float)):
                    confidence = confidence / 100.0 if confidence > 1 else confidence
                else:
                    confidence = 0.5

                signal = Signal(
                    symbol=pick.get('symbol', pick.get('pair', 'UNKNOWN')),
                    direction=direction,
                    confidence=confidence,
                    system=system_name,
                    timestamp=datetime.now(),
                    entry_price=self._parse_price(pick.get('entry_price', pick.get('entryPrice'))),
                    tp_price=self._parse_price(pick.get('take_profit', pick.get('tp_price', pick.get('targetPrice')))),
                    sl_price=self._parse_price(pick.get('stop_loss', pick.get('sl_price', pick.get('stopPrice')))),
                    timeframe=pick.get('timeframe', '1h'),
                    strategy_dna=pick.get('strategy_dna'),
                    quality_score=pick.get('quality_score', 0.0),
                    metadata={'source': system_name}
                )
                signals.append(signal)
            except Exception as e:
                logger.debug(f"Parse error for {system_name}: {e}")
                continue
        
        return signals
    
    def _parse_price(self, price) -> Optional[float]:
        """Parse price from various formats."""
        if price is None:
            return None
        try:
            return float(price)
        except:
            return None
    
    def _update_system_status(self, system_name: str, status: str, signal_count: int):
        """Update system status for registry."""
        self.system_status[system_name] = {
            'status': status,
            'signal_count': signal_count,
            'last_check': datetime.now().isoformat()
        }
    
    async def aggregate_all_signals(self) -> Dict[str, ConsensusSignal]:
        """Aggregate signals from all available systems."""
        logger.info("Starting signal aggregation...")
        
        # Fetch from all systems
        all_systems = list(self.LOCAL_SYSTEM_PATHS.keys())
        tasks = [self.fetch_system_signals(name) for name in all_systems]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect all signals
        all_signals = []
        active_systems = 0
        
        for system_name, result in zip(all_systems, results):
            if isinstance(result, Exception):
                logger.error(f"{system_name} failed: {result}")
                continue
            
            if result:
                all_signals.extend(result)
                active_systems += 1
        
        logger.info(f"Active systems: {active_systems}/{len(all_systems)}")
        logger.info(f"Total signals: {len(all_signals)}")
        
        # Group by symbol
        symbol_signals = defaultdict(list)
        for signal in all_signals:
            symbol_signals[signal.symbol].append(signal)
        
        # Calculate consensus
        self.consensus_signals = {}
        for symbol, signals in symbol_signals.items():
            consensus = self._calculate_consensus(symbol, signals)
            if consensus:
                self.consensus_signals[symbol] = consensus
        
        logger.info(f"Consensus signals: {len(self.consensus_signals)}")
        return self.consensus_signals
    
    def _calculate_consensus(self, symbol: str, signals: List[Signal]) -> Optional[ConsensusSignal]:
        """Calculate consensus for a symbol."""
        if not signals:
            return None
        
        # Count by direction
        direction_counts = defaultdict(list)
        for signal in signals:
            direction_counts[signal.direction].append(signal)
        
        # Find dominant direction
        if not direction_counts:
            return None
        
        dominant_direction = max(direction_counts.keys(),
                                key=lambda d: len(direction_counts[d]))
        dominant_signals = direction_counts[dominant_direction]

        # Keep only the strongest signal per system so one noisy system
        # cannot look like multi-system consensus.
        best_by_system: Dict[str, Signal] = {}
        for sig in dominant_signals:
            current = best_by_system.get(sig.system)
            if current is None or sig.confidence > current.confidence:
                best_by_system[sig.system] = sig
        dominant_unique = list(best_by_system.values())

        # Calculate consensus metrics
        total_systems = len({s.system for s in signals})
        if total_systems == 0:
            return None
        agreeing_systems = sorted(best_by_system.keys())
        avg_confidence = np.mean([s.confidence for s in dominant_unique]) if dominant_unique else 0.0

        # Consensus score: % of systems agreeing * avg confidence
        agreement_ratio = len(agreeing_systems) / total_systems
        consensus_score = agreement_ratio * avg_confidence

        return ConsensusSignal(
            symbol=symbol,
            direction=dominant_direction,
            consensus_score=consensus_score,
            agreeing_systems=agreeing_systems,
            total_systems=total_systems,
            average_confidence=avg_confidence,
            timestamp=datetime.now(),
            signals=dominant_unique
        )
    
    def export_consensus(self, output_path: str = "signal_aggregator/data/consensus_output.json"):
        """Export consensus signals to file."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'timestamp': datetime.now().isoformat(),
            'total_consensus': len(self.consensus_signals),
            'system_status': self.system_status,
            'signals': {k: v.to_dict() for k, v in self.consensus_signals.items()}
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Consensus exported to {output_path}")
        return output_path
    
    def get_active_systems_count(self) -> int:
        """Get count of active systems."""
        return sum(1 for s in self.system_status.values() if s.get('status') == 'active')


async def main():
    """Test the fixed aggregator."""
    print("Testing Fixed Signal Aggregator...")
    
    async with FixedSignalAggregator() as agg:
        consensus = await agg.aggregate_all_signals()
        
        print(f"\nActive systems: {agg.get_active_systems_count()}")
        print(f"Consensus signals: {len(consensus)}")
        
        if consensus:
            print("\nTop signals:")
            for symbol, sig in sorted(consensus.items(), 
                                     key=lambda x: x[1].consensus_score, 
                                     reverse=True)[:5]:
                print(f"  {symbol}: {sig.direction.value} "
                      f"(consensus: {sig.consensus_score:.2f}, "
                      f"systems: {len(sig.agreeing_systems)})")
        
        agg.export_consensus()


if __name__ == '__main__':
    asyncio.run(main())
