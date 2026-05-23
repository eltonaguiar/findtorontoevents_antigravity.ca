#!/usr/bin/env python3
"""Quick strategy analyzer — stdlib only (no pandas/numpy required)."""

import sqlite3
import json
from collections import defaultdict
from pathlib import Path


def load_audit_data(db_path):
    """Load raw picks from audit trail DB."""
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT source_system, strategy, symbol, asset_class, direction,
               entry_price, take_profit, stop_loss, risk_reward, confidence,
               signal_timestamp, recorded_at, was_stale, was_banned
        FROM raw_picks
        ORDER BY recorded_at DESC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    print(f"  Loaded {len(rows)} raw picks from audit DB")
    return rows


def load_consensus_picks(db_path):
    """Load consensus picks (multi-system agreement)."""
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT symbol, asset_class, direction, entry_price, take_profit, stop_loss,
               risk_reward, confidence, agreement_count, source_systems,
               source_strategies, consensus_tier, classification,
               status, exit_price, exit_reason, pnl_pct, generated_at, closed_at
        FROM consensus_picks
        ORDER BY generated_at DESC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    print(f"  Loaded {len(rows)} consensus picks")
    return rows


def load_deep_research():
    """Load deep research results."""
    path = Path(__file__).parent / 'genome' / 'results' / 'deep_research_what_works.json'
    if not path.exists():
        print(f"  Research file not found: {path}")
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_strategy_coverage(picks):
    """Find strategies that fire across the most symbols."""
    strat_symbols = defaultdict(set)
    strat_picks = defaultdict(list)

    for p in picks:
        key = p['strategy'] or p['source_system']
        strat_symbols[key].add(p['symbol'])
        strat_picks[key].append(p)

    # Sort by symbol coverage
    ranked = sorted(strat_symbols.items(), key=lambda x: len(x[1]), reverse=True)

    print("\n--- STRATEGY COVERAGE (symbols covered) ---")
    print(f"{'Strategy':<40} {'Symbols':>7} {'Picks':>6} {'Avg Conf':>9} {'Avg R:R':>8}")
    print("-" * 80)

    for strategy, symbols in ranked[:25]:
        sp = strat_picks[strategy]
        n = len(sp)
        avg_conf = sum(p['confidence'] or 0 for p in sp) / n if n else 0
        avg_rr = sum(p['risk_reward'] or 0 for p in sp) / n if n else 0
        print(f"  {strategy:<38} {len(symbols):>7} {n:>6} {avg_conf:>8.3f} {avg_rr:>8.2f}")

    return strat_picks


def analyze_system_performance(picks):
    """Aggregate performance by source system."""
    sys_picks = defaultdict(list)
    for p in picks:
        sys_picks[p['source_system']].append(p)

    print("\n--- SYSTEM BREAKDOWN ---")
    print(f"{'System':<30} {'Picks':>6} {'Symbols':>8} {'Avg Conf':>9} {'Stale%':>7} {'Banned%':>8}")
    print("-" * 80)

    for system in sorted(sys_picks, key=lambda s: len(sys_picks[s]), reverse=True):
        sp = sys_picks[system]
        n = len(sp)
        symbols = len({p['symbol'] for p in sp})
        avg_conf = sum(p['confidence'] or 0 for p in sp) / n
        stale_pct = sum(1 for p in sp if p['was_stale']) / n * 100
        banned_pct = sum(1 for p in sp if p['was_banned']) / n * 100
        print(f"  {system:<28} {n:>6} {symbols:>8} {avg_conf:>8.3f} {stale_pct:>6.1f}% {banned_pct:>7.1f}%")


def analyze_consensus(consensus_picks):
    """Analyze consensus picks — these are the highest conviction signals."""
    if not consensus_picks:
        print("\n--- CONSENSUS PICKS: None found ---")
        return

    print(f"\n--- CONSENSUS PICKS ({len(consensus_picks)} total) ---")

    # Closed picks with PnL
    closed = [p for p in consensus_picks if p['status'] in ('WON', 'LOST', 'closed')]
    active = [p for p in consensus_picks if p['status'] not in ('WON', 'LOST', 'closed')]

    if closed:
        wins = sum(1 for p in closed if (p.get('pnl_pct') or 0) > 0)
        losses = len(closed) - wins
        avg_pnl = sum(p.get('pnl_pct') or 0 for p in closed) / len(closed)
        print(f"  Closed: {len(closed)} | Wins: {wins} | Losses: {losses} | WR: {wins/len(closed):.1%} | Avg PnL: {avg_pnl:.2f}%")

    if active:
        print(f"  Active: {len(active)}")
        print(f"  {'Symbol':<12} {'Dir':<6} {'Entry':>10} {'TP':>10} {'SL':>10} {'Conf':>6} {'Agree':>6} {'Tier':<10} {'Systems'}")
        print("  " + "-" * 100)
        for p in sorted(active, key=lambda x: x['confidence'] or 0, reverse=True):
            print(f"  {p['symbol']:<12} {p['direction']:<6} {p['entry_price']:>10.4g} "
                  f"{p['take_profit']:>10.4g} {p['stop_loss']:>10.4g} "
                  f"{(p['confidence'] or 0):>5.3f} {p['agreement_count']:>6} "
                  f"{(p['consensus_tier'] or ''):>10} {p['source_systems']}")


