"""Full universe backtest — per-symbol/asset/direction breakdown for all strategies."""
import json, os
from datetime import datetime
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ─── Load all closed picks ───
FILES = [
    'alpha_engine/data/closed_picks.json',
    'battleground/data/closed_picks.json',
    'KIMI_RISEOFTHECLAW/data/closed_picks.json',
    'mercury2/data/closed_picks.json',
    'claude_gainer_ml/tracker/short_term_closed.json',
    'genome/data/closed_picks.json',
    'paper_trading/data/closed_picks.json',
    'rapid_fire_data/closed_picks.json',
    'crypto_signal_engine/data/closed_picks.json',
    'breakout_arena/approach_a_sr_breakout/data/closed_picks.json',
    'breakout_arena/approach_b_ml_breakout/data/closed_picks.json',
    'breakout_arena/approach_c_spike_reverse/data/closed_picks.json',
    'ml_battleground/ensemble_data/closed_picks.json',
    'ml_battleground/system_a_filter/data/closed_picks.json',
    'ml_battleground/system_b_regime/data/closed_picks.json',
    'ml_battleground/system_c_deeplearn/data/closed_picks.json',
    'ml_battleground/system_d_carry/data/closed_picks.json',
    'ml_battleground/system_e_momentum/data/closed_picks.json',
    'ml_battleground/system_f_clawsofdoom/data/closed_picks.json',
    'ml_crypto_predictor/enhanced_models/live_picks/closed_picks.json',
    'ml_crypto_predictor/enhanced_models/live_picks/archive_v1.2/closed_picks.json',
]

all_trades = []
for f in FILES:
    fp = os.path.join(BASE, f)
    if not os.path.exists(fp):
        continue
    try:
        data = json.load(open(fp, 'r', encoding='utf-8'))
        if not isinstance(data, list):
            continue
        all_trades.extend(data)
    except Exception:
        pass

# ─── Normalize ───
KNOWN_STOCKS = {'AAPL','MSFT','NVDA','TSLA','AMZN','GOOGL','META','AMD','SPY','QQQ','IWM',
                'PLTR','SOFI','RIVN','LCID','NIO','SNDL','GME','AMC','COIN','MSTR',
                'JPM','GS','WFC','BAC','V','MA','UNH','JNJ','PFE','ABBV','LLY',
                'WMT','HD','MCD','KO','PEP','PG','COST','BA','CAT','CVX','XOM',
                'DIS','VZ','T','NFLX','CRM'}
ETFS = {'XLK','XLF','XLE','XLV','GLD','SLV','TLT','HYG','IWM'}

def classify_asset(symbol):
    s = symbol.upper()
    if '=X' in s: return 'FOREX'
    if '=F' in s: return 'COMMODITY'
    base = s.replace('USDT','').replace('-USD','').replace('USD','')
    if base in KNOWN_STOCKS or s in KNOWN_STOCKS: return 'EQUITY'
    if base in ETFS or s in ETFS: return 'ETF'
    return 'CRYPTO'

def normalize_direction(d):
    if not d: return 'LONG'
    d = str(d).upper()
    if d in ('BUY', 'LONG'): return 'LONG'
    if d in ('SELL', 'SHORT'): return 'SHORT'
    return d

def get_pnl(t):
    for k in ['pnl_pct', 'realized_pnl_pct']:
        v = t.get(k)
        if v is not None:
            try: return float(v)
            except: pass
    return None

def get_strategy(t):
    for k in ['strategy', 'algorithm', 'strategy_name']:
        v = t.get(k)
        if v and str(v) != 'unknown':
            return str(v).lower().strip()
    return 'unknown'

normalized = []
for t in all_trades:
    pnl = get_pnl(t)
    if pnl is None:
        continue
    symbol = t.get('symbol', 'UNKNOWN')
    direction = normalize_direction(t.get('direction'))
    strategy = get_strategy(t)
    ac = t.get('asset_class', '').upper() if t.get('asset_class') else classify_asset(symbol)
    entry_date = t.get('entry_time', t.get('timestamp', t.get('opened_at', '')))
    normalized.append({
        'symbol': symbol,
        'direction': direction,
        'strategy': strategy,
        'pnl_pct': pnl,
        'asset_class': ac,
        'entry_date': str(entry_date)[:10] if entry_date else '',
        'win': pnl > 0,
    })

