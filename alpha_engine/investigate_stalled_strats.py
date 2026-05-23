import json
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Config
DATA_DIR = Path("e:/findtorontoevents_antigravity.ca/alpha_engine/data")
PERF_PATH = DATA_DIR / "strategy_performance.json"
ACTIVE_PATH = DATA_DIR / "active_picks.json"
CLOSED_PATH = DATA_DIR / "closed_picks.json"

def fetch_price(symbol):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    try:
        r = requests.get(url, timeout=5)
        return float(r.json()['price'])
    except: return None

def fetch_rsi(symbol, interval="1h"):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit=100"
    try:
        r = requests.get(url, timeout=5)
        klines = r.json()
        closes = [float(k[4]) for k in klines]
        # Simple RSI
        period = 14
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas[-period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-period:]]
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0: return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))
    except: return None

def investigate():
    print("--- STALLED STRATEGY INVESTIGATION ---")
    with open(PERF_PATH, "r") as f:
        perf = json.load(f)
    
    with open(ACTIVE_PATH, "r") as f:
        active = json.load(f)
    active_strats = set([p.get('strategy') for p in active])

    targets = []
    for strat, data in perf.items():
        if data.get('win_rate', 0) > 0.8 and data.get('closed_picks', 0) >= 3:
            if strat not in active_strats:
                targets.append(strat)

    print(f"High-WR Stalled Targets: {targets}")
    
    for strat in targets:
        symbol = strat.split("_")[2] if "ml_enhanced" in strat else None
        if not symbol: continue
        
        # Get current RSI and Price
        rsi = fetch_rsi(symbol)
        price = fetch_price(symbol)
        
        print(f"\nTarget: {strat} ({symbol})")
        print(f"  Current Price: {price}")
        print(f"  Current RSI(1h): {rsi}")
        
        # Check against standard ml_strategy_reviver filters
        # RSI range 30-65
        if rsi is not None:
            if rsi > 65:
                print(f"  BLOCKED: RSI {rsi:.1f} > 65 (Overbought)")
            elif rsi < 30:
                print(f"  BLOCKED: RSI {rsi:.1f} < 30 (Oversold - though reviver allows this sometimes)")
            else:
                print(f"  PASSED: RSI {rsi:.1f} is within 30-65 range.")
        
        # Note: Reviver also checks EMA trend
        print(f"  Conclusion: Strategy is inactive likely due to technical filter misalignment in current market regime.")

if __name__ == "__main__":
    investigate()
