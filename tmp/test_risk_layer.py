"""
Test the new risk layer modules against cached OHLCV data.
Tests: VPIN detector, position sizer, exchange flow strategies.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from pathlib import Path

# Load cached OHLCV data
cache_dir = Path("genome/data/ohlcv_cache")
npz_files = sorted(cache_dir.glob("*.npz"))

data = {}
for f in npz_files:
    symbol = f.stem.split("_")[0]
    arr = np.load(f)
    cols = ["Open", "High", "Low", "Close", "Volume"]
    df = pd.DataFrame({c: arr[c] for c in cols if c in arr.files})
    if len(df) > 100:
        data[symbol] = df

print(f"Loaded {len(data)} symbols from cache\n")

# Test 1: VPIN Detector
print("=" * 60)
print("TEST 1: VPIN Detector")
print("=" * 60)
try:
    from alpha_engine.vpin_detector import vpin_alert
    alerts = vpin_alert(data)
    print(f"  VPIN alerts generated: {len(alerts)}")
    for a in alerts[:5]:
        print(f"  - {a.get('symbol', '?')}: Z={a.get('vpin_zscore', '?'):.2f}, "
              f"action={a.get('direction', '?')}, conf={a.get('confidence', '?'):.2f}")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 2: Position Sizer
print("\n" + "=" * 60)
print("TEST 2: Position Sizer")
print("=" * 60)
try:
    from alpha_engine.position_sizer import PositionSizer
    sizer = PositionSizer()

    # Create mock signals to size
    mock_signals = [
        {"symbol": "BTCUSDT", "direction": "BUY", "confidence": 0.65, "entry_price": 70000,
         "take_profit": 77000, "stop_loss": 67000, "strategy": "test"},
        {"symbol": "ETHUSDT", "direction": "BUY", "confidence": 0.55, "entry_price": 3500,
         "take_profit": 3850, "stop_loss": 3350, "strategy": "test"},
    ]

    sized = sizer.size_signals(mock_signals, data)
    print(f"  Signals sized: {len(sized)}")
    for s in sized:
        regime = s.get("regime", "?")
        mult = s.get("size_multiplier", "?")
        print(f"  - {s['symbol']}: regime={regime}, multiplier={mult}")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 3: Exchange Flow Strategies
print("\n" + "=" * 60)
print("TEST 3: Exchange Flow Strategies")
print("=" * 60)
try:
    from alpha_engine.exchange_flow_strategies import exchange_reserve_decline
    signals = exchange_reserve_decline(data)
    print(f"  Exchange flow signals: {len(signals)}")
    for s in signals[:5]:
        print(f"  - {s.get('symbol', '?')}: {s.get('direction', '?')}, "
              f"conf={s.get('confidence', '?'):.2f}, {s.get('rationale', '?')[:60]}")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 4: Confluence Pipeline
print("\n" + "=" * 60)
print("TEST 4: Confluence Pipeline")
print("=" * 60)
try:
    from alpha_engine.confluence_pipeline import filter_signals_through_pipeline
    # Use the exchange flow signals as input (or mock some)
    test_signals = [
        {"symbol": "BTCUSDT", "direction": "BUY", "confidence": 0.65, "entry_price": 70000,
         "take_profit": 77000, "stop_loss": 67000, "strategy": "test_strat", "category": "crypto"},
        {"symbol": "ETHUSDT", "direction": "BUY", "confidence": 0.55, "entry_price": 3500,
         "take_profit": 3850, "stop_loss": 3350, "strategy": "test_strat", "category": "crypto"},
    ]
    filtered = filter_signals_through_pipeline(test_signals, data, min_score=30.0)
    print(f"  Input signals: {len(test_signals)}, After pipeline: {len(filtered)}")
    for s in filtered:
        print(f"  - {s.get('symbol', '?')}: score={s.get('confluence_score', '?')}")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 5: Regime Router
print("\n" + "=" * 60)
print("TEST 5: Regime Router")
print("=" * 60)
try:
    from alpha_engine.regime_router import RegimeRouter
    router = RegimeRouter()
    summary = router.summarize(data)
    print(f"  Symbols classified: {len(summary)}")
    for sym, info in list(summary.items())[:5]:
        print(f"  - {sym}: {info.get('trend', '?')} x {info.get('volatility', '?')} = {info.get('cell', '?')}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n" + "=" * 60)
print("ALL TESTS COMPLETE")
print("=" * 60)
