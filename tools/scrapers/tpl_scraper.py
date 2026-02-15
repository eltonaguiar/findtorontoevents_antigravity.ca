#!/usr/bin/env python3
"""
Toronto Public Library Events Scraper
Scrapes torontopubliclibrary.ca/programs-and-classes/ for free community events.

TPL hosts hundreds of free events weekly across 100 branches:
  - Author readings, book clubs
  - Kids & family programs
  - Technology workshops, coding classes
  - Language learning, cultural events
  - Film screenings, art exhibits
  - Community wellness programs
"""
import re
import json
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Set
from .base_scraper import BaseScraper, ScrapedEvent, TORONTO_VENUES


class TorontoPublicLibraryScraper(BaseScraper):
    """Scraper for Toronto Public Library events and programs."""

    SOURCE_NAME = "Toronto Public Library"
    BASE_URL = "https://www.torontopubliclibrary.ca"

    # TPL uses an events/programs listing system
    EVENTS_URLS = [
        f"{BASE_URL}/programs-and-classes/",
        f"{BASE_URL}/programs-and-classes/featured/",
    ]

    # TPL also has a calendar feed
    CALENDAR_URL = f"{BASE_URL}/events/"

    def __init__(self):
        super().__init__()
        self.rate_limit_delay = 1.0
        self.seen_ids: Set[str] = set()

    def _iso(self, date_str: str) -> Optional[str]:
        """Parse a date string into ISO format."""
        if not date_str:
            return None
        date_str = date_str.strip()

        # ISO formats
        m = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", date_str)
        if m:
            return m.group(1) + "Z"
        m = re.match(r"(\d{4}-\d{2}-\d{2})$", date_str)
        if m:
            return m.group(1) + "T00:00:00Z"

        # Spelled month
        for fmt in ["%B %d, %Y", "%b %d, %Y", "%B %d %Y"]:
            try:
                return datetime.strptime(date_str, fmt).isoformat() + "Z"
            except ValueError:
                continue

        # Without year
        for fmt in ["%B %d", "%b %d"]:
            try:
                dt = datetime.strptime(date_str, fmt).replace(year=datetime.now().year)
                return dt.isoformat() + "Z"
            except ValueError:
                continue

        # "Sat, Feb 15 at 2:00 PM"
        m = re.match(
            r"\w+,?\s*(\w+)\s+(\d{1,2})(?:\s+at\s+(\d{1,2}:\d{2})\s*(AM|PM))?",
            date_str, re.I
        )
        if m:
            month, day, time_str, ampm = m.groups()
            year = datetime.now().year
            try:
                if time_str and ampm:
                    dt = datetime.strptime(
                        f"{month} {day} {year} {time_str} {ampm}",
                        "%b %d %Y %I:%M %p"
                    )
                else:
                    dt = datetime.strptime(f"{month} {day} {year}", "%b %d %Y")
                return dt.isoformat() + "Z"
            except ValueError:
                pass

        return self.parse_date(date_str)

    def _extract_jsonld(self, soup) -> List[Dict]:
        events = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "{}")
                if isinstance(data, dict):
                    if data.get("@type") == "Event":
                        events.append(data)
                    for node in data.get("@graph", []):
                        if isinstance(node, dict) and node.get("@type") == "Event":
                            events.append(node)
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "Event":
                            events.append(item)
            except (json.JSONDecodeError, TypeError):
                continue
        return events

    def _parse_event_card(self, card, page_url: str) -> Optional[ScrapedEvent]:
        """Parse an HTML event/program card from TPL."""
        try:
            title_el = (
                card.find(class_=re.compile(r"title|heading|name|program-title", re.I))
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
            date_el = card.find(class_=re.compile(r"date|time|when|schedule", re.I)) or card.find("time")
            date_text = ""
            if date_el:
                date_text = date_el.get("datetime", "") or date_el.get_text(strip=True)

            parsed_date = self._iso(date_text)
            if not parsed_date:
                text = card.get_text()
                dm = re.search(r"(\w+ \d{1,2},?\s*\d{4})", text)
                if dm:
                    parsed_date = self._iso(dm.group(1))

            if not parsed_date:
                return None

            # Location (library branch)
            loc_el = card.find(class_=re.compile(r"location|branch|venue|library", re.I))
            branch = loc_el.get_text(strip=True) if loc_el else "Toronto Public Library"
            loc_info = self.enhance_location(branch, title)

            # Description
            desc_el = card.find(class_=re.compile(r"desc|summary|excerpt|body", re.I))
            description = desc_el.get_text(strip=True)[:500] if desc_el else ""

            # Age/audience
            age_el = card.find(class_=re.compile(r"age|audience|for", re.I))
            if age_el:
                age_text = age_el.get_text(strip=True)
                if age_text and not description:
                    description = f"For: {age_text}"

            categories, tags = self.categorize_event(title, description)

            # TPL events are typically free
            event_id = self.generate_event_id(title, parsed_date, self.SOURCE_NAME)
            if event_id in self.seen_ids:
                return None
            self.seen_ids.add(event_id)

            return ScrapedEvent(
                id=event_id,
                title=title,
                date=parsed_date,
                location=loc_info.get("location", branch),
                address=loc_info.get("address"),
                lat=loc_info.get("lat"),
                lng=loc_info.get("lng"),
                source=self.SOURCE_NAME,
                host="Toronto Public Library",
                url=event_url,
                price="Free",
                price_amount=0.0,
                is_free=True,
                description=description,
                categories=categories,
                tags=tags,
                status="UPCOMING",
            )
        except Exception as e:
            print(f"[{self.SOURCE_NAME}] Error parsing card: {e}")
            return None

    def scrape(self) -> List[ScrapedEvent]:
        """Scrape events from Toronto Public Library."""
        all_events = []

        print(f"[{self.SOURCE_NAME}] Starting scrape...")

        for url in self.EVENTS_URLS:
            print(f"[{self.SOURCE_NAME}] Fetching {url}...")
            soup = self.fetch_page(url)
            if not soup:
                continue

            # JSON-LD events
            for ld in self._extract_jsonld(soup):
                title = ld.get("name", "")
                start = ld.get("startDate", "")
                if not title or not start:
                    continue
                parsed = self._iso(start)
                if not parsed:
                    continue
                eid = self.generate_event_id(title, parsed, self.SOURCE_NAME)
                if eid in self.seen_ids:
                    continue
                self.seen_ids.add(eid)

                desc = (ld.get("description") or "")[:500]
                ev_url = ld.get("url", url)
                if ev_url and not ev_url.startswith("http"):
                    ev_url = self.BASE_URL + ev_url

                loc = ld.get("location") or {}
                venue = "Toronto Public Library"
                address = None
                lat = None
                lng = None
                if isinstance(loc, dict):
                    venue = loc.get("name", venue)
                    addr = loc.get("address") or {}
                    if isinstance(addr, dict) and addr.get("streetAddress"):
                        address = ", ".join(
                            p for p in [addr.get("streetAddress"), addr.get("addressLocality"), "ON"] if p
                        )
                    geo = loc.get("geo") or {}
                    if isinstance(geo, dict):
                        lat = geo.get("latitude")
                        lng = geo.get("longitude")

                categories, tags = self.categorize_event(title, desc)

                all_events.append(ScrapedEvent(
                    id=eid,
                    title=title,
                    date=parsed,
                    location=venue,
                    address=address,
                    lat=float(lat) if lat else None,
                    lng=float(lng) if lng else None,
                    source=self.SOURCE_NAME,
                    host="Toronto Public Library",
                    url=ev_url,
                    price="Free",
                    price_amount=0.0,
                    is_free=True,
                    description=desc,
                    categories=categories,
                    tags=tags,
                    status="UPCOMING",
                ))

            # HTML cards
            containers = (
                soup.find_all(class_=re.compile(r"program-card|event-card|event-item|listing", re.I))
                or soup.find_all("article", class_=re.compile(r"program|event", re.I))
                or soup.find_all("div", class_=re.compile(r"program-card|event-card|card", re.I))
                or soup.find_all("li", class_=re.compile(r"program|event", re.I))
            )
            for card in containers:
                ev = self._parse_event_card(card, url)
                if ev:
                    all_events.append(ev)

            time.sleep(self.rate_limit_delay)

        print(f"[{self.SOURCE_NAME}] Scraped {len(all_events)} events")
        return all_events


def scrape_tpl() -> List[dict]:
    """Convenience function for standalone use."""
    scraper = TorontoPublicLibraryScraper()
    return scraper.scrape_to_json()


if __name__ == "__main__":
    events = scrape_tpl()
    if events:
        print(json.dumps(events[:3], indent=2))
        print(f"\nTotal events: {len(events)}")
    else:
        print("No events found.")
