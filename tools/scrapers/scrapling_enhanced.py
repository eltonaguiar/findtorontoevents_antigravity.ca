#!/usr/bin/env python3
"""
Enhanced Toronto event scrapers using Scrapling for better extraction.

Targets NEW sources not in the current pipeline:
  1. Scotiabank Arena (Raptors, Leafs, concerts)
  2. Rogers Centre / Rogers Stadium (Blue Jays, concerts, TFC at BMO)
  3. Massey Hall / Roy Thomson Hall (concerts, classical)
  4. Casa Loma (heritage site events)
  5. Ontario Science Centre (family events)
  6. University of Toronto (public lectures, exhibitions)
  7. TO Live (Meridian Hall, St Lawrence Centre, Civic Theatres)
  8. Toronto Botanical Garden / Edwards Gardens

Uses Scrapling's Fetcher for TLS-fingerprinted requests + fast parsing.
Falls back to requests + BeautifulSoup if Scrapling unavailable.
"""
import json
import re
import time
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict

import requests

try:
    from scrapling import Fetcher
    HAS_SCRAPLING = True
except ImportError:
    HAS_SCRAPLING = False

from .base_scraper import BaseScraper, ScrapedEvent

logger = logging.getLogger(__name__)

# Rate limit between requests (seconds)
DEFAULT_DELAY = 1.0

# Garbage titles to filter out (navigation elements, etc.)
GARBAGE_TITLES = {
    "skip to content", "skip to main content", "skip to navigation",
    "menu", "search", "home", "back to top", "close", "open menu",
    "toggle navigation", "loading", "please wait", "cookie policy",
    "accept cookies", "privacy policy", "terms of service",
}


