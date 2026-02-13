#!/usr/bin/env python3
"""Quick test: fetch kraken_ranked endpoint and print top 10."""
import urllib.request
import json

import sys
action = sys.argv[1] if len(sys.argv) > 1 else "kraken_ranked"
url = f"https://findtorontoevents.ca/findcryptopairs/api/meme_market_pulse.php?action={action}&force=1"
try:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"})
    r = urllib.request.urlopen(req, timeout=30)
    d = json.loads(r.read())
    print(f"ok: {d.get('ok')}")
    print(f"total_coins: {d.get('total_coins')}")
    mood = d.get('mood', {})
    print(f"mood: {mood.get('mood', 'N/A')}")
    print(f"latency: {d.get('latency_ms')}ms")
    print(f"cached: {d.get('cached')}")
    print()

    rankings = d.get('rankings', [])
    if rankings:
        print(f"{'#':>3} {'Symbol':8} {'Rating':>6}  {'Signal':14} {'Price':>12}  {'24h':>7}  {'Volume':>10}")
        print("-" * 75)
        for c in rankings[:15]:
            print(f"{c['rank']:3} {c['symbol']:8} {c['rating_10']:>3}/10  {c['rating_label']:14} ${c['price']:<11.6f} {c['chg_24h']:>+6.1f}%  ${c['vol_24h_usd']:>10,.0f}")
    else:
        print("No rankings returned")
        if 'error' in d:
            print(f"Error: {d['error']}")

    # Show model info
    model = d.get('model', {})
    if model:
        print(f"\nModel: {model.get('name')} v{model.get('version')} ({model.get('scale')} scale)")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
