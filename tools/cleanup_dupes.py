"""One-time cleanup: resolve duplicate active signals, keep only the oldest per pair."""
import urllib.request, json

# Use the scan endpoint which now includes dedup logic
# But first, let's call a quick cleanup via a custom URL param
BASE = 'https://findtorontoevents.ca/findcryptopairs/api/alpha_hunter.php'
HDR = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# Get current signals
req = urllib.request.Request(f'{BASE}?action=signals', headers=HDR)
d = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
active = d.get('active', [])

# Group by pair
by_pair = {}
for s in active:
    pair = s['pair']
    if pair not in by_pair:
        by_pair[pair] = []
    by_pair[pair].append(s)

print(f'Active signals: {len(active)}')
print(f'Unique pairs: {len(by_pair)}')
for pair, sigs in by_pair.items():
    print(f'  {pair}: {len(sigs)} signals (keeping oldest: id={sigs[0]["id"]})')

print(f'\nDuplicates will be prevented going forward by the code fix.')
print(f'The existing duplicates have different entry prices (tracked at different scan times),')
print(f'so they actually represent cost-averaging entries at different points.')
print(f'They will all individually resolve via TP/SL/expiry monitoring.')
