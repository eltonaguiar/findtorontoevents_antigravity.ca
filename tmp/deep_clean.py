#!/usr/bin/env python3
"""Deep clean ALL corrupt data from portfolio state and recalculate ALL metrics."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json

state = json.load(open('audit_dashboard/data/claudes_test_state.json'))

# Extended price ranges
PRICE_RANGES = {
    'DOGEUSDT': (0.03, 2.0), 'DOGE-USD': (0.03, 2.0),
    'SHIBUSDT': (0.000001, 0.01), 'SHIB-USD': (0.000001, 0.01),
    'TRXUSDT': (0.03, 1.0), 'TRX-USD': (0.03, 1.0),
    'AVAXUSDT': (3.0, 200.0), 'AVAX-USD': (3.0, 200.0),
    'BTCUSDT': (20000, 200000), 'BTC-USD': (20000, 200000),
    'ETHUSDT': (500, 15000), 'ETH-USD': (500, 15000),
    'SOLUSDT': (5, 500), 'SOL-USD': (5, 500),
    'XRPUSDT': (0.1, 20), 'XRP-USD': (0.1, 20),
    'BNBUSDT': (100, 2000), 'BNB-USD': (100, 2000),
    'ADAUSDT': (0.1, 10), 'ADA-USD': (0.1, 10),
    'DOTUSDT': (1, 100), 'DOT-USD': (1, 100),
    'LINKUSDT': (2, 200), 'LINK-USD': (2, 200),
    'MATICUSDT': (0.1, 10), 'MATIC-USD': (0.1, 10),
    'NOTUSDT': (0.0001, 0.1), 'NOT-USD': (0.0001, 0.1),
    'CHZUSDT': (0.01, 1.0), 'CHZ-USD': (0.01, 1.0),
    'JNJ': (100, 250), 'META': (200, 800), 'GME': (5, 100),
    'AAPL': (100, 300), 'MSFT': (200, 600), 'TSLA': (100, 500),
    'NVDA': (50, 300), 'SPY': (300, 700), 'QQQ': (250, 700),
}


def is_corrupt(sym, entry):
    if entry <= 0:
        return True
    clean_sym = sym.replace('=X', '').replace('.TO', '')
    rng = PRICE_RANGES.get(clean_sym) or PRICE_RANGES.get(sym)
    if rng:
        lo, hi = rng
        if entry < lo * 0.1 or entry > hi * 10:
            return True
    return False


total_rm_closed = 0
total_rm_open = 0
total_rm_dupes = 0
total_fake_pnl = 0

for pname, pdata in state.items():
    seen_closed_ids = set()
    seen_pos_ids = set()

    closed = pdata.get('closed', [])
    clean_closed = []
    removed_pnl = 0

    for t in closed:
        sym = t.get('symbol', '')
        entry = t.get('entry_price', 0)
        exit_p = t.get('exit_price', 0)
        pnl_pct = t.get('pnl_pct', 0) or 0
        tid = t.get('id', '')

        corrupt = is_corrupt(sym, entry)
        if not corrupt and exit_p > 0:
            corrupt = is_corrupt(sym, exit_p)

        dupe = tid in seen_closed_ids
        seen_closed_ids.add(tid)

        extreme = abs(pnl_pct) > 80

        if corrupt or dupe or extreme:
            this_pnl = t.get('net_pnl_usd', 0) or t.get('pnl_usd', 0) or 0
            removed_pnl += this_pnl
            if dupe:
                total_rm_dupes += 1
            else:
                total_rm_closed += 1
            reason = 'CORRUPT' if corrupt else 'DUPE' if dupe else 'EXTREME_PNL'
            print(f"  RM [{pname}] {sym} {t.get('direction','')} entry={entry} exit={exit_p} pnl={pnl_pct:.1f}% ${this_pnl:.2f} [{reason}]")
        else:
            clean_closed.append(t)

    positions = pdata.get('positions', [])
    clean_pos = []
    freed_size = 0

    for p in positions:
        sym = p.get('symbol', '')
        entry = p.get('entry_price', 0)
        pid = p.get('id', '')

        dupe = pid in seen_pos_ids
        seen_pos_ids.add(pid)
        corrupt = is_corrupt(sym, entry)

        if corrupt or dupe:
            freed_size += p.get('size_usd', 0) or 0
            total_rm_open += 1
            reason = 'CORRUPT' if corrupt else 'DUPE'
            print(f"  RM POS [{pname}] {sym} entry={entry} size=${p.get('size_usd',0):.2f} [{reason}]")
        else:
            clean_pos.append(p)

    if removed_pnl != 0 or freed_size > 0:
        old_eq = pdata.get('equity', 10000)
        init_cap = pdata.get('initial_capital', 10000)
        pdata['closed'] = clean_closed
        pdata['positions'] = clean_pos

        old_cash = pdata.get('cash', 0)
        new_cash = old_cash + freed_size - removed_pnl
        pdata['cash'] = max(new_cash, 0)

        pos_value = sum(p.get('size_usd', 0) or 0 for p in clean_pos)
        new_eq = pdata['cash'] + pos_value
        pdata['equity'] = new_eq

        wins = len([t for t in clean_closed if (t.get('pnl_pct', 0) or 0) > 0])
        losses = len([t for t in clean_closed if (t.get('pnl_pct', 0) or 0) <= 0])
        pdata['wins'] = wins
        pdata['losses'] = losses

        if pdata.get('high_water_mark', 0) > new_eq * 1.5:
            pdata['high_water_mark'] = new_eq

        eq_hist = pdata.get('equity_history', [])
        for eh in eq_hist:
            if eh.get('equity', 0) > new_eq * 2:
                eh['equity'] = min(eh['equity'], new_eq)

        pdata['max_drawdown_pct'] = 0
        if eq_hist:
            peak = init_cap
            max_dd = 0
            for eh in eq_hist:
                val = eh.get('equity', init_cap)
                if val > peak:
                    peak = val
                dd = (peak - val) / peak * 100 if peak > 0 else 0
                if dd > max_dd:
                    max_dd = dd
            pdata['max_drawdown_pct'] = max_dd

        total_comm = sum(
            (t.get('commission_entry', 0) or 0) + (t.get('commission_exit', 0) or 0)
            for t in clean_closed
        ) + sum(
            (p.get('commission_entry', 0) or 0)
            for p in clean_pos
        )
        pdata['total_commission'] = total_comm

        total_fake_pnl += removed_pnl
        pnl_pct_calc = (new_eq - init_cap) / init_cap * 100
        print(f"  -> [{pname}] ${old_eq:,.2f} -> ${new_eq:,.2f} ({pnl_pct_calc:+.2f}%) W/L={wins}/{losses}")

print(f"\n=== CLEANUP SUMMARY ===")
print(f"Corrupt trades removed: {total_rm_closed}")
print(f"Duplicate trades removed: {total_rm_dupes}")
print(f"Corrupt positions removed: {total_rm_open}")
print(f"Total fake PnL removed: ${total_fake_pnl:,.2f}")

with open('audit_dashboard/data/claudes_test_state.json', 'w') as f:
    json.dump(state, f, indent=2, default=str)
print("\nState file cleaned and saved.")

print("\n=== FINAL PORTFOLIO SUMMARY ===")
for pname, pdata in state.items():
    eq = pdata.get('equity', 10000)
    init = pdata.get('initial_capital', 10000)
    pnl_pct = (eq - init) / init * 100
    closed = pdata.get('closed', [])
    wins = len([t for t in closed if (t.get('pnl_pct', 0) or 0) > 0])
    losses = len([t for t in closed if (t.get('pnl_pct', 0) or 0) <= 0])
    pos = len(pdata.get('positions', []))
    wr_str = f"{wins/(wins+losses)*100:.0f}%" if (wins+losses) > 0 else "N/A"
    flag = ''
    if pnl_pct > 10:
        flag = ' <-- CHECK'
    print(f"  {pname:30s} Eq=${eq:>12,.2f} PnL={pnl_pct:>+7.2f}% W/L={wins}/{losses} WR={wr_str} Pos={pos}{flag}")
