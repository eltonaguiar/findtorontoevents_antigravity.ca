import json
from datetime import datetime

def extract_summary(filepath):
    """Extract summary from a backtest JSON file."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    if not data.get('ok'):
        return None
    return data.get('summary', {}), data.get('params', {}), data.get('trades', [])

def compute_per_algo(trades):
    """Compute per-algorithm stats from trades list."""
    algo_trades = {}
    for t in trades:
        algo = t.get('algorithm', 'Unknown')
        if algo not in algo_trades:
            algo_trades[algo] = []
        algo_trades[algo].append(t)

    results = []
    for algo, atrades in algo_trades.items():
        wins = [t for t in atrades if t.get('net_profit', t.get('gross_profit', 0)) > 0]
        losses = [t for t in atrades if t.get('net_profit', t.get('gross_profit', 0)) <= 0]
        total = len(atrades)
        win_count = len(wins)
        win_rate = (win_count / total * 100) if total > 0 else 0

        returns = [t.get('return_pct', 0) for t in atrades]
        avg_return = sum(returns) / len(returns) if returns else 0

        win_returns = [t.get('return_pct', 0) for t in wins]
        loss_returns = [t.get('return_pct', 0) for t in losses]
        avg_win = sum(win_returns) / len(win_returns) if win_returns else 0
        avg_loss = sum(loss_returns) / len(loss_returns) if loss_returns else 0

        gross_wins = sum(t.get('net_profit', t.get('gross_profit', 0)) for t in wins)
        gross_losses = abs(sum(t.get('net_profit', t.get('gross_profit', 0)) for t in losses))
        pf = round(gross_wins / gross_losses, 4) if gross_losses > 0 else None

        results.append({
            'algorithm': algo,
            'total_trades': total,
            'winning_trades': win_count,
            'losing_trades': len(losses),
            'win_rate': round(win_rate, 2),
            'avg_return_pct': round(avg_return, 4),
            'avg_win_pct': round(avg_win, 4),
            'avg_loss_pct': round(avg_loss, 4),
            'profit_factor': pf,
        })

    return sorted(results, key=lambda x: -x['win_rate'])

BASE = 'e:/findtorontoevents_antigravity.ca/data/'

summary = {
    "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
    "description": "Comprehensive backtest results from production APIs at findtorontoevents.ca",
    "data_source": "findstocks/api/backtest.php, whatif.php, horizon_picks.php, short_backtest.php, penny_stocks.php",
    "sections": {}
}

# SECTION 1: Individual Algorithm Backtests (10% TP / 5% SL / 7d)
section1 = {
    "label": "Individual Algorithm Backtests (10% TP / 5% SL / 7-day hold)",
    "params": {"take_profit_pct": 10, "stop_loss_pct": 5, "max_hold_days": 7, "initial_capital": 10000, "fee_model": "questrade"},
    "results": []
}

for fname, algo_name in [
    ('algo_cursor_genius.json', 'Cursor Genius'),
    ('algo_blue_chip.json', 'Blue Chip Growth'),
    ('algo_composite_rating.json', 'Composite Rating'),
    ('algo_sector_momentum.json', 'Sector Momentum'),
    ('algo_etf_masters.json', 'ETF Masters'),
    ('algo_sector_rotation.json', 'Sector Rotation'),
    ('algo_tech_momentum.json', 'Technical Momentum'),
]:
    result = extract_summary(BASE + fname)
    if result:
        s, p, _ = result
        section1['results'].append({
            'algorithm': algo_name,
            'win_rate': s.get('win_rate'),
            'total_trades': s.get('total_trades'),
            'total_return_pct': s.get('total_return_pct'),
            'final_value': s.get('final_value'),
            'avg_win_pct': s.get('avg_win_pct'),
            'avg_loss_pct': s.get('avg_loss_pct'),
            'sharpe_ratio': s.get('sharpe_ratio'),
            'sortino_ratio': s.get('sortino_ratio'),
            'max_drawdown_pct': s.get('max_drawdown_pct'),
            'profit_factor': s.get('profit_factor'),
            'expectancy': s.get('expectancy'),
            'total_commissions': s.get('total_commissions'),
        })

section1['results'].sort(key=lambda x: -(x.get('win_rate') or 0))
summary['sections']['individual_algo_backtests_7d'] = section1

# SECTION 2: Cursor Genius Swing Trade (20% TP / 8% SL / 20d)
result = extract_summary(BASE + 'algo_cursor_genius_swing.json')
if result:
    s, p, _ = result
    summary['sections']['cursor_genius_swing_20d'] = {
        "label": "Cursor Genius Swing Trade (20% TP / 8% SL / 20-day hold)",
        "params": {"take_profit_pct": 20, "stop_loss_pct": 8, "max_hold_days": 20, "initial_capital": 10000, "fee_model": "questrade"},
        "result": {
            'algorithm': 'Cursor Genius',
            'win_rate': s.get('win_rate'),
            'total_trades': s.get('total_trades'),
            'total_return_pct': s.get('total_return_pct'),
            'final_value': s.get('final_value'),
            'avg_win_pct': s.get('avg_win_pct'),
            'avg_loss_pct': s.get('avg_loss_pct'),
            'sharpe_ratio': s.get('sharpe_ratio'),
            'sortino_ratio': s.get('sortino_ratio'),
            'max_drawdown_pct': s.get('max_drawdown_pct'),
            'profit_factor': s.get('profit_factor'),
            'expectancy': s.get('expectancy'),
        }
    }

# SECTION 3: Blue Chip Growth Buy-Hold 90d
result = extract_summary(BASE + 'algo_blue_chip_90d.json')
if result:
    s, p, _ = result
    summary['sections']['blue_chip_buyhold_90d'] = {
        "label": "Blue Chip Growth Buy-Hold 90 Days (no TP/SL)",
        "params": {"take_profit_pct": 999, "stop_loss_pct": 999, "max_hold_days": 90, "initial_capital": 10000, "fee_model": "questrade"},
        "result": {
            'algorithm': 'Blue Chip Growth',
            'win_rate': s.get('win_rate'),
            'total_trades': s.get('total_trades'),
            'total_return_pct': s.get('total_return_pct'),
            'final_value': s.get('final_value'),
            'avg_win_pct': s.get('avg_win_pct'),
            'avg_loss_pct': s.get('avg_loss_pct'),
            'sharpe_ratio': s.get('sharpe_ratio'),
            'sortino_ratio': s.get('sortino_ratio'),
            'max_drawdown_pct': s.get('max_drawdown_pct'),
            'profit_factor': s.get('profit_factor'),
            'expectancy': s.get('expectancy'),
        }
    }

# SECTION 4: All Algos - 3 Strategy Profiles (Aggregate + Per-Algo)
section4 = {
    "label": "All Algorithms Combined - Multiple Strategy Profiles",
    "profiles": []
}

for fname, profile_name, tp, sl, mhd in [
    ('backtest_custom.json', 'Day Trade / Scalp', 5, 3, 1),
    ('backtest_swing.json', 'Swing Trade', 20, 8, 20),
    ('backtest_buyhold_180d.json', 'Buy and Hold (180d)', 999, 999, 180),
]:
    result = extract_summary(BASE + fname)
    if result:
        s, p, trades = result
        per_algo = compute_per_algo(trades)
        section4['profiles'].append({
            'profile': profile_name,
            'params': {'take_profit_pct': tp, 'stop_loss_pct': sl, 'max_hold_days': mhd},
            'aggregate': {
                'win_rate': s.get('win_rate'),
                'total_trades': s.get('total_trades'),
                'total_return_pct': s.get('total_return_pct'),
                'final_value': s.get('final_value'),
                'sharpe_ratio': s.get('sharpe_ratio'),
                'max_drawdown_pct': s.get('max_drawdown_pct'),
                'profit_factor': s.get('profit_factor'),
                'expectancy': s.get('expectancy'),
                'avg_win_pct': s.get('avg_win_pct'),
                'avg_loss_pct': s.get('avg_loss_pct'),
            },
            'per_algorithm': per_algo,
        })

summary['sections']['all_algos_strategy_profiles'] = section4

# SECTION 5: What-If Scenario Comparison (19 scenarios)
with open(BASE + 'whatif_comparison.json', 'r') as f:
    whatif_data = json.load(f)

section5 = {
    "label": "What-If Scenario Comparison (19 Scenarios)",
    "scenarios": []
}

if whatif_data.get('ok'):
    for sc in whatif_data.get('scenarios', []):
        s = sc.get('summary', {})
        section5['scenarios'].append({
            'scenario_key': sc.get('scenario_key'),
            'name': sc.get('name'),
            'description': sc.get('description'),
            'params': sc.get('params'),
            'win_rate': s.get('win_rate'),
            'total_trades': s.get('total_trades'),
            'total_return_pct': s.get('total_return_pct'),
            'final_value': s.get('final_value'),
            'max_drawdown_pct': s.get('max_drawdown_pct'),
            'sharpe_ratio': s.get('sharpe_ratio'),
            'profit_factor': s.get('profit_factor'),
            'expectancy': s.get('expectancy'),
        })

section5['scenarios'].sort(key=lambda x: -(x.get('win_rate') or 0))
summary['sections']['whatif_scenario_comparison'] = section5

# SECTION 6: Short Backtest
with open(BASE + 'short_backtest.json', 'r') as f:
    short_data = json.load(f)

if short_data.get('ok'):
    s = short_data.get('summary', {})
    regime = short_data.get('regime_breakdown', {})
    summary['sections']['short_backtest'] = {
        "label": "Short Selling Backtest (10% TP / 5% SL / 7-day hold)",
        "params": {"take_profit_pct": 10, "stop_loss_pct": 5, "max_hold_days": 7, "direction": "SHORT"},
        "result": {
            'win_rate': s.get('win_rate'),
            'total_trades': s.get('total_trades'),
            'total_return_pct': s.get('total_return_pct'),
            'final_value': s.get('final_value'),
            'max_drawdown_pct': s.get('max_drawdown_pct'),
            'sharpe_ratio': s.get('sharpe_ratio'),
            'profit_factor': s.get('profit_factor'),
            'total_commissions': s.get('total_commissions'),
        },
        "regime_breakdown": regime,
    }

# SECTION 7: Horizon Picks with Backtests
with open(BASE + 'horizon_backtests.json', 'r') as f:
    horizon_data = json.load(f)

section7 = {
    "label": "Horizon Picks with Inline Backtests (3 time horizons)",
    "horizons": []
}

if horizon_data.get('ok'):
    for h in horizon_data.get('horizons', []):
        bt = h.get('backtest', {})
        section7['horizons'].append({
            'horizon': h.get('name'),
            'subtitle': h.get('subtitle'),
            'risk_level': h.get('risk_level'),
            'params': {'tp_pct': h.get('tp_pct'), 'sl_pct': h.get('sl_pct'), 'hold_days': h.get('hold_days')},
            'backtest': {
                'total_trades': bt.get('total_trades'),
                'win_rate': bt.get('win_rate'),
                'avg_win_pct': bt.get('avg_win_pct'),
                'avg_loss_pct': bt.get('avg_loss_pct'),
                'avg_return_pct': bt.get('avg_return_pct'),
                'best_trade_pct': bt.get('best_trade_pct'),
                'worst_trade_pct': bt.get('worst_trade_pct'),
            },
            'projection_1000': bt.get('projection_1000'),
            'pick_count': h.get('pick_count'),
        })

summary['sections']['horizon_picks'] = section7

# SECTION 8: Grand Ranking - All algorithms sorted by win rate across all strategies
grand_ranking = []

for fname, tp, sl, mhd, strat_label in [
    ('backtest_swing.json', 20, 8, 20, 'Swing (20/8/20)'),
    ('backtest_buyhold_180d.json', 999, 999, 180, 'Buy-Hold (180d)'),
    ('backtest_custom.json', 5, 3, 1, 'Scalp (5/3/1)'),
]:
    result = extract_summary(BASE + fname)
    if result:
        _, _, trades = result
        per_algo = compute_per_algo(trades)
        for a in per_algo:
            grand_ranking.append({
                'algorithm': a['algorithm'],
                'strategy': strat_label,
                'params': {'tp': tp, 'sl': sl, 'max_hold': mhd},
                'win_rate': a['win_rate'],
                'total_trades': a['total_trades'],
                'avg_return_pct': a['avg_return_pct'],
                'profit_factor': a['profit_factor'],
            })

grand_ranking.sort(key=lambda x: (-x['win_rate'], -(x.get('profit_factor') or 0)))
summary['sections']['grand_ranking'] = {
    "label": "Grand Ranking - All Algorithms x All Strategies (sorted by win rate desc)",
    "note": "Win rate alone is not sufficient - check profit_factor and avg_return_pct for edge quality",
    "entries": grand_ranking
}

# SECTION 9: Penny Stocks Summary
with open(BASE + 'penny_stocks.json', 'r') as f:
    penny_data = json.load(f)

summary['sections']['penny_stocks'] = {
    "label": "Penny Stocks (Canadian, under $5)",
    "total_found": penny_data.get('total'),
    "returned": penny_data.get('count'),
    "top_5_by_volume": [
        {
            'symbol': s['symbol'],
            'name': s['name'],
            'price': s['price'],
            'change_pct': s['change_pct'],
            'volume': s['volume'],
        }
        for s in penny_data.get('stocks', [])[:5]
    ]
}

# SECTION 10: Failed API calls
summary['sections']['failed_apis'] = {
    "label": "Failed or Unavailable API Calls",
    "entries": [
        {
            "endpoint": "backtest.php?algorithms=Challenger%20Bot",
            "error": "No picks found for the selected algorithms. Import picks first.",
            "note": "Challenger Bot is only available in the live-monitor, not in the historical backtest system"
        },
        {
            "endpoint": "portfolio2/api/whatif.php?compare=1",
            "error": "500 Internal Server Error (timed out at /fc/ path, worked at /findstocks/api/ path)",
            "note": "The whatif.php in portfolio2 has server-side issues; use findstocks/api/whatif.php instead"
        }
    ]
}

# Write the summary
with open(BASE + 'backtest_summary.json', 'w') as f:
    json.dump(summary, f, indent=2)

print("Summary written successfully!")
print(f"File: {BASE}backtest_summary.json")
print(f"Sections: {list(summary['sections'].keys())}")
print(f"Grand ranking entries: {len(grand_ranking)}")
print(f"What-if scenarios: {len(section5['scenarios'])}")
print(f"Strategy profiles: {len(section4['profiles'])}")
print()

# Print key findings
print("=" * 70)
print("KEY FINDINGS")
print("=" * 70)

print("\n--- TOP 10 by Win Rate (Grand Ranking) ---")
for i, e in enumerate(grand_ranking[:10]):
    pf_str = f"PF={e['profit_factor']}" if e['profit_factor'] is not None else "PF=N/A"
    print(f"  {i+1:2d}. {e['algorithm']:40s} ({e['strategy']:16s}): WR={e['win_rate']:6.2f}%, AvgRet={e['avg_return_pct']:8.4f}%, {pf_str}")

print("\n--- TOP 5 What-If Scenarios ---")
for i, sc in enumerate(section5['scenarios'][:5]):
    print(f"  {i+1}. {sc['name']:35s}: WR={sc['win_rate']:6.2f}%, Return={sc['total_return_pct']:>15.4f}%, Sharpe={sc['sharpe_ratio']:8.4f}")

print("\n--- Horizon Picks Backtests ---")
for h in section7['horizons']:
    bt = h['backtest']
    print(f"  {h['horizon']:20s} ({h['subtitle']:12s}): WR={bt['win_rate']:6.1f}%, AvgRet={bt['avg_return_pct']:6.2f}%, BestTrade={bt['best_trade_pct']}%, WorstTrade={bt['worst_trade_pct']}%")

print("\n--- Short Selling Result ---")
short_r = summary['sections']['short_backtest']['result']
print(f"  Win Rate: {short_r['win_rate']}%, Return: {short_r['total_return_pct']}%, Sharpe: {short_r['sharpe_ratio']}")
print(f"  Regime breakdown: Bull WR={regime.get('bull',{}).get('win_rate',0)}%, Bear WR={regime.get('bear',{}).get('win_rate',0)}%, Sideways WR={regime.get('sideways',{}).get('win_rate',0)}%")

print("\n--- Strategy Profile Comparison (All Algos) ---")
for p in section4['profiles']:
    a = p['aggregate']
    print(f"  {p['profile']:25s}: WR={a['win_rate']:6.2f}%, Return={a['total_return_pct']:>15.4f}%, Sharpe={a['sharpe_ratio']:8.4f}, MaxDD={a['max_drawdown_pct']:6.2f}%")
