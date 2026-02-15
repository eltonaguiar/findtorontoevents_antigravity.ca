#!/usr/bin/env python3
"""
Eventbrite Event Scraper for Toronto
Uses Eventbrite's free public API to fetch events in Toronto
"""
import requests
import time
from datetime import datetime
from typing import List, Optional, Dict
from .base_scraper import BaseScraper, ScrapedEvent


class EventbriteScraper(BaseScraper):
    """Scraper for Eventbrite events in Toronto using their public API"""

    SOURCE_NAME = "Eventbrite"
    BASE_URL = "https://www.eventbriteapi.com/v3"
    SEARCH_ENDPOINT = f"{BASE_URL}/events/search/"

    # Eventbrite category mapping to our categories
    CATEGORY_MAP = {
        "103": "Music",  # Music
        "105": "Arts",   # Performing & Visual Arts
        "108": "Sports", # Sports & Fitness
        "110": "Food & Drink",  # Food & Drink
        "113": "Community",  # Community & Culture
        "101": "Business",  # Business & Professional
        "104": "Arts",   # Film, Media & Entertainment
        "111": "Family",  # Family & Education
        "116": "Nightlife",  # Nightlife
        "119": "Community",  # Charity & Causes
    }

    def __init__(self):
        super().__init__()
        self.rate_limit_delay = 0.35  # 350ms between requests (3 req/sec limit)

    def _make_request(self, url: str, params: Dict = None) -> Optional[Dict]:
        """Make API request with rate limiting"""
        try:
            time.sleep(self.rate_limit_delay)
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                print(f"[{self.SOURCE_NAME}] Rate limit exceeded, waiting 2 seconds...")
                time.sleep(2)
                return self._make_request(url, params)
            else:
                print(f"[{self.SOURCE_NAME}] HTTP error {e.response.status_code}: {e}")
                return None
        except Exception as e:
            print(f"[{self.SOURCE_NAME}] Error making request: {e}")
            return None

    def _map_category(self, category_id: str) -> str:
        """Map Eventbrite category ID to our category"""
        return self.CATEGORY_MAP.get(category_id, "General")

    def _parse_price(self, event_data: Dict) -> tuple:
        """Extract price information from event data"""
        is_free = event_data.get("is_free", False)

        if is_free:
            return "Free", 0.0, True

        # Try to get minimum ticket price
        ticket_availability = event_data.get("ticket_availability", {})
        min_price = ticket_availability.get("minimum_ticket_price", {})

        if min_price and "display" in min_price:
            price_display = min_price["display"]
            price_value = min_price.get("major_value", 0.0)
            return price_display, float(price_value), False

        return "See Tickets", 0.0, False

    def _detect_multi_day(self, start_date: str, end_date: str, is_series: bool) -> tuple:
        """Detect if event is multi-day and calculate duration category"""
        try:
            start = datetime.fromisoformat(start_date.replace("Z", ""))
            end = datetime.fromisoformat(end_date.replace("Z", ""))
            days = (end - start).days

            is_multi = days > 0 or is_series

            # Duration category
            if days == 0:
                duration_cat = "single"
            elif days <= 7:
                duration_cat = "short"
            elif days <= 30:
                duration_cat = "medium"
            else:
                duration_cat = "long"

            return is_multi, duration_cat
        except:
            return False, "single"

    def scrape(self) -> List[ScrapedEvent]:
        """Scrape events from Eventbrite API"""
        events = []
        page = 1
        max_pages = 20  # Limit to prevent infinite loops

        print(f"[{self.SOURCE_NAME}] Starting scrape...")

        while page <= max_pages:
            print(f"[{self.SOURCE_NAME}] Fetching page {page}...")

            params = {
                "location.address": "Toronto, ON, Canada",
                "location.within": "50km",
                "expand": "venue,category,organizer",
                "page": page,
                "page_size": 50,
                "sort_by": "date",
            }

            data = self._make_request(self.SEARCH_ENDPOINT, params)

            if not data or "events" not in data:
                print(f"[{self.SOURCE_NAME}] No more events found")
                break

            page_events = data.get("events", [])
            if not page_events:
                print(f"[{self.SOURCE_NAME}] Empty page, stopping")
                break

            for event_data in page_events:
                try:
                    # Extract basic info
                    title = event_data.get("name", {}).get("text", "")
                    if not title or self.should_exclude(title):
                        continue

                    # Extract dates
                    start_data = event_data.get("start", {})
                    end_data = event_data.get("end", {})

                    start_date = start_data.get("utc", "")
                    end_date = end_data.get("utc", "")

                    if not start_date:
                        continue

                    # Ensure ISO format with Z suffix
                    if not start_date.endswith("Z"):
                        start_date += "Z"
                    if end_date and not end_date.endswith("Z"):
                        end_date += "Z"

                    # Multi-day detection
                    is_series = event_data.get("is_series", False)
                    is_multi, duration_cat = self._detect_multi_day(start_date, end_date, is_series)

                    # Extract description
                    description = event_data.get("description", {}).get("text", "")
                    if not description:
                        description = event_data.get("summary", "")

                    # Extract venue/location
                    venue_data = event_data.get("venue")
                    if venue_data:
                        venue_name = venue_data.get("name", "Toronto, ON")
                        address = venue_data.get("address", {}).get("localized_address_display", "")
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

                    # Extract category
                    category_id = event_data.get("category_id")
                    primary_category = self._map_category(category_id)

                    # Use categorize_event for tags and additional categories
                    categories, tags = self.categorize_event(title, description)

                    # Add primary category from Eventbrite
                    if primary_category != "General" and primary_category not in categories:
                        categories.insert(0, primary_category)

                    # Extract price
                    price_display, price_amount, is_free = self._parse_price(event_data)

                    # Extract URL
                    event_url = event_data.get("url", "")

                    # Extract image
                    logo_data = event_data.get("logo")
                    image_url = logo_data.get("original", {}).get("url", "") if logo_data else ""

                    # Extract organizer
                    organizer = event_data.get("organizer", {}).get("name", self.SOURCE_NAME)

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
                        description=description[:500] if description else "",  # Limit description length
                        categories=categories,
                        tags=tags,
                        status="UPCOMING",
                        is_multi_day=is_multi,
                        duration_category=duration_cat,
                        is_recurring=is_series,
                        recurrence_pattern="series" if is_series else None,
                    )

                    events.append(event)

                except Exception as e:
                    print(f"[{self.SOURCE_NAME}] Error parsing event: {e}")
                    continue

            # Check if there are more pages
            pagination = data.get("pagination", {})
            has_more = pagination.get("has_more_items", False)

            if not has_more:
                print(f"[{self.SOURCE_NAME}] No more pages")
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
