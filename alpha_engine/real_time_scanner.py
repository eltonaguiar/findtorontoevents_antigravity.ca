import asyncio
import json
import datetime
import time
import pandas as pd

from config import CRYPTO_SYMBOLS, YF_PERIOD_DAILY, YF_INTERVAL_DAILY
from scanner import fetch_market_data
from crypto_strategies import CRYPTO_STRATEGIES
import websockets

async def real_time_scanner():
    # Fetch initial historical data for major crypto pairs
    major_yf_symbols = [symbol for symbol, info in CRYPTO_SYMBOLS.items() if info.get('tier') == 'major']
    historical_data = fetch_market_data(major_yf_symbols, period=YF_PERIOD_DAILY, interval=YF_INTERVAL_DAILY)
    
    # Map to Binance symbols
    binance_to_yf = {info['binance']: symbol for symbol, info in CRYPTO_SYMBOLS.items() if 'binance' in info and info.get('tier') == 'major'}
    major_binance_symbols = list(binance_to_yf.keys())
    
    uri = "wss://stream.binance.com:9443/ws"
    
    subscribe_msg = {
        "method": "SUBSCRIBE",
        "params": [s.lower() + "@ticker" for s in major_binance_symbols],
        "id": 1
    }
    
    latest_prices = {}
    last_generate = time.time()
    generation_interval = 60  # seconds
    
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps(subscribe_msg))
        
        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=generation_interval)
                data = json.loads(msg)
                
                if 's' in data:
                    symbol = data['s'].upper()
                    latest_prices[symbol] = {
                        'price': float(data['c']),
                        'volume': float(data['v']),
                        'timestamp': datetime.datetime.utcnow()
                    }
            except asyncio.TimeoutError:
                # Timeout means no message in interval, proceed to generate signals
                pass
            
            # Check if time to generate signals
            current_time = time.time()
            if current_time - last_generate >= generation_interval:
                signals = []
                for binance_sym, yf_sym in binance_to_yf.items():
                    if binance_sym in latest_prices:
                        df = historical_data.get(yf_sym, pd.DataFrame()).copy()
                        live = latest_prices[binance_sym]
                        
                        # Append live data as new row
                        new_row = pd.DataFrame({
                            'Open': [live['price']],
                            'High': [live['price']],
                            'Low': [live['price']],
                            'Close': [live['price']],
                            'Volume': [live['volume']]
                        }, index=[live['timestamp']])
                        
                        df = pd.concat([df, new_row])
                        df = df.sort_index()
                        
                        # Run each strategy on updated data
                        for strategy in CRYPTO_STRATEGIES:
                            strat_signals = strategy({yf_sym: df})
                            if strat_signals:
                                signals.extend(strat_signals)
                
                if signals:
                    print(f"[{datetime.datetime.now()}] New signals generated:")
                    for sig in signals:
                        print(sig)
                    # TODO: Integrate with database or notification system
                
                last_generate = current_time

if __name__ == "__main__":
    asyncio.run(real_time_scanner())
