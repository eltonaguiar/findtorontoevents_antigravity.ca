#!/usr/bin/env python3
"""Test QUQ across all price sources."""
import urllib.request, json, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch(url, timeout=8):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=timeout, context=ctx)

print("=== QUQ Price Source Tests ===\n")

# 1. Crypto.com
try:
    r = fetch("https://api.crypto.com/exchange/v1/public/get-tickers?instrument_name=QUQ_USDT")
    d = json.loads(r.read().decode())
    if d.get("result", {}).get("data"):
        t = d["result"]["data"][0]
        print("Crypto.com: price=" + str(t.get("a")) + " vol=" + str(t.get("vv")))
    else:
        print("Crypto.com: No data for QUQ_USDT")
except Exception as e:
    print("Crypto.com: FAIL - " + str(e)[:100])

# 2. Binance
try:
    r = fetch("https://api.binance.com/api/v3/ticker/price?symbol=QUQUSDT")
    d = json.loads(r.read().decode())
    print("Binance: price=" + str(d.get("price")))
except Exception as e:
    print("Binance: FAIL - " + str(e)[:100])

# 3. KuCoin
try:
    r = fetch("https://api.kucoin.com/api/v1/market/stats?symbol=QUQ-USDT")
    d = json.loads(r.read().decode())
    if d.get("data", {}).get("last"):
        print("KuCoin: price=" + d["data"]["last"] + " vol=" + str(d["data"].get("volValue")))
    else:
        print("KuCoin: No data - " + str(d.get("code")) + " " + str(d.get("msg", "")))
except Exception as e:
    print("KuCoin: FAIL - " + str(e)[:100])

# 4. Gate.io
try:
    r = fetch("https://api.gateio.ws/api/v4/spot/tickers?currency_pair=QUQ_USDT")
    d = json.loads(r.read().decode())
    if isinstance(d, list) and len(d) > 0:
        print("Gate.io: price=" + str(d[0].get("last")) + " vol=" + str(d[0].get("base_volume")))
    else:
        print("Gate.io: No data")
except Exception as e:
    print("Gate.io: FAIL - " + str(e)[:100])

# 5. MEXC
try:
    r = fetch("https://api.mexc.com/api/v3/ticker/price?symbol=QUQUSDT")
    d = json.loads(r.read().decode())
    if d.get("price"):
        print("MEXC: price=" + str(d.get("price")))
    else:
        print("MEXC: No data - " + str(d))
except Exception as e:
    print("MEXC: FAIL - " + str(e)[:100])

# 6. CoinGecko search
try:
    r = fetch("https://api.coingecko.com/api/v3/search?query=QUQ")
    d = json.loads(r.read().decode())
    coins = d.get("coins", [])[:5]
    if coins:
        for c in coins:
            print("CoinGecko search: id=" + c["id"] + " symbol=" + c["symbol"] + " name=" + c["name"])
    else:
        print("CoinGecko search: No results for QUQ")
except Exception as e:
    print("CoinGecko search: FAIL - " + str(e)[:100])

# 7. DexScreener
try:
    r = fetch("https://api.dexscreener.com/latest/dex/search?q=QUQ")
    d = json.loads(r.read().decode())
    pairs = d.get("pairs", [])[:5]
    if pairs:
        for p in pairs:
            base = p["baseToken"]["symbol"]
            quote = p["quoteToken"]["symbol"]
            price = p.get("priceUsd", "?")
            dex = p["dexId"]
            chain = p["chainId"]
            liq = p.get("liquidity", {}).get("usd", 0)
            print("DexScreener: " + base + "/" + quote + " price=$" + str(price) + " dex=" + dex + " chain=" + chain + " liq=$" + str(liq))
    else:
        print("DexScreener: No pairs for QUQ")
except Exception as e:
    print("DexScreener: FAIL - " + str(e)[:100])

# 8. Kraken
try:
    r = fetch("https://api.kraken.com/0/public/Ticker?pair=QUQUSDT")
    d = json.loads(r.read().decode())
    if d.get("error") and len(d["error"]) > 0:
        print("Kraken: " + str(d["error"]))
    else:
        for k, v in d.get("result", {}).items():
            print("Kraken: " + k + " ask=" + str(v.get("a", ["?"])[0]))
except Exception as e:
    print("Kraken: FAIL - " + str(e)[:100])
