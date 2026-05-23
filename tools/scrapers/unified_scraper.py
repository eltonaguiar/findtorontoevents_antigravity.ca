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
    # Direct platform scrapers
    from .eventbrite_scraper import EventbriteScraper
    from .ticketmaster_scraper import TicketmasterScraper
    from .meetup_scraper import MeetupScraper
    # Toronto media & aggregators (NEW)
    from .blogto_scraper import BlogTOScraper
    from .nowtoronto_scraper import NOWTorontoScraper
    from .torontocom_scraper import TorontoComScraper
    # Major venues (NEW)
    from .harbourfront_scraper import HarbourfrontCentreScraper
    from .major_venues_scraper import MajorVenuesScraper
    from .tpl_bibliocommons_scraper import TPLBiblioCommonsScraper as TorontoPublicLibraryScraper
    from .singles_extras_scraper import SingleInTheCityScraper
    # Community calendars
    from .toronto_events_weekly import TorontoEventsWeeklyScraper
    from .american_arenas import AmericanArenasScraper
    from .creative_code_sheet import CreativeCodeSheetScraper
    from .lightmorning_calendar import LightMorningCalendarScraper
    from .sofiaadelgiudice_notion import SofiaAdelGiudiceNotionScraper
    # Enhanced scrapers (Scrapling-powered — Ticketmaster venues, concert halls, gardens)
    from .scrapling_enhanced import (
        ScotiabankArenaScraper, MasseyHallScraper, CasaLomaScraper,
        TOLiveScraper, UofTEventsScraper, TorontoBotanicalGardenScraper,
        BMOFieldScraper, RogersCentreScraper,
    )
    # Dating & singles events (Eventbrite categories + 25dates.com)
    from .dating_events_scraper import DatingEventsScraper
    # Fatsoma Toronto dating events
    from .fatsoma_scraper import FatsomaScraper
    # Thursday dating events
    from .thursday_scraper import GetThursdayScraper
    # Manually curated on-demand / TBD experiences (222, Timeleft, ...)
    from .manual_curated_scraper import ManualCuratedScraper
    # Additional high-volume sources (Songkick, Mirvish, RA, Zoo, Luma, Major Festivals)
    from .additional_sources_scraper import (
        SongkickScraper, MirvishTheatresScraper, ResidentAdvisorScraper,
        TorontoZooScraper, LumaScraper, MajorFestivalsScraper,
    )
    # ToDoCanada + Toronto.ca Calendar + Destination Toronto
    from .scrapling_new_sources import (
        ToDoCanadaScraper, TorontoCaCalendarScraper, DestinationTorontoScraper,
    )
except ImportError:
    # Allow running as standalone
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from base_scraper import ScrapedEvent, TORONTO_VENUES
    from nathan_phillips_square import NathanPhillipsSquareScraper
    from sankofa_square import SankofaSquareScraper
    from city_of_toronto import CityOfTorontoEventsScraper
    from unity_maps import UnityMapsScraper
    # Direct platform scrapers
    from eventbrite_scraper import EventbriteScraper
    from ticketmaster_scraper import TicketmasterScraper
    from meetup_scraper import MeetupScraper
    # Toronto media & aggregators (NEW)
    from blogto_scraper import BlogTOScraper
    from nowtoronto_scraper import NOWTorontoScraper
    from torontocom_scraper import TorontoComScraper
    # Major venues (NEW)
    from harbourfront_scraper import HarbourfrontCentreScraper
    from major_venues_scraper import MajorVenuesScraper
    from tpl_bibliocommons_scraper import TPLBiblioCommonsScraper as TorontoPublicLibraryScraper
    from singles_extras_scraper import SingleInTheCityScraper
    # Community calendars
    from toronto_events_weekly import TorontoEventsWeeklyScraper
    from american_arenas import AmericanArenasScraper
    from creative_code_sheet import CreativeCodeSheetScraper
    from lightmorning_calendar import LightMorningCalendarScraper
    from sofiaadelgiudice_notion import SofiaAdelGiudiceNotionScraper
    # Enhanced scrapers (Scrapling-powered)
    from scrapling_enhanced import (
        ScotiabankArenaScraper, MasseyHallScraper, CasaLomaScraper,
        TOLiveScraper, UofTEventsScraper, TorontoBotanicalGardenScraper,
        BMOFieldScraper, RogersCentreScraper,
    )
    # Dating & singles events (Eventbrite categories + 25dates.com)
    from dating_events_scraper import DatingEventsScraper
    # Fatsoma Toronto dating events
    from fatsoma_scraper import FatsomaScraper
    # Manually curated on-demand / TBD experiences (222, Timeleft, ...)
    from manual_curated_scraper import ManualCuratedScraper
    # Additional high-volume sources (Songkick, Mirvish, RA, Zoo, Luma, Major Festivals)
    from additional_sources_scraper import (
        SongkickScraper, MirvishTheatresScraper, ResidentAdvisorScraper,
        TorontoZooScraper, LumaScraper, MajorFestivalsScraper,
    )
    # ToDoCanada + Toronto.ca Calendar + Destination Toronto
    from scrapling_new_sources import (
        ToDoCanadaScraper, TorontoCaCalendarScraper, DestinationTorontoScraper,
    )


