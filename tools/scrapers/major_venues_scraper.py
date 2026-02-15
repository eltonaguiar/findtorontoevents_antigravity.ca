#!/usr/bin/env python3
"""
Major Toronto Venues Events Scraper
Scrapes events from major Toronto cultural institutions:
  - Royal Ontario Museum (ROM) — rom.on.ca/whats-on
  - Art Gallery of Ontario (AGO) — ago.ca/events
  - TIFF Bell Lightbox — tiff.net/events
  - The Bentway — thebentway.ca
  - Evergreen Brick Works — evergreen.ca/whats-on

Each venue has its own subclass that can also be used independently.
"""
import re
import json
import time
from datetime import datetime
from typing import List, Optional, Dict, Set
from .base_scraper import BaseScraper, ScrapedEvent, TORONTO_VENUES


class _VenueScraperBase(BaseScraper):
    """Shared base for all venue scrapers."""

    VENUE_NAME = ""
    VENUE_DATA = {}
    PAGES = []

    def __init__(self):
        super().__init__()
        self.rate_limit_delay = 1.0
        self.seen_ids: Set[str] = set()

    # ── helpers ──

    def _iso(self, date_str: str) -> Optional[str]:
        """Parse a date string into ISO-8601 Z format."""
        if not date_str:
            return None
        date_str = date_str.strip()

        # Full ISO with optional TZ offset
        m = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", date_str)
        if m:
            return m.group(1) + "Z"

        # Date only
        m = re.match(r"(\d{4}-\d{2}-\d{2})$", date_str)
        if m:
            return m.group(1) + "T00:00:00Z"

        # Long month
        for fmt in ["%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y"]:
            try:
                return datetime.strptime(date_str, fmt).isoformat() + "Z"
            except ValueError:
                continue

        # No year
        for fmt in ["%B %d", "%b %d"]:
            try:
                dt = datetime.strptime(date_str, fmt).replace(year=datetime.now().year)
                return dt.isoformat() + "Z"
            except ValueError:
                continue

        return self.parse_date(date_str)

    def _jsonld_events(self, soup) -> List[Dict]:
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
                    if data.get("@type") == "ItemList":
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

    def _ld_to_event(self, ld: Dict, page_url: str) -> Optional[ScrapedEvent]:
        """Convert JSON-LD Event to ScrapedEvent."""
        title = (ld.get("name") or "").strip()
        start = ld.get("startDate", "")
        if not title or not start:
            return None

        parsed = self._iso(start)
        if not parsed:
            return None

        eid = self.generate_event_id(title, parsed, self.SOURCE_NAME)
        if eid in self.seen_ids:
            return None
        self.seen_ids.add(eid)

        end = ld.get("endDate", "")
        parsed_end = self._iso(end) if end else None
        is_multi = False
        if parsed and parsed_end:
            try:
                s = datetime.fromisoformat(parsed.replace("Z", ""))
                e = datetime.fromisoformat(parsed_end.replace("Z", ""))
                is_multi = (e - s).days > 0
            except (ValueError, TypeError):
                pass

        desc = (ld.get("description") or "")[:500]
        url = ld.get("url", page_url)
        if url and not url.startswith("http"):
            url = self.BASE_URL + url

        loc = ld.get("location") or {}
        venue = self.VENUE_NAME
        address = self.VENUE_DATA.get("address")
        lat = self.VENUE_DATA.get("lat")
        lng = self.VENUE_DATA.get("lng")
        if isinstance(loc, dict):
            v = loc.get("name", "")
            if v:
                venue = v
            addr = loc.get("address") or {}
            if isinstance(addr, dict) and addr.get("streetAddress"):
                address = ", ".join(
                    p for p in [
                        addr.get("streetAddress", ""),
                        addr.get("addressLocality", ""),
                        addr.get("addressRegion", ""),
                    ] if p
                )
            geo = loc.get("geo") or {}
            if isinstance(geo, dict):
                lat = geo.get("latitude") or lat
                lng = geo.get("longitude") or lng

        # Price
        offers = ld.get("offers") or {}
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

        categories, tags = self.categorize_event(title, desc)

        return ScrapedEvent(
            id=eid,
            title=title,
            date=parsed,
            end_date=parsed_end,
            location=venue,
            address=address,
            lat=float(lat) if lat else None,
            lng=float(lng) if lng else None,
            source=self.SOURCE_NAME,
            host=self.VENUE_NAME,
            url=url,
            price=price_display,
            price_amount=0.0,
            is_free=is_free,
            description=desc,
            categories=categories,
            tags=tags,
            status="UPCOMING",
            is_multi_day=is_multi,
        )

    def _html_cards(self, soup, page_url: str) -> List[ScrapedEvent]:
        events = []
        containers = (
            soup.find_all(class_=re.compile(r"event-card|event-item|card|listing", re.I))
            or soup.find_all("article", class_=re.compile(r"event|program", re.I))
            or soup.find_all("div", class_=re.compile(r"event-card|listing-card|card", re.I))
        )
        for card in containers:
            try:
                title_el = (
                    card.find(class_=re.compile(r"title|heading|name", re.I))
                    or card.find(["h2", "h3", "h4"])
                )
                if not title_el:
                    lnk = card.find("a", href=True)
                    if lnk:
                        title_el = lnk
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                if not title or len(title) < 3 or self.should_exclude(title):
                    continue

                link = card.find("a", href=True)
                ev_url = link["href"] if link else page_url
                if ev_url and not ev_url.startswith("http"):
                    ev_url = self.BASE_URL + ev_url

                date_el = card.find(class_=re.compile(r"date|time|when", re.I)) or card.find("time")
                dt_text = ""
                if date_el:
                    dt_text = date_el.get("datetime", "") or date_el.get_text(strip=True)
                parsed = self._iso(dt_text)
                if not parsed:
                    dm = re.search(r"(\w+ \d{1,2},?\s*\d{4})", card.get_text())
                    if dm:
                        parsed = self._iso(dm.group(1))
                if not parsed:
                    continue

                eid = self.generate_event_id(title, parsed, self.SOURCE_NAME)
                if eid in self.seen_ids:
                    continue
                self.seen_ids.add(eid)

                desc_el = card.find(class_=re.compile(r"desc|summary|excerpt", re.I))
                desc = desc_el.get_text(strip=True)[:500] if desc_el else ""

                categories, tags = self.categorize_event(title, desc)

                events.append(ScrapedEvent(
                    id=eid,
                    title=title,
                    date=parsed,
                    location=self.VENUE_NAME,
                    address=self.VENUE_DATA.get("address"),
                    lat=self.VENUE_DATA.get("lat"),
                    lng=self.VENUE_DATA.get("lng"),
                    source=self.SOURCE_NAME,
                    host=self.VENUE_NAME,
                    url=ev_url,
                    price="See Website",
                    price_amount=0.0,
                    is_free=False,
                    description=desc,
                    categories=categories,
                    tags=tags,
                    status="UPCOMING",
                ))
            except Exception:
                continue
        return events

    def scrape(self) -> List[ScrapedEvent]:
        all_events = []
        print(f"[{self.SOURCE_NAME}] Starting scrape...")
        for url in self.PAGES:
            print(f"[{self.SOURCE_NAME}] Fetching {url}...")
            soup = self.fetch_page(url)
            if not soup:
                continue
            for ld in self._jsonld_events(soup):
                ev = self._ld_to_event(ld, url)
                if ev:
                    all_events.append(ev)
            for ev in self._html_cards(soup, url):
                all_events.append(ev)
            time.sleep(self.rate_limit_delay)
        print(f"[{self.SOURCE_NAME}] Scraped {len(all_events)} events")
        return all_events


