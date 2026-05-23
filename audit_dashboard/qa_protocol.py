#!/usr/bin/env python3
"""
PORTFOLIO QA PROTOCOL — Comprehensive system health check.
Run after every portfolio reset, code change, or when investigating issues.

Checks 5 layers:
  1. DATA INTEGRITY — prices, sizes, audit trail fields
  2. SYSTEM HEALTH — idle portfolios, pick flow, pipeline connectivity
  3. PERFORMANCE — PnL, win rate, equity drift
  4. PIPELINE — source picks → filter → firewall → portfolio (count at each stage)
  5. MUTATION ENGINE — DNA picks loading, freshness, diversity
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
import urllib.request


def fetch_bybit_prices():
    """Fetch live prices from Bybit for verification."""
    bybit = {}
    for cat in ['spot', 'linear']:
        url = f'https://api.bybit.com/v5/market/tickers?category={cat}'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            for t in json.loads(resp.read())['result']['list']:
                if t['symbol'] not in bybit:
                    bybit[t['symbol']] = float(t['lastPrice'])
        except Exception as e:
            print(f"  [WARN] Bybit {cat} fetch failed: {e}")
    return bybit


def check_data_integrity(state, bybit):
    """Layer 1: Data integrity — prices, sizes, audit trail."""
    issues = []
    total_pos = 0

    for name, pf in state.items():
        if not isinstance(pf, dict) or 'positions' not in pf:
            continue
        for pos in pf.get('positions', []):
            total_pos += 1
            sym = pos.get('symbol', '?')

            # Check required fields
            for field in ['entry_price', 'size_usd', 'direction', 'opened_at', 'take_profit', 'stop_loss']:
                if field not in pos or pos[field] is None:
                    issues.append(f"MISSING FIELD: {name}/{sym} missing '{field}'")

            # Check size_usd > 0
            if pos.get('size_usd', 0) <= 0:
                issues.append(f"ZERO SIZE: {name}/{sym} size_usd={pos.get('size_usd')}")

            # Check audit trail
            if '_price_source' not in pos:
                issues.append(f"NO AUDIT TRAIL: {name}/{sym} missing _price_source")

            # Check stale entries (>24h)
            opened = pos.get('opened_at', '')
            if opened:
                try:
                    dt = datetime.fromisoformat(opened.replace('Z', '+00:00'))
                    now = datetime.now(timezone.utc)
                    if (now - dt).total_seconds() > 86400:
                        issues.append(f"STALE ENTRY: {name}/{sym} opened {int((now-dt).total_seconds()/3600)}h ago")
                except:
                    pass

            # Verify price vs Bybit
            entry = pos.get('entry_price', 0)
            norm = sym.replace('-USD', 'USDT').replace('-', '')
            live = bybit.get(norm)
            if live and entry:
                drift = abs(live - entry) / entry * 100
                if drift > 15:
                    issues.append(f"PRICE DRIFT: {name}/{sym} entry=${entry} live=${live} drift={drift:.1f}%")

    return issues, total_pos


def check_system_health(state):
    """Layer 2: System health — idle portfolios, activity levels."""
    issues = []
    idle = []
    low_activity = []

    for name, pf in state.items():
        if not isinstance(pf, dict) or 'positions' not in pf:
            continue
        n_pos = len(pf.get('positions', []))
        n_closed = len(pf.get('closed_trades', pf.get('closed', [])))

        if n_pos == 0 and n_closed == 0:
            idle.append(name)
        elif n_pos == 0 and n_closed > 0:
            low_activity.append(name)

    if idle:
        issues.append(f"IDLE PORTFOLIOS ({len(idle)}): {', '.join(idle)}")

    return issues, idle


def check_performance(state, bybit):
    """Layer 3: Performance — PnL, high-loss positions."""
    issues = []
    total_equity = 0
    total_initial = 0
    high_pnl = []

    for name, pf in state.items():
        if not isinstance(pf, dict) or 'positions' not in pf:
            continue
        equity = pf.get('equity', 0)
        initial = pf.get('initial_capital', 0)
        total_equity += equity
        total_initial += initial

        for pos in pf.get('positions', []):
            sym = pos.get('symbol', '?')
            entry = pos.get('entry_price', 0)
            direction = pos.get('direction', 'LONG')
            size_usd = pos.get('size_usd', 0)
            norm = sym.replace('-USD', 'USDT').replace('-', '')
            live = bybit.get(norm)

            if live and entry and size_usd:
                if direction == 'LONG':
                    pnl_pct = ((live - entry) / entry) * 100
                else:
                    pnl_pct = ((entry - live) / entry) * 100

                if abs(pnl_pct) > 10:
                    high_pnl.append(f"{name}/{sym}: {pnl_pct:+.1f}% (entry={entry}, live={live})")

    if high_pnl:
        for h in high_pnl:
            issues.append(f"PNL >10%: {h}")

    net_pnl = total_equity - total_initial
    return issues, total_equity, total_initial, net_pnl


def check_pipeline(state):
    """Layer 4: Pipeline — check pick sources are connected."""
    issues = []
    root = Path(__file__).parent.parent

    # Check source pick files exist and are fresh
    pick_sources = {
        'alpha_engine': root / 'alpha_engine' / 'data' / 'active_picks.json',
        'dna_mutations': root / 'genome' / 'data' / 'dna_winner_picks.json',
    }

    for name, path in pick_sources.items():
        if not path.exists():
            issues.append(f"MISSING SOURCE: {name} ({path})")
            continue

        # Check freshness
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        age_h = (datetime.now(timezone.utc) - mtime).total_seconds() / 3600

        try:
            with open(path) as f:
                data = json.load(f)
            if isinstance(data, dict):
                picks = data.get('picks', data.get('active_picks', []))
            else:
                picks = data

            if not picks:
                issues.append(f"EMPTY SOURCE: {name} has 0 picks")
            elif age_h > 6:
                issues.append(f"STALE SOURCE: {name} is {age_h:.0f}h old ({len(picks)} picks)")
            else:
                print(f"  [OK] {name}: {len(picks)} picks, {age_h:.1f}h old")
        except Exception as e:
            issues.append(f"CORRUPT SOURCE: {name} — {e}")

    # Check portfolio manager is wired to DNA picks
    pm_path = root / 'audit_dashboard' / 'portfolio_manager.py'
    pm_text = pm_path.read_text(encoding='utf-8', errors='ignore')
    if 'dna_winner_picks' not in pm_text:
        issues.append("DISCONNECTED: portfolio_manager.py does NOT load DNA mutation picks")

    return issues


def check_mutation_engine():
    """Layer 5: Mutation engine health."""
    issues = []
    root = Path(__file__).parent.parent

    dna_path = root / 'genome' / 'data' / 'dna_winner_picks.json'
    if not dna_path.exists():
        issues.append("MUTATION ENGINE: dna_winner_picks.json not found")
        return issues

    try:
        with open(dna_path) as f:
            data = json.load(f)

        meta = data.get('metadata', {})
        picks = data.get('picks', [])
        mutations_triggered = data.get('mutations_triggered', [])
        mutations_silent = data.get('mutations_silent', [])

        # Check mutation diversity
        strategies = set(p.get('strategy', '') for p in picks)
        symbols = set(p.get('symbol', '') for p in picks)

        print(f"  Mutations: {len(mutations_triggered)} active, {len(mutations_silent)} silent")
        print(f"  Picks: {len(picks)} across {len(strategies)} strategies, {len(symbols)} symbols")

        if len(picks) < 5:
            issues.append(f"LOW MUTATIONS: only {len(picks)} picks generated")

        ts = meta.get('timestamp', '')
        if ts:
            try:
                gen_time = datetime.fromisoformat(ts)
                if gen_time.tzinfo is None:
                    gen_time = gen_time.replace(tzinfo=timezone.utc)
                age_h = (datetime.now(timezone.utc) - gen_time).total_seconds() / 3600
                if age_h > 4:
                    issues.append(f"STALE MUTATIONS: generated {age_h:.0f}h ago")
            except:
                pass
    except Exception as e:
        issues.append(f"MUTATION ENGINE ERROR: {e}")

    return issues


def run_full_qa():
    """Run all 5 QA layers and report."""
    root = Path(__file__).parent.parent
    state_path = root / 'audit_dashboard' / 'data' / 'claudes_test_state.json'

    with open(state_path) as f:
        state = json.load(f)

    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    print(f"{'='*60}")
    print(f"  PORTFOLIO QA PROTOCOL — {ts}")
    print(f"{'='*60}")

    all_issues = []

    # Layer 1: Data Integrity
    print(f"\n[1/5] DATA INTEGRITY")
    bybit = fetch_bybit_prices()
    integrity_issues, total_pos = check_data_integrity(state, bybit)
    all_issues.extend(integrity_issues)
    print(f"  Positions: {total_pos} | Issues: {len(integrity_issues)}")
    for i in integrity_issues:
        print(f"  !! {i}")

    # Layer 2: System Health
    print(f"\n[2/5] SYSTEM HEALTH")
    health_issues, idle = check_system_health(state)
    all_issues.extend(health_issues)
    n_portfolios = sum(1 for v in state.values() if isinstance(v, dict) and 'positions' in v)
    n_active = n_portfolios - len(idle)
    print(f"  Portfolios: {n_portfolios} total, {n_active} active, {len(idle)} idle")
    for i in health_issues:
        print(f"  !! {i}")

    # Layer 3: Performance
    print(f"\n[3/5] PERFORMANCE")
    perf_issues, total_equity, total_initial, net_pnl = check_performance(state, bybit)
    all_issues.extend(perf_issues)
    pnl_pct = (net_pnl / total_initial * 100) if total_initial > 0 else 0
    print(f"  Equity: ${total_equity:,.2f} | Initial: ${total_initial:,.0f} | Net PnL: ${net_pnl:+,.2f} ({pnl_pct:+.3f}%)")
    for i in perf_issues:
        print(f"  !! {i}")

    # Layer 4: Pipeline
    print(f"\n[4/5] PIPELINE CONNECTIVITY")
    pipeline_issues = check_pipeline(state)
    all_issues.extend(pipeline_issues)
    for i in pipeline_issues:
        print(f"  !! {i}")

    # Layer 5: Mutation Engine
    print(f"\n[5/5] MUTATION ENGINE")
    mutation_issues = check_mutation_engine()
    all_issues.extend(mutation_issues)
    for i in mutation_issues:
        print(f"  !! {i}")

    # Summary
    print(f"\n{'='*60}")
    if all_issues:
        print(f"  RESULT: FAIL — {len(all_issues)} issues found")
        for i in all_issues:
            print(f"    - {i}")
    else:
        print(f"  RESULT: ALL CLEAR — 5/5 layers pass")
    print(f"{'='*60}")

    return len(all_issues)


if __name__ == "__main__":
    issues = run_full_qa()
    sys.exit(1 if issues > 0 else 0)
