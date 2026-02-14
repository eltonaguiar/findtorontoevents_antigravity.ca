"""Find the most volatile crypto pairs on Kraken by 24h range."""
import urllib.request
import json

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# All interesting Kraken USD pairs - memes + altcoins + majors
PAIRS = (
    "PEPEUSD,XDGUSD,SHIBUSD,BONKUSD,WIFUSD,FLOKIUSD,PENGUUSD,TRUMPUSD,"
    "FARTCOINUSD,SPXUSD,PONKEUSD,POPCATUSD,MOODENGUSD,GIGAUSD,VIRTUALUSD,"
    "TURBOUSD,MOGUSD,DOGUSD,PNUTUSD,NEIROUSD,COQUSD,FWOGUSD,DEGENUSD,"
    "AZTECUSD,ESPUSD,MEUSD,TOSHIUSD,LRCUSD,CAMPUSD,SOSOUSD"
)

PAIRS2 = (
    "SOLUSD,XBTUSD,ETHUSD,AVAXUSD,LINKUSD,DOTUSD,ADAUSD,ATOMUSD,NEARUSD,"
    "FETUSD,INJUSD,SUIUSD,APTUSD,OPUSD,ARBUSD,AAVEUSD,CRVUSD,LDOUSD,"
    "DYDXUSD,BLURUSD,IMXUSD,AXSUSD,MANAUSD,SANDUSD,GALAUSD,GRTUSD,"
    "FTMUSD,KSMUSD,FLOWUSD,MINAUSD,SUSHIUSD,YFIUSD,BALUSD,ZRXUSD,"
    "UNIUSD,XRPUSD,LTCUSD,BCHUSD,ETCUSD,ZECUSD,XLMUSD,TRXUSD,EOSUSD,"
    "DASHUSD,XMRUSD,SNXUSD,COMPUSD,MKRUSD,LPTUSD"
)

def fetch_tickers(pair_list):
    url = 'https://api.kraken.com/0/public/Ticker?pair=' + pair_list
    req = urllib.request.Request(url, headers=HEADERS)
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read())
    return data.get('result', {})

def main():
    print("Fetching Kraken tickers (batch 1 - memes + small caps)...")
    t1 = fetch_tickers(PAIRS)
    print("Fetching Kraken tickers (batch 2 - altcoins + majors)...")
    t2 = fetch_tickers(PAIRS2)
    
    all_tickers = {}
    all_tickers.update(t1)
    all_tickers.update(t2)
    
    pairs = []
    for pair_key, t in all_tickers.items():
        price = float(t['c'][0])
        high = float(t['h'][1])  # 24h high
        low = float(t['l'][1])   # 24h low
        vol_coins = float(t['v'][1])  # 24h volume
        vol_usd = vol_coins * price
        open_price = float(t['o'])
        chg_pct = ((price - open_price) / open_price * 100) if open_price > 0 else 0
        
        if low > 0:
            range_pct = ((high - low) / low) * 100
        else:
            range_pct = 0
        
        # Spread
        ask = float(t['a'][0])
        bid = float(t['b'][0])
        spread = ((ask - bid) / ask * 100) if ask > 0 else 0
        
        pairs.append({
            'pair': pair_key,
            'price': price,
            'high': high,
            'low': low,
            'range_pct': round(range_pct, 2),
            'chg_pct': round(chg_pct, 2),
            'vol_usd': round(vol_usd),
            'spread_pct': round(spread, 3),
            'trades': int(t['t'][1])  # 24h trade count
        })
    
    # Sort by volatility
    pairs.sort(key=lambda x: x['range_pct'], reverse=True)
    
    print()
    print("=" * 100)
    print("TOP 40 MOST VOLATILE KRAKEN USD PAIRS (sorted by 24h range)")
    print("=" * 100)
    print(f"{'#':>3} {'PAIR':20} {'RANGE%':>8} {'CHG%':>8} {'PRICE':>14} {'VOL(USD)':>16} {'SPREAD%':>8} {'TRADES':>8}")
    print("-" * 100)
    
    for i, p in enumerate(pairs[:40]):
        print(f"{i+1:3d} {p['pair']:20s} {p['range_pct']:7.2f}% {p['chg_pct']:+7.2f}% {p['price']:<14} ${p['vol_usd']:>14,} {p['spread_pct']:7.3f}% {p['trades']:>7,}")
    
    print()
    print(f"Total pairs: {len(pairs)}")
    
    # Filter for backtest candidates: high volatility + decent volume + decent trades
    print()
    print("=" * 100)
    print("BACKTEST CANDIDATES (range > 5%, vol > $50K, trades > 100)")
    print("=" * 100)
    candidates = [p for p in pairs if p['range_pct'] > 5 and p['vol_usd'] > 50000 and p['trades'] > 100]
    for i, p in enumerate(candidates):
        print(f"{i+1:3d} {p['pair']:20s} range={p['range_pct']:6.2f}% vol=${p['vol_usd']:>12,} trades={p['trades']:>6,}")
    
    print(f"\n{len(candidates)} pairs qualify for backtesting")
    
    # Output as JSON for later use
    with open('tools/volatile_pairs.json', 'w') as f:
        json.dump(candidates, f, indent=2)
    print("Saved to tools/volatile_pairs.json")

if __name__ == '__main__':
    main()
