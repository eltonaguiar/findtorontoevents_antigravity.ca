#!/usr/bin/env python3
"""
Signal Router Usage Examples
============================
Practical examples for using the Unified Signal Router.
"""

import json
from datetime import datetime, timedelta
from unified_signal_router import (
    SignalRouter, DatabaseConsolidator, 
    ConflictResolver, SignalSource, SignalDirection,
    NormalizedSignal, SourceAdapter
)


# =============================================================================
# EXAMPLE 1: BASIC USAGE
# =============================================================================

def example_basic_usage():
    """Basic signal routing example"""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 1: Basic Signal Router Usage")
    print("=" * 60)
    
    # Create router
    router = SignalRouter(
        db_path=":memory:",  # In-memory for demo
        min_confidence=0.3
    )
    
    # Ingest signals from different sources
    print("\n[1] Ingesting signals...")
    
    # Battleground signal (highest priority)
    bg_signal = {
        'ticker': 'BTCUSDT',
        'direction': 'long',
        'strength': 0.92,
        'price': 45000,
        'sl': 43000,
        'tp': 50000
    }
    router.ingest_signal(bg_signal, 'battleground')
    
    # Alpha Engine signal
    ae_signal = {
        'pair': 'BTCUSDT',
        'signal': 'buy',
        'confidence': 0.75,
        'entry_price': 45200
    }
    router.ingest_signal(ae_signal, 'alpha_engine')
    
    # Mercury2 signal
    m2_signal = {
        'symbol': 'ETHUSDT',
        'prob_up': 0.65,
        'prob_down': 0.35,
        'predicted_price': 3200
    }
    router.ingest_signal(m2_signal, 'mercury2')
    
    print("[2] Resolving conflicts...")
    router.resolve_conflicts()
    
    print("[3] Generating output...")
    output = router.output_consensus(output_path=None)
    
    print(f"\nResults:")
    print(f"  - Signals ingested: {router.stats['ingested']}")
    print(f"  - Conflicts resolved: {router.stats['resolved']}")
    print(f"  - Consensus picks: {len(output['picks'])}")
    
    for pick in output['picks']:
        print(f"\n  {pick['symbol']}: {pick['direction'].upper()}")
        print(f"    Score: {pick['consensus_score']:.2f}")
        print(f"    Sources: {', '.join(pick['sources'])}")


# =============================================================================
# EXAMPLE 2: CONFLICT RESOLUTION METHODS
# =============================================================================

def example_conflict_resolution():
    """Demonstrate different conflict resolution methods"""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Conflict Resolution Methods")
    print("=" * 60)
    
    # Create conflicting signals
    conflicting_signals = [
        NormalizedSignal(
            signal_id='test_1',
            source='battleground',
            source_priority=1,
            symbol='BTCUSDT',
            asset_class='crypto',
            direction=SignalDirection.LONG.value,
            confidence=0.75,
            confidence_level='HIGH'
        ),
        NormalizedSignal(
            signal_id='test_2',
            source='alpha_engine',
            source_priority=2,
            symbol='BTCUSDT',
            asset_class='crypto',
            direction=SignalDirection.SHORT.value,
            confidence=0.90,
            confidence_level='VERY_HIGH'
        ),
        NormalizedSignal(
            signal_id='test_3',
            source='mercury2',
            source_priority=3,
            symbol='BTCUSDT',
            asset_class='crypto',
            direction=SignalDirection.LONG.value,
            confidence=0.60,
            confidence_level='MEDIUM'
        ),
    ]
    
    print("\nConflicting Signals:")
    for s in conflicting_signals:
        print(f"  {s.source}: {s.direction} (conf={s.confidence}, priority={s.source_priority})")
    
    # Test different resolvers
    resolvers = [
        ('Priority Based', ConflictResolver.priority_based),
        ('Confidence Based', ConflictResolver.confidence_based),
        ('Weighted Score', ConflictResolver.weighted_score),
        ('Consensus Merge', ConflictResolver.consensus_merge),
    ]
    
    print("\nResolution Results:")
    for name, resolver in resolvers:
        try:
            winner = resolver(conflicting_signals)
            print(f"\n  {name}:")
            print(f"    Winner: {winner.source}")
            print(f"    Direction: {winner.direction}")
            print(f"    Confidence: {winner.confidence:.2f}")
        except Exception as e:
            print(f"\n  {name}: Error - {e}")


