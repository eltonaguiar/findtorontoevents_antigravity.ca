#!/usr/bin/env python3
"""
Strategy-Level Cross-System Consensus Matrix
=============================================
Fixes the fundamental flaw in system-level agreement: tracks consensus at the
STRATEGY level, filtered to only the WINNING parts of each system.

Instead of "3 systems agree on BTCUSDT LONG", this answers:
"8 historically-winning strategies agree on BTCUSDT LONG"

Output: alpha_engine/data/strategy_consensus_matrix.json
"""
import sys
import os
import json
import io
from datetime import datetime, timezone
from collections import defaultdict
from itertools import combinations

# Windows UTF-8 fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ── Paths ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
PAYLOAD_PATH = os.path.join(REPO_ROOT, 'audit_trail', 'data', 'dashboard_payload.json')
OUTPUT_PATH = os.path.join(SCRIPT_DIR, 'data', 'strategy_consensus_matrix.json')


def norm_symbol(s):
    """Normalize symbol to XXXUSDT format."""
    s = (s or '').upper().replace('-', '').split('/')[0]
    if s.endswith('USD') and not s.endswith('USDT'):
        s += 'T'
    if not s.endswith('USDT') and not s.endswith('USD'):
        s += 'USDT'
    return s


def load_payload():
    """Load dashboard payload."""
    if not os.path.exists(PAYLOAD_PATH):
        print(f"[WARN] Payload not found: {PAYLOAD_PATH}")
        return None
    with open(PAYLOAD_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_performance_profiles(closed_picks):
    """
    Step 2: Build per-(strategy, symbol, direction) performance profiles.
    Returns dict keyed by (strategy, symbol, direction) -> stats.
    """
    profiles = defaultdict(lambda: {
        'trades': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0, 'timestamps': []
    })

    for cp in closed_picks:
        strat = cp.get('strategy', '')
        if not strat:
            continue
        sym = norm_symbol(cp.get('symbol', ''))
        direction = (cp.get('direction', '') or '').upper()
        if direction not in ('LONG', 'SHORT'):
            continue
        source = cp.get('source_system', '')

        status = (cp.get('status', '') or cp.get('outcome', '')).upper()
        pnl = float(cp.get('pnl_pct', 0) or 0)

        is_win = pnl > 0 or status in ('WON', 'WIN', 'TP_HIT', 'CLOSED_TP')
        is_loss = pnl < 0 or status in ('LOST', 'LOSS', 'SL_HIT', 'CLOSED_SL')

        # Skip auto-expired with zero PnL (noise)
        if cp.get('_auto_expired') and abs(pnl) < 0.001:
            continue

        key = (strat, sym, direction, source)
        profiles[key]['trades'] += 1
        if is_win:
            profiles[key]['wins'] += 1
        if is_loss:
            profiles[key]['losses'] += 1
        profiles[key]['pnl'] += pnl
        profiles[key]['timestamps'].append(cp.get('timestamp', ''))

    # Compute derived stats
    result = {}
    for key, stats in profiles.items():
        resolved = stats['wins'] + stats['losses']
        wr = (stats['wins'] / resolved * 100) if resolved > 0 else 0
        avg_pnl = stats['pnl'] / stats['trades'] if stats['trades'] > 0 else 0
        result[key] = {
            'strategy': key[0],
            'symbol': key[1],
            'direction': key[2],
            'source_system': key[3],
            'trades': stats['trades'],
            'wins': stats['wins'],
            'losses': stats['losses'],
            'wr': round(wr, 1),
            'pnl': round(stats['pnl'], 2),
            'avg_pnl': round(avg_pnl, 3),
        }

    return result


def is_winner(profile):
    """
    Step 3: A strategy is a 'winner' on a specific symbol+direction if:
    - WR >= 50% AND trades >= 5
    - OR WR >= 60% with trades >= 3
    """
    wr = profile['wr']
    trades = profile['trades']

    if wr >= 50 and trades >= 5:
        return True
    if wr >= 60 and trades >= 3:
        return True
    return False


def build_strategy_aggregates(profiles):
    """
    Build aggregated performance per strategy (across all symbols/directions)
    and per strategy+direction (across all symbols).
    This provides fallback data when symbol-specific data is sparse.
    """
    # Per strategy (all symbols, all directions)
    strat_agg = defaultdict(lambda: {'trades': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0})
    # Per strategy+direction (all symbols)
    strat_dir_agg = defaultdict(lambda: {'trades': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0})

    for key, prof in profiles.items():
        strat, sym, direction, source = key
        # Aggregate by strategy
        strat_agg[strat]['trades'] += prof['trades']
        strat_agg[strat]['wins'] += prof['wins']
        strat_agg[strat]['losses'] += prof['losses']
        strat_agg[strat]['pnl'] += prof['pnl']
        # Aggregate by strategy+direction
        sd_key = (strat, direction)
        strat_dir_agg[sd_key]['trades'] += prof['trades']
        strat_dir_agg[sd_key]['wins'] += prof['wins']
        strat_dir_agg[sd_key]['losses'] += prof['losses']
        strat_dir_agg[sd_key]['pnl'] += prof['pnl']

    # Compute WR
    result_agg = {}
    for strat, stats in strat_agg.items():
        resolved = stats['wins'] + stats['losses']
        result_agg[strat] = {
            'trades': stats['trades'],
            'wins': stats['wins'],
            'losses': stats['losses'],
            'wr': round(stats['wins'] / resolved * 100 if resolved > 0 else 0, 1),
            'pnl': round(stats['pnl'], 2),
            'avg_pnl': round(stats['pnl'] / stats['trades'] if stats['trades'] > 0 else 0, 3),
        }

    result_dir = {}
    for (strat, d), stats in strat_dir_agg.items():
        resolved = stats['wins'] + stats['losses']
        result_dir[(strat, d)] = {
            'trades': stats['trades'],
            'wins': stats['wins'],
            'losses': stats['losses'],
            'wr': round(stats['wins'] / resolved * 100 if resolved > 0 else 0, 1),
            'pnl': round(stats['pnl'], 2),
            'avg_pnl': round(stats['pnl'] / stats['trades'] if stats['trades'] > 0 else 0, 3),
        }

    return result_agg, result_dir


def build_consensus_matrix(active_picks, profiles, strat_agg, strat_dir_agg, active_strat_fwd):
    """
    Step 4: Build the strategy-level consensus matrix.
    For each symbol+direction in active picks, find which strategies are signaling
    and filter to only winners.

    Profile lookup cascade:
      1. Exact (strategy, symbol, direction, source)
      2. (strategy, symbol, direction) any source
      3. (strategy, direction) aggregated across all symbols
      4. (strategy) aggregated across everything
      5. Forward performance from active pick metadata (strat_fwd_wr, strat_fwd_trades)
    """
    # Group active picks by symbol+direction
    active_signals = defaultdict(list)
    for p in active_picks:
        sym = norm_symbol(p.get('symbol', ''))
        direction = (p.get('direction', '') or '').upper()
        if direction not in ('LONG', 'SHORT'):
            continue
        strat = p.get('strategy', '')
        source = p.get('source_system', '')
        if not strat:
            continue
        active_signals[(sym, direction)].append({
            'strategy': strat,
            'source_system': source,
            'entry_price': p.get('entry_price'),
            'confidence': p.get('confidence'),
            'strat_fwd_wr': p.get('strat_fwd_wr'),
            'strat_fwd_trades': p.get('strat_fwd_trades'),
        })

    consensus = {}
    for (sym, direction), signals in active_signals.items():
        key = f"{sym}_{direction}"
        winning_strategies = []
        losing_strategies = []
        untracked_strategies = []

        for sig in signals:
            strat = sig['strategy']
            source = sig['source_system']
            profile_key = (strat, sym, direction, source)
            match_level = 'exact'

            profile = profiles.get(profile_key)
            if profile is None:
                # Level 2: Try without source system match
                matching = [v for k, v in profiles.items()
                            if k[0] == strat and k[1] == sym and k[2] == direction]
                if matching:
                    profile = max(matching, key=lambda x: x['trades'])
                    match_level = 'sym+dir'

            if profile is None or profile['trades'] < 3:
                # Level 3: strategy+direction aggregate
                sd_prof = strat_dir_agg.get((strat, direction))
                if sd_prof and sd_prof['trades'] >= 3:
                    profile = sd_prof
                    match_level = 'dir_agg'

            if profile is None or profile['trades'] < 3:
                # Level 4: strategy aggregate (all symbols, all directions)
                s_prof = strat_agg.get(strat)
                if s_prof and s_prof['trades'] >= 3:
                    profile = s_prof
                    match_level = 'strat_agg'

            if profile is None or profile['trades'] < 3:
                # Level 5: Use forward performance from active pick metadata
                fwd_wr = sig.get('strat_fwd_wr')
                fwd_trades = sig.get('strat_fwd_trades')
                if fwd_wr is not None and fwd_trades is not None and fwd_trades >= 3:
                    wins_est = int(round(fwd_wr / 100 * fwd_trades))
                    profile = {
                        'trades': fwd_trades,
                        'wins': wins_est,
                        'losses': fwd_trades - wins_est,
                        'wr': round(fwd_wr, 1),
                        'pnl': 0,
                        'avg_pnl': 0,
                    }
                    match_level = 'fwd_meta'

            if profile and profile['trades'] >= 3:
                entry = {
                    'name': strat,
                    'system': source,
                    'wr': profile['wr'],
                    'trades': profile['trades'],
                    'pnl': profile['pnl'],
                    'avg_pnl': profile['avg_pnl'],
                    'match_level': match_level,
                }
                if is_winner(profile):
                    winning_strategies.append(entry)
                else:
                    losing_strategies.append(entry)
            else:
                untracked_strategies.append({
                    'name': strat,
                    'system': source,
                    'trades': profile['trades'] if profile else 0,
                    'wr': profile['wr'] if profile else 0,
                })

        # Sort by WR descending
        winning_strategies.sort(key=lambda x: (-x['wr'], -x['trades']))
        losing_strategies.sort(key=lambda x: (-x['wr'], -x['trades']))

        total = len(signals)
        winning_ct = len(winning_strategies)
        losing_ct = len(losing_strategies)
        untracked_ct = len(untracked_strategies)

        # Conviction levels
        if winning_ct >= 5:
            conviction = 'VERY_HIGH'
        elif winning_ct >= 3:
            conviction = 'HIGH'
        elif winning_ct >= 2:
            conviction = 'MEDIUM'
        elif winning_ct >= 1:
            conviction = 'LOW'
        else:
            conviction = 'NONE'

        consensus[key] = {
            'symbol': sym,
            'direction': direction,
            'total_signals': total,
            'winning_signals': winning_ct,
            'losing_signals': losing_ct,
            'untracked_signals': untracked_ct,
            'winning_strategies': winning_strategies[:15],  # cap for readability
            'losing_strategies': losing_strategies[:10],
            'untracked_strategies': untracked_strategies[:10],
            'true_consensus_score': winning_ct,
            'conviction': conviction,
        }

    return consensus


def compute_pair_analysis(active_picks, profiles, closed_picks):
    """
    Step 5: For every PAIR of winning strategies, compute their combined
    historical WR when they BOTH signal the same symbol+direction.
    """
    # Build index: (symbol, direction) -> set of strategies that are active now
    active_by_sd = defaultdict(set)
    for p in active_picks:
        sym = norm_symbol(p.get('symbol', ''))
        d = (p.get('direction', '') or '').upper()
        strat = p.get('strategy', '')
        if strat and d in ('LONG', 'SHORT'):
            active_by_sd[(sym, d)].add(strat)

    # Filter to winning strategies only
    winning_strats = set()
    for key, prof in profiles.items():
        if is_winner(prof):
            winning_strats.add(key[0])  # strategy name

    # Build co-occurrence from closed picks:
    # For each closed pick timestamp window (~1h), which strategies were active?
    # Simpler approach: for each symbol+direction, find overlapping strategies in closed picks
    # Group closed by (symbol, direction, approximate time bucket)
    from collections import Counter

    # Build: for each (sym, dir), which strategies had closed picks and their outcomes
    strat_outcomes = defaultdict(list)  # (sym, dir, strat) -> [is_win, ...]
    for cp in closed_picks:
        sym = norm_symbol(cp.get('symbol', ''))
        d = (cp.get('direction', '') or '').upper()
        strat = cp.get('strategy', '')
        if not strat or d not in ('LONG', 'SHORT'):
            continue
        pnl = float(cp.get('pnl_pct', 0) or 0)
        status = (cp.get('status', '') or '').upper()
        is_win = pnl > 0 or status in ('WON', 'WIN', 'TP_HIT', 'CLOSED_TP')
        strat_outcomes[(sym, d, strat)].append(is_win)

    # For pairs of winning strategies currently signaling the same symbol+direction
    pair_results = {}
    seen_pairs = set()

    for (sym, d), strats in active_by_sd.items():
        winning_active = [s for s in strats if s in winning_strats]
        if len(winning_active) < 2:
            continue

        for s1, s2 in combinations(sorted(winning_active), 2):
            pair_key = (s1, s2)
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            # Find symbols where both strategies have closed trades
            outcomes_1 = strat_outcomes.get((sym, d, s1), [])
            outcomes_2 = strat_outcomes.get((sym, d, s2), [])

            # Both had trades on this symbol+direction
            both_count = min(len(outcomes_1), len(outcomes_2))
            if both_count < 2:
                continue

            # Use smaller set for combined WR estimate
            combined_wins = sum(outcomes_1[:both_count]) + sum(outcomes_2[:both_count])
            combined_total = both_count * 2
            combined_wr = (combined_wins / combined_total * 100) if combined_total > 0 else 0

            # Individual WRs
            wr1 = sum(outcomes_1) / len(outcomes_1) * 100 if outcomes_1 else 0
            wr2 = sum(outcomes_2) / len(outcomes_2) * 100 if outcomes_2 else 0
            avg_individual = (wr1 + wr2) / 2

            edge = combined_wr - avg_individual

            if pair_key not in pair_results:
                pair_results[pair_key] = {
                    'strategy_1': s1,
                    'strategy_2': s2,
                    'both_signaled': both_count,
                    'combined_wr': round(combined_wr, 1),
                    'individual_avg_wr': round(avg_individual, 1),
                    'edge_pct': round(edge, 1),
                    'symbols': [],
                }
            pair_results[pair_key]['symbols'].append(sym)

    # Sort by combined WR descending
    pairs_list = sorted(pair_results.values(), key=lambda x: (-x['combined_wr'], -x['both_signaled']))
    return pairs_list[:30]  # top 30 pairs


def build_summary(consensus):
    """Step 6: Build summary of high/medium/low conviction picks."""
    high_longs = []
    high_shorts = []
    medium_longs = []
    medium_shorts = []
    avoid = []

    for key, data in consensus.items():
        sym = data['symbol']
        direction = data['direction']
        conviction = data['conviction']
        winning = data['winning_signals']
        total = data['total_signals']

        if conviction in ('HIGH', 'VERY_HIGH'):
            if direction == 'LONG':
                high_longs.append({
                    'symbol': sym,
                    'winning_strategies': winning,
                    'total_strategies': total,
                    'conviction': conviction,
                })
            else:
                high_shorts.append({
                    'symbol': sym,
                    'winning_strategies': winning,
                    'total_strategies': total,
                    'conviction': conviction,
                })
        elif conviction == 'MEDIUM':
            if direction == 'LONG':
                medium_longs.append(sym)
            else:
                medium_shorts.append(sym)
        elif winning == 0 and total >= 2:
            avoid.append(f"{sym} {direction} - only losing/untracked strategies signal ({total} signals, 0 winners)")

    return {
        'high_conviction_longs': sorted(high_longs, key=lambda x: -x['winning_strategies']),
        'high_conviction_shorts': sorted(high_shorts, key=lambda x: -x['winning_strategies']),
        'medium_conviction_longs': sorted(medium_longs),
        'medium_conviction_shorts': sorted(medium_shorts),
        'avoid': avoid,
    }


def main():
    print("=" * 60)
    print("  STRATEGY CONSENSUS MATRIX")
    print("  True signal quality - strategy level, not system level")
    print("=" * 60)

    # Step 1: Load data
    payload = load_payload()
    if not payload:
        print("[ERROR] No payload data found. Exiting.")
        return

    picks = payload.get('picks', {})
    active_picks = picks.get('active', [])
    closed_picks = picks.get('recent_closed', [])

    print(f"\n  Active picks:  {len(active_picks)}")
    print(f"  Closed picks:  {len(closed_picks)}")

    if not active_picks:
        print("[WARN] No active picks. Nothing to analyze.")
        # Write empty output
        output = {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'symbols': {},
            'best_strategy_pairs': [],
            'summary': {'high_conviction_longs': [], 'high_conviction_shorts': [], 'avoid': []},
            'meta': {'active_count': 0, 'closed_count': len(closed_picks)},
        }
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)
        return

    # Step 2: Build performance profiles
    profiles = build_performance_profiles(closed_picks)
    print(f"\n  Performance profiles: {len(profiles)} unique (strategy, symbol, direction) combos")

    # Step 2b: Build aggregated profiles (fallback for sparse symbol-specific data)
    strat_agg, strat_dir_agg = build_strategy_aggregates(profiles)
    print(f"  Strategy aggregates:  {len(strat_agg)} strategies, {len(strat_dir_agg)} strategy+dir combos")

    # Count winners
    winners = {k: v for k, v in profiles.items() if is_winner(v)}
    losers = {k: v for k, v in profiles.items() if not is_winner(v) and v['trades'] >= 3}
    print(f"  Winning combos:      {len(winners)} (WR>=50%+5t or WR>=60%+3t)")
    print(f"  Losing combos:       {len(losers)}")

    # Step 4: Build consensus matrix
    consensus = build_consensus_matrix(active_picks, profiles, strat_agg, strat_dir_agg, {})
    print(f"\n  Consensus entries:   {len(consensus)} symbol+direction combos")

    # Step 5: Pair analysis
    pair_analysis = compute_pair_analysis(active_picks, profiles, closed_picks)
    print(f"  Strategy pairs:      {len(pair_analysis)} winning-strategy pairs")

    # Restructure consensus by symbol
    symbols_output = {}
    for key, data in consensus.items():
        sym = data['symbol']
        direction = data['direction']
        if sym not in symbols_output:
            symbols_output[sym] = {}

        # Find best pair for this symbol+direction
        best_pair = None
        for pair in pair_analysis:
            if sym in pair.get('symbols', []):
                best_pair = {
                    'strategies': [pair['strategy_1'], pair['strategy_2']],
                    'combined_wr': pair['combined_wr'],
                    'edge_pct': pair['edge_pct'],
                }
                break

        entry = {
            'total_signals': data['total_signals'],
            'winning_signals': data['winning_signals'],
            'losing_signals': data['losing_signals'],
            'untracked_signals': data['untracked_signals'],
            'true_consensus': data['true_consensus_score'],
            'conviction': data['conviction'],
            'winning_strategies': data['winning_strategies'],
            'losing_strategies': data['losing_strategies'],
        }
        if best_pair:
            entry['best_pair'] = best_pair

        symbols_output[sym][direction] = entry

    # Step 6: Build summary
    summary = build_summary(consensus)

    # Final output
    output = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'symbols': symbols_output,
        'best_strategy_pairs': pair_analysis[:15],
        'summary': summary,
        'meta': {
            'active_count': len(active_picks),
            'closed_count': len(closed_picks),
            'total_profiles': len(profiles),
            'winning_profiles': len(winners),
            'losing_profiles': len(losers),
        },
    }

    # Save
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    print(f"\n  Output saved to: {OUTPUT_PATH}")

    # Print summary
    print(f"\n  === SUMMARY ===")
    hc_longs = summary.get('high_conviction_longs', [])
    hc_shorts = summary.get('high_conviction_shorts', [])
    if hc_longs:
        print(f"  HIGH conviction LONG:  {', '.join(x['symbol'] for x in hc_longs)}")
    if hc_shorts:
        print(f"  HIGH conviction SHORT: {', '.join(x['symbol'] for x in hc_shorts)}")
    if summary.get('avoid'):
        print(f"  AVOID: {len(summary['avoid'])} symbol+direction combos with zero winners")
    if pair_analysis:
        top = pair_analysis[0]
        print(f"  Best strategy pair:    {top['strategy_1']} + {top['strategy_2']} = {top['combined_wr']}% combined WR")

    print(f"\n{'=' * 60}")


if __name__ == '__main__':
    main()
