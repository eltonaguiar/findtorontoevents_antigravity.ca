#!/usr/bin/env python3
"""Deep strategy performance analysis across all systems."""
import json, os, sys

system_paths = {
    'battleground': 'battleground/data',
    'alpha_engine': 'alpha_engine/data',
    'kimi_claw': 'KIMI_RISEOFTHECLAW/data',
    'paper_trading': 'paper_trading/data',
    'multi_asset': 'multi_asset/data',
    'mercury2': 'mercury2/data',
    'crypto_signal': 'crypto_signal_engine/data',
    'crypto_ml_edge': 'crypto_ml_edge/data',
    'ml_system_a': 'ml_battleground/system_a_filter/data',
    'ml_system_b': 'ml_battleground/system_b_regime/data',
    'ml_system_c': 'ml_battleground/system_c_deeplearn/data',
    'ml_system_d': 'ml_battleground/system_d_carry/data',
    'ml_system_e': 'ml_battleground/system_e_momentum/data',
    'ml_system_f': 'ml_battleground/system_f_clawsofdoom/data',
    'breakout_a': 'breakout_arena/approach_a_sr_breakout/data',
    'breakout_b': 'breakout_arena/approach_b_ml_breakout/data',
    'breakout_c': 'breakout_arena/approach_c_spike_reverse/data',
    'coinglass': 'coinglass_strategies/data',
}

# ── Collect all closed picks ──
rows = []
all_strat_data = {}  # strategy -> list of pnl values

for sys_name, data_dir in system_paths.items():
    closed = []
    for fname in ['closed_picks.json', 'multi_asset_closed.json']:
        fpath = os.path.join(data_dir, fname)
        if os.path.exists(fpath):
            try:
                with open(fpath) as f:
                    data = json.load(f)
                if isinstance(data, list):
                    closed.extend(data)
            except:
                pass
    if not closed:
        continue

    pnls = []
    wins = losses = 0
    for p in closed:
        pnl = p.get('realized_pnl_pct', p.get('pnl_pct', p.get('unrealized_pnl_pct', 0))) or 0
        if isinstance(pnl, (int, float)) and abs(pnl) > 0 and abs(pnl) < 1:
            pnl *= 100
        status = (p.get('status', '') or '').upper()
        if 'WON' in status or 'TP' in status or 'WIN' in status:
            wins += 1
        elif 'LOST' in status or 'SL' in status or 'LOSS' in status:
            losses += 1
        if abs(pnl) > 0.001:
            pnls.append(pnl)

        # Strategy-level tracking
        strat = p.get('strategy', p.get('strategy_name', 'unknown'))
        strat_key = f"{sys_name}::{strat}"
        all_strat_data.setdefault(strat_key, []).append(pnl)

    total_wl = wins + losses
    wr = wins / total_wl * 100 if total_wl else 0
    avg_pnl = sum(pnls) / len(pnls) if pnls else 0
    total_pnl = sum(pnls)
    pos = [p for p in pnls if p > 0]
    neg = [p for p in pnls if p < 0]
    pf = sum(pos) / abs(sum(neg)) if neg else 999

    equity = 1000
    for pv in pnls:
        equity *= (1 + pv / 100)

    rows.append((sys_name, len(closed), len(pnls), wins, losses, wr, avg_pnl, total_pnl, pf, equity))

# ── System-level table ──
rows.sort(key=lambda x: x[7], reverse=True)

print("=" * 110)
print("SYSTEM-BY-SYSTEM PERFORMANCE (sorted by Total PnL)")
print("=" * 110)
hdr = "{:<25s} {:>5s} {:>5s} {:>8s} {:>6s} {:>9s} {:>10s} {:>6s} {:>10s}"
print(hdr.format('System', 'Close', 'Real', 'W/L', 'WR', 'Avg PnL', 'Total PnL', 'PF', '$1000'))
print("-" * 110)
tw = tl = tt = 0
for r in rows:
    sys_name, cl, real, w, l, wr, avg, tot, pf, eq = r
    tw += w
    tl += l
    tt += tot
    eq_s = "${:,.0f}".format(eq) if eq > 0.01 else "$0"
    pf_s = "{:.2f}".format(pf) if pf < 100 else "INF"
    line = "{:<25s} {:>5d} {:>5d} {:>3d}W/{:<3d}L {:>5.1f}% {:>+8.3f}% {:>+9.1f}% {:>6s} {:>10s}"
    print(line.format(sys_name, cl, real, w, l, wr, avg, tot, pf_s, eq_s))

print("-" * 110)
total_wr = tw / (tw + tl) * 100 if tw + tl else 0
print("AGGREGATE: {} closed | {}W/{}L ({:.1f}%) | Total PnL: {:+.1f}%".format(
    sum(r[1] for r in rows), tw, tl, total_wr, tt))

