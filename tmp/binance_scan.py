"""
Binance Top Gainers/Losers Scanner
Fetches 24h ticker data, filters USDT pairs with >$1M volume,
identifies top gainers and losers, and fetches 7-day momentum for top gainers.
"""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

API_BASE = "https://api.binance.com/api/v3"
OUTPUT_PATH = "e:/findtorontoevents_antigravity.ca/genome/data/top_gainers_scan.json"


def fetch_json(url, retries=3):
    """Fetch JSON from URL with retries."""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(1)


def fetch_kline_price_7d_ago(symbol):
    """Get the close price from ~7 days ago using 1h klines."""
    try:
        # Fetch 168 bars of 1h klines (7 days)
        url = f"{API_BASE}/klines?symbol={symbol}&interval=1h&limit=168"
        data = fetch_json(url)
        if data and len(data) > 0:
            # First bar's close price = price ~7 days ago
            return float(data[0][4])  # index 4 = close price
    except Exception as e:
        print(f"  [WARN] Could not fetch 7d kline for {symbol}: {e}")
    return None


def main():
    print("=" * 80)
    print("BINANCE TOP GAINERS/LOSERS SCANNER")
    print(f"Scan time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 80)

    # Step 1: Fetch 24h ticker data
    print("\n[1/4] Fetching 24h ticker data from Binance...")
    tickers = fetch_json(f"{API_BASE}/ticker/24hr")
    print(f"  Total tickers fetched: {len(tickers)}")

    # Step 2: Filter USDT pairs with volume > $1M
    usdt_pairs = []
    for t in tickers:
        symbol = t["symbol"]
        if not symbol.endswith("USDT"):
            continue
        try:
            volume_usd = float(t["quoteVolume"])
            change_pct = float(t["priceChangePercent"])
            price = float(t["lastPrice"])
        except (ValueError, KeyError):
            continue
        if volume_usd < 1_000_000:
            continue
        usdt_pairs.append({
            "symbol": symbol,
            "price": price,
            "change_24h_pct": change_pct,
            "volume_usd": round(volume_usd, 2),
        })

    print(f"  USDT pairs with >$1M volume: {len(usdt_pairs)}")

    # Step 3: Sort by priceChangePercent descending
    usdt_pairs.sort(key=lambda x: x["change_24h_pct"], reverse=True)

    # Step 4: Top 30 gainers
    top_gainers = usdt_pairs[:30]

    # Step 5: Top 30 losers (sort ascending for biggest drops)
    top_losers = sorted(usdt_pairs, key=lambda x: x["change_24h_pct"])[:30]

    # Print gainers table
    print("\n" + "=" * 80)
    print("TOP 30 GAINERS (24h)")
    print("=" * 80)
    print(f"{'#':>3}  {'Symbol':<16} {'Price':>14} {'24h Change':>12} {'Volume (USD)':>16}")
    print("-" * 65)
    for i, g in enumerate(top_gainers, 1):
        vol_str = f"${g['volume_usd']:,.0f}"
        print(f"{i:>3}  {g['symbol']:<16} {g['price']:>14.8g} {g['change_24h_pct']:>+11.2f}% {vol_str:>16}")

    # Print losers table
    print("\n" + "=" * 80)
    print("TOP 30 LOSERS (24h) - Potential Bounce Plays")
    print("=" * 80)
    print(f"{'#':>3}  {'Symbol':<16} {'Price':>14} {'24h Change':>12} {'Volume (USD)':>16}")
    print("-" * 65)
    for i, l in enumerate(top_losers, 1):
        vol_str = f"${l['volume_usd']:,.0f}"
        print(f"{i:>3}  {l['symbol']:<16} {l['price']:>14.8g} {l['change_24h_pct']:>+11.2f}% {vol_str:>16}")

    # Step 6: Fetch 7-day momentum for top 15 gainers
    print("\n" + "=" * 80)
    print("7-DAY MOMENTUM - Top 15 Gainers")
    print("=" * 80)
    print("[2/4] Fetching 7-day klines for top 15 gainers...")

    weekly_momentum = []
    for i, g in enumerate(top_gainers[:15], 1):
        symbol = g["symbol"]
        print(f"  [{i}/15] Fetching {symbol}...", end=" ")
        price_7d_ago = fetch_kline_price_7d_ago(symbol)
        if price_7d_ago and price_7d_ago > 0:
            change_7d_pct = round(((g["price"] - price_7d_ago) / price_7d_ago) * 100, 2)
            weekly_momentum.append({
                "symbol": symbol,
                "price_now": g["price"],
                "price_7d_ago": price_7d_ago,
                "change_7d_pct": change_7d_pct,
            })
            print(f"7d: {change_7d_pct:+.2f}%")
        else:
            print("SKIP (no data)")
        # Small delay to avoid rate limiting
        if i < 15:
            time.sleep(0.15)

    # Print weekly momentum table
    print(f"\n{'#':>3}  {'Symbol':<16} {'Price Now':>14} {'Price 7d Ago':>14} {'7d Change':>12}")
    print("-" * 65)
    weekly_momentum.sort(key=lambda x: x["change_7d_pct"], reverse=True)
    for i, w in enumerate(weekly_momentum, 1):
        print(f"{i:>3}  {w['symbol']:<16} {w['price_now']:>14.8g} {w['price_7d_ago']:>14.8g} {w['change_7d_pct']:>+11.2f}%")

    # Build output JSON
    scan_result = {
        "scan_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_usdt_pairs_filtered": len(usdt_pairs),
        "min_volume_usd": 1_000_000,
        "top_gainers_24h": top_gainers,
        "top_losers_24h": top_losers,
        "weekly_momentum": weekly_momentum,
    }

    # Save to file
    print(f"\n[3/4] Saving results to {OUTPUT_PATH}...")
    with open(OUTPUT_PATH, "w") as f:
        json.dump(scan_result, f, indent=2)
    print(f"  Saved successfully.")

    # Summary
    print("\n" + "=" * 80)
    print("SCAN COMPLETE")
    print(f"  Gainers saved: {len(top_gainers)}")
    print(f"  Losers saved:  {len(top_losers)}")
    print(f"  Weekly momentum: {len(weekly_momentum)} symbols")
    if weekly_momentum:
        best_7d = max(weekly_momentum, key=lambda x: x["change_7d_pct"])
        print(f"  Best 7d performer: {best_7d['symbol']} ({best_7d['change_7d_pct']:+.2f}%)")
    print("=" * 80)


if __name__ == "__main__":
    main()
