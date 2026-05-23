#!/usr/bin/env python3
"""Full data validation: every position, every closed trade, every equity value."""
import json, urllib.request, sys
from datetime import datetime, timezone
sys.stdout.reconfigure(encoding='utf-8')

# Fetch live prices from Bybit
bybit = {}
for cat in ['spot', 'linear']:
    url = f'https://api.bybit.com/v5/market/tickers?category={cat}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    resp = urllib.request.urlopen(req, timeout=15)
    for t in json.loads(resp.read())['result']['list']:
        if t['symbol'] not in bybit:
            bybit[t['symbol']] = float(t['lastPrice'])

with open('audit_dashboard/data/claudes_test_state.json') as f:
    state = json.load(f)

errors = []
warnings = []
now = datetime.now(timezone.utc)

print("=" * 80)
print("  COMPREHENSIVE DATA VALIDATION REPORT")
print(f"  {now.strftime('%Y-%m-%d %H:%M UTC')}")
print("=" * 80)

# 1. Validate every open position
print("\n[1] OPEN POSITION VALIDATION")
print("-" * 60)
total_positions = 0
for name, pf in sorted(state.items()):
    if not isinstance(pf, dict) or 'positions' not in pf:
        continue
    for pos in pf.get('positions', []):
        total_positions += 1
        sym = pos.get('symbol', '?')
        entry = pos.get('entry_price', 0)
        size = pos.get('size_usd', 0)
        direction = pos.get('direction', '')
        tp = pos.get('take_profit', 0)
        sl = pos.get('stop_loss', 0)
        opened = pos.get('opened_at', '')
        strategy = pos.get('strategy', '')
        source = pos.get('_price_source', '')

        # Validate required fields
        for field in ['entry_price', 'size_usd', 'direction', 'opened_at', 'take_profit', 'stop_loss']:
            if not pos.get(field):
                errors.append(f"MISSING FIELD: {name}/{sym} missing '{field}'")

        # Validate direction
        if direction not in ('LONG', 'SHORT'):
            errors.append(f"BAD DIRECTION: {name}/{sym} direction='{direction}'")

        # Validate entry price > 0
        if entry <= 0:
            errors.append(f"ZERO ENTRY: {name}/{sym} entry_price={entry}")

        # Validate size > 0
        if size <= 0:
            errors.append(f"ZERO SIZE: {name}/{sym} size_usd={size}")

        # Validate TP/SL make sense
        if direction == 'LONG':
            if tp and tp <= entry:
                warnings.append(f"TP BELOW ENTRY: {name}/{sym} LONG entry={entry} tp={tp}")
            if sl and sl >= entry:
                warnings.append(f"SL ABOVE ENTRY: {name}/{sym} LONG entry={entry} sl={sl}")
        elif direction == 'SHORT':
            if tp and tp >= entry:
                warnings.append(f"TP ABOVE ENTRY: {name}/{sym} SHORT entry={entry} tp={tp}")
            if sl and sl <= entry:
                warnings.append(f"SL BELOW ENTRY: {name}/{sym} SHORT entry={entry} sl={sl}")

        # Validate entry price against live Bybit
        norm = sym.replace('-USD', 'USDT').replace('-', '')
        live = bybit.get(norm)
        if live and entry:
            drift = abs(live - entry) / entry * 100
            if drift > 15:
                errors.append(f"PRICE DRIFT >15%: {name}/{sym} entry={entry} live={live} drift={drift:.1f}%")
            elif drift > 5:
                warnings.append(f"PRICE DRIFT >5%: {name}/{sym} entry={entry} live={live} drift={drift:.1f}%")

            # Calculate real PnL
            if direction == 'LONG':
                real_pnl_pct = ((live - entry) / entry) * 100
            else:
                real_pnl_pct = ((entry - live) / entry) * 100
            real_pnl_usd = (real_pnl_pct / 100) * size

            stored_pnl = pos.get('pnl_pct', 0)
            pnl_diff = abs(real_pnl_pct - stored_pnl)

            status = "OK" if pnl_diff < 2 else "STALE"
            if abs(real_pnl_pct) > 10:
                errors.append(f"PNL >10%: {name}/{sym} real={real_pnl_pct:+.2f}%")

            print(f"  {name:30s} {sym:15s} {direction:5s} entry={entry:<12} live={live:<12} pnl={real_pnl_pct:+.2f}% (${real_pnl_usd:+,.2f}) [{status}]")
        else:
            if not live:
                warnings.append(f"NO LIVE PRICE: {name}/{sym} (not found on Bybit)")
            print(f"  {name:30s} {sym:15s} {direction:5s} entry={entry:<12} live=N/A")

        # Validate opened_at is a valid date and not in the future
        if opened:
            try:
                dt = datetime.fromisoformat(opened.replace('Z', '+00:00'))
                if dt > now:
                    errors.append(f"FUTURE DATE: {name}/{sym} opened_at={opened}")
                age_h = (now - dt).total_seconds() / 3600
                if age_h > 168:  # > 7 days
                    warnings.append(f"OLD POSITION: {name}/{sym} opened {age_h:.0f}h ago")
            except:
                errors.append(f"BAD DATE: {name}/{sym} opened_at='{opened}'")

