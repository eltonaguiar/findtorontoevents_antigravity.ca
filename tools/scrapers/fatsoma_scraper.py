#!/usr/bin/env python3
"""
Fatsoma Toronto Dating Events Scraper

Fatsoma is a global event ticketing platform with a Dating category.
This scraper:
  1. Fetches paginated pages of Fatsoma's Dating discover page.
  2. Filters for events located in Toronto (or nearby GTA cities).
  3. Fetches each event's detail page for full address, description, and image.

Dating category URL:
  https://www.fatsoma.com/discover?category-id=292067f6-677e-4af9-9196-1211e04d3039

Toronto events seen:
  - "Thursday | Sunrise Forgives | Toronto"
  - "Thursday | Summer Yacht Party | Toronto"
  (more may exist across subsequent pages)
"""
import re
import time
import logging
from datetime import datetime
from typing import List, Optional, Tuple

import requests

try:
    from scrapling import Fetcher
    HAS_SCRAPLING = True
except ImportError:
    HAS_SCRAPLING = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

try:
    from .base_scraper import BaseScraper, ScrapedEvent
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from base_scraper import BaseScraper, ScrapedEvent

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

FATSOMA_BASE = "https://www.fatsoma.com"
FATSOMA_DATING_URL = (
    f"{FATSOMA_BASE}/discover"
    "?category-id=292067f6-677e-4af9-9196-1211e04d3039"
)

# Toronto / GTA location markers used to identify local events
TORONTO_MARKERS = [
    "toronto", " on,", "ontario", "scarborough", "north york",
    "etobicoke", "mississauga", "markham", "vaughan", "richmond hill",
    "brampton", "oakville", "ajax", "oshawa", "pickering",
]

# Month abbreviation map for Fatsoma date strings ("30th Apr")
_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# Max pages to iterate on the discover page (Fatsoma shows ~11 pages per run)
MAX_PAGES = 12

# Seconds to wait between requests (be polite)
DELAY = 1.5


# ── Scraper ──────────────────────────────────────────────────────────────────

