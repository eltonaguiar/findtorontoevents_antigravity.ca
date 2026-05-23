import json
from database import SQLiteStore
store = SQLiteStore()
picks = store.get_open_picks()
crypto = [p for p in picks if p.get('category') == 'crypto' or p['symbol'].endswith('USDT')]
for p in crypto:
    print(p['symbol'], p.get('category'), p.get('confidence'))
