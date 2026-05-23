"""Quick validation test for all 5 new coinglass strategies."""
import sys, json, logging
sys.path.insert(0, '.')
logging.basicConfig(level=logging.WARNING)

print('=== LIVE SIGNAL GENERATION TEST ===')
print('Testing each new strategy against BTCUSDT...')
print()

# Test calendar spread
from coinglass_strategies.strategies import calendar_spread
sig = calendar_spread.run('BTCUSDT', [], {})
if sig:
    d = sig.to_dict()
    print(f'S9-CalendarSpread: {d["direction"]} {d["symbol"]} conf={d["confidence"]}')
    print(f'  Reason: {d["reason"][:150]}')
else:
    print('S9-CalendarSpread: No signal (building basis history -- normal on first run)')
print()

# Test roll yield
from coinglass_strategies.strategies import roll_yield
sig = roll_yield.run('BTCUSDT', [], {})
if sig:
    d = sig.to_dict()
    print(f'S10-RollYield: {d["direction"]} {d["symbol"]} conf={d["confidence"]}')
    print(f'  Reason: {d["reason"][:150]}')
else:
    print('S10-RollYield: No signal (funding not persistent enough or insufficient data)')
print()

# Test options volatility
from coinglass_strategies.strategies import options_volatility
sig = options_volatility.run('BTCUSDT', [], {})
if sig:
    d = sig.to_dict()
    print(f'S11-OptionsVolatility: {d["direction"]} {d["symbol"]} conf={d["confidence"]}')
    print(f'  Reason: {d["reason"][:150]}')
else:
    print('S11-OptionsVolatility: No signal (IV not extreme or building history)')
print()

# Test news sentiment
from coinglass_strategies.strategies import news_sentiment
sig = news_sentiment.run('BTCUSDT', [], {})
if sig:
    d = sig.to_dict()
    print(f'S12-NewsSentiment: {d["direction"]} {d["symbol"]} conf={d["confidence"]}')
    print(f'  Reason: {d["reason"][:150]}')
else:
    print('S12-NewsSentiment: No signal (sentiment not extreme enough)')
print()

# Test risk parity
from coinglass_strategies.strategies import risk_parity
sig = risk_parity.run('BTCUSDT', [], {})
if sig:
    d = sig.to_dict()
    print(f'S13-RiskParity: {d["direction"]} {d["symbol"]} conf={d["confidence"]}')
    print(f'  Reason: {d["reason"][:150]}')
else:
    print('S13-RiskParity: No signal (risk-adjusted momentum not extreme enough)')
print()

print('=== All 5 strategies executed successfully ===')