class ScraplingBaseScraper(BaseScraper):
    """Enhanced base scraper using Scrapling's Fetcher for TLS-fingerprinted requests."""

    DELAY = DEFAULT_DELAY

    def __init__(self):
        super().__init__()
        if HAS_SCRAPLING:
            self._fetcher = Fetcher(auto_match=False)

    def _is_garbage_title(self, title: str) -> bool:
        """Filter out navigation elements, generic labels, etc."""
        t = title.strip().lower()
        if t in GARBAGE_TITLES:
            return True
        if len(t) < 4:
            return True
        # All-caps single words like "OPEN" or nav items
        if len(t.split()) == 1 and len(t) < 10:
            return True
        return False

    def fetch_and_parse(self, url: str):
        """Fetch URL and return parsed page (Scrapling or BS4 fallback)."""
        try:
            if HAS_SCRAPLING:
                page = self._fetcher.get(url, timeout=30)
                return page  # Scrapling Adaptor with .css() etc.
            else:
                resp = self.session.get(url, timeout=30)
                resp.raise_for_status()
                from bs4 import BeautifulSoup
                return BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            logger.warning(f"[{self.SOURCE_NAME}] Error fetching {url}: {e}")
            return None

    def extract_jsonld(self, page) -> List[dict]:
        """Extract JSON-LD Event data from page."""
        events = []
        if page is None:
            return events

        if HAS_SCRAPLING:
            scripts = page.css('script[type="application/ld+json"]')
            for s in scripts:
                try:
                    data = json.loads(s.text)
                    events.extend(self._flatten_jsonld(data))
                except (json.JSONDecodeError, TypeError):
                    continue
        else:
            scripts = page.find_all("script", {"type": "application/ld+json"})
            for s in scripts:
                try:
                    data = json.loads(s.string or "")
                    events.extend(self._flatten_jsonld(data))
                except (json.JSONDecodeError, TypeError):
                    continue
        return events

    def _flatten_jsonld(self, data) -> List[dict]:
        """Flatten JSON-LD into list of Event dicts."""
        results = []
        if isinstance(data, list):
            for item in data:
                results.extend(self._flatten_jsonld(item))
        elif isinstance(data, dict):
            typ = data.get("@type", "")
            if isinstance(typ, list):
                typ = typ[0] if typ else ""
            if typ == "Event":
                results.append(data)
            elif typ == "ItemList":
                for item in data.get("itemListElement", []):
                    if isinstance(item, dict):
                        inner = item.get("item", item)
                        results.extend(self._flatten_jsonld(inner))
            elif "@graph" in data:
                results.extend(self._flatten_jsonld(data["@graph"]))
        return results

    def jsonld_to_event(self, ld: dict, source: str, fallback_url: str = "") -> Optional[ScrapedEvent]:
        """Convert a JSON-LD Event dict to ScrapedEvent."""
        title = ld.get("name", "").strip()
        if not title or self.should_exclude(title):
            return None

        start = ld.get("startDate", "")
        if not start:
            return None
        date_iso = self._normalize_date(start)
        if not date_iso:
            return None

        end = ld.get("endDate", "")
        end_iso = self._normalize_date(end) if end else None

        # Location
        loc = ld.get("location", {})
        if isinstance(loc, dict):
            venue_name = loc.get("name", "Toronto, ON")
            address_obj = loc.get("address", {})
            if isinstance(address_obj, dict):
                address = address_obj.get("streetAddress", "")
            elif isinstance(address_obj, str):
                address = address_obj
            else:
                address = ""
            geo = loc.get("geo", {})
            lat = float(geo.get("latitude", 0)) if geo else None
            lng = float(geo.get("longitude", 0)) if geo else None
        elif isinstance(loc, str):
            venue_name = loc
            address = ""
            lat = lng = None
        else:
            venue_name = "Toronto, ON"
            address = ""
            lat = lng = None

        # Price
        offers = ld.get("offers", {})
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        price_val = offers.get("price", 0)
        try:
            price_amount = float(price_val)
        except (ValueError, TypeError):
            price_amount = 0.0
        is_free = price_amount == 0 or str(offers.get("availability", "")).lower() == "free"
        price_str = "Free" if is_free else f"${price_amount:.2f}"

        # Image
        image = ld.get("image", "")
        if isinstance(image, list):
            image = image[0] if image else ""
        if isinstance(image, dict):
            image = image.get("url", "")

        # Description
        desc = ld.get("description", "")[:500]

        # URL
        url = ld.get("url", fallback_url)

        # Organizer
        org = ld.get("organizer", {})
        host = org.get("name", "") if isinstance(org, dict) else str(org)

        # Multi-day detection
        is_multi = False
        duration_cat = "single"
        if end_iso and date_iso:
            try:
                s = datetime.fromisoformat(date_iso.replace("Z", "+00:00"))
                e = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
                hours = (e - s).total_seconds() / 3600
                if hours >= 18:
                    is_multi = True
                    days = hours / 24
                    if days <= 7:
                        duration_cat = "short"
                    elif days <= 30:
                        duration_cat = "medium"
                    else:
                        duration_cat = "long"
            except Exception:
                pass

        eid = self.generate_event_id(title, date_iso, source)
        cats, tags = self.categorize_event(title, desc)

        return ScrapedEvent(
            id=eid,
            title=title,
            date=date_iso,
            end_date=end_iso,
            location=venue_name,
            address=address,
            lat=lat,
            lng=lng,
            source=source,
            host=host,
            url=url,
            price=price_str,
            price_amount=price_amount,
            is_free=is_free,
            description=desc,
            categories=cats,
            tags=tags,
            status="UPCOMING",
            is_multi_day=is_multi,
            duration_category=duration_cat,
            image=image,
        )

    def _normalize_date(self, date_str: str) -> Optional[str]:
        """Normalize various date strings to ISO-8601.

        Uses noon UTC (T12:00:00Z) for date-only values to avoid the
        midnight-UTC timezone bug (T00:00:00Z = previous day in EDT).
        """
        if not date_str:
            return None
        date_str = date_str.strip()
        # Already ISO
        if re.match(r"\d{4}-\d{2}-\d{2}T", date_str):
            if not date_str.endswith("Z") and "+" not in date_str[10:]:
                date_str += "Z"
            # Rewrite bare midnight UTC → noon UTC for calendar-day safety
            if date_str.endswith("T00:00:00Z"):
                date_str = date_str.replace("T00:00:00Z", "T12:00:00Z")
            return date_str
        # Try common formats
        for fmt in ["%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y",
                    "%A, %B %d, %Y", "%A, %b %d, %Y"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                # Date-only → noon UTC so Toronto stays on same calendar day
                dt = dt.replace(hour=12, minute=0, second=0)
                return dt.isoformat() + "Z"
            except ValueError:
                continue
        # Formats with actual time component
        for fmt in ["%B %d, %Y %I:%M %p", "%b %d, %Y %I:%M %p"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.isoformat() + "Z"
            except ValueError:
                continue
        return None


# ─── Individual Scrapers ─────────────────────────────────────────────

class ScotiabankArenaScraper(ScraplingBaseScraper):
    """Scotiabank Arena — Leafs, Raptors, concerts, shows.

    Uses Ticketmaster's venue page as fallback since the arena site
    requires JavaScript rendering for event cards.
    """
    SOURCE_NAME = "Scotiabank Arena"
    BASE_URL = "https://www.scotiabankarena.com"
    VENUE_LAT = 43.6435
    VENUE_LNG = -79.3791
    VENUE_ADDRESS = "40 Bay St, Toronto, ON M5J 2X2"

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        urls = [
            f"{self.BASE_URL}/events",
            # Ticketmaster venue page has better JSON-LD for events
            "https://www.ticketmaster.ca/scotiabank-arena-tickets-toronto/venue/131157",
        ]
        for url in urls:
            page = self.fetch_and_parse(url)
            if not page:
                continue

            # Try JSON-LD first
            ld_events = self.extract_jsonld(page)
            for ld in ld_events:
                ev = self.jsonld_to_event(ld, self.SOURCE_NAME, url)
                if ev:
                    ev.lat = self.VENUE_LAT
                    ev.lng = self.VENUE_LNG
                    ev.address = self.VENUE_ADDRESS
                    events.append(ev)

            # HTML fallback — look for event cards/links
            if not events:
                events.extend(self._parse_html_cards(page, url))

            time.sleep(self.DELAY)

        logger.info(f"[{self.SOURCE_NAME}] Scraped {len(events)} events")
        return events

    def _parse_html_cards(self, page, base_url: str) -> List[ScrapedEvent]:
        """Parse HTML event cards from Scotiabank Arena."""
        results = []
        if HAS_SCRAPLING:
            cards = (page.css('.event-card') or page.css('.event-item') or
                     page.css('[class*="event"]') or page.css('article'))
        else:
            cards = (page.select('.event-card') or page.select('.event-item') or
                     page.select('[class*="event"]') or page.select('article'))

        for card in cards[:50]:
            try:
                if HAS_SCRAPLING:
                    title_el = card.css_first('h2, h3, h4, .event-title, .title, a')
                    date_el = card.css_first('.event-date, .date, time, [datetime]')
                    link_el = card.css_first('a[href]')
                    img_el = card.css_first('img[src]')
                else:
                    title_el = card.select_one('h2, h3, h4, .event-title, .title, a')
                    date_el = card.select_one('.event-date, .date, time, [datetime]')
                    link_el = card.select_one('a[href]')
                    img_el = card.select_one('img[src]')

                if not title_el:
                    continue

                title = title_el.text.strip() if hasattr(title_el, 'text') else str(title_el.string or "").strip()
                if not title or self._is_garbage_title(title) or self.should_exclude(title):
                    continue

                # Date
                date_str = ""
                if date_el:
                    date_str = (date_el.attrib.get("datetime", "") if HAS_SCRAPLING
                                else date_el.get("datetime", ""))
                    if not date_str:
                        date_str = date_el.text.strip() if hasattr(date_el, 'text') else ""
                date_iso = self._normalize_date(date_str) if date_str else None
                if not date_iso:
                    # Skip events without dates
                    continue

                # URL
                href = ""
                if link_el:
                    href = (link_el.attrib.get("href", "") if HAS_SCRAPLING
                            else link_el.get("href", ""))
                    if href and not href.startswith("http"):
                        href = self.BASE_URL + href

                # Image
                img = ""
                if img_el:
                    img = (img_el.attrib.get("src", "") if HAS_SCRAPLING
                           else img_el.get("src", ""))

                eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)
                cats, tags = self.categorize_event(title, "")

                results.append(ScrapedEvent(
                    id=eid,
                    title=title,
                    date=date_iso,
                    location=self.SOURCE_NAME,
                    address=self.VENUE_ADDRESS,
                    lat=self.VENUE_LAT,
                    lng=self.VENUE_LNG,
                    source=self.SOURCE_NAME,
                    url=href or base_url,
                    categories=cats,
                    tags=tags,
                    image=img,
                ))
            except Exception as e:
                logger.debug(f"[{self.SOURCE_NAME}] Card parse error: {e}")
                continue
        return results


class MasseyHallScraper(ScraplingBaseScraper):
    """Massey Hall + Roy Thomson Hall — concerts, classical, comedy.

    Both venues moved to mhrth.com (Massey Hall & Roy Thomson Hall).
    """
    SOURCE_NAME = "Massey Hall"
    BASE_URL = "https://masseyhall.mhrth.com"
    VENUES = {
        "Massey Hall": {"lat": 43.6541, "lng": -79.3766, "address": "178 Victoria St, Toronto, ON M5B 1T7"},
        "Roy Thomson Hall": {"lat": 43.6465, "lng": -79.3863, "address": "60 Simcoe St, Toronto, ON M5J 2H5"},
    }

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        urls = [
            ("https://masseyhall.mhrth.com/tickets/", "Massey Hall"),
            ("https://roythomsonhall.mhrth.com/tickets/", "Roy Thomson Hall"),
            ("https://www.ticketmaster.ca/massey-hall-tickets-toronto/venue/131094", "Massey Hall"),
            ("https://www.ticketmaster.ca/roy-thomson-hall-tickets-toronto/venue/131112", "Roy Thomson Hall"),
        ]
        for url, venue in urls:
            page = self.fetch_and_parse(url)
            if not page:
                continue

            ld_events = self.extract_jsonld(page)
            for ld in ld_events:
                ev = self.jsonld_to_event(ld, venue, url)
                if ev:
                    v = self.VENUES.get(venue, {})
                    ev.lat = v.get("lat")
                    ev.lng = v.get("lng")
                    ev.address = v.get("address", "")
                    events.append(ev)

            if not ld_events:
                events.extend(self._parse_html_cards(page, url, venue))

            time.sleep(self.DELAY)

        logger.info(f"[{self.SOURCE_NAME}] Scraped {len(events)} events")
        return events

    def _parse_html_cards(self, page, base_url: str, venue: str) -> List[ScrapedEvent]:
        results = []
        if HAS_SCRAPLING:
            cards = (page.css('.event-card') or page.css('.event-listing') or
                     page.css('[class*="event"]') or page.css('.card'))
        else:
            cards = (page.select('.event-card') or page.select('.event-listing') or
                     page.select('[class*="event"]') or page.select('.card'))

        for card in cards[:50]:
            try:
                if HAS_SCRAPLING:
                    title_el = card.css_first('h2, h3, h4, .title, a')
                    date_el = card.css_first('.date, time, [datetime], .event-date')
                    link_el = card.css_first('a[href]')
                    img_el = card.css_first('img[src], img[data-src]')
                else:
                    title_el = card.select_one('h2, h3, h4, .title, a')
                    date_el = card.select_one('.date, time, [datetime], .event-date')
                    link_el = card.select_one('a[href]')
                    img_el = card.select_one('img[src], img[data-src]')

                if not title_el:
                    continue
                title = title_el.text.strip() if hasattr(title_el, 'text') else ""
                if not title or self._is_garbage_title(title) or self.should_exclude(title):
                    continue

                date_str = ""
                if date_el:
                    date_str = (date_el.attrib.get("datetime", "") if HAS_SCRAPLING
                                else date_el.get("datetime", ""))
                    if not date_str:
                        date_str = date_el.text.strip() if hasattr(date_el, 'text') else ""
                date_iso = self._normalize_date(date_str) if date_str else None
                if not date_iso:
                    continue

                href = ""
                if link_el:
                    href = (link_el.attrib.get("href", "") if HAS_SCRAPLING
                            else link_el.get("href", ""))
                    if href and not href.startswith("http"):
                        href = base_url.rstrip("/") + href

                img = ""
                if img_el:
                    img = (img_el.attrib.get("src", "") or img_el.attrib.get("data-src", "")
                           if HAS_SCRAPLING else img_el.get("src", "") or img_el.get("data-src", ""))

                v = self.VENUES.get(venue, {})
                eid = self.generate_event_id(title, date_iso, venue)
                cats, tags = self.categorize_event(title, "")

                results.append(ScrapedEvent(
                    id=eid, title=title, date=date_iso,
                    location=venue, address=v.get("address", ""),
                    lat=v.get("lat"), lng=v.get("lng"),
                    source=venue, url=href or base_url,
                    categories=cats, tags=tags, image=img,
                ))
            except Exception:
                continue
        return results


class CasaLomaScraper(ScraplingBaseScraper):
    """Casa Loma — heritage events, exhibits, seasonal festivals."""
    SOURCE_NAME = "Casa Loma"
    BASE_URL = "https://casaloma.ca"
    VENUE_LAT = 43.6780
    VENUE_LNG = -79.4094
    VENUE_ADDRESS = "1 Austin Terrace, Toronto, ON M5R 1X8"

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        urls = [
            f"{self.BASE_URL}/whats-on",
            f"{self.BASE_URL}/events",
            f"{self.BASE_URL}/experiences",
        ]
        for url in urls:
            page = self.fetch_and_parse(url)
            if not page:
                continue

            ld_events = self.extract_jsonld(page)
            for ld in ld_events:
                ev = self.jsonld_to_event(ld, self.SOURCE_NAME, url)
                if ev:
                    ev.lat = self.VENUE_LAT
                    ev.lng = self.VENUE_LNG
                    ev.address = self.VENUE_ADDRESS
                    events.append(ev)

            if not ld_events:
                events.extend(self._parse_html(page, url))

            time.sleep(self.DELAY)

        logger.info(f"[{self.SOURCE_NAME}] Scraped {len(events)} events")
        return events

    def _parse_html(self, page, base_url: str) -> List[ScrapedEvent]:
        results = []
        if HAS_SCRAPLING:
            cards = (page.css('.event-card, .experience-card, .card, article, '
                             '[class*="event"], [class*="experience"]'))
        else:
            cards = page.select('.event-card, .experience-card, .card, article, '
                               '[class*="event"], [class*="experience"]')

        for card in cards[:30]:
            try:
                if HAS_SCRAPLING:
                    title_el = card.css_first('h2, h3, h4, .title, a')
                    date_el = card.css_first('.date, time, [datetime]')
                    link_el = card.css_first('a[href]')
                    img_el = card.css_first('img[src]')
                    desc_el = card.css_first('p, .description, .excerpt')
                else:
                    title_el = card.select_one('h2, h3, h4, .title, a')
                    date_el = card.select_one('.date, time, [datetime]')
                    link_el = card.select_one('a[href]')
                    img_el = card.select_one('img[src]')
                    desc_el = card.select_one('p, .description, .excerpt')

                if not title_el:
                    continue
                title = title_el.text.strip() if hasattr(title_el, 'text') else ""
                if not title or self._is_garbage_title(title) or self.should_exclude(title):
                    continue

                date_str = ""
                if date_el:
                    date_str = (date_el.attrib.get("datetime", "") if HAS_SCRAPLING
                                else date_el.get("datetime", ""))
                    if not date_str:
                        date_str = date_el.text.strip() if hasattr(date_el, 'text') else ""

                date_iso = self._normalize_date(date_str) if date_str else None
                # Casa Loma events may not have explicit dates — use "ongoing" marker
                if not date_iso:
                    continue  # Skip events without proper dates

                href = ""
                if link_el:
                    href = (link_el.attrib.get("href", "") if HAS_SCRAPLING
                            else link_el.get("href", ""))
                    if href and not href.startswith("http"):
                        href = self.BASE_URL + href

                desc = ""
                if desc_el:
                    desc = desc_el.text.strip()[:300] if hasattr(desc_el, 'text') else ""

                img = ""
                if img_el:
                    img = (img_el.attrib.get("src", "") if HAS_SCRAPLING
                           else img_el.get("src", ""))

                eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)
                cats, tags = self.categorize_event(title, desc)
                tags = list(set(tags + ["Heritage", "Casa Loma"]))

                results.append(ScrapedEvent(
                    id=eid, title=title, date=date_iso,
                    location=self.SOURCE_NAME, address=self.VENUE_ADDRESS,
                    lat=self.VENUE_LAT, lng=self.VENUE_LNG,
                    source=self.SOURCE_NAME, url=href or base_url,
                    description=desc, categories=cats, tags=tags, image=img,
                ))
            except Exception:
                continue
        return results