# =============================================================================
# EXAMPLE 3: DATABASE CONSOLIDATION
# =============================================================================

def example_database_consolidation():
    """Demonstrate database consolidation from multiple sources"""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Database Consolidation")
    print("=" * 60)
    
    router = SignalRouter(db_path=":memory:")
    consolidator = DatabaseConsolidator(router)
    
    # Example: Create a temporary source database
    import sqlite3
    import tempfile
    import os
    
    # Create temp database
    temp_db = tempfile.mktemp(suffix='.db')
    conn = sqlite3.connect(temp_db)
    
    # Create sample table
    conn.execute('''
        CREATE TABLE signals (
            id TEXT PRIMARY KEY,
            pair TEXT,
            signal TEXT,
            confidence REAL,
            price REAL,
            created_at TEXT
        )
    ''')
    
    # Insert sample data
    sample_data = [
        ('sig_1', 'BTCUSDT', 'buy', 0.82, 45000, datetime.utcnow().isoformat()),
        ('sig_2', 'ETHUSDT', 'sell', 0.75, 3200, datetime.utcnow().isoformat()),
        ('sig_3', 'SOLUSDT', 'buy', 0.68, 98, datetime.utcnow().isoformat()),
    ]
    
    conn.executemany(
        'INSERT INTO signals VALUES (?, ?, ?, ?, ?, ?)',
        sample_data
    )
    conn.commit()
    conn.close()
    
    print(f"\n[1] Created temp database: {temp_db}")
    
    # Consolidate from database
    print("[2] Consolidating signals...")
    count = consolidator.consolidate_sqlite(
        db_path=temp_db,
        source='legacy_system',
        query='SELECT * FROM signals',
        column_mapping={
            'pair': 'symbol',
            'signal': 'direction',
            'confidence': 'confidence',
            'price': 'suggested_price'
        }
    )
    
    print(f"[3] Consolidated {count} signals")
    
    # Show live picks
    picks = router.get_live_picks()
    print(f"\n[4] Live picks ({len(picks)}):")
    for pick in picks:
        print(f"  {pick['symbol']}: {pick['direction']}")
    
    # Cleanup
    os.unlink(temp_db)


# =============================================================================
# EXAMPLE 4: CUSTOM ADAPTER
# =============================================================================

def example_custom_adapter():
    """Create and use a custom source adapter"""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Custom Source Adapter")
    print("=" * 60)
    
    # Define custom adapter for a proprietary system
    class ProprietaryAdapter(SourceAdapter):
        def __init__(self):
            super().__init__('proprietary', 10)
        
        def adapt(self, raw: dict) -> NormalizedSignal:
            # Custom mapping logic
            direction_map = {
                1: SignalDirection.LONG.value,
                -1: SignalDirection.SHORT.value,
                0: SignalDirection.NEUTRAL.value
            }
            
            return NormalizedSignal(
                signal_id=self._generate_signal_id(raw),
                source=self.source_name,
                source_priority=self.priority,
                symbol=raw.get('ticker'),
                asset_class='stock',
                direction=direction_map.get(raw.get('signal_code'), SignalDirection.HOLD.value),
                confidence=raw.get('probability', 0.5),
                confidence_level='MEDIUM',
                suggested_price=raw.get('target_price'),
                strategy=raw.get('model_name'),
                raw_data=raw
            )
    
    # Create router with custom adapter
    router = SignalRouter(db_path=":memory:")
    
    # Register custom adapter
    from unified_signal_router import ADAPTER_REGISTRY
    ADAPTER_REGISTRY['proprietary'] = ProprietaryAdapter()
    
    # Ingest proprietary signal
    proprietary_signal = {
        'ticker': 'AAPL',
        'signal_code': 1,  # Long
        'probability': 0.78,
        'target_price': 185.50,
        'model_name': 'prop_v2'
    }
    
    print("\n[1] Ingesting proprietary signal...")
    normalized = router.ingest_signal(proprietary_signal, 'proprietary')
    
    if normalized:
        print(f"[2] Normalized signal:")
        print(f"    Symbol: {normalized.symbol}")
        print(f"    Direction: {normalized.direction}")
        print(f"    Confidence: {normalized.confidence}")
        print(f"    Price: {normalized.suggested_price}")


