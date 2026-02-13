#!/usr/bin/env python3
"""Discover all meme-related pairs available on Kraken."""
import urllib.request, json, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

MEME_KEYWORDS = [
    'DOGE', 'SHIB', 'PEPE', 'FLOKI', 'BONK', 'WIF', 'MEME',
    'NEIRO', 'TURBO', 'BRETT', 'MOG', 'POPCAT', 'MYRO',
    'MOODENG', 'ACT', 'SPX', 'GIGA', 'PONKE', 'FWOG', 'SLERF',
    'BOME', 'WOJAK', 'TRUMP', 'BABYDOGE', 'PENGU', 'MEW',
    'FARTCOIN', 'AI16Z', 'VIRTUAL', 'PNUT', 'GOAT',
    'COQ', 'TOSHI', 'LADYS', 'DEGEN', 'HIGHER', 'ANDY',
    'SATS', 'ORDI', 'DOG', 'PORK', 'MICHI', 'WEN',
    'CHAD', 'GRIFFAIN', 'CHILLGUY', 'NEIROCTO',
]

# Get all Kraken asset pairs
req = urllib.request.Request("https://api.kraken.com/0/public/AssetPairs", headers={"User-Agent": "Mozilla/5.0"})
resp = urllib.request.urlopen(req, timeout=15, context=ctx)
data = json.loads(resp.read().decode())

if data.get("error") and len(data["error"]) > 0:
    print("Kraken API error:", data["error"])
else:
    pairs = data.get("result", {})
    print(f"Total Kraken pairs: {len(pairs)}\n")
    
    # Find USD and USDT pairs
    usd_pairs = {}
    for pair_name, info in pairs.items():
        base = info.get("base", "")
        quote = info.get("quote", "")
        wsname = info.get("wsname", pair_name)
        altname = info.get("altname", pair_name)
        
        if quote in ("USD", "ZUSD", "USDT"):
            # Normalize base name (Kraken uses X prefix for some)
            clean_base = base.lstrip("X").lstrip("Z")
            usd_pairs[clean_base] = {
                "pair": pair_name,
                "wsname": wsname,
                "altname": altname,
                "quote": quote,
                "base": base
            }
    
    print(f"USD/USDT pairs: {len(usd_pairs)}\n")
    
    # Find meme coins
    print("=== MEME COINS ON KRAKEN ===\n")
    meme_found = []
    for keyword in MEME_KEYWORDS:
        for clean_base, info in usd_pairs.items():
            if keyword.upper() in clean_base.upper():
                meme_found.append((keyword, clean_base, info))
    
    seen = set()
    for kw, base, info in sorted(meme_found, key=lambda x: x[1]):
        if base not in seen:
            seen.add(base)
            print(f"  {base:15s} pair={info['altname']:20s} quote={info['quote']:5s} wsname={info['wsname']}")
    
    print(f"\nTotal meme coins on Kraken: {len(seen)}")
    
    # Also list ALL crypto USD pairs for reference
    print(f"\n=== ALL KRAKEN USD/USDT PAIRS ({len(usd_pairs)}) ===\n")
    for base in sorted(usd_pairs.keys()):
        info = usd_pairs[base]
        print(f"  {base:10s} {info['altname']:20s} ({info['quote']})")