class TOLiveScraper(ScraplingBaseScraper):
    """TO Live — Meridian Hall, St Lawrence Centre for the Arts."""
    SOURCE_NAME = "TO Live"
    BASE_URL = "https://tolive.com"
    VENUES = {
        "Meridian Hall": {"lat": 43.6474, "lng": -79.3764, "address": "1 Front St E, Toronto, ON M5E 1B2"},
        "St Lawrence Centre": {"lat": 43.6487, "lng": -79.3739, "address": "27 Front St E, Toronto, ON M5E 1B4"},
    }

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        urls = [
            f"{self.BASE_URL}/Events-Page",
            f"{self.BASE_URL}/Upcoming-Events-%E2%80%94-See-All",
            # Ticketmaster fallback for Meridian Hall
            "https://www.ticketmaster.ca/meridian-hall-tickets-toronto/venue/131106",
        ]
        for url in urls:
            page = self.fetch_and_parse(url)
            if not page:
                continue

            ld_events = self.extract_jsonld(page)
            for ld in ld_events:
                ev = self.jsonld_to_event(ld, self.SOURCE_NAME, url)
                if ev:
                    self._assign_venue(ev)
                    events.append(ev)

            if not ld_events:
                events.extend(self._parse_cards(page, url))

            time.sleep(self.DELAY)

        logger.info(f"[{self.SOURCE_NAME}] Scraped {len(events)} events")
        return events

    def _assign_venue(self, ev: ScrapedEvent):
        """Assign venue coordinates based on location name."""
        loc = (ev.location or "").lower()
        for name, coords in self.VENUES.items():
            if name.lower() in loc:
                ev.lat = coords["lat"]
                ev.lng = coords["lng"]
                ev.address = coords["address"]
                return
        # Default to Meridian Hall
        v = self.VENUES["Meridian Hall"]
        ev.lat = v["lat"]
        ev.lng = v["lng"]
        ev.address = v["address"]

    def _parse_cards(self, page, base_url: str) -> List[ScrapedEvent]:
        results = []
        if HAS_SCRAPLING:
            cards = (page.css('.event-card, .show-card, article, [class*="event"], .card'))
        else:
            cards = page.select('.event-card, .show-card, article, [class*="event"], .card')

        for card in cards[:50]:
            try:
                if HAS_SCRAPLING:
                    title_el = card.css_first('h2, h3, h4, .title, a')
                    date_el = card.css_first('.date, time, [datetime]')
                    link_el = card.css_first('a[href]')
                    img_el = card.css_first('img[src]')
                    venue_el = card.css_first('.venue, .location')
                else:
                    title_el = card.select_one('h2, h3, h4, .title, a')
                    date_el = card.select_one('.date, time, [datetime]')
                    link_el = card.select_one('a[href]')
                    img_el = card.select_one('img[src]')
                    venue_el = card.select_one('.venue, .location')

                if not title_el:
                    continue
                title = title_el.text.strip() if hasattr(title_el, 'text') else ""
                if not title or self._is_garbage_title(title) or self.should_exclude(title):
                    continue

                date_str = ""
                if date_el:
                    date_str = (date_el.attrib.get("datetime", "") if HAS_SCRAPLING
                                else date_el.get("datetime", ""))
                    if not date_str:
                        date_str = date_el.text.strip() if hasattr(date_el, 'text') else ""
                date_iso = self._normalize_date(date_str) if date_str else None
                if not date_iso:
                    continue

                venue_name = self.SOURCE_NAME
                if venue_el:
                    venue_name = venue_el.text.strip() if hasattr(venue_el, 'text') else self.SOURCE_NAME

                href = ""
                if link_el:
                    href = (link_el.attrib.get("href", "") if HAS_SCRAPLING
                            else link_el.get("href", ""))
                    if href and not href.startswith("http"):
                        href = self.BASE_URL + href

                img = ""
                if img_el:
                    img = (img_el.attrib.get("src", "") if HAS_SCRAPLING
                           else img_el.get("src", ""))

                eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)
                cats, tags = self.categorize_event(title, "")

                ev = ScrapedEvent(
                    id=eid, title=title, date=date_iso,
                    location=venue_name, source=self.SOURCE_NAME,
                    url=href or base_url, categories=cats, tags=tags, image=img,
                )
                self._assign_venue(ev)
                results.append(ev)
            except Exception:
                continue
        return results


