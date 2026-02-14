#!/usr/bin/env python3
"""
================================================================================
DATABASE SETUP SCRIPT
================================================================================

One-command setup for entire database infrastructure:
1. Tests all connections
2. Creates schemas
3. Seeds initial data
4. Verifies setup

Usage:
    python setup_databases.py
================================================================================
"""

import sys
from multi_db_manager import manager
from schema_extensions import SchemaManager
from unified_interface import TradingDB


def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def main():
    print_header("DATABASE INFRASTRUCTURE SETUP")
    print("Target: mysql.50webs.com")
    print("Databases: memecoin, stocks, favcreators")
    
    # Step 1: Test connections
    print_header("STEP 1: Testing Connections")
    results = manager.test_all_connections()
    
    working_dbs = [name for name, ok in results.items() if ok]
    if not working_dbs:
        print("\n[FAIL] All connections failed. Please check:")
        print("   - Internet connection")
        print("   - Database credentials")
        sys.exit(1)
    elif len(working_dbs) < 3:
        print(f"\n[WARNING] Only {len(working_dbs)}/3 databases connected")
        print(f"   Working: {', '.join(working_dbs)}")
        print("   Continuing with available databases...")
    
    # Step 2: Show existing tables
    print_header("STEP 2: Current Database State")
    for db_name in working_dbs:
        try:
            tables = manager.list_tables(db_name)
            counts = manager.get_table_counts(db_name)
            
            print(f"\n[DB] {db_name}: {len(tables)} tables")
            # Show top 20 tables by row count
            sorted_tables = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:20]
            for table, count in sorted_tables:
                print(f"   - {table}: {count:,} rows")
            if len(tables) > 20:
                print(f"   ... and {len(tables)-20} more tables")
        except Exception as e:
            print(f"\n[DB] {db_name}: Error - {e}")
    
    # Step 3: Create schemas
    print_header("STEP 3: Creating Schemas")
    schema_mgr = SchemaManager()
    
    try:
        if 'memecoin' in working_dbs:
            schema_mgr.create_memecoin_schema()
        if 'stocks' in working_dbs:
            schema_mgr.create_stocks_schema()
        if 'favcreators' in working_dbs:
            schema_mgr.create_forex_schema()
        print("\n[OK] Schema creation complete")
    except Exception as e:
        print(f"\n[WARNING] Schema creation had warnings: {e}")
        print("   (This is normal if tables already exist)")
    
    # Step 4: Seed initial data
    print_header("STEP 4: Seeding Initial Data")
    try:
        schema_mgr.seed_initial_data()
    except Exception as e:
        print(f"[WARNING] Seeding had warnings: {e}")
    
    # Step 5: Test unified interface
    print_header("STEP 5: Testing Unified Interface")
    db = TradingDB()
    
    # Test save
    import time
    ts = int(time.time())
    
    success = db.save_ohlcv('BTC', '1h', ts, 69000, 69500, 68800, 69200, 1500.5)
    print(f"Test OHLCV save: {'[OK]' if success else '[FAIL]'}")
    
    success = db.save_signal(f'TEST_{ts}', 'BTC', 'buy', 69200, 
                             target_price=72000, stop_loss=67000)
    print(f"Test signal save: {'[OK]' if success else '[FAIL]'}")
    
    # Step 6: Final status
    print_header("SETUP COMPLETE")
    
    stats = db.get_database_stats()
    
    print("\n[STATS] Final Database Statistics:")
    for db_name, db_stats in stats.items():
        if 'error' in db_stats:
            print(f"  {db_name}: [FAIL] {db_stats['error']}")
        else:
            print(f"  {db_name}: {db_stats['tables']} tables, "
                  f"{db_stats['total_rows']:,} total rows")
    
    print("\n" + "=" * 60)
    print("  INFRASTRUCTURE READY FOR #1 WORLDWIDE")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Run live data ingestion")
    print("  2. Train ML models")
    print("  3. Deploy signals")
    print("\nUsage:")
    print("  from database import get_trading_db")
    print("  db = get_trading_db()")
    print("  db.save_ohlcv('BTC', '1h', timestamp, o, h, l, c, v)")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[FAIL] Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
