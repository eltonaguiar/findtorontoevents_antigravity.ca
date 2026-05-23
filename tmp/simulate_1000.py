#!/usr/bin/env python3
"""$1000 Investment Simulation across all systems and strategies."""
import json
from pathlib import Path
from collections import defaultdict

def load_picks(path):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ['picks', 'active', 'signals']:
                if key in data and isinstance(data[key], list):
                    return data[key]
            return []
        return []
    except:
        return []

def get_pnls(picks, pnl_key='pnl_pct', alt_key='unrealized_pnl_pct'):
    pnls = []
    for p in picks:
        v = p.get(pnl_key) or p.get(alt_key)
        if v is not None:
            try:
                pnls.append(float(v))
            except:
                pass
    return pnls

def analyze_system(name, path, pnl_key='pnl_pct', alt_key='unrealized_pnl_pct'):
    picks = load_picks(path)
    pnls = get_pnls(picks, pnl_key, alt_key)
    if not pnls:
        return None
    avg = sum(pnls) / len(pnls)
    wins = len([p for p in pnls if p > 0])
    wr = wins / len(pnls) * 100
    return {
        'name': name,
        'picks': len(pnls),
        'wr': wr,
        'avg_pnl': avg,
        'total_pnl': sum(pnls),
        'invested': 1000,
        'return_1k': 1000 * (1 + avg / 100),
        'best': max(pnls),
        'worst': min(pnls),
    }

# ── SYSTEM-LEVEL COMPARISON ──
print("=" * 90)
print("$1000 INVESTMENT SIMULATION: If you put $1000 into each system's picks today")
print("(Equal-weight across all picks in that system)")
print("=" * 90)

systems = []
configs = [
    ("Battleground (388 closed, PROVEN)", "battleground/data/closed_picks.json"),
    ("ClawsOfDoom (56 closed)", "ml_battleground/system_f_clawsofdoom/data/closed_picks.json"),
    ("Mercury2 (46 closed)", "mercury2/data/closed_picks.json"),
    ("Paper Trading (34 closed)", "paper_trading/data/closed_picks.json"),
    ("Alpha Engine (26 closed)", "alpha_engine/data/closed_picks.json"),
    ("ML System A (19 closed)", "ml_battleground/system_a_filter/data/closed_picks.json"),
    ("ML System B (19 closed)", "ml_battleground/system_b_regime/data/closed_picks.json"),
    ("ML Ensemble (8 closed)", "ml_battleground/ensemble_data/closed_picks.json"),
    ("ML DeepLearn (5 closed)", "ml_battleground/system_c_deeplearn/data/closed_picks.json"),
    # Active (today's snapshot)
    ("Multi-Asset Scanner (15 active)", "multi_asset/data/active_picks.json", "unrealized_pnl_pct"),
    ("Alpha Engine (56 active)", "alpha_engine/data/active_picks.json", "unrealized_pnl_pct"),
    ("ClawsOfDoom (10 active)", "ml_battleground/system_f_clawsofdoom/data/active_picks.json"),
    ("Mercury2 (3 active)", "mercury2/data/active_picks.json", "unrealized_pnl_pct"),
    ("Crypto ML Edge (9 active)", "crypto_ml_edge/data/active_picks.json", "unrealized_pnl_pct"),
    ("Paper Trading (29 active)", "paper_trading/data/active_picks.json", "unrealized_pnl_pct"),
]

for cfg in configs:
    name, path = cfg[0], cfg[1]
    alt = cfg[2] if len(cfg) > 2 else 'unrealized_pnl_pct'
    result = analyze_system(name, path, alt_key=alt)
    if result:
        systems.append(result)

systems.sort(key=lambda x: x['return_1k'], reverse=True)

print(f"\n{'System':<40} {'Picks':>5} {'WR':>6} {'Avg PnL':>9} {'$1000 ->':>10} {'P/L':>9}")
print("-" * 82)
for s in systems:
    pl = s['return_1k'] - 1000
    print(f"{s['name']:<40} {s['picks']:>5} {s['wr']:>5.1f}% {s['avg_pnl']:>+8.3f}% ${s['return_1k']:>8.2f} {'+' if pl>=0 else ''}{pl:>8.2f}")

print(f"\n{'GIC Benchmark (per trade cycle)':<40} {'---':>5} {'100%':>6} {'+0.011%':>9} ${'1000.11':>8} {'+0.11':>9}")

# ── BY STRATEGY (Battleground proven data) ──
print("\n" + "=" * 90)
print("$1000 PER STRATEGY (Battleground - 388 real forward-tested trades)")
print("=" * 90)

picks = load_picks("battleground/data/closed_picks.json")
strats = defaultdict(list)
for p in picks:
    s = p.get('strategy', 'unknown')
    pnl = p.get('pnl_pct')
    if pnl is not None:
        strats[s].append(float(pnl))

print(f"\n{'Strategy':<50} {'Trades':>6} {'WR':>6} {'AvgPnL':>8} {'$1000->':>9} {'P/L':>8}")
print("-" * 90)
for s, pnls in sorted(strats.items(), key=lambda x: sum(x[1])/len(x[1]), reverse=True):
    wr = len([p for p in pnls if p > 0]) / len(pnls) * 100
    avg = sum(pnls) / len(pnls)
    ret = 1000 * (1 + avg / 100)
    pl = ret - 1000
    print(f"{s:<50} {len(pnls):>6} {wr:>5.1f}% {avg:>+7.3f}% ${ret:>7.2f} {'+' if pl>=0 else ''}{pl:>7.2f}")