# ────────────────────────────────────────────────────────────────
# Individual venue scrapers
# ────────────────────────────────────────────────────────────────

class ROMScraper(_VenueScraperBase):
    """Royal Ontario Museum events."""
    SOURCE_NAME = "ROM"
    BASE_URL = "https://www.rom.on.ca"
    VENUE_NAME = "Royal Ontario Museum"
    VENUE_DATA = TORONTO_VENUES["rom"]
    PAGES = [
        "https://www.rom.on.ca/whats-on",
        "https://www.rom.on.ca/whats-on/events",
        "https://www.rom.on.ca/whats-on/exhibitions",
    ]


class AGOScraper(_VenueScraperBase):
    """Art Gallery of Ontario events."""
    SOURCE_NAME = "AGO"
    BASE_URL = "https://ago.ca"
    VENUE_NAME = "Art Gallery of Ontario"
    VENUE_DATA = TORONTO_VENUES["ago"]
    PAGES = [
        "https://ago.ca/events",
        "https://ago.ca/exhibitions",
    ]


class TIFFScraper(_VenueScraperBase):
    """TIFF Bell Lightbox events."""
    SOURCE_NAME = "TIFF"
    BASE_URL = "https://www.tiff.net"
    VENUE_NAME = "TIFF Bell Lightbox"
    VENUE_DATA = TORONTO_VENUES["tiff bell lightbox"]
    PAGES = [
        "https://www.tiff.net/events",
        "https://www.tiff.net/calendar",
    ]


class TheBentwayScraper(_VenueScraperBase):
    """The Bentway events (under the Gardiner)."""
    SOURCE_NAME = "The Bentway"
    BASE_URL = "https://www.thebentway.ca"
    VENUE_NAME = "The Bentway"
    VENUE_DATA = TORONTO_VENUES["the bentway"]
    PAGES = [
        "https://thebentway.ca/whats-on/",
        "https://thebentway.ca/",
    ]


class EvergreenBrickWorksScraper(_VenueScraperBase):
    """Evergreen Brick Works events."""
    SOURCE_NAME = "Evergreen Brick Works"
    BASE_URL = "https://www.evergreen.ca"
    VENUE_NAME = "Evergreen Brick Works"
    VENUE_DATA = TORONTO_VENUES["evergreen brick works"]
    PAGES = [
        "https://www.evergreen.ca/whats-on/",
    ]


class MajorVenuesScraper(BaseScraper):
    """
    Aggregator that runs all major venue scrapers at once.
    Used by the unified scraper to collect from all venues in a single call.
    """
    SOURCE_NAME = "Major Venues"

    def __init__(self):
        super().__init__()
        self.venue_scrapers = [
            ROMScraper(),
            AGOScraper(),
            TIFFScraper(),
            TheBentwayScraper(),
            EvergreenBrickWorksScraper(),
        ]

    def scrape(self) -> List[ScrapedEvent]:
        all_events = []
        for scraper in self.venue_scrapers:
            try:
                events = scraper.scrape()
                all_events.extend(events)
            except Exception as e:
                print(f"[{scraper.SOURCE_NAME}] Error: {e}")
        print(f"[{self.SOURCE_NAME}] Total from all venues: {len(all_events)}")
        return all_events


def scrape_major_venues() -> List[dict]:
    """Convenience function for standalone use."""
    scraper = MajorVenuesScraper()
    return scraper.scrape_to_json()


if __name__ == "__main__":
    events = scrape_major_venues()
    if events:
        print(json.dumps(events[:5], indent=2))
        print(f"\nTotal events: {len(events)}")
    else:
        print("No events found.")
