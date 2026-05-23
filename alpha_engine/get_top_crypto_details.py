from database import SQLiteStore
store = SQLiteStore()
symbols = ['TON11419-USD','COIN','BNB-USD']
for sym in symbols:
    picks = [p for p in store.get_open_picks() if p['symbol']==sym]
    if picks:
        p = picks[0]
        print(f"{p['strategy']}|{p['symbol']}|{p.get('signal_type','')}|{p['entry_price']}|{p.get('take_profit')}|{p.get('stop_loss')}|{p.get('confidence')}")
    else:
        print(f"{sym}|NO_PICK")
