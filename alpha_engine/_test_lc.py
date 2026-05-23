"""Test EVERY known LunarCrush API endpoint pattern."""
import urllib.request
import json

KEY = "x9x54kkyb9nnw78ew3xdmqsriemmsi39gikcu07uh"

endpoints = [
    # v4 documented endpoints from GitHub
    ("v4 coins list", "https://lunarcrush.com/api4/public/coins/list/v1", True),
    ("v4 coin BTC", "https://lunarcrush.com/api4/public/coins/1/v1", True),  # BTC = id 1
    ("v4 coin btc lowercase", "https://lunarcrush.com/api4/public/coins/btc/v1", True),
    ("v4 coin BTC upper", "https://lunarcrush.com/api4/public/coins/BTC/v1", True),
    ("v4 coins galaxy", "https://lunarcrush.com/api4/public/coins/galaxy-score/v1", True),
    # Try with config= param
    ("v4 config", f"https://lunarcrush.com/api4/public/coins/BTC/v1?key={KEY}", False),
    # Older patterns
    ("v3 assets", f"https://lunarcrush.com/api3/coins?key={KEY}", False),
    ("v3 coin", f"https://lunarcrush.com/api3/coins/1?key={KEY}", False),
    # API v2 legacy
    ("v2 assets", f"https://lunarcrush.com/api/v2?data=assets&key={KEY}&symbol=BTC", False),
    # Direct coin page API
    ("coin page", "https://lunarcrush.com/api4/public/coins/bitcoin/overview/v1", True),
]

for name, url, use_bearer in endpoints:
    try:
        headers = {"User-Agent": "AlphaEngine/1.0", "Accept": "application/json"}
        if use_bearer:
            headers["Authorization"] = f"Bearer {KEY}"
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=10)
        raw = resp.read()
        data = json.loads(raw)
        text = str(data)[:300]
        print(f"  OK  {name}: {text}")
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode()[:100]
        except:
            pass
        print(f"  ERR {name}: HTTP {e.code} {e.reason} | {body}")
    except Exception as e:
        print(f"  ERR {name}: {e}")
