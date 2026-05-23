#!/usr/bin/env python3
"""Parse all v0.05 TradingView backtest Excel exports and produce a full analysis."""
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

def safe_float(val, default=0.0):
    try:
        v = float(val)
        if pd.isna(v):
            return default
        return v
    except (ValueError, TypeError):
        return default

def safe_int(val, default=0):
    try:
        v = int(float(val))
        return v
    except (ValueError, TypeError):
        return default

results = []

print(f"{'Symbol':12s} {'Trades':>7s} {'Win%':>6s} {'PF':>7s} {'Net%':>8s} {'MaxDD%':>8s} {'Sharpe':>8s} {'AvgBars':>7s} {'AvgWin%':>8s} {'AvgLos%':>8s} {'W/L':>6s}")
print('=' * 110)

for path, sym in files:
    if not os.path.exists(path):
        print(f"{sym:12s} MISSING")
        continue
    try:
        perf = pd.read_excel(path, sheet_name='Performance', header=None)
        trades_df = pd.read_excel(path, sheet_name='Trades analysis', header=None)
        risk = pd.read_excel(path, sheet_name='Risk-adjusted performance', header=None)
        props = pd.read_excel(path, sheet_name='Properties', header=None)

        net_pct = safe_float(perf.iloc[3, 2])
        gross_profit = safe_float(perf.iloc[4, 1])
        gross_loss = safe_float(perf.iloc[5, 1])
        commission = safe_float(perf.iloc[7, 1])
        max_dd_pct = safe_float(perf.iloc[28, 2])
        buy_hold_pct = safe_float(perf.iloc[9, 1])

        total_trades = safe_int(trades_df.iloc[2, 1])
        winning_trades = safe_int(trades_df.iloc[3, 1])
        losing_trades = safe_int(trades_df.iloc[4, 1])
        wr = safe_float(trades_df.iloc[6, 1])
        avg_win_pct = safe_float(trades_df.iloc[8, 2])
        avg_loss_pct = safe_float(trades_df.iloc[9, 2])
        win_loss_ratio = safe_float(trades_df.iloc[10, 1])
        avg_bars = safe_int(trades_df.iloc[15, 1])
        avg_bars_win = safe_int(trades_df.iloc[16, 1])
        avg_bars_loss = safe_int(trades_df.iloc[17, 1])

        pf = safe_float(risk.iloc[3, 1])
        sharpe = safe_float(risk.iloc[1, 1])
        sortino = safe_float(risk.iloc[2, 1])

        period = str(props.iloc[1, 1]) if len(props) > 1 else ''
        timeframe = str(props.iloc[4, 1]) if len(props) > 4 else ''
        mode = ''
        tpsl = ''
        for i in range(len(props)):
            name = str(props.iloc[i, 0]).strip()
            if name == 'Strategy Mode':
                mode = str(props.iloc[i, 1])
            elif name == 'TP/SL Mode':
                tpsl = str(props.iloc[i, 1])

        print(f"{sym:12s} {total_trades:7d} {wr:5.1f}% {pf:7.3f} {net_pct:+7.2f}% {max_dd_pct:7.2f}% {sharpe:+7.3f} {avg_bars:7d} {avg_win_pct:+7.2f}% {avg_loss_pct:+7.2f}% {win_loss_ratio:5.3f}")

        results.append({
            'symbol': sym,
            'trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': wr,
            'profit_factor': pf,
            'net_pct': net_pct,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'commission': commission,
            'max_dd_pct': max_dd_pct,
            'sharpe': sharpe,
            'sortino': sortino,
            'avg_bars': avg_bars,
            'avg_bars_win': avg_bars_win,
            'avg_bars_loss': avg_bars_loss,
            'avg_win_pct': avg_win_pct,
            'avg_loss_pct': avg_loss_pct,
            'win_loss_ratio': win_loss_ratio,
            'buy_hold_pct': buy_hold_pct,
            'mode': mode,
            'tpsl_mode': tpsl,
            'timeframe': timeframe,
            'period': period,
        })
    except Exception as e:
        print(f"{sym:12s} ERROR: {e}")

os.makedirs('backtest_results', exist_ok=True)
with open('backtest_results/tradingview_v05_results.json', 'w') as f:
    json.dump(results, f, indent=2)

profitable = sorted([r for r in results if r['profit_factor'] > 1.0], key=lambda x: -x['profit_factor'])
near_be = sorted([r for r in results if 0.95 <= r['profit_factor'] <= 1.0], key=lambda x: -x['profit_factor'])
losing = sorted([r for r in results if r['profit_factor'] < 0.95], key=lambda x: x['profit_factor'])

