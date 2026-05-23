import json
import glob
import os

target_systems = [
    'battleground/data/active_picks.json',
    'claude_gainer_ml/tracker/claude_live_picks.json',
    'alpha_engine/data/active_picks.json',
    'ml_battleground/system_f_clawsofdoom/data/active_picks.json',
    'mercury2/data/active_picks.json',
    'alpha_engine/data/active_picks_fast.json' # Assuming this is alpha engine fast
]

crypto_winners = []

for file_path in target_systems:
    full_path = os.path.join('E:/findtorontoevents_antigravity.ca', file_path)
    if not os.path.exists(full_path):
        continue
        
    try:
        with open(full_path, 'r') as f:
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
                    if 'USDT' in symbol or 'BTC' in symbol or 'ETH' in symbol or 'SOL' in symbol or 'XRP' in symbol:
                        pnl = float(pick.get('pnl_pct', pick.get('unrealized_pnl_pct', 0.0)))
                        pick['source_file'] = file_path
                        crypto_winners.append(pick)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")

# Sort by PnL
crypto_winners.sort(key=lambda x: float(x.get('pnl_pct', x.get('unrealized_pnl_pct', 0.0))), reverse=True)

with open('E:/findtorontoevents_antigravity.ca/temp_top_tier_picks.txt', 'w') as f:
    f.write(f"Top Tier Systems Active Crypto Picks\n\n")
    for pick in crypto_winners[:20]:
        pnl = pick.get('pnl_pct', pick.get('unrealized_pnl_pct', 0.0))
        # Format PnL as percentage
        if pnl < 1.0 and pnl > -1.0 and str(pnl).count('0') > 1: # rough check if it's decimal representing percent
            pnl_display = round(pnl * 100, 2) if pick.get('unrealized_pnl_pct') is not None else pnl
        else:
            pnl_display = pnl
        
        f.write(f"Symbol: {pick.get('symbol')} | Direction: {pick.get('direction', 'LONG')} | PnL: {pnl_display}% | Strategy: {pick.get('strategy', pick.get('system', 'Unknown'))}\n")
        f.write(f"Source: {pick.get('source_file')}\n")
        f.write("-" * 40 + "\n")

print(f"Done gathering top tier picks.")
