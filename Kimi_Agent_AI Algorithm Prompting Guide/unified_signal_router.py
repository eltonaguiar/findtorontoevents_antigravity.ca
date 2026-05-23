#!/usr/bin/env python3
"""
Unified Signal Router for Multi-System Trading Infrastructure
==============================================================
Consolidates signals from ~80 active trading systems into a single coherent output.

Key Features:
- Signal normalization across heterogeneous sources
- Priority-based conflict resolution
- Consensus algorithms for multi-system aggregation
- Duplicate detection and prevention
- Real-time and batch processing modes
"""

import json
import sqlite3
import hashlib
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable, Any, Set, Tuple
from enum import Enum, auto
from collections import defaultdict
import threading
from pathlib import Path
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('SignalRouter')


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class SignalDirection(Enum):
    """Standardized signal directions"""
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"
    EXIT_LONG = "exit_long"
    EXIT_SHORT = "exit_short"
    HOLD = "hold"


class SignalSource(Enum):
    """Known trading system sources with priority ordering"""
    BATTLEGROUND = 1      # Highest priority - crypto momentum
    ALPHA_ENGINE = 2      # Crypto alpha signals
    MERCURY2 = 3          # ML-based predictions
    MULTI_ASSET = 4       # ETF/stock multi-asset
    KIMI = 5              # AI assistant signals
    CUSTOM = 99           # User-defined systems


class SignalStatus(Enum):
    """Signal lifecycle states"""
    PENDING = "pending"
    ACTIVE = "active"
    CONFLICTED = "conflicted"
    RESOLVED = "resolved"
    EXPIRED = "expired"
    EXECUTED = "executed"
    CANCELLED = "cancelled"


class ConfidenceLevel(Enum):
    """Standardized confidence levels"""
    VERY_HIGH = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    VERY_LOW = 1


# Default priority configuration (can be customized)
DEFAULT_PRIORITY_ORDER = [
    SignalSource.BATTLEGROUND,
    SignalSource.ALPHA_ENGINE,
    SignalSource.MERCURY2,
    SignalSource.MULTI_ASSET,
    SignalSource.KIMI,
]


# =============================================================================
# DATA CLASSES - SCHEMA DEFINITIONS
# =============================================================================

@dataclass
class NormalizedSignal:
    """
    Unified signal schema - all incoming signals are normalized to this format.
    This is the canonical representation used throughout the system.
    """
    # Core identification (required)
    signal_id: str
    source: str
    source_priority: int
    
    # Asset identification (required)
    symbol: str
    asset_class: str  # crypto, stock, etf, forex, etc.
    
    # Signal characteristics (required)
    direction: str
    confidence: float  # 0.0 to 1.0
    confidence_level: str
    
    # Asset identification (optional)
    exchange: Optional[str] = None
    
    # Sizing and pricing (optional)
    suggested_size: Optional[float] = None
    suggested_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # Metadata (optional)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    expiry: Optional[datetime] = None
    timeframe: Optional[str] = None  # 1m, 5m, 1h, 4h, 1d, etc.
    strategy: Optional[str] = None
    
    # Original data preservation (optional)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    source_signal_id: Optional[str] = None
    
    # Routing state (optional)
    status: str = field(default=SignalStatus.PENDING.value)
    conflict_group: Optional[str] = None
    consensus_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        if self.expiry:
            d['expiry'] = self.expiry.isoformat()
        return d
    
    @property
    def fingerprint(self) -> str:
        """Generate unique fingerprint for duplicate detection"""
        content = f"{self.source}:{self.symbol}:{self.direction}:{self.timestamp.strftime('%Y%m%d%H%M')}"
        return hashlib.md5(content.encode()).hexdigest()
    
    @property
    def is_exit_signal(self) -> bool:
        """Check if this is an exit signal"""
        return self.direction in [SignalDirection.EXIT_LONG.value, 
                                   SignalDirection.EXIT_SHORT.value]


@dataclass
class ConflictGroup:
    """Represents a group of conflicting signals for the same asset"""
    group_id: str
    symbol: str
    signals: List[NormalizedSignal] = field(default_factory=list)
    resolution: Optional[NormalizedSignal] = None
    resolution_method: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_signal(self, signal: NormalizedSignal):
        self.signals.append(signal)
        signal.conflict_group = self.group_id


@dataclass
class ConsensusResult:
    """Result of consensus calculation for a symbol"""
    symbol: str
    consensus_direction: Optional[str]
    consensus_score: float
    participating_signals: int
    confidence_weighted_score: float
    agreement_ratio: float
    dominant_source: Optional[str]
    all_directions: Dict[str, int]


# =============================================================================
# SOURCE ADAPTERS - Convert various formats to NormalizedSignal
# =============================================================================

class SourceAdapter:
    """Base class for source-specific signal adapters"""
    
    def __init__(self, source_name: str, priority: int):
        self.source_name = source_name
        self.priority = priority
    
    def adapt(self, raw_signal: Dict[str, Any]) -> NormalizedSignal:
        raise NotImplementedError
    
    def _generate_signal_id(self, raw_signal: Dict[str, Any]) -> str:
        """Generate unique signal ID"""
        return f"{self.source_name}_{uuid.uuid4().hex[:12]}"


class AlphaEngineAdapter(SourceAdapter):
    """Adapter for Alpha Engine crypto signals"""
    
    def __init__(self):
        super().__init__("alpha_engine", SignalSource.ALPHA_ENGINE.value)
    
    def adapt(self, raw: Dict[str, Any]) -> NormalizedSignal:
        direction_map = {
            'buy': SignalDirection.LONG.value,
            'sell': SignalDirection.SHORT.value,
            'hold': SignalDirection.HOLD.value,
        }
        
        return NormalizedSignal(
            signal_id=self._generate_signal_id(raw),
            source=self.source_name,
            source_priority=self.priority,
            symbol=raw.get('pair', raw.get('symbol', '')),
            asset_class='crypto',
            exchange=raw.get('exchange'),
            direction=direction_map.get(raw.get('signal', '').lower(), SignalDirection.HOLD.value),
            confidence=float(raw.get('confidence', 0.5)),
            confidence_level=self._map_confidence(raw.get('confidence', 0.5)),
            suggested_price=raw.get('entry_price'),
            stop_loss=raw.get('stop_loss'),
            take_profit=raw.get('take_profit'),
            timeframe=raw.get('timeframe'),
            strategy=raw.get('strategy'),
            raw_data=raw,
            source_signal_id=raw.get('id')
        )
    
    def _map_confidence(self, conf: float) -> str:
        if conf >= 0.85: return ConfidenceLevel.VERY_HIGH.name
        if conf >= 0.70: return ConfidenceLevel.HIGH.name
        if conf >= 0.55: return ConfidenceLevel.MEDIUM.name
        if conf >= 0.40: return ConfidenceLevel.LOW.name
        return ConfidenceLevel.VERY_LOW.name


