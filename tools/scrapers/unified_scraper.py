#!/usr/bin/env python3
"""
Unified Toronto Event Scraper
Combines all Toronto event sources into a single scraped dataset.
Handles deduplication, location enhancement, and multi-day event detection.
"""
import json
import hashlib
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from pathlib import Path

# Import individual scrapers
try:
    from .base_scraper import ScrapedEvent, TORONTO_VENUES
    from .nathan_phillips_square import NathanPhillipsSquareScraper
    from .sankofa_square import SankofaSquareScraper
    from .city_of_toronto import CityOfTorontoEventsScraper
    from .unity_maps import UnityMapsScraper
    from .allevents_calendar import AllEventsCalendarScraper
    from .toronto_events_weekly import TorontoEventsWeeklyScraper
    from .american_arenas import AmericanArenasScraper
    from .creative_code_sheet import CreativeCodeSheetScraper
    from .lightmorning_calendar import LightMorningCalendarScraper
    from .sofiaadelgiudice_notion import SofiaAdelGiudiceNotionScraper
except ImportError:
    # Allow running as standalone
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from base_scraper import ScrapedEvent, TORONTO_VENUES
    from nathan_phillips_square import NathanPhillipsSquareScraper
    from sankofa_square import SankofaSquareScraper
    from city_of_toronto import CityOfTorontoEventsScraper
    from unity_maps import UnityMapsScraper
    from allevents_calendar import AllEventsCalendarScraper
    from toronto_events_weekly import TorontoEventsWeeklyScraper
    from american_arenas import AmericanArenasScraper
    from creative_code_sheet import CreativeCodeSheetScraper
    from lightmorning_calendar import LightMorningCalendarScraper
    from sofiaadelgiudice_notion import SofiaAdelGiudiceNotionScraper


