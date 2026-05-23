import json
from database import SQLiteStore
store = SQLiteStore()
open_picks = store.get_open_picks()
crypto = [p for p in open_picks if p.get('category') == 'crypto' or p['symbol'].endswith('USDT')]
crypto.sort(key=lambda p: p.get('confidence', 0), reverse=True)
top = crypto[:3]
for p in top:
    print(f"{p['strategy']} {p['symbol']} ({p.get('category')}) conf={p.get('confidence',0):.2f} entry={p['entry_price']} tp={p.get('take_profit')} sl={p.get('stop_loss')}")
