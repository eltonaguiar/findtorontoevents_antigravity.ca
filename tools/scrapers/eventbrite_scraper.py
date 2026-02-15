#!/usr/bin/env python3
"""
Eventbrite Event Scraper for Toronto
Uses web scraping from Eventbrite's public event listings
"""
import re
import time
from datetime import datetime
from typing import List, Optional, Dict
from .base_scraper import BaseScraper, ScrapedEvent


class EventbriteScraper(BaseScraper):
    """Scraper for Eventbrite events in Toronto using web scraping"""

    SOURCE_NAME = "Eventbrite"
    BASE_URL = "https://www.eventbrite.ca/d/canada--toronto/events/"

    def __init__(self):
        super().__init__()
        self.rate_limit_delay = 0.5  # 500ms between requests

    def _extract_event_data_from_script(self, soup) -> List[Dict]:
        """Extract event data from Next.js __NEXT_DATA__ script tag"""
        try:
            # Find the __NEXT_DATA__ script tag
            script_tag = soup.find("script", {"id": "__NEXT_DATA__"})
            if not script_tag:
                return []

            import json
            data = json.loads(script_tag.string)

            # Navigate through the Next.js data structure
            # Structure: props > pageProps > __APOLLO_STATE__ > events
            page_props = data.get("props", {}).get("pageProps", {})
            apollo_state = page_props.get("__APOLLO_STATE__", {})

            events = []
            for key, value in apollo_state.items():
                if key.startswith("Event:") and isinstance(value, dict):
                    events.append(value)

            return events
        except Exception as e:
            print(f"[{self.SOURCE_NAME}] Error extracting script data: {e}")
            return []

    def _parse_event_card(self, event_data: Dict) -> Optional[ScrapedEvent]:
        """Parse individual event data from Apollo state"""
        try:
            # Extract basic info
            title = event_data.get("name", "")
            if not title or self.should_exclude(title):
                return None

            # Extract URL - might be in 'url' or need to construct from id
            event_url = event_data.get("url", "")
            if not event_url and "id" in event_data:
                event_id_num = event_data["id"]
                event_url = f"https://www.eventbrite.ca/e/{event_id_num}"

            # Extract dates
            start_date = event_data.get("startDate", "")
            end_date = event_data.get("endDate", "")

            if not start_date:
                return None

            # Ensure ISO format
            if not start_date.endswith("Z") and "+" not in start_date:
                start_date += "Z"
            if end_date and not end_date.endswith("Z") and "+" not in end_date:
                end_date += "Z"

            # Multi-day detection
            is_multi = False
            duration_cat = "single"
            if start_date and end_date:
                try:
                    start = datetime.fromisoformat(start_date.replace("Z", ""))
                    end = datetime.fromisoformat(end_date.replace("Z", ""))
                    days = (end - start).days
                    is_multi = days > 0

                    if days == 0:
                        duration_cat = "single"
                    elif days <= 7:
                        duration_cat = "short"
                    elif days <= 30:
                        duration_cat = "medium"
                    else:
                        duration_cat = "long"
                except:
                    pass

            # Extract description
            description = event_data.get("description", "") or event_data.get("summary", "")

            # Extract venue/location
            venue_data = event_data.get("venue", {}) or event_data.get("location", {})
            if venue_data:
                venue_name = venue_data.get("name", "Toronto, ON")
                address_data = venue_data.get("address", {})
                address = address_data.get("localized_address_display", "") or address_data.get("address", "")
                lat = venue_data.get("latitude")
                lng = venue_data.get("longitude")

                location_info = {
                    "location": venue_name,
                    "address": address if address else None,
                    "lat": float(lat) if lat else None,
                    "lng": float(lng) if lng else None
                }
            else:
                location_info = self.enhance_location("Toronto, ON", title)

            # Categorize event
            categories, tags = self.categorize_event(title, description)

            # Extract price
            is_free = event_data.get("isFree", False) or event_data.get("is_free", False)
            if is_free:
                price_display = "Free"
                price_amount = 0.0
            else:
                # Look for price in various fields
                ticket_price = event_data.get("ticketPrice", {})
                if ticket_price:
                    price_display = ticket_price.get("display", "See Tickets")
                    price_amount = float(ticket_price.get("value", 0.0))
                else:
                    price_display = "See Tickets"
                    price_amount = 0.0

            # Extract image
            image_data = event_data.get("image", {}) or event_data.get("logo", {})
            image_url = image_data.get("url", "") if image_data else ""

            # Extract organizer
            organizer_data = event_data.get("organizer", {})
            organizer = organizer_data.get("name", self.SOURCE_NAME) if organizer_data else self.SOURCE_NAME

            # Generate event ID
            event_id = self.generate_event_id(title, start_date, self.SOURCE_NAME)

            # Create ScrapedEvent
            event = ScrapedEvent(
                id=event_id,
                title=title,
                date=start_date,
                end_date=end_date if is_multi else None,
                location=location_info["location"],
                address=location_info["address"],
                lat=location_info["lat"],
                lng=location_info["lng"],
                source=self.SOURCE_NAME,
                host=organizer,
                url=event_url,
                price=price_display,
                price_amount=price_amount,
                is_free=is_free,
                description=description[:500] if description else "",
                categories=categories,
                tags=tags,
                status="UPCOMING",
                is_multi_day=is_multi,
                duration_category=duration_cat,
            )

            return event

        except Exception as e:
            print(f"[{self.SOURCE_NAME}] Error parsing event card: {e}")
            return None

    def scrape(self) -> List[ScrapedEvent]:
        """Scrape events from Eventbrite browse page"""
        events = []
        page = 1
        max_pages = 10  # Limit pages for now

        print(f"[{self.SOURCE_NAME}] Starting web scrape...")

        while page <= max_pages:
            print(f"[{self.SOURCE_NAME}] Fetching page {page}...")

            # Construct URL with page parameter
            url = f"{self.BASE_URL}?page={page}"
            soup = self.fetch_page(url)

            if not soup:
                print(f"[{self.SOURCE_NAME}] Failed to fetch page {page}")
                break

            # Try to extract events from Next.js data
            event_data_list = self._extract_event_data_from_script(soup)

            if not event_data_list:
                # Fallback: try to scrape event cards from HTML
                print(f"[{self.SOURCE_NAME}] No events found in script data, trying HTML scraping...")
                # This would require analyzing the actual HTML structure
                # For now, break if no script data
                break

            for event_data in event_data_list:
                event = self._parse_event_card(event_data)
                if event:
                    events.append(event)

            # Rate limiting
            time.sleep(self.rate_limit_delay)

            # Check if there are more pages (this is heuristic-based)
            if len(event_data_list) < 20:  # If we got fewer events, likely no more pages
                print(f"[{self.SOURCE_NAME}] Fewer events on page, assuming end")
                break

            page += 1

        print(f"[{self.SOURCE_NAME}] Scraped {len(events)} events")
        return events


def scrape_eventbrite() -> List[dict]:
    """Convenience function for standalone use"""
    scraper = EventbriteScraper()
    return scraper.scrape_to_json()


if __name__ == "__main__":
    import json
    events = scrape_eventbrite()
    print(json.dumps(events[:3], indent=2))  # Print first 3 events as sample
    print(f"\nTotal events: {len(events)}")