class OntarioScienceCentreScraper(ScraplingBaseScraper):
    """Ontario Science Centre — family events, exhibits."""
    SOURCE_NAME = "Ontario Science Centre"
    BASE_URL = "https://www.ontariosciencecentre.ca"
    VENUE_LAT = 43.7165
    VENUE_LNG = -79.3388
    VENUE_ADDRESS = "770 Don Mills Rd, North York, ON M3C 1T3"

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        urls = [
            f"{self.BASE_URL}/whats-on",
            f"{self.BASE_URL}/events",
            f"{self.BASE_URL}/exhibitions",
        ]
        for url in urls:
            page = self.fetch_and_parse(url)
            if not page:
                continue

            ld_events = self.extract_jsonld(page)
            for ld in ld_events:
                ev = self.jsonld_to_event(ld, self.SOURCE_NAME, url)
                if ev:
                    ev.lat = self.VENUE_LAT
                    ev.lng = self.VENUE_LNG
                    ev.address = self.VENUE_ADDRESS
                    events.append(ev)

            if not ld_events:
                events.extend(self._parse_html(page, url))

            time.sleep(self.DELAY)

        logger.info(f"[{self.SOURCE_NAME}] Scraped {len(events)} events")
        return events

    def _parse_html(self, page, base_url: str) -> List[ScrapedEvent]:
        results = []
        if HAS_SCRAPLING:
            cards = (page.css('.event-card, .exhibition-card, article, '
                             '[class*="event"], [class*="exhibit"], .card'))
        else:
            cards = page.select('.event-card, .exhibition-card, article, '
                               '[class*="event"], [class*="exhibit"], .card')

        for card in cards[:30]:
            try:
                if HAS_SCRAPLING:
                    title_el = card.css_first('h2, h3, h4, .title, a')
                    date_el = card.css_first('.date, time, [datetime]')
                    link_el = card.css_first('a[href]')
                    img_el = card.css_first('img[src]')
                    desc_el = card.css_first('p, .description')
                else:
                    title_el = card.select_one('h2, h3, h4, .title, a')
                    date_el = card.select_one('.date, time, [datetime]')
                    link_el = card.select_one('a[href]')
                    img_el = card.select_one('img[src]')
                    desc_el = card.select_one('p, .description')

                if not title_el:
                    continue
                title = title_el.text.strip() if hasattr(title_el, 'text') else ""
                if not title or self._is_garbage_title(title) or self.should_exclude(title):
                    continue

                date_str = ""
                if date_el:
                    date_str = (date_el.attrib.get("datetime", "") if HAS_SCRAPLING
                                else date_el.get("datetime", ""))
                    if not date_str:
                        date_str = date_el.text.strip() if hasattr(date_el, 'text') else ""
                date_iso = self._normalize_date(date_str) if date_str else None
                if not date_iso:
                    continue  # Skip events without proper dates

                href = ""
                if link_el:
                    href = (link_el.attrib.get("href", "") if HAS_SCRAPLING
                            else link_el.get("href", ""))
                    if href and not href.startswith("http"):
                        href = self.BASE_URL + href

                desc = desc_el.text.strip()[:300] if desc_el and hasattr(desc_el, 'text') else ""
                img = ""
                if img_el:
                    img = (img_el.attrib.get("src", "") if HAS_SCRAPLING
                           else img_el.get("src", ""))

                eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)
                cats, tags = self.categorize_event(title, desc)
                tags = list(set(tags + ["Science", "Family"]))

                results.append(ScrapedEvent(
                    id=eid, title=title, date=date_iso,
                    location=self.SOURCE_NAME, address=self.VENUE_ADDRESS,
                    lat=self.VENUE_LAT, lng=self.VENUE_LNG,
                    source=self.SOURCE_NAME, url=href or base_url,
                    description=desc, categories=cats, tags=tags, image=img,
                ))
            except Exception:
                continue
        return results