# ─── Helper ───
def compute_stats(trades):
    if not trades:
        return {'trades': 0, 'wr': 0, 'avg_pnl': 0, 'total_pnl': 0, 'wins': 0, 'losses': 0}
    wins = sum(1 for t in trades if t['win'])
    total = len(trades)
    avg_pnl = sum(t['pnl_pct'] for t in trades) / total
    total_pnl = sum(t['pnl_pct'] for t in trades)
    return {
        'trades': total,
        'wr': round(wins / total * 100, 2),
        'avg_pnl': round(avg_pnl, 4),
        'total_pnl': round(total_pnl, 4),
        'wins': wins,
        'losses': total - wins,
    }

# ─── Strategy categories ───
STRATEGY_CATEGORIES = {
    'rsi': ['rsi', 'connors_rsi'],
    'keltner': ['keltner'],
    'macd': ['macd'],
    'mean_reversion': ['reversion', 'mean_rev', 'bollinger', 'bb_squeeze'],
    'fear_greed': ['fear_greed'],
    'inverse': ['inverse'],
    'momentum': ['momentum'],
    'volume': ['volume', 'obv'],
}

def categorize_strategy(name):
    cats = []
    for cat, keywords in STRATEGY_CATEGORIES.items():
        for kw in keywords:
            if kw in name:
                cats.append(cat)
                break
    return cats if cats else ['other']

# ─── Group by strategy ───
by_strat = defaultdict(list)
for t in normalized:
    by_strat[t['strategy']].append(t)

# ─── Build results ───
results = {
    'generated_at': datetime.utcnow().isoformat() + 'Z',
    'total_trades_analyzed': len(normalized),
    'total_unique_symbols': len(set(t['symbol'] for t in normalized)),
    'total_unique_strategies': len(by_strat),
    'strategies': {},
    'category_summaries': {},
}

for strat_name, trades in sorted(by_strat.items(), key=lambda x: -len(x[1])):
    if len(trades) < 3:
        continue
    overall = compute_stats(trades)

    # By symbol
    by_sym = defaultdict(list)
    for t in trades:
        by_sym[t['symbol']].append(t)
    sym_stats = {}
    for sym, st in by_sym.items():
        s = compute_stats(st)
        sym_stats[sym] = {'trades': s['trades'], 'wr': s['wr'], 'avg_pnl': s['avg_pnl'], 'total_pnl': s['total_pnl']}

    # By asset class
    by_ac = defaultdict(list)
    for t in trades:
        by_ac[t['asset_class']].append(t)
    ac_stats = {}
    for ac, at in by_ac.items():
        s = compute_stats(at)
        ac_stats[ac] = {'trades': s['trades'], 'wr': s['wr'], 'avg_pnl': s['avg_pnl'], 'total_pnl': s['total_pnl']}

    # By direction
    by_dir = defaultdict(list)
    for t in trades:
        by_dir[t['direction']].append(t)
    dir_stats = {}
    for d, dt in by_dir.items():
        s = compute_stats(dt)
        dir_stats[d] = {'trades': s['trades'], 'wr': s['wr'], 'avg_pnl': s['avg_pnl'], 'total_pnl': s['total_pnl']}

    # Best/worst symbols (min 2 trades)
    scored = [(sym, s['wr'], s['avg_pnl'], s['trades']) for sym, s in sym_stats.items() if s['trades'] >= 2]
    scored.sort(key=lambda x: (-x[1], -x[2]))
    best = [{'symbol': s[0], 'wr': s[1], 'avg_pnl': s[2], 'trades': s[3]} for s in scored[:5]]
    worst = [{'symbol': s[0], 'wr': s[1], 'avg_pnl': s[2], 'trades': s[3]} for s in scored[-5:]]

    # Recommendation
    rec = []
    if overall['wr'] >= 55:
        rec.append("VIABLE: %.1f%% WR across %d trades" % (overall['wr'], overall['trades']))
    elif overall['wr'] >= 45:
        rec.append("MARGINAL: %.1f%% WR -- needs symbol filtering" % overall['wr'])
    else:
        rec.append("WEAK: %.1f%% WR -- consider inverse or kill" % overall['wr'])

    if best and best[0]['wr'] >= 60 and best[0]['trades'] >= 3:
        rec.append("Best symbol: %s (%.1f%% WR, %d trades)" % (best[0]['symbol'], best[0]['wr'], best[0]['trades']))

    if 'LONG' in dir_stats and 'SHORT' in dir_stats:
        l_s, s_s = dir_stats['LONG'], dir_stats['SHORT']
        if s_s['wr'] > l_s['wr'] + 5:
            rec.append("SHORT edge: %.1f%% vs LONG %.1f%%" % (s_s['wr'], l_s['wr']))
        elif l_s['wr'] > s_s['wr'] + 5:
            rec.append("LONG edge: %.1f%% vs SHORT %.1f%%" % (l_s['wr'], s_s['wr']))

    if len(ac_stats) > 1:
        best_ac = max(ac_stats.items(), key=lambda x: x[1]['wr'] if x[1]['trades'] >= 3 else 0)
        if best_ac[1]['trades'] >= 3:
            rec.append("Best asset class: %s (%.1f%% WR)" % (best_ac[0], best_ac[1]['wr']))

    results['strategies'][strat_name] = {
        'total_trades': overall['trades'],
        'total_wr': overall['wr'],
        'avg_pnl': overall['avg_pnl'],
        'total_pnl': overall['total_pnl'],
        'wins': overall['wins'],
        'losses': overall['losses'],
        'by_symbol': sym_stats,
        'by_asset_class': ac_stats,
        'by_direction': dir_stats,
        'best_symbols': best,
        'worst_symbols': worst,
        'categories': categorize_strategy(strat_name),
        'recommendation': ' | '.join(rec),
    }

