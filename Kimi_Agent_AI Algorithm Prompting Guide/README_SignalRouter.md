# Unified Signal Router

A production-ready signal aggregation system that consolidates picks from ~80 active trading systems into a single coherent output.

## Overview

The Unified Signal Router solves the problem of fragmented signal flow in multi-system trading infrastructures. It provides:

- **Signal Normalization**: Converts heterogeneous signal formats into a unified schema
- **Conflict Resolution**: Handles overlapping signals with priority-based and consensus algorithms
- **Duplicate Prevention**: Fingerprint-based deduplication
- **Consensus Generation**: Aggregates multiple signals into unified picks
- **Real-time & Batch Processing**: Supports both streaming and scheduled aggregation

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         UNIFIED SIGNAL ROUTER                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Battleground│  │Alpha Engine │  │  Mercury2   │  │ Multi-Asset │        │
│  │  (Priority 1)│  │ (Priority 2)│  │ (Priority 3)│  │ (Priority 4)│        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │               │
│         └────────────────┴────────────────┴────────────────┘               │
│                                    │                                        │
│                         ┌──────────▼──────────┐                            │
│                         │   SOURCE ADAPTERS   │                            │
│                         │  (Normalization)    │                            │
│                         └──────────┬──────────┘                            │
│                                    │                                        │
│                         ┌──────────▼──────────┐                            │
│                         │  UNIFIED DATABASE   │                            │
│                         │   (SQLite)          │                            │
│                         └──────────┬──────────┘                            │
│                                    │                                        │
│              ┌─────────────────────┼─────────────────────┐                │
│              │                     │                     │                │
│    ┌─────────▼─────────┐  ┌────────▼────────┐  ┌────────▼───────┐       │
│    │CONFLICT RESOLUTION│  │  CONSENSUS      │  │  DUPLICATES    │       │
│    │  (Priority-based) │  │  CALCULATION    │  │  DETECTION     │       │
│    └─────────┬─────────┘  └────────┬────────┘  └────────────────┘       │
│              │                     │                                      │
│              └─────────────────────┼─────────────────────┐               │
│                                    │                     │               │
│                         ┌──────────▼──────────┐         │               │
│                         │   OUTPUT GENERATOR  │         │               │
│                         └──────────┬──────────┘         │               │
│                                    │                    │               │
│                         ┌──────────▼──────────┐         │               │
│                         │   live_picks.json   │         │               │
│                         │   (Unified Output)  │◄────────┘               │
│                         └─────────────────────┘                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Priority Order

The default priority configuration (highest to lowest):

1. **Battleground** (Priority 1) - Crypto momentum signals
2. **Alpha Engine** (Priority 2) - Crypto alpha signals
3. **Mercury2** (Priority 3) - ML-based predictions
4. **Multi-Asset** (Priority 4) - ETF/stock signals
5. **KIMI** (Priority 5) - AI assistant signals

## Installation

```bash
# Copy the main router file to your project
cp unified_signal_router.py /your/trading/system/

# Install dependencies (if using webhooks or message queues)
pip install flask redis pika
```

## Quick Start

```python
from unified_signal_router import SignalRouter, ConflictResolver

# Initialize router
router = SignalRouter(
    db_path="unified_signals.db",
    conflict_window_minutes=30,
    min_confidence=0.4,
    consensus_threshold=0.5,
    output_path="live_picks.json"
)

# Ingest signals from different sources
router.ingest_signal({
    'ticker': 'BTCUSDT',
    'direction': 'long',
    'strength': 0.92,
    'price': 45000
}, 'battleground')

router.ingest_signal({
    'pair': 'BTCUSDT',
    'signal': 'buy',
    'confidence': 0.75,
    'entry_price': 45200
}, 'alpha_engine')

# Resolve conflicts
router.resolve_conflicts()

# Generate output
output = router.output_consensus()
print(f"Generated {len(output['picks'])} consensus picks")
```

## Core Components

### 1. SignalRouter Class

Main orchestrator for signal aggregation.

**Key Methods:**

| Method | Description |
|--------|-------------|
| `ingest_signal(raw_signal, source)` | Ingest and normalize a single signal |
| `ingest_batch(signals, source)` | Ingest multiple signals from same source |
| `resolve_conflicts(symbol=None)` | Resolve conflicting signals |
| `output_consensus()` | Generate unified output |
| `run_cycle()` | Complete routing cycle |

### 2. Source Adapters

