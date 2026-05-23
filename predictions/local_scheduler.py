#!/usr/bin/env python3
"""
Local Prediction Tracker Scheduler
Run this on your local machine to bypass GitHub Actions IP blocks
Schedule with Windows Task Scheduler or cron
"""

import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from validation.price_validator import validate_all

# Import all scrapers
SCRAPERS = [
    ("polymarket", "scrapers.polymarket_scraper", "scrape_polymarket"),
    ("tradingview", "scrapers.tradingview_scraper", "scrape_tradingview"),
    ("stocktwits", "scrapers.stocktwits_scraper", "scrape_stocktwits"),
    ("coincodex", "scrapers.coincodex_scraper", "scrape_coincodex"),
    ("coinmarketcap", "scrapers.coinmarketcap_scraper", "scrape_cmc"),
    ("kalshi", "scrapers.kalshi_scraper", "scrape_kalshi"),
    ("limitless", "scrapers.limitless_scraper", "scrape_limitless"),
]


def run_scraper(name: str, module: str, func: str) -> int:
    """Run a single scraper and return count of new predictions"""
    print(f"\n[{datetime.now()}] Running {name}...")
    try:
        # Dynamic import
        mod = __import__(module, fromlist=[func])
        scraper_func = getattr(mod, func)
        
        # Run the scraper
        count = scraper_func()
        print(f"  ✓ {name}: {count} predictions")
        return count
        
    except Exception as e:
        print(f"  ✗ {name} failed: {e}")
        return 0


def run_all_scrapers():
    """Run all scrapers in sequence"""
    print("=" * 60)
    print(f"Prediction Tracker - Local Run")
    print(f"Started: {datetime.now()}")
    print("=" * 60)
    
    total = 0
    results = {}
    
    for name, module, func in SCRAPERS:
        count = run_scraper(name, module, func)
        results[name] = count
        total += count
        time.sleep(2)  # Rate limiting between scrapers
    
    # Refresh active ledger + export leaderboard
    print("\n" + "=" * 60)
    print("Refreshing active predictions + leaderboard...")
    
    try:
        summary = validate_all() or {}
        print(
            "  ✓ Refreshed active predictions "
            f"(validated={summary.get('validated', 0)}, "
            f"closed={summary.get('closed', 0)}, "
            f"active={summary.get('still_active', 0)})"
        )
    except Exception as e:
        print(f"  ✗ Refresh failed: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, count in results.items():
        status = "✓" if count > 0 else "✗"
        print(f"  {status} {name:20} | {count:3} predictions")
    print(f"\n  TOTAL: {total} predictions")
    print(f"  Finished: {datetime.now()}")
    print("=" * 60)
    
    return total


def continuous_mode(interval_minutes: int = 30):
    """Run scrapers continuously at interval"""
    print(f"Starting continuous mode (interval: {interval_minutes} minutes)")
    print("Press Ctrl+C to stop\n")
    
    while True:
        run_all_scrapers()
        
        next_run = datetime.now().timestamp() + (interval_minutes * 60)
        print(f"\nNext run at {datetime.fromtimestamp(next_run)}")
        print("-" * 60)
        
        try:
            time.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            print("\n\nStopping scheduler...")
            break


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Local Prediction Tracker")
    parser.add_argument("--continuous", "-c", action="store_true", help="Run continuously")
    parser.add_argument("--interval", "-i", type=int, default=30, help="Interval in minutes (default: 30)")
    
    args = parser.parse_args()
    
    if args.continuous:
        continuous_mode(args.interval)
    else:
        run_all_scrapers()
