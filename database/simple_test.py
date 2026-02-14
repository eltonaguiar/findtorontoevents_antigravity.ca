#!/usr/bin/env python3
from unified_interface import TradingDB
import time

db = TradingDB()
ts = int(time.time())

print("Testing OHLCV...")
ok = db.save_ohlcv('BTC', '1h', ts, 69000, 69500, 68800, 69200, 1500.5)
print(f"  Insert: {'OK' if ok else 'FAIL'}")

data = db.get_ohlcv('BTC', '1h', limit=2)
print(f"  Query: {len(data)} rows")

print("Testing Signals...")
ok = db.save_signal(f'TEST_{ts}', 'BTC', 'buy', 69200, target_price=72000, stop_loss=67000)
print(f"  Create: {'OK' if ok else 'FAIL'}")

print("Testing Patterns...")
ok = db.save_pattern('BTC', 'bull_flag', 'Test Pattern', '1h', ts-3600, ts, 0.85, 69200)
print(f"  Save: {'OK' if ok else 'FAIL'}")

print("Testing ML Models...")
ok = db.register_model('test_model', '1.0', 'test', 'crypto', 0.85, ['rsi', 'macd'])
print(f"  Register: {'OK' if ok else 'FAIL'}")

print("\nALL TESTS COMPLETE")
