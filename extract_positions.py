import json
from datetime import datetime
import pytz

def parse_time(entry_time, est):
    time_str = "Unknown"
    if entry_time:
        try:
            if isinstance(entry_time, str):
                if entry_time.endswith('Z'):
                    dt = datetime.strptime(entry_time, "%Y-%m-%dT%H:%M:%S.%fZ")
                else:
                    dt = datetime.fromisoformat(entry_time)
                
                if dt.tzinfo is None:
                    dt = pytz.utc.localize(dt)
                    
                dt_est = dt.astimezone(est)
                time_str = dt_est.strftime("%Y-%m-%d %H:%M:%S EST")
        except Exception:
            time_str = str(entry_time)
    return time_str

try:
    with open('e:/findtorontoevents_antigravity.ca/audit_dashboard/data/claudes_test_state.json', 'r') as f:
        state = json.load(f)

    print("### Current Open Positions (EST) - March 2026")
    
    positions_found = False
    est = pytz.timezone('US/Eastern')
    
    # Track by asset class
    ac_dict = {}
    
    # We will categorize them basically by portfolio name or just list them all
    for pid, port in state.items():
        if 'positions' in port and len(port['positions']) > 0:
            for trade in port['positions']:
                sym = trade.get('symbol', 'UNKNOWN')
                direction = trade.get('direction', 'LONG')
                entry_time = trade.get('opened_at', trade.get('time', None))
                asset_class = trade.get('asset_class', 'UNKNOWN')
                port_name = port.get('name', 'Unknown Portfolio')
                
                time_str = parse_time(entry_time, est)
                
                if asset_class not in ac_dict:
                    ac_dict[asset_class] = []
                    
                ac_dict[asset_class].append(f"- **{sym}** ({direction}) in *{port_name}* | Entry: {time_str}")
                positions_found = True

    if not positions_found:
        print("- No open positions currently found in claudes_test_state.")
    else:
        for ac, trades in ac_dict.items():
            print(f"\n#### {ac.upper()}")
            for t in trades:
                print(t)

except Exception as e:
    print(f"Error: {e}")
