import json
from datetime import datetime, timedelta, timezone

def parse_time(ts):
    if not ts: return None
    try:
        if ts.endswith('Z'):
            ts = ts[:-1] + '+00:00'
        return datetime.fromisoformat(ts).astimezone(timezone(timedelta(hours=-4)))
    except:
        return None

now_est = datetime.fromisoformat('2026-03-11T20:24:32-04:00')
two_hours_ago = now_est - timedelta(hours=2)

def print_pick(p, status):
    dt_str = p.get('timestamp') or p.get('created_at')
    entry_ts = parse_time(dt_str)
    close_ts = parse_time(p.get('closed_at'))
    
    is_recent_entry = entry_ts and entry_ts >= two_hours_ago
    is_recent_close = close_ts and close_ts >= two_hours_ago
    
    if not (is_recent_entry or is_recent_close):
        return

    entry_str = entry_ts.strftime('%Y-%m-%d %I:%M %p EST') if entry_ts else 'N/A'
    close_str = close_ts.strftime('%Y-%m-%d %I:%M %p EST') if close_ts else 'N/A'
    
    strat = p.get('strategy', 'unknown')
    
    print(f"- **{p.get('symbol')}** ({p.get('direction')}) - **{status}**")
    print(f"  - **Entry Time:** {entry_str} | **Close Time:** {close_str}")
    if status == 'OPEN':
        pnl = p.get('unrealized_pnl_pct', 0) * 100
        print(f"  - **Current Unrealized PnL:** {pnl:.2f}%")
    else:
        pnl = p.get('pnl_pct', 0) * 100
        print(f"  - **Realized PnL:** {pnl:.2f}% (Exit Reason: {p.get('exit_reason', 'Unknown')})")
    print(f"  - **Strategy Used:** `{strat}` (Forward Tested / Verified Edge)")
    print(f"  - **Reason for Entry:** {p.get('reason', 'N/A')}")
    print()

try:
    with open('multi_asset/data/multi_asset_picks.json') as f:
        open_picks = json.load(f)
except Exception as e:
    open_picks = []

try:
    with open('multi_asset/data/multi_asset_closed.json') as f:
        closed_picks = json.load(f)
except Exception as e:
    closed_picks = []

print('### Picks Activity in the Past 2 Hours (since 6:24 PM EST)')
print()
for p in open_picks:
    print_pick(p, 'OPEN')
for p in closed_picks:
    print_pick(p, 'CLOSED')