print(f"\n  Total open positions validated: {total_positions}")

# 2. Validate every closed trade
print("\n[2] CLOSED TRADE VALIDATION")
print("-" * 60)
total_closed = 0
for name, pf in sorted(state.items()):
    if not isinstance(pf, dict):
        continue
    closed = pf.get('closed', pf.get('recent_closed', []))
    for t in closed:
        total_closed += 1
        sym = t.get('symbol', '?')
        entry = t.get('entry_price', 0)
        exit_p = t.get('exit_price', 0)
        pnl_pct = t.get('pnl_pct', 0)
        pnl_usd = t.get('pnl_usd', 0)
        direction = t.get('direction', '')
        reason = t.get('exit_reason', t.get('close_reason', t.get('reason', '?')))

        # Validate PnL math
        if entry > 0 and exit_p > 0:
            if direction == 'LONG':
                expected_pnl = ((exit_p - entry) / entry) * 100
            elif direction == 'SHORT':
                expected_pnl = ((entry - exit_p) / entry) * 100
            else:
                expected_pnl = pnl_pct

            diff = abs(expected_pnl - pnl_pct)
            if diff > 0.5:
                errors.append(f"PNL MATH ERROR: {name}/{sym} stored={pnl_pct:.2f}% computed={expected_pnl:.2f}% (diff={diff:.2f})")
                print(f"  !! {name:30s} {sym:15s} entry={entry} exit={exit_p} stored_pnl={pnl_pct:.2f}% computed={expected_pnl:.2f}%")
            else:
                print(f"  OK {name:30s} {sym:15s} {direction:5s} {pnl_pct:+.2f}% (${pnl_usd:+,.2f}) reason={reason}")
        else:
            if entry <= 0:
                errors.append(f"ZERO ENTRY: {name}/{sym} closed trade entry_price={entry}")
            if exit_p <= 0:
                errors.append(f"ZERO EXIT: {name}/{sym} closed trade exit_price={exit_p}")
            print(f"  ?? {name:30s} {sym:15s} entry={entry} exit={exit_p}")

        # Validate exit reason
        if reason not in ('TP', 'SL', 'MANUAL', 'TIMEOUT', 'BLOWN', '?', '--'):
            warnings.append(f"UNUSUAL EXIT: {name}/{sym} reason='{reason}'")

print(f"\n  Total closed trades validated: {total_closed}")

