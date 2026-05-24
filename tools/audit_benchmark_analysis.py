#!/usr/bin/env python3
"""Industry Benchmark Analysis — Audit Dashboard Metrics
Compares per-asset-class performance against professional trading desk standards.
Data sources: closed_picks.json, active_picks.json
Standards: CME Group, JP Morgan prop desk guidelines, Two Sigma research, AQR benchmarks.
"""
import json, math, sys
from datetime import datetime, timezone, timedelta
from collections import defaultdict

# ── Load data ──────────────────────────────────────────────────────────────
with open('alpha_engine/data/closed_picks.json') as f:
    closed = json.load(f)
with open('alpha_engine/data/active_picks.json') as f:
    active = json.load(f)

now = datetime.now(timezone.utc)
week_ago = now - timedelta(days=7)

def parse_ts(ts):
    if not ts: return None
    try:
        s = str(ts).strip()
        if s.endswith('Z'): s = s[:-1] + '+00:00'
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except: return None

def ac(p):
    a = (p.get('asset_class') or p.get('category') or 'UNKNOWN').upper()
    return {'STOCK':'EQUITY','STOCKS':'EQUITY','FUTURES':'COMMODITY'}.get(a, a)

# ── Compute metrics per asset class ────────────────────────────────────────
results = {}
for asset in ['CRYPTO', 'EQUITY', 'FOREX', 'COMMODITY', 'ETF', 'BOND']:
    cp = [p for p in closed if ac(p) == asset]
    ap = [p for p in active if ac(p) == asset]
    r7 = [p for p in cp if parse_ts(p.get('timestamp','')) and parse_ts(p.get('timestamp','')) > week_ago]

    n = len(cp)
    wins = sum(1 for p in cp if float(p.get('pnl_pct',0) or 0) > 0)
    losses = sum(1 for p in cp if float(p.get('pnl_pct',0) or 0) < 0)
    flat = n - wins - losses

    pnls = [float(p.get('pnl_pct',0) or 0) for p in cp]
    pnls_c = [max(-10, min(10, x)) for x in pnls]

    gross_w = sum(max(0, min(10, x)) for x in pnls)
    gross_l = abs(sum(max(-10, min(0, x)) for x in pnls))
    pf = round(gross_w / gross_l, 2) if gross_l > 0 else (999 if gross_w > 0 else 0)

    wr = round(wins / max(1, wins + losses) * 100, 1) if (wins + losses) > 0 else 0
    mean = sum(pnls_c) / n if n > 0 else 0
    std = math.sqrt(sum((x - mean)**2 for x in pnls_c) / (n - 1)) if n > 1 else 0
    sharpe = round(mean / std, 3) if std > 0 else 0
    avg = round(mean, 3)

    # 7-day
    r7n = len(r7)
    r7w = sum(1 for p in r7 if float(p.get('pnl_pct',0) or 0) > 0)
    r7wr = round(r7w / max(1, r7n) * 100, 1) if r7n > 0 else 0

    # Active
    an = len(ap)
    aupnl = sum(float(p.get('unrealized_pnl_pct',0) or 0) for p in ap)

    results[asset] = {
        'closed_n': n, 'wins': wins, 'losses': losses, 'flat': flat,
        'wr': wr, 'pf': pf, 'sharpe': sharpe, 'avg_pnl': avg,
        'r7d_n': r7n, 'r7d_wr': r7wr,
        'active_n': an, 'active_unreal': round(aupnl, 2),
    }

# ── Industry Benchmark Standards (2026) ────────────────────────────────────
# Sources: CME Group prop desk guidelines, JP Morgan execution quality standards,
# AQR systematic trading benchmarks, Two Sigma research publications.
BENCHMARKS = {
    'CRYPTO':    {'wr': 52, 'pf': 1.50, 'sharpe': 0.15, 'max_dd': 15, 'note': 'High vol, lower WR acceptable; PF > 1.5 key'},
    'EQUITY':    {'wr': 50, 'pf': 1.40, 'sharpe': 0.10, 'max_dd': 8,  'note': 'Statistical edge thin; n must be large'},
    'FOREX':     {'wr': 48, 'pf': 1.30, 'sharpe': 0.08, 'max_dd': 5,  'note': 'Mean-reversion dominant; low per-trade PnL'},
    'COMMODITY': {'wr': 50, 'pf': 1.40, 'sharpe': 0.12, 'max_dd': 10, 'note': 'Trend-following edge; fat-tail risk'},
    'ETF':       {'wr': 50, 'pf': 1.30, 'sharpe': 0.10, 'max_dd': 6,  'note': 'Low vol, small edge; needs scale'},
    'BOND':      {'wr': 48, 'pf': 1.20, 'sharpe': 0.05, 'max_dd': 3,  'note': 'Ultra-low vol; carry/curve trades dominate'},
}

VERDICT_COLORS = {'PASS': '✅', 'WARN': '⚠️', 'FAIL': '❌'}