# ── BATTLEGROUND ONLY (our proven system) ──
print("\n" + "=" * 110)
print("BATTLEGROUND DEEP DIVE (Only Proven System)")
print("=" * 110)

bg_closed = []
for fname in ['closed_picks.json']:
    fpath = os.path.join('battleground/data', fname)
    if os.path.exists(fpath):
        with open(fpath) as f:
            bg_closed = json.load(f)

bg_strats = {}
bg_symbols = {}
for p in bg_closed:
    pnl = p.get('realized_pnl_pct', p.get('pnl_pct', 0)) or 0
    if isinstance(pnl, (int, float)) and abs(pnl) > 0 and abs(pnl) < 1:
        pnl *= 100
    strat = p.get('strategy', '?')
    sym = p.get('symbol', '?')

    bg_strats.setdefault(strat, {'pnls': [], 'w': 0, 'l': 0})
    bg_strats[strat]['pnls'].append(pnl)
    status = (p.get('status', '') or '').upper()
    if 'WON' in status or 'TP' in status: bg_strats[strat]['w'] += 1
    elif 'LOST' in status or 'SL' in status: bg_strats[strat]['l'] += 1

    bg_symbols.setdefault(sym, []).append(pnl)

print("\nStrategy breakdown:")
print("{:<45s} {:>5s} {:>8s} {:>6s} {:>9s} {:>10s} {:>6s}".format(
    'Strategy', 'Count', 'W/L', 'WR', 'Avg PnL', 'Total', 'PF'))
print("-" * 100)
for s, d in sorted(bg_strats.items(), key=lambda x: sum(x[1]['pnls']), reverse=True):
    pnls = d['pnls']
    real = [p for p in pnls if abs(p) > 0.001]
    total_wl = d['w'] + d['l']
    wr = d['w'] / total_wl * 100 if total_wl else 0
    avg = sum(real) / len(real) if real else 0
    tot = sum(real)
    pos = sum(p for p in real if p > 0)
    neg = abs(sum(p for p in real if p < 0))
    pf = pos / neg if neg else 999
    pf_s = "{:.2f}".format(pf) if pf < 100 else "INF"
    line = "{:<45s} {:>5d} {:>3d}W/{:<3d}L {:>5.1f}% {:>+8.3f}% {:>+9.1f}% {:>6s}"
    print(line.format(s[:45], len(pnls), d['w'], d['l'], wr, avg, tot, pf_s))

print("\nSymbol breakdown (top 10):")
print("{:<15s} {:>5s} {:>9s} {:>10s}".format('Symbol', 'Count', 'Avg PnL', 'Total'))
print("-" * 45)
for sym, pnls in sorted(bg_symbols.items(), key=lambda x: sum(x[1]), reverse=True)[:10]:
    real = [p for p in pnls if abs(p) > 0.001]
    avg = sum(real) / len(real) if real else 0
    print("{:<15s} {:>5d} {:>+8.3f}% {:>+9.1f}%".format(sym, len(pnls), avg, sum(real)))

# ── TOP 20 strategies across ALL systems ──
print("\n" + "=" * 110)
print("TOP 20 STRATEGIES ACROSS ALL SYSTEMS (min 5 trades, sorted by avg PnL)")
print("=" * 110)

strat_rows = []
for key, pnls in all_strat_data.items():
    real = [p for p in pnls if abs(p) > 0.001]
    if len(real) < 5:
        continue
    avg = sum(real) / len(real)
    tot = sum(real)
    pos = [p for p in real if p > 0]
    neg = [p for p in real if p < 0]
    wr = len(pos) / len(real) * 100
    pf = sum(pos) / abs(sum(neg)) if neg else 999
    strat_rows.append((key, len(real), wr, avg, tot, pf))

strat_rows.sort(key=lambda x: x[3], reverse=True)
print("{:<55s} {:>5s} {:>6s} {:>9s} {:>10s} {:>6s}".format(
    'System::Strategy', 'Count', 'WR', 'Avg PnL', 'Total', 'PF'))
print("-" * 100)
for key, cnt, wr, avg, tot, pf in strat_rows[:20]:
    pf_s = "{:.2f}".format(pf) if pf < 100 else "INF"
    print("{:<55s} {:>5d} {:>5.1f}% {:>+8.3f}% {:>+9.1f}% {:>6s}".format(key[:55], cnt, wr, avg, tot, pf_s))

# ── WORST 10 strategies ──
print("\nBOTTOM 10 STRATEGIES (money destroyers):")
print("-" * 100)
for key, cnt, wr, avg, tot, pf in strat_rows[-10:]:
    pf_s = "{:.2f}".format(pf) if pf < 100 else "INF"
    print("{:<55s} {:>5d} {:>5.1f}% {:>+8.3f}% {:>+9.1f}% {:>6s}".format(key[:55], cnt, wr, avg, tot, pf_s))

