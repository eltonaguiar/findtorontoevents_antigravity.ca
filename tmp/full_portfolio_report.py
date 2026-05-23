#!/usr/bin/env python3
"""Generate comprehensive portfolio report for updates page."""
import json
from datetime import datetime, timezone, timedelta

EST = timezone(timedelta(hours=-5))
now = datetime.now(EST)

state = json.load(open('audit_dashboard/data/claudes_test_state.json'))

print("=" * 120)
print("COMPREHENSIVE PORTFOLIO REPORT")
print(f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S EST')}")
print("=" * 120)

total_resets = 0
total_running_strong = 0
total_positions_ever = 0

for pid, port in sorted(state.items(), key=lambda x: x[1].get('equity', 0) - x[1].get('initial_capital', 0), reverse=True):
    name = port.get('name', pid)
    ic = port.get('initial_capital', 10000)
    equity = port.get('equity', ic)
    pnl_usd = equity - ic
    pnl_pct = (pnl_usd / ic) * 100 if ic > 0 else 0
    positions = port.get('positions', [])
    closed = port.get('closed', [])
    wins = port.get('wins', 0)
    losses = port.get('losses', 0)
    total_trades = wins + losses
    resets = port.get('resets', 0)
    status = port.get('status', 'ACTIVE')
    methodology = port.get('methodology', '?')
    created = port.get('created_at', '')
    last_updated = port.get('last_updated', '')
    max_dd = port.get('max_drawdown_pct', 0)
    hwm = port.get('high_water_mark', ic)
    commission = port.get('total_commission', 0)

    # Calculate hours active
    hours_active = 0
    if created:
        try:
            created_dt = datetime.fromisoformat(created)
            hours_active = (now - created_dt).total_seconds() / 3600
        except:
            pass

    days_active = hours_active / 24

    if resets > 0:
        total_resets += resets
    else:
        if total_trades > 0 or len(positions) > 0:
            total_running_strong += 1

    total_positions_ever += total_trades + len(positions)

    wr = (wins / total_trades * 100) if total_trades > 0 else 0

    print(f"\n{'─' * 100}")
    print(f"  {name} [{methodology.upper()}] — {status}")
    print(f"  Capital: ${ic:,.0f} → ${equity:,.2f} ({pnl_pct:+.3f}%)")
    print(f"  Active: {days_active:.1f} days ({hours_active:.0f} hours)")
    print(f"  Positions: {len(positions)} open | {total_trades} closed (W:{wins} L:{losses} WR:{wr:.1f}%)")
    print(f"  Max DD: {max_dd:.2f}% | HWM: ${hwm:,.2f} | Commission: ${commission:.2f}")
    print(f"  Resets: {resets} | Prop: {port.get('prop_firm', False)}")

    # Show current positions
    if positions:
        print(f"  Current Holdings:")
        for pos in positions:
            sym = pos.get('symbol', '?')
            d = pos.get('direction', '?')
            entry = pos.get('entry_price', 0)
            tp = pos.get('take_profit', 0)
            sl = pos.get('stop_loss', 0)
            pnl = pos.get('pnl_pct', 0)
            pnl_d = pos.get('pnl_usd', 0)
            strat = pos.get('strategy', '?')
            size = pos.get('size_usd', 0)
            opened = pos.get('opened_at', '')
            print(f"    {sym:14s} {d:5s} ${size:>8,.2f} entry=${entry:<12,.4f} TP=${tp:<12,.4f} SL=${sl:<12,.4f} PnL={pnl:+.2f}% (${pnl_d:+.2f}) | {strat}")

    # Show reset history
    if resets > 0:
        print(f"  Reset History:")
        ls = port.get('lifetime_stats', {})
        reset_log = ls.get('reset_log', [])
        for r in reset_log:
            print(f"    Reset #{r.get('reset_num', '?')}: {r.get('time', '?')[:19]} | Equity=${r.get('equity_at_reset', 0):,.2f} | PnL=${r.get('pnl_usd', 0):+.2f} | W:{r.get('wins', 0)} L:{r.get('losses', 0)} | DD={r.get('max_dd', 0):.1f}% | {r.get('reason', '?')}")

        reset_hist = port.get('reset_history', [])
        for r in reset_hist:
            print(f"    Blow event: {r.get('time', '?')[:19]} | Equity=${r.get('equity_at_blow', 0):,.2f} | {r.get('reason', '?')}")

    # Show last 5 closed trades
    if closed:
        print(f"  Last {min(5, len(closed))} Closed Trades:")
        for c in closed[-5:]:
            net = c.get('net_pnl_usd', 0)
            result = 'WIN' if net > 0 else 'LOSS'
            reason = c.get('exit_reason', '?')
            print(f"    {c.get('symbol','?'):14s} {c.get('direction','?'):5s} → {reason:8s} PnL=${net:+.2f} ({c.get('pnl_pct',0):+.2f}%) | {c.get('strategy','?')}")

print(f"\n{'=' * 120}")
print(f"SUMMARY")
print(f"  Total portfolios: {len(state)}")
print(f"  Running strong (no resets, has trades/positions): {total_running_strong}")
print(f"  Total resets across all portfolios: {total_resets}")
print(f"  Total positions opened ever: {total_positions_ever}")
print(f"  All portfolios currently profitable: {all(s.get('equity', s.get('initial_capital', 0)) >= s.get('initial_capital', 0) for s in state.values())}")
combined_pnl = sum(s.get('equity', s.get('initial_capital', 0)) - s.get('initial_capital', 0) for s in state.values())
print(f"  Combined unrealized P&L: ${combined_pnl:+,.2f}")
print(f"{'=' * 120}")
