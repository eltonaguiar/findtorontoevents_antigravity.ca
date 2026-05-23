#!/usr/bin/env python3
"""
Realistic Validation - Fast Version
===================================

Honest assessment with transaction costs.
"""

import json
import numpy as np
from pathlib import Path
from datetime import datetime

# Transaction costs
FEE = 0.001  # 0.1%
SLIPPAGE = 0.002  # 0.2% average
SPREAD = 0.0005  # 0.05%
TOTAL_COST = (FEE + SLIPPAGE + SPREAD) * 2  # Round trip

print("="*80)
print("  REALISTIC VALIDATION - WITH TRANSACTION COSTS")
print("="*80)
print(f"\nCost assumptions per round-trip trade:")
print(f"  Trading fees: {FEE*2:.2%}")
print(f"  Slippage: {SLIPPAGE*2:.2%}")
print(f"  Spread: {SPREAD*2:.2%}")
print(f"  TOTAL: {TOTAL_COST:.2%} per trade")

# Load data
trades = []
for period in ['today', 'yesterday', 'week']:
    file_path = Path(f'genome/results/historical_{period}.json')
    if file_path.exists():
        with open(file_path) as f:
            data = json.load(f)
            for t in data.get('best_trades', []):
                trades.append({
                    'symbol': t['symbol'],
                    'direction': t['direction'],
                    'gross_pnl': t['pnl_pct'],
                    'cost': TOTAL_COST * 100,
                    'net_pnl': t['pnl_pct'] - (TOTAL_COST * 100),
                    'mae': t['max_dd'] * 1.5
                })

print(f"\nTotal trades: {len(trades)}")

# Calculate metrics
gross_pnls = [t['gross_pnl'] for t in trades]
net_pnls = [t['net_pnl'] for t in trades]

wins_gross = sum(1 for p in gross_pnls if p > 0)
wins_net = sum(1 for p in net_pnls if p > 0)

print(f"\n{'='*80}")
print("  PROFIT FACTOR & EXPECTANCY")
print(f"{'='*80}")

# Profit Factor
gross_profits = sum(p for p in net_pnls if p > 0)
gross_losses = abs(sum(p for p in net_pnls if p < 0))
pf = gross_profits / gross_losses if gross_losses > 0 else 999

print(f"\nProfit Factor: {pf:.2f}")
print(f"  Gross Profits: {gross_profits:.1f}%")
print(f"  Gross Losses: {gross_losses:.1f}%")

# Win rate
wr_gross = wins_gross / len(trades)
wr_net = wins_net / len(trades)

print(f"\nWin Rate BEFORE costs: {wr_gross:.1%} ({wins_gross}/{len(trades)})")
print(f"Win Rate AFTER costs:  {wr_net:.1%} ({wins_net}/{len(trades)})")
print(f"Trades turned to losers: {wins_gross - wins_net}")

# Expectancy
avg_win = np.mean([p for p in net_pnls if p > 0]) if any(p > 0 for p in net_pnls) else 0
avg_loss = np.mean([p for p in net_pnls if p < 0]) if any(p < 0 for p in net_pnls) else 0
expectancy = (wr_net * avg_win) - ((1 - wr_net) * abs(avg_loss))

print(f"\nExpectancy per trade: {expectancy:.2f}%")
print(f"  Avg Win: {avg_win:.2f}%")
print(f"  Avg Loss: {avg_loss:.2f}%")
print(f"  Risk:Reward Ratio: 1:{abs(avg_win/avg_loss):.2f}")

print(f"\n{'='*80}")
print("  TAIL RISK (CVaR & MAE)")
print(f"{'='*80}")

# VaR and CVaR
var_95 = np.percentile(net_pnls, 5)
var_99 = np.percentile(net_pnls, 1)
cvar_95 = np.mean([p for p in net_pnls if p <= var_95]) if any(p <= var_95 for p in net_pnls) else var_95

print(f"\nValue at Risk:")
print(f"  95% VaR: {var_95:.2f}%")
print(f"  99% VaR: {var_99:.2f}%")
print(f"\nConditional VaR (Expected Shortfall):")
print(f"  CVaR 95%: {cvar_95:.2f}%")
print(f"    -> In worst 5% of trades, expect to lose {abs(cvar_95):.2f}% on average")

# MAE
maes = [t['mae'] for t in trades]
print(f"\nMaximum Adverse Excursion:")
print(f"  Average MAE: {np.mean(maes):.2f}%")
print(f"  95th percentile MAE: {np.percentile(maes, 95):.2f}%")
print(f"  Maximum MAE: {max(maes):.2f}%")

print(f"\n{'='*80}")
print("  REALISTIC MONTE CARLO (1,000 simulations)")
print(f"{'='*80}")

# Simplified Monte Carlo
n_sims = 1000
initial = 10000
final_equities = []
max_drawdowns = []