# ── Benchmark comparison ──
print("\n" + "=" * 110)
print("BENCHMARK COMPARISON")
print("=" * 110)
# Calculate our aggregate metrics
all_real_pnls = []
for key, pnls in all_strat_data.items():
    for p in pnls:
        if abs(p) > 0.001:
            all_real_pnls.append(p)

our_wr = len([p for p in all_real_pnls if p > 0]) / len(all_real_pnls) * 100 if all_real_pnls else 0
our_avg = sum(all_real_pnls) / len(all_real_pnls) if all_real_pnls else 0
our_pos = sum(p for p in all_real_pnls if p > 0)
our_neg = abs(sum(p for p in all_real_pnls if p < 0))
our_pf = our_pos / our_neg if our_neg else 0

# Only battleground
bg_all = []
for key, pnls in all_strat_data.items():
    if key.startswith('battleground::'):
        bg_all.extend([p for p in pnls if abs(p) > 0.001])
bg_wr = len([p for p in bg_all if p > 0]) / len(bg_all) * 100 if bg_all else 0
bg_avg = sum(bg_all) / len(bg_all) if bg_all else 0
bg_pos = sum(p for p in bg_all if p > 0)
bg_neg = abs(sum(p for p in bg_all if p < 0))
bg_pf = bg_pos / bg_neg if bg_neg else 0

print("{:<30s} {:>8s} {:>8s} {:>8s} {:>12s}".format('Benchmark', 'WR', 'Avg PnL', 'PF', 'Verdict'))
print("-" * 75)
print("{:<30s} {:>7.1f}% {:>+7.3f}% {:>7.2f}  {:>12s}".format(
    'ALL SYSTEMS COMBINED', our_wr, our_avg, our_pf, 'LOSING' if our_avg < 0 else 'WINNING'))
print("{:<30s} {:>7.1f}% {:>+7.3f}% {:>7.2f}  {:>12s}".format(
    'BATTLEGROUND ONLY', bg_wr, bg_avg, bg_pf, 'LOSING' if bg_avg < 0 else 'WINNING'))
print("{:<30s} {:>7.1f}% {:>+7.3f}% {:>7.2f}  {:>12s}".format(
    'Random coin flip', 50.0, 0.0, 1.0, 'BREAK-EVEN'))
print("{:<30s} {:>7.1f}% {:>+7.3f}% {:>7.2f}  {:>12s}".format(
    'Hedge fund target', 55.0, 0.200, 1.50, 'GOOD'))
print("{:<30s} {:>7.1f}% {:>+7.3f}% {:>7.2f}  {:>12s}".format(
    'Elite quant (Renaissance)', 51.0, 0.050, 1.10, 'GREAT (volume)'))

# ── $1000 simulation: battleground only vs all systems ──
print("\n$1000 COMPOUNDING SIMULATION:")
eq_all = 1000
for p in all_real_pnls:
    eq_all *= (1 + p / 100)
eq_bg = 1000
for p in bg_all:
    eq_bg *= (1 + p / 100)

# Only winning strategies (PF > 1.2, WR > 55%, min 10 trades)
cherry_pnls = []
for key, pnls in all_strat_data.items():
    real = [p for p in pnls if abs(p) > 0.001]
    if len(real) < 10:
        continue
    pos_sum = sum(p for p in real if p > 0)
    neg_sum = abs(sum(p for p in real if p < 0))
    wr = len([p for p in real if p > 0]) / len(real) * 100
    pf = pos_sum / neg_sum if neg_sum else 999
    if pf > 1.2 and wr > 55:
        cherry_pnls.extend(real)

eq_cherry = 1000
for p in cherry_pnls:
    eq_cherry *= (1 + p / 100)

print("  All systems combined:     ${:>10,.2f} ({:+.1f}%) over {} trades".format(
    eq_all, (eq_all / 1000 - 1) * 100, len(all_real_pnls)))
print("  Battleground only:        ${:>10,.2f} ({:+.1f}%) over {} trades".format(
    eq_bg, (eq_bg / 1000 - 1) * 100, len(bg_all)))
print("  Cherry-picked winners:    ${:>10,.2f} ({:+.1f}%) over {} trades".format(
    eq_cherry, (eq_cherry / 1000 - 1) * 100, len(cherry_pnls)))
print("  S&P 500 buy-and-hold:     ${:>10,.2f} (+10.0%) (annual avg)".format(1100))
print("  GIC (5% guaranteed):      ${:>10,.2f} (+5.0%) (annual, zero risk)".format(1050))
