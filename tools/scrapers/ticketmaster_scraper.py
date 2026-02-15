#!/usr/bin/env python3
"""
Ticketmaster Event Scraper for Toronto
Uses Ticketmaster Discovery API (free API key required)
Register at: https://developer.ticketmaster.com/
"""
import os
import requests
from datetime import datetime
from typing import List, Optional, Dict
from .base_scraper import BaseScraper, ScrapedEvent


class TicketmasterScraper(BaseScraper):
    """Scraper for Ticketmaster events in Toronto using Discovery API"""

    SOURCE_NAME = "Ticketmaster"
    BASE_URL = "https://app.ticketmaster.com/discovery/v2"
    SEARCH_ENDPOINT = f"{BASE_URL}/events.json"

    # Ticketmaster classification mapping to our categories
    CLASSIFICATION_MAP = {
        "Music": "Music",
        "Sports": "Sports",
        "Arts & Theatre": "Arts",
        "Film": "Arts",
        "Miscellaneous": "General",
        "Undefined": "General",
    }

    def __init__(self, api_key: str = None):
        super().__init__()
        # Try both environment variable names
        self.api_key = api_key or os.getenv("TICKETMAST_CONSUMER_KEY") or os.getenv("TICKETMASTER_API_KEY")
        if not self.api_key:
            print(f"[{self.SOURCE_NAME}] Warning: No API key found. Set TICKETMAST_CONSUMER_KEY environment variable.")
            print(f"[{self.SOURCE_NAME}] Register for free at: https://developer.ticketmaster.com/")

    def _make_request(self, params: Dict) -> Optional[Dict]:
        """Make API request to Ticketmaster"""
        try:
            if not self.api_key:
                print(f"[{self.SOURCE_NAME}] Cannot make request without API key")
                return None

            params["apikey"] = self.api_key
            response = self.session.get(self.SEARCH_ENDPOINT, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"[{self.SOURCE_NAME}] HTTP error {e.response.status_code}: {e}")
            if e.response.status_code == 401:
                print(f"[{self.SOURCE_NAME}] Invalid API key. Check TICKETMASTER_API_KEY.")
            return None
        except Exception as e:
            print(f"[{self.SOURCE_NAME}] Error making request: {e}")
            return None

    def _map_classification(self, event_data: Dict) -> str:
        """Extract and map event classification to our category"""
        classifications = event_data.get("classifications", [])
        if classifications:
            segment = classifications[0].get("segment", {}).get("name", "General")
            return self.CLASSIFICATION_MAP.get(segment, "General")
        return "General"

    def _parse_date(self, dates_data: Dict) -> tuple:
        """Extract start and end dates from Ticketmaster date structure"""
        start_data = dates_data.get("start", {})

        # Get local date and time
        local_date = start_data.get("localDate")
        local_time = start_data.get("localTime", "00:00:00")

        if not local_date:
            return None, None

        # Combine date and time into ISO format
        try:
            # Parse and convert to ISO format with Z suffix
            dt_str = f"{local_date}T{local_time}"
            dt = datetime.fromisoformat(dt_str)
            start_date = dt.isoformat() + "Z"

            # Check for end date
            end_data = dates_data.get("end")
            end_date = None
            if end_data:
                end_local_date = end_data.get("localDate")
                end_local_time = end_data.get("localTime", "23:59:59")
                if end_local_date:
                    end_dt_str = f"{end_local_date}T{end_local_time}"
                    end_dt = datetime.fromisoformat(end_dt_str)
                    end_date = end_dt.isoformat() + "Z"

            return start_date, end_date
        except Exception as e:
            print(f"[{self.SOURCE_NAME}] Error parsing date: {e}")
            return None, None

    def _parse_price(self, event_data: Dict) -> tuple:
        """Extract price information"""
        price_ranges = event_data.get("priceRanges", [])

        if price_ranges:
            min_price = price_ranges[0].get("min", 0.0)
            max_price = price_ranges[0].get("max", 0.0)
            currency = price_ranges[0].get("currency", "CAD")

            if min_price == 0 and max_price == 0:
                return "Free", 0.0, True
            elif min_price == max_price:
                return f"{currency} ${min_price:.2f}", float(min_price), False
            else:
                return f"{currency} ${min_price:.2f} - ${max_price:.2f}", float(min_price), False

        return "See Tickets", 0.0, False

    def _extract_venue(self, event_data: Dict) -> Dict:
        """Extract venue information"""
        embedded = event_data.get("_embedded", {})
        venues = embedded.get("venues", [])

        if venues:
            venue = venues[0]
            venue_name = venue.get("name", "Toronto, ON")
            address_data = venue.get("address", {})
            city_data = venue.get("city", {})
            location = venue.get("location", {})

            # Build full address
            address_line = address_data.get("line1", "")
            city = city_data.get("name", "Toronto")
            postal = address_data.get("postalCode", "")

            full_address = f"{address_line}, {city}, ON {postal}".strip(", ")

            return {
                "location": venue_name,
                "address": full_address if address_line else None,
                "lat": float(location.get("latitude")) if location.get("latitude") else None,
                "lng": float(location.get("longitude")) if location.get("longitude") else None,
            }

        return {
            "location": "Toronto, ON",
            "address": None,
            "lat": None,
            "lng": None
        }

    def scrape(self) -> List[ScrapedEvent]:
        """Scrape events from Ticketmaster API"""
        events = []
        page = 0
        max_pages = 20

        print(f"[{self.SOURCE_NAME}] Starting scrape...")

        while page < max_pages:
            print(f"[{self.SOURCE_NAME}] Fetching page {page}...")

            params = {
                "city": "Toronto",
                "countryCode": "CA",
                "size": 50,
                "page": page,
                "sort": "date,asc",
            }

            data = self._make_request(params)

            if not data:
                break

            embedded = data.get("_embedded")
            if not embedded or "events" not in embedded:
                print(f"[{self.SOURCE_NAME}] No more events found")
                break

            page_events = embedded.get("events", [])
            if not page_events:
                print(f"[{self.SOURCE_NAME}] Empty page, stopping")
                break

            for event_data in page_events:
                try:
                    # Extract basic info
                    title = event_data.get("name", "")
                    if not title or self.should_exclude(title):
                        continue

                    # Extract dates
                    dates_data = event_data.get("dates", {})
                    start_date, end_date = self._parse_date(dates_data)

                    if not start_date:
                        continue

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

                    # Extract info and description
                    info = event_data.get("info", "")
                    please_note = event_data.get("pleaseNote", "")
                    description = f"{info}\n{please_note}".strip()

                    # Extract venue/location
                    venue_info = self._extract_venue(event_data)

                    # Extract category
                    primary_category = self._map_classification(event_data)

                    # Use categorize_event for tags and additional categories
                    categories, tags = self.categorize_event(title, description)

                    # Add primary category from Ticketmaster
                    if primary_category != "General" and primary_category not in categories:
                        categories.insert(0, primary_category)

                    # Extract price
                    price_display, price_amount, is_free = self._parse_price(event_data)

                    # Extract URL
                    event_url = event_data.get("url", "")

                    # Extract image
                    images = event_data.get("images", [])
                    image_url = images[0].get("url", "") if images else ""

                    # Extract promoter/organizer
                    promoters = event_data.get("promoters", [])
                    host = promoters[0].get("name", self.SOURCE_NAME) if promoters else self.SOURCE_NAME

                    # Generate event ID
                    event_id = self.generate_event_id(title, start_date, self.SOURCE_NAME)

                    # Create ScrapedEvent
                    event = ScrapedEvent(
                        id=event_id,
                        title=title,
                        date=start_date,
                        end_date=end_date if is_multi else None,
                        location=venue_info["location"],
                        address=venue_info["address"],
                        lat=venue_info["lat"],
                        lng=venue_info["lng"],
                        source=self.SOURCE_NAME,
                        host=host,
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

                    events.append(event)

                except Exception as e:
                    print(f"[{self.SOURCE_NAME}] Error parsing event: {e}")
                    continue

            # Check pagination
            page_data = data.get("page", {})
            total_pages = page_data.get("totalPages", 1)

            if page >= total_pages - 1:
                print(f"[{self.SOURCE_NAME}] Reached last page")
                break

            page += 1

        print(f"[{self.SOURCE_NAME}] Scraped {len(events)} events")
        return events


def scrape_ticketmaster() -> List[dict]:
    """Convenience function for standalone use"""
    scraper = TicketmasterScraper()
    return scraper.scrape_to_json()


if __name__ == "__main__":
    import json
    events = scrape_ticketmaster()
    if events:
        print(json.dumps(events[:3], indent=2))  # Print first 3 events as sample
        print(f"\nTotal events: {len(events)}")
    else:
        print("No events found. Check API key configuration.")