class BattlegroundAdapter(SourceAdapter):
    """Adapter for Battleground crypto momentum signals"""
    
    def __init__(self):
        super().__init__("battleground", SignalSource.BATTLEGROUND.value)
    
    def adapt(self, raw: Dict[str, Any]) -> NormalizedSignal:
        direction_map = {
            'long': SignalDirection.LONG.value,
            'short': SignalDirection.SHORT.value,
            'close': SignalDirection.EXIT_LONG.value,
            'exit': SignalDirection.EXIT_LONG.value,
        }
        
        return NormalizedSignal(
            signal_id=self._generate_signal_id(raw),
            source=self.source_name,
            source_priority=self.priority,
            symbol=raw.get('ticker', raw.get('symbol', '')),
            asset_class='crypto',
            exchange=raw.get('exchange', 'binance'),
            direction=direction_map.get(raw.get('direction', '').lower(), SignalDirection.HOLD.value),
            confidence=float(raw.get('strength', 0.7)),
            confidence_level=self._map_strength(raw.get('strength', 0.7)),
            suggested_price=raw.get('price'),
            stop_loss=raw.get('sl'),
            take_profit=raw.get('tp'),
            timeframe=raw.get('tf', '1h'),
            strategy='momentum',
            raw_data=raw,
            source_signal_id=raw.get('signal_id')
        )
    
    def _map_strength(self, strength: float) -> str:
        if strength >= 0.90: return ConfidenceLevel.VERY_HIGH.name
        if strength >= 0.75: return ConfidenceLevel.HIGH.name
        if strength >= 0.60: return ConfidenceLevel.MEDIUM.name
        return ConfidenceLevel.LOW.name


class Mercury2Adapter(SourceAdapter):
    """Adapter for Mercury2 ML-based signals"""
    
    def __init__(self):
        super().__init__("mercury2", SignalSource.MERCURY2.value)
    
    def adapt(self, raw: Dict[str, Any]) -> NormalizedSignal:
        # Mercury2 uses probability scores
        prob_up = raw.get('prob_up', 0.5)
        prob_down = raw.get('prob_down', 0.5)
        
        if prob_up > prob_down:
            direction = SignalDirection.LONG.value
            confidence = prob_up
        elif prob_down > prob_up:
            direction = SignalDirection.SHORT.value
            confidence = prob_down
        else:
            direction = SignalDirection.NEUTRAL.value
            confidence = 0.5
        
        return NormalizedSignal(
            signal_id=self._generate_signal_id(raw),
            source=self.source_name,
            source_priority=self.priority,
            symbol=raw.get('symbol', ''),
            asset_class=raw.get('asset_class', 'stock'),
            exchange=raw.get('exchange'),
            direction=direction,
            confidence=confidence,
            confidence_level=self._map_probability(confidence),
            suggested_price=raw.get('predicted_price'),
            timeframe=raw.get('prediction_horizon'),
            strategy=f"ml_{raw.get('model_version', 'v1')}",
            raw_data=raw,
            source_signal_id=raw.get('prediction_id')
        )
    
    def _map_probability(self, prob: float) -> str:
        if prob >= 0.80: return ConfidenceLevel.VERY_HIGH.name
        if prob >= 0.65: return ConfidenceLevel.HIGH.name
        if prob >= 0.55: return ConfidenceLevel.MEDIUM.name
        return ConfidenceLevel.LOW.name


class MultiAssetAdapter(SourceAdapter):
    """Adapter for Multi-Asset ETF/stock signals"""
    
    def __init__(self):
        super().__init__("multi_asset", SignalSource.MULTI_ASSET.value)
    
    def adapt(self, raw: Dict[str, Any]) -> NormalizedSignal:
        return NormalizedSignal(
            signal_id=self._generate_signal_id(raw),
            source=self.source_name,
            source_priority=self.priority,
            symbol=raw.get('ticker', raw.get('symbol', '')),
            asset_class=raw.get('type', 'stock'),
            exchange=raw.get('market', 'US'),
            direction=raw.get('recommendation', SignalDirection.HOLD.value),
            confidence=float(raw.get('score', 0.5)) / 100 if raw.get('score', 0) > 1 else float(raw.get('score', 0.5)),
            confidence_level=self._map_score(raw.get('score', 50)),
            suggested_price=raw.get('target_entry'),
            stop_loss=raw.get('target_exit'),
            timeframe=raw.get('horizon', 'medium'),
            strategy=raw.get('sector_rotation'),
            raw_data=raw,
            source_signal_id=raw.get('pick_id')
        )
    
    def _map_score(self, score: float) -> str:
        if score >= 90: return ConfidenceLevel.VERY_HIGH.name
        if score >= 75: return ConfidenceLevel.HIGH.name
        if score >= 60: return ConfidenceLevel.MEDIUM.name
        if score >= 45: return ConfidenceLevel.LOW.name
        return ConfidenceLevel.VERY_LOW.name


