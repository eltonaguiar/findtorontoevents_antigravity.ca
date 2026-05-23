#!/usr/bin/env python3
"""
Scraper for City of Toronto official event pages:
- Festivals & Events Calendar
- Doors Open Toronto
- Nuit Blanche
- Canada Day
- FIFA World Cup Toronto 26
- Environmental Events
"""
import re
from datetime import datetime
from typing import List, Optional, Dict
from .base_scraper import BaseScraper, ScrapedEvent, TORONTO_VENUES


class CityOfTorontoEventsScraper(BaseScraper):
    """Scraper for City of Toronto official event pages"""
    
    SOURCE_NAME = "City of Toronto"
    
    # All City of Toronto event source URLs
    SOURCES = {
        "festivals_events": {
            "url": "https://www.toronto.ca/explore-enjoy/festivals-events/",
            "name": "Toronto Festivals & Events"
        },
        "festivals_calendar": {
            "url": "https://www.toronto.ca/explore-enjoy/festivals-events/festivals-events-calendar/",
            "name": "Festivals Calendar"
        },
        "doors_open": {
            "url": "https://www.toronto.ca/explore-enjoy/festivals-events/doors-open-toronto/",
            "name": "Doors Open Toronto"
        },
        "canada_day": {
            "url": "https://www.toronto.ca/explore-enjoy/festivals-events/canada-day/",
            "name": "Canada Day Toronto"
        },
        "nuit_blanche": {
            "url": "https://www.toronto.ca/explore-enjoy/festivals-events/nuitblanche/",
            "name": "Nuit Blanche Toronto"
        },
        "fifa_world_cup": {
            "url": "https://www.toronto.ca/explore-enjoy/festivals-events/fifa-world-cup-26/toronto-26-events/",
            "name": "FIFA World Cup Toronto 26"
        },
        "exhibits_events": {
            "url": "https://www.toronto.ca/explore-enjoy/history-art-culture/exhibits-events/",
            "name": "Exhibits & Events"
        },
        "environmental_events": {
            "url": "https://www.toronto.ca/services-payments/water-environment/live-green-toronto/environmental-events/",
            "name": "Live Green Toronto Events"
        }
    }
    
    def parse_toronto_date(self, date_text: str) -> tuple:
        """Parse various Toronto.ca date formats"""
        date_text = date_text.strip()
        year = datetime.now().year
        
        start_date = None
        end_date = None
        is_multi_day = False
        
        # Month mapping
        months = {
            "january": 1, "february": 2, "march": 3, "april": 4,
            "may": 5, "june": 6, "july": 7, "august": 8,
            "september": 9, "october": 10, "november": 11, "december": 12,
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
        }
        
        # Pattern: "May 23 to 24" or "May 23-24"
        range_same_month = re.search(r"(\w+)\s+(\d+)\s*(?:to|-)\s*(\d+)(?:,\s*(\d{4}))?", date_text, re.IGNORECASE)
        if range_same_month:
            month = months.get(range_same_month.group(1).lower(), 1)
            start_day = int(range_same_month.group(2))
            end_day = int(range_same_month.group(3))
            if range_same_month.group(4):
                year = int(range_same_month.group(4))
            try:
                start_date = datetime(year, month, start_day)
                end_date = datetime(year, month, end_day)
                is_multi_day = True
            except ValueError:
                pass
            return start_date, end_date, is_multi_day
        
        # Pattern: "May 23 to June 5" or "May 23 - June 5"
        range_cross_month = re.search(r"(\w+)\s+(\d+)\s*(?:to|-)\s*(\w+)\s+(\d+)(?:,\s*(\d{4}))?", date_text, re.IGNORECASE)
        if range_cross_month:
            start_month = months.get(range_cross_month.group(1).lower(), 1)
            start_day = int(range_cross_month.group(2))
            end_month = months.get(range_cross_month.group(3).lower(), 1)
            end_day = int(range_cross_month.group(4))
            if range_cross_month.group(5):
                year = int(range_cross_month.group(5))
            try:
                start_date = datetime(year, start_month, start_day)
                end_date = datetime(year, end_month, end_day)
                is_multi_day = True
            except ValueError:
                pass
            return start_date, end_date, is_multi_day
        
        # Pattern: "May 23, 2026" or "May 23"
        single_date = re.search(r"(\w+)\s+(\d+)(?:,\s*(\d{4}))?", date_text, re.IGNORECASE)
        if single_date:
            month = months.get(single_date.group(1).lower(), None)
            if month:
                day = int(single_date.group(2))
                if single_date.group(3):
                    year = int(single_date.group(3))
                try:
                    start_date = datetime(year, month, day)
                except ValueError:
                    pass
            return start_date, end_date, is_multi_day
        
        return start_date, end_date, is_multi_day
    
    def scrape_page(self, url: str, source_name: str) -> List[ScrapedEvent]:
        """Scrape a single City of Toronto event page"""
        events = []
        soup = self.fetch_page(url)
        
        if not soup:
            print(f"[{self.SOURCE_NAME}] Failed to fetch {source_name}")
            return events
        
        # Find event items - look for common patterns
        # City of Toronto pages often use specific class patterns
        
        # Try finding event cards/items
        event_containers = (
            soup.find_all(class_=re.compile(r"event|card|item|listing")) or
            soup.find_all("article") or
            soup.find_all("li", class_=re.compile(r"event|item"))
        )
        
        for container in event_containers:
            try:
                # Extract title
                title_elem = container.find(["h2", "h3", "h4", "a"], class_=re.compile(r"title|heading"))
                if not title_elem:
                    title_elem = container.find(["h2", "h3", "h4"])
                
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                if not title or len(title) < 3 or self.should_exclude(title):
                    continue
                
                # Extract date
                date_elem = container.find(class_=re.compile(r"date|time|when"))
                if not date_elem:
                    date_elem = container.find("time")
                
                date_text = date_elem.get_text(strip=True) if date_elem else ""
                start_date, end_date, is_multi_day = self.parse_toronto_date(date_text)
                
                if not start_date:
                    # Try to find date in nearby text
                    text = container.get_text()
                    start_date, end_date, is_multi_day = self.parse_toronto_date(text)
                
                if not start_date:
                    # Default to a placeholder for undated events
                    continue
                
                # Extract location
                location_elem = container.find(class_=re.compile(r"location|venue|where|address"))
                location_text = location_elem.get_text(strip=True) if location_elem else "Toronto, ON"
                
                # Enhance location
                loc_info = self.enhance_location(location_text, title)
                
                # Extract URL
                link = container.find("a", href=True)
                event_url = link["href"] if link else url
                if event_url and not event_url.startswith("http"):
                    event_url = "https://www.toronto.ca" + event_url
                
                # Extract description
                desc_elem = container.find(class_=re.compile(r"desc|summary|excerpt|body|content"))
                description = desc_elem.get_text(strip=True) if desc_elem else ""
                
                # Generate ID
                event_id = self.generate_event_id(title, start_date.isoformat(), source_name)
                
                # Categorize
                categories, tags = self.categorize_event(title, description)
                
                # Add source-specific tags
                if "doors open" in source_name.lower():
                    tags.append("Doors Open")
                    categories = ["Arts", "Community"]
                elif "nuit blanche" in source_name.lower():
                    tags.append("Nuit Blanche")
                    categories = ["Arts", "Nightlife"]
                elif "fifa" in source_name.lower() or "world cup" in source_name.lower():
                    tags.append("FIFA World Cup")
                    categories = ["Sports"]
                elif "canada day" in source_name.lower():
                    tags.append("Canada Day")
                    categories = ["Community"]
                elif "environmental" in source_name.lower() or "green" in source_name.lower():
                    tags.append("Environmental")
                    categories = ["Community"]
                
                # Create event
                event = ScrapedEvent(
                    id=event_id,
                    title=title,
                    date=start_date.isoformat() + "Z",
                    end_date=end_date.isoformat() + "Z" if end_date else None,
                    location=loc_info["location"],
                    address=loc_info.get("address"),
                    lat=loc_info.get("lat"),
                    lng=loc_info.get("lng"),
                    source=source_name,
                    host="City of Toronto",
                    url=event_url,
                    price="Free",
                    price_amount=0.0,
                    is_free=True,
                    description=description[:500] if description else f"{title} - City of Toronto Event",
                    categories=list(set(categories)),
                    tags=list(set(tags)),
                    status="UPCOMING",
                    is_multi_day=is_multi_day
                )
                
                events.append(event)
                
            except Exception as e:
                print(f"[{self.SOURCE_NAME}] Error parsing event from {source_name}: {e}")
                continue
        
        # If no structured events found, try text parsing
        if not events:
            events = self.scrape_text_based(soup, url, source_name)
        
        return events
    
    def scrape_text_based(self, soup, url: str, source_name: str) -> List[ScrapedEvent]:
        """Fallback text-based scraping"""
        events = []
        
        # Get main content
        main = soup.find("main") or soup.find(class_="content") or soup
        text = main.get_text(separator="\n")
        
        # Look for date patterns followed by event descriptions
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        
        for i, line in enumerate(lines):
            # Look for date headers
            date_match = re.search(r"(\w+\s+\d+(?:\s*[-to]+\s*\w*\s*\d+)?(?:,\s*\d{4})?)", line)
            if date_match:
                date_text = date_match.group(1)
                start_date, end_date, is_multi_day = self.parse_toronto_date(date_text)
                
                if start_date and i + 1 < len(lines):
                    # Next line might be event name
                    title = lines[i + 1] if len(lines[i + 1]) > 5 else line
                    
                    if self.should_exclude(title):
                        continue
                    
                    event_id = self.generate_event_id(title, start_date.isoformat(), source_name)
                    categories, tags = self.categorize_event(title)
                    
                    event = ScrapedEvent(
                        id=event_id,
                        title=title,
                        date=start_date.isoformat() + "Z",
                        end_date=end_date.isoformat() + "Z" if end_date else None,
                        location="Toronto, ON",
                        source=source_name,
                        host="City of Toronto",
                        url=url,
                        categories=categories,
                        tags=tags,
                        is_multi_day=is_multi_day
                    )
                    events.append(event)
        
        return events
    
    def scrape(self) -> List[ScrapedEvent]:
        """Scrape all City of Toronto event sources"""
        all_events = []
        
        for source_key, source_info in self.SOURCES.items():
            print(f"[{self.SOURCE_NAME}] Scraping {source_info['name']}...")
            events = self.scrape_page(source_info["url"], source_info["name"])
            all_events.extend(events)
            print(f"[{self.SOURCE_NAME}] Found {len(events)} events from {source_info['name']}")
        
        print(f"[{self.SOURCE_NAME}] Total scraped: {len(all_events)} events")
        return all_events


def scrape_city_of_toronto() -> List[dict]:
    """Convenience function to scrape and return as dictionaries"""
    scraper = CityOfTorontoEventsScraper()
    return scraper.scrape_to_json()


if __name__ == "__main__":
    import json
    events = scrape_city_of_toronto()
    print(json.dumps(events, indent=2))