Convert source-specific formats to unified schema.

**Built-in Adapters:**
- `AlphaEngineAdapter` - Crypto alpha signals
- `BattlegroundAdapter` - Momentum signals
- `Mercury2Adapter` - ML predictions
- `MultiAssetAdapter` - ETF/stock signals
- `KIMIAdapter` - AI analysis signals

**Custom Adapter Example:**

```python
from unified_signal_router import SourceAdapter, NormalizedSignal

class MyCustomAdapter(SourceAdapter):
    def __init__(self):
        super().__init__('my_system', priority=10)
    
    def adapt(self, raw: dict) -> NormalizedSignal:
        return NormalizedSignal(
            signal_id=self._generate_signal_id(raw),
            source=self.source_name,
            source_priority=self.priority,
            symbol=raw['ticker'],
            asset_class='stock',
            direction=raw['signal'],
            confidence=raw['confidence'],
            confidence_level='MEDIUM',
            raw_data=raw
        )

# Register adapter
from unified_signal_router import ADAPTER_REGISTRY
ADAPTER_REGISTRY['my_system'] = MyCustomAdapter()
```

### 3. Conflict Resolution

**Available Methods:**

| Method | Description | Use Case |
|--------|-------------|----------|
| `priority_based` | Select highest priority signal | Default resolution |
| `confidence_based` | Select highest confidence | Same priority conflicts |
| `weighted_score` | Combine priority and confidence | Balanced approach |
| `consensus_merge` | Merge with weighted average | Multi-direction signals |
| `directional_agreement` | Require 60% agreement | Validation |

**Usage:**

```python
# Set conflict resolver
router.set_conflict_resolver(ConflictResolver.consensus_merge)

# Resolve all conflicts
router.resolve_conflicts()

# Resolve specific symbol
router.resolve_conflicts(symbol='BTCUSDT')
```

### 4. Database Schema

**Core Tables:**

```sql
-- Signals table
CREATE TABLE signals (
    signal_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    source_priority INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    direction TEXT NOT NULL,
    confidence REAL NOT NULL,
    suggested_price REAL,
    stop_loss REAL,
    take_profit REAL,
    timestamp TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    fingerprint TEXT UNIQUE,
    ...
);

-- Conflict groups
CREATE TABLE conflict_groups (
    group_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    resolution_method TEXT,
    resolved_signal_id TEXT,
    ...
);

-- Consensus history
CREATE TABLE consensus_history (
    consensus_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    consensus_direction TEXT,
    consensus_score REAL,
    ...
);
```

## Integration Patterns

### Pattern 1: Webhook Integration

```python
from integration_patterns import WebhookSignalReceiver

webhook = WebhookSignalReceiver(router, port=8080)
webhook.start_server()

# Signals received at POST /webhook/<source>
```

### Pattern 2: Database Polling

```python
from integration_patterns import DatabasePoller

poller = DatabasePoller(router)
poller.register_database(
    name="alpha_engine",
    db_path="/path/to/alpha/signals.db",
    query="SELECT * FROM signals WHERE status = 'active'",
    column_mapping={
        'pair': 'symbol',
        'signal': 'direction',
        'confidence': 'confidence'
    },
    source="alpha_engine",
    interval_seconds=60
)
poller.start()
```

### Pattern 3: File Watcher

```python
from integration_patterns import FileWatcher

watcher = FileWatcher(router)
watcher.watch_directory(
    name="battleground",
    directory="/data/battleground/output",
    pattern="*.json",
    source="battleground",
    interval_seconds=30
)
watcher.start()
```

### Pattern 4: Scheduled Aggregation

```python
from integration_patterns import ScheduledAggregator

aggregator = ScheduledAggregator(router)
aggregator.start(interval_minutes=5)  # Runs every 5 minutes
```

### Pattern 5: Message Queue (Redis)

```python
from integration_patterns import MessageQueueConsumer

consumer = MessageQueueConsumer(router)
consumer.consume_redis(
    name="mercury2",
    redis_url="redis://localhost:6379",
    channel="mercury2:predictions",
    source="mercury2"
)
consumer.start()
```

### Pattern 6: REST API Polling

```python
from integration_patterns import APIClientIntegration

client = APIClientIntegration(router)
client.poll_api(
    name="kimi",
    endpoint="https://api.kimi.example.com/v1/signals",
    source="kimi",
    headers={"Authorization": "Bearer TOKEN"},
    interval_seconds=300
)
client.start()
```

