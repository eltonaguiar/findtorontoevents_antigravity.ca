import sys
import os
import json
import statistics

# Set path to alpha_engine
sys.path.append(r'e:/findtorontoevents_antigravity.ca/alpha_engine')

try:
    from quant_algorithms import _fetch_klines, _parse_ohlcv, _get_whale_consensus_weight, _atr
    
    symbols = ['UNIUSDT', 'BNBUSDT', 'NEARUSDT', 'LTCUSDT']
    results = {}

    for sym in symbols:
        klines = _fetch_klines(sym)
        if klines:
            ohlcv = _parse_ohlcv(klines)
            price = ohlcv['close'][-1]
            vol = ohlcv['volume'][-1]
            avg_vol = statistics.mean(ohlcv['volume'][-20:])
            vol_ratio = vol / avg_vol if avg_vol > 0 else 1.0
            whale = _get_whale_consensus_weight(sym)
            atr = _atr(ohlcv['high'], ohlcv['low'], ohlcv['close'])
            
            results[sym] = {
                'price': price,
                'vol_ratio_4h': round(vol_ratio, 2),
                'whale_weight': whale['weight'],
                'whale_reason': whale['reason'],
                'atr_pct': round((atr/price)*100, 2)
            }
            
    print(json.dumps(results, indent=2))

except Exception as e:
    print(f"ERROR: {str(e)}")
