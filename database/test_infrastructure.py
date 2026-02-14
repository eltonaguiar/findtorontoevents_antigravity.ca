#!/usr/bin/env python3
"""
================================================================================
TEST DATABASE INFRASTRUCTURE
================================================================================
"""

import time
import random
from multi_db_manager import manager
from unified_interface import TradingDB


def test_ohlcv():
    """Test OHLCV operations"""
    print("\n[TEST] OHLCV Operations")
    print("-" * 40)
    
    db = TradingDB()
    ts = int(time.time())
    
    # Insert sample OHLCV
    success = db.save_ohlcv('BTC', '1h', ts, 69000, 69500, 68800, 69200, 1500.5)
    print(f"  Insert BTC OHLCV: {'OK' if success else 'FAIL'}")
    
    # Query back
    data = db.get_ohlcv('BTC', '1h', limit=5)
    print(f"  Query returned: {len(data)} rows")
    if data:
        print(f"  Latest close: ${data[0]['close']:,.2f}")
    
    return len(data) > 0


def test_signals():
    """Test signal operations"""
    print("\n[TEST] Signal Operations")
    print("-" * 40)
    
    db = TradingDB()
    ts = int(time.time())
    
    # Create signal
    signal_id = f"TEST_{ts}"
    success = db.save_signal(
        signal_id=signal_id,
        symbol='BTC',
        signal_type='buy',
        entry_price=69200,
        target_price=72000,
        stop_loss=67000,
        confidence=0.85,
        strategy='extreme_test'
    )
    print(f"  Create signal: {'OK' if success else 'FAIL'}")
    
    # Query active signals
    signals = db.get_active_signals()
    print(f"  Active signals: {len(signals)}")
    
    return success


def test_patterns():
    """Test pattern storage"""
    print("\n[TEST] Pattern Storage")
    print("-" * 40)
    
    db = TradingDB()
    ts = int(time.time())
    
    # Save pattern
    success = db.save_pattern(
        symbol='BTC',
        pattern_type='bull_flag',
        pattern_name='Bull Flag on 1H',
        timeframe='1h',
        start_ts=ts - 3600,
        end_ts=ts,
        confidence=0.82,
        price=69200,
        target=72000,
        stop_loss=67000,
        embedding=[0.1, 0.2, 0.3, 0.4, 0.5]
    )
    print(f"  Save pattern: {'OK' if success else 'FAIL'}")
    
    # Query patterns
    patterns = db.find_patterns('BTC', min_confidence=0.8)
    print(f"  Patterns found: {len(patterns)}")
    
    return success


def test_ml_models():
    """Test ML model registry"""
    print("\n[TEST] ML Model Registry")
    print("-" * 40)
    
    db = TradingDB()
    
    # Register model
    success = db.register_model(
        model_name='xgboost_v1',
        version='1.0.0',
        model_type='xgboost',
        asset_class='crypto',
        accuracy=0.823,
        features=['rsi', 'macd', 'ema_cross', 'volume_profile', 'bb_width'],
        hyperparameters={'lr': 0.001, 'depth': 6, 'rounds': 100}
    )
    print(f"  Register model: {'OK' if success else 'FAIL'}")
    
    # Get active model
    model = db.get_active_model('xgboost_v1')
    if model:
        print(f"  Model found: {model['model_name']} v{model['model_version']}")
        print(f"  Accuracy: {model['accuracy']:.1%}")
    
    return success


def test_batch_insert():
    """Test batch OHLCV insert"""
    print("\n[TEST] Batch Insert Performance")
    print("-" * 40)
    
    db = TradingDB()
    ts = int(time.time())
    
    # Generate 100 candles
    data = []
    base_price = 69000
    for i in range(100):
        price = base_price + random.randint(-500, 500)
        data.append((
            ts - (i * 3600),
            price - 50,
            price + 100,
            price - 100,
            price,
            random.randint(1000, 2000)
        ))
    
    start = time.time()
    count = db.save_ohlcv_batch('ETH', '1h', data)
    elapsed = time.time() - start
    
    print(f"  Inserted: {count} rows")
    print(f"  Time: {elapsed:.2f}s ({count/elapsed:.0f} rows/sec)")
    
    return count == len(data)


def show_stats():
    """Show database statistics"""
    print("\n[STATS] Database Statistics")
    print("-" * 40)
    
    stats = TradingDB().get_database_stats()
    
    for db_name, db_stats in stats.items():
        if 'error' in db_stats:
            print(f"  {db_name}: ERROR - {db_stats['error']}")
        else:
            print(f"  {db_name}: {db_stats['tables']} tables, {db_stats['total_rows']:,} rows")


def main():
    print("=" * 60)
    print("DATABASE INFRASTRUCTURE TEST")
    print("=" * 60)
    
    results = []
    
    try:
        results.append(("OHLCV", test_ohlcv()))
        results.append(("Signals", test_signals()))
        results.append(("Patterns", test_patterns()))
        results.append(("ML Models", test_ml_models()))
        results.append(("Batch Insert", test_batch_insert()))
        
        show_stats()
        
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        for name, passed in results:
            status = "PASS" if passed else "FAIL"
            print(f"  {name}: {status}")
        
        all_passed = all(r[1] for r in results)
        print("\n" + ("ALL TESTS PASSED" if all_passed else "SOME TESTS FAILED"))
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
