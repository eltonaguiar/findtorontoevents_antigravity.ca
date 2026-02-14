"""Scan Kraken for the most volatile USD trading pairs."""
import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Fetch all tickers
req = urllib.request.Request("https://api.kraken.com/0/public/Ticker",
    headers={"User-Agent": "VolScanner/1.0"})
resp = urllib.request.urlopen(req, context=ctx)
data = json.loads(resp.read().decode())
tickers = data.get("result", {})

volatile = []
for pair, d in tickers.items():
    if not (pair.endswith("USD") or pair.endswith("ZUSD")):
        continue
    # Skip stablecoins and fiat
    skip = ["USDCUSD", "USDTUSD", "DAIUSD", "PAXUSD", "BUSDUSD", "TUSDUSD",
            "ZGBPZUSD", "ZEURZUSD", "ZCADZUSD", "ZJPYZUSD", "ZAUDZUSD",
            "PYUSDUSD", "FDUSD", "USDE"]
    if any(pair.startswith(s.replace("USD","")) for s in skip):
        continue
    try:
        high24 = float(d["h"][1])
        low24 = float(d["l"][1])
        price = float(d["c"][0])
        vol = float(d["v"][1])
        open24 = float(d["o"])
        if low24 <= 0 or price <= 0 or high24 <= 0:
            continue
        range_pct = ((high24 - low24) / low24) * 100
        change_pct = ((price - open24) / open24) * 100
        vol_usd = vol * price
        if vol_usd < 50000:
            continue
        volatile.append({
            "pair": pair, "price": price,
            "range_pct": round(range_pct, 2),
            "change_pct": round(change_pct, 2),
            "vol_usd": round(vol_usd),
            "high24": high24, "low24": low24
        })
    except:
        continue

volatile.sort(key=lambda x: x["range_pct"], reverse=True)

print("TOP 50 MOST VOLATILE KRAKEN USD PAIRS")
print("=" * 95)
print(f"{'#':<4}{'Pair':<16}{'Price':>12}{'24h Range%':>12}{'24h Chg%':>10}{'Vol USD':>16}")
print("-" * 95)
for i, v in enumerate(volatile[:50]):
    print(f"{i+1:<4}{v['pair']:<16}${v['price']:>11.6f}{v['range_pct']:>10.2f}%{v['change_pct']:>+9.2f}%  ${v['vol_usd']:>13,}")

print(f"\nTotal pairs scanned: {len(volatile)}")

# Save top 30 for the backtest engine
top30 = volatile[:30]
with open("findcryptopairs/volatile_pairs.json", "w") as f:
    json.dump(top30, f, indent=2)
print(f"\nSaved top 30 to findcryptopairs/volatile_pairs.json")