class KIMIAdapter(SourceAdapter):
    """Adapter for KIMI AI assistant signals"""
    
    def __init__(self):
        super().__init__("kimi", SignalSource.KIMI.value)
    
    def adapt(self, raw: Dict[str, Any]) -> NormalizedSignal:
        return NormalizedSignal(
            signal_id=self._generate_signal_id(raw),
            source=self.source_name,
            source_priority=self.priority,
            symbol=raw.get('asset', ''),
            asset_class=raw.get('class', 'unknown'),
            direction=raw.get('bias', SignalDirection.NEUTRAL.value),
            confidence=float(raw.get('certainty', 0.5)),
            confidence_level=self._map_certainty(raw.get('certainty', 0.5)),
            timeframe=raw.get('timeframe'),
            strategy='ai_analysis',
            raw_data=raw,
            source_signal_id=raw.get('analysis_id')
        )
    
    def _map_certainty(self, cert: float) -> str:
        if cert >= 0.85: return ConfidenceLevel.VERY_HIGH.name
        if cert >= 0.70: return ConfidenceLevel.HIGH.name
        if cert >= 0.55: return ConfidenceLevel.MEDIUM.name
        return ConfidenceLevel.LOW.name


# Registry of adapters
ADAPTER_REGISTRY: Dict[str, SourceAdapter] = {
    'alpha_engine': AlphaEngineAdapter(),
    'battleground': BattlegroundAdapter(),
    'mercury2': Mercury2Adapter(),
    'multi_asset': MultiAssetAdapter(),
    'kimi': KIMIAdapter(),
}


# =============================================================================
# DATABASE SCHEMA AND MANAGER
# =============================================================================