# =============================================================================
# EXAMPLE 5: BATCH PROCESSING
# =============================================================================

def example_batch_processing():
    """Process signals in batch"""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Batch Processing")
    print("=" * 60)
    
    router = SignalRouter(db_path=":memory:")
    
    # Batch of signals
    batch = [
        {'ticker': 'BTCUSDT', 'direction': 'long', 'strength': 0.85, 'price': 45000},
        {'ticker': 'ETHUSDT', 'direction': 'short', 'strength': 0.72, 'price': 3200},
        {'ticker': 'SOLUSDT', 'direction': 'long', 'strength': 0.90, 'price': 98},
        {'ticker': 'ADAUSDT', 'direction': 'long', 'strength': 0.65, 'price': 0.55},
        {'ticker': 'DOTUSDT', 'direction': 'short', 'strength': 0.78, 'price': 7.2},
    ]
    
    print(f"\n[1] Processing batch of {len(batch)} signals...")
    results = router.ingest_batch(batch, 'battleground')
    
    print(f"[2] Accepted: {len(results)}/{len(batch)}")
    
    print("\n[3] Signal summary:")
    for sig in results:
        print(f"    {sig.symbol}: {sig.direction} (conf={sig.confidence:.2f})")
    
    # Generate output
    output = router.output_consensus(output_path=None)
    print(f"\n[4] Consensus picks: {len(output['picks'])}")


# =============================================================================
# EXAMPLE 6: PRIORITY CONFIGURATION
# =============================================================================

def example_priority_configuration():
    """Configure custom priority order"""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Priority Configuration")
    print("=" * 60)
    
    router = SignalRouter(db_path=":memory:")
    
    # Set custom priority order
    custom_order = [
        SignalSource.MERCURY2,      # ML signals first
        SignalSource.BATTLEGROUND,  # Then momentum
        SignalSource.ALPHA_ENGINE,  # Then alpha
        SignalSource.MULTI_ASSET,   # Then multi-asset
        SignalSource.KIMI,          # AI last
    ]
    
    router.set_priority_order(custom_order)
    
    print("\n[1] Custom priority order set:")
    for i, source in enumerate(custom_order, 1):
        print(f"    {i}. {source.name}")
    
    # Add conflicting signals
    signals = [
        {'symbol': 'BTCUSDT', 'direction': 'long', 'confidence': 0.70},  # Will be Mercury2
        {'ticker': 'BTCUSDT', 'direction': 'short', 'strength': 0.95},   # Will be Battleground
    ]
    
    # Ingest with different sources
    router.ingest_signal(signals[0], 'mercury2')
    router.ingest_signal(signals[1], 'battleground')
    
    print("\n[2] Conflicting signals ingested:")
    print("    Mercury2: LONG (conf=0.70)")
    print("    Battleground: SHORT (conf=0.95)")
    
    # Resolve
    router.resolve_conflicts()
    
    print("\n[3] Resolution (Mercury2 wins due to priority):")
    picks = router.get_live_picks()
    for pick in picks:
        print(f"    {pick['symbol']}: {pick['direction']} from {pick['source']}")


# =============================================================================
# EXAMPLE 7: OUTPUT FORMATS
# =============================================================================