# ─── Category summaries ───
cat_trades = defaultdict(list)
for t in normalized:
    cats = categorize_strategy(t['strategy'])
    for c in cats:
        cat_trades[c].append(t)

for cat_name, trades in cat_trades.items():
    if len(trades) < 5:
        continue
    overall = compute_stats(trades)

    by_ac = defaultdict(list)
    for t in trades:
        by_ac[t['asset_class']].append(t)
    ac_stats = {}
    for ac, at in by_ac.items():
        s = compute_stats(at)
        ac_stats[ac] = {'trades': s['trades'], 'wr': s['wr'], 'avg_pnl': s['avg_pnl']}

    by_sym = defaultdict(list)
    for t in trades:
        by_sym[t['symbol']].append(t)
    sym_perf = []
    for sym, st in by_sym.items():
        if len(st) >= 2:
            s = compute_stats(st)
            sym_perf.append({'symbol': sym, 'trades': s['trades'], 'wr': s['wr'], 'avg_pnl': s['avg_pnl']})
    sym_perf.sort(key=lambda x: (-x['wr'], -x['avg_pnl']))

    by_dir = defaultdict(list)
    for t in trades:
        by_dir[t['direction']].append(t)
    dir_stats = {}
    for d, dt in by_dir.items():
        s = compute_stats(dt)
        dir_stats[d] = {'trades': s['trades'], 'wr': s['wr'], 'avg_pnl': s['avg_pnl']}

    best_ac_item = max(ac_stats.items(), key=lambda x: x[1]['wr'] if x[1]['trades'] >= 3 else 0) if ac_stats else ('N/A', {})

    results['category_summaries'][cat_name] = {
        'total_trades': overall['trades'],
        'total_wr': overall['wr'],
        'avg_pnl': overall['avg_pnl'],
        'by_asset_class': ac_stats,
        'by_direction': dir_stats,
        'best_asset_class': best_ac_item[0] if best_ac_item[1].get('trades', 0) >= 3 else 'N/A',
        'top_5_symbols': sym_perf[:5],
        'bottom_5_symbols': sym_perf[-5:] if len(sym_perf) >= 5 else sym_perf,
    }

