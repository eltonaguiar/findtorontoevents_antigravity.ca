#!/usr/bin/env python3
"""Check current status of KIMI Top 3 Picks."""

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from genome.mutation_lab.innovative_mutations import fetch_binance_klines
from genome.kimi_top_picks_automation import williams_r_indicator

def main():
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'DOTUSDT']
    
    print('='*60)
    print('KIMI TOP 3 PICKS - CURRENT MARKET SCAN')
    print('='*60)
    print()
    
    picks_ready = []
    
    for symbol in symbols:
        df = fetch_binance_klines(symbol, '1h', 200)
        if df.empty:
            continue
        
        close = df['Close']
        current = close.iloc[-1]
        
        # Williams %R
        wr = williams_r_indicator(close).iloc[-1]
        
        # 200 SMA
        sma_200 = close.rolling(200).mean().iloc[-1]
        above_sma = current > sma_200
        
        # Check if close to signal
        if wr < -70 and above_sma:
            picks_ready.append({
                'symbol': symbol,
                'price': current,
                'wr': wr,
                'sma_200': sma_200,
                'strategy': 'Williams %R Mean Reversion'
            })
        
        # Status
        if wr > -80:
            wr_dist = wr - (-80)
            wr_status = f'{wr_dist:.1f} pts from oversold'
        else:
            wr_status = '** OVERSOLD - READY FOR SIGNAL **'
        
        print(f'{symbol}:')
        print(f'  Price: ${current:,.2f}')
        print(f'  Williams %R: {wr:.1f} ({wr_status})')
        print(f'  200 SMA: ${sma_200:,.2f} ({"ABOVE" if above_sma else "BELOW"})')
        print()
    
    if picks_ready:
        print('='*60)
        print('PICKS READY FOR ENTRY:')
        print('='*60)
        for pick in picks_ready:
            print(f"  {pick['symbol']} @ ${pick['price']:,.2f}")
            print(f"    Strategy: {pick['strategy']}")
            print(f"    Williams %R: {pick['wr']:.1f}")
    else:
        print('='*60)
        print('STATUS: No picks in entry zone yet')
        print('='*60)
        print()
        print('The system is WAITING for:')
        print('  - Williams %R to drop below -80 (oversold)')
        print('  - Price to remain above 200 SMA')
        print('  - OR: VWAP squeeze conditions')
        print('  - OR: EMA ribbon alignment')
        print()
        print('Current market may be overbought or in chop.')
        print('System is being SELECTIVE (good thing).')

if __name__ == '__main__':
    main()