def analyze_deep_research(data):
    """Surface patterns from deep research."""
    if data is None:
        return

    print("\n--- DEEP RESEARCH INSIGHTS ---")

    # Pattern analysis
    patterns = data.get('pattern_analysis', {})
    if patterns:
        print("\n  Consistent Patterns (>=66% consistency):")
        found = False
        for name, stats in patterns.items():
            if stats.get('consistency', 0) >= 66:
                found = True
                trades = stats.get('total_trades', 0)
                sharpe = stats.get('avg_sharpe', 0)
                dd = stats.get('max_dd', 0)
                print(f"    {name}: {trades} trades, Sharpe {sharpe:.1f}, Max DD {dd:.1f}%")
        if not found:
            print("    (none met threshold)")

    # Regime analysis
    regimes = data.get('regime_analysis', {})
    if regimes:
        print("\n  Regime Performance:")
        for regime, stats in regimes.items():
            trades = stats.get('trades', 0)
            if trades >= 5:
                avg_pnl = stats.get('avg_pnl', 0)
                print(f"    {regime}: {trades} trades, Avg PnL {avg_pnl:.2f}%")

    # Playbook
    playbook = data.get('playbook', {})
    what_works = playbook.get('what_works', {})
    top_symbols = what_works.get('top_symbols', [])
    if top_symbols:
        print("\n  Top Symbols from Research:")
        for item in top_symbols[:10]:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                sym, stats = item
                if isinstance(stats, dict):
                    trades = stats.get('trades', '?')
                    avg = stats.get('avg_pnl_per_trade', 0)
                    if avg > 0.1:
                        print(f"    {sym}: {trades} trades, {avg:.3f}% avg PnL/trade")


def analyze_high_confidence(picks, threshold=0.8):
    """Show picks with high confidence."""
    high = [p for p in picks if (p.get('confidence') or 0) >= threshold and not p.get('was_stale') and not p.get('was_banned')]
    high.sort(key=lambda x: x['confidence'] or 0, reverse=True)

    print(f"\n--- HIGH CONFIDENCE PICKS (>={threshold}) — {len(high)} total ---")
    if not high:
        print("  None found.")
        return

    # Show top 20
    print(f"  {'Symbol':<12} {'Dir':<6} {'System':<25} {'Strategy':<30} {'Conf':>6} {'R:R':>6}")
    print("  " + "-" * 90)
    for p in high[:20]:
        print(f"  {p['symbol']:<12} {p['direction']:<6} {p['source_system']:<25} "
              f"{(p['strategy'] or '-'):<30} {p['confidence']:>5.3f} {(p['risk_reward'] or 0):>6.2f}")

    if len(high) > 20:
        print(f"  ... and {len(high) - 20} more")


def main():
    print("=" * 60)
    print("  CRYPTO STRATEGY AUDIT ANALYZER (stdlib, no pandas)")
    print("=" * 60)

    db_path = Path(__file__).parent / 'data' / 'audit_trail.db'

    print("\nLoading data...")
    picks = load_audit_data(db_path)
    consensus = load_consensus_picks(db_path)
    research = load_deep_research()

    if not picks:
        print("\nNo picks data — nothing to analyze.")
        return

    # Filter to crypto
    crypto_picks = [p for p in picks if p['asset_class'] == 'CRYPTO']
    print(f"\n  Total picks: {len(picks)} | Crypto: {len(crypto_picks)}")

    analyze_system_performance(crypto_picks)
    analyze_strategy_coverage(crypto_picks)
    analyze_high_confidence(crypto_picks)
    analyze_consensus(consensus)
    analyze_deep_research(research)

    print("\n" + "=" * 60)
    print("  ANALYSIS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