class UofTEventsScraper(ScraplingBaseScraper):
    """University of Toronto — public lectures, exhibitions, open events."""
    SOURCE_NAME = "University of Toronto"
    BASE_URL = "https://www.utoronto.ca"
    VENUE_LAT = 43.6629
    VENUE_LNG = -79.3957
    VENUE_ADDRESS = "27 King's College Cir, Toronto, ON M5S 1A1"

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        urls = [
            "https://www.utoronto.ca/events",
            "https://alumni.utoronto.ca/events-and-programs/upcoming-events",
        ]
        for url in urls:
            page = self.fetch_and_parse(url)
            if not page:
                continue

            ld_events = self.extract_jsonld(page)
            for ld in ld_events:
                ev = self.jsonld_to_event(ld, self.SOURCE_NAME, url)
                if ev:
                    if not ev.lat:
                        ev.lat = self.VENUE_LAT
                        ev.lng = self.VENUE_LNG
                    events.append(ev)

            if not ld_events:
                events.extend(self._parse_html(page, url))

            time.sleep(self.DELAY)

        logger.info(f"[{self.SOURCE_NAME}] Scraped {len(events)} events")
        return events

    def _parse_html(self, page, base_url: str) -> List[ScrapedEvent]:
        results = []
        if HAS_SCRAPLING:
            cards = (page.css('.event-card, .views-row, article, '
                             '[class*="event"], .card, .node--type-event'))
        else:
            cards = page.select('.event-card, .views-row, article, '
                               '[class*="event"], .card, .node--type-event')

        for card in cards[:50]:
            try:
                if HAS_SCRAPLING:
                    title_el = card.css_first('h2, h3, h4, .title, a, .field--name-title')
                    date_el = card.css_first('.date, time, [datetime], .field--name-field-date')
                    link_el = card.css_first('a[href]')
                else:
                    title_el = card.select_one('h2, h3, h4, .title, a, .field--name-title')
                    date_el = card.select_one('.date, time, [datetime], .field--name-field-date')
                    link_el = card.select_one('a[href]')

                if not title_el:
                    continue
                title = title_el.text.strip() if hasattr(title_el, 'text') else ""
                if not title or self._is_garbage_title(title) or self.should_exclude(title):
                    continue

                date_str = ""
                if date_el:
                    date_str = (date_el.attrib.get("datetime", "") if HAS_SCRAPLING
                                else date_el.get("datetime", ""))
                    if not date_str:
                        date_str = date_el.text.strip() if hasattr(date_el, 'text') else ""
                date_iso = self._normalize_date(date_str) if date_str else None
                if not date_iso:
                    continue

                href = ""
                if link_el:
                    href = (link_el.attrib.get("href", "") if HAS_SCRAPLING
                            else link_el.get("href", ""))
                    if href and not href.startswith("http"):
                        href = self.BASE_URL + href

                eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)
                cats, tags = self.categorize_event(title, "")
                tags = list(set(tags + ["University", "Academic"]))

                results.append(ScrapedEvent(
                    id=eid, title=title, date=date_iso,
                    location=self.SOURCE_NAME, address=self.VENUE_ADDRESS,
                    lat=self.VENUE_LAT, lng=self.VENUE_LNG,
                    source=self.SOURCE_NAME, url=href or base_url,
                    categories=cats, tags=tags,
                ))
            except Exception:
                continue
        return results