# ─── Write results ───
out_path = os.path.join(BASE, 'alpha_engine/data/universe_backtest_results.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print("Written to %s" % out_path)
print("Strategies analyzed: %d" % len(results['strategies']))
print("Categories analyzed: %d" % len(results['category_summaries']))
print()

# ─── Print summary ───
print("=" * 80)
print("UNIVERSE BACKTEST RESULTS SUMMARY")
print("=" * 80)
print("Total trades: %d" % results['total_trades_analyzed'])
print("Unique symbols: %d" % results['total_unique_symbols'])
print("Unique strategies: %d" % results['total_unique_strategies'])
print()

# Per-category
for cat_name in ['rsi', 'keltner', 'macd', 'mean_reversion', 'fear_greed', 'inverse', 'momentum', 'volume']:
    if cat_name not in results['category_summaries']:
        continue
    cs = results['category_summaries'][cat_name]
    print("--- %s strategies ---" % cat_name.upper())
    print("  Total: %d trades, %.1f%% WR, avg PnL: %.4f%%" % (cs['total_trades'], cs['total_wr'], cs['avg_pnl']))
    print("  Best asset class: %s" % cs['best_asset_class'])
    if cs['by_asset_class']:
        for ac, s in sorted(cs['by_asset_class'].items(), key=lambda x: -x[1]['wr']):
            print("    %s: %d trades, %.1f%% WR, avg %.4f%%" % (ac, s['trades'], s['wr'], s['avg_pnl']))
    if cs['by_direction']:
        for d, s in cs['by_direction'].items():
            print("    %s: %d trades, %.1f%% WR, avg %.4f%%" % (d, s['trades'], s['wr'], s['avg_pnl']))
    if cs['top_5_symbols']:
        print("  Top 5 symbols:")
        for s in cs['top_5_symbols']:
            print("    %s: %.1f%% WR (%d trades, avg %.4f%%)" % (s['symbol'], s['wr'], s['trades'], s['avg_pnl']))
    if cs['bottom_5_symbols']:
        print("  Bottom 5 symbols:")
        for s in cs['bottom_5_symbols']:
            print("    %s: %.1f%% WR (%d trades, avg %.4f%%)" % (s['symbol'], s['wr'], s['trades'], s['avg_pnl']))
    print()

# Key strategy deep dives
print("=" * 80)
print("KEY STRATEGY DEEP DIVES")
print("=" * 80)
key_strats = [
    'st_fear_greed_contrarian', 'st_rsi_momentum_confluence', 'macd_crossover',
    'irb_hoffman', 'quan_engine_scalp', 'ensemble', 'extreme_fear',
    'st_multi_day_momentum', 'st_obv_support_divergence', 'st_bb_squeeze_expansion',
]
for sn in key_strats:
    if sn not in results['strategies']:
        continue
    s = results['strategies'][sn]
    print()
    print("--- %s ---" % sn)
    print("  %d trades | %.1f%% WR | avg PnL: %.4f%% | total PnL: %.4f%%" % (
        s['total_trades'], s['total_wr'], s['avg_pnl'], s['total_pnl']))
    print("  Recommendation: %s" % s['recommendation'])
    if s['by_direction']:
        for d, ds in s['by_direction'].items():
            print("  %s: %d trades, %.1f%% WR, avg %.4f%%" % (d, ds['trades'], ds['wr'], ds['avg_pnl']))
    if s['by_asset_class']:
        for ac, acs in sorted(s['by_asset_class'].items(), key=lambda x: -x[1]['wr']):
            print("  [%s]: %d trades, %.1f%% WR" % (ac, acs['trades'], acs['wr']))
    if s['best_symbols']:
        print("  Best: %s" % ', '.join("%s(%.0f%%)" % (b['symbol'], b['wr']) for b in s['best_symbols'][:3]))
    if s['worst_symbols']:
        print("  Worst: %s" % ', '.join("%s(%.0f%%)" % (b['symbol'], b['wr']) for b in s['worst_symbols'][:3]))

# Inverse strategies
print()
print("=" * 80)
print("INVERSE STRATEGIES")
print("=" * 80)
for sn, s in results['strategies'].items():
    if 'inverse' not in sn:
        continue
    print("  %s: %d trades, %.1f%% WR, avg %.4f%% | %s" % (
        sn, s['total_trades'], s['total_wr'], s['avg_pnl'], s['recommendation']))

# RSI cross-asset
print()
print("=" * 80)
print("RSI STRATEGIES: CROSS-ASSET COMPARISON")
print("=" * 80)
rsi_strats = [sn for sn in results['strategies'] if 'rsi' in sn]
for sn in rsi_strats:
    s = results['strategies'][sn]
    acs = s['by_asset_class']
    ac_str = ', '.join("%s:%.1f%%(%d)" % (ac, v['wr'], v['trades']) for ac, v in sorted(acs.items(), key=lambda x: -x[1]['wr']))
    print("  %s: %.1f%% WR (%d) | %s" % (sn, s['total_wr'], s['total_trades'], ac_str))

# Keltner
print()
print("=" * 80)
print("KELTNER STRATEGIES: PER-SYMBOL")
print("=" * 80)
keltner_strats = [sn for sn in results['strategies'] if 'keltner' in sn]
for sn in keltner_strats:
    s = results['strategies'][sn]
    print("  %s: %.1f%% WR (%d)" % (sn, s['total_wr'], s['total_trades']))
    for sym, ss in sorted(s['by_symbol'].items(), key=lambda x: -x[1]['wr']):
        print("    %s: %.1f%% WR (%d trades, avg %.4f%%)" % (sym, ss['wr'], ss['trades'], ss['avg_pnl']))

print()
print("Done.")
