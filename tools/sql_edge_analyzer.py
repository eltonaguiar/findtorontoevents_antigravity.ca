"""
SQL Extract Edge Analyzer - Finds actionable edges from ejaguiar1_stocks live data.
Focuses on at_raw_picks (live trades) and at_signal_outcomes, NOT bt_backtest_trades.
"""
import re
import sys
import json
from collections import defaultdict

SQL_FILE = r"C:\Users\zerou\Downloads\ejaguiar1_stocks_apr62026_extract.sql"

def parse_at_raw_picks(sql_file):
    """Parse at_raw_picks INSERT statements for closed trades with pnl_pct."""
    picks = []
    in_raw_picks = False
    buffer = ""

    with open(sql_file, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            # Detect when we enter at_raw_picks data
            if "INSERT INTO `at_raw_picks`" in line:
                in_raw_picks = True
                buffer = line
                continue

            if in_raw_picks:
                buffer += line
                # Check if statement ends
                if line.strip().endswith(';'):
                    in_raw_picks = False
                    # Parse the buffer
                    picks.extend(extract_raw_pick_rows(buffer))
                    buffer = ""

    return picks

def extract_raw_pick_rows(sql_text):
    """Extract individual rows from INSERT statement."""
    rows = []
    # Match each VALUES tuple - find patterns between the parentheses
    # Fields: id, aggregation_run_id, source_system, symbol, asset_class, direction,
    #         entry_price, take_profit, stop_loss, risk_reward, confidence, strategy,
    #         raw_payload, signal_timestamp, recorded_at, dedup_hash,
    #         was_stale, was_banned, was_demoted, was_wr_suppressed, created_by,
    #         status, exit_price, exit_reason, pnl_pct, closed_at

    # Simple approach: find status and pnl fields via regex on each row
    # Look for WON/LOST status with pnl_pct values
    pattern = re.compile(
        r"'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*"  # id, agg_run_id, source_system, symbol, asset_class, direction
        r"([\d.]+|NULL),\s*([\d.]+|NULL),\s*([\d.]+|NULL),\s*([\d.]+|NULL),\s*([\d.]+|NULL),\s*"  # entry_price, tp, sl, rr, confidence
        r"'([^']*)',\s*"  # strategy (simplified - may not capture all)
    )

    # Simpler: just find closed picks with status WON or LOST and extract key fields
    # Split by the UUID pattern that starts each row
    uuid_pattern = re.compile(r"\('([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'")

    positions = []
    for m in uuid_pattern.finditer(sql_text):
        positions.append(m.start())

    for i, pos in enumerate(positions):
        end = positions[i+1] if i+1 < len(positions) else len(sql_text)
        row_text = sql_text[pos:end]

        # Extract fields we care about using targeted regex
        # source_system is 3rd field
        source_match = re.search(r"'[^']*',\s*'[^']*',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)'", row_text)
        if not source_match:
            continue

        source_system = source_match.group(1)
        symbol = source_match.group(2)
        asset_class = source_match.group(3)
        direction = source_match.group(4)

        # Find status (WON/LOST/OPEN/EXPIRED/CLOSED)
        status_match = re.search(r"'(WON|LOST|OPEN|EXPIRED|CLOSED)'", row_text[200:])  # skip past raw_payload
        if not status_match:
            continue
        status = status_match.group(1)

        # Find pnl_pct - it's near the end, after status
        pnl_match = re.search(r"'(?:WON|LOST|OPEN|EXPIRED|CLOSED)',\s*([\d.-]+|NULL),\s*'?([^',]*)'?,\s*([-\d.]+|NULL)", row_text[200:])
        pnl_pct = None
        if pnl_match:
            try:
                if pnl_match.group(3) != 'NULL':
                    pnl_pct = float(pnl_match.group(3))
            except (ValueError, IndexError):
                pass

        # Find strategy
        strategy_match = re.search(r"'([^']{1,200})',\s*'\{", row_text)
        if strategy_match:
            strategy = strategy_match.group(1)
        else:
            strategy = "unknown"

        # Find confidence
        conf_match = re.search(r"([\d.]+),\s*'[^']*',\s*'\{", row_text)
        confidence = None
        if conf_match:
            try:
                confidence = float(conf_match.group(1))
            except ValueError:
                pass

        rows.append({
            'source_system': source_system,
            'symbol': symbol,
            'asset_class': asset_class,
            'direction': direction,
            'strategy': strategy,
            'status': status,
            'pnl_pct': pnl_pct,
            'confidence': confidence
        })

    return rows

def parse_signal_outcomes(sql_file):
    """Parse at_signal_outcomes table."""
    outcomes = []
    in_outcomes = False
    buffer = ""

    with open(sql_file, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            if "INSERT INTO `at_signal_outcomes`" in line:
                in_outcomes = True
                buffer = line
                continue
            if in_outcomes:
                buffer += line
                if line.strip().endswith(';'):
                    in_outcomes = False
                    # Parse outcomes
                    # Fields: id, symbol, direction, entry_price, take_profit, stop_loss, exit_price, outcome, pnl_pct, source_system, strategy, asset_class, opened_at, closed_at, created_at
                    pattern = re.compile(r"\((\d+),\s*'([^']*)',\s*'([^']*)',\s*([\d.]+|NULL),\s*([\d.]+|NULL),\s*([\d.]+|NULL),\s*([\d.]+|NULL),\s*'([^']*)',\s*([-\d.]+|NULL),\s*'([^']*)',\s*(NULL|'[^']*'),\s*'([^']*)'")
                    for m in pattern.finditer(buffer):
                        outcome = m.group(8)
                        pnl = None
                        try:
                            if m.group(9) != 'NULL':
                                pnl = float(m.group(9))
                        except ValueError:
                            pass
                        strat = m.group(11).strip("'") if m.group(11) != 'NULL' else None
                        outcomes.append({
                            'symbol': m.group(2),
                            'direction': m.group(3),
                            'outcome': outcome,
                            'pnl_pct': pnl,
                            'source_system': m.group(10),
                            'strategy': strat,
                            'asset_class': m.group(12)
                        })
                    buffer = ""
    return outcomes

def parse_algorithm_performance(sql_file):
    """Parse algorithm_performance table for backtest vs live comparison."""
    perfs = []
    in_perf = False
    buffer = ""

    with open(sql_file, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            if "INSERT INTO `algorithm_performance`" in line:
                in_perf = True
                buffer = line
                continue
            if in_perf:
                buffer += line
                if line.strip().endswith(';'):
                    in_perf = False
                    break
    return buffer

def parse_consensus_picks(sql_file):
    """Parse at_consensus_picks for closed trades."""
    picks = []
    in_consensus = False
    buffer = ""

    with open(sql_file, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            if "INSERT INTO `at_consensus_picks`" in line:
                in_consensus = True
                buffer = line
                continue
            if in_consensus:
                buffer += line
                if line.strip().endswith(';'):
                    in_consensus = False
                    # Find WON/LOST picks with pnl
                    won_count = buffer.count("'WON'")
                    lost_count = buffer.count("'LOST'")
                    open_count = buffer.count("'OPEN'")
                    print(f"\n=== CONSENSUS PICKS ===")
                    print(f"WON: {won_count}, LOST: {lost_count}, OPEN: {open_count}")

                    # Extract individual closed consensus picks
                    uuid_pattern = re.compile(r"\('([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'")
                    positions = list(uuid_pattern.finditer(buffer))

                    for i, m in enumerate(positions):
                        end = positions[i+1].start() if i+1 < len(positions) else len(buffer)
                        row = buffer[m.start():end]

                        # Get symbol (4th field after id, agg_run_id)
                        fields = re.search(r"'[^']*',\s*'[^']*',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)'", row)
                        if not fields:
                            continue
                        symbol = fields.group(1)
                        asset_class = fields.group(2)
                        direction = fields.group(3)

                        # agreement_count
                        agree_match = re.search(r"(\d+),\s*'\[", row)
                        agreement = int(agree_match.group(1)) if agree_match else None

                        status_match = re.search(r"'(WON|LOST|OPEN|EXPIRED|CLOSED)'", row[100:])
                        if not status_match:
                            continue
                        status = status_match.group(1)

                        # pnl_pct near end
                        pnl_match = re.search(r"'(?:WON|LOST)',\s*([\d.-]+|NULL),\s*'?([^',]*)'?,\s*([-\d.]+|NULL)", row[100:])
                        pnl = None
                        if pnl_match:
                            try:
                                if pnl_match.group(3) != 'NULL':
                                    pnl = float(pnl_match.group(3))
                            except (ValueError, IndexError):
                                pass

                        picks.append({
                            'symbol': symbol,
                            'asset_class': asset_class,
                            'direction': direction,
                            'agreement': agreement,
                            'status': status,
                            'pnl_pct': pnl
                        })
                    buffer = ""
    return picks


def analyze_edges(picks, outcomes, consensus):
    """Compute WR, PF, avg PnL per strategy and symbol."""

    print("\n" + "="*80)
    print("EJAGUIAR1_STOCKS SQL EXTRACT - LIVE EDGE ANALYSIS")
    print("="*80)

    # === RAW PICKS ANALYSIS ===
    print(f"\n--- AT_RAW_PICKS: {len(picks)} total rows ---")

    # Count by status
    status_counts = defaultdict(int)
    for p in picks:
        status_counts[p['status']] += 1
    print(f"Status breakdown: {dict(status_counts)}")

    # Filter to closed trades only (WON or LOST with pnl_pct)
    closed = [p for p in picks if p['status'] in ('WON', 'LOST') and p['pnl_pct'] is not None]
    print(f"Closed trades with PnL: {len(closed)}")

    # Filter out backtest imports (source_system containing 'backtest' or signal dates before 2026)
    live_closed = [p for p in closed if 'backtest' not in p.get('source_system', '').lower()]
    print(f"Live closed (excl backtest imports): {len(live_closed)}")

    # === BY SOURCE SYSTEM ===
    print("\n--- BY SOURCE SYSTEM (closed trades) ---")
    by_source = defaultdict(list)
    for p in closed:
        by_source[p['source_system']].append(p)

    source_stats = []
    for source, trades in sorted(by_source.items(), key=lambda x: -len(x[1])):
        wins = sum(1 for t in trades if t['status'] == 'WON')
        losses = sum(1 for t in trades if t['status'] == 'LOST')
        total = wins + losses
        wr = wins / total * 100 if total > 0 else 0
        avg_pnl = sum(t['pnl_pct'] for t in trades) / len(trades)
        total_pnl = sum(t['pnl_pct'] for t in trades)

        # Profit factor
        gross_profit = sum(t['pnl_pct'] for t in trades if t['pnl_pct'] > 0)
        gross_loss = abs(sum(t['pnl_pct'] for t in trades if t['pnl_pct'] < 0))
        pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        source_stats.append((source, total, wr, avg_pnl, total_pnl, pf, gross_profit, gross_loss))
        if total >= 5:
            print(f"  {source:40s} n={total:5d} WR={wr:5.1f}% avgPnL={avg_pnl:+8.2f}% totalPnL={total_pnl:+10.2f}% PF={pf:.2f}")

    # === BY STRATEGY (top edges) ===
    print("\n--- BY STRATEGY (min 10 closed trades, sorted by WR) ---")
    by_strategy = defaultdict(list)
    for p in closed:
        by_strategy[p['strategy']].append(p)

    strategy_stats = []
    for strat, trades in by_strategy.items():
        wins = sum(1 for t in trades if t['status'] == 'WON')
        total = len(trades)
        if total < 10:
            continue
        wr = wins / total * 100
        avg_pnl = sum(t['pnl_pct'] for t in trades) / total
        total_pnl = sum(t['pnl_pct'] for t in trades)
        gross_profit = sum(t['pnl_pct'] for t in trades if t['pnl_pct'] > 0)
        gross_loss = abs(sum(t['pnl_pct'] for t in trades if t['pnl_pct'] < 0))
        pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        strategy_stats.append((strat, total, wr, avg_pnl, total_pnl, pf))

    strategy_stats.sort(key=lambda x: -x[2])  # Sort by WR desc

    print(f"\n  TOP 15 by Win Rate (n>=10):")
    for strat, total, wr, avg_pnl, total_pnl, pf in strategy_stats[:15]:
        print(f"    {strat:50s} n={total:4d} WR={wr:5.1f}% avgPnL={avg_pnl:+7.2f}% PF={pf:.2f}")

    print(f"\n  TOP 15 by Total PnL (n>=10):")
    strategy_stats_pnl = sorted(strategy_stats, key=lambda x: -x[4])
    for strat, total, wr, avg_pnl, total_pnl, pf in strategy_stats_pnl[:15]:
        print(f"    {strat:50s} n={total:4d} WR={wr:5.1f}% totalPnL={total_pnl:+10.2f}% PF={pf:.2f}")

    print(f"\n  BOTTOM 10 (worst strategies, n>=10):")
    for strat, total, wr, avg_pnl, total_pnl, pf in strategy_stats_pnl[-10:]:
        print(f"    {strat:50s} n={total:4d} WR={wr:5.1f}% totalPnL={total_pnl:+10.2f}% PF={pf:.2f}")

    # === BY SYMBOL (top performers) ===
    print("\n--- BY SYMBOL (min 5 closed trades, sorted by total PnL) ---")
    by_symbol = defaultdict(list)
    for p in closed:
        by_symbol[p['symbol']].append(p)

    symbol_stats = []
    for sym, trades in by_symbol.items():
        wins = sum(1 for t in trades if t['status'] == 'WON')
        total = len(trades)
        if total < 5:
            continue
        wr = wins / total * 100
        avg_pnl = sum(t['pnl_pct'] for t in trades) / total
        total_pnl = sum(t['pnl_pct'] for t in trades)
        gross_profit = sum(t['pnl_pct'] for t in trades if t['pnl_pct'] > 0)
        gross_loss = abs(sum(t['pnl_pct'] for t in trades if t['pnl_pct'] < 0))
        pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        symbol_stats.append((sym, total, wr, avg_pnl, total_pnl, pf))

    symbol_stats.sort(key=lambda x: -x[4])

    print(f"\n  TOP 15 symbols by total PnL:")
    for sym, total, wr, avg_pnl, total_pnl, pf in symbol_stats[:15]:
        print(f"    {sym:20s} n={total:4d} WR={wr:5.1f}% avgPnL={avg_pnl:+7.2f}% totalPnL={total_pnl:+10.2f}% PF={pf:.2f}")

    print(f"\n  BOTTOM 10 symbols (worst):")
    for sym, total, wr, avg_pnl, total_pnl, pf in symbol_stats[-10:]:
        print(f"    {sym:20s} n={total:4d} WR={wr:5.1f}% avgPnL={avg_pnl:+7.2f}% totalPnL={total_pnl:+10.2f}% PF={pf:.2f}")

    # === BY DIRECTION ===
    print("\n--- BY DIRECTION ---")
    for d in ['LONG', 'SHORT']:
        dtrades = [p for p in closed if p['direction'] == d]
        if not dtrades:
            continue
        wins = sum(1 for t in dtrades if t['status'] == 'WON')
        total = len(dtrades)
        wr = wins / total * 100
        avg_pnl = sum(t['pnl_pct'] for t in dtrades) / total
        print(f"  {d:6s}: n={total:5d} WR={wr:5.1f}% avgPnL={avg_pnl:+7.2f}%")

    # === BY ASSET CLASS ===
    print("\n--- BY ASSET CLASS ---")
    by_ac = defaultdict(list)
    for p in closed:
        by_ac[p['asset_class']].append(p)
    for ac, trades in sorted(by_ac.items(), key=lambda x: -len(x[1])):
        wins = sum(1 for t in trades if t['status'] == 'WON')
        total = len(trades)
        wr = wins / total * 100
        avg_pnl = sum(t['pnl_pct'] for t in trades) / total
        print(f"  {ac:15s}: n={total:5d} WR={wr:5.1f}% avgPnL={avg_pnl:+7.2f}%")

    # === CONFIDENCE BANDS ===
    print("\n--- BY CONFIDENCE BAND ---")
    conf_trades = [p for p in closed if p['confidence'] is not None]
    if conf_trades:
        bands = [(0, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 0.85), (0.85, 1.01)]
        for lo, hi in bands:
            band = [t for t in conf_trades if lo <= t['confidence'] < hi]
            if not band:
                continue
            wins = sum(1 for t in band if t['status'] == 'WON')
            total = len(band)
            wr = wins / total * 100
            avg_pnl = sum(t['pnl_pct'] for t in band) / total
            print(f"  conf [{lo:.1f}-{hi:.1f}): n={total:5d} WR={wr:5.1f}% avgPnL={avg_pnl:+7.2f}%")

    # === SIGNAL OUTCOMES ===
    if outcomes:
        print(f"\n--- AT_SIGNAL_OUTCOMES: {len(outcomes)} total ---")
        closed_outcomes = [o for o in outcomes if o['outcome'] in ('WIN', 'LOSS') and o['pnl_pct'] is not None]
        print(f"Closed with PnL: {len(closed_outcomes)}")

        wins = sum(1 for o in closed_outcomes if o['outcome'] == 'WIN')
        total = len(closed_outcomes)
        if total > 0:
            wr = wins / total * 100
            avg_pnl = sum(o['pnl_pct'] for o in closed_outcomes) / total
            print(f"  Overall: WR={wr:.1f}% avgPnL={avg_pnl:+.2f}%")

        # By source
        by_src = defaultdict(list)
        for o in closed_outcomes:
            by_src[o['source_system']].append(o)
        for src, trades in sorted(by_src.items(), key=lambda x: -len(x[1])):
            w = sum(1 for t in trades if t['outcome'] == 'WIN')
            n = len(trades)
            wr = w / n * 100
            avg = sum(t['pnl_pct'] for t in trades) / n
            print(f"    {src:40s} n={n:4d} WR={wr:5.1f}% avgPnL={avg:+7.2f}%")

    # === CONSENSUS PICKS ===
    if consensus:
        closed_consensus = [c for c in consensus if c['status'] in ('WON', 'LOST')]
        print(f"\n--- CONSENSUS PICKS: {len(consensus)} total, {len(closed_consensus)} closed ---")
        if closed_consensus:
            wins = sum(1 for c in closed_consensus if c['status'] == 'WON')
            total = len(closed_consensus)
            wr = wins / total * 100
            pnl_trades = [c for c in closed_consensus if c['pnl_pct'] is not None]
            avg_pnl = sum(c['pnl_pct'] for c in pnl_trades) / len(pnl_trades) if pnl_trades else 0
            print(f"  Overall: WR={wr:.1f}% avgPnL={avg_pnl:+.2f}% (n={total})")

            # By agreement count
            by_agree = defaultdict(list)
            for c in closed_consensus:
                if c['agreement'] is not None:
                    by_agree[c['agreement']].append(c)
            for agree in sorted(by_agree.keys()):
                trades = by_agree[agree]
                w = sum(1 for t in trades if t['status'] == 'WON')
                n = len(trades)
                wr = w / n * 100
                print(f"    agreement={agree}: n={n:4d} WR={wr:5.1f}%")

    # === HIGHEST EDGE STRATEGIES (positive avgPnL, n>=10) ===
    print("\n" + "="*80)
    print("ACTIONABLE EDGES SUMMARY")
    print("="*80)

    positive_strats = [(s, n, wr, ap, tp, pf) for s, n, wr, ap, tp, pf in strategy_stats if ap > 0 and n >= 10]
    positive_strats.sort(key=lambda x: -x[4])

    print(f"\nStrategies with POSITIVE avg PnL (n>=10): {len(positive_strats)}")
    for strat, total, wr, avg_pnl, total_pnl, pf in positive_strats[:20]:
        print(f"  ** {strat:50s} n={total:4d} WR={wr:5.1f}% avgPnL={avg_pnl:+7.2f}% totalPnL={total_pnl:+10.2f}% PF={pf:.2f}")

    # Symbols with consistent positive PnL
    positive_syms = [(s, n, wr, ap, tp, pf) for s, n, wr, ap, tp, pf in symbol_stats if ap > 0 and n >= 5]
    positive_syms.sort(key=lambda x: -x[4])
    print(f"\nSymbols with POSITIVE avg PnL (n>=5): {len(positive_syms)}")
    for sym, total, wr, avg_pnl, total_pnl, pf in positive_syms[:20]:
        print(f"  ** {sym:20s} n={total:4d} WR={wr:5.1f}% avgPnL={avg_pnl:+7.2f}% totalPnL={total_pnl:+10.2f}% PF={pf:.2f}")

    return {
        'total_picks': len(picks),
        'closed_picks': len(closed),
        'positive_strategies': positive_strats[:10],
        'positive_symbols': positive_syms[:10],
        'strategy_stats': strategy_stats,
        'symbol_stats': symbol_stats,
        'source_stats': source_stats,
    }


if __name__ == '__main__':
    print("Parsing at_raw_picks...")
    picks = parse_at_raw_picks(SQL_FILE)
    print(f"Parsed {len(picks)} raw picks")

    print("Parsing at_signal_outcomes...")
    outcomes = parse_signal_outcomes(SQL_FILE)
    print(f"Parsed {len(outcomes)} signal outcomes")

    print("Parsing at_consensus_picks...")
    consensus = parse_consensus_picks(SQL_FILE)
    print(f"Parsed {len(consensus)} consensus picks")

    results = analyze_edges(picks, outcomes, consensus)