class TorontoBotanicalGardenScraper(ScraplingBaseScraper):
    """Toronto Botanical Garden / Edwards Gardens."""
    SOURCE_NAME = "Toronto Botanical Garden"
    BASE_URL = "https://torontobotanicalgarden.ca"
    VENUE_LAT = 43.7335
    VENUE_LNG = -79.3600
    VENUE_ADDRESS = "777 Lawrence Ave E, North York, ON M3C 1P2"

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        urls = [
            f"{self.BASE_URL}/events",
            f"{self.BASE_URL}/whats-on",
        ]
        for url in urls:
            page = self.fetch_and_parse(url)
            if not page:
                continue

            ld_events = self.extract_jsonld(page)
            for ld in ld_events:
                ev = self.jsonld_to_event(ld, self.SOURCE_NAME, url)
                if ev:
                    ev.lat = self.VENUE_LAT
                    ev.lng = self.VENUE_LNG
                    ev.address = self.VENUE_ADDRESS
                    events.append(ev)

            if not ld_events:
                events.extend(self._parse_html(page, url))

            time.sleep(self.DELAY)

        logger.info(f"[{self.SOURCE_NAME}] Scraped {len(events)} events")
        return events

    def _parse_html(self, page, base_url: str) -> List[ScrapedEvent]:
        results = []
        if HAS_SCRAPLING:
            cards = (page.css('.event-card, .tribe-events-list, article, '
                             '[class*="event"], .card'))
        else:
            cards = page.select('.event-card, .tribe-events-list, article, '
                               '[class*="event"], .card')

        for card in cards[:30]:
            try:
                if HAS_SCRAPLING:
                    title_el = card.css_first('h2, h3, h4, .title, a, .tribe-events-list-event-title')
                    date_el = card.css_first('.date, time, [datetime], .tribe-event-schedule-details')
                    link_el = card.css_first('a[href]')
                    img_el = card.css_first('img[src]')
                else:
                    title_el = card.select_one('h2, h3, h4, .title, a, .tribe-events-list-event-title')
                    date_el = card.select_one('.date, time, [datetime], .tribe-event-schedule-details')
                    link_el = card.select_one('a[href]')
                    img_el = card.select_one('img[src]')

                if not title_el:
                    continue
                title = title_el.text.strip() if hasattr(title_el, 'text') else ""
                if not title or self._is_garbage_title(title) or self.should_exclude(title):
                    continue

                date_str = ""
                if date_el:
                    date_str = (date_el.attrib.get("datetime", "") if HAS_SCRAPLING
                                else date_el.get("datetime", ""))
                    if not date_str:
                        date_str = date_el.text.strip() if hasattr(date_el, 'text') else ""
                date_iso = self._normalize_date(date_str) if date_str else None
                if not date_iso:
                    continue

                href = ""
                if link_el:
                    href = (link_el.attrib.get("href", "") if HAS_SCRAPLING
                            else link_el.get("href", ""))
                    if href and not href.startswith("http"):
                        href = self.BASE_URL + href

                img = ""
                if img_el:
                    img = (img_el.attrib.get("src", "") if HAS_SCRAPLING
                           else img_el.get("src", ""))

                eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)
                cats, tags = self.categorize_event(title, "")
                tags = list(set(tags + ["Garden", "Nature", "Outdoor"]))

                results.append(ScrapedEvent(
                    id=eid, title=title, date=date_iso,
                    location=self.SOURCE_NAME, address=self.VENUE_ADDRESS,
                    lat=self.VENUE_LAT, lng=self.VENUE_LNG,
                    source=self.SOURCE_NAME, url=href or base_url,
                    categories=cats, tags=tags, image=img,
                ))
            except Exception:
                continue
        return results