class FatsomaScraper(BaseScraper):
    """Scrape Fatsoma dating events located in Toronto / GTA."""

    SOURCE_NAME = "Fatsoma"
    BASE_URL = FATSOMA_BASE

    def __init__(self):
        super().__init__()
        # Prefer Scrapling for TLS fingerprinting; fall back to requests
        if HAS_SCRAPLING:
            self._fetcher = Fetcher(auto_match=False)
        # Browser-like UA helps avoid bot detection
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-CA,en;q=0.9",
        })

    # ── Fetch helpers ─────────────────────────────────────────────────────────

    def _fetch_text(self, url: str) -> Optional[str]:
        """Return raw HTML text for *url* or None on failure."""
        try:
            if HAS_SCRAPLING:
                resp = self._fetcher.get(url, timeout=30)
                body = getattr(resp, "body", None) or getattr(resp, "content", None)
                if isinstance(body, (bytes, bytearray)):
                    return body.decode("utf-8", errors="replace")
                if isinstance(body, str):
                    return body
                return str(resp)
            else:
                resp = self.session.get(url, timeout=30)
                resp.raise_for_status()
                return resp.text
        except Exception as exc:
            logger.warning(f"[Fatsoma] fetch failed for {url}: {exc}")
            return None

    def _parse_html(self, html: str):
        """Return a BeautifulSoup object or None if bs4 unavailable."""
        if not HAS_BS4:
            return None
        return BeautifulSoup(html, "html.parser")

    # ── Date parsing ──────────────────────────────────────────────────────────

    def _parse_fatsoma_date(self, date_str: str) -> Optional[str]:
        """
        Parse Fatsoma date strings like "Thu 30th Apr at 7:00pm" →
        ISO-8601 UTC string.  Uses noon UTC if no time found.
        """
        if not date_str:
            return None
        date_str = date_str.strip()

        # Remove ordinal suffixes: "30th" → "30", "1st" → "1", etc.
        date_str = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", date_str, flags=re.IGNORECASE)

        # Expected pattern: "Thu 30 Apr at 7:00pm"
        m = re.search(
            r"(\d{1,2})\s+([A-Za-z]{3})"  # day + month abbreviation
            r"(?:\s+(\d{4}))?"             # optional year
            r"(?:\s+at\s+(\d{1,2}:\d{2})(am|pm))?",  # optional time
            date_str, re.IGNORECASE
        )
        if not m:
            return None

        day = int(m.group(1))
        month_str = m.group(2).lower()[:3]
        month = _MONTH_MAP.get(month_str)
        if not month:
            return None

        year_str = m.group(3)
        year = int(year_str) if year_str else datetime.utcnow().year

        time_str = m.group(4)   # e.g. "7:00"
        ampm = m.group(5)       # "am" / "pm"

        if time_str and ampm:
            hour, minute = map(int, time_str.split(":"))
            if ampm.lower() == "pm" and hour != 12:
                hour += 12
            elif ampm.lower() == "am" and hour == 12:
                hour = 0
            # Treat as EDT (UTC-4) → convert to UTC
            hour_utc = (hour + 4) % 24
            dt = datetime(year, month, day, hour_utc, minute)
        else:
            # Date-only: use noon UTC so calendar day is correct in Eastern time
            dt = datetime(year, month, day, 12, 0)

        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    # ── Location helpers ──────────────────────────────────────────────────────

    def _is_toronto(self, location_text: str) -> bool:
        """Return True if *location_text* references Toronto or GTA."""
        lt = location_text.lower()
        return any(marker in lt for marker in TORONTO_MARKERS)

    def _extract_address_from_detail(self, html: str) -> Tuple[Optional[str], Optional[float], Optional[float]]:
        """
        Pull venue address and Google Maps coordinates from a Fatsoma event
        detail page.

        Fatsoma renders the address in a venue section like:
          "545 King St W, Toronto, ON M5V 1M1, Canada"
        and provides a Google Maps link:
          https://maps.google.com/maps?daddr=43.6442891,-79.3987526
        """
        address = None
        lat = lng = None

        # Google Maps link gives us lat/lng directly
        maps_m = re.search(r"maps\.google\.com/maps\?daddr=([\d.\-]+),([\d.\-]+)", html)
        if maps_m:
            try:
                lat = float(maps_m.group(1))
                lng = float(maps_m.group(2))
            except ValueError:
                pass

        # Extract address text.  Fatsoma renders it near "Open in Maps" text.
        addr_m = re.search(
            r'([A-Z0-9][^<\n]{10,120}(?:Toronto|Scarborough|Mississauga|North York'
            r'|Etobicoke|Markham|Vaughan|Richmond Hill|Brampton|Oakville)[^<\n]{0,80}Canada)',
            html, re.IGNORECASE
        )
        if addr_m:
            address = addr_m.group(1).strip()
            # Remove any trailing " [Open in Maps]" or similar artefacts
            address = re.sub(r'\s*\[?Open in Maps\]?.*', '', address, flags=re.IGNORECASE).strip()

        return address, lat, lng

    def _extract_image_from_detail(self, html: str) -> Optional[str]:
        """Return the first fatsoma.imgix.net image URL from the detail page."""
        m = re.search(r'(https://fatsoma\.imgix\.net/[^\s"\']+)', html)
        return m.group(1) if m else None

    def _extract_description_from_detail(self, html: str) -> str:
        """Extract a plain-text description snippet from the event detail page."""
        soup = self._parse_html(html)
        if not soup:
            return ""
        # Look for the main event description section
        for sel in ["div.event-description", "section.description", "article", "main"]:
            el = soup.select_one(sel)
            if el:
                text = el.get_text(separator=" ", strip=True)
                # Trim to 500 chars
                return text[:500]
        return ""

    def _extract_price_from_detail(self, html: str) -> Tuple[str, float, bool]:
        """Return (price_str, price_amount, is_free) from a detail page."""
        # Pattern: "CA$35.00 + CA$3.50 booking fee" or "Free"
        free_m = re.search(r'\bFree\b', html, re.IGNORECASE)
        price_m = re.search(r'CA\$\s*([\d.]+)', html)
        if free_m and not price_m:
            return "Free", 0.0, True
        if price_m:
            amount = float(price_m.group(1))
            return f"CA${amount:.2f}", amount, amount == 0.0
        return "See site", 0.0, False

    # ── Discover page parsing ─────────────────────────────────────────────────

    def _parse_discover_page(self, html: str) -> List[dict]:
        """
        Parse a Fatsoma discover page and return a list of raw event dicts for
        events located in Toronto.

        Fatsoma's discover page renders server-side via Ember FastBoot, so
        Beautiful Soup can parse the event cards directly.

        Each card in the rendered HTML has structure roughly:
          <a href="/e/{id}/{slug}">Event Title</a>
          followed by date/time text and venue text.

        We fall back to regex over the raw HTML if bs4 isn't available.
        """
        events = []

        # ── Regex approach (works without BS4) ────────────────────────────────
        # Event links look like: href="/e/c41j6xsc/thursday-sunrise-forgives-toronto"
        pattern = re.compile(
            r'href="(/e/([a-z0-9]+)/([^"]+))"[^>]*>([^<]+)</a>'
            r'([^<]{0,300})',  # capture surrounding text for date/venue
            re.DOTALL
        )
        for match in pattern.finditer(html):
            rel_url = match.group(1)
            slug = match.group(3)
            title = match.group(4).strip()
            context = match.group(5)

            # Only keep events that look like they're in Toronto
            combined = f"{slug} {title} {context}".lower()
            if "toronto" not in combined:
                continue

            # Skip if title is empty or a nav link
            if not title or len(title) < 5:
                continue

            # Try to extract date and venue from the surrounding text
            date_m = re.search(
                r'((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+\d+\w+\s+\w+(?:\s+at\s+[\d:]+(?:am|pm))?)',
                context, re.IGNORECASE
            )
            date_str = date_m.group(1) if date_m else ""

            # Venue text: often "Venue Name, City" after the date
            venue_m = re.search(r'([A-Z][^,\n<]{3,60},\s*Toronto[^,<]*)', context, re.IGNORECASE)
            venue_text = venue_m.group(1).strip() if venue_m else "Toronto, ON"

            # Price text
            price_m = re.search(r'CA\$[\d.\s\-]+', context)
            price_text = price_m.group(0).strip() if price_m else ""

            events.append({
                "url": FATSOMA_BASE + rel_url,
                "title": title,
                "date_str": date_str,
                "venue_text": venue_text,
                "price_text": price_text,
            })

        return events

    # ── Detail page fetch ─────────────────────────────────────────────────────

    def _enrich_from_detail(self, raw: dict) -> Optional[ScrapedEvent]:
        """Fetch a Fatsoma event detail page and build a ScrapedEvent."""
        url = raw["url"]
        title = raw["title"]

        date_iso = self._parse_fatsoma_date(raw.get("date_str", ""))
        if not date_iso:
            logger.debug(f"[Fatsoma] Skipping '{title}' — could not parse date '{raw.get('date_str')}'")
            return None

        html = self._fetch_text(url)
        if not html:
            return None

        address, lat, lng = self._extract_address_from_detail(html)
        image = self._extract_image_from_detail(html)
        description = self._extract_description_from_detail(html)
        price_str, price_amount, is_free = self._extract_price_from_detail(html)

        # Fall back to discover-page price text
        if not price_str or price_str == "See site":
            if raw.get("price_text"):
                price_str = raw["price_text"]

        # Venue / location from detail page address or discover-page venue text
        venue_text = raw.get("venue_text") or "Toronto, ON"
        if address:
            # Extract venue name (first part before the street number or comma)
            venue_name = venue_text.split(",")[0].strip()
        else:
            venue_name = venue_text.split(",")[0].strip()
            address = venue_text if "," in venue_text else None

        loc_info = self.enhance_location(venue_name or "Toronto, ON", title)
        if not address and loc_info.get("address"):
            address = loc_info["address"]
        if not lat and loc_info.get("lat"):
            lat = loc_info["lat"]
            lng = loc_info["lng"]

        # Ensure Toronto coordinates if still missing
        if not lat:
            lat, lng = 43.6532, -79.3832  # downtown Toronto

        cats, tags = self.categorize_event(title, description)
        if "Dating" not in cats:
            cats.insert(0, "Dating")
        if "Singles" not in tags:
            tags.append("Singles")

        eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)

        return ScrapedEvent(
            id=eid,
            title=title,
            date=date_iso,
            location=venue_name or "Toronto, ON",
            address=address,
            lat=lat,
            lng=lng,
            source=self.SOURCE_NAME,
            host="Fatsoma",
            url=url,
            price=price_str,
            price_amount=price_amount,
            is_free=is_free,
            description=description[:500],
            categories=cats,
            tags=tags,
            status="UPCOMING",
            is_multi_day=False,
            duration_category="single",
            image=image,
        )

    # ── Main scrape ───────────────────────────────────────────────────────────

    def scrape(self) -> List[ScrapedEvent]:
        """Scrape all Toronto dating events from Fatsoma."""
        all_events: List[ScrapedEvent] = []
        seen_urls: set = set()
        raw_events: List[dict] = []

        print(f"[{self.SOURCE_NAME}] Scanning Fatsoma Dating discover pages for Toronto events...")

        for page_num in range(1, MAX_PAGES + 1):
            if page_num == 1:
                url = FATSOMA_DATING_URL
            else:
                url = f"{FATSOMA_DATING_URL}&page={page_num}"

            html = self._fetch_text(url)
            if not html:
                break

            page_events = self._parse_discover_page(html)
            new_count = 0
            for ev in page_events:
                ev_url = ev["url"]
                if ev_url not in seen_urls:
                    seen_urls.add(ev_url)
                    raw_events.append(ev)
                    new_count += 1

            print(f"  Page {page_num}: found {new_count} Toronto events "
                  f"(total raw so far: {len(raw_events)})")

            if new_count == 0 and page_num > 1:
                # No new Toronto events on this page — Fatsoma pages are
                # globally mixed so we keep trying for a few more pages
                # before giving up.
                if page_num >= 5:
                    break

            time.sleep(DELAY)

        # Fetch detail pages for each unique Toronto event
        print(f"[{self.SOURCE_NAME}] Fetching details for {len(raw_events)} Toronto events...")
        for raw in raw_events:
            try:
                ev = self._enrich_from_detail(raw)
                if ev:
                    all_events.append(ev)
                    print(f"  ✓ {ev.title[:70]}")
            except Exception as exc:
                logger.warning(f"[Fatsoma] Error enriching '{raw.get('title')}': {exc}")
            time.sleep(DELAY)

        print(f"[{self.SOURCE_NAME}] Total Toronto dating events: {len(all_events)}")
        return all_events


def scrape_fatsoma_events() -> List[dict]:
    """Convenience function for standalone use."""
    scraper = FatsomaScraper()
    return scraper.scrape_to_json()


if __name__ == "__main__":
    import json
    events = scrape_fatsoma_events()
    print(json.dumps(events[:5], indent=2))