print(f"\n{'='*80}")
print(f"PROFITABLE ({len(profitable)}/{len(results)})")
print(f"{'='*80}")
for r in profitable:
    print(f"  {r['symbol']:12s} PF {r['profit_factor']:.3f}  Net {r['net_pct']:+6.2f}%  WR {r['win_rate']:.1f}%  {r['trades']} trades  DD {r['max_dd_pct']:.1f}%  AvgBars {r['avg_bars']}")

print(f"\nNEAR BREAKEVEN ({len(near_be)}/{len(results)})")
print(f"{'='*80}")
for r in near_be:
    print(f"  {r['symbol']:12s} PF {r['profit_factor']:.3f}  Net {r['net_pct']:+6.2f}%  WR {r['win_rate']:.1f}%  {r['trades']} trades  DD {r['max_dd_pct']:.1f}%  AvgBars {r['avg_bars']}")

print(f"\nLOSING ({len(losing)}/{len(results)})")
print(f"{'='*80}")
for r in losing:
    print(f"  {r['symbol']:12s} PF {r['profit_factor']:.3f}  Net {r['net_pct']:+6.2f}%  WR {r['win_rate']:.1f}%  {r['trades']} trades  DD {r['max_dd_pct']:.1f}%  AvgBars {r['avg_bars']}")

print(f"\n{'='*80}")
print("PATTERN ANALYSIS")
print(f"{'='*80}")

if profitable:
    avg_pf_win = sum(r['profit_factor'] for r in profitable) / len(profitable)
    avg_wr_win = sum(r['win_rate'] for r in profitable) / len(profitable)
    avg_bars_win = sum(r['avg_bars'] for r in profitable) / len(profitable)
    avg_wl_win = sum(r['win_loss_ratio'] for r in profitable) / len(profitable)
    avg_avgwin_win = sum(r['avg_win_pct'] for r in profitable) / len(profitable)
    avg_avgloss_win = sum(abs(r['avg_loss_pct']) for r in profitable) / len(profitable)
    avg_comm_win = sum(r['commission'] for r in profitable) / len(profitable)
    print(f"\nWinners pattern:")
    print(f"  Avg PF: {avg_pf_win:.3f}  Avg WR: {avg_wr_win:.1f}%  Avg Bars Held: {avg_bars_win:.0f}")
    print(f"  Avg Win/Loss Ratio: {avg_wl_win:.3f}  Avg Win: {avg_avgwin_win:+.2f}%  Avg Loss: {avg_avgloss_win:.2f}%")
    print(f"  Avg Commission: ${avg_comm_win:.2f}")

if losing:
    avg_pf_los = sum(r['profit_factor'] for r in losing) / len(losing)
    avg_wr_los = sum(r['win_rate'] for r in losing) / len(losing)
    avg_bars_los = sum(r['avg_bars'] for r in losing) / len(losing)
    avg_wl_los = sum(r['win_loss_ratio'] for r in losing) / len(losing)
    avg_avgwin_los = sum(r['avg_win_pct'] for r in losing) / len(losing)
    avg_avgloss_los = sum(abs(r['avg_loss_pct']) for r in losing) / len(losing)
    avg_comm_los = sum(r['commission'] for r in losing) / len(losing)
    print(f"\nLosers pattern:")
    print(f"  Avg PF: {avg_pf_los:.3f}  Avg WR: {avg_wr_los:.1f}%  Avg Bars Held: {avg_bars_los:.0f}")
    print(f"  Avg Win/Loss Ratio: {avg_wl_los:.3f}  Avg Win: {avg_avgwin_los:+.2f}%  Avg Loss: {avg_avgloss_los:.2f}%")
    print(f"  Avg Commission: ${avg_comm_los:.2f}")

print(f"\nCommission impact:")
for r in sorted(results, key=lambda x: -x['commission']):
    comm_pct = (r['commission'] / (r['gross_profit'] + 0.001)) * 100
    print(f"  {r['symbol']:12s} Comm: ${r['commission']:7.2f}  ({comm_pct:5.1f}% of gross profit)  GP: ${r['gross_profit']:.2f}  GL: ${r['gross_loss']:.2f}")

print(f"\nAvg bars held (winners vs losers per symbol):")
for r in sorted(results, key=lambda x: x['avg_bars']):
    print(f"  {r['symbol']:12s} AvgBars: {r['avg_bars']:3d} (win: {r['avg_bars_win']:3d}, loss: {r['avg_bars_loss']:3d})  PF: {r['profit_factor']:.3f}")

print(f"\nSaved {len(results)} results to backtest_results/tradingview_v05_results.json")
