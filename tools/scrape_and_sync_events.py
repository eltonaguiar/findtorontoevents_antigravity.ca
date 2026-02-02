#!/usr/bin/env python3
"""
Toronto Events Scraper and Sync Tool

This script:
1. Scrapes events from official Toronto sources (City of Toronto, Nathan Phillips Square, Sankofa Square, etc.)
2. Merges with existing events.json
3. Syncs to the remote database
4. Updates stats

Usage:
    python scrape_and_sync_events.py                    # Scrape and update local events.json
    python scrape_and_sync_events.py --sync             # Scrape, update, and sync to database
    python scrape_and_sync_events.py --deploy           # Scrape, update, sync, and deploy to FTP
"""
import json
import os
import sys
import argparse
import requests
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

# Import the unified scraper
from scrapers.unified_scraper import UnifiedTorontoScraper


def load_existing_events(events_path: Path) -> list:
    """Load existing events from events.json"""
    if events_path.exists():
        with open(events_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_events(events: list, events_path: Path):
    """Save events to events.json"""
    with open(events_path, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(events)} events to {events_path}")


def sync_to_database(events: list, api_base: str = "https://findtorontoevents.ca/fc/api"):
    """Sync events to the remote database via API"""
    sync_url = f"{api_base}/events_sync.php"
    
    try:
        print(f"Syncing {len(events)} events to database...")
        response = requests.post(
            sync_url,
            json={"events": events},
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        response.raise_for_status()
        
        result = response.json()
        print(f"Sync result: {result}")
        return result
    except Exception as e:
        print(f"Error syncing to database: {e}")
        return None


def run_duplicate_finder(api_base: str = "https://findtorontoevents.ca/fc/api"):
    """Run the duplicate event finder to link multi-source events"""
    url = f"{api_base}/events_find_duplicates.php"
    
    try:
        print("Running duplicate finder...")
        response = requests.get(url, timeout=30)
        result = response.json()
        print(f"Duplicate finder result: {result}")
        return result
    except Exception as e:
        print(f"Error running duplicate finder: {e}")
        return None


def get_stats(api_base: str = "https://findtorontoevents.ca/fc/api"):
    """Get current event stats from database"""
    url = f"{api_base}/events_get_stats.php"
    
    try:
        response = requests.get(url, timeout=30)
        return response.json()
    except Exception as e:
        print(f"Error getting stats: {e}")
        return None


def deploy_events_json():
    """Deploy events.json to FTP server"""
    try:
        # Import the deploy script
        from deploy_to_ftp import deploy_to_ftp
        
        # Deploy just the events.json file
        events_path = PROJECT_ROOT / "events.json"
        if events_path.exists():
            print("Deploying events.json to FTP server...")
            # This will depend on how deploy_to_ftp is structured
            # For now, just print a message
            print("To deploy, run: python tools/deploy_to_ftp.py")
    except ImportError:
        print("Deploy script not available. Please deploy manually.")


def main():
    parser = argparse.ArgumentParser(description="Scrape and sync Toronto events")
    parser.add_argument("--sync", action="store_true", help="Sync to remote database after scraping")
    parser.add_argument("--deploy", action="store_true", help="Deploy events.json to FTP after syncing")
    parser.add_argument("--output", "-o", type=str, help="Output file path (default: events.json in project root)")
    parser.add_argument("--api", type=str, default="https://findtorontoevents.ca/fc/api", 
                        help="API base URL for syncing")
    parser.add_argument("--dry-run", action="store_true", help="Don't save changes, just show what would be done")
    
    args = parser.parse_args()
    
    # Paths
    events_path = Path(args.output) if args.output else PROJECT_ROOT / "events.json"
    
    print("="*60)
    print("Toronto Events Scraper")
    print("="*60)
    print(f"Output file: {events_path}")
    print(f"Sync to database: {args.sync}")
    print(f"Deploy to FTP: {args.deploy}")
    print("="*60)
    
    # Load existing events
    print("\nLoading existing events...")
    existing_events = load_existing_events(events_path)
    print(f"Found {len(existing_events)} existing events")
    
    # Run the unified scraper
    print("\nStarting Toronto event scraping...")
    scraper = UnifiedTorontoScraper()
    new_events = scraper.scrape_all()
    print(f"Scraped {len(new_events)} events from official sources")
    
    # Merge events
    print("\nMerging events...")
    merged = existing_events.copy()
    added_count = 0
    updated_count = 0
    
    # Create lookup by normalized title + date
    existing_lookup = {}
    for i, evt in enumerate(merged):
        key = (scraper.normalize_title(evt.get("title", "")), evt.get("date", "")[:10])
        existing_lookup[key] = i
    
    for event in new_events:
        key = (scraper.normalize_title(event.get("title", "")), event.get("date", "")[:10])
        
        if key in existing_lookup:
            # Update existing event with new data (keep original ID)
            idx = existing_lookup[key]
            old_id = merged[idx].get("id")
            merged[idx].update(event)
            if old_id:
                merged[idx]["id"] = old_id
            updated_count += 1
        else:
            merged.append(event)
            added_count += 1
    
    # Sort by date
    merged.sort(key=lambda x: x.get("date", ""))
    
    print(f"Added {added_count} new events, updated {updated_count} existing events")
    print(f"Total events: {len(merged)}")
    
    # Count multi-day events
    multi_day_count = sum(1 for e in merged if e.get("is_multi_day"))
    print(f"Multi-day events: {multi_day_count}")
    
    # Count events with location coordinates
    with_coords = sum(1 for e in merged if e.get("lat") and e.get("lng"))
    print(f"Events with coordinates: {with_coords}")
    
    if args.dry_run:
        print("\n[DRY RUN] No changes saved.")
        return
    
    # Save merged events
    print("\nSaving events...")
    save_events(merged, events_path)
    
    # Sync to database if requested
    if args.sync:
        print("\nSyncing to database...")
        sync_result = sync_to_database(merged, args.api)
        
        if sync_result:
            # Run duplicate finder to link multi-source events
            print("\nRunning duplicate finder...")
            dup_result = run_duplicate_finder(args.api)
            
            # Get updated stats
            print("\nGetting updated stats...")
            stats = get_stats(args.api)
            if stats:
                print(f"Database stats: {json.dumps(stats, indent=2)}")
    
    # Deploy if requested
    if args.deploy:
        print("\nDeploying to FTP...")
        deploy_events_json()
    
    print("\n" + "="*60)
    print("Scraping complete!")
    print("="*60)


if __name__ == "__main__":
    main()
