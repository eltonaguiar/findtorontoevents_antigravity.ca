#!/usr/bin/env python3
"""
GetThursday.com Toronto Events Scraper

Scrapes dating events from Thursday's Toronto page:
  https://events.getthursday.com/toronto/

Thursday is a major dating/singles platform operating globally.
The site uses a modern JavaScript architecture with dynamic content loading.

This scraper extracts event data by parsing the HTML structure.
"""
import re
import time
import logging
from datetime import datetime
from typing import List, Optional

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

# Constants
GTHURSDAY_TORONTO_URL = "https://events.getthursday.com/toronto/"
GTHURSDAY_BASE = "https://events.getthursday.com"

# Month map for date parsing
_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# Dating-related keywords for filtering/tagging
DATING_KEYWORDS = [
    "dating", "singles", "speed dating", "matchmaking", "social mixer",
    "mingle", "meet singles", "single professionals", "date night",
    "lgbtq", "gay singles", "lesbian singles", "lgbtq+", "pride",
]


class GetThursdayScraper(BaseScraper):
    """Scrape Thursday dating events from their Toronto page."""

    SOURCE_NAME = "Thursday"
    BASE_URL = GTHURSDAY_BASE

    def __init__(self):
        super().__init__()
        if HAS_SCRAPLING:
            self._fetcher = Fetcher(auto_match=False)
        # Browser-like headers
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-CA,en;q=0.9",
        })

    def _fetch_html(self, url: str) -> Optional[str]:
        """Fetch HTML from URL with fallback."""
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
            logger.warning(f"[{self.SOURCE_NAME}] fetch failed for {url}: {exc}")
            return None

    def _parse_thursday_date(self, date_str: str) -> Optional[str]:
        """
        Parse Thursday date strings like:
        - "Sat 25th April 2026 at 6:30 pm"
        - "Thu 30th April 2026 at 7:00 pm"
        - "Tue 5th May 2026 at 7:00 pm"

        Returns ISO-8601 UTC string.
        """
        if not date_str:
            return None
        date_str = date_str.strip()

        # Remove ordinal suffixes: "25th" → "25", "1st" → "1"
        date_str = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", date_str, flags=re.IGNORECASE)

        # Pattern: Day Month Year at time
        m = re.search(
            r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\s+at\s+(\d{1,2}):(\d{2})\s*(am|pm)",
            date_str, re.IGNORECASE
        )

        if not m:
            # Fallback: try without year
            m = re.search(
                r"(\d{1,2})\s+([A-Za-z]+)\s+at\s+(\d{1,2}):(\d{2})\s*(am|pm)",
                date_str, re.IGNORECASE
            )

        if not m:
            return None

        day = int(m.group(1))
        month_str = m.group(2).lower()[:3]
        month = _MONTH_MAP.get(month_str)
        if not month:
            return None

        if len(m.groups()) > 5:
            # Has year
            year_str = m.group(3)
            year = int(year_str)
            hour = int(m.group(4))
            minute = int(m.group(5))
            ampm = m.group(6) if len(m.groups()) > 6 else ""
        else:
            # No year - assume current year
            year = datetime.utcnow().year
            hour = int(m.group(3))
            minute = int(m.group(4))
            ampm = m.group(5)

        if ampm:
            if ampm.lower() == "pm" and hour != 12:
                hour += 12
            elif ampm.lower() == "am" and hour == 12:
                hour = 0

        # Treat as EDT (UTC-4) → convert to UTC
        hour_utc = (hour + 4) % 24
        dt = datetime(year, month, day, hour_utc, minute)

        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _parse_event_card(self, card, use_scrapling: bool) -> Optional[dict]:
        """Parse a single event card from Thursday's HTML."""
        try:
            # Extract event URL from card-link attribute (primary method)
            url = ""
            if use_scrapling:
                url = getattr(card, "attrib", {}).get("card-link", "")
                if not url:
                    link_el = card.css_first(".card__heading a.heading-link")
                    if link_el:
                        url = getattr(link_el, "attrib", {}).get("href", "")
            else:
                url = card.get("card-link", "")
                if not url:
                    link_el = card.select_one(".card__heading a.heading-link")
                    if link_el:
                        url = link_el.get("href", "")

            if not url:
                return None

            if not url.startswith("http"):
                url = GTHURSDAY_BASE + url

            # Extract title
            title = ""
            if use_scrapling:
                title_el = card.css_first(".card__heading a.heading-link")
                if title_el:
                    title = (getattr(title_el, "text", "") or "").strip()
            else:
                title_el = card.select_one(".card__heading a.heading-link")
                if title_el:
                    title = title_el.get_text(strip=True)

            if not title or len(title) < 5:
                return None

            # Skip navigation/footer links
            if title.lower() in ["events", "dinners", "trips", "about", "faqs", "news"]:
                return None

            # Extract date/time
            date_str = ""
            if use_scrapling:
                date_el = card.css_first(".meta--date")
                if date_el:
                    date_str = (getattr(date_el, "text", "") or "").strip()
            else:
                date_el = card.select_one(".meta--date")
                if date_el:
                    date_str = date_el.get_text(strip=True)

            # Extract venue location
            venue = "Toronto, ON"
            if use_scrapling:
                venue_el = card.css_first(".meta--location")
                if venue_el:
                    venue = (getattr(venue_el, "text", "") or "").strip()
            else:
                venue_el = card.select_one(".meta--location")
                if venue_el:
                    venue = venue_el.get_text(strip=True)

            # Extract image
            image = ""
            if use_scrapling:
                img_el = card.css_first(".card__media--image")
                if img_el:
                    image = getattr(img_el, "attrib", {}).get("src", "")
            else:
                img_el = card.select_one(".card__media--image")
                if img_el:
                    image = img_el.get("src", "")

            return {
                "title": title,
                "url": url,
                "date_str": date_str,
                "venue": venue,
                "image": image,
            }
        except Exception as e:
            logger.debug(f"[{self.SOURCE_NAME}] Error parsing card: {e}")
            return None

    def _scrape_to_event(self, raw: dict) -> Optional[ScrapedEvent]:
        """Convert raw event data to ScrapedEvent."""
        title = raw["title"]
        url = raw["url"]

        # Parse date
        date_iso = self._parse_thursday_date(raw.get("date_str", ""))
        if not date_iso:
            logger.debug(f"[{self.SOURCE_NAME}] Could not parse date for '{title}': {raw.get('date_str')}")
            return None

        # Venue and location
        venue = raw.get("venue", "Toronto, ON")
        loc_info = self.enhance_location(venue, title)

        # Categories and tags - force Dating category
        cats, tags = self.categorize_event(title, "")
        if "Dating" not in cats:
            cats.insert(0, "Dating")

        # Add relevant dating tags based on title
        title_lower = title.lower()
        for kw in DATING_KEYWORDS:
            if kw in title_lower and kw not in tags:
                tags.append(kw.capitalize())

        if "Singles" not in tags:
            tags.append("Singles")

        # Generate event ID
        eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)

        # Fix image URL if needed
        image = raw.get("image", "")
        if image and not image.startswith(("http://", "https://")):
            image = ""

        return ScrapedEvent(
            id=eid,
            title=title,
            date=date_iso,
            location=loc_info.get("location", venue),
            address=loc_info.get("address"),
            lat=loc_info.get("lat"),
            lng=loc_info.get("lng"),
            source=self.SOURCE_NAME,
            host="Thursday App",
            url=url,
            price="See App",
            price_amount=0.0,
            is_free=False,
            description="",
            categories=cats,
            tags=tags,
            status="UPCOMING",
            is_multi_day=False,
            duration_category="single",
            image=image if image else None,
        )

    def scrape(self) -> List[ScrapedEvent]:
        """Scrape Thursday Toronto events."""
        all_events = []
        seen_urls = set()

        print(f"[{self.SOURCE_NAME}] Scraping Thursday Toronto events...")

        html = self._fetch_html(GTHURSDAY_TORONTO_URL)
        if not html:
            print(f"[{self.SOURCE_NAME}] Failed to fetch page")
            return []

        # Parse HTML
        if HAS_BS4:
            soup = BeautifulSoup(html, "html.parser")
            # Thursday uses specific BEM-style CSS classes for event cards
            cards = soup.select(".events-grid-flexible-columns__card, .card__wrapper[card-link]")
            use_scrapling = False
        elif HAS_SCRAPLING:
            page = self._fetcher.get(GTHURSDAY_TORONTO_URL)
            cards = page.css(".events-grid-flexible-columns__card, .card__wrapper[card-link]")
            use_scrapling = True
        else:
            print(f"[{self.SOURCE_NAME}] No HTML parser available")
            return []

        # Extract raw event data
        raw_events = []
        for card in cards:
            try:
                raw = self._parse_event_card(card, use_scrapling)
                if raw and raw["url"] not in seen_urls:
                    seen_urls.add(raw["url"])
                    raw_events.append(raw)
            except Exception as e:
                logger.debug(f"[{self.SOURCE_NAME}] Error processing card: {e}")

        print(f"[{self.SOURCE_NAME}] Found {len(raw_events)} unique events")

        # Convert to ScrapedEvent objects
        for raw in raw_events:
            event = self._scrape_to_event(raw)
            if event:
                all_events.append(event)
                print(f"  ✓ {event.title[:70]}")

        print(f"[{self.SOURCE_NAME}] Total Thursday dating events: {len(all_events)}")
        return all_events


def scrape_thursday_events() -> List[dict]:
    """Convenience function for standalone use."""
    scraper = GetThursdayScraper()
    return scraper.scrape_to_json()


if __name__ == "__main__":
    import json
    import sys
    import io

    # Fix Windows encoding
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    logging.basicConfig(level=logging.DEBUG)

    print(f"Scrapling available: {HAS_SCRAPLING}")
    print(f"BeautifulSoup available: {HAS_BS4}")
    print("=" * 60)

    events = scrape_thursday_events()

    print(f"\n{'='*60}")
    print(f"TOTAL: {len(events)} Thursday events")

    for ev in events[:10]:
        print(f"\n  {ev.get('title', '?')}")
        print(f"    Date: {ev.get('date', '?')}")
        print(f"    Venue: {ev.get('location', '?')}")
        print(f"    URL: {ev.get('url', '?')[:80]}")
        print(f"    Categories: {ev.get('categories', [])}")
        print(f"    Tags: {ev.get('tags', [])}")

    output_path = "thursday_events_sample.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, default=str, ensure_ascii=False)
    print(f"\nSaved {len(events)} events to {output_path}")