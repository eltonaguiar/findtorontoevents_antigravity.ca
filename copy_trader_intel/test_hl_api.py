import requests, json

# Test HL API with known whale address
print("=== Test 1: clearinghouseState ===")
r = requests.post('https://api.hyperliquid.xyz/info', json={
    'type': 'clearinghouseState',
    'user': '0x5078C2fBeA2b2aD61bc840Bc023E35Fce56BeDb6'
}, timeout=10)
print(f"Status: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    if isinstance(d, dict):
        print(f"Keys: {list(d.keys())}")
        ms = d.get('marginSummary', {})
        print(f"Account value: {ms.get('accountValue', 'N/A')}")
        positions = d.get('assetPositions', [])
        print(f"Open positions: {len(positions)}")
        for p in positions[:3]:
            pos = p.get('position', p)
            print(f"  {pos.get('coin')}: size={pos.get('szi')}, entry={pos.get('entryPx')}, upnl={pos.get('unrealizedPnl')}")

print("\n=== Test 2: userFills ===")
r2 = requests.post('https://api.hyperliquid.xyz/info', json={
    'type': 'userFills',
    'user': '0x5078C2fBeA2b2aD61bc840Bc023E35Fce56BeDb6'
}, timeout=10)
print(f"Status: {r2.status_code}")
if r2.status_code == 200:
    fills = r2.json()
    if isinstance(fills, list):
        print(f"Fills count: {len(fills)}")
        if fills:
            print(f"First fill keys: {list(fills[0].keys())}")
            for f in fills[:3]:
                print(f"  {f.get('coin')} {f.get('side')} {f.get('sz')} @ {f.get('px')} | closedPnl={f.get('closedPnl')} | time={f.get('time')}")

print("\n=== Test 3: metaAndAssetCtxs ===")
r3 = requests.post('https://api.hyperliquid.xyz/info', json={'type': 'metaAndAssetCtxs'}, timeout=10)
print(f"Status: {r3.status_code}")
if r3.status_code == 200:
    d3 = r3.json()
    if isinstance(d3, list) and len(d3) >= 1:
        meta = d3[0]
        if isinstance(meta, dict) and 'universe' in meta:
            print(f"Universe coins: {len(meta['universe'])}")