# ─── Aggregator ──────────────────────────────────────────────────────

class BMOFieldScraper(ScraplingBaseScraper):
    """BMO Field — Toronto FC, concerts, rugby (via Ticketmaster)."""
    SOURCE_NAME = "BMO Field"
    BASE_URL = "https://www.ticketmaster.ca"
    VENUE_LAT = 43.6332
    VENUE_LNG = -79.4186
    VENUE_ADDRESS = "170 Princes Blvd, Toronto, ON M6K 3C3"

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        urls = [
            "https://www.ticketmaster.ca/bmo-field-tickets-toronto/venue/131340",
        ]
        for url in urls:
            page = self.fetch_and_parse(url)
            if not page:
                continue
            ld_events = self.extract_jsonld(page)
            for ld in ld_events:
                ev = self.jsonld_to_event(ld, self.SOURCE_NAME, url)
                if ev:
                    ev.lat = self.VENUE_LAT
                    ev.lng = self.VENUE_LNG
                    ev.address = self.VENUE_ADDRESS
                    events.append(ev)
            time.sleep(self.DELAY)
        logger.info(f"[{self.SOURCE_NAME}] Scraped {len(events)} events")
        return events


class RogersCentreScraper(ScraplingBaseScraper):
    """Rogers Centre — Blue Jays, concerts, large events (via Ticketmaster)."""
    SOURCE_NAME = "Rogers Centre"
    BASE_URL = "https://www.ticketmaster.ca"
    VENUE_LAT = 43.6414
    VENUE_LNG = -79.3894
    VENUE_ADDRESS = "1 Blue Jays Way, Toronto, ON M5V 1J1"

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        urls = [
            "https://www.ticketmaster.ca/rogers-centre-tickets-toronto/venue/131358",
        ]
        for url in urls:
            page = self.fetch_and_parse(url)
            if not page:
                continue
            ld_events = self.extract_jsonld(page)
            for ld in ld_events:
                ev = self.jsonld_to_event(ld, self.SOURCE_NAME, url)
                if ev:
                    ev.lat = self.VENUE_LAT
                    ev.lng = self.VENUE_LNG
                    ev.address = self.VENUE_ADDRESS
                    events.append(ev)
            time.sleep(self.DELAY)
        logger.info(f"[{self.SOURCE_NAME}] Scraped {len(events)} events")
        return events


