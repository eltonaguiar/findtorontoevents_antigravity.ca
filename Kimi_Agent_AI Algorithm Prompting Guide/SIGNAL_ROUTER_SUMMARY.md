# Signal Router Implementation Summary

## Files Created

| File | Description | Size |
|------|-------------|------|
| `unified_signal_router.py` | Main implementation with SignalRouter class | ~1500 lines |
| `integration_patterns.py` | Integration patterns for various data sources | ~800 lines |
| `usage_examples.py` | Practical usage examples | ~600 lines |
| `signal_router_config.json` | Configuration template | ~200 lines |
| `README_SignalRouter.md` | Complete documentation | ~500 lines |

## Key Features Implemented

### 1. SignalRouter Class

**Core Methods:**
- `ingest_signal()` - Normalize and store incoming signals
- `ingest_batch()` - Process multiple signals efficiently
- `resolve_conflicts()` - Apply conflict resolution strategies
- `output_consensus()` - Generate unified output
- `run_cycle()` - Complete routing cycle

**Configuration Options:**
- `db_path` - Database location
- `conflict_window_minutes` - Time window for conflict detection
- `min_confidence` - Minimum confidence threshold
- `consensus_threshold` - Minimum consensus score for output
- `output_path` - Output file location

### 2. Source Adapters

**Built-in Adapters:**

| Adapter | Source | Priority | Asset Class |
|---------|--------|----------|-------------|
| BattlegroundAdapter | battleground | 1 | crypto |
| AlphaEngineAdapter | alpha_engine | 2 | crypto |
| Mercury2Adapter | mercury2 | 3 | crypto/stock |
| MultiAssetAdapter | multi_asset | 4 | etf/stock |
| KIMIAdapter | kimi | 5 | any |

**Adapter Interface:**
```python
class SourceAdapter:
    def __init__(self, source_name: str, priority: int)
    def adapt(self, raw_signal: Dict) -> NormalizedSignal
```

### 3. Conflict Resolution

**Available Methods:**

| Method | Algorithm | Best For |
|--------|-----------|----------|
| `priority_based` | Highest priority wins | Default resolution |
| `confidence_based` | Highest confidence wins | Same priority conflicts |
| `weighted_score` | priority × confidence | Balanced approach |
| `consensus_merge` | Weighted average merge | Multi-signal aggregation |
| `directional_agreement` | 60% threshold | Validation |

### 4. Database Schema

**Tables:**

```sql
signals          - Core signal storage
conflict_groups  - Conflict tracking
consensus_history - Consensus calculations
source_metadata  - Source information
signal_relationships - Duplicate tracking
```

**Indexes:**
- `idx_signals_symbol` - Fast symbol lookups
- `idx_signals_source` - Source filtering
- `idx_signals_status` - Status filtering
- `idx_signals_timestamp` - Time-based queries
- `idx_signals_fingerprint` - Duplicate detection

### 5. Integration Patterns

| Pattern | Class | Use Case |
|---------|-------|----------|
| Webhook | `WebhookSignalReceiver` | Real-time HTTP signals |
| Database Poll | `DatabasePoller` | SQLite-based systems |
| File Watcher | `FileWatcher` | JSON file outputs |
| Scheduled | `ScheduledAggregator` | Batch processing |
| Redis | `MessageQueueConsumer` | High-throughput streams |
| RabbitMQ | `MessageQueueConsumer` | Message queue systems |
| API Poll | `APIClientIntegration` | REST API sources |

## Normalized Signal Schema

```python
@dataclass
class NormalizedSignal:
    # Required fields
    signal_id: str
    source: str
    source_priority: int
    symbol: str
    asset_class: str
    direction: str
    confidence: float
    confidence_level: str
    
    # Optional fields
    exchange: Optional[str]
    suggested_size: Optional[float]
    suggested_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    timestamp: datetime
    expiry: Optional[datetime]
    timeframe: Optional[str]
    strategy: Optional[str]
    raw_data: Dict
    source_signal_id: Optional[str]
    status: str
    conflict_group: Optional[str]
    consensus_score: Optional[float]
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
    }
  ]
}
```

## Usage Examples

### Basic Usage

```python
from unified_signal_router import SignalRouter

router = SignalRouter()

# Ingest signals
router.ingest_signal({
    'ticker': 'BTCUSDT',
    'direction': 'long',
    'strength': 0.92
}, 'battleground')

# Resolve and output
router.resolve_conflicts()
output = router.output_consensus()
```