# 3. Win/Loss count validation
print("\n[3] WIN/LOSS COUNT VALIDATION")
print("-" * 60)
for name, pf in sorted(state.items()):
    if not isinstance(pf, dict) or 'positions' not in pf:
        continue
    closed = pf.get('closed', pf.get('recent_closed', []))
    stored_wins = pf.get('wins', 0)
    stored_losses = pf.get('losses', 0)
    computed_wins = sum(1 for t in closed if t.get('net_pnl_usd', t.get('pnl_usd', 0)) > 0)
    computed_losses = sum(1 for t in closed if t.get('net_pnl_usd', t.get('pnl_usd', 0)) <= 0)

    if stored_wins != computed_wins or stored_losses != computed_losses:
        errors.append(f"W/L MISMATCH: {name} stored W={stored_wins}/L={stored_losses} computed W={computed_wins}/L={computed_losses}")
        print(f"  !! {name:35s} stored W={stored_wins}/L={stored_losses}  computed W={computed_wins}/L={computed_losses}")
    elif closed:
        print(f"  OK {name:35s} W={stored_wins}/L={stored_losses}")

# 4. Equity validation (live recalculated)
print("\n[4] EQUITY VALIDATION (vs LIVE PRICES)")
print("-" * 60)
total_phantom = 0
for name, pf in sorted(state.items()):
    if not isinstance(pf, dict) or 'positions' not in pf:
        continue
    initial = pf.get('initial_capital', 10000)
    commission = pf.get('total_commission', 0)
    slippage = pf.get('total_slippage', 0)
    closed = pf.get('closed', pf.get('recent_closed', []))
    realized = sum(t.get('pnl_usd', 0) for t in closed)

    unrealized = 0
    for pos in pf.get('positions', []):
        s = pos.get('symbol', '?')
        e = pos.get('entry_price', 0)
        sz = pos.get('size_usd', 0)
        d = pos.get('direction', 'LONG')
        norm = s.replace('-USD', 'USDT').replace('-', '')
        live = bybit.get(norm)
        if live and e and sz:
            pct = ((live - e) / e) if d == 'LONG' else ((e - live) / e)
            unrealized += pct * sz
        else:
            unrealized += pos.get('pnl_usd', 0)

    true_eq = initial + realized + unrealized - commission - slippage
    stored_eq = pf.get('equity', 0)
    diff = stored_eq - true_eq
    total_phantom += diff

    if abs(diff) > 50:
        errors.append(f"PHANTOM EQUITY: {name} stored=${stored_eq:,.2f} true=${true_eq:,.2f} phantom=${diff:+,.2f}")
    if abs(diff) > 1:
        print(f"  {'!!' if abs(diff)>50 else 'ok'} {name:35s} stored=${stored_eq:>12,.2f} true=${true_eq:>12,.2f} diff=${diff:>8,.2f}")

print(f"\n  Total phantom P&L: ${total_phantom:,.2f}")

# 5. Symbol concentration check
print("\n[5] SYMBOL CONCENTRATION")
print("-" * 60)
sym_portfolios = {}
for name, pf in state.items():
    if not isinstance(pf, dict):
        continue
    for pos in pf.get('positions', []):
        sym = pos.get('symbol', '?')
        if sym not in sym_portfolios:
            sym_portfolios[sym] = []
        sym_portfolios[sym].append(name)

for sym, ports in sorted(sym_portfolios.items(), key=lambda x: -len(x[1])):
    if len(ports) >= 2:
        warnings.append(f"CONCENTRATION: {sym} in {len(ports)} portfolios: {', '.join(ports)}")
    print(f"  {sym:20s} in {len(ports)} portfolio(s): {', '.join(ports[:5])}")

# Summary
print("\n" + "=" * 80)
print(f"  VALIDATION COMPLETE")
print(f"  Positions: {total_positions} | Closed: {total_closed}")
print(f"  ERRORS: {len(errors)} | WARNINGS: {len(warnings)}")
print("=" * 80)
if errors:
    print("\n  ERRORS:")
    for e in errors:
        print(f"    [E] {e}")
if warnings:
    print("\n  WARNINGS:")
    for w in warnings:
        print(f"    [W] {w}")