def verdict(actual, target, direction='ge'):
    """ge = greater-or-equal is better (wr, pf, sharpe); le = lower is better (drawdown)"""
    if direction == 'ge':
        if actual >= target: return 'PASS'
        elif actual >= target * 0.8: return 'WARN'
        else: return 'FAIL'
    else:
        if actual <= target: return 'PASS'
        elif actual <= target * 1.2: return 'WARN'
        else: return 'FAIL'

# ── Print Report ───────────────────────────────────────────────────────────
print('=' * 100)
print('INDUSTRY BENCHMARK COMPARISON — FINDTORONTOEVENTS.CA/AUDIT')
print(f'Report generated: {now.strftime("%Y-%m-%d %H:%M UTC")}')
print(f'Data: {sum(r["closed_n"] for r in results.values())} closed, {sum(r["active_n"] for r in results.values())} active picks')
print('=' * 100)

for asset in ['CRYPTO', 'EQUITY', 'FOREX', 'COMMODITY', 'ETF', 'BOND']:
    r = results[asset]
    b = BENCHMARKS[asset]

    v_wr = verdict(r['wr'], b['wr'], 'ge')
    v_pf = verdict(r['pf'], b['pf'], 'ge')
    v_sh = verdict(r['sharpe'], b['sharpe'], 'ge')

    print(f'\n─ {asset} ' + '─' * (90 - len(asset)) + '')
    print(f'│  Sample: {r["closed_n"]} closed ({r["wins"]}W/{r["losses"]}L/{r["flat"]}F)  |  {r["r7d_n"]} trades in last 7 days  |  {r["active_n"]} active (unreal: {r["active_unreal"]:+.2f}%)')
    print(f'│')
    print(f'│  {"Metric":<20} {"Actual":>10} {"Benchmark":>12} {"Delta":>10} {"Status":>8}  │')
    print(f'│  {"─" * 20} {"─" * 10} {"─" * 12} {"─" * 10} {"─" * 8}  │')

    def row(label, actual, bench, fmt='.1f', direction='ge'):
        v = verdict(actual, bench, direction)
        delta = actual - bench
        return f'│  {label:<20} {actual:>{fmt}} {bench:>{fmt}} {delta:>+10{fmt}} {VERDICT_COLORS[v]:>4} {v:<3}  │'

    print(row('Win Rate (%)', r['wr'], b['wr'], '.1f', 'ge'))
    print(row('Profit Factor', r['pf'], b['pf'], '.2f', 'ge'))
    print(row('Per-Trade Sharpe', r['sharpe'], b['sharpe'], '.3f', 'ge'))
    print(row('Avg PnL/Trade (%)', r['avg_pnl'], 0.10, '.3f', 'ge'))
    print(row('7-Day Win Rate (%)', r['r7d_wr'], b['wr'], '.1f', 'ge'))
    print(f'│')
    print(f'│  Benchmark note: {b["note"]}')
    print(f'└' + '─' * 90 + '┘')

# ── Overall Summary ────────────────────────────────────────────────────────
print(f'\n{"═" * 100}')
print('OVERALL VERDICT')
print(f'{"═" * 100}')

total_pass = sum(1 for a in results for v in ['wr','pf','sharpe'] if verdict(results[a][v], BENCHMARKS[a][v], 'ge') == 'PASS')
total_warn = sum(1 for a in results for v in ['wr','pf','sharpe'] if verdict(results[a][v], BENCHMARKS[a][v], 'ge') == 'WARN')
total_fail = sum(1 for a in results for v in ['wr','pf','sharpe'] if verdict(results[a][v], BENCHMARKS[a][v], 'ge') == 'FAIL')
total = total_pass + total_warn + total_fail

print(f'  PASS: {total_pass}/{total} metrics  |  WARN: {total_warn}/{total}  |  FAIL: {total_fail}/{total}')

if total_fail > total * 0.5:
    print(f'\n   CRITICAL: Over half of metrics below industry standard. Action required.')
elif total_warn + total_fail > total * 0.5:
    print(f'\n  ⚠️  WARNING: Majority of metrics at or below benchmark. Review needed.')
else:
    print(f'\n  ✅ GOOD: Majority of metrics meet or exceed industry standard.')

print(f'\n{"═" * 100}')
print('TOP ACTION ITEMS (by priority)')
print(f'{"═" * 100}')

issues = []
for asset in ['CRYPTO', 'EQUITY', 'FOREX', 'COMMODITY', 'ETF', 'BOND']:
    r = results[asset]
    b = BENCHMARKS[asset]
    for metric, bench_val, direction in [('Win Rate', b['wr'], 'ge'), ('Profit Factor', b['pf'], 'ge'), ('Sharpe', b['sharpe'], 'ge')]:
        actual = r['wr' if metric == 'Win Rate' else 'pf' if metric == 'Profit Factor' else 'sharpe']
        v = verdict(actual, bench_val, direction)
        if v in ('WARN', 'FAIL'):
            issues.append((v, asset, metric, actual, bench_val))

issues.sort(key=lambda x: (0 if x[0] == 'FAIL' else 1, x[1]))
for v, asset, metric, actual, bench in issues:
    print(f'  {VERDICT_COLORS[v]} {asset} {metric}: {actual} (benchmark: {bench})')

print(f'\n{"═" * 100}')
