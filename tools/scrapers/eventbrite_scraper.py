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

    def _extract_event_data_from_jsonld(self, soup) -> List[Dict]:
        """Extract event data from JSON-LD structured data"""
        try:
            import json

            # Find JSON-LD script tags
            scripts = soup.find_all("script", type="application/ld+json")

            for script in scripts:
                try:
                    data = json.loads(script.string)

                    # Look for ItemList containing events
                    if data.get("@type") == "ItemList":
                        items = data.get("itemListElement", [])
                        events = []

                        for item in items:
                            event_data = item.get("item", {})
                            if event_data.get("@type") == "Event":
                                events.append(event_data)

                        if events:
                            return events

                except json.JSONDecodeError:
                    continue

            return []

        except Exception as e:
            print(f"[{self.SOURCE_NAME}] Error extracting JSON-LD data: {e}")
            return []

    def _parse_event_card(self, event_data: Dict) -> Optional[ScrapedEvent]:
        """Parse individual event data from JSON-LD schema.org Event"""
        try:
            # Extract basic info
            title = event_data.get("name", "")
            if not title or self.should_exclude(title):
                return None

            # Extract URL
            event_url = event_data.get("url", "")
            if not event_url:
                return None

            # Extract dates (schema.org format: YYYY-MM-DD or ISO 8601)
            start_date = event_data.get("startDate", "")
            end_date = event_data.get("endDate", "")

            if not start_date:
                return None

            # Convert to ISO format with time
            try:
                # If date only (YYYY-MM-DD), add time
                if len(start_date) == 10:
                    start_date = f"{start_date}T00:00:00Z"
                elif not start_date.endswith("Z") and "+" not in start_date and "-" not in start_date[-6:]:
                    start_date += "Z"

                if end_date:
                    if len(end_date) == 10:
                        end_date = f"{end_date}T23:59:59Z"
                    elif not end_date.endswith("Z") and "+" not in end_date and "-" not in end_date[-6:]:
                        end_date += "Z"
            except:
                pass

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
            description = event_data.get("description", "")

            # Extract venue/location (schema.org Place structure)
            location_data = event_data.get("location", {})
            if location_data and isinstance(location_data, dict):
                venue_name = location_data.get("name", "Toronto, ON")

                # Extract address
                address_data = location_data.get("address", {})
                if isinstance(address_data, dict):
                    street = address_data.get("streetAddress", "")
                    city = address_data.get("addressLocality", "")
                    region = address_data.get("addressRegion", "")
                    postal = address_data.get("postalCode", "")

                    # Build full address
                    address_parts = [p for p in [street, city, region, postal] if p]
                    full_address = ", ".join(address_parts) if address_parts else None
                else:
                    full_address = str(address_data) if address_data else None

                # Extract coordinates
                geo_data = location_data.get("geo", {})
                if isinstance(geo_data, dict):
                    lat = geo_data.get("latitude")
                    lng = geo_data.get("longitude")
                else:
                    lat = None
                    lng = None

                location_info = {
                    "location": venue_name,
                    "address": full_address,
                    "lat": float(lat) if lat else None,
                    "lng": float(lng) if lng else None
                }
            else:
                location_info = self.enhance_location("Toronto, ON", title)

            # Categorize event
            categories, tags = self.categorize_event(title, description)

            # Extract price from offers (schema.org offers structure)
            offers = event_data.get("offers", {})
            is_free = False
            price_display = "See Tickets"
            price_amount = 0.0

            if isinstance(offers, dict):
                # Check if free
                price = offers.get("price")
                if price == "0" or price == 0 or offers.get("priceCurrency") == "Free":
                    is_free = True
                    price_display = "Free"
                elif price:
                    try:
                        price_amount = float(price)
                        currency = offers.get("priceCurrency", "CAD")
                        price_display = f"{currency} ${price_amount:.2f}"
                    except:
                        pass

            # Extract image
            image_url = event_data.get("image", "")

            # Extract organizer (schema.org doesn't always have this)
            organizer_data = event_data.get("organizer", {})
            if isinstance(organizer_data, dict):
                organizer = organizer_data.get("name", self.SOURCE_NAME)
            else:
                organizer = self.SOURCE_NAME

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
            print(f"[{self.SOURCE_NAME}] Error parsing event: {e}")
            import traceback
            traceback.print_exc()
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

            # Extract events from JSON-LD structured data
            event_data_list = self._extract_event_data_from_jsonld(soup)

            if not event_data_list:
                print(f"[{self.SOURCE_NAME}] No events found in JSON-LD data on page {page}")
                break

            for event_data in event_data_list:
                event = self._parse_event_card(event_data)
                if event:
                    events.append(event)

            # Rate limiting
            time.sleep(self.rate_limit_delay)

            # Check if there are more pages
            # JSON-LD typically returns ~32 events per page
            if len(event_data_list) < 10:  # If we got very few events, likely no more pages
                print(f"[{self.SOURCE_NAME}] Only {len(event_data_list)} events on page, assuming end")
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
