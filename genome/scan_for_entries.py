#!/usr/bin/env python3
"""
Scan broader symbol universe for KIMI Top Picks entry opportunities.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from genome.mutation_lab.innovative_mutations import fetch_binance_klines
from genome.kimi_top_picks_automation import williams_r_indicator
import pandas as pd

def get_reason(pick):
    if pick['signal_type'] == 'OVERSOLD_LONG':
        return f"Williams %R at {pick['wr']:.1f} is oversold (below -80) while price remains above 200 SMA. Mean reversion setup with high probability bounce expected."
    elif pick['signal_type'] == 'OVERBOUGHT_SHORT':
        return f"Williams %R at {pick['wr']:.1f} is overbought (above -20) with price below 200 SMA. Bearish momentum continuation expected."
    elif pick['signal_type'] == 'COMPRESSION':
        return f"Price compressed near 200 SMA with low volatility ({pick['atr_pct']:.2f}% ATR). Breakout imminent."
    return "Technical setup based on momentum and trend analysis."

# Extended symbol list
SYMBOLS = [
    # Tier 1 Majors
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    # Tier 2 Alts
    "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "DOGEUSDT",
    "NEARUSDT", "SUIUSDT", "APTUSDT", "INJUSDT", "ATOMUSDT",
    # Tier 3 Higher Vol
    "SEIUSDT", "TIAUSDT", "FETUSDT", "OPUSDT", "ARBUSDT",
    "STXUSDT", "IMXUSDT", "GRTUSDT", "LDOUSDT", "RNDRUSDT",
]

print("="*70)
print("KIMI TOP PICKS - EXTENDED SYMBOL SCAN")
print("="*70)
print(f"Scanning {len(SYMBOLS)} symbols for entry opportunities...")
print()

candidates = []

for symbol in SYMBOLS:
    try:
        df = fetch_binance_klines(symbol, '1h', limit=200)
        if df.empty or len(df) < 50:
            continue
        
        close = df['Close']
        current = close.iloc[-1]
        
        # Skip very low prices (noise)
        if current < 0.01:
            continue
        
        # Williams %R
        wr = williams_r_indicator(close).iloc[-1]
        
        # 200 SMA
        sma_200 = close.rolling(200).mean().iloc[-1]
        above_sma = current > sma_200
        
        # ATR
        atr_val = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
        atr_pct = atr_val / current * 100
        
        # Check for entry conditions
        # Condition 1: Williams %R oversold + above SMA (mean reversion)
        if wr < -80 and above_sma:
            candidates.append({
                'symbol': symbol,
                'strategy': 'Williams %R Mean Reversion',
                'direction': 'LONG',
                'price': current,
                'wr': wr,
                'sma_200': sma_200,
                'atr_pct': atr_pct,
                'signal_type': 'OVERSOLD_LONG',
                'strength': abs(wr + 80),  # How far below -80
            })
        
        # Condition 2: Williams %R overbought + below SMA (short)
        elif wr > -20 and not above_sma:
            candidates.append({
                'symbol': symbol,
                'strategy': 'Williams %R Mean Reversion',
                'direction': 'SHORT',
                'price': current,
                'wr': wr,
                'sma_200': sma_200,
                'atr_pct': atr_pct,
                'signal_type': 'OVERBOUGHT_SHORT',
                'strength': abs(wr + 20),
            })
        
        # Condition 3: Near SMA with low volatility (breakout setup)
        elif abs((current - sma_200) / sma_200) < 0.02 and atr_pct < 3:
            candidates.append({
                'symbol': symbol,
                'strategy': 'SMA Compression Breakout',
                'direction': 'LONG' if above_sma else 'SHORT',
                'price': current,
                'wr': wr,
                'sma_200': sma_200,
                'atr_pct': atr_pct,
                'signal_type': 'COMPRESSION',
                'strength': 50,  # Neutral
            })
        
    except Exception as e:
        continue

print(f"Found {len(candidates)} potential candidates")
print()

# Sort by signal strength
candidates.sort(key=lambda x: x['strength'], reverse=True)

# Display top 10
print("TOP 10 ENTRY OPPORTUNITIES:")
print("-"*70)

for i, c in enumerate(candidates[:10], 1):
    direction_str = "[LONG]" if c['direction'] == 'LONG' else "[SHORT]"
    signal_str = {
        'OVERSOLD_LONG': '[OVERSOLD]',
        'OVERBOUGHT_SHORT': '[OVERBOUGHT]',
        'COMPRESSION': '[COMPRESSION]',
    }.get(c['signal_type'], '[?]')
    
    print(f"\n{i}. {c['symbol']} {direction_str}")
    print(f"   Signal: {signal_str}")
    print(f"   Price: ${c['price']:,.4f}" if c['price'] < 1 else f"   Price: ${c['price']:,.2f}")
    print(f"   Williams %R: {c['wr']:.1f}")
    print(f"   200 SMA: ${c['sma_200']:,.2f}")
    print(f"   ATR: {c['atr_pct']:.2f}%")
    print(f"   Strength Score: {c['strength']:.1f}")
    
    # Calculate TP/SL
    if c['direction'] == 'LONG':
        tp = c['price'] * 1.04
        sl = c['price'] * 0.97
    else:
        tp = c['price'] * 0.96
        sl = c['price'] * 1.03
    
    print(f"   Suggested TP: ${tp:,.2f} | SL: ${sl:,.2f}")

print("\n" + "="*70)

# Pick top 2 for addition to portfolio
if len(candidates) >= 2:
    top_2 = candidates[:2]
    
    print("\n*** TOP 2 RECOMMENDATIONS FOR PORTFOLIO ***")
    print("="*70)
    
    for i, pick in enumerate(top_2, 4):  # Continue from #4
        direction_str = "LONG" if pick['direction'] == 'LONG' else "SHORT"
        
        if pick['direction'] == 'LONG':
            tp = pick['price'] * 1.04
            sl = pick['price'] * 0.97
        else:
            tp = pick['price'] * 0.96
            sl = pick['price'] * 1.03
        
        print(f"\n### PICK #{i}: {pick['symbol']} - [{direction_str}]")
        print(f"**Strategy:** {pick['strategy']}")
        print(f"**Direction:** **{direction_str}** (explicit)")
        print(f"**Entry Price:** ${pick['price']:,.4f}" if pick['price'] < 1 else f"**Entry Price:** ${pick['price']:,.2f}")
        print(f"**Take Profit:** ${tp:,.2f}")
        print(f"**Stop Loss:** ${sl:,.2f}")
        print(f"**Williams %R:** {pick['wr']:.1f}")
        print(f"**Signal Type:** {pick['signal_type']}")
        print(f"**Reason:** {get_reason(pick)}")
    
    # Save top 2 to file for chatwithit.md
    output = {
        'timestamp': pd.Timestamp.now().isoformat(),
        'picks_4_and_5': [
            {
                'rank': 4,
                'symbol': top_2[0]['symbol'],
                'direction': top_2[0]['direction'],
                'entry': round(top_2[0]['price'], 4 if top_2[0]['price'] < 1 else 2),
                'tp': round(top_2[0]['price'] * 1.04 if top_2[0]['direction'] == 'LONG' else top_2[0]['price'] * 0.96, 4 if top_2[0]['price'] < 1 else 2),
                'sl': round(top_2[0]['price'] * 0.97 if top_2[0]['direction'] == 'LONG' else top_2[0]['price'] * 1.03, 4 if top_2[0]['price'] < 1 else 2),
                'wr': round(top_2[0]['wr'], 1),
                'reason': get_reason(top_2[0]),
            },
            {
                'rank': 5,
                'symbol': top_2[1]['symbol'],
                'direction': top_2[1]['direction'],
                'entry': round(top_2[1]['price'], 4 if top_2[1]['price'] < 1 else 2),
                'tp': round(top_2[1]['price'] * 1.04 if top_2[1]['direction'] == 'LONG' else top_2[1]['price'] * 0.96, 4 if top_2[1]['price'] < 1 else 2),
                'sl': round(top_2[1]['price'] * 0.97 if top_2[1]['direction'] == 'LONG' else top_2[1]['price'] * 1.03, 4 if top_2[1]['price'] < 1 else 2),
                'wr': round(top_2[1]['wr'], 1),
                'reason': get_reason(top_2[1]),
            }
        ]
    }
    
    output_path = ROOT / 'genome' / 'data' / 'kimi_picks_4_and_5.json'
    with open(output_path, 'w') as f:
        import json
        json.dump(output, f, indent=2)
    
    print(f"\n\nSaved to: {output_path}")
    
else:
    print("\n[ERR] Not enough candidates found")
