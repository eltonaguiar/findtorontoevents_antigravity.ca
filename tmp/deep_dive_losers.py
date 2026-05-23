import json

picks_path = r'e:\findtorontoevents_antigravity.ca\audit_trail\data\universal_resolved_picks.json'

with open(picks_path, 'r') as f:
    picks = json.load(f)

# Find all picks for ml_crypto_predictor
ml_picks = [p for p in picks if p.get('source_system') == 'ml_crypto_predictor']

# Also find picks specifically for TRXUSDT across ALL systems
trx_picks = [p for p in picks if p.get('symbol') == 'TRXUSDT']

print(f"Total ml_crypto_predictor picks: {len(ml_picks)}")
print(f"Total TRXUSDT picks: {len(trx_picks)}")

# Group ml_crypto_predictor picks by symbol
from collections import defaultdict
ml_by_sym = defaultdict(list)
for p in ml_picks:
    ml_by_sym[p.get('symbol', 'unknown')].append(p)

print("\n--- ml_crypto_predictor top symbol trades ---")
sym_stats = []
for sym, sym_picks in ml_by_sym.items():
    pnl = sum([p.get('pnl_pct', 0) for p in sym_picks])
    sym_stats.append({'symbol': sym, 'pnl': pnl, 'trades': len(sym_picks)})

sym_stats.sort(key=lambda x: x['pnl'])
for s in sym_stats[:10]:
    print(f"Symbol: {s['symbol']}, Trades: {s['trades']}, Cumulative PnL: {s['pnl']:.2f}%")

print("\n--- TRXUSDT trades by source system ---")
trx_by_system = defaultdict(list)
for p in trx_picks:
    trx_by_system[p.get('source_system', 'unknown')].append(p)

trx_system_stats = []
for sys, sys_picks in trx_by_system.items():
    pnl = sum([p.get('pnl_pct', 0) for p in sys_picks])
    trx_system_stats.append({'system': sys, 'pnl': pnl, 'trades': len(sys_picks)})

trx_system_stats.sort(key=lambda x: x['pnl'])
for s in trx_system_stats:
    print(f"System: {s['system']}, Trades: {s['trades']}, PnL on TRX: {s['pnl']:.2f}%")