class UnifiedTorontoScraper:
    """
    Unified scraper that combines all Toronto event sources,
    handles deduplication, and enhances location data.
    """
    
    def __init__(self):
        self.scrapers = [
            NathanPhillipsSquareScraper(),
            SankofaSquareScraper(),
            CityOfTorontoEventsScraper(),
            UnityMapsScraper(),
            AllEventsCalendarScraper(),
            TorontoEventsWeeklyScraper(),
            AmericanArenasScraper(),
            CreativeCodeSheetScraper(),
            LightMorningCalendarScraper(),
            SofiaAdelGiudiceNotionScraper(),
        ]
        self.seen_titles: Set[str] = set()
    
    def normalize_title(self, title: str) -> str:
        """Normalize title for deduplication comparison"""
        # Lowercase, remove punctuation, normalize whitespace
        title = title.lower()
        title = re.sub(r"[^\w\s]", " ", title)
        title = re.sub(r"\s+", " ", title)
        return title.strip()
    
    def is_duplicate(self, event: Dict, existing_events: List[Dict]) -> bool:
        """Check if an event is a duplicate of an existing one"""
        norm_title = self.normalize_title(event.get("title", ""))
        event_date = event.get("date", "")[:10]  # Just the date part
        
        for existing in existing_events:
            existing_norm = self.normalize_title(existing.get("title", ""))
            existing_date = existing.get("date", "")[:10]
            
            # Exact title match on same date
            if norm_title == existing_norm and event_date == existing_date:
                return True
            
            # Similar title (80% word overlap) on same date
            title_words = set(norm_title.split())
            existing_words = set(existing_norm.split())
            if title_words and existing_words:
                overlap = len(title_words & existing_words)
                max_words = max(len(title_words), len(existing_words))
                if overlap / max_words > 0.8 and event_date == existing_date:
                    return True
        
        return False
    
    def enhance_location_for_event(self, event: Dict) -> Dict:
        """Enhance event location with coordinates and proper address"""
        title = event.get("title", "")
        location = event.get("location", "Toronto, ON")
        
        # Check if location is too generic
        generic_locations = ["toronto", "toronto, on", "toronto, ontario", "gta", "greater toronto area"]
        
        if location.lower() in generic_locations:
            # Try to extract venue from title
            combined = f"{title} {event.get('description', '')}".lower()
            
            for venue_name, venue_data in TORONTO_VENUES.items():
                if venue_name in combined:
                    event["location"] = venue_name.title()
                    event["address"] = venue_data["address"]
                    event["lat"] = venue_data["lat"]
                    event["lng"] = venue_data["lng"]
                    break
        
        return event
    
    def detect_multi_day(self, event: Dict) -> Dict:
        """Detect and mark multi-day events"""
        if event.get("is_multi_day"):
            return event
        
        start_date = event.get("date", "")
        end_date = event.get("end_date")
        
        if start_date and end_date:
            try:
                start = datetime.fromisoformat(start_date.replace("Z", ""))
                end = datetime.fromisoformat(end_date.replace("Z", ""))
                event["is_multi_day"] = (end - start).days > 0
            except ValueError:
                pass
        
        return event
    
    def scrape_all(self) -> List[Dict]:
        """Scrape all sources and return combined, deduplicated events"""
        all_events = []
        
        for scraper in self.scrapers:
            try:
                print(f"\n{'='*50}")
                print(f"Running {scraper.SOURCE_NAME} scraper...")
                print('='*50)
                
                events = scraper.scrape_to_json()
                
                for event in events:
                    # Enhance location
                    event = self.enhance_location_for_event(event)
                    
                    # Detect multi-day
                    event = self.detect_multi_day(event)
                    
                    # Check for duplicates
                    if not self.is_duplicate(event, all_events):
                        all_events.append(event)
                    else:
                        print(f"  [Duplicate] Skipping: {event.get('title', 'Unknown')[:50]}")
                
                print(f"Added {len(events)} events from {scraper.SOURCE_NAME}")
                
            except Exception as e:
                print(f"Error running {scraper.SOURCE_NAME}: {e}")
                continue
        
        # Sort by date
        all_events.sort(key=lambda x: x.get("date", ""))
        
        print(f"\n{'='*50}")
        print(f"Total unique events scraped: {len(all_events)}")
        print('='*50)
        
        return all_events
    
    def scrape_to_file(self, output_path: str) -> int:
        """Scrape all sources and save to JSON file"""
        events = self.scrape_all()
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(events)} events to {output_path}")
        return len(events)
    
    def merge_with_existing(self, existing_path: str, output_path: str = None) -> int:
        """Scrape new events and merge with existing events.json"""
        new_events = self.scrape_all()
        
        # Load existing events
        existing_events = []
        if Path(existing_path).exists():
            with open(existing_path, "r", encoding="utf-8") as f:
                existing_events = json.load(f)
        
        # Merge, avoiding duplicates
        merged = existing_events.copy()
        added = 0
        
        for event in new_events:
            if not self.is_duplicate(event, merged):
                merged.append(event)
                added += 1
        
        # Sort by date
        merged.sort(key=lambda x: x.get("date", ""))
        
        # Save
        output = output_path or existing_path
        with open(output, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)
        
        print(f"Merged {added} new events. Total: {len(merged)}")
        return added


def scrape_toronto_events(output_file: str = None) -> List[Dict]:
    """Main entry point - scrape all Toronto events"""
    scraper = UnifiedTorontoScraper()
    
    if output_file:
        scraper.scrape_to_file(output_file)
    
    return scraper.scrape_all()


def merge_toronto_events(events_json_path: str) -> int:
    """Merge scraped events with existing events.json"""
    scraper = UnifiedTorontoScraper()
    return scraper.merge_with_existing(events_json_path)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Scrape Toronto events from official sources")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument("--merge", "-m", help="Merge with existing events.json file")
    
    args = parser.parse_args()
    
    if args.merge:
        merge_toronto_events(args.merge)
    elif args.output:
        scrape_toronto_events(args.output)
    else:
        # Default: print events
        events = scrape_toronto_events()
        print(json.dumps(events[:5], indent=2))  # Print first 5 as sample
        print(f"\n... and {len(events) - 5} more events")