ALL_ENHANCED_SCRAPERS = [
    ScotiabankArenaScraper,
    MasseyHallScraper,
    CasaLomaScraper,
    TOLiveScraper,
    # OntarioScienceCentreScraper — permanently closed
    UofTEventsScraper,
    TorontoBotanicalGardenScraper,
    BMOFieldScraper,
    RogersCentreScraper,
]


def scrape_all_enhanced(verbose: bool = True) -> List[ScrapedEvent]:
    """Run all enhanced scrapers and return combined events."""
    all_events = []
    for scraper_cls in ALL_ENHANCED_SCRAPERS:
        name = scraper_cls.SOURCE_NAME
        try:
            scraper = scraper_cls()
            events = scraper.scrape()
            if verbose:
                print(f"  [{name}] → {len(events)} events")
            all_events.extend(events)
        except Exception as e:
            if verbose:
                print(f"  [{name}] ERROR: {e}")
    return all_events


# ─── CLI for testing ─────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import io
    # Fix Windows encoding for unicode arrows etc.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    logging.basicConfig(level=logging.INFO)

    print(f"Scrapling available: {HAS_SCRAPLING}")
    print(f"Enhanced scrapers: {len(ALL_ENHANCED_SCRAPERS)}")
    print("=" * 60)

    all_events = scrape_all_enhanced(verbose=True)

    print(f"\n{'=' * 60}")
    print(f"TOTAL: {len(all_events)} events from {len(ALL_ENHANCED_SCRAPERS)} sources")

    # Print sample from each source
    by_source = {}
    for ev in all_events:
        by_source.setdefault(ev.source, []).append(ev)

    for source, evts in by_source.items():
        print(f"\n--- {source} ({len(evts)} events) ---")
        for ev in evts[:3]:
            print(f"  {ev.title}")
            print(f"    Date: {ev.date}")
            print(f"    Location: {ev.location}")
            print(f"    URL: {ev.url}")
            if ev.price != "Free":
                print(f"    Price: {ev.price}")
            print()

    # Always save JSON for review
    output = [ev.to_dict() for ev in all_events]
    with open("scrapling_sample_output.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str, ensure_ascii=False)
    print(f"\nSaved {len(output)} events to scrapling_sample_output.json")
