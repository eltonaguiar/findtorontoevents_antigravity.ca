import json
import glob
import os

all_active_files = glob.glob('E:/findtorontoevents_antigravity.ca/**/active_picks*.json', recursive=True)
all_active_files += glob.glob('E:/findtorontoevents_antigravity.ca/**/cross_aggregation/data/consensus_outcomes.json', recursive=True)
all_active_files += glob.glob('E:/findtorontoevents_antigravity.ca/**/live_picks*.json', recursive=True)

crypto_winners = []

for file in all_active_files:
    try:
        with open(file, 'r') as f:
            data = json.load(f)
            # data could be list or dict
            picks = []
            if isinstance(data, list):
                picks = data
            elif isinstance(data, dict):
                # Check for common structures
                if 'picks' in data:
                    picks = data['picks']
                elif 'consensus_picks' in data:
                    picks = data['consensus_picks']
                elif 'active_picks' in data:
                    picks = data['active_picks']
                else:
                    picks = [v for k, v in data.items() if isinstance(v, dict) and 'symbol' in v]
            
            for pick in picks:
                status = pick.get('status', '').upper()
                symbol = pick.get('symbol', '').upper()
                
                # We want OPEN/ACTIVE crypto picks
                if status in ('OPEN', 'ACTIVE', 'PENDING') or not status:
                    if 'USDT' in symbol or 'BTC' in symbol or 'ETH' in symbol:
                        pnl = float(pick.get('pnl_pct', pick.get('unrealized_pnl_pct', 0.0)))
                        # only care about picks that are winning right now
                        if pnl > 0.5:
                            pick['source_file'] = os.path.relpath(file, 'E:/findtorontoevents_antigravity.ca')
                            crypto_winners.append(pick)
    except Exception as e:
        continue

# Sort by PnL
crypto_winners.sort(key=lambda x: float(x.get('pnl_pct', x.get('unrealized_pnl_pct', 0.0))), reverse=True)

with open('E:/findtorontoevents_antigravity.ca/temp_active_winners.txt', 'w') as f:
    f.write(f"Total hidden winners found (PnL > 0.5%): {len(crypto_winners)}\n\n")
    for pick in crypto_winners[:30]:
        pnl = pick.get('pnl_pct', pick.get('unrealized_pnl_pct', 0.0))
        f.write(f"Symbol: {pick.get('symbol')} | Direction: {pick.get('direction', 'LONG')} | PnL: {pnl}% | Strategy: {pick.get('strategy', pick.get('system', 'Unknown'))}\n")
        f.write(f"Source: {pick.get('source_file')}\n")
        f.write(f"Entry: {pick.get('entry_price')} | TP: {pick.get('take_profit')} | SL: {pick.get('stop_loss')}\n")
        f.write(f"Date: {pick.get('timestamp', pick.get('signal_date', 'Unknown'))}\n")
        f.write("-" * 40 + "\n")

print(f"Done. Found {len(crypto_winners)} winners.")
