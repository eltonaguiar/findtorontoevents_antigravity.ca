#!/usr/bin/env python3
"""
Scraper for Sankofa Square events
https://www.sankofasquare.ca/calendar
"""
import re
from datetime import datetime
from typing import List, Optional
from .base_scraper import BaseScraper, ScrapedEvent, TORONTO_VENUES


class SankofaSquareScraper(BaseScraper):
    """Scraper for Sankofa Square (formerly Yonge-Dundas Square) events"""
    
    SOURCE_NAME = "Sankofa Square"
    BASE_URL = "https://www.sankofasquare.ca/calendar"
    
    # Sankofa Square location (same as Yonge-Dundas Square)
    VENUE = TORONTO_VENUES["sankofa square"]
    
    def parse_sankofa_date(self, date_text: str) -> tuple:
        """Parse Sankofa Square date formats"""
        # Clean up text
        date_text = date_text.strip()
        
        start_date = None
        end_date = None
        is_multi_day = False
        
        # Get current year
        year = datetime.now().year
        
        # Month mapping
        months = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
            "january": 1, "february": 2, "march": 3, "april": 4,
            "june": 6, "july": 7, "august": 8, "september": 9,
            "october": 10, "november": 11, "december": 12
        }
        
        # Pattern: "Feb 1 to Feb 28" or "Feb 1 - Feb 28"
        range_match = re.search(r"(\w+)\s+(\d+)\s*(?:to|-)\s*(\w+)\s+(\d+)", date_text, re.IGNORECASE)
        if range_match:
            start_month = months.get(range_match.group(1).lower()[:3], 1)
            start_day = int(range_match.group(2))
            end_month = months.get(range_match.group(3).lower()[:3], 1)
            end_day = int(range_match.group(4))
            try:
                start_date = datetime(year, start_month, start_day)
                end_date = datetime(year, end_month, end_day)
                is_multi_day = True
            except ValueError:
                pass
            return start_date, end_date, is_multi_day
        
        # Pattern: "Feb 7" (single day)
        single_match = re.search(r"(\w+)\s+(\d+)", date_text, re.IGNORECASE)
        if single_match:
            month = months.get(single_match.group(1).lower()[:3], 1)
            day = int(single_match.group(2))
            try:
                start_date = datetime(year, month, day)
            except ValueError:
                pass
            return start_date, end_date, is_multi_day
        
        return start_date, end_date, is_multi_day
    
    def parse_time(self, time_text: str) -> Optional[str]:
        """Parse time strings like '12:00 p.m.' to 24hr format"""
        time_match = re.search(r"(\d{1,2}):?(\d{2})?\s*(a\.?m\.?|p\.?m\.?)", time_text, re.IGNORECASE)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
            period = time_match.group(3).lower().replace(".", "")
            
            if period == "pm" and hour != 12:
                hour += 12
            elif period == "am" and hour == 12:
                hour = 0
            
            return f"{hour:02d}:{minute:02d}"
        return None
    
    def scrape(self) -> List[ScrapedEvent]:
        """Scrape Sankofa Square events"""
        events = []
        soup = self.fetch_page(self.BASE_URL)
        
        if not soup:
            print(f"[{self.SOURCE_NAME}] Failed to fetch page")
            return events
        
        # Find all event items - they typically have specific class patterns
        # Look for event containers
        event_containers = soup.find_all("article") or soup.find_all(class_=re.compile(r"event|calendar-item"))
        
        # Also look for event links/divs with specific patterns
        if not event_containers:
            # Try finding by common patterns in the HTML
            event_containers = soup.find_all("div", class_=re.compile(r"summary|event|item"))
        
        # Parse page text for events if structured parsing fails
        if not event_containers:
            return self.scrape_from_text(soup)
        
        for container in event_containers:
            try:
                # Extract title
                title_elem = container.find(["h1", "h2", "h3", "h4", "a"], class_=re.compile(r"title|name|heading"))
                if not title_elem:
                    title_elem = container.find(["h1", "h2", "h3", "h4"])
                
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                if not title or self.should_exclude(title):
                    continue
                
                # Extract date
                date_elem = container.find(class_=re.compile(r"date|time|when"))
                if not date_elem:
                    date_elem = container.find("time")
                
                date_text = date_elem.get_text(strip=True) if date_elem else ""
                start_date, end_date, is_multi_day = self.parse_sankofa_date(date_text)
                
                if not start_date:
                    continue
                
                # Extract URL
                link = container.find("a", href=True)
                url = link["href"] if link else self.BASE_URL
                if url and not url.startswith("http"):
                    url = "https://www.sankofasquare.ca" + url
                
                # Extract description
                desc_elem = container.find(class_=re.compile(r"desc|summary|excerpt|body"))
                description = desc_elem.get_text(strip=True) if desc_elem else ""
                
                # Generate ID
                event_id = self.generate_event_id(title, start_date.isoformat(), self.SOURCE_NAME)
                
                # Categorize
                categories, tags = self.categorize_event(title, description)
                
                # Create event
                event = ScrapedEvent(
                    id=event_id,
                    title=title,
                    date=start_date.isoformat() + "Z",
                    end_date=end_date.isoformat() + "Z" if end_date else None,
                    location="Sankofa Square",
                    address=self.VENUE["address"],
                    lat=self.VENUE["lat"],
                    lng=self.VENUE["lng"],
                    source=self.SOURCE_NAME,
                    host="Sankofa Square",
                    url=url,
                    price="Free",
                    price_amount=0.0,
                    is_free=True,
                    description=description[:500] if description else f"{title} at Sankofa Square",
                    categories=categories,
                    tags=tags,
                    status="UPCOMING",
                    is_multi_day=is_multi_day
                )
                
                events.append(event)
                
            except Exception as e:
                print(f"[{self.SOURCE_NAME}] Error parsing event: {e}")
                continue
        
        print(f"[{self.SOURCE_NAME}] Scraped {len(events)} events")
        return events
    
    def scrape_from_text(self, soup) -> List[ScrapedEvent]:
        """Fallback scraping from page text"""
        events = []
        
        # Get all text and look for event patterns
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        # Look for date headers followed by event names
        current_date = None
        
        for i, line in enumerate(lines):
            # Check for date patterns
            date_match = re.match(r"(\w{3})\s+(\d{1,2})", line, re.IGNORECASE)
            if date_match:
                month_str = date_match.group(1)
                day = int(date_match.group(2))
                
                months = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                         "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
                
                month = months.get(month_str.lower(), None)
                if month:
                    try:
                        current_date = datetime(datetime.now().year, month, day)
                    except ValueError:
                        pass
                continue
            
            # Look for event titles (usually in ALL CAPS or specific patterns)
            if current_date and len(line) > 5:
                # Skip time-only lines
                if re.match(r"^\d{1,2}:\d{2}", line):
                    continue
                
                # Skip navigation/UI elements
                if line.lower() in ["view event", "learn more", "back", "next", "previous"]:
                    continue
                
                # This might be an event title
                title = line
                if self.should_exclude(title):
                    continue
                
                event_id = self.generate_event_id(title, current_date.isoformat(), self.SOURCE_NAME)
                categories, tags = self.categorize_event(title)
                
                event = ScrapedEvent(
                    id=event_id,
                    title=title,
                    date=current_date.isoformat() + "Z",
                    location="Sankofa Square",
                    address=self.VENUE["address"],
                    lat=self.VENUE["lat"],
                    lng=self.VENUE["lng"],
                    source=self.SOURCE_NAME,
                    host="Sankofa Square",
                    url=self.BASE_URL,
                    categories=categories,
                    tags=tags,
                    is_multi_day=False
                )
                
                events.append(event)
        
        return events


def scrape_sankofa_square() -> List[dict]:
    """Convenience function to scrape and return as dictionaries"""
    scraper = SankofaSquareScraper()
    return scraper.scrape_to_json()


if __name__ == "__main__":
    import json
    events = scrape_sankofa_square()
    print(json.dumps(events, indent=2))
