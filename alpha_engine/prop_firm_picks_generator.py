#!/usr/bin/env python3
"""
Prop Firm Picks Generator
=========================
Runs prop firm strategies and outputs active picks to JSON for audit dashboard.

Usage: python -m alpha_engine.prop_firm_picks_generator
"""

import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import numpy as np

# Import our prop firm strategies
from new_strategies_prop_firm import (
    KeltnerCompressionScalper,
    VWAPMeanReversionElite,
    MultiTimeframeRSIConfluence
)
from new_strategies_general import (
    FlashCrashReversalHunter,
    FundingRateMomentumPro,
    BollingerSqueezeBreakout
)

# Data directory
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "prop_firm_picks"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Crypto pairs to scan
CRYPTO_PAIRS = [
    'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT',
    'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'LINKUSDT', 'LTCUSDT'
]


def fetch_data(symbols):
    """Fetch data from Binance or use cached data (with endpoint failover)."""
    _SPOT_BASES = [
        "https://api.binance.com", "https://api1.binance.com",
        "https://data-api.binance.vision", "https://api.binance.us",
    ]
    data = {}
    for symbol in symbols:
        try:
            import requests
            response = None
            for _base in _SPOT_BASES:
                url = f"{_base}/api/v3/klines?symbol={symbol}&interval=1h&limit=100"
                response = requests.get(url, timeout=10)
                if response.status_code not in (451, 403):
                    break
            if response is None:
                continue
            response.raise_for_status()
            
            df_data = response.json()
            df = pd.DataFrame(df_data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
            
            data[symbol] = df
        except Exception as e:
            print(f"  Error fetching {symbol}: {e}")
            continue
    
    return data


def generate_picks():
    """Generate picks from all prop firm strategies."""
    print("=" * 70)
    print("PROP FIRM PICKS GENERATOR")
    print("=" * 70)
    print()
    
    # Fetch data
    print("Fetching market data...")
    data = fetch_data(CRYPTO_PAIRS)
    if not data:
        print("ERROR: No data fetched")
        return
    print(f"  Loaded {len(data)} pairs")
    print()
    
    all_picks = []
    
    # Strategy 1: KC_SCALP_v1
    print("Running KC_SCALP_v1...")
    try:
        kc = KeltnerCompressionScalper()
        kc_picks = kc.generate_signals(data, list(data.keys())[0] if data else "BTCUSDT")
        for pick in kc_picks:
            all_picks.append({
                "symbol": pick.symbol,
                "direction": pick.signal_type.value,
                "entry_price": pick.entry_price,
                "take_profit": pick.take_profit,
                "stop_loss": pick.stop_loss,
                "confidence": pick.confidence,
                "strategy": "KC_SCALP_v1",
                "timestamp": pick.timestamp.isoformat(),
                "metadata": pick.metadata
            })
        print(f"  Generated {len(kc_picks)} picks")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Strategy 2: MTF_RSI_v1
    print("Running MTF_RSI_v1...")
    try:
        mtf = MultiTimeframeRSIConfluence()
        mtf_picks = mtf.generate_signals(data, list(data.keys())[0] if data else "BTCUSDT")
        for pick in mtf_picks:
            all_picks.append({
                "symbol": pick.symbol,
                "direction": pick.signal_type.value,
                "entry_price": pick.entry_price,
                "take_profit": pick.take_profit,
                "stop_loss": pick.stop_loss,
                "confidence": pick.confidence,
                "strategy": "MTF_RSI_v1",
                "timestamp": pick.timestamp.isoformat(),
                "metadata": pick.metadata
            })
        print(f"  Generated {len(mtf_picks)} picks")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Strategy 3: VWAP_ELITE_v1
    print("Running VWAP_ELITE_v1...")
    try:
        vwap = VWAPMeanReversionElite()
        vwap_picks = vwap.generate_signals(data, list(data.keys())[0] if data else "BTCUSDT")
        for pick in vwap_picks:
            all_picks.append({
                "symbol": pick.symbol,
                "direction": pick.signal_type.value,
                "entry_price": pick.entry_price,
                "take_profit": pick.take_profit,
                "stop_loss": pick.stop_loss,
                "confidence": pick.confidence,
                "strategy": "VWAP_ELITE_v1",
                "timestamp": pick.timestamp.isoformat(),
                "metadata": pick.metadata
            })
        print(f"  Generated {len(vwap_picks)} picks")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Strategy 4: FLASH_REV_v1
    print("Running FLASH_REV_v1...")
    try:
        flash = FlashCrashReversalHunter()
        flash_picks = flash.generate_signals(data, list(data.keys())[0] if data else "BTCUSDT")
        for pick in flash_picks:
            all_picks.append({
                "symbol": pick['symbol'],
                "direction": pick['signal_type'],
                "entry_price": pick['entry_price'],
                "take_profit": pick['take_profit'],
                "stop_loss": pick['stop_loss'],
                "confidence": pick['confidence'],
                "strategy": "FLASH_REV_v1",
                "timestamp": pick['timestamp'].isoformat(),
                "metadata": pick['metadata']
            })
        print(f"  Generated {len(flash_picks)} picks")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Strategy 5: FUNDING_PRO_v1
    print("Running FUNDING_PRO_v1...")
    try:
        fund = FundingRateMomentumPro()
        fund_picks = fund.generate_signals(data, list(data.keys())[0] if data else "BTCUSDT")
        for pick in fund_picks:
            all_picks.append({
                "symbol": pick['symbol'],
                "direction": pick['signal_type'],
                "entry_price": pick['entry_price'],
                "take_profit": pick['take_profit'],
                "stop_loss": pick['stop_loss'],
                "confidence": pick['confidence'],
                "strategy": "FUNDING_PRO_v1",
                "timestamp": pick['timestamp'].isoformat(),
                "metadata": pick['metadata']
            })
        print(f"  Generated {len(fund_picks)} picks")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Strategy 6: BB_SQUEEZE_v1
    print("Running BB_SQUEEZE_v1...")
    try:
        bb = BollingerSqueezeBreakout()
        bb_picks = bb.generate_signals(data, list(data.keys())[0] if data else "BTCUSDT")
        for pick in bb_picks:
            all_picks.append({
                "symbol": pick['symbol'],
                "direction": pick['signal_type'],
                "entry_price": pick['entry_price'],
                "take_profit": pick['take_profit'],
                "stop_loss": pick['stop_loss'],
                "confidence": pick['confidence'],
                "strategy": "BB_SQUEEZE_v1",
                "timestamp": pick['timestamp'].isoformat(),
                "metadata": pick['metadata']
            })
        print(f"  Generated {len(bb_picks)} picks")
    except Exception as e:
        print(f"  Error: {e}")
    
    print()
    print("=" * 70)
    print(f"TOTAL PICKS: {len(all_picks)}")
    print("=" * 70)
    
    # Save to JSON
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy_type": "prop_firm",
        "total_picks": len(all_picks),
        "picks": all_picks
    }
    
    output_file = DATA_DIR / "active_picks.json"
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n[OK] Saved to: {output_file}")
    
    # Also save to audit_trail data directory for dashboard
    audit_data_dir = Path(__file__).resolve().parent.parent / "audit_trail" / "data"
    audit_data_dir.mkdir(parents=True, exist_ok=True)
    audit_file = audit_data_dir / "prop_firm_picks.json"
    with open(audit_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"[OK] Saved to: {audit_file}")
    
    return all_picks


if __name__ == "__main__":
    generate_picks()
