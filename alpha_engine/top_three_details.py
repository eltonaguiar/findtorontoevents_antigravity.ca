from database import SQLiteStore
store = SQLiteStore()
targets = ['TON11419-USD','COIN','BNB-USD']
for sym in targets:
    picks = [p for p in store.get_open_picks() if p['symbol']==sym]
    if picks:
        p = picks[0]
        print(f"{p['strategy']} {p['symbol']} {p.get('category')} {p.get('signal_type')} entry:{p['entry_price']} tp:{p.get('take_profit')} sl:{p.get('stop_loss')} conf:{p.get('confidence')}" )
    else:
        print(f"No open pick for {sym}")