class UnifiedTorontoScraper:
    """
    Unified scraper that combines all Toronto event sources,
    handles deduplication, and enhances location data.
    """
    
    def __init__(self):
        self.scrapers = [
            # Official Toronto sources
            NathanPhillipsSquareScraper(),
            SankofaSquareScraper(),
            CityOfTorontoEventsScraper(),
            SofiaAdelGiudiceNotionScraper(),

            # Direct platform scrapers
            EventbriteScraper(),
            TicketmasterScraper(),
            MeetupScraper(),

            # Toronto media & aggregators (fills major gap)
            BlogTOScraper(),
            NOWTorontoScraper(),
            TorontoComScraper(),

            # Major venues (fills cultural/arts gap)
            HarbourfrontCentreScraper(),
            MajorVenuesScraper(),  # ROM, AGO, TIFF, Bentway, Evergreen
            TorontoPublicLibraryScraper(),  # BiblioCommons gateway — ~7,000 free events
            SingleInTheCityScraper(),       # GTA singles vertical — speed dating, mixers

            # Community calendars
            UnityMapsScraper(),
            TorontoEventsWeeklyScraper(),
            CreativeCodeSheetScraper(),
            LightMorningCalendarScraper(),
            AmericanArenasScraper(),

            # Enhanced scrapers (Scrapling-powered — Ticketmaster venues, etc.)
            ScotiabankArenaScraper(),      # Leafs, Raptors, concerts
            MasseyHallScraper(),           # Massey Hall + Roy Thomson Hall
            CasaLomaScraper(),             # Heritage events
            TOLiveScraper(),               # Meridian Hall, St Lawrence Centre
            UofTEventsScraper(),           # Public lectures, exhibitions
            TorontoBotanicalGardenScraper(),  # Garden events
            BMOFieldScraper(),              # TFC, concerts
            RogersCentreScraper(),          # Blue Jays, concerts

            # Dating & singles events (Eventbrite dating categories + 25dates.com)
            DatingEventsScraper(),

            # Fatsoma Toronto dating events (global platform, filtered to Toronto)
            FatsomaScraper(),

            # Thursday dating events (getthursday.com/toronto/)
            GetThursdayScraper(),

            # Manually curated (on-demand / TBD experiences like 222, Timeleft)
            ManualCuratedScraper(),

            # Additional high-volume sources (NEW)
            MajorFestivalsScraper(),        # Known annual festivals (Luminato, TIFF, CNE, Caribana...)
            MirvishTheatresScraper(),        # Princess of Wales, Royal Alex, Ed Mirvish, CAA Theatre
            SongkickScraper(),               # Concert/tour aggregator (API — needs SONGKICK_API_KEY)
            ResidentAdvisorScraper(),         # Electronic/DJ events (HTML scraping)
            TorontoZooScraper(),             # Family events, seasonal programs
            LumaScraper(),                   # Tech/community event platform (API + HTML fallback)

            # ToDoCanada + Toronto.ca Calendar + Destination Toronto
            ToDoCanadaScraper(),
            TorontoCaCalendarScraper(),
            DestinationTorontoScraper(),
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
    
    # Multi-day title keywords (must match UI logic in index.html isMultiDayEvent())
    MULTI_DAY_KEYWORDS = [
        'festival', 'exhibition', 'exhibit', 'runs until', 'conference',
        'ongoing', 'all month', 'all week', 'multiple dates', 'series',
    ]

    def detect_multi_day(self, event: Dict) -> Dict:
        """Detect and categorize multi-day events with duration classification.

        Sets BOTH snake_case and camelCase field names so the data is
        compatible with:
          - Python scraper pipeline (is_multi_day, end_date, duration_category)
          - React UI / JS (isMultiDay, endDate, durationCategory)
          - detect_multiday.js post-processor (isMultiDay)
        """
        if not event.get("date"):
            return event

        start_date = event.get("date", "")
        # Accept both field name conventions
        end_date = event.get("end_date") or event.get("endDate")

        is_multi = False
        duration_cat = "single"

        # 1) Date-range detection
        if start_date and end_date:
            try:
                start = datetime.fromisoformat(start_date.replace("Z", ""))
                end = datetime.fromisoformat(end_date.replace("Z", ""))
                days = (end - start).days
                hours = (end - start).total_seconds() / 3600

                # Match UI threshold: >=18 hours = multi-day
                if hours >= 18:
                    is_multi = True

                if days == 0:
                    duration_cat = "single"
                elif days <= 7:
                    duration_cat = "short"
                elif days <= 30:
                    duration_cat = "medium"
                else:
                    duration_cat = "long"
            except (ValueError, TypeError):
                pass

        # 2) Title/description keyword detection (matches UI isMultiDayEvent())
        if not is_multi:
            text = f"{event.get('title', '')} {event.get('description', '')}".lower()
            if any(kw in text for kw in self.MULTI_DAY_KEYWORDS):
                is_multi = True

        # Set both snake_case and camelCase
        event["is_multi_day"] = is_multi
        event["isMultiDay"] = is_multi
        event["duration_category"] = duration_cat
        event["durationCategory"] = duration_cat

        # Sync end_date / endDate
        if end_date:
            event["end_date"] = end_date
            event["endDate"] = end_date

        # 3) Keyword-based recurring detection
        text = f"{event.get('title', '')} {event.get('description', '')}".lower()
        recurring_keywords = ['recurring', 'weekly', 'monthly', 'every week', 'every month', 'series event']

        if any(kw in text for kw in recurring_keywords):
            event["is_recurring"] = True
            event["isRecurring"] = True

            if 'weekly' in text or 'every week' in text:
                event["recurrence_pattern"] = "weekly"
                event["recurrencePattern"] = "weekly"
            elif 'monthly' in text or 'every month' in text:
                event["recurrence_pattern"] = "monthly"
                event["recurrencePattern"] = "monthly"

        return event

    @staticmethod
    def fix_midnight_utc(event: Dict) -> Dict:
        """Replace T00:00:00Z with T12:00:00Z so events land on the correct
        Toronto calendar day.  Midnight UTC is 8 PM EDT / 7 PM EST the
        previous day, which causes events to appear on the wrong date in the
        frontend's America/Toronto date filter.  Noon UTC is safe for both
        EST and EDT offsets.

        Only rewrites bare midnight timestamps that lack a real time;
        timestamps with any non-zero time component are left untouched.
        """
        for key in ("date", "end_date", "endDate"):
            val = event.get(key)
            if isinstance(val, str) and val.endswith("T00:00:00Z"):
                event[key] = val.replace("T00:00:00Z", "T12:00:00Z")
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

                    # Fix midnight-UTC dates (safety net for any scraper
                    # that still emits T00:00:00Z for date-only values)
                    event = self.fix_midnight_utc(event)
                    
                    # Check for duplicates
                    if not self.is_duplicate(event, all_events):
                        all_events.append(event)
                    else:
                        # Use ASCII encoding to avoid Windows terminal Unicode errors
                        title = event.get('title', 'Unknown')[:50].encode('ascii', 'replace').decode('ascii')
                        print(f"  [Duplicate] Skipping: {title}")
                
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
