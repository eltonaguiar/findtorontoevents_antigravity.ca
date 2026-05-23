import os
import json
import sys
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from pathlib import Path

# API failover: never rely on a single Binance endpoint
try:
    from alpha_engine import api_failover
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from alpha_engine import api_failover

# --- Configuration ---
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "alpha_engine" / "data"
OUTPUT_FILE = DATA_DIR / "revival_picks.json"

# Relaxed Thresholds for Stalled Winners
STRATEGY_CONFIGS = {
    "st_atr_vol_breakout": {
        "original_atr": 0.03, "relaxed_atr": 0.015,
        "original_vol": 2.0, "relaxed_vol": 1.2,
        "dna_group_id": "dna_genome"
    },
    "st_fear_greed_contrarian": {
        "original_fg": 25, "relaxed_fg": 38,
        "dna_group_id": "dna_genome"
    },
    "drawdown_recovery_rsi": {
        "original_dd": 0.06, "relaxed_dd": 0.03,
        "original_rsi": 35, "relaxed_rsi": 42,
        "dna_group_id": "dna_genome"
    },
    "funding_momentum": {
        "original_funding": 0.0005, "relaxed_funding": 0.0003,
        "dna_group_id": "dna_genome"
    }
}

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "DOGEUSDT"]

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def fetch_fg_index():
    try:
        resp = requests.get("https://api.alternative.me/fng/", timeout=10)
        data = resp.json()
        return int(data['data'][0]['value'])
    except (requests.RequestException, ValueError, KeyError):
        return 50

def fetch_binance_data(symbol):
    """Fetch klines with api_failover (Binance mirrors + Bybit/KuCoin/CryptoCompare)."""
    try:
        data = api_failover.fetch_klines(symbol, interval="1d", limit=100)
        if not data:
            return None
        # Normalize: klines may have 6+ columns depending on source
        rows = [row[:6] for row in data]  # [ts, open, high, low, close, vol]
        df = pd.DataFrame(rows, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['vol'] = df['vol'].astype(float)
        return df
    except (requests.RequestException, ValueError, KeyError, IndexError):
        return None

def fetch_funding_rates():
    """Fetch funding rates with Binance fapi mirror rotation + Bybit fallback."""
    for base in api_failover.BINANCE_FAPI_BASES:
        try:
            resp = requests.get(f"{base}/fapi/v1/premiumIndex", timeout=10)
            if resp.status_code == 451:
                continue  # geo-blocked, try next mirror
            resp.raise_for_status()
            return {item['symbol']: float(item['lastFundingRate']) for item in resp.json() if 'USDT' in item['symbol']}
        except Exception:
            continue
    # All fapi mirrors failed - fall back to individual api_failover.fetch_funding_rate()
    rates = {}
    for sym in SYMBOLS:
        fr = api_failover.fetch_funding_rate(sym)
        if fr:
            rates[sym] = fr["rate"]
    return rates

def generate_picks():
    print(f"Starting Elite Strategy Revival at {_now_iso()}")
    fg = fetch_fg_index()
    funding = fetch_funding_rates()
    
    all_picks = []
    
    for symbol in SYMBOLS:
        df = fetch_binance_data(symbol)
        if df is None or len(df) < 30: continue
        
        current_price = df['close'].iloc[-1]
        prev_close = df['close'].iloc[-2]
        high = df['high'].iloc[-1]
        low = df['low'].iloc[-1]
        vol = df['vol'].iloc[-1]
        avg_vol = df['vol'].tail(20).mean()
        
        # 1. ATR Breakout (Relaxed)
        atr_14 = (df['high'] - df['low']).rolling(14).mean().iloc[-1]
        atr_pct = atr_14 / current_price
        vol_ratio = vol / avg_vol
        
        conf = 0.0
        if atr_pct > 0.015 and vol_ratio > 1.2:
            signal_type = "BUY" if current_price > prev_close else "SELL"
            all_picks.append({
                "id": f"revival_atr_{symbol}_{int(time.time())}",
                "strategy": "st_atr_vol_breakout (Revival)",
                "dna_group_id": "dna_genome",
                "symbol": symbol,
                "signal_type": signal_type,
                "entry_price": current_price,
                "take_profit": current_price * (1.03 if signal_type == "BUY" else 0.97),
                "stop_loss": current_price * (0.985 if signal_type == "BUY" else 1.015),
                "confidence": 0.75,
                "reason": f"Relaxed ATR Breakout: ATR={atr_pct:.2%}, Vol={vol_ratio:.1f}x",
                "timestamp": _now_iso()
            })

        # 2. Fear & Greed Contrarian (Relaxed)
        if fg < 38:
            all_picks.append({
                "id": f"revival_fg_{symbol}_{int(time.time())}",
                "strategy": "st_fear_greed_contrarian (Revival)",
                "dna_group_id": "dna_genome",
                "symbol": symbol,
                "signal_type": "BUY",
                "entry_price": current_price,
                "take_profit": current_price * 1.04,
                "stop_loss": current_price * 0.97,
                "confidence": 0.78,
                "reason": f"Relaxed F&G Contrarian: F&G={fg} (Extreme Fear territory)",
                "timestamp": _now_iso()
            })

        # 3. Drawdown Recovery (Relaxed)
        high_50 = df['high'].tail(50).max()
        dd = (current_price / high_50) - 1.0
        if dd < -0.03: # 3% drawdown
            all_picks.append({
                "id": f"revival_dd_{symbol}_{int(time.time())}",
                "strategy": "drawdown_recovery_rsi (Revival)",
                "dna_group_id": "dna_genome",
                "symbol": symbol,
                "signal_type": "BUY",
                "entry_price": current_price,
                "take_profit": current_price * 1.05,
                "stop_loss": current_price * 0.96,
                "confidence": 0.72,
                "reason": f"Relaxed Drawdown: DD={dd:.1%}, High50={high_50:.2f}",
                "timestamp": _now_iso()
            })

        # 4. Funding Momentum (Relaxed)
        fr = funding.get(symbol, 0)
        if abs(fr) > 0.0003:
            signal_type = "SELL" if fr > 0 else "BUY"
            all_picks.append({
                "id": f"revival_funding_{symbol}_{int(time.time())}",
                "strategy": "funding_momentum (Revival)",
                "dna_group_id": "dna_genome",
                "symbol": symbol,
                "signal_type": signal_type,
                "entry_price": current_price,
                "take_profit": current_price * (1.02 if signal_type == "BUY" else 0.98),
                "stop_loss": current_price * (0.985 if signal_type == "BUY" else 1.015),
                "confidence": 0.80,
                "reason": f"Relaxed Funding: FR={fr*100:.4f}%",
                "timestamp": _now_iso()
            })

    # Save to file
    payload = {
        "generated_at": _now_iso(),
        "picks": all_picks
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(payload, f, indent=4)
    
    print(f"Saved {len(all_picks)} revival picks to {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_picks()
