#!/usr/bin/env python3
"""Read TradingView backtest Excel exports and summarize."""
import pandas as pd
import os, json

files = [
    r'C:\Users\zerou\Downloads\SIMP_KC04_BINANCE_BTCUSDT_2026-02-21.xlsx',
    r'C:\Users\zerou\Downloads\SIMP_KC04_BINANCE_SOLUSDT_2026-02-21.xlsx',
    r'C:\Users\zerou\Downloads\SIMP_KC04_BINANCE_BNBUSDT_2026-02-21.xlsx',
    r'C:\Users\zerou\Downloads\SIMP_KC04_BINANCE_XRPUSDT_2026-02-21.xlsx',
    r'C:\Users\zerou\Downloads\SIMP_KC04_BINANCE_DOGEUSDT_2026-02-21.xlsx',
    r'C:\Users\zerou\Downloads\SIMP_KC04_BINANCE_DOGEUSDT_2026-02-21 (1).xlsx',
    r'C:\Users\zerou\Downloads\SIMP_KC04_BINANCE_INJUSDT_2026-02-21.xlsx',
    r'C:\Users\zerou\Downloads\SIMP_KC04_BINANCE_ZKUSDT_2026-02-21.xlsx',
    r'C:\Users\zerou\Downloads\SIMP_KC04_BINANCE_ZROUSDT_2026-02-21.xlsx',
    r'C:\Users\zerou\Downloads\SIMP_KC04_BINANCE_STRKUSDT_2026-02-21.xlsx',
    r'C:\Users\zerou\Downloads\SIMP_KC04_BINANCE_WLDUSDT_2026-02-21.xlsx',
    r'C:\Users\zerou\Downloads\SIMP_KC04_BINANCE_HBARUSDT_2026-02-21.xlsx',
    r'C:\Users\zerou\Downloads\SIMP_KC04_BINANCE_ALGOUSDT_2026-02-21.xlsx',
]

results = {}

for f in files:
    if not os.path.exists(f):
        print(f"MISSING: {os.path.basename(f)}")
        continue
    
    basename = os.path.basename(f)
    parts = basename.replace('.xlsx', '').split('_')
    symbol = parts[3] if len(parts) > 3 else basename
    
    try:
        xl = pd.ExcelFile(f)
        print(f"\n{'='*60}")
        print(f"  {symbol} — {basename}")
        print(f"  Sheets: {xl.sheet_names}")
        print(f"{'='*60}")
        
        for sheet in xl.sheet_names:
            df = pd.read_excel(f, sheet_name=sheet, header=None)
            print(f"\n  --- Sheet: {sheet} ({df.shape[0]} rows x {df.shape[1]} cols) ---")
            for i in range(min(40, len(df))):
                row = df.iloc[i]
                vals = []
                for v in row:
                    s = str(v)
                    if s != 'nan':
                        vals.append(s)
                if vals:
                    print(f"    {i:3d}: {' | '.join(vals)}")
            
    except Exception as e:
        print(f"ERROR {symbol}: {e}")

print("\n\nDone reading all files.")