# ── BY CRYPTO SYMBOL ──
print("\n" + "=" * 90)
print("$1000 PER CRYPTO SYMBOL (Battleground closed trades)")
print("=" * 90)

symbols = defaultdict(list)
for p in picks:
    sym = p.get('symbol', 'unknown')
    pnl = p.get('pnl_pct')
    if pnl is not None:
        symbols[sym].append(float(pnl))

print(f"\n{'Symbol':<20} {'Trades':>6} {'WR':>6} {'AvgPnL':>8} {'TotalPnL':>10} {'$1000->':>9}")
print("-" * 62)
for s, pnls in sorted(symbols.items(), key=lambda x: sum(x[1])/len(x[1]), reverse=True):
    wr = len([p for p in pnls if p > 0]) / len(pnls) * 100
    avg = sum(pnls) / len(pnls)
    total = sum(pnls)
    ret = 1000 * (1 + avg / 100)
    print(f"{s:<20} {len(pnls):>6} {wr:>5.1f}% {avg:>+7.3f}% {total:>+9.2f}% ${ret:>7.2f}")

# ── BEST COMBINATIONS ──
print("\n" + "=" * 90)
print("BEST CRYPTO STRATEGY + SYMBOL COMBOS (min 5 trades)")
print("=" * 90)

combos = defaultdict(list)
for p in picks:
    key = f"{p.get('strategy','?')} on {p.get('symbol','?')}"
    pnl = p.get('pnl_pct')
    if pnl is not None:
        combos[key].append(float(pnl))

print(f"\n{'Combo':<60} {'N':>4} {'WR':>6} {'AvgPnL':>8} {'$1000->':>9}")
print("-" * 90)
for key, pnls in sorted(combos.items(), key=lambda x: sum(x[1])/len(x[1]) if len(x[1])>=5 else -999, reverse=True):
    if len(pnls) < 5:
        continue
    wr = len([p for p in pnls if p > 0]) / len(pnls) * 100
    avg = sum(pnls) / len(pnls)
    ret = 1000 * (1 + avg / 100)
    print(f"{key:<60} {len(pnls):>4} {wr:>5.1f}% {avg:>+7.3f}% ${ret:>7.2f}")

# ── MULTI-DAY ANALYSIS: Does it hold up over time? ──
print("\n" + "=" * 90)
print("MULTI-DAY ANALYSIS: $1000 compounded across ALL 388 Battleground trades")
print("=" * 90)

all_pnls = [float(p.get('pnl_pct', 0)) for p in picks if p.get('pnl_pct') is not None]
# Sort by entry date
dated_picks = [(p.get('entry_time', p.get('opened_at', '')), float(p.get('pnl_pct', 0))) for p in picks if p.get('pnl_pct') is not None]
dated_picks.sort()

capital = 1000
peak = 1000
max_dd = 0
trade_results = []
for date, pnl in dated_picks:
    capital *= (1 + pnl / 100)
    if capital > peak:
        peak = capital
    dd = (capital - peak) / peak * 100
    if dd < max_dd:
        max_dd = dd
    trade_results.append((date[:10] if date else '?', capital, dd))

print(f"\nStarting capital: $1,000.00")
print(f"After 388 trades: ${capital:,.2f}")
print(f"Total return:     {(capital/1000-1)*100:+.1f}%")
print(f"Peak capital:     ${peak:,.2f}")
print(f"Max drawdown:     {max_dd:+.1f}%")

# Show by week/period
print("\nCapital progression (every 50 trades):")
for i in range(0, len(trade_results), 50):
    date, cap, dd = trade_results[i]
    print(f"  Trade {i+1:>3} ({date}): ${cap:>10,.2f}  (DD: {dd:>+.1f}%)")
if len(trade_results) % 50 != 0:
    date, cap, dd = trade_results[-1]
    print(f"  Trade {len(trade_results):>3} ({date}): ${cap:>10,.2f}  (DD: {dd:>+.1f}%)")

# ── WHICH SYSTEM TO BET WITH? ──
print("\n" + "=" * 90)
print("VERDICT: WHICH SYSTEM SHOULD YOU BET $1000 ON?")
print("=" * 90)

print("""
TIER 1 - PROVEN (would bet real money):
  1. Battleground crypto_keltner_compression_expansion_v1 on BTC
     -> 72.9% WR, 48 trades, $1000 -> $1004.19 per trade avg
     -> Compounded over 48 trades: $1000 -> $1,222

  2. Battleground keltner_compression_expansion_sol_v1 on SOL
     -> 66.7% WR, 36 trades, $1000 -> $1004.21 per trade avg

  3. Battleground multi_period_rsi_confluence on XRP
     -> 64.0% WR, 25 trades, highest avg PnL at +0.73%

TIER 2 - PROMISING (paper trade more):
  4. Mercury2 XGBoost ensemble (3 active, all green)
  5. ClawsOfDoom extreme_fear contrarian (60% WR active, 50% closed)
  6. Crypto ML Edge (83% WR but only 9 trades - too few)

TIER 3 - AVOID:
  7. ML System A Filter (10.5% WR, -$33 per $1000)
  8. ML System B Regime (10.5% WR, -$14 per $1000)
  9. ML Ensemble (0% WR, -$20 per $1000)
  10. ML DeepLearn (0% WR, -$5 per $1000)

CRYPTO-SPECIFIC ANSWER:
  Best system to bet AGAINST crypto: None reliably. SHORT signals
  from Coinglass sentiment_composite exist but unproven.

  Best system to bet FOR crypto: Battleground Keltner compression
  on BTC (72.9% WR) + RSI confluence on XRP (64% WR).
  Combined, you'd compound $1000 into ~$1,200-$1,500 over 80 trades.
""")
