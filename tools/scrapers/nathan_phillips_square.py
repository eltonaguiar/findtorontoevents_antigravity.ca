#!/usr/bin/env python3
"""
Scraper for Nathan Phillips Square events from Toronto.ca
https://www.toronto.ca/services-payments/venues-facilities-bookings/booking-city-facilities/city-squares/nathan-phillips-square/events-happening-on-nathan-phillips-square/
"""
import re
from datetime import datetime
from typing import List, Optional
from .base_scraper import BaseScraper, ScrapedEvent, TORONTO_VENUES


class NathanPhillipsSquareScraper(BaseScraper):
    """Scraper for Nathan Phillips Square events"""
    
    SOURCE_NAME = "Nathan Phillips Square"
    BASE_URL = "https://www.toronto.ca/services-payments/venues-facilities-bookings/booking-city-facilities/city-squares/nathan-phillips-square/events-happening-on-nathan-phillips-square/"
    
    # Nathan Phillips Square location
    VENUE = TORONTO_VENUES["nathan phillips square"]
    
    def parse_nps_date(self, date_text: str, month_name: str, year: int) -> tuple:
        """Parse NPS-specific date formats"""
        # Remove leading/trailing whitespace
        date_text = date_text.strip()
        
        # Month name to number
        months = {
            "january": 1, "february": 2, "march": 3, "april": 4,
            "may": 5, "june": 6, "july": 7, "august": 8,
            "september": 9, "october": 10, "november": 11, "december": 12
        }
        month_num = months.get(month_name.lower(), 1)
        
        start_date = None
        end_date = None
        is_multi_day = False
        
        # Pattern: "January 1 to 7" or "January 1 - 7"
        range_match = re.match(r"(\w+)\s+(\d+)\s*(?:to|-)\s*(\d+)", date_text, re.IGNORECASE)
        if range_match:
            start_day = int(range_match.group(2))
            end_day = int(range_match.group(3))
            start_date = datetime(year, month_num, start_day)
            end_date = datetime(year, month_num, end_day)
            is_multi_day = True
            return start_date, end_date, is_multi_day
        
        # Pattern: "January 15 to February 20" 
        cross_month_match = re.match(r"(\w+)\s+(\d+)\s*(?:to|-)\s*(\w+)\s+(\d+)", date_text, re.IGNORECASE)
        if cross_month_match:
            start_month = months.get(cross_month_match.group(1).lower(), month_num)
            start_day = int(cross_month_match.group(2))
            end_month = months.get(cross_month_match.group(3).lower(), month_num)
            end_day = int(cross_month_match.group(4))
            start_date = datetime(year, start_month, start_day)
            end_date = datetime(year, end_month, end_day)
            is_multi_day = True
            return start_date, end_date, is_multi_day
        
        # Pattern: "January 15" (single day)
        single_match = re.match(r"(\w+)\s+(\d+)", date_text, re.IGNORECASE)
        if single_match:
            day = int(single_match.group(2))
            try:
                start_date = datetime(year, month_num, day)
            except ValueError:
                pass
            return start_date, end_date, is_multi_day
        
        return start_date, end_date, is_multi_day
    
    def extract_event_info(self, text: str) -> tuple:
        """Extract event name and date info from text like 'January 4: New Year's Skate Party'"""
        # Pattern: "Month Day: Event Name" or "Month Day to Day: Event Name"
        patterns = [
            # "January 1 to 7: Cavalcade of Lights"
            r"(\w+)\s+(\d+)\s*(?:to|-)\s*(\d+):\s*(.+)",
            # "January 15: Event Name"
            r"(\w+)\s+(\d+):\s*(.+)",
            # "January 15 (Holiday): Event" 
            r"(\w+)\s+(\d+)\s*\([^)]+\):\s*(.+)",
            # "January 15 (Holiday)" - holiday only
            r"(\w+)\s+(\d+)\s*\(([^)]+)\)",
        ]
        
        for pattern in patterns:
            match = re.match(pattern, text.strip(), re.IGNORECASE)
            if match:
                return match.groups()
        
        return None
    
    def scrape(self) -> List[ScrapedEvent]:
        """Scrape Nathan Phillips Square events"""
        events = []
        soup = self.fetch_page(self.BASE_URL)
        
        if not soup:
            print(f"[{self.SOURCE_NAME}] Failed to fetch page")
            return events
        
        # Current year - events span from current year
        current_year = datetime.now().year
        
        # Find all month sections (they use accordion or similar structure)
        # The page has month headers followed by event lists
        content = soup.find("div", class_="entry-content") or soup.find("main") or soup
        
        # Look for month headers and their content
        current_month = None
        
        # Find all text content that looks like events
        all_text = content.get_text(separator="\n")
        lines = [line.strip() for line in all_text.split("\n") if line.strip()]
        
        # Month patterns
        month_names = ["january", "february", "march", "april", "may", "june", 
                       "july", "august", "september", "october", "november", "december"]
        
        for line in lines:
            # Check if this is a month header
            line_lower = line.lower()
            for month in month_names:
                if line_lower == month or line_lower.startswith(month + " "):
                    current_month = month
                    break
            
            if not current_month:
                continue
            
            # Skip maintenance and non-event entries
            if self.should_exclude(line):
                continue
            
            # Try to extract event info
            info = self.extract_event_info(line)
            if not info:
                continue
            
            # Determine if it's a range or single date
            if len(info) == 4:  # Range with event
                month_str, start_day, end_day, event_name = info
                start_date = datetime(current_year, month_names.index(month_str.lower()) + 1, int(start_day))
                end_date = datetime(current_year, month_names.index(month_str.lower()) + 1, int(end_day))
                is_multi_day = True
            elif len(info) == 3:
                month_str, day, event_name = info
                # Could be event name or holiday name
                try:
                    start_date = datetime(current_year, month_names.index(month_str.lower()) + 1, int(day))
                    end_date = None
                    is_multi_day = False
                except (ValueError, IndexError):
                    continue
            else:
                continue
            
            # Clean event name
            event_name = event_name.strip()
            if not event_name:
                continue
            
            # Skip if it's just a holiday marker
            if event_name.lower() in ["family day", "christmas", "boxing day", "new year's eve", 
                                       "canada day", "victoria day", "labour day", "thanksgiving",
                                       "good friday", "easter monday", "remembrance day", "simcoe day"]:
                # These are holidays, not events - skip unless there's more info
                continue
            
            # Check for "(Event: actual dates)" pattern
            event_match = re.search(r"\(Event:\s*([^)]+)\)", event_name)
            if event_match:
                actual_dates = event_match.group(1)
                event_name = re.sub(r"\s*\(Event:[^)]+\)", "", event_name).strip()
            
            # Generate event ID
            event_id = self.generate_event_id(event_name, start_date.isoformat(), self.SOURCE_NAME)
            
            # Categorize
            categories, tags = self.categorize_event(event_name)
            
            # Create event
            event = ScrapedEvent(
                id=event_id,
                title=event_name,
                date=start_date.isoformat() + "Z",
                end_date=end_date.isoformat() + "Z" if end_date else None,
                location="Nathan Phillips Square",
                address=self.VENUE["address"],
                lat=self.VENUE["lat"],
                lng=self.VENUE["lng"],
                source=self.SOURCE_NAME,
                host="City of Toronto",
                url=self.BASE_URL,
                price="Free",
                price_amount=0.0,
                is_free=True,
                description=f"{event_name} at Nathan Phillips Square",
                categories=categories,
                tags=tags,
                status="UPCOMING",
                is_multi_day=is_multi_day
            )
            
            events.append(event)
        
        print(f"[{self.SOURCE_NAME}] Scraped {len(events)} events")
        return events


def scrape_nathan_phillips_square() -> List[dict]:
    """Convenience function to scrape and return as dictionaries"""
    scraper = NathanPhillipsSquareScraper()
    return scraper.scrape_to_json()


if __name__ == "__main__":
    import json
    events = scrape_nathan_phillips_square()
    print(json.dumps(events, indent=2))