for _ in range(n_sims):
    sample = np.random.choice(net_pnls, size=len(net_pnls), replace=True)
    equity = initial
    peak = equity
    max_dd = 0
    
    for pnl in sample:
        equity *= (1 + pnl/100)
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak
        max_dd = max(max_dd, dd)
        
        if equity < initial * 0.5:  # Blow up
            break
    
    final_equities.append(equity)
    max_drawdowns.append(max_dd)

returns = [(e - initial) / initial * 100 for e in final_equities]

print(f"\nReturn Distribution:")
print(f"  5th percentile (worst): {np.percentile(returns, 5):.1f}%")
print(f"  25th percentile: {np.percentile(returns, 25):.1f}%")
print(f"  Median: {np.percentile(returns, 50):.1f}%")
print(f"  Mean: {np.mean(returns):.1f}%")
print(f"  75th percentile: {np.percentile(returns, 75):.1f}%")
print(f"  95th percentile (best): {np.percentile(returns, 95):.1f}%")

print(f"\nDrawdown Scenarios:")
print(f"  Median max DD: {np.median(max_drawdowns)*100:.1f}%")
print(f"  Worst 5% DD: {np.percentile(max_drawdowns, 95)*100:.1f}%")
print(f"  Worst 1% DD: {np.percentile(max_drawdowns, 99)*100:.1f}%")

prob_profit = sum(1 for r in returns if r > 0) / n_sims
prob_blowup = sum(1 for e in final_equities if e < initial * 0.5) / n_sims

print(f"\nRisk Metrics:")
print(f"  Probability of profit: {prob_profit:.1%}")
print(f"  Probability of blow-up (>50% loss): {prob_blowup:.2%}")

print(f"\n{'='*80}")
print("  HONEST VERDICT")
print(f"{'='*80}")

# Score
checks = []
score = 0

if pf > 1.3:
    score += 15
    checks.append("✓ Profit Factor > 1.3")
else:
    checks.append(f"✗ Profit Factor {pf:.2f} < 1.3")

if expectancy > 0:
    score += 20
    checks.append("✓ Positive Expectancy")
else:
    checks.append("✗ Negative Expectancy")

if wr_net > 0.5:
    score += 15
    checks.append("✓ Win Rate > 50%")
else:
    checks.append(f"✗ Win Rate {wr_net:.1%} < 50%")

if cvar_95 > -5:
    score += 15
    checks.append("✓ CVaR 95% > -5%")
else:
    checks.append(f"⚠ CVaR 95% {cvar_95:.2f}%")

if np.percentile(max_drawdowns, 95) < 0.30:
    score += 15
    checks.append("✓ Max DD < 30%")
else:
    checks.append(f"⚠ Max DD {np.percentile(max_drawdowns, 95)*100:.1f}%")

if prob_profit > 0.6:
    score += 10
    checks.append("✓ Prob of Profit > 60%")
else:
    checks.append(f"⚠ Prob of Profit {prob_profit:.1%}")

if prob_blowup < 0.01:
    score += 10
    checks.append("✓ Blow-up risk < 1%")
else:
    checks.append(f"⚠ Blow-up risk {prob_blowup:.2%}")

print(f"\nRealistic Readiness Score: {score}/100")
for check in checks:
    print(f"  {check}")

print(f"\n{'-'*80}")
if score >= 80:
    verdict = "GOOD - Ready for small live test with tight risk controls"
elif score >= 60:
    verdict = "MARGINAL - Paper trade only, high costs eroding edge"
else:
    verdict = "NOT READY - Strategy loses money after realistic costs"

print(f"Verdict: {verdict}")

print(f"\n{'-'*80}")
print("REALISTIC EXPECTATIONS:")
print(f"  With $10,000 capital:")
print(f"  - Median outcome: ${initial * (1 + np.percentile(returns, 50)/100):.0f}")
print(f"  - Worst 5% outcome: ${initial * (1 + np.percentile(returns, 5)/100):.0f}")
print(f"  - Expect drawdowns of {np.median(max_drawdowns)*100:.1f}% or more")
print(f"  - You will be underwater part of the time")

print(f"\n{'='*80}")

# Save
report = {
    'timestamp': datetime.now().isoformat(),
    'score': score,
    'verdict': verdict,
    'profit_factor': pf,
    'win_rate_after_costs': wr_net,
    'expectancy': expectancy,
    'cvar_95': cvar_95,
    'median_max_dd': float(np.median(max_drawdowns)),
    'worst_dd_5th': float(np.percentile(max_drawdowns, 95)),
    'prob_profit': prob_profit,
    'trades_analyzed': len(trades),
    'trades_turned_to_losers': wins_gross - wins_net
}

with open('genome/results/realistic_validation_fast.json', 'w') as f:
    json.dump(report, f, indent=2)

print("\n[Saved] genome/results/realistic_validation_fast.json")
print("="*80 + "\n")
