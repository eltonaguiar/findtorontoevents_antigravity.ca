#!/usr/bin/env python3
"""Extract and summarize TradingView backtest Excel exports."""
import pandas as pd
import os
import json

files = [
    (r'C:\Users\zerou\Downloads\SIMP_KC04_BINANCE_BTCUSDT_2026-02-21.xlsx', 'BTCUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC04_BINANCE_SOLUSDT_2026-02-21.xlsx', 'SOLUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC04_BINANCE_BNBUSDT_2026-02-21.xlsx', 'BNBUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC04_BINANCE_XRPUSDT_2026-02-21.xlsx', 'XRPUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC04_BINANCE_DOGEUSDT_2026-02-21.xlsx', 'DOGEUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC04_BINANCE_DOGEUSDT_2026-02-21 (1).xlsx', 'DOGEUSDT_v2'),
    (r'C:\Users\zerou\Downloads\SIMP_KC04_BINANCE_INJUSDT_2026-02-21.xlsx', 'INJUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC04_BINANCE_ZKUSDT_2026-02-21.xlsx', 'ZKUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC04_BINANCE_ZROUSDT_2026-02-21.xlsx', 'ZROUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC04_BINANCE_STRKUSDT_2026-02-21.xlsx', 'STRKUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC04_BINANCE_WLDUSDT_2026-02-21.xlsx', 'WLDUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC04_BINANCE_HBARUSDT_2026-02-21.xlsx', 'HBARUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC04_BINANCE_ALGOUSDT_2026-02-21.xlsx', 'ALGOUSDT'),
]

header = f"{'Symbol':12s} {'Trades':>7s} {'WR%':>7s} {'PF':>7s} {'Net%':>8s} {'MaxDD%':>8s} {'Sharpe':>8s} {'AvgBars':>8s}  Period"
print(header)
print('-' * 105)

results = []
for path, sym in files:
    if not os.path.exists(path):
        print(f"{sym:12s} MISSING")
        continue
    try:
        perf = pd.read_excel(path, sheet_name='Performance', header=None)
        trades_df = pd.read_excel(path, sheet_name='Trades analysis', header=None)
        risk = pd.read_excel(path, sheet_name='Risk-adjusted performance', header=None)
        props = pd.read_excel(path, sheet_name='Properties', header=None)

        net_pct = float(perf.iloc[3, 2])
        max_dd_pct = float(perf.iloc[28, 2])
        total_trades = int(trades_df.iloc[2, 1])
        wr = float(trades_df.iloc[6, 1])
        avg_bars = int(trades_df.iloc[15, 1])
        pf = float(risk.iloc[3, 1])
        sharpe = float(risk.iloc[1, 1])

        period = str(props.iloc[1, 1]) if len(props) > 1 else ''
        mode = str(props.iloc[10, 1]) if len(props) > 10 else ''
        tpsl = str(props.iloc[12, 1]) if len(props) > 12 else ''
        timeframe = str(props.iloc[4, 1]) if len(props) > 4 else ''

        print(f"{sym:12s} {total_trades:7d} {wr:6.1f}% {pf:7.3f} {net_pct:+7.2f}% {max_dd_pct:7.2f}% {sharpe:+7.3f} {avg_bars:7d}  {period[:50]}")

        results.append({
            'symbol': sym,
            'trades': total_trades,
            'win_rate': wr,
            'profit_factor': pf,
            'net_pct': net_pct,
            'max_dd_pct': max_dd_pct,
            'sharpe': sharpe,
            'avg_bars': avg_bars,
            'mode': mode,
            'tpsl_mode': tpsl,
            'timeframe': timeframe,
            'period': period,
        })
    except Exception as e:
        print(f"{sym:12s} ERROR: {e}")

os.makedirs('backtest_results', exist_ok=True)
with open('backtest_results/tradingview_v04_results.json', 'w') as f:
    json.dump(results, f, indent=2)
print(f"\nSaved {len(results)} results to backtest_results/tradingview_v04_results.json")

profitable = [r for r in results if r['profit_factor'] > 1.0]
losing = [r for r in results if r['profit_factor'] <= 1.0]

print(f"\n=== PROFITABLE ({len(profitable)}/{len(results)}) ===")
for r in sorted(profitable, key=lambda x: -x['profit_factor']):
    s = r['symbol']
    print(f"  {s:12s} PF {r['profit_factor']:.3f}  Net {r['net_pct']:+.2f}%  WR {r['win_rate']:.1f}%  {r['trades']} trades  DD {r['max_dd_pct']:.1f}%")

print(f"\n=== LOSING ({len(losing)}/{len(results)}) ===")
for r in sorted(losing, key=lambda x: x['profit_factor']):
    s = r['symbol']
    print(f"  {s:12s} PF {r['profit_factor']:.3f}  Net {r['net_pct']:+.2f}%  WR {r['win_rate']:.1f}%  {r['trades']} trades  DD {r['max_dd_pct']:.1f}%")

avg_pf = sum(r['profit_factor'] for r in results) / len(results) if results else 0
avg_wr = sum(r['win_rate'] for r in results) / len(results) if results else 0
print(f"\n=== AVERAGES ===")
print(f"  Average PF:  {avg_pf:.3f}")
print(f"  Average WR:  {avg_wr:.1f}%")
print(f"  Win count:   {len(profitable)}/{len(results)} ({100*len(profitable)/len(results):.0f}%)")