### Custom Priority Order

```python
from unified_signal_router import SignalSource

router.set_priority_order([
    SignalSource.MERCURY2,      # ML first
    SignalSource.BATTLEGROUND,  # Then momentum
    SignalSource.ALPHA_ENGINE,
    SignalSource.MULTI_ASSET,
    SignalSource.KIMI,
])
```

### Custom Conflict Resolver

```python
from unified_signal_router import ConflictResolver

router.set_conflict_resolver(ConflictResolver.consensus_merge)
```

### Database Consolidation

```python
from unified_signal_router import DatabaseConsolidator

consolidator = DatabaseConsolidator(router)

# From SQLite
consolidator.consolidate_sqlite(
    db_path="legacy.db",
    source="legacy",
    query="SELECT * FROM signals",
    column_mapping={'ticker': 'symbol', 'signal': 'direction'}
)

# From JSON
consolidator.consolidate_json(
    json_path="signals.json",
    source="file_system"
)
```

## Conflict Resolution Examples

### Example 1: Priority Wins

```
Input:
  Battleground: LONG (conf=0.75, priority=1)
  Alpha Engine: LONG (conf=0.90, priority=2)

Resolution: Battleground wins (priority=1)
Output: LONG from Battleground
```

### Example 2: Confidence Wins (same priority)

```
Input:
  Alpha Engine: LONG (conf=0.75)
  Alpha Engine: LONG (conf=0.90)

Resolution: Higher confidence wins
Output: LONG with conf=0.90
```

### Example 3: Opposing Directions

```
Input:
  Battleground: LONG  (conf=0.85, priority=1)
  Alpha Engine: SHORT (conf=0.95, priority=2)

Resolution: Battleground wins (priority trumps confidence)
Output: LONG from Battleground
```

### Example 4: Consensus Merge

```
Input:
  Battleground: LONG (conf=0.80, price=100)
  Alpha Engine: LONG (conf=0.70, price=102)
  Mercury2:     LONG (conf=0.60, price=99)

Resolution: Weighted average
Output: LONG with price=100.4 (weighted by confidence)
```

## Performance Characteristics

| Operation | Complexity | Notes |
|-----------|------------|-------|
| Signal Ingestion | O(1) | With fingerprint check |
| Conflict Detection | O(n) | Per symbol |
| Conflict Resolution | O(n log n) | Sorting by priority |
| Consensus Calculation | O(n) | Per symbol |
| Database Query | O(log n) | With indexes |

## Integration Checklist

- [ ] Copy `unified_signal_router.py` to your project
- [ ] Configure priority order for your sources
- [ ] Set up source adapters for custom systems
- [ ] Configure conflict resolution method
- [ ] Set up integration pattern (webhook/poller/watcher)
- [ ] Configure output path for `live_picks.json`
- [ ] Set up scheduled aggregation (5-minute cycle)
- [ ] Test with sample signals from each source
- [ ] Monitor statistics and adjust thresholds
- [ ] Deploy to production

## Migration from Existing System

1. **Identify all signal sources** (35+ databases, 60+ JSON files)
2. **Map source formats** to unified schema
3. **Configure adapters** for each source
4. **Set up consolidation** for historical data
5. **Run parallel** with existing system
6. **Validate output** matches expectations
7. **Switch over** to unified router

## Monitoring

```python
# Get statistics
stats = router.get_stats()
print(f"Ingested: {stats['router_stats']['ingested']}")
print(f"Conflicts: {stats['router_stats']['conflicts']}")
print(f"Output: {stats['router_stats']['output']}")

# Get live picks
picks = router.get_live_picks()
for pick in picks:
    print(f"{pick['symbol']}: {pick['direction']}")
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| No signals output | Confidence threshold too high | Lower `min_confidence` |
| Too many conflicts | Time window too large | Reduce `conflict_window_minutes` |
| Duplicates not caught | Time granularity too coarse | Use finer granularity |
| Wrong source wins | Priority order incorrect | Reconfigure `priority_order` |
| Database locked | Concurrent access | Use file-based database |

## Next Steps

1. Review configuration in `signal_router_config.json`
2. Run demonstration: `python unified_signal_router.py`
3. Test with your actual signal sources
4. Customize adapters for proprietary systems
5. Deploy to production environment

## Support

For questions or issues:
1. Check `README_SignalRouter.md` for detailed documentation
2. Review `usage_examples.py` for code samples
3. Examine `integration_patterns.py` for integration options
