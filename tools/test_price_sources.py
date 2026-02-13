#!/usr/bin/env python3
"""Test which price APIs return MOODENG and other meme coin data."""
import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch(url, timeout=8):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
    return json.loads(resp.read().decode("utf-8"))

print("=== MOODENG Price Source Tests ===\n")

# 1. Binance
try:
    data = fetch("https://api.binance.com/api/v3/ticker/price?symbol=MOODENGUSDT")
    print("Binance: OK - price=" + str(data.get("price")))
except Exception as e:
    print("Binance: FAIL - " + str(e)[:120])

# 2. CoinGecko search
try:
    data = fetch("https://api.coingecko.com/api/v3/search?query=moodeng")
    coins = data.get("coins", [])[:3]
    for c in coins:
        print("CoinGecko search: id=" + c["id"] + " symbol=" + c["symbol"] + " name=" + c["name"])
except Exception as e:
    print("CoinGecko search: FAIL - " + str(e)[:120])

# 3. CoinGecko direct price (using discovered id)
try:
    data = fetch("https://api.coingecko.com/api/v3/simple/price?ids=moodeng&vs_currencies=usd&include_24hr_vol=true&include_24hr_change=true")
    print("CoinGecko price (id=moodeng): " + json.dumps(data))
except Exception as e:
    print("CoinGecko price: FAIL - " + str(e)[:120])

# 4. KuCoin
try:
    data = fetch("https://api.kucoin.com/api/v1/market/orderbook/level1?symbol=MOODENG-USDT")
    print("KuCoin: " + json.dumps(data)[:300])
except Exception as e:
    print("KuCoin: FAIL - " + str(e)[:120])

# 5. DexScreener
try:
    data = fetch("https://api.dexscreener.com/latest/dex/search?q=MOODENG")
    pairs = data.get("pairs", [])[:3]
    for p in pairs:
        base = p["baseToken"]["symbol"]
        quote = p["quoteToken"]["symbol"]
        price = p.get("priceUsd", "?")
        dex = p["dexId"]
        chain = p["chainId"]
        print("DexScreener: " + base + "/" + quote + " price=$" + str(price) + " dex=" + dex + " chain=" + chain)
except Exception as e:
    print("DexScreener: FAIL - " + str(e)[:120])

# 6. Kraken
try:
    data = fetch("https://api.kraken.com/0/public/Ticker?pair=MOODENGUSDT")
    if data.get("error") and len(data["error"]) > 0:
        print("Kraken: " + str(data["error"]))
    else:
        result = data.get("result", {})
        for k, v in result.items():
            print("Kraken: " + k + " ask=" + str(v.get("a", ["?"])[0]) + " bid=" + str(v.get("b", ["?"])[0]))
except Exception as e:
    print("Kraken: FAIL - " + str(e)[:120])

# 7. MEXC
try:
    data = fetch("https://api.mexc.com/api/v3/ticker/price?symbol=MOODENGUSDT")
    print("MEXC: OK - price=" + str(data.get("price")))
except Exception as e:
    print("MEXC: FAIL - " + str(e)[:120])

# 8. Gate.io
try:
    data = fetch("https://api.gateio.ws/api/v4/spot/tickers?currency_pair=MOODENG_USDT")
    if isinstance(data, list) and len(data) > 0:
        print("Gate.io: OK - last=" + str(data[0].get("last")) + " vol=" + str(data[0].get("base_volume")))
    else:
        print("Gate.io: empty response")
except Exception as e:
    print("Gate.io: FAIL - " + str(e)[:120])
