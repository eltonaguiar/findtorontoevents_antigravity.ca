#!/usr/bin/env python3
"""
Consensus Accuracy Tracker
===========================
Measures whether strategy consensus actually predicts winning trades.

Critical finding from 2000 closed picks:
  1 system agreement:  41.1% WR (1965 trades)
  2-3 systems:         33.3% WR (24 trades)
  4-7 systems:         20.0% WR (10 trades)
  8+ systems:           0.0% WR (1 trade)

MORE consensus = WORSE results. This tracker investigates WHY and finds
what ACTUALLY predicts multi-system success (strategy family diversity,
trust tier diversity, direction+asset class).

Output: alpha_engine/data/consensus_accuracy.json
"""
import sys
import os
import io
import json
from datetime import datetime, timezone
from collections import defaultdict

# ── Windows UTF-8 fix ──
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ── Paths ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
CLOSED_PICKS_PATH = os.path.join(SCRIPT_DIR, 'data', 'closed_picks.json')
ACTIVE_PICKS_PATH = os.path.join(SCRIPT_DIR, 'data', 'active_picks.json')
CONSENSUS_MATRIX_PATH = os.path.join(SCRIPT_DIR, 'data', 'strategy_consensus_matrix.json')
OUTPUT_PATH = os.path.join(SCRIPT_DIR, 'data', 'consensus_accuracy.json')

# ── Strategy family mapping (imported from config.py) ──
try:
    sys.path.insert(0, SCRIPT_DIR)
    from config import STRATEGY_FAMILIES
except ImportError:
    STRATEGY_FAMILIES = {}


def norm_symbol(s):
    """Normalize symbol to XXXUSDT format."""
    s = (s or '').upper().replace('-', '').split('/')[0]
    if s.endswith('USD') and not s.endswith('USDT'):
        s += 'T'
    if not s.endswith('USDT') and not s.endswith('USD'):
        s += 'USDT'
    return s


def infer_direction(pick):
    """Infer LONG/SHORT from a pick record."""
    d = (pick.get('direction', '') or '').upper()
    if d in ('LONG', 'SHORT'):
        return d
    sig = (pick.get('signal_type', '') or '').upper()
    if sig in ('BUY', 'LONG'):
        return 'LONG'
    if sig in ('SELL', 'SHORT'):
        return 'SHORT'
    return 'LONG'  # default


def get_family(strategy_name):
    """Get strategy family from STRATEGY_FAMILIES map, with heuristic fallback."""
    if strategy_name in STRATEGY_FAMILIES:
        return STRATEGY_FAMILIES[strategy_name]
    # Heuristic: infer from name keywords (order matters — more specific first)
    name = strategy_name.lower()
    # ML-enhanced strategies: classify by the model type
    if name.startswith('ml_enhanced'):
        return 'ml_model'
    # Copy trader / social-derived picks
    if any(kw in name for kw in ('copy_', 'hl_', 'binance_smart_money')):
        return 'copy_trader'
    # Backfill variants are derived from their base strategy
    if 'volume_spike' in name:
        return 'volume'
    if 'ema_crossover' in name:
        return 'trend'
    if 'rsi_bounce' in name or 'rsi' in name:
        return 'momentum'
    if 'winner_pattern' in name or 'precursor' in name:
        return 'structure'
    if any(kw in name for kw in ('momentum', 'macd', 'crossover', 'cross_sectional', 'gainer')):
        return 'momentum'
    if any(kw in name for kw in ('ema', 'sma', 'ichimoku', 'trend', 'hull', 'adx', 'kalman',
                                  'cusum', 'hoffman')):
        return 'trend'
    if any(kw in name for kw in ('volume', 'obv', 'vwap', 'cmf', 'mfi', 'vpin', 'ofi', 'spike')):
        return 'volume'
    if any(kw in name for kw in ('fear', 'greed', 'sentiment', 'funding', 'social', 'carry',
                                  'news', 'cyclic')):
        return 'sentiment'
    if any(kw in name for kw in ('mvrv', 'hash', 'whale', 'onchain', 'chain', 'netflow',
                                  'stablecoin', 'smart_money')):
        return 'on_chain'
    if any(kw in name for kw in ('sr_', 'fvg', 'bos', 'wyckoff', 'swing', 'fractal',
                                  'pattern', 'head_shoulders')):
        return 'structure'
    if any(kw in name for kw in ('bollinger', 'keltner', 'atr', 'squeeze', 'volatility',
                                  'sigma', 'reversion')):
        return 'volatility'
    return 'unknown'


