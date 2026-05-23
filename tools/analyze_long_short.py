#!/usr/bin/env python3
"""Analyze long vs short performance across all v0.05 coins."""
import pandas as pd
import os
import json

files = [
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_BTCUSDT_2026-02-21.xlsx', 'BTCUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_ETHUSDT_2026-02-21.xlsx', 'ETHUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_SOLUSDT_2026-02-21.xlsx', 'SOLUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_BNBUSDT_2026-02-21.xlsx', 'BNBUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_XRPUSDT_2026-02-21.xlsx', 'XRPUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_DOGEUSDT_2026-02-21.xlsx', 'DOGEUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_ADAUSDT_2026-02-21.xlsx', 'ADAUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_AVAXUSDT_2026-02-21.xlsx', 'AVAXUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_TRXUSDT_2026-02-21.xlsx', 'TRXUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_DOTUSDT_2026-02-21.xlsx', 'DOTUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_LINKUSDT_2026-02-21.xlsx', 'LINKUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_POLUSDT_2026-02-21.xlsx', 'POLUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_LTCUSDT_2026-02-21.xlsx', 'LTCUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_BCHUSDT_2026-02-21.xlsx', 'BCHUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_OKX_TONUSDT_2026-02-21.xlsx', 'TONUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_SHIBUSDT_2026-02-21.xlsx', 'SHIBUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_INJUSDT_2026-02-21.xlsx', 'INJUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_FETUSDT_2026-02-21.xlsx', 'FETUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_SUIUSDT_2026-02-21.xlsx', 'SUIUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_ARBUSDT_2026-02-21.xlsx', 'ARBUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_OPUSDT_2026-02-21.xlsx', 'OPUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_SEIUSDT_2026-02-21.xlsx', 'SEIUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_TIAUSDT_2026-02-21.xlsx', 'TIAUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_DYDXUSDT_2026-02-21.xlsx', 'DYDXUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_APEUSDT_2026-02-21.xlsx', 'APEUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_ALGOUSDT_2026-02-21.xlsx', 'ALGOUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_HBARUSDT_2026-02-21.xlsx', 'HBARUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_WLDUSDT_2026-02-21.xlsx', 'WLDUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_STRKUSDT_2026-02-21.xlsx', 'STRKUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_ZROUSDT_2026-02-21.xlsx', 'ZROUSDT'),
    (r'C:\Users\zerou\Downloads\SIMP_KC05_BINANCE_ZKUSDT_2026-02-21.xlsx', 'ZKUSDT'),
]

def sf(val, default=0.0):
    try:
        v = float(val)
        return default if pd.isna(v) else v
    except (ValueError, TypeError):
        return default

print("LONG vs SHORT BREAKDOWN")
print("{:12s} {:>9s} {:>9s} {:>8s} {:>8s} {:>8s} {:>8s} {:>10s}".format(
    "Symbol", "Net Long%", "Net Shrt%", "PF Long", "PF Shrt", "WR Long", "WR Shrt", "Verdict"))
print("=" * 95)

data = []
for path, sym in files:
    if not os.path.exists(path):
        continue
    try:
        perf = pd.read_excel(path, sheet_name='Performance', header=None)
        trades_df = pd.read_excel(path, sheet_name='Trades analysis', header=None)
        risk = pd.read_excel(path, sheet_name='Risk-adjusted performance', header=None)

        net_long_pct = sf(perf.iloc[3, 4])
        net_short_pct = sf(perf.iloc[3, 6])
        pf_long = sf(risk.iloc[3, 3])
        pf_short = sf(risk.iloc[3, 5])
        long_trades = int(sf(trades_df.iloc[2, 3]))
        short_trades = int(sf(trades_df.iloc[2, 5]))
        wr_long = sf(trades_df.iloc[6, 3])
        wr_short = sf(trades_df.iloc[6, 5])

        if net_long_pct > 0 and net_short_pct > 0:
            verdict = "BOTH WIN"
        elif net_long_pct > 0 and net_short_pct <= 0:
            verdict = "LONG ONLY"
        elif net_long_pct <= 0 and net_short_pct > 0:
            verdict = "SHORT ONLY"
        else:
            verdict = "BOTH LOSE"

        print("{:12s} {:+8.2f}% {:+8.2f}% {:8.3f} {:8.3f} {:7.1f}% {:7.1f}% {:>10s}".format(
            sym, net_long_pct, net_short_pct, pf_long, pf_short, wr_long, wr_short, verdict))

        data.append({
            'symbol': sym,
            'net_long_pct': net_long_pct,
            'net_short_pct': net_short_pct,
            'pf_long': pf_long,
            'pf_short': pf_short,
            'long_trades': long_trades,
            'short_trades': short_trades,
            'wr_long': wr_long,
            'wr_short': wr_short,
            'verdict': verdict,
        })
    except Exception as e:
        print("{:12s} ERROR: {}".format(sym, e))

print("\n" + "=" * 60)
long_only = [d for d in data if d['verdict'] == 'LONG ONLY']
both_win = [d for d in data if d['verdict'] == 'BOTH WIN']
short_only = [d for d in data if d['verdict'] == 'SHORT ONLY']
both_lose = [d for d in data if d['verdict'] == 'BOTH LOSE']

print("BOTH WIN:   {} coins".format(len(both_win)))
for d in both_win:
    print("  {} L:{:+.2f}% S:{:+.2f}%".format(d['symbol'], d['net_long_pct'], d['net_short_pct']))

print("LONG ONLY:  {} coins (longs profitable, shorts lose)".format(len(long_only)))
for d in sorted(long_only, key=lambda x: -x['net_long_pct']):
    print("  {} L:{:+.2f}% S:{:+.2f}% (shorts drag: {:.2f}%)".format(
        d['symbol'], d['net_long_pct'], d['net_short_pct'], d['net_short_pct']))

print("SHORT ONLY: {} coins".format(len(short_only)))
for d in short_only:
    print("  {} L:{:+.2f}% S:{:+.2f}%".format(d['symbol'], d['net_long_pct'], d['net_short_pct']))

print("BOTH LOSE:  {} coins".format(len(both_lose)))
for d in sorted(both_lose, key=lambda x: x['net_long_pct'] + x['net_short_pct']):
    print("  {} L:{:+.2f}% S:{:+.2f}%".format(d['symbol'], d['net_long_pct'], d['net_short_pct']))

total_long = sum(d['net_long_pct'] for d in data)
total_short = sum(d['net_short_pct'] for d in data)
print("\nAGGREGATE: Long total: {:+.2f}%  Short total: {:+.2f}%".format(total_long, total_short))
print("If long-only: {:+.2f}% combined vs current {:+.2f}%".format(
    total_long, total_long + total_short))

with open('backtest_results/long_short_analysis.json', 'w') as f:
    json.dump(data, f, indent=2)
