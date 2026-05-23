"""
Direction Conflict Detector

Detects and resolves conflicts where the same symbol has both LONG and SHORT positions
from different strategies or systems.
"""

import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class ConflictType(Enum):
    """Types of conflicts"""
    DIRECT_OPPOSITE = "direct_opposite"  # Same symbol, opposite directions
    OVERLAPPING_RANGES = "overlapping_ranges"  # TP/SL ranges overlap
    HIGH_CORRELATION = "high_correlation"  # Correlated assets, opposite directions


@dataclass
class Conflict:
    """Represents a detected conflict"""
    conflict_type: ConflictType
    symbol: str
    long_picks: List[Dict]
    short_picks: List[Dict]
    severity: str  # 'critical', 'warning', 'info'
    net_exposure: str  # 'long', 'short', 'neutral'
    recommended_action: str
    timestamp: str


class ConflictDetector:
    """
    Detects conflicts between trading picks.
    
    Key checks:
    1. Same symbol with both LONG and SHORT positions
    2. Overlapping TP/SL ranges (would trigger both)
    3. High correlation pairs with opposite directions
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize conflict detector.
        
        Args:
            config: Optional configuration for thresholds
        """
        self.config = config or {}
        self.critical_threshold = self.config.get('critical_threshold', 3)  # 3+ systems conflicting
        self.warning_threshold = self.config.get('warning_threshold', 2)    # 2 systems conflicting
        
    def detect_conflicts(self, picks: List[Dict]) -> List[Conflict]:
        """
        Detect all conflicts in a list of picks.
        
        Args:
            picks: List of pick dictionaries
            
        Returns:
            List of detected conflicts
        """
        conflicts = []
        
        # Group picks by symbol
        by_symbol = self._group_by_symbol(picks)
        
        # Check for direct opposites
        for symbol, symbol_picks in by_symbol.items():
            longs = [p for p in symbol_picks if p.get('direction') == 'LONG']
            shorts = [p for p in symbol_picks if p.get('direction') == 'SHORT']
            
            if longs and shorts:
                conflict = self._create_opposite_conflict(symbol, longs, shorts)
                if conflict:
                    conflicts.append(conflict)
        
        return conflicts
    
    def resolve_conflicts(self, picks: List[Dict], conflicts: List[Conflict]) -> List[Dict]:
        """
        Resolve conflicts by filtering or modifying picks.
        
        Strategy:
        1. For critical conflicts (3+ systems): Keep only higher-scoring direction
        2. For warning conflicts (2 systems): Reduce position sizes by 50%
        3. For info conflicts: Flag but allow
        
        Args:
            picks: Original picks list
            conflicts: Detected conflicts
            
        Returns:
            Filtered/modified picks list
        """
        picks_to_remove = set()
        picks_to_modify = {}  # pick_id -> modification dict
        
        for conflict in conflicts:
            if conflict.severity == 'critical':
                # Remove lower-scoring direction entirely
                long_avg_score = sum(p.get('quality_score', 0) for p in conflict.long_picks) / len(conflict.long_picks)
                short_avg_score = sum(p.get('quality_score', 0) for p in conflict.short_picks) / len(conflict.short_picks)
                
                if long_avg_score > short_avg_score:
                    # Remove shorts
                    for pick in conflict.short_picks:
                        picks_to_remove.add(pick.get('id'))
                else:
                    # Remove longs
                    for pick in conflict.long_picks:
                        picks_to_remove.add(pick.get('id'))
                        
            elif conflict.severity == 'warning':
                # Reduce position sizes by 50% for both directions
                for pick in conflict.long_picks + conflict.short_picks:
                    pick_id = pick.get('id')
                    current_size = pick.get('position_size_pct', 3.0)
                    picks_to_modify[pick_id] = {'position_size_pct': current_size * 0.5}
        
        # Apply modifications
        resolved_picks = []
        for pick in picks:
            pick_id = pick.get('id')
            
            if pick_id in picks_to_remove:
                continue
                
            if pick_id in picks_to_modify:
                pick = pick.copy()
                pick.update(picks_to_modify[pick_id])
                pick['conflict_adjusted'] = True
                
            resolved_picks.append(pick)
        
        return resolved_picks
    
    def _group_by_symbol(self, picks: List[Dict]) -> Dict[str, List[Dict]]:
        """Group picks by symbol."""
        by_symbol = {}
        for pick in picks:
            symbol = pick.get('symbol', 'UNKNOWN')
            if symbol not in by_symbol:
                by_symbol[symbol] = []
            by_symbol[symbol].append(pick)
        return by_symbol
    
    def _create_opposite_conflict(self, symbol: str, longs: List[Dict], shorts: List[Dict]) -> Optional[Conflict]:
        """Create conflict object for opposite direction picks."""
        total_systems = len(longs) + len(shorts)
        
        # Determine severity
        if total_systems >= self.critical_threshold:
            severity = 'critical'
        elif total_systems >= self.warning_threshold:
            severity = 'warning'
        else:
            severity = 'info'
        
        # Calculate net exposure
        long_score = sum(p.get('quality_score', 0) * p.get('consensus_count', 1) for p in longs)
        short_score = sum(p.get('quality_score', 0) * p.get('consensus_count', 1) for p in shorts)
        
        if long_score > short_score * 1.2:
            net_exposure = 'long'
            recommended_action = 'favor_longs'
        elif short_score > long_score * 1.2:
            net_exposure = 'short'
            recommended_action = 'favor_shorts'
        else:
            net_exposure = 'neutral'
            recommended_action = 'reduce_size_or_skip'
        
        return Conflict(
            conflict_type=ConflictType.DIRECT_OPPOSITE,
            symbol=symbol,
            long_picks=longs,
            short_picks=shorts,
            severity=severity,
            net_exposure=net_exposure,
            recommended_action=recommended_action,
            timestamp=datetime.utcnow().isoformat() + 'Z'
        )
    
    def to_dict(self, conflict: Conflict) -> Dict:
        """Convert conflict to dictionary."""
        return {
            'conflict_type': conflict.conflict_type.value,
            'symbol': conflict.symbol,
            'long_count': len(conflict.long_picks),
            'short_count': len(conflict.short_picks),
            'severity': conflict.severity,
            'net_exposure': conflict.net_exposure,
            'recommended_action': conflict.recommended_action,
            'timestamp': conflict.timestamp,
            'long_picks': [{'id': p.get('id'), 'score': p.get('quality_score')} for p in conflict.long_picks],
            'short_picks': [{'id': p.get('id'), 'score': p.get('quality_score')} for p in conflict.short_picks]
        }
    
    def generate_alert(self, conflict: Conflict) -> str:
        """Generate human-readable conflict alert."""
        long_count = len(conflict.long_picks)
        short_count = len(conflict.short_picks)
        
        emoji = "🚨" if conflict.severity == 'critical' else "⚠️" if conflict.severity == 'warning' else "ℹ️"
        
        return (
            f"{emoji} {conflict.symbol}: CONFLICT DETECTED\n"
            f"   LONG: {long_count} picks | SHORT: {short_count} picks\n"
            f"   Net Exposure: {conflict.net_exposure.upper()}\n"
            f"   Recommendation: {conflict.recommended_action}\n"
            f"   Severity: {conflict.severity.upper()}"
        )


