import pandas as pd
import numpy as np
import yfinance as yf
from world_class_strategies_v21 import WORLD_CLASS_V21_STRATEGIES

def main():
    print("[TEST] Fetching data for BTC-USD to test v2.1 strategies...")
    df = yf.download("BTC-USD", period="1d", interval="1h")
    if df.empty:
        print("[ERROR] Could not fetch data.")
        return
    
    data = {"BTCUSDT": df}
    symbol = "BTCUSDT"
    
    for name, func in WORLD_CLASS_V21_STRATEGIES.items():
        print(f"\n[TEST] Running {name}...")
        try:
            signals = func(data, symbol)
            if signals:
                print(f"[SUCCESS] {name} generated {len(signals)} signals: {signals}")
            else:
                print(f"[INFO] {name} did not fire (normal for single candle test).")
        except Exception as e:
            print(f"[ERROR] {name} CRASHED: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