## Output Format

### live_picks.json

```json
{
  "generated_at": "2024-01-15T10:30:00",
  "router_stats": {
    "ingested": 150,
    "normalized": 148,
    "duplicates": 2,
    "conflicts": 12,
    "resolved": 12,
    "output": 25
  },
  "active_symbols": 25,
  "consensus_picks": 20,
  "picks": [
    {
      "symbol": "BTCUSDT",
      "direction": "long",
      "consensus_score": 0.92,
      "confidence": 0.90,
      "source": "battleground",
      "sources": ["battleground", "alpha_engine", "mercury2"],
      "agreement_ratio": 1.0,
      "suggested_price": 45000,
      "stop_loss": 43000,
      "take_profit": 50000,
      "signal_id": "bg_abc123",
      "timestamp": "2024-01-15T10:25:00"
    },
    ...
  ]
}
```

## Configuration

See `signal_router_config.json` for complete configuration template.

```json
{
  "router": {
    "db_path": "unified_signals.db",
    "conflict_window_minutes": 30,
    "min_confidence": 0.4,
    "consensus_threshold": 0.5,
    "output_path": "live_picks.json"
  },
  "priority_order": [
    "BATTLEGROUND",
    "ALPHA_ENGINE",
    "MERCURY2",
    "MULTI_ASSET",
    "KIMI"
  ],
  "conflict_resolver": "priority_based",
  "sources": { ... }
}
```

## Conflict Resolution Examples

### Example 1: Same Direction, Different Sources

```
BTCUSDT signals:
- Battleground: LONG (conf=0.92, priority=1)
- Alpha Engine: LONG (conf=0.75, priority=2)
- Mercury2:     LONG (conf=0.65, priority=3)

Resolution: Battleground wins (highest priority)
Output: LONG from Battleground
```

### Example 2: Opposing Directions

```
ETHUSDT signals:
- Battleground: LONG  (conf=0.85, priority=1)
- Alpha Engine: SHORT (conf=0.90, priority=2)

Resolution: Battleground wins (priority trumps confidence)
Output: LONG from Battleground
```

### Example 3: Consensus Merge

```
SOLUSDT signals:
- Battleground: LONG (conf=0.80, price=98)
- Alpha Engine: LONG (conf=0.75, price=99)
- Mercury2:     LONG (conf=0.70, price=97)

Resolution: Consensus merge (weighted average)
Output: LONG with price=98.1 (weighted by confidence)
```

## Database Consolidation

Consolidate from 35+ SQLite databases and 60+ JSON files:

```python
from unified_signal_router import DatabaseConsolidator

consolidator = DatabaseConsolidator(router)

# From SQLite
consolidator.consolidate_sqlite(
    db_path="legacy_system.db",
    source="legacy",
    query="SELECT * FROM signals",
    column_mapping={
        'ticker': 'symbol',
        'signal': 'direction',
        'confidence': 'confidence'
    }
)

# From JSON
consolidator.consolidate_json(
    json_path="signals.json",
    source="file_system"
)

# From directory
consolidator.consolidate_directory(
    directory="/data/signals",
    pattern="*.json",
    source="batch_processor"
)
```

## Monitoring & Statistics

```python
# Get router statistics
stats = router.get_stats()
print(json.dumps(stats, indent=2))

# Output:
# {
#   "router_stats": {
#     "ingested": 150,
#     "normalized": 148,
#     "duplicates": 2,
#     "conflicts": 12,
#     "resolved": 12,
#     "output": 25
#   },
#   "config": {
#     "conflict_window_minutes": 30,
#     "min_confidence": 0.4,
#     "consensus_threshold": 0.5
#   }
# }
```

## Running the Demo

```bash
python unified_signal_router.py
```

This will run a complete demonstration showing:
- Signal ingestion from multiple sources
- Conflict resolution
- Consensus generation
- Output formatting

## Testing

```bash
# Run usage examples
python usage_examples.py
```

## Performance Considerations

- **Database**: SQLite with proper indexes for fast lookups
- **Thread Safety**: Thread-local connections for concurrent access
- **Memory**: In-memory option available for testing
- **Batch Processing**: Efficient batch ingestion for large datasets

## API Reference

See inline documentation in `unified_signal_router.py` for complete API reference.

## License

MIT License - See LICENSE file for details.

## Support

For issues and feature requests, please open an issue on the project repository.
