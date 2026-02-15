#!/usr/bin/env python3
"""
toronto.com Events Scraper
Scrapes toronto.com/events/ for upcoming Toronto events.

toronto.com is an official city-affiliated event listing platform that covers
arts/music, attractions, community, festivals, food & drink, lifestyle, and sports.
"""
import re
import json
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from .base_scraper import BaseScraper, ScrapedEvent


class TorontoComScraper(BaseScraper):
    """Scraper for toronto.com events."""

    SOURCE_NAME = "toronto.com"
    BASE_URL = "https://www.toronto.com"

    EVENTS_URLS = [
        f"{BASE_URL}/events/",
        f"{BASE_URL}/events/events-this-weekend/",
        f"{BASE_URL}/events/arts-and-music/",
        f"{BASE_URL}/events/community/",
        f"{BASE_URL}/events/festivals-and-fairs/",
        f"{BASE_URL}/events/food-and-drink/",
        f"{BASE_URL}/events/sports-and-outdoors/",
    ]

    def __init__(self):
        super().__init__()
        self.rate_limit_delay = 1.0
        self.seen_ids = set()

    def _extract_jsonld(self, soup) -> List[Dict]:
        """Extract Event schema from JSON-LD."""
        events = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "{}")
                if isinstance(data, dict):
                    if data.get("@type") == "Event":
                        events.append(data)
                    elif "@graph" in data:
                        for node in data["@graph"]:
                            if isinstance(node, dict) and node.get("@type") == "Event":
                                events.append(node)
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

    def _parse_tc_date(self, date_str: str) -> Optional[str]:
        """Parse toronto.com date formats."""
        if not date_str:
            return None
        date_str = date_str.strip()

        # ISO
        iso_m = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", date_str)
        if iso_m:
            return iso_m.group(1) + "Z"

        iso_d = re.match(r"(\d{4}-\d{2}-\d{2})$", date_str)
        if iso_d:
            return iso_d.group(1) + "T00:00:00Z"

        # "February 15, 2026" etc.
        for fmt in ["%B %d, %Y", "%b %d, %Y", "%B %d %Y"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.isoformat() + "Z"
            except ValueError:
                continue

        # "Feb 15" (no year)
        for fmt in ["%B %d", "%b %d"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                dt = dt.replace(year=datetime.now().year)
                return dt.isoformat() + "Z"
            except ValueError:
                continue

        return self.parse_date(date_str)

    def _parse_event_card(self, card, page_url: str) -> Optional[ScrapedEvent]:
        """Parse an HTML event card."""
        try:
            title_el = (
                card.find(class_=re.compile(r"title|heading|name", re.I))
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
            link = card.find("a", href=True)
            event_url = link["href"] if link else page_url
            if event_url and not event_url.startswith("http"):
                event_url = self.BASE_URL + event_url

            # Date
            date_el = (
                card.find(class_=re.compile(r"date|time|when", re.I))
                or card.find("time")
            )
            date_text = ""
            if date_el:
                date_text = date_el.get("datetime", "") or date_el.get_text(strip=True)

            parsed_date = self._parse_tc_date(date_text)
            if not parsed_date:
                text = card.get_text()
                date_match = re.search(r"(\w+ \d{1,2},?\s*\d{4})", text)
                if date_match:
                    parsed_date = self._parse_tc_date(date_match.group(1))

            if not parsed_date:
                return None

            # Location
            loc_el = card.find(class_=re.compile(r"location|venue|place|address", re.I))
            location = loc_el.get_text(strip=True) if loc_el else "Toronto, ON"
            loc_info = self.enhance_location(location, title)

            # Description
            desc_el = card.find(class_=re.compile(r"desc|summary|excerpt|body", re.I))
            description = desc_el.get_text(strip=True)[:500] if desc_el else ""

            # Price
            price_el = card.find(class_=re.compile(r"price|cost|ticket", re.I))
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
                host="toronto.com",
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

    def scrape(self) -> List[ScrapedEvent]:
        """Scrape events from toronto.com."""
        all_events = []

        print(f"[{self.SOURCE_NAME}] Starting scrape...")

        for url in self.EVENTS_URLS:
            print(f"[{self.SOURCE_NAME}] Fetching {url}...")
            soup = self.fetch_page(url)
            if not soup:
                continue

            # JSON-LD
            for ev_data in self._extract_jsonld(soup):
                title = ev_data.get("name", "")
                start = ev_data.get("startDate", "")
                end = ev_data.get("endDate", "")

                if not title or not start:
                    continue

                parsed_date = self._parse_tc_date(start)
                parsed_end = self._parse_tc_date(end) if end else None
                if not parsed_date:
                    continue

                event_id = self.generate_event_id(title, parsed_date, self.SOURCE_NAME)
                if event_id in self.seen_ids:
                    continue
                self.seen_ids.add(event_id)

                loc = ev_data.get("location") or {}
                venue = "Toronto, ON"
                address = None
                lat = None
                lng = None
                if isinstance(loc, dict):
                    venue = loc.get("name", "Toronto, ON")
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

                description = (ev_data.get("description") or "")[:500]
                event_url = ev_data.get("url", url)

                categories, tags = self.categorize_event(title, description)

                is_multi = False
                if parsed_date and parsed_end:
                    try:
                        s = datetime.fromisoformat(parsed_date.replace("Z", ""))
                        e = datetime.fromisoformat(parsed_end.replace("Z", ""))
                        is_multi = (e - s).days > 0
                    except (ValueError, TypeError):
                        pass

                all_events.append(ScrapedEvent(
                    id=event_id,
                    title=title,
                    date=parsed_date,
                    end_date=parsed_end,
                    location=loc_info.get("location", venue),
                    address=address or loc_info.get("address"),
                    lat=float(lat) if lat else loc_info.get("lat"),
                    lng=float(lng) if lng else loc_info.get("lng"),
                    source=self.SOURCE_NAME,
                    host="toronto.com",
                    url=event_url,
                    price="See Website",
                    price_amount=0.0,
                    is_free=False,
                    description=description,
                    categories=categories,
                    tags=tags,
                    status="UPCOMING",
                    is_multi_day=is_multi,
                ))

            # HTML cards
            containers = (
                soup.find_all(class_=re.compile(r"event-card|event-item|listing-card", re.I))
                or soup.find_all("article", class_=re.compile(r"event|listing", re.I))
                or soup.find_all("div", class_=re.compile(r"event-card|card|listing", re.I))
            )
            for card in containers:
                ev = self._parse_event_card(card, url)
                if ev:
                    all_events.append(ev)

            time.sleep(self.rate_limit_delay)

        print(f"[{self.SOURCE_NAME}] Scraped {len(all_events)} events")
        return all_events


def scrape_toronto_com() -> List[dict]:
    """Convenience function for standalone use."""
    scraper = TorontoComScraper()
    return scraper.scrape_to_json()


if __name__ == "__main__":
    events = scrape_toronto_com()
    if events:
        print(json.dumps(events[:3], indent=2))
        print(f"\nTotal events: {len(events)}")
    else:
        print("No events found.")
