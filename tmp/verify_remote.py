import urllib.request, json

url = "https://findtorontoevents.ca/riseoftheclaw/data/active_picks.json"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
r = urllib.request.urlopen(req)
d = json.loads(r.read())
picks = d.get("activePicks", [])
print(f"Remote: {len(picks)} active picks")
for p in picks:
    sym = p.get("symbol", "?")
    price = p.get("entryPrice", 0)
    reason = p.get("reason", "")
    algo = p.get("algorithmName", "")
    print(f"  {sym:10s} @ ${price:>10.2f}  {algo:30s}  {reason}")
print(f"Updated: {d.get('lastUpdated', '?')}")
