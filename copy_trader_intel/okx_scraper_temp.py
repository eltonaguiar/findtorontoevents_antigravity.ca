import json
import time
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

# Windows UTF-8 fix
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

BASE = "https://www.okx.com/api/v5/copytrading"

def fetch_json(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json"
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
            else:
                print(f"  FAILED {url}: {e}")
                return None

def get_all_traders():
    all_traders = {}

    # Page 1
    data = fetch_json(f"{BASE}/public-lead-traders?instType=SWAP")
    if not data or data["code"] != "0":
        print("Failed to fetch initial page")
        return {}

    total_pages = int(data["data"][0].get("totalPage", 1))
    print(f"Total pages available: {total_pages}")

    for r in data["data"][0]["ranks"]:
        all_traders[r["uniqueCode"]] = r
    print(f"Page 1: {len(data['data'][0]['ranks'])} traders (total unique: {len(all_traders)})")

    # Remaining pages
    for page in range(2, total_pages + 1):
        time.sleep(0.4)
        data = fetch_json(f"{BASE}/public-lead-traders?instType=SWAP&page={page}")
        if data and data["code"] == "0":
            ranks = data["data"][0]["ranks"]
            for r in ranks:
                all_traders[r["uniqueCode"]] = r
            print(f"Page {page}: {len(ranks)} traders (total unique: {len(all_traders)})")
        else:
            print(f"Page {page}: FAILED")

    # Also try SPOT
    data = fetch_json(f"{BASE}/public-lead-traders?instType=SPOT")
    if data and data["code"] == "0":
        spot_pages = int(data["data"][0].get("totalPage", 1))
        print(f"SPOT: {spot_pages} pages available")
        for r in data["data"][0]["ranks"]:
            if r["uniqueCode"] not in all_traders:
                r["_source"] = "SPOT"
                all_traders[r["uniqueCode"]] = r
        print(f"SPOT page 1: total now {len(all_traders)}")
        for page in range(2, min(spot_pages + 1, 15)):
            time.sleep(0.4)
            data = fetch_json(f"{BASE}/public-lead-traders?instType=SPOT&page={page}")
            if data and data["code"] == "0":
                for r in data["data"][0]["ranks"]:
                    if r["uniqueCode"] not in all_traders:
                        r["_source"] = "SPOT"
                        all_traders[r["uniqueCode"]] = r
                print(f"SPOT page {page}: total now {len(all_traders)}")

    return all_traders

def enrich_trader(unique_code):
    stats = None
    prefs = None

    data = fetch_json(f"{BASE}/public-stats?instType=SWAP&uniqueCode={unique_code}")
    if data and data["code"] == "0" and data["data"]:
        stats = data["data"][0] if isinstance(data["data"], list) else data["data"]

    time.sleep(0.15)

    data = fetch_json(f"{BASE}/public-preference-currency?instType=SWAP&uniqueCode={unique_code}")
    if data and data["code"] == "0" and data["data"]:
        prefs = data["data"]

    return stats, prefs

def main():
    print("=" * 60)
    print("OKX Copy Trading Lead Trader Database Builder")
    print("=" * 60)

    print("\n[1/3] Fetching all lead traders...")
    all_traders = get_all_traders()
    print(f"\nTotal unique traders found: {len(all_traders)}")

    print(f"\n[2/3] Enriching traders with stats & preferences...")
    enriched = []
    count = 0
    for code, trader in all_traders.items():
        count += 1
        if count % 20 == 0:
            print(f"  Progress: {count}/{len(all_traders)}")

        stats, prefs = enrich_trader(code)
        time.sleep(0.2)

        entry = {
            "uniqueCode": code,
            "nickName": trader.get("nickName", ""),
            "winRatio": trader.get("winRatio", "0"),
            "pnl": trader.get("pnl", "0"),
            "pnlRatio": trader.get("pnlRatio", "0"),
            "copyTraderNum": trader.get("copyTraderNum", "0"),
            "accCopyTraderNum": trader.get("accCopyTraderNum", "0"),
            "leadDays": trader.get("leadDays", "0"),
            "aum": trader.get("aum", "0"),
            "ccy": trader.get("ccy", "USDT"),
            "maxCopyTraderNum": trader.get("maxCopyTraderNum", "0"),
            "traderInsts": trader.get("traderInsts", []),
            "pnlRatios": trader.get("pnlRatios", []),
            "portLink": trader.get("portLink", ""),
            "instType": trader.get("_source", "SWAP"),
        }

        if stats:
            entry["stats"] = stats
        if prefs:
            entry["preferredCurrencies"] = prefs

        enriched.append(entry)

    print(f"\n[3/3] Filtering for quality...")
    quality = []
    for t in enriched:
        try:
            wr = float(t.get("winRatio", "0"))
            days = int(t.get("leadDays", "0"))
            followers = int(t.get("copyTraderNum", "0")) + int(t.get("accCopyTraderNum", "0"))
        except (ValueError, TypeError):
            wr, days, followers = 0, 0, 0

        if wr >= 0.50 and days >= 30 and followers > 0:
            t["_qualityScore"] = round(wr * 0.4 + min(days / 365, 1) * 0.3 + min(followers / 1000, 1) * 0.3, 4)
            quality.append(t)

    quality.sort(key=lambda x: x.get("_qualityScore", 0), reverse=True)

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "okx_copy_trading_api",
        "api_endpoints": {
            "lead_traders": f"{BASE}/public-lead-traders?instType=SWAP",
            "stats": f"{BASE}/public-stats?instType=SWAP&uniqueCode={{code}}",
            "preferences": f"{BASE}/public-preference-currency?instType=SWAP&uniqueCode={{code}}",
            "pagination": "page=1..N (10 per page, totalPage in response)",
        },
        "total_scraped": len(enriched),
        "quality_filtered": len(quality),
        "filter_criteria": {
            "winRate": ">= 50%",
            "leadDays": ">= 30",
            "followers": "> 0 (current + accumulated)",
        },
        "research_notes": {
            "aggregator_sites": [
                "https://www.okx.com/copy-trading/leaderboard - OKX official leaderboard",
                "https://www.coinglass.com/CopyTrading - cross-exchange copy trading aggregator",
                "https://www.copin.io - decentralized copy trading analytics",
                "https://cryptorank.io - trader ranking aggregator",
                "https://app.trdr.io - copy trading performance tracker",
            ],
            "github_scrapers": [
                "Search: okx copy trading scraper",
                "Search: okx leaderboard api",
                "Most OKX scraping projects use the same public API endpoints",
            ],
            "pagination_details": "page param (1-indexed), 10 results per page, totalPage field in response, instType=SWAP or SPOT",
            "additional_api_endpoints": [
                f"{BASE}/public-current-subpositions?instType=SWAP&uniqueCode={{code}} - open positions",
                f"{BASE}/public-history-subpositions?instType=SWAP&uniqueCode={{code}} - trade history",
            ],
        },
        "quality_traders": quality,
        "all_traders": enriched,
    }

    out_path = r"e:\findtorontoevents_antigravity.ca\copy_trader_intel\data\okx_trader_database.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\nResults:")
    print(f"  Total traders scraped: {len(enriched)}")
    print(f"  Quality filtered: {len(quality)}")
    print(f"  Saved to: {out_path}")

    print(f"\nTop 20 quality traders:")
    header = f"{'Rank':<5} {'Name':<25} {'WR%':<8} {'PnL%':<12} {'Followers':<10} {'Days':<6} {'AUM':<15} {'Score':<8}"
    print(header)
    print("-" * len(header))
    for i, t in enumerate(quality[:20], 1):
        wr = float(t.get("winRatio", 0)) * 100
        pnl = float(t.get("pnlRatio", 0)) * 100
        fol = int(t.get("accCopyTraderNum", 0))
        days = int(t.get("leadDays", 0))
        aum = float(t.get("aum", 0))
        score = t.get("_qualityScore", 0)
        name = t["nickName"][:24]
        print(f"{i:<5} {name:<25} {wr:<8.1f} {pnl:<12.1f} {fol:<10} {days:<6} {aum:<15.0f} {score:<8.4f}")

if __name__ == "__main__":
    main()
