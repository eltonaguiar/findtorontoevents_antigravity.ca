"""Master Social Media Farming Aggregator

Runs all scrapers to collect predictions from:
SOCIAL MEDIA:
- Reddit (25+ subreddits)
- Twitter/X (top analysts)
- 4chan /biz/
- StockTwits
- YouTube (via RSS)

TRADING PLATFORMS:
- TradingView
- CoinCodex
- CoinMarketCap (trending + sentiment)

PREDICTION MARKETS:
- Polymarket (with outcome validation)

COMMUNITIES:
- BitcoinTalk
- CryptoCompare

ANALYSTS:
- 20+ tracked analysts

Usage:
    python master_farmer.py [--source SOURCE] [--validate]

Options:
    --source    Run specific scraper only
    --validate  Run price validation after scraping
"""
import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from db import get_db, export_leaderboard_json

# Import all scrapers
from scrapers.tradingview_scraper import scrape_tradingview
from scrapers.reddit_scraper import scrape_reddit
from scrapers.twitter_scraper import scrape_twitter
from scrapers.polymarket_scraper import scrape_polymarket
from scrapers.coincodex_scraper import scrape_coincodex
from scrapers.fourchan_scraper import scrape_4chan_biz
from scrapers.stocktwits_scraper import scrape_stocktwits
from scrapers.analyst_scraper import run as run_analyst_scraper
from scrapers.coinmarketcap_scraper import scrape_coinmarketcap
from scrapers.crypto_community_scraper import scrape_crypto_communities
from scrapers.youtube_scraper import scrape_youtube_crypto

SCRAPER_REGISTRY = {
    # Social Media
    "reddit": ("Reddit (25+ subreddits)", scrape_reddit),
    "twitter": ("Twitter/X Analysts", scrape_twitter),
    "4chan": ("4chan /biz/", scrape_4chan_biz),
    "stocktwits": ("StockTwits", scrape_stocktwits),
    "youtube": ("YouTube", scrape_youtube_crypto),
    
    # Trading Platforms
    "tradingview": ("TradingView Ideas", scrape_tradingview),
    "coincodex": ("CoinCodex Analysis", scrape_coincodex),
    "coinmarketcap": ("CoinMarketCap", scrape_coinmarketcap),
    
    # Prediction Markets
    "polymarket": ("Polymarket Predictions", scrape_polymarket),
    
    # Communities
    "communities": ("Crypto Communities", scrape_crypto_communities),
    
    # Analysts
    "analyst": ("Analyst Registry", run_analyst_scraper),
}


def run_all_scrapers() -> dict:
    """Run all scrapers and return results."""
    results = {}
    total_predictions = 0
    
    print("\n" + "=" * 70)
    print(" MASTER SOCIAL MEDIA FARMING AGGREGATOR")
    print("=" * 70)
    print(f" Started: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)
    
    for source, (name, scraper_func) in SCRAPER_REGISTRY.items():
        print(f"\n{'─' * 70}")
        print(f" Source: {name}")
        print(f"{'─' * 70}")
        
        try:
            count = scraper_func()
            results[source] = {"status": "success", "count": count}
            total_predictions += count
            print(f" Result: {count} predictions extracted")
        except Exception as e:
            results[source] = {"status": "error", "error": str(e)}
            print(f" Error: {e}")
    
    print("\n" + "=" * 70)
    print(" FARMING COMPLETE")
    print("=" * 70)
    print(f" Total predictions extracted: {total_predictions}")
    print(f" Sources successful: {sum(1 for r in results.values() if r['status'] == 'success')}/{len(SCRAPER_REGISTRY)}")
    print(f" Finished: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)
    
    return results


def run_single_scraper(source: str) -> dict:
    """Run a single scraper."""
    if source not in SCRAPER_REGISTRY:
        print(f"Unknown source: {source}")
        print(f"Available: {', '.join(SCRAPER_REGISTRY.keys())}")
        return {}
    
    name, scraper_func = SCRAPER_REGISTRY[source]
    print(f"\n{'=' * 70}")
    print(f" Running: {name}")
    print(f"{'=' * 70}")
    
    try:
        count = scraper_func()
        print(f"\n Extracted: {count} predictions")
        return {source: {"status": "success", "count": count}}
    except Exception as e:
        print(f"\n Error: {e}")
        return {source: {"status": "error", "error": str(e)}}


def export_results():
    """Export leaderboard and active predictions to JSON."""
    print("\n" + "=" * 70)
    print(" Exporting results...")
    print("=" * 70)
    
    conn = get_db()
    
    # Export main leaderboard
    leaderboard_path = Path(__file__).parent / "data" / "leaderboard.json"
    export_leaderboard_json(conn, leaderboard_path)
    print(f" Leaderboard exported: {leaderboard_path}")
    
    # Get stats
    cursor = conn.execute("SELECT COUNT(*) as total FROM predictions")
    total = cursor.fetchone()["total"]
    
    cursor = conn.execute("SELECT COUNT(*) as active FROM predictions WHERE status = 'ACTIVE'")
    active = cursor.fetchone()["active"]
    
    cursor = conn.execute("SELECT COUNT(DISTINCT predictor_id) as predictors FROM predictors")
    predictors = cursor.fetchone()["predictors"]
    
    conn.close()
    
    print(f"\n Database stats:")
    print(f"  - Total predictions: {total}")
    print(f"  - Active predictions: {active}")
    print(f"  - Unique predictors: {predictors}")
    
    return {"total": total, "active": active, "predictors": predictors}


def main():
    parser = argparse.ArgumentParser(
        description="Master Social Media Farming Aggregator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python master_farmer.py              # Run all scrapers
  python master_farmer.py --source reddit    # Run Reddit only
  python master_farmer.py --validate   # Run all + price validation
        """
    )
    parser.add_argument("--source", help="Run specific scraper only")
    parser.add_argument("--validate", action="store_true", help="Run price validation after")
    parser.add_argument("--export-only", action="store_true", help="Just export current data")
    
    args = parser.parse_args()
    
    if args.export_only:
        export_results()
        return
    
    # Run scrapers
    if args.source:
        results = run_single_scraper(args.source)
    else:
        results = run_all_scrapers()
    
    # Export results
    stats = export_results()
    
    # Run validation if requested
    if args.validate:
        print("\n" + "=" * 70)
        print(" Running price validation...")
        print("=" * 70)
        try:
            from validation.price_validator import validate_all
            validation_results = validate_all()
            print(f" Validation: {validation_results}")
            
            # Re-export after validation
            export_results()
        except Exception as e:
            print(f" Validation error: {e}")
    
    print("\n" + "=" * 70)
    print(" Done!")
    print("=" * 70)


if __name__ == "__main__":
    main()