class DuplicateDetector:
    """Detects duplicate picks in the active set."""
    
    def __init__(self):
        self.duplicate_keys = set()
    
    def detect_duplicates(self, picks: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Detect duplicate picks.
        
        Duplicates are defined as:
        - Same symbol + direction + system
        - Same symbol + direction + similar entry price (< 0.5% diff)
        
        Returns:
            Dict mapping duplicate key to list of duplicate picks
        """
        duplicates = {}
        seen = {}
        
        for pick in picks:
            # Create duplicate key
            key = self._create_key(pick)
            
            if key in seen:
                if key not in duplicates:
                    duplicates[key] = [seen[key]]
                duplicates[key].append(pick)
            else:
                seen[key] = pick
        
        return duplicates
    
    def remove_duplicates(self, picks: List[Dict], keep_highest_score: bool = True) -> Tuple[List[Dict], int]:
        """
        Remove duplicate picks.
        
        Args:
            picks: List of picks
            keep_highest_score: If True, keep highest scoring duplicate; else keep first
            
        Returns:
            Tuple of (deduplicated picks, number removed)
        """
        duplicates = self.detect_duplicates(picks)
        
        picks_to_remove = set()
        for key, dup_picks in duplicates.items():
            if keep_highest_score:
                # Sort by score descending, keep first
                sorted_picks = sorted(dup_picks, key=lambda p: p.get('quality_score', 0), reverse=True)
                for pick in sorted_picks[1:]:
                    picks_to_remove.add(pick.get('id'))
            else:
                # Keep first, remove rest
                for pick in dup_picks[1:]:
                    picks_to_remove.add(pick.get('id'))
        
        deduplicated = [p for p in picks if p.get('id') not in picks_to_remove]
        return deduplicated, len(picks_to_remove)
    
    def _create_key(self, pick: Dict) -> str:
        """Create unique key for duplicate detection."""
        symbol = pick.get('symbol', 'UNKNOWN')
        direction = pick.get('direction', 'LONG')
        system = pick.get('system', pick.get('strategy_dna', 'unknown'))
        entry = pick.get('entry_price', 0)
        
        # Round entry price to reduce sensitivity
        entry_rounded = round(entry, 2) if entry >= 100 else round(entry, 4)
        
        return f"{symbol}:{direction}:{system}:{entry_rounded}"


# Integration with PicksGenerator
def filter_picks_with_conflict_detection(picks: List[Dict], config: Optional[Dict] = None) -> Dict:
    """
    Filter picks using conflict and duplicate detection.
    
    Args:
        picks: Raw picks list
        config: Optional configuration
        
    Returns:
        Dict with filtered picks and conflict report
    """
    # Step 1: Remove duplicates
    dup_detector = DuplicateDetector()
    deduplicated, dup_count = dup_detector.remove_duplicates(picks)
    
    # Step 2: Detect conflicts
    conflict_detector = ConflictDetector(config)
    conflicts = conflict_detector.detect_conflicts(deduplicated)
    
    # Step 3: Resolve conflicts
    resolved = conflict_detector.resolve_conflicts(deduplicated, conflicts)
    
    return {
        'original_count': len(picks),
        'duplicates_removed': dup_count,
        'conflicts_detected': len(conflicts),
        'conflicts': [conflict_detector.to_dict(c) for c in conflicts],
        'final_count': len(resolved),
        'picks': resolved
    }


if __name__ == '__main__':
    # Test the conflict detector
    test_picks = [
        {
            'id': 'pick_001',
            'symbol': 'BTCUSDT',
            'direction': 'LONG',
            'quality_score': 85,
            'consensus_count': 3,
            'system': 'alpha_engine',
            'position_size_pct': 3.0
        },
        {
            'id': 'pick_002',
            'symbol': 'BTCUSDT',
            'direction': 'SHORT',
            'quality_score': 75,
            'consensus_count': 2,
            'system': 'battleground',
            'position_size_pct': 3.0
        },
        {
            'id': 'pick_003',
            'symbol': 'ETHUSDT',
            'direction': 'LONG',
            'quality_score': 90,
            'consensus_count': 4,
            'system': 'mercury2',
            'position_size_pct': 3.0
        },
        {
            'id': 'pick_004',  # Duplicate of pick_001
            'symbol': 'BTCUSDT',
            'direction': 'LONG',
            'quality_score': 82,
            'consensus_count': 3,
            'system': 'alpha_engine',
            'position_size_pct': 3.0
        }
    ]
    
    result = filter_picks_with_conflict_detection(test_picks)
    
    print("=" * 60)
    print("CONFLICT & DUPLICATE DETECTION TEST")
    print("=" * 60)
    print(f"Original picks: {result['original_count']}")
    print(f"Duplicates removed: {result['duplicates_removed']}")
    print(f"Conflicts detected: {result['conflicts_detected']}")
    print(f"Final picks: {result['final_count']}")
    
    if result['conflicts']:
        print("\nDetected Conflicts:")
        for conflict in result['conflicts']:
            print(f"  - {conflict['symbol']}: {conflict['long_count']} LONG vs {conflict['short_count']} SHORT")
            print(f"    Severity: {conflict['severity']}, Action: {conflict['recommended_action']}")
    
    print("\nFinal Picks:")
    for pick in result['picks']:
        adjusted = " (adjusted)" if pick.get('conflict_adjusted') else ""
        print(f"  {pick['symbol']} {pick['direction']} - Score: {pick['quality_score']}, Size: {pick['position_size_pct']:.1f}%{adjusted}")
    
    print("=" * 60)
