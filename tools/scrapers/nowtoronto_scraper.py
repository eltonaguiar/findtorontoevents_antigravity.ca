#!/usr/bin/env python3
"""
NOW Toronto Events Scraper
Scrapes nowtoronto.com/events/ for upcoming Toronto events.

NOW Toronto is one of the city's oldest and most comprehensive event
listing platforms, using The Events Calendar (Tribe Events) WordPress plugin.
It has structured date-based URLs and category filtering.
"""
import re
import json
import time
import html as html_mod
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from .base_scraper import BaseScraper, ScrapedEvent


class NOWTorontoScraper(BaseScraper):
    """Scraper for NOW Toronto events calendar."""

    SOURCE_NAME = "NOW Toronto"
    BASE_URL = "https://nowtoronto.com"

    # Tribe Events uses date-based URLs
    def _build_day_url(self, date: datetime) -> str:
        return f"{self.BASE_URL}/events/{date.strftime('%Y-%m-%d')}/"

    # Category slugs for targeted scraping
    CATEGORY_SLUGS = [
        "event-music",
        "event-nightlife",
        "event-arts",
        "event-food-drink",
        "event-community",
        "event-comedy",
        "event-family",
        "event-sports",
        "event-film",
    ]

    def __init__(self):
        super().__init__()
        self.rate_limit_delay = 1.0
        self.seen_ids = set()

    def _extract_jsonld_events(self, soup) -> List[Dict]:
        """Extract Event schema from JSON-LD."""
        events = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "{}")
                if isinstance(data, dict):
                    if data.get("@type") == "Event":
                        events.append(data)
                    elif data.get("@type") == "ItemList":
                        for item in data.get("itemListElement", []):
                            ev = item.get("item", item)
                            if isinstance(ev, dict) and ev.get("@type") == "Event":
                                events.append(ev)
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "Event":
                            events.append(item)
            except (json.JSONDecodeError, TypeError):
                continue
        return events

    def _parse_now_date(self, date_str: str) -> Optional[str]:
        """Parse NOW Toronto date formats."""
        if not date_str:
            return None
        date_str = date_str.strip()

        # ISO with timezone offset: "2026-02-15T19:00:00-05:00"
        iso_m = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", date_str)
        if iso_m:
            return iso_m.group(1) + "Z"

        # ISO date only
        iso_d = re.match(r"(\d{4}-\d{2}-\d{2})$", date_str)
        if iso_d:
            return iso_d.group(1) + "T00:00:00Z"

        # "February 15, 2026 @ 7:00 pm" (Tribe Events format)
        m = re.match(
            r"(\w+)\s+(\d{1,2}),?\s*(\d{4})(?:\s*@?\s*(\d{1,2}:\d{2})\s*(am|pm))?",
            date_str,
            re.I,
        )
        if m:
            month, day, year, time_str, ampm = m.groups()
            try:
                if time_str and ampm:
                    dt = datetime.strptime(
                        f"{month} {day} {year} {time_str} {ampm}",
                        "%B %d %Y %I:%M %p",
                    )
                else:
                    dt = datetime.strptime(f"{month} {day} {year}", "%B %d %Y")
                return dt.isoformat() + "Z"
            except ValueError:
                pass

        # Fallback
        return self.parse_date(date_str)

    def _parse_html_event_card(self, card, page_url: str) -> Optional[ScrapedEvent]:
        """Parse a Tribe Events calendar card from NOW Toronto HTML."""
        try:
            # Title
            title_el = (
                card.find(class_=re.compile(r"tribe-events-.*title|tribe-event-title", re.I))
                or card.find(["h2", "h3", "h4"])
            )
            if not title_el:
                link = card.find("a", href=True)
                if link:
                    title_el = link
            if not title_el:
                return None

            title = title_el.get_text(strip=True)
            if not title or len(title) < 3 or self.should_exclude(title):
                return None

            # URL
            link = title_el.find("a", href=True) or card.find("a", href=True)
            event_url = link["href"] if link else page_url
            if event_url and not event_url.startswith("http"):
                event_url = self.BASE_URL + event_url

            # Date
            date_el = (
                card.find(class_=re.compile(r"tribe-event.*date|tribe-events.*datetime", re.I))
                or card.find("time")
                or card.find("abbr", class_=re.compile(r"tribe-events-abbr"))
            )
            date_text = ""
            if date_el:
                date_text = date_el.get("datetime", "") or date_el.get("title", "") or date_el.get_text(strip=True)

            parsed_date = self._parse_now_date(date_text)
            if not parsed_date:
                # Try text from the whole card
                text = card.get_text()
                date_match = re.search(r"(\w+ \d{1,2},?\s*\d{4})", text)
                if date_match:
                    parsed_date = self._parse_now_date(date_match.group(1))

            if not parsed_date:
                return None

            # Location/Venue
            venue_el = card.find(class_=re.compile(r"tribe-venue|venue|location", re.I))
            venue_name = venue_el.get_text(strip=True) if venue_el else "Toronto, ON"
            loc_info = self.enhance_location(venue_name, title)

            # Description
            desc_el = card.find(class_=re.compile(r"tribe-events.*description|excerpt|desc", re.I))
            description = desc_el.get_text(strip=True)[:500] if desc_el else ""

            # Price
            price_el = card.find(class_=re.compile(r"tribe-events-.*cost|price|ticket", re.I))
            price_text = price_el.get_text(strip=True) if price_el else ""
            is_free = "free" in price_text.lower() if price_text else False
            price_display = "Free" if is_free else (price_text or "See Website")

            categories, tags = self.categorize_event(title, description)
            event_id = self.generate_event_id(title, parsed_date, self.SOURCE_NAME)

            if event_id in self.seen_ids:
                return None
            self.seen_ids.add(event_id)

            return ScrapedEvent(
                id=event_id,
                title=title,
                date=parsed_date,
                location=loc_info["location"],
                address=loc_info.get("address"),
                lat=loc_info.get("lat"),
                lng=loc_info.get("lng"),
                source=self.SOURCE_NAME,
                host="NOW Toronto",
                url=event_url,
                price=price_display,
                price_amount=0.0,
                is_free=is_free,
                description=description,
                categories=categories,
                tags=tags,
                status="UPCOMING",
            )
        except Exception as e:
            print(f"[{self.SOURCE_NAME}] Error parsing card: {e}")
            return None

    def _scrape_day_page(self, url: str) -> List[ScrapedEvent]:
        """Scrape a single day's event listing page."""
        events = []
        soup = self.fetch_page(url)
        if not soup:
            return events

        # 1) JSON-LD
        for ev_data in self._extract_jsonld_events(soup):
            title = html_mod.unescape(ev_data.get("name", ""))
            start = ev_data.get("startDate", "")
            end = ev_data.get("endDate", "")

            if not title or not start:
                continue

            parsed_date = self._parse_now_date(start)
            parsed_end = self._parse_now_date(end) if end else None
            if not parsed_date:
                continue

            event_id = self.generate_event_id(title, parsed_date, self.SOURCE_NAME)
            if event_id in self.seen_ids:
                continue
            self.seen_ids.add(event_id)

            # Location
            loc = ev_data.get("location") or {}
            venue = "Toronto, ON"
            address = None
            lat = None
            lng = None
            if isinstance(loc, dict):
                venue = html_mod.unescape(loc.get("name", "Toronto, ON"))
                addr = loc.get("address") or {}
                if isinstance(addr, dict):
                    street = addr.get("streetAddress", "")
                    city = addr.get("addressLocality", "")
                    parts = [p for p in [street, city, "ON"] if p]
                    address = ", ".join(parts) if street else None
                geo = loc.get("geo") or {}
                if isinstance(geo, dict):
                    lat = geo.get("latitude")
                    lng = geo.get("longitude")

            loc_info = self.enhance_location(venue, title)
            if loc_info.get("lat") and not lat:
                lat = loc_info["lat"]
                lng = loc_info["lng"]
            if loc_info.get("address") and not address:
                address = loc_info["address"]

            description = html_mod.unescape((ev_data.get("description") or "")[:500])
            event_url = ev_data.get("url", url)

            # Price
            offers = ev_data.get("offers") or {}
            if isinstance(offers, list) and offers:
                offers = offers[0]
            is_free = False
            price_display = "See Website"
            if isinstance(offers, dict):
                try:
                    pv = float(offers.get("price", 0))
                    if pv == 0:
                        is_free = True
                        price_display = "Free"
                    else:
                        price_display = f"CAD ${pv:.2f}"
                except (ValueError, TypeError):
                    pass

            categories, tags = self.categorize_event(title, description)

            events.append(ScrapedEvent(
                id=event_id,
                title=title,
                date=parsed_date,
                end_date=parsed_end if parsed_end else None,
                location=loc_info.get("location", venue),
                address=address,
                lat=float(lat) if lat else None,
                lng=float(lng) if lng else None,
                source=self.SOURCE_NAME,
                host="NOW Toronto",
                url=event_url,
                price=price_display,
                price_amount=0.0,
                is_free=is_free,
                description=description,
                categories=categories,
                tags=tags,
                status="UPCOMING",
            ))

        # 2) HTML cards (Tribe Events structure)
        containers = (
            soup.find_all(class_=re.compile(r"tribe-events-calendar-list__event|tribe_events.*event", re.I))
            or soup.find_all("article", class_=re.compile(r"tribe|event", re.I))
            or soup.find_all("div", class_=re.compile(r"type-tribe_events|event-card", re.I))
        )
        for card in containers:
            ev = self._parse_html_event_card(card, url)
            if ev:
                events.append(ev)

        return events

    def scrape(self) -> List[ScrapedEvent]:
        """Scrape events from NOW Toronto for today + next 7 days."""
        all_events = []

        print(f"[{self.SOURCE_NAME}] Starting scrape...")

        # Scrape today + next 7 days
        today = datetime.now()
        for day_offset in range(8):
            target_date = today + timedelta(days=day_offset)
            url = self._build_day_url(target_date)
            label = target_date.strftime("%b %d")

            print(f"[{self.SOURCE_NAME}] Fetching events for {label}...")
            events = self._scrape_day_page(url)
            all_events.extend(events)
            print(f"[{self.SOURCE_NAME}]   {len(events)} events for {label}")

            time.sleep(self.rate_limit_delay)

        print(f"[{self.SOURCE_NAME}] Scraped {len(all_events)} events total")
        return all_events


def scrape_nowtoronto() -> List[dict]:
    """Convenience function for standalone use."""
    scraper = NOWTorontoScraper()
    return scraper.scrape_to_json()


if __name__ == "__main__":
    events = scrape_nowtoronto()
    if events:
        print(json.dumps(events[:3], indent=2))
        print(f"\nTotal events: {len(events)}")
    else:
        print("No events found.")