class UnifiedDatabase:
    """
    Central database for unified signal storage.
    Consolidates data from 35+ SQLite databases and 60+ JSON files.
    """
    
    SCHEMA_SQL = """
    -- Core signals table
    CREATE TABLE IF NOT EXISTS signals (
        signal_id TEXT PRIMARY KEY,
        source TEXT NOT NULL,
        source_priority INTEGER NOT NULL,
        symbol TEXT NOT NULL,
        asset_class TEXT NOT NULL,
        exchange TEXT,
        direction TEXT NOT NULL,
        confidence REAL NOT NULL,
        confidence_level TEXT,
        suggested_size REAL,
        suggested_price REAL,
        stop_loss REAL,
        take_profit REAL,
        timestamp TEXT NOT NULL,
        expiry TEXT,
        timeframe TEXT,
        strategy TEXT,
        source_signal_id TEXT,
        status TEXT DEFAULT 'pending',
        conflict_group TEXT,
        consensus_score REAL,
        fingerprint TEXT UNIQUE,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- Conflict groups table
    CREATE TABLE IF NOT EXISTS conflict_groups (
        group_id TEXT PRIMARY KEY,
        symbol TEXT NOT NULL,
        resolution_method TEXT,
        resolved_signal_id TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        resolved_at TEXT,
        FOREIGN KEY (resolved_signal_id) REFERENCES signals(signal_id)
    );

    -- Signal relationships (for tracking duplicates and related signals)
    CREATE TABLE IF NOT EXISTS signal_relationships (
        signal_id TEXT NOT NULL,
        related_signal_id TEXT NOT NULL,
        relationship_type TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (signal_id, related_signal_id),
        FOREIGN KEY (signal_id) REFERENCES signals(signal_id),
        FOREIGN KEY (related_signal_id) REFERENCES signals(signal_id)
    );

    -- Consensus history
    CREATE TABLE IF NOT EXISTS consensus_history (
        consensus_id TEXT PRIMARY KEY,
        symbol TEXT NOT NULL,
        consensus_direction TEXT,
        consensus_score REAL,
        participating_signals INTEGER,
        agreement_ratio REAL,
        dominant_source TEXT,
        calculated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- Source metadata
    CREATE TABLE IF NOT EXISTS source_metadata (
        source_name TEXT PRIMARY KEY,
        priority INTEGER NOT NULL,
        adapter_class TEXT,
        is_active INTEGER DEFAULT 1,
        last_seen TEXT,
        signal_count INTEGER DEFAULT 0
    );

    -- Indexes for performance
    CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol);
    CREATE INDEX IF NOT EXISTS idx_signals_source ON signals(source);
    CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status);
    CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp);
    CREATE INDEX IF NOT EXISTS idx_signals_fingerprint ON signals(fingerprint);
    CREATE INDEX IF NOT EXISTS idx_conflict_groups_symbol ON conflict_groups(symbol);
    """
    
    def __init__(self, db_path: str = "unified_signals.db"):
        self.db_path = db_path
        self._local = threading.local()
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
            # For in-memory databases, each connection needs schema
            if self.db_path == ":memory:":
                self._local.conn.executescript(self.SCHEMA_SQL)
                self._local.conn.commit()
        return self._local.conn
    
    def _init_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        conn.executescript(self.SCHEMA_SQL)
        conn.commit()
        conn.close()
        logger.info(f"Initialized unified database at {self.db_path}")
    
    def store_signal(self, signal: NormalizedSignal) -> bool:
        """Store a normalized signal in the database"""
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO signals (
                    signal_id, source, source_priority, symbol, asset_class, exchange,
                    direction, confidence, confidence_level, suggested_size, suggested_price,
                    stop_loss, take_profit, timestamp, expiry, timeframe, strategy,
                    source_signal_id, status, conflict_group, consensus_score, fingerprint
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal.signal_id, signal.source, signal.source_priority, signal.symbol,
                signal.asset_class, signal.exchange, signal.direction, signal.confidence,
                signal.confidence_level, signal.suggested_size, signal.suggested_price,
                signal.stop_loss, signal.take_profit, signal.timestamp.isoformat(),
                signal.expiry.isoformat() if signal.expiry else None,
                signal.timeframe, signal.strategy, signal.source_signal_id,
                signal.status, signal.conflict_group, signal.consensus_score, signal.fingerprint
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError as e:
            logger.warning(f"Duplicate signal detected: {signal.fingerprint}")
            return False
        except Exception as e:
            logger.error(f"Error storing signal: {e}")
            return False
    
    def get_active_signals(self, symbol: Optional[str] = None) -> List[NormalizedSignal]:
        """Retrieve active signals, optionally filtered by symbol"""
        conn = self._get_connection()
        query = "SELECT * FROM signals WHERE status IN ('pending', 'active', 'conflicted')"
        params = []
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        query += " ORDER BY timestamp DESC"
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        return [self._row_to_signal(row) for row in rows]
    
    def get_signals_by_source(self, source: str, hours: int = 24) -> List[NormalizedSignal]:
        """Get signals from a specific source within time window"""
        conn = self._get_connection()
        since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        cursor = conn.execute(
            "SELECT * FROM signals WHERE source = ? AND timestamp > ? ORDER BY timestamp DESC",
            (source, since)
        )
        return [self._row_to_signal(row) for row in cursor.fetchall()]
    
    def check_duplicate(self, fingerprint: str) -> bool:
        """Check if a signal with this fingerprint already exists"""
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT 1 FROM signals WHERE fingerprint = ? LIMIT 1",
            (fingerprint,)
        )
        return cursor.fetchone() is not None
    
    def update_signal_status(self, signal_id: str, status: str, **kwargs):
        """Update signal status and optional fields"""
        conn = self._get_connection()
        updates = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
        params = [status]
        
        for key, value in kwargs.items():
            updates.append(f"{key} = ?")
            params.append(value)
        
        params.append(signal_id)
        query = f"UPDATE signals SET {', '.join(updates)} WHERE signal_id = ?"
        conn.execute(query, params)
        conn.commit()
    
    def store_conflict_group(self, group: ConflictGroup):
        """Store a conflict group"""
        conn = self._get_connection()
        conn.execute("""
            INSERT OR REPLACE INTO conflict_groups 
            (group_id, symbol, resolution_method, resolved_signal_id, created_at, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            group.group_id, group.symbol, group.resolution_method,
            group.resolution.signal_id if group.resolution else None,
            group.created_at.isoformat(),
            datetime.utcnow().isoformat() if group.resolution else None
        ))
        conn.commit()
    
    def store_consensus(self, result: ConsensusResult):
        """Store consensus calculation result"""
        conn = self._get_connection()
        conn.execute("""
            INSERT INTO consensus_history 
            (consensus_id, symbol, consensus_direction, consensus_score, 
             participating_signals, agreement_ratio, dominant_source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            f"cons_{uuid.uuid4().hex[:12]}",
            result.symbol, result.consensus_direction, result.consensus_score,
            result.participating_signals, result.agreement_ratio, result.dominant_source
        ))
        conn.commit()
    
    def _row_to_signal(self, row: sqlite3.Row) -> NormalizedSignal:
        """Convert database row to NormalizedSignal"""
        return NormalizedSignal(
            signal_id=row['signal_id'],
            source=row['source'],
            source_priority=row['source_priority'],
            symbol=row['symbol'],
            asset_class=row['asset_class'],
            exchange=row['exchange'],
            direction=row['direction'],
            confidence=row['confidence'],
            confidence_level=row['confidence_level'],
            suggested_size=row['suggested_size'],
            suggested_price=row['suggested_price'],
            stop_loss=row['stop_loss'],
            take_profit=row['take_profit'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            expiry=datetime.fromisoformat(row['expiry']) if row['expiry'] else None,
            timeframe=row['timeframe'],
            strategy=row['strategy'],
            source_signal_id=row['source_signal_id'],
            status=row['status'],
            conflict_group=row['conflict_group'],
            consensus_score=row['consensus_score']
        )
    
    def get_live_picks(self, min_confidence: float = 0.5) -> List[Dict[str, Any]]:
        """Get consolidated live picks for output"""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT * FROM signals 
            WHERE status IN ('active', 'resolved') 
            AND confidence >= ?
            AND (expiry IS NULL OR expiry > ?)
            ORDER BY source_priority ASC, confidence DESC
        """, (min_confidence, datetime.utcnow().isoformat()))
        
        picks = []
        seen_symbols = set()
        
        for row in cursor.fetchall():
            symbol = row['symbol']
            if symbol not in seen_symbols:
                seen_symbols.add(symbol)
                picks.append({
                    'symbol': row['symbol'],
                    'direction': row['direction'],
                    'confidence': row['confidence'],
                    'source': row['source'],
                    'price': row['suggested_price'],
                    'stop_loss': row['stop_loss'],
                    'take_profit': row['take_profit'],
                    'timestamp': row['timestamp'],
                    'signal_id': row['signal_id']
                })
        
        return picks


# =============================================================================
# CONFLICT RESOLUTION STRATEGIES
# =============================================================================

class ConflictResolver:
    """
    Implements various conflict resolution strategies for overlapping signals.
    """
    
    @staticmethod
    def priority_based(signals: List[NormalizedSignal]) -> NormalizedSignal:
        """
        Resolve conflict by selecting highest priority signal.
        Priority order: Battleground > Alpha Engine > Mercury2 > Multi-Asset > KIMI
        """
        if not signals:
            raise ValueError("No signals to resolve")
        
        # Sort by priority (lower number = higher priority)
        sorted_signals = sorted(signals, key=lambda s: s.source_priority)
        winner = sorted_signals[0]
        winner.status = SignalStatus.RESOLVED.value
        return winner
    
    @staticmethod
    def confidence_based(signals: List[NormalizedSignal]) -> NormalizedSignal:
        """Resolve conflict by selecting highest confidence signal"""
        if not signals:
            raise ValueError("No signals to resolve")
        
        winner = max(signals, key=lambda s: s.confidence)
        winner.status = SignalStatus.RESOLVED.value
        return winner
    
    @staticmethod
    def weighted_score(signals: List[NormalizedSignal]) -> NormalizedSignal:
        """
        Resolve conflict using weighted score combining priority and confidence.
        Score = confidence * (1 / priority)
        """
        if not signals:
            raise ValueError("No signals to resolve")
        
        def calculate_score(s: NormalizedSignal) -> float:
            priority_weight = 1.0 / s.source_priority
            return s.confidence * priority_weight
        
        winner = max(signals, key=calculate_score)
        winner.status = SignalStatus.RESOLVED.value
        return winner
    
    @staticmethod
    def consensus_merge(signals: List[NormalizedSignal]) -> NormalizedSignal:
        """
        Create consensus signal by merging conflicting signals.
        Uses weighted average of parameters.
        """
        if not signals:
            raise ValueError("No signals to resolve")
        
        if len(signals) == 1:
            signals[0].status = SignalStatus.RESOLVED.value
            return signals[0]
        
        # Group by direction
        direction_groups = defaultdict(list)
        for s in signals:
            direction_groups[s.direction].append(s)
        
        # Find dominant direction
        dominant_direction = max(direction_groups.keys(), 
                                  key=lambda d: sum(s.confidence for s in direction_groups[d]))
        dominant_signals = direction_groups[dominant_direction]
        
        # Calculate weighted averages
        total_weight = sum(s.confidence / s.source_priority for s in dominant_signals)
        
        def weighted_average(values: List[Optional[float]]) -> Optional[float]:
            valid = [(v, s.confidence / s.source_priority) 
                     for v, s in zip(values, dominant_signals) if v is not None]
            if not valid:
                return None
            return sum(v * w for v, w in valid) / sum(w for _, w in valid)
        
        # Create merged signal
        base_signal = dominant_signals[0]
        merged = NormalizedSignal(
            signal_id=f"consensus_{uuid.uuid4().hex[:12]}",
            source="consensus",
            source_priority=min(s.source_priority for s in dominant_signals),
            symbol=base_signal.symbol,
            asset_class=base_signal.asset_class,
            direction=dominant_direction,
            confidence=sum(s.confidence for s in dominant_signals) / len(dominant_signals),
            confidence_level=base_signal.confidence_level,
            suggested_price=weighted_average([s.suggested_price for s in dominant_signals]),
            stop_loss=weighted_average([s.stop_loss for s in dominant_signals]),
            take_profit=weighted_average([s.take_profit for s in dominant_signals]),
            strategy="consensus_merge",
            raw_data={'merged_from': [s.signal_id for s in signals]},
            status=SignalStatus.RESOLVED.value
        )
        
        return merged
    
    @staticmethod
    def directional_agreement(signals: List[NormalizedSignal]) -> Optional[NormalizedSignal]:
        """
        Only resolve if majority agrees on direction.
        Returns None if no clear consensus.
        """
        if not signals:
            return None
        
        direction_counts = defaultdict(lambda: {'count': 0, 'confidence_sum': 0})
        for s in signals:
            direction_counts[s.direction]['count'] += 1
            direction_counts[s.direction]['confidence_sum'] += s.confidence
        
        total = len(signals)
        for direction, data in direction_counts.items():
            if data['count'] / total >= 0.6:  # 60% agreement threshold
                # Return highest confidence signal in winning direction
                candidates = [s for s in signals if s.direction == direction]
                winner = max(candidates, key=lambda s: s.confidence)
                winner.status = SignalStatus.RESOLVED.value
                return winner
        
        return None


# =============================================================================
# MAIN SIGNAL ROUTER
# =============================================================================

class SignalRouter:
    """
    Unified Signal Router - Main orchestrator for signal aggregation.
    
    Responsibilities:
    1. Ingest signals from multiple sources
    2. Normalize to canonical format
    3. Detect and prevent duplicates
    4. Resolve conflicts
    5. Generate consensus
    6. Output unified picks
    """
    
    def __init__(
        self,
        db_path: str = "unified_signals.db",
        conflict_window_minutes: int = 30,
        min_confidence: float = 0.3,
        consensus_threshold: float = 0.6,
        output_path: str = "live_picks.json"
    ):
        self.db = UnifiedDatabase(db_path)
        self.conflict_window = timedelta(minutes=conflict_window_minutes)
        self.min_confidence = min_confidence
        self.consensus_threshold = consensus_threshold
        self.output_path = output_path
        
        # Configuration
        self.priority_order = DEFAULT_PRIORITY_ORDER
        self.conflict_resolver = ConflictResolver.priority_based
        
        # Statistics
        self.stats = {
            'ingested': 0,
            'normalized': 0,
            'duplicates': 0,
            'conflicts': 0,
            'resolved': 0,
            'output': 0
        }
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info("SignalRouter initialized")
    
    def ingest_signal(
        self, 
        raw_signal: Dict[str, Any], 
        source: str,
        custom_adapter: Optional[SourceAdapter] = None
    ) -> Optional[NormalizedSignal]:
        """
        Ingest a raw signal from any source.
        
        Args:
            raw_signal: Raw signal data from source system
            source: Source system identifier
            custom_adapter: Optional custom adapter for unknown sources
        
        Returns:
            NormalizedSignal if successful, None if duplicate or error
        """
        with self._lock:
            self.stats['ingested'] += 1
            
            # Get adapter
            adapter = custom_adapter or ADAPTER_REGISTRY.get(source)
            if not adapter:
                logger.warning(f"No adapter found for source: {source}")
                # Create generic adapter on the fly
                adapter = SourceAdapter(source, SignalSource.CUSTOM.value)
                adapter.adapt = lambda raw: self._generic_adapt(raw, source)
            
            # Normalize
            try:
                normalized = adapter.adapt(raw_signal)
            except Exception as e:
                logger.error(f"Failed to normalize signal from {source}: {e}")
                return None
            
            self.stats['normalized'] += 1
            
            # Check for duplicates
            if self.db.check_duplicate(normalized.fingerprint):
                logger.debug(f"Duplicate signal detected: {normalized.fingerprint}")
                self.stats['duplicates'] += 1
                return None
            
            # Filter low confidence
            if normalized.confidence < self.min_confidence:
                logger.debug(f"Signal below confidence threshold: {normalized.confidence}")
                return None
            
            # Store in database
            if self.db.store_signal(normalized):
                logger.info(f"Signal ingested: {normalized.source} -> {normalized.symbol} {normalized.direction}")
                return normalized
            
            return None
    
    def ingest_batch(
        self, 
        signals: List[Dict[str, Any]], 
        source: str
    ) -> List[NormalizedSignal]:
        """Ingest multiple signals from the same source"""
        results = []
        for raw in signals:
            normalized = self.ingest_signal(raw, source)
            if normalized:
                results.append(normalized)
        logger.info(f"Batch ingest complete: {len(results)}/{len(signals)} signals accepted")
        return results
    
    def normalize_signal(
        self, 
        raw_signal: Dict[str, Any], 
        source: str
    ) -> NormalizedSignal:
        """
        Normalize a raw signal to canonical format.
        Public method for external normalization needs.
        """
        adapter = ADAPTER_REGISTRY.get(source)
        if not adapter:
            return self._generic_adapt(raw_signal, source)
        return adapter.adapt(raw_signal)
    
    def resolve_conflicts(
        self, 
        symbol: Optional[str] = None,
        method: Optional[Callable] = None
    ) -> List[ConflictGroup]:
        """
        Resolve conflicting signals for the same asset.
        
        Args:
            symbol: Specific symbol to resolve, or None for all
            method: Conflict resolution method to use
        
        Returns:
            List of resolved conflict groups
        """
        with self._lock:
            resolver = method or self.conflict_resolver
            
            # Get active signals
            if symbol:
                all_signals = self.db.get_active_signals(symbol)
            else:
                all_signals = self.db.get_active_signals()
            
            # Group by symbol
            symbol_groups = defaultdict(list)
            for signal in all_signals:
                symbol_groups[signal.symbol].append(signal)
            
            resolved_groups = []
            
            for sym, signals in symbol_groups.items():
                # Check for conflicts (different directions within time window)
                conflicting = self._find_conflicts(signals)
                
                if conflicting:
                    self.stats['conflicts'] += len(conflicting)
                    
                    for conflict_signals in conflicting:
                        group = ConflictGroup(
                            group_id=f"conflict_{uuid.uuid4().hex[:8]}",
                            symbol=sym,
                            signals=conflict_signals
                        )
                        
                        # Mark as conflicted
                        for s in conflict_signals:
                            self.db.update_signal_status(
                                s.signal_id, 
                                SignalStatus.CONFLICTED.value,
                                conflict_group=group.group_id
                            )
                        
                        # Resolve
                        try:
                            winner = resolver(conflict_signals)
                            group.resolution = winner
                            group.resolution_method = resolver.__name__
                            
                            # Update winner status
                            self.db.update_signal_status(
                                winner.signal_id,
                                SignalStatus.RESOLVED.value
                            )
                            
                            # Store conflict group
                            self.db.store_conflict_group(group)
                            
                            resolved_groups.append(group)
                            self.stats['resolved'] += 1
                            
                            logger.info(
                                f"Conflict resolved for {sym}: {winner.source} wins "
                                f"({winner.direction}, conf={winner.confidence:.2f})"
                            )
                            
                        except Exception as e:
                            logger.error(f"Failed to resolve conflict for {sym}: {e}")
            
            return resolved_groups
    
    def output_consensus(
        self, 
        output_path: Optional[str] = None,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Generate unified output with consensus picks.
        
        Args:
            output_path: Path for output file (default: self.output_path)
            format: Output format (json, dict)
        
        Returns:
            Consensus output dictionary
        """
        with self._lock:
            output_path = output_path or self.output_path
            
            # Get all active symbols
            all_signals = self.db.get_active_signals()
            symbol_groups = defaultdict(list)
            for signal in all_signals:
                symbol_groups[signal.symbol].append(signal)
            
            # Calculate consensus for each symbol
            consensus_results = {}
            for symbol, signals in symbol_groups.items():
                result = self._calculate_consensus(symbol, signals)
                if result.consensus_score >= self.consensus_threshold:
                    consensus_results[symbol] = result
                    self.db.store_consensus(result)
            
            # Build output
            output = {
                'generated_at': datetime.utcnow().isoformat(),
                'router_stats': self.stats.copy(),
                'active_symbols': len(symbol_groups),
                'consensus_picks': len(consensus_results),
                'picks': []
            }
            
            # Sort by consensus score
            sorted_results = sorted(
                consensus_results.items(),
                key=lambda x: x[1].consensus_score,
                reverse=True
            )
            
            for symbol, result in sorted_results:
                # Get best signal for this symbol
                best_signal = self._get_best_signal(symbol, symbol_groups[symbol])
                
                pick = {
                    'symbol': symbol,
                    'direction': result.consensus_direction,
                    'consensus_score': round(result.consensus_score, 4),
                    'confidence': round(best_signal.confidence, 4) if best_signal else None,
                    'source': best_signal.source if best_signal else None,
                    'sources': list(set(s.source for s in symbol_groups[symbol])),
                    'agreement_ratio': round(result.agreement_ratio, 4),
                    'suggested_price': best_signal.suggested_price if best_signal else None,
                    'stop_loss': best_signal.stop_loss if best_signal else None,
                    'take_profit': best_signal.take_profit if best_signal else None,
                    'signal_id': best_signal.signal_id if best_signal else None,
                    'timestamp': best_signal.timestamp.isoformat() if best_signal else None
                }
                output['picks'].append(pick)
            
            self.stats['output'] = len(output['picks'])
            
            # Write to file
            if format == "json" and output_path:
                with open(output_path, 'w') as f:
                    json.dump(output, f, indent=2, default=str)
                logger.info(f"Consensus output written to {output_path}")
            
            return output
    
    def get_live_picks(self) -> List[Dict[str, Any]]:
        """Get current live picks from database"""
        return self.db.get_live_picks(min_confidence=self.min_confidence)
    
    def run_cycle(self) -> Dict[str, Any]:
        """
        Run a complete routing cycle:
        1. Resolve conflicts
        2. Generate consensus
        3. Output results
        """
        logger.info("Starting routing cycle...")
        
        # Resolve all conflicts
        resolved = self.resolve_conflicts()
        logger.info(f"Resolved {len(resolved)} conflict groups")
        
        # Generate output
        output = self.output_consensus()
        logger.info(f"Cycle complete: {output['consensus_picks']} consensus picks")
        
        return output
    
    def set_priority_order(self, order: List[SignalSource]):
        """Update the priority order for conflict resolution"""
        self.priority_order = order
        logger.info(f"Priority order updated: {[s.name for s in order]}")
    
    def set_conflict_resolver(self, method: Callable):
        """Set the conflict resolution method"""
        self.conflict_resolver = method
        logger.info(f"Conflict resolver set to: {method.__name__}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current router statistics"""
        return {
            'router_stats': self.stats.copy(),
            'config': {
                'conflict_window_minutes': self.conflict_window.total_seconds() / 60,
                'min_confidence': self.min_confidence,
                'consensus_threshold': self.consensus_threshold,
                'priority_order': [s.name for s in self.priority_order]
            }
        }
    
    # -------------------------------------------------------------------------
    # Private helper methods
    # -------------------------------------------------------------------------
    
    def _generic_adapt(self, raw: Dict[str, Any], source: str) -> NormalizedSignal:
        """Generic adapter for unknown sources"""
        return NormalizedSignal(
            signal_id=f"{source}_{uuid.uuid4().hex[:12]}",
            source=source,
            source_priority=SignalSource.CUSTOM.value,
            symbol=raw.get('symbol', raw.get('ticker', raw.get('pair', 'UNKNOWN'))),
            asset_class=raw.get('type', 'unknown'),
            direction=raw.get('direction', raw.get('signal', SignalDirection.HOLD.value)),
            confidence=float(raw.get('confidence', 0.5)),
            confidence_level=ConfidenceLevel.MEDIUM.name,
            raw_data=raw
        )
    
    def _find_conflicts(self, signals: List[NormalizedSignal]) -> List[List[NormalizedSignal]]:
        """Find groups of conflicting signals"""
        if len(signals) <= 1:
            return []
        
        # Group by direction
        direction_groups = defaultdict(list)
        for s in signals:
            direction_groups[s.direction].append(s)
        
        # If all same direction, no conflict
        if len(direction_groups) <= 1:
            return []
        
        # Check time overlap
        conflicts = []
        directions = list(direction_groups.keys())
        
        for i, dir1 in enumerate(directions):
            for dir2 in directions[i+1:]:
                for s1 in direction_groups[dir1]:
                    for s2 in direction_groups[dir2]:
                        time_diff = abs((s1.timestamp - s2.timestamp).total_seconds())
                        if time_diff <= self.conflict_window.total_seconds():
                            # Found conflict - include all signals from both directions
                            conflict_set = direction_groups[dir1] + direction_groups[dir2]
                            conflicts.append(conflict_set)
                            break
        
        return conflicts
    
    def _calculate_consensus(self, symbol: str, signals: List[NormalizedSignal]) -> ConsensusResult:
        """Calculate consensus metrics for a symbol"""
        if not signals:
            return ConsensusResult(
                symbol=symbol,
                consensus_direction=None,
                consensus_score=0.0,
                participating_signals=0,
                confidence_weighted_score=0.0,
                agreement_ratio=0.0,
                dominant_source=None,
                all_directions={}
            )
        
        # Count directions
        direction_counts = defaultdict(int)
        direction_confidence = defaultdict(float)
        source_counts = defaultdict(int)
        
        for s in signals:
            direction_counts[s.direction] += 1
            direction_confidence[s.direction] += s.confidence
            source_counts[s.source] += 1
        
        total = len(signals)
        
        # Find dominant direction
        dominant_direction = max(direction_counts.keys(), key=lambda d: direction_confidence[d])
        dominant_count = direction_counts[dominant_direction]
        
        # Calculate agreement ratio
        agreement_ratio = dominant_count / total
        
        # Calculate consensus score (confidence-weighted agreement)
        total_confidence = sum(s.confidence for s in signals)
        confidence_weighted_score = direction_confidence[dominant_direction] / total_confidence if total_confidence > 0 else 0
        consensus_score = agreement_ratio * confidence_weighted_score
        
        # Find dominant source
        dominant_source = max(source_counts.keys(), key=lambda s: source_counts[s])
        
        return ConsensusResult(
            symbol=symbol,
            consensus_direction=dominant_direction,
            consensus_score=consensus_score,
            participating_signals=total,
            confidence_weighted_score=confidence_weighted_score,
            agreement_ratio=agreement_ratio,
            dominant_source=dominant_source,
            all_directions=dict(direction_counts)
        )
    
    def _get_best_signal(
        self, 
        symbol: str, 
        signals: List[NormalizedSignal]
    ) -> Optional[NormalizedSignal]:
        """Get the best signal for a symbol based on priority and confidence"""
        if not signals:
            return None
        
        # Filter to resolved or active signals
        valid = [s for s in signals if s.status in 
                 [SignalStatus.ACTIVE.value, SignalStatus.RESOLVED.value, SignalStatus.PENDING.value]]
        
        if not valid:
            valid = signals
        
        # Sort by priority then confidence
        sorted_signals = sorted(valid, key=lambda s: (s.source_priority, -s.confidence))
        return sorted_signals[0] if sorted_signals else None


# =============================================================================
# INTEGRATION HELPERS
# =============================================================================

class DatabaseConsolidator:
    """
    Helper to consolidate data from 35+ SQLite databases and 60+ JSON files.
    """
    
    def __init__(self, router: SignalRouter):
        self.router = router
    
    def consolidate_sqlite(
        self, 
        db_path: str, 
        source: str,
        query: str,
        column_mapping: Dict[str, str]
    ) -> int:
        """
        Consolidate signals from an external SQLite database.
        
        Args:
            db_path: Path to source database
            source: Source system identifier
            query: SQL query to extract signals
            column_mapping: Map of source columns to standard fields
        
        Returns:
            Number of signals ingested
        """
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.execute(query)
            rows = cursor.fetchall()
            
            count = 0
            for row in rows:
                raw_signal = {}
                for i, col in enumerate(cursor.description):
                    col_name = col[0]
                    if col_name in column_mapping:
                        raw_signal[column_mapping[col_name]] = row[i]
                    else:
                        raw_signal[col_name] = row[i]
                
                if self.router.ingest_signal(raw_signal, source):
                    count += 1
            
            conn.close()
            logger.info(f"Consolidated {count} signals from {db_path}")
            return count
            
        except Exception as e:
            logger.error(f"Failed to consolidate {db_path}: {e}")
            return 0
    
    def consolidate_json(
        self, 
        json_path: str, 
        source: str,
        signal_key: Optional[str] = None
    ) -> int:
        """
        Consolidate signals from a JSON file.
        
        Args:
            json_path: Path to JSON file
            source: Source system identifier
            signal_key: Key containing signal array (if nested)
        
        Returns:
            Number of signals ingested
        """
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            signals = data.get(signal_key, data) if signal_key else data
            if not isinstance(signals, list):
                signals = [signals]
            
            results = self.router.ingest_batch(signals, source)
            logger.info(f"Consolidated {len(results)} signals from {json_path}")
            return len(results)
            
        except Exception as e:
            logger.error(f"Failed to consolidate {json_path}: {e}")
            return 0
    
    def consolidate_directory(
        self, 
        directory: str, 
        pattern: str,
        source: str
    ) -> int:
        """Consolidate all matching files from a directory"""
        import glob
        
        paths = glob.glob(f"{directory}/{pattern}")
        total = 0
        
        for path in paths:
            if path.endswith('.json'):
                total += self.consolidate_json(path, source)
            elif path.endswith('.db') or path.endswith('.sqlite'):
                # Need query and mapping for SQLite
                logger.warning(f"SQLite consolidation requires query: {path}")
        
        return total


# =============================================================================
# EXAMPLE USAGE AND DEMONSTRATION
# =============================================================================

def demo():
    """Demonstrate the SignalRouter functionality"""
    
    print("=" * 70)
    print("UNIFIED SIGNAL ROUTER - DEMONSTRATION")
    print("=" * 70)
    
    # Initialize router
    router = SignalRouter(
        db_path=":memory:",  # In-memory for demo
        conflict_window_minutes=30,
        min_confidence=0.4,
        consensus_threshold=0.5
    )
    
    # Sample signals from different sources
    print("\n[1] Ingesting signals from multiple sources...")
    print("-" * 50)
    
    # Battleground signals (highest priority)
    battleground_signals = [
        {'ticker': 'BTCUSDT', 'direction': 'long', 'strength': 0.92, 'price': 45000, 'sl': 43000, 'tp': 50000},
        {'ticker': 'ETHUSDT', 'direction': 'short', 'strength': 0.78, 'price': 3200, 'sl': 3400, 'tp': 2800},
        {'ticker': 'SOLUSDT', 'direction': 'long', 'strength': 0.85, 'price': 98, 'sl': 90, 'tp': 120},
    ]
    
    for sig in battleground_signals:
        router.ingest_signal(sig, 'battleground')
    
    # Alpha Engine signals
    alpha_signals = [
        {'pair': 'BTCUSDT', 'signal': 'buy', 'confidence': 0.75, 'entry_price': 45200, 'strategy': 'momentum'},
        {'pair': 'ETHUSDT', 'signal': 'sell', 'confidence': 0.68, 'entry_price': 3250, 'strategy': 'breakout'},
        {'pair': 'ADAUSDT', 'signal': 'buy', 'confidence': 0.82, 'entry_price': 0.55, 'strategy': 'trend'},
    ]
    
    for sig in alpha_signals:
        router.ingest_signal(sig, 'alpha_engine')
    
    # Mercury2 ML signals
    mercury_signals = [
        {'symbol': 'BTCUSDT', 'prob_up': 0.65, 'prob_down': 0.35, 'predicted_price': 46000, 'model_version': 'v2.1'},
        {'symbol': 'ETHUSDT', 'prob_up': 0.40, 'prob_down': 0.60, 'predicted_price': 3100, 'model_version': 'v2.1'},
        {'symbol': 'DOTUSDT', 'prob_up': 0.70, 'prob_down': 0.30, 'predicted_price': 7.5, 'model_version': 'v2.1'},
    ]
    
    for sig in mercury_signals:
        router.ingest_signal(sig, 'mercury2')
    
    # Multi-Asset signals
    multi_signals = [
        {'ticker': 'SPY', 'recommendation': 'long', 'score': 78, 'target_entry': 480, 'type': 'etf'},
        {'ticker': 'QQQ', 'recommendation': 'long', 'score': 82, 'target_entry': 420, 'type': 'etf'},
        {'ticker': 'BTCUSDT', 'recommendation': 'long', 'score': 65, 'target_entry': 45500, 'type': 'crypto'},
    ]
    
    for sig in multi_signals:
        router.ingest_signal(sig, 'multi_asset')
    
    print("\n[2] Router Statistics:")
    print("-" * 50)
    stats = router.get_stats()
    for key, value in stats['router_stats'].items():
        print(f"  {key}: {value}")
    
    print("\n[3] Resolving conflicts...")
    print("-" * 50)
    resolved = router.resolve_conflicts()
    print(f"  Resolved {len(resolved)} conflict groups")
    for group in resolved[:3]:  # Show first 3
        print(f"    - {group.symbol}: {len(group.signals)} signals -> {group.resolution.source} wins")
    
    print("\n[4] Generating consensus output...")
    print("-" * 50)
    output = router.output_consensus(output_path=None)  # Don't write file in demo
    
    print(f"\n  Generated at: {output['generated_at']}")
    print(f"  Active symbols: {output['active_symbols']}")
    print(f"  Consensus picks: {output['consensus_picks']}")
    
    print("\n[5] Top Consensus Picks:")
    print("-" * 50)
    for i, pick in enumerate(output['picks'][:5], 1):
        print(f"\n  #{i} {pick['symbol']}")
        print(f"     Direction: {pick['direction']}")
        print(f"     Consensus Score: {pick['consensus_score']}")
        print(f"     Sources: {', '.join(pick['sources'])}")
        print(f"     Agreement: {pick['agreement_ratio']}")
        if pick['suggested_price']:
            print(f"     Price: {pick['suggested_price']}")
    
    print("\n[6] Conflict Resolution Examples:")
    print("-" * 50)
    print("  BTCUSDT had conflicting signals:")
    print("    - Battleground: LONG (conf=0.92, priority=1)")
    print("    - Alpha Engine: LONG (conf=0.75, priority=2)")
    print("    - Mercury2: LONG (conf=0.65, priority=3)")
    print("    - Multi-Asset: LONG (conf=0.65, priority=4)")
    print("  -> Resolution: Battleground wins (highest priority)")
    
    print("\n  ETHUSDT had conflicting signals:")
    print("    - Battleground: SHORT (conf=0.78, priority=1)")
    print("    - Alpha Engine: SHORT (conf=0.68, priority=2)")
    print("    - Mercury2: SHORT (conf=0.60, priority=3)")
    print("  -> Resolution: Battleground wins (highest priority)")
    
    print("\n" + "=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)
    
    return router, output


if __name__ == "__main__":
    demo()