def example_output_formats():
    """Demonstrate different output formats"""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 7: Output Formats")
    print("=" * 60)
    
    router = SignalRouter(db_path=":memory:")
    
    # Add some signals
    signals = [
        {'ticker': 'BTCUSDT', 'direction': 'long', 'strength': 0.92, 'price': 45000, 'sl': 43000, 'tp': 50000},
        {'ticker': 'ETHUSDT', 'direction': 'long', 'strength': 0.85, 'price': 3200, 'sl': 3000, 'tp': 3600},
        {'pair': 'SOLUSDT', 'signal': 'buy', 'confidence': 0.78, 'entry_price': 98},
    ]
    
    router.ingest_signal(signals[0], 'battleground')
    router.ingest_signal(signals[1], 'battleground')
    router.ingest_signal(signals[2], 'alpha_engine')
    
    # Generate output
    output = router.output_consensus(output_path=None)
    
    print("\n[1] JSON Output Structure:")
    print(json.dumps(output, indent=2, default=str)[:1500] + "...")
    
    print("\n[2] Live Picks (simplified):")
    picks = router.get_live_picks()
    for pick in picks:
        print(f"    {pick['symbol']}: {pick['direction']} (score={pick.get('consensus_score', 'N/A')})")


# =============================================================================
# EXAMPLE 8: REAL-TIME SIMULATION
# =============================================================================

def example_realtime_simulation():
    """Simulate real-time signal flow"""
    
    print("\n" + "=" * 60)
    print("EXAMPLE 8: Real-Time Simulation")
    print("=" * 60)
    
    router = SignalRouter(db_path=":memory:")
    
    # Simulate signals arriving over time
    timeline = [
        (0, 'battleground', {'ticker': 'BTCUSDT', 'direction': 'long', 'strength': 0.90, 'price': 45000}),
        (1, 'alpha_engine', {'pair': 'BTCUSDT', 'signal': 'buy', 'confidence': 0.75, 'entry_price': 45200}),
        (2, 'mercury2', {'symbol': 'ETHUSDT', 'prob_up': 0.70, 'prob_down': 0.30, 'predicted_price': 3300}),
        (3, 'battleground', {'ticker': 'ETHUSDT', 'direction': 'long', 'strength': 0.85, 'price': 3250}),
        (4, 'alpha_engine', {'pair': 'SOLUSDT', 'signal': 'buy', 'confidence': 0.80, 'entry_price': 100}),
        (5, 'battleground', {'ticker': 'SOLUSDT', 'direction': 'short', 'strength': 0.70, 'price': 99}),
    ]
    
    print("\n[1] Simulating signal timeline...")
    print("\nTime | Source       | Symbol   | Direction | Strength")
    print("-" * 55)
    
    for time, source, signal in timeline:
        symbol = signal.get('ticker', signal.get('pair', signal.get('symbol')))
        direction = signal.get('direction', signal.get('signal', 'unknown'))
        strength = signal.get('strength', signal.get('confidence', 'N/A'))
        
        print(f"  {time}s | {source:12} | {symbol:8} | {direction:9} | {strength}")
        
        # Ingest signal
        router.ingest_signal(signal, source)
    
    print("\n[2] Resolving conflicts...")
    resolved = router.resolve_conflicts()
    print(f"    Resolved {len(resolved)} conflicts")
    
    print("\n[3] Final consensus:")
    output = router.output_consensus(output_path=None)
    
    for pick in output['picks']:
        print(f"    {pick['symbol']}: {pick['direction'].upper()}")
        print(f"      Sources: {', '.join(pick['sources'])}")
        print(f"      Agreement: {pick['agreement_ratio']:.0%}")


# =============================================================================
# RUN ALL EXAMPLES
# =============================================================================

def run_all_examples():
    """Run all usage examples"""
    
    examples = [
        example_basic_usage,
        example_conflict_resolution,
        example_database_consolidation,
        example_custom_adapter,
        example_batch_processing,
        example_priority_configuration,
        example_output_formats,
        example_realtime_simulation,
    ]
    
    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\nError in {example.__name__}: {e}")
    
    print("\n" + "=" * 60)
    print("ALL EXAMPLES COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_all_examples()