def get_asset_class(symbol):
    """Infer asset class from symbol."""
    sym = (symbol or '').upper()
    forex_pairs = {'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'NZDUSD',
                   'USDCHF', 'EURGBP', 'EURJPY', 'GBPJPY'}
    if sym.replace('T', '') in forex_pairs or sym in forex_pairs:
        return 'forex'
    equity_syms = {'AAPL', 'MSFT', 'TSLA', 'NVDA', 'AMZN', 'GOOGL', 'META',
                   'SPY', 'QQQ', 'IWM', 'DIA'}
    base = sym.replace('USDT', '').replace('USD', '')
    if base in equity_syms:
        return 'equity'
    return 'crypto'


def load_json(path):
    """Load JSON file, return empty list/dict on failure."""
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def classify_outcome(pick):
    """Return (is_win, pnl_pct) for a closed pick."""
    pnl = float(pick.get('pnl_pct', 0) or 0)
    status = (pick.get('status', '') or pick.get('outcome', '') or '').upper()
    is_win = pnl > 0 or status in ('WON', 'WIN', 'TP_HIT', 'CLOSED_TP')
    return is_win, pnl


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1: Backtest historical consensus from closed picks
# ─────────────────────────────────────────────────────────────────────────────

def backtest_consensus(closed_picks):
    """
    Reconstruct consensus at entry time.
    Group closed picks by (symbol, direction, entry_date).
    Picks entered on the same day for the same symbol+direction = consensus.
    """
    # Group by (symbol, direction, entry_date)
    groups = defaultdict(list)
    for p in closed_picks:
        sym = norm_symbol(p.get('symbol', ''))
        direction = infer_direction(p)
        entry_date = (p.get('entry_date', '') or '')[:10]
        if not entry_date or not sym:
            continue
        # Skip auto-expired noise
        if p.get('_auto_expired') and abs(float(p.get('pnl_pct', 0) or 0)) < 0.001:
            continue
        groups[(sym, direction, entry_date)].append(p)

    # ── Analysis 1: By raw agreement count ──
    by_agreement = defaultdict(lambda: {'trades': 0, 'wins': 0, 'pnl': 0.0})

    # ── Analysis 2: By strategy family diversity ──
    by_family_diversity = defaultdict(lambda: {'trades': 0, 'wins': 0, 'pnl': 0.0})

    # ── Analysis 3: By direction + asset class ──
    by_dir_asset = defaultdict(lambda: {'trades': 0, 'wins': 0, 'pnl': 0.0})

    # ── Analysis 4: By source_system diversity ──
    by_source_diversity = defaultdict(lambda: {'trades': 0, 'wins': 0, 'pnl': 0.0})

    for (sym, direction, entry_date), picks_in_group in groups.items():
        agreement_count = len(picks_in_group)

        # Categorize agreement level
        if agreement_count == 1:
            agreement_bucket = '1'
        elif agreement_count <= 3:
            agreement_bucket = '2-3'
        elif agreement_count <= 7:
            agreement_bucket = '4-7'
        else:
            agreement_bucket = '8+'

        # Strategy families present
        families = set()
        sources = set()
        for p in picks_in_group:
            strat = p.get('strategy', '')
            families.add(get_family(strat))
            src = p.get('source_system', '')
            if src:
                sources.add(str(src))

        family_count = len(families - {'unknown'}) or 1
        if family_count == 1:
            family_bucket = '1_family'
        elif family_count == 2:
            family_bucket = '2_families'
        else:
            family_bucket = '3+_families'

        source_count = len(sources)
        if source_count <= 1:
            source_bucket = '1_source'
        elif source_count == 2:
            source_bucket = '2_sources'
        else:
            source_bucket = '3+_sources'

        asset_class = get_asset_class(sym)
        dir_asset_key = f"{direction}_{asset_class}"

        # Score each pick individually but attribute to group characteristics
        for p in picks_in_group:
            is_win, pnl = classify_outcome(p)

            by_agreement[agreement_bucket]['trades'] += 1
            if is_win:
                by_agreement[agreement_bucket]['wins'] += 1
            by_agreement[agreement_bucket]['pnl'] += pnl

            by_family_diversity[family_bucket]['trades'] += 1
            if is_win:
                by_family_diversity[family_bucket]['wins'] += 1
            by_family_diversity[family_bucket]['pnl'] += pnl

            by_dir_asset[dir_asset_key]['trades'] += 1
            if is_win:
                by_dir_asset[dir_asset_key]['wins'] += 1
            by_dir_asset[dir_asset_key]['pnl'] += pnl

            by_source_diversity[source_bucket]['trades'] += 1
            if is_win:
                by_source_diversity[source_bucket]['wins'] += 1
            by_source_diversity[source_bucket]['pnl'] += pnl

    def finalize(d):
        result = {}
        for k, v in sorted(d.items()):
            wr = (v['wins'] / v['trades'] * 100) if v['trades'] > 0 else 0
            result[k] = {
                'trades': v['trades'],
                'wins': v['wins'],
                'wr': round(wr, 1),
                'pnl': round(v['pnl'], 2),
                'avg_pnl': round(v['pnl'] / v['trades'], 4) if v['trades'] > 0 else 0,
            }
        return result

    return {
        'by_agreement_count': finalize(by_agreement),
        'by_strategy_diversity': finalize(by_family_diversity),
        'by_direction_asset': finalize(by_dir_asset),
        'by_source_diversity': finalize(by_source_diversity),
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: Detailed family-level analysis
# ─────────────────────────────────────────────────────────────────────────────

def analyze_family_combinations(closed_picks):
    """
    For groups with 2+ picks, track which family COMBINATIONS win most.
    E.g., momentum+structure might beat momentum+momentum.
    """
    groups = defaultdict(list)
    for p in closed_picks:
        sym = norm_symbol(p.get('symbol', ''))
        direction = infer_direction(p)
        entry_date = (p.get('entry_date', '') or '')[:10]
        if not entry_date or not sym:
            continue
        if p.get('_auto_expired') and abs(float(p.get('pnl_pct', 0) or 0)) < 0.001:
            continue
        groups[(sym, direction, entry_date)].append(p)

    combo_stats = defaultdict(lambda: {'trades': 0, 'wins': 0, 'pnl': 0.0})
    same_vs_diverse = {'same_family': {'trades': 0, 'wins': 0, 'pnl': 0.0},
                       'diverse_families': {'trades': 0, 'wins': 0, 'pnl': 0.0}}

    for (sym, direction, entry_date), picks_in_group in groups.items():
        if len(picks_in_group) < 2:
            continue

        families = sorted(set(get_family(p.get('strategy', '')) for p in picks_in_group))
        families = [f for f in families if f != 'unknown']
        if not families:
            continue

        combo_key = '+'.join(families)
        is_diverse = len(families) >= 2

        for p in picks_in_group:
            is_win, pnl = classify_outcome(p)
            combo_stats[combo_key]['trades'] += 1
            if is_win:
                combo_stats[combo_key]['wins'] += 1
            combo_stats[combo_key]['pnl'] += pnl

            cat = 'diverse_families' if is_diverse else 'same_family'
            same_vs_diverse[cat]['trades'] += 1
            if is_win:
                same_vs_diverse[cat]['wins'] += 1
            same_vs_diverse[cat]['pnl'] += pnl

    # Top combos by trade count (need statistical significance)
    combos_list = []
    for combo, stats in sorted(combo_stats.items(), key=lambda x: -x[1]['trades']):
        if stats['trades'] < 3:
            continue
        wr = stats['wins'] / stats['trades'] * 100 if stats['trades'] > 0 else 0
        combos_list.append({
            'families': combo,
            'trades': stats['trades'],
            'wins': stats['wins'],
            'wr': round(wr, 1),
            'pnl': round(stats['pnl'], 2),
        })

    # Same vs diverse summary
    svd_result = {}
    for k, v in same_vs_diverse.items():
        wr = v['wins'] / v['trades'] * 100 if v['trades'] > 0 else 0
        svd_result[k] = {
            'trades': v['trades'],
            'wins': v['wins'],
            'wr': round(wr, 1),
            'pnl': round(v['pnl'], 2),
        }

    return {
        'top_family_combinations': combos_list[:20],
        'same_vs_diverse': svd_result,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: Per-strategy family performance
# ─────────────────────────────────────────────────────────────────────────────

def analyze_family_performance(closed_picks):
    """Which strategy families have the best solo performance?"""
    family_stats = defaultdict(lambda: {'trades': 0, 'wins': 0, 'pnl': 0.0})

    for p in closed_picks:
        if p.get('_auto_expired') and abs(float(p.get('pnl_pct', 0) or 0)) < 0.001:
            continue
        strat = p.get('strategy', '')
        family = get_family(strat)
        is_win, pnl = classify_outcome(p)
        family_stats[family]['trades'] += 1
        if is_win:
            family_stats[family]['wins'] += 1
        family_stats[family]['pnl'] += pnl

    result = {}
    for fam, stats in sorted(family_stats.items(), key=lambda x: -x[1]['trades']):
        wr = stats['wins'] / stats['trades'] * 100 if stats['trades'] > 0 else 0
        result[fam] = {
            'trades': stats['trades'],
            'wins': stats['wins'],
            'wr': round(wr, 1),
            'pnl': round(stats['pnl'], 2),
            'avg_pnl': round(stats['pnl'] / stats['trades'], 4) if stats['trades'] > 0 else 0,
        }
    return result


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4: Active picks consensus snapshot (for tracking over time)
# ─────────────────────────────────────────────────────────────────────────────

def snapshot_active_consensus(active_picks):
    """
    Record current consensus state for active picks.
    When these close, we can compare: did high-consensus picks actually win?
    """
    groups = defaultdict(list)
    for p in active_picks:
        sym = norm_symbol(p.get('symbol', ''))
        direction = infer_direction(p)
        strat = p.get('strategy', '')
        if not strat or not sym:
            continue
        groups[(sym, direction)].append({
            'strategy': strat,
            'family': get_family(strat),
            'confidence': p.get('confidence'),
            'entry_price': p.get('entry_price'),
            'source_system': p.get('source_system', ''),
        })

    snapshot = {}
    for (sym, direction), signals in groups.items():
        families = set(s['family'] for s in signals if s['family'] != 'unknown')
        sources = set(str(s['source_system']) for s in signals if s['source_system'])
        snapshot[f"{sym}_{direction}"] = {
            'symbol': sym,
            'direction': direction,
            'strategy_count': len(signals),
            'family_count': len(families),
            'source_count': len(sources),
            'families': sorted(families),
            'strategies': [s['strategy'] for s in signals],
            'snapshot_time': datetime.now(timezone.utc).isoformat(),
        }

    return snapshot


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5: Generate verdict and recommendations
# ─────────────────────────────────────────────────────────────────────────────

def generate_verdict(backtest, family_combos, family_perf):
    """Produce an actionable verdict from the data."""
    agreement = backtest.get('by_agreement_count', {})
    diversity = backtest.get('by_strategy_diversity', {})

    # Check if raw count is anti-predictive
    wr_by_agreement = []
    for bucket in ['1', '2-3', '4-7', '8+']:
        data = agreement.get(bucket, {})
        if data.get('trades', 0) >= 3:
            wr_by_agreement.append((bucket, data['wr'], data['trades']))

    raw_count_declining = False
    if len(wr_by_agreement) >= 2:
        # Check if WR decreases as agreement increases
        wrs = [x[1] for x in wr_by_agreement]
        declining_pairs = sum(1 for i in range(len(wrs) - 1) if wrs[i] > wrs[i + 1])
        raw_count_declining = declining_pairs >= (len(wrs) - 1) * 0.5

    # Check if family diversity IS predictive
    div_1 = diversity.get('1_family', {})
    div_2 = diversity.get('2_families', {})
    div_3 = diversity.get('3+_families', {})

    diversity_helps = False
    div_wr_1 = div_1.get('wr', 0) if div_1.get('trades', 0) >= 10 else None
    div_wr_2 = div_2.get('wr', 0) if div_2.get('trades', 0) >= 5 else None
    div_wr_3 = div_3.get('wr', 0) if div_3.get('trades', 0) >= 3 else None

    if div_wr_1 is not None and div_wr_2 is not None:
        diversity_helps = div_wr_2 > div_wr_1
    if div_wr_3 is not None and div_wr_1 is not None:
        diversity_helps = diversity_helps or (div_wr_3 > div_wr_1)

    # Same vs diverse from family_combos
    svd = family_combos.get('same_vs_diverse', {})
    same_wr = svd.get('same_family', {}).get('wr', 0)
    diverse_wr = svd.get('diverse_families', {}).get('wr', 0)
    same_trades = svd.get('same_family', {}).get('trades', 0)
    diverse_trades = svd.get('diverse_families', {}).get('trades', 0)

    # Best and worst families
    best_family = None
    worst_family = None
    for fam, stats in family_perf.items():
        if stats['trades'] < 10:
            continue
        if best_family is None or stats['wr'] > family_perf.get(best_family, {}).get('wr', 0):
            best_family = fam
        if worst_family is None or stats['wr'] < family_perf.get(worst_family, {}).get('wr', 0):
            worst_family = fam

    # Build verdict
    lines = []

    if raw_count_declining:
        lines.append("Raw consensus count is ANTI-PREDICTIVE: more systems agreeing = worse win rate.")
    else:
        lines.append("Raw consensus count shows no clear positive signal.")

    if diversity_helps:
        wr1_str = f"{div_wr_1:.1f}%" if div_wr_1 is not None else "N/A"
        wr2_str = f"{div_wr_2:.1f}%" if div_wr_2 is not None else "N/A"
        wr3_str = f"{div_wr_3:.1f}%" if div_wr_3 is not None else "N/A"
        lines.append(
            f"Strategy FAMILY diversity IS predictive: "
            f"1 family={wr1_str}, 2 families={wr2_str}, 3+ families={wr3_str}."
        )
    else:
        lines.append("Strategy family diversity shows no clear advantage in this dataset.")

    if same_trades >= 5 and diverse_trades >= 5:
        lines.append(
            f"Same-family consensus: {same_wr:.1f}% WR ({same_trades}t) vs "
            f"diverse-family consensus: {diverse_wr:.1f}% WR ({diverse_trades}t)."
        )

    if best_family and worst_family and best_family != worst_family:
        bf_wr = family_perf[best_family]['wr']
        wf_wr = family_perf[worst_family]['wr']
        lines.append(f"Best family: {best_family} ({bf_wr:.1f}% WR). Worst: {worst_family} ({wf_wr:.1f}% WR).")

    # Recommended filter
    rec = []
    if diversity_helps:
        rec.append("Require 2+ DIFFERENT strategy families to agree, ignore raw system count.")
    if best_family:
        rec.append(f"Weight '{best_family}' family signals higher.")
    if not rec:
        rec.append("No strong consensus filter found. Use individual strategy WR as the primary signal.")

    return {
        'verdict': ' '.join(lines),
        'raw_count_anti_predictive': raw_count_declining,
        'family_diversity_predictive': diversity_helps,
        'recommended_filter': ' '.join(rec),
        'best_family': best_family,
        'worst_family': worst_family,
        'same_family_wr': round(same_wr, 1) if same_trades >= 5 else None,
        'diverse_family_wr': round(diverse_wr, 1) if diverse_trades >= 5 else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  CONSENSUS ACCURACY TRACKER")
    print("  Does consensus actually predict winning trades?")
    print("=" * 70)

    # Load data
    closed_picks = load_json(CLOSED_PICKS_PATH)
    active_picks = load_json(ACTIVE_PICKS_PATH)

    if isinstance(closed_picks, dict):
        closed_picks = closed_picks.get('picks', [])
    if isinstance(active_picks, dict):
        active_picks = active_picks.get('picks', [])

    print(f"\n  Closed picks loaded: {len(closed_picks)}")
    print(f"  Active picks loaded: {len(active_picks)}")

    if not closed_picks:
        print("[ERROR] No closed picks found. Cannot compute consensus accuracy.")
        return

    # ── Section 1: Backtest historical consensus ──
    print("\n  [1/5] Backtesting historical consensus...")
    backtest = backtest_consensus(closed_picks)

    print("\n  --- BY AGREEMENT COUNT ---")
    for bucket, stats in backtest['by_agreement_count'].items():
        print(f"    {bucket:>5} system(s): {stats['wr']:5.1f}% WR  ({stats['trades']:>5} trades, PnL: {stats['pnl']:>+8.1f}%)")

    print("\n  --- BY STRATEGY FAMILY DIVERSITY ---")
    for bucket, stats in backtest['by_strategy_diversity'].items():
        print(f"    {bucket:>15}: {stats['wr']:5.1f}% WR  ({stats['trades']:>5} trades, PnL: {stats['pnl']:>+8.1f}%)")

    print("\n  --- BY DIRECTION + ASSET CLASS ---")
    for bucket, stats in backtest['by_direction_asset'].items():
        print(f"    {bucket:>20}: {stats['wr']:5.1f}% WR  ({stats['trades']:>5} trades)")

    # ── Section 2: Family combination analysis ──
    print("\n  [2/5] Analyzing family combinations...")
    family_combos = analyze_family_combinations(closed_picks)

    svd = family_combos.get('same_vs_diverse', {})
    if svd:
        for k, v in svd.items():
            print(f"    {k:>20}: {v['wr']:5.1f}% WR  ({v['trades']:>5} trades)")

    top_combos = family_combos.get('top_family_combinations', [])
    if top_combos:
        print("\n  Top family combinations:")
        for c in top_combos[:10]:
            print(f"    {c['families']:>40}: {c['wr']:5.1f}% WR  ({c['trades']:>4} trades)")

    # ── Section 3: Per-family performance ──
    print("\n  [3/5] Family-level performance...")
    family_perf = analyze_family_performance(closed_picks)
    for fam, stats in sorted(family_perf.items(), key=lambda x: -x[1]['wr']):
        indicator = "  *" if stats['wr'] >= 50 else ""
        print(f"    {fam:>15}: {stats['wr']:5.1f}% WR  ({stats['trades']:>5} trades, avg PnL: {stats['avg_pnl']:>+.4f}){indicator}")

    # ── Section 4: Active picks snapshot ──
    print("\n  [4/5] Snapshotting active consensus...")
    active_snapshot = snapshot_active_consensus(active_picks)
    multi_signal = {k: v for k, v in active_snapshot.items() if v['strategy_count'] >= 2}
    print(f"    Active symbol+direction combos: {len(active_snapshot)}")
    print(f"    With 2+ strategy consensus:     {len(multi_signal)}")
    if multi_signal:
        for k, v in sorted(multi_signal.items(), key=lambda x: -x[1]['strategy_count'])[:5]:
            print(f"      {v['symbol']:>12} {v['direction']}: {v['strategy_count']} strategies, "
                  f"{v['family_count']} families ({', '.join(v['families'][:4])})")

    # ── Section 5: Verdict ──
    print("\n  [5/5] Generating verdict...")
    verdict = generate_verdict(backtest, family_combos, family_perf)

    print(f"\n  {'=' * 66}")
    print(f"  VERDICT: {verdict['verdict']}")
    print(f"  RECOMMENDATION: {verdict['recommended_filter']}")
    print(f"  {'=' * 66}")

    # ── Build output ──
    output = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'total_closed_picks_analyzed': len(closed_picks),
        'total_active_picks': len(active_picks),
        'backtest_results': backtest,
        'family_combination_analysis': family_combos,
        'family_performance': family_perf,
        'active_consensus_snapshot': active_snapshot,
        'verdict': verdict,
        'meta': {
            'strategy_families_mapped': len(STRATEGY_FAMILIES),
            'analysis_sections': [
                'by_agreement_count',
                'by_strategy_diversity',
                'by_direction_asset',
                'by_source_diversity',
                'family_combinations',
                'family_performance',
                'active_snapshot',
                'verdict',
            ],
        },
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n  Output saved: {OUTPUT_PATH}")
    print(f"  ({os.path.getsize(OUTPUT_PATH):,} bytes)")


if __name__ == '__main__':
    main()
