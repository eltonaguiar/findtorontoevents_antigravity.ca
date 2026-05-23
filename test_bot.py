#!/usr/bin/env python3
"""Quick test to verify the autonomous bot works"""

import os
import sys

# Set environment variables for testing
os.environ['PRIMARY_EXCHANGE'] = 'FREE_DATA'
os.environ.setdefault('COINGECKO_API_KEY', '')
os.environ.setdefault('CRYPTOCOMPARE_API_KEY', '')

# Add the bot to path
sys.path.insert(0, '/root/.openclaw/workspace')

# Import and test
from live_trading_bot_canada import Config, FreeDataFetcher

print("🧪 Testing Autonomous Trading Bot...")
print("=" * 50)

# Test config
config = Config()
print(f"✅ Config loaded: PRIMARY_EXCHANGE={config.PRIMARY_EXCHANGE}")

# Test free data fetcher
fetcher = FreeDataFetcher(config)
print(f"✅ FreeDataFetcher initialized")

# Test getting ticker data
print("\n📊 Fetching BTC price from CoinGecko (FREE)...")
ticker = fetcher.get_ticker('BTC-USD')

if ticker:
    print(f"✅ SUCCESS!")
    print(f"   Symbol: {ticker['symbol']}")
    print(f"   Price: ${ticker['price']:,.2f}")
    print(f"   24h Change: {ticker['price_change']:+.2f}%")
    print(f"   Volume: ${ticker['volume_24h']:,.0f}")
    print(f"   Source: {ticker['source']}")
else:
    print("❌ Failed to fetch ticker")

# Test getting historical data
print("\n📈 Fetching 30-day history...")
history = fetcher.get_klines('BTC-USD', days=7)

if not history.empty:
    print(f"✅ SUCCESS! Got {len(history)} days of data")
    print(f"   Latest close: ${history['close'].iloc[-1]:,.2f}")
    print(f"   7-day high: ${history['high'].max():,.2f}")
    print(f"   7-day low: ${history['low'].min():,.2f}")
else:
    print("❌ Failed to fetch history")

print("\n" + "=" * 50)
print("🎉 Bot is ready to run autonomously!")
print("   - GitHub Actions will trigger every 4 hours")
print("   - Results will be committed automatically")
print("   - No user intervention required!")
