#!/usr/bin/env python3
"""
New Toronto event sources powered by Scrapling.

Targets high-volume sources NOT yet in the pipeline:
  1. ToDoCanada (todocanada.ca/city/toronto/event/) — 24-page paginated calendar
  2. Toronto.ca Festivals & Events Calendar — City-run events API
  3. SeeTorontoNow / Destination Toronto — Tourism board events

Uses Scrapling's Fetcher for TLS-fingerprinted requests + fast CSS parsing.
Falls back to requests + BeautifulSoup if Scrapling unavailable.
"""
import json
import re
import time
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple

import requests

try:
    from scrapling import Fetcher
    HAS_SCRAPLING = True
except ImportError:
    HAS_SCRAPLING = False

try:
    from .scrapling_enhanced import ScraplingBaseScraper
    from .base_scraper import ScrapedEvent
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from scrapling_enhanced import ScraplingBaseScraper
    from base_scraper import ScrapedEvent

logger = logging.getLogger(__name__)


# ─── ToDoCanada ──────────────────────────────────────────────────────

class ToDoCanadaScraper(ScraplingBaseScraper):
    """Scrape events from todocanada.ca/city/toronto/event/ (paginated).

    The site has ~24 pages of Toronto events with structured cards containing:
    title, location, dates, price.  Events span months into the future.
    """
    SOURCE_NAME = "ToDoCanada"
    BASE_URL = "https://www.todocanada.ca"
    EVENTS_URL = "https://www.todocanada.ca/city/toronto/event/"
    MAX_PAGES = 24
    DELAY = 1.5  # Be polite — not a high-traffic API

    # Toronto-area keywords to filter for relevance (some events are GTA/Ontario)
    TORONTO_AREA_KEYWORDS = {
        "toronto", "north york", "scarborough", "etobicoke", "york",
        "east york", "downtown", "midtown", "queen st", "king st",
        "bloor", "yonge", "harbourfront", "distillery", "liberty village",
        "kensington", "leslieville", "beaches", "parkdale", "roncesvalles",
        "junction", "high park", "danforth", "greektown",
    }

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        seen_urls = set()

        for page_num in range(1, self.MAX_PAGES + 1):
            url = self.EVENTS_URL if page_num == 1 else f"{self.EVENTS_URL}page/{page_num}/"
            logger.info(f"[{self.SOURCE_NAME}] Fetching page {page_num}/{self.MAX_PAGES}: {url}")
            print(f"  [{self.SOURCE_NAME}] Page {page_num}/{self.MAX_PAGES}...")

            page = self.fetch_and_parse(url)
            if not page:
                logger.warning(f"[{self.SOURCE_NAME}] Failed to fetch page {page_num}, stopping pagination.")
                break

            page_events = self._parse_event_list(page, seen_urls)
            if not page_events:
                # Empty page = we've gone past the last page
                break

            events.extend(page_events)
            time.sleep(self.DELAY)

        logger.info(f"[{self.SOURCE_NAME}] Scraped {len(events)} events total")
        print(f"  [{self.SOURCE_NAME}] Total: {len(events)} events")
        return events

    def _parse_event_list(self, page, seen_urls: set) -> List[ScrapedEvent]:
        """Parse event cards from a ToDoCanada event list page.

        Structure: page has `.entry` elements, each containing:
        - h2 > a (title + link)
        - get_all_text() has: date range, location, phone, price, description
        """
        results = []

        if HAS_SCRAPLING:
            # Each event is a .entry or .post element
            cards = page.css('.entry')
            if not cards:
                cards = page.css('.post')

            for card in cards[:50]:
                try:
                    # Get sub-elements using Selector.css()
                    title_links = card.css('h2 a')
                    if not title_links:
                        continue
                    title_el = title_links[0]
                    title = title_el.text.strip()
                    if not title or self._is_garbage_title(title) or self.should_exclude(title):
                        continue

                    href = title_el.attrib.get("href", "")
                    if not href or href in seen_urls:
                        continue
                    if not href.startswith("http"):
                        href = self.BASE_URL + href
                    seen_urls.add(href)

                    # get_all_text() gives us the full block: date, location, price, description
                    block_text = card.get_all_text()

                    date_iso, end_date_iso = self._extract_dates_from_text(block_text)
                    if not date_iso:
                        continue

                    location = self._extract_location_from_text(block_text)
                    price_str, price_amount, is_free = self._extract_price_from_text(block_text)

                    eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)
                    cats, tags = self.categorize_event(title, block_text)

                    is_multi, duration_cat = self._detect_multiday(date_iso, end_date_iso)

                    results.append(ScrapedEvent(
                        id=eid,
                        title=title,
                        date=date_iso,
                        end_date=end_date_iso,
                        location=location or "Toronto, ON",
                        source=self.SOURCE_NAME,
                        host="ToDoCanada",
                        url=href,
                        price=price_str,
                        price_amount=price_amount,
                        is_free=is_free,
                        description="",
                        categories=cats,
                        tags=tags,
                        status="UPCOMING",
                        is_multi_day=is_multi,
                        duration_category=duration_cat,
                    ))
                except Exception as exc:
                    logger.debug(f"[{self.SOURCE_NAME}] Card parse error: {exc}")
                    continue
        else:
            # BeautifulSoup fallback
            cards = page.select('.entry') or page.select('.post')
            for card in cards[:50]:
                try:
                    title_el = card.select_one('h2 a')
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)
                    if not title or self._is_garbage_title(title) or self.should_exclude(title):
                        continue

                    href = title_el.get("href", "")
                    if not href or href in seen_urls:
                        continue
                    if not href.startswith("http"):
                        href = self.BASE_URL + href
                    seen_urls.add(href)

                    block_text = card.get_text("\n", strip=True)

                    date_iso, end_date_iso = self._extract_dates_from_text(block_text)
                    if not date_iso:
                        continue

                    location = self._extract_location_from_text(block_text)
                    price_str, price_amount, is_free = self._extract_price_from_text(block_text)

                    eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)
                    cats, tags = self.categorize_event(title, block_text)
                    is_multi, duration_cat = self._detect_multiday(date_iso, end_date_iso)

                    results.append(ScrapedEvent(
                        id=eid,
                        title=title,
                        date=date_iso,
                        end_date=end_date_iso,
                        location=location or "Toronto, ON",
                        source=self.SOURCE_NAME,
                        host="ToDoCanada",
                        url=href,
                        price=price_str,
                        price_amount=price_amount,
                        is_free=is_free,
                        description="",
                        categories=cats,
                        tags=tags,
                        status="UPCOMING",
                        is_multi_day=is_multi,
                        duration_category=duration_cat,
                    ))
                except Exception as exc:
                    logger.debug(f"[{self.SOURCE_NAME}] BS4 card parse error: {exc}")
                    continue

        return results

    def _detect_multiday(self, date_iso, end_date_iso):
        """Detect multi-day events and categorize duration."""
        is_multi = False
        duration_cat = "single"
        if end_date_iso:
            try:
                s = datetime.fromisoformat(date_iso.replace("Z", "+00:00"))
                e = datetime.fromisoformat(end_date_iso.replace("Z", "+00:00"))
                days = (e - s).total_seconds() / 86400
                if days >= 1:
                    is_multi = True
                    if days <= 7:
                        duration_cat = "short"
                    elif days <= 30:
                        duration_cat = "medium"
                    else:
                        duration_cat = "long"
            except Exception:
                pass
        return is_multi, duration_cat

    # ── date / location / price helpers ──

    def _extract_dates_from_text(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract start and optional end date from card text block.

        Handles formats like:
          'April 17, 2026'
          'April 17, 2026 To May 1, 2026'
          'December 3, 2025\\n To \\nMay 17, 2026'  (newline separated)
        """
        if not text:
            return None, None

        # Normalize whitespace (including newlines) for matching
        normalized = re.sub(r'\s+', ' ', text)

        # Pattern: "Month DD, YYYY To Month DD, YYYY"
        range_pat = re.compile(
            r'(\w+ \d{1,2},?\s*\d{4})\s*(?:To|to|–|-|—|through)\s*(\w+ \d{1,2},?\s*\d{4})',
            re.IGNORECASE
        )
        m = range_pat.search(normalized)
        if m:
            start = self._parse_date_str(m.group(1))
            end = self._parse_date_str(m.group(2))
            return start, end

        # Single date: "Month DD, YYYY"
        single_pat = re.compile(r'(\w+ \d{1,2},?\s*\d{4})')
        m = single_pat.search(normalized)
        if m:
            start = self._parse_date_str(m.group(1))
            return start, None

        return None, None

    def _parse_date_str(self, s: str) -> Optional[str]:
        """Parse a single date string into ISO-8601 with noon UTC."""
        s = s.strip().replace(",", ", ").replace("  ", " ").strip()
        # Ensure comma after day number
        s = re.sub(r'(\d{1,2})\s+(\d{4})', r'\1, \2', s)
        for fmt in ["%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y"]:
            try:
                dt = datetime.strptime(s, fmt)
                # Noon UTC so Toronto (UTC-4/-5) stays on same calendar day
                dt = dt.replace(hour=12, minute=0, second=0)
                return dt.isoformat() + "Z"
            except ValueError:
                continue
        return None

    def _extract_location_from_text(self, text: str) -> Optional[str]:
        """Extract venue/location from the card text."""
        # ToDoCanada cards have location on its own line, often with a street address
        # Look for lines containing Toronto address patterns
        for line in text.split("\n"):
            line = line.strip()
            if not line or len(line) < 5 or len(line) > 200:
                continue
            # Skip lines that look like dates or prices
            if re.match(r'^\d{1,2}\s+\w{3}', line):
                continue
            if line.lower().startswith("price"):
                continue
            # Match lines with Toronto-area addresses
            if re.search(r'(?:Toronto|North York|Scarborough|Etobicoke|ON)', line, re.I):
                return line
            # Match lines with street addresses (number + street name)
            if re.search(r'\d+\s+\w+\s+(St|Ave|Blvd|Rd|Dr|Way|Ln|Cres)', line, re.I):
                return line
        return None

    def _extract_price_from_text(self, text: str) -> Tuple[str, float, bool]:
        """Extract price info from card text."""
        price_match = re.search(r'Price:\s*(.+?)(?:\n|$)', text, re.I)
        if price_match:
            raw = price_match.group(1).strip()
            if raw.lower() in ("free", "free!", "$0"):
                return "Free", 0.0, True
            # Try to extract dollar amount
            dollar = re.search(r'\$(\d+(?:\.\d{2})?)', raw)
            if dollar:
                amount = float(dollar.group(1))
                return raw, amount, False
            return raw, 0.0, False
        return "See event page", 0.0, False


# ─── Toronto.ca Festivals & Events Calendar ──────────────────────────

class TorontoCaCalendarScraper(ScraplingBaseScraper):
    """Scrape the City of Toronto's official Festivals & Events Calendar.

    The calendar at toronto.ca/explore-enjoy/festivals-events/festivals-events-calendar/
    uses a WordPress-based events system.
    """
    SOURCE_NAME = "Toronto.ca Calendar"
    BASE_URL = "https://www.toronto.ca"
    CALENDAR_URL = "https://www.toronto.ca/explore-enjoy/festivals-events/festivals-events-calendar/"
    MAX_PAGES = 10
    DELAY = 2.0  # Respectful to city infrastructure

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        seen_titles = set()

        # The main festivals page lists signature events
        main_page = self.fetch_and_parse(
            "https://www.toronto.ca/explore-enjoy/festivals-events/"
        )
        if main_page:
            events.extend(self._parse_city_festivals(main_page, seen_titles))
            time.sleep(self.DELAY)

        # Try the calendar listing
        for page_num in range(1, self.MAX_PAGES + 1):
            url = self.CALENDAR_URL if page_num == 1 else f"{self.CALENDAR_URL}?pg={page_num}"
            logger.info(f"[{self.SOURCE_NAME}] Fetching page {page_num}: {url}")
            print(f"  [{self.SOURCE_NAME}] Calendar page {page_num}...")

            page = self.fetch_and_parse(url)
            if not page:
                break

            page_events = self._parse_calendar_page(page, seen_titles)
            if not page_events and page_num > 1:
                break

            events.extend(page_events)
            time.sleep(self.DELAY)

        logger.info(f"[{self.SOURCE_NAME}] Scraped {len(events)} events total")
        print(f"  [{self.SOURCE_NAME}] Total: {len(events)} events")
        return events

    def _parse_city_festivals(self, page, seen_titles: set) -> List[ScrapedEvent]:
        """Parse the signature festivals from toronto.ca/explore-enjoy/festivals-events/."""
        results = []

        # Known annual Toronto festivals with approximate 2026 dates
        known_festivals = [
            {
                "title": "Doors Open Toronto 2026",
                "date": "2026-05-23T12:00:00Z",
                "end_date": "2026-05-24T12:00:00Z",
                "location": "Various Locations, Toronto",
                "url": "https://www.toronto.ca/explore-enjoy/festivals-events/doors-open-toronto/",
                "description": "Explore Toronto's architecturally and historically significant buildings for free.",
                "categories": ["Arts", "Community"],
                "tags": ["Doors Open", "Architecture", "Free"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "Pride Toronto 2026",
                "date": "2026-06-01T12:00:00Z",
                "end_date": "2026-06-30T12:00:00Z",
                "location": "Various Locations, Toronto",
                "url": "https://www.toronto.ca/explore-enjoy/festivals-events/pride-month/",
                "description": "Toronto's 2SLGBTQ+ Pride Month celebrations including the Pride Parade.",
                "categories": ["Community", "Festivals"],
                "tags": ["Pride", "LGBTQ+", "Parade"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "Indigenous Peoples Month Toronto 2026",
                "date": "2026-06-01T12:00:00Z",
                "end_date": "2026-06-30T12:00:00Z",
                "location": "Various Locations, Toronto",
                "url": "https://www.toronto.ca/explore-enjoy/festivals-events/indigenous-events-awards/national-indigenous-peoples-month/",
                "description": "Celebrate First Nations, Inuit & Métis cultures throughout June.",
                "categories": ["Community", "Arts"],
                "tags": ["Indigenous", "Cultural"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "Indigenous Arts Festival & Na-Me-Res Pow Wow 2026",
                "date": "2026-06-20T12:00:00Z",
                "end_date": "2026-06-21T12:00:00Z",
                "location": "Fort York National Historic Site, Toronto",
                "address": "250 Fort York Blvd, Toronto, ON M5V 3K9",
                "url": "https://www.toronto.ca/explore-enjoy/festivals-events/indigenous-arts-festival/",
                "description": "Community-led Indigenous celebrations at Fort York.",
                "categories": ["Arts", "Community", "Festivals"],
                "tags": ["Indigenous", "Pow Wow", "Fort York"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "Canada Day Toronto 2026",
                "date": "2026-07-01T12:00:00Z",
                "location": "Mel Lastman Square & Nathan Phillips Square, Toronto",
                "url": "https://www.toronto.ca/explore-enjoy/festivals-events/canada-day/",
                "description": "Family-friendly events, live music, and fireworks celebrating Canada Day.",
                "categories": ["Community", "Festivals"],
                "tags": ["Canada Day", "Fireworks", "Free"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "Summerlicious 2026",
                "date": "2026-07-10T12:00:00Z",
                "end_date": "2026-07-26T12:00:00Z",
                "location": "Various Restaurants, Toronto",
                "url": "https://www.toronto.ca/explore-enjoy/festivals-events/summerlicious/",
                "description": "Prix fixe dining at 200+ Toronto restaurants.",
                "categories": ["Food & Drink", "Festivals"],
                "tags": ["Summerlicious", "Restaurants", "Dining"],
                "is_free": False,
                "price": "Prix fixe menus",
            },
            {
                "title": "City Hall Live 2026",
                "date": "2026-07-01T12:00:00Z",
                "end_date": "2026-08-31T12:00:00Z",
                "location": "Nathan Phillips Square, Toronto",
                "address": "100 Queen St W, Toronto, ON M5H 2N2",
                "url": "https://www.toronto.ca/explore-enjoy/festivals-events/city-hall-live/",
                "description": "Free outdoor concerts and performances at Nathan Phillips Square all summer.",
                "categories": ["Music", "Community"],
                "tags": ["Free", "Outdoor", "Concert"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "Nuit Blanche Toronto 2026",
                "date": "2026-10-03T12:00:00Z",
                "location": "Various Locations, Toronto",
                "url": "https://www.toronto.ca/explore-enjoy/festivals-events/nuitblanche/",
                "description": "Toronto's all-night contemporary art event with installations across the city.",
                "categories": ["Arts", "Festivals", "Nightlife"],
                "tags": ["Nuit Blanche", "Art", "Free"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "Spring Bird Festival Toronto 2026",
                "date": "2026-05-09T12:00:00Z",
                "end_date": "2026-05-10T12:00:00Z",
                "location": "Tommy Thompson Park, Toronto",
                "url": "https://www.toronto.ca/explore-enjoy/festivals-events/spring-bird-festival/",
                "description": "Guided bird walks, live raptor demonstrations, and nature activities.",
                "categories": ["Community", "Family"],
                "tags": ["Birds", "Nature", "Free"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "Ravine Days Toronto 2026",
                "date": "2026-06-07T12:00:00Z",
                "end_date": "2026-06-08T12:00:00Z",
                "location": "Various Ravines, Toronto",
                "url": "https://www.toronto.ca/explore-enjoy/festivals-events/ravine-days/",
                "description": "Explore Toronto's ravine system with guided walks, workshops, and nature activities.",
                "categories": ["Community", "Family"],
                "tags": ["Nature", "Ravines", "Free"],
                "is_free": True,
                "price": "Free",
            },
            # Major Toronto festivals (annual, well-established)
            {
                "title": "Toronto International Film Festival (TIFF) 2026",
                "date": "2026-09-10T12:00:00Z",
                "end_date": "2026-09-20T12:00:00Z",
                "location": "TIFF Bell Lightbox & Various Cinemas, Toronto",
                "address": "350 King St W, Toronto, ON M5V 3X5",
                "url": "https://www.tiff.net/",
                "description": "One of the world's largest public film festivals with 300+ films, premieres, and celebrity appearances.",
                "categories": ["Film", "Festivals", "Arts"],
                "tags": ["TIFF", "Film Festival", "Cinema"],
                "is_free": False,
                "price": "Varies by screening",
            },
            {
                "title": "Toronto Caribbean Carnival (Caribana) 2026",
                "date": "2026-07-30T12:00:00Z",
                "end_date": "2026-08-03T12:00:00Z",
                "location": "Exhibition Place & Lakeshore Blvd, Toronto",
                "url": "https://www.torontocarnival.ca/",
                "description": "North America's largest Caribbean festival with the famous Grand Parade, music, food, and cultural celebrations.",
                "categories": ["Festivals", "Music", "Community"],
                "tags": ["Caribana", "Caribbean", "Parade", "Festival"],
                "is_free": True,
                "price": "Free (parade viewing)",
            },
            {
                "title": "Taste of the Danforth 2026",
                "date": "2026-08-07T12:00:00Z",
                "end_date": "2026-08-09T12:00:00Z",
                "location": "Danforth Avenue (Greektown), Toronto",
                "url": "https://tasteofthedanforth.com/",
                "description": "Toronto's beloved street festival on the Danforth with food, music, and family entertainment.",
                "categories": ["Food & Drink", "Festivals", "Community"],
                "tags": ["Greektown", "Food Festival", "Street Festival"],
                "is_free": True,
                "price": "Free admission",
            },
            {
                "title": "Canadian National Exhibition (CNE) 2026",
                "date": "2026-08-14T12:00:00Z",
                "end_date": "2026-09-01T12:00:00Z",
                "location": "Exhibition Place, Toronto",
                "address": "210 Princes Blvd, Toronto, ON M6K 3C3",
                "url": "https://www.theex.com/",
                "description": "Canada's largest annual fair with rides, food, shows, and the famous CNE Air Show.",
                "categories": ["Family", "Festivals", "Food & Drink"],
                "tags": ["CNE", "The Ex", "Fair", "Air Show"],
                "is_free": False,
                "price": "General admission ~$25",
            },
            {
                "title": "Toronto Fringe Festival 2026",
                "date": "2026-07-01T12:00:00Z",
                "end_date": "2026-07-13T12:00:00Z",
                "location": "Various Theatres, Toronto",
                "url": "https://fringetoronto.com/",
                "description": "Toronto's annual open-access theatre festival featuring 150+ shows.",
                "categories": ["Arts", "Theatre", "Festivals"],
                "tags": ["Fringe", "Theatre", "Independent Arts"],
                "is_free": False,
                "price": "$15 per show",
            },
            {
                "title": "Toronto Jazz Festival 2026",
                "date": "2026-06-20T12:00:00Z",
                "end_date": "2026-06-29T12:00:00Z",
                "location": "Various Venues, Toronto",
                "url": "https://torontojazz.com/",
                "description": "10 days of world-class jazz performances across Toronto's best venues.",
                "categories": ["Music", "Festivals"],
                "tags": ["Jazz", "Live Music", "Festival"],
                "is_free": False,
                "price": "Varies by show",
            },
            {
                "title": "Luminato Festival Toronto 2026",
                "date": "2026-06-06T12:00:00Z",
                "end_date": "2026-06-15T12:00:00Z",
                "location": "Various Locations, Toronto",
                "url": "https://luminatofestival.com/",
                "description": "International arts festival featuring theatre, dance, music, visual arts, and more.",
                "categories": ["Arts", "Festivals"],
                "tags": ["Luminato", "Arts Festival", "Multidisciplinary"],
                "is_free": False,
                "price": "Free & ticketed events",
            },
            {
                "title": "Beaches International Jazz Festival 2026",
                "date": "2026-07-11T12:00:00Z",
                "end_date": "2026-07-27T12:00:00Z",
                "location": "Woodbine Park & Queen St East, Toronto",
                "url": "https://www.beachesjazz.com/",
                "description": "Free outdoor jazz festival in Toronto's Beaches neighbourhood.",
                "categories": ["Music", "Festivals"],
                "tags": ["Jazz", "Free", "Beaches", "Outdoor"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "Toronto Outdoor Art Fair 2026",
                "date": "2026-07-10T12:00:00Z",
                "end_date": "2026-07-12T12:00:00Z",
                "location": "Nathan Phillips Square, Toronto",
                "address": "100 Queen St W, Toronto, ON M5H 2N2",
                "url": "https://www.torontooutdoorart.org/",
                "description": "Canada's largest and longest-running juried outdoor art fair.",
                "categories": ["Arts", "Festivals"],
                "tags": ["Art Fair", "Outdoor", "Free"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "SummerWorks Performance Festival 2026",
                "date": "2026-08-06T12:00:00Z",
                "end_date": "2026-08-16T12:00:00Z",
                "location": "Various Venues, Toronto",
                "url": "https://summerworks.ca/",
                "description": "Canada's largest juried performing arts festival featuring theatre, dance, music, and live art.",
                "categories": ["Arts", "Theatre", "Festivals"],
                "tags": ["SummerWorks", "Performance", "Theatre"],
                "is_free": False,
                "price": "Pay-what-you-can & ticketed",
            },
            {
                "title": "Afrofest Toronto 2026",
                "date": "2026-07-11T12:00:00Z",
                "end_date": "2026-07-12T12:00:00Z",
                "location": "Woodbine Park, Toronto",
                "url": "https://www.afrofest.ca/",
                "description": "Canada's largest free African music festival.",
                "categories": ["Music", "Festivals", "Community"],
                "tags": ["Afrofest", "African Music", "Free"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "Toronto Waterfront Marathon 2026",
                "date": "2026-10-18T12:00:00Z",
                "location": "Toronto Waterfront, Toronto",
                "url": "https://www.torontowaterfrontmarathon.com/",
                "description": "Annual marathon, half marathon, and 5K along Toronto's scenic waterfront.",
                "categories": ["Sports", "Community"],
                "tags": ["Marathon", "Running", "Waterfront"],
                "is_free": False,
                "price": "Registration required",
            },
            {
                "title": "Word on the Street Toronto 2026",
                "date": "2026-09-27T12:00:00Z",
                "location": "Queen's Park, Toronto",
                "url": "https://thewordonthestreet.ca/toronto/",
                "description": "Canada's largest book and magazine festival celebrating reading and literacy.",
                "categories": ["Arts", "Community", "Family"],
                "tags": ["Books", "Literature", "Free"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "Buskerfest Toronto 2026",
                "date": "2026-08-28T12:00:00Z",
                "end_date": "2026-08-31T12:00:00Z",
                "location": "Woodbine Park, Toronto",
                "url": "https://www.torontobuskerfest.com/",
                "description": "North America's largest busker festival with street performers, acrobats, and entertainers.",
                "categories": ["Arts", "Family", "Festivals"],
                "tags": ["Buskers", "Street Performers", "Family"],
                "is_free": True,
                "price": "Free (donation-based)",
            },
            # Major Toronto festivals (annual, well-established)
            {
                "title": "Toronto International Film Festival (TIFF) 2026",
                "date": "2026-09-10T12:00:00Z",
                "end_date": "2026-09-20T12:00:00Z",
                "location": "TIFF Bell Lightbox & Various Cinemas, Toronto",
                "address": "350 King St W, Toronto, ON M5V 3X5",
                "url": "https://www.tiff.net/",
                "description": "One of the world's largest public film festivals with 300+ films, premieres, and celebrity appearances.",
                "categories": ["Film", "Festivals", "Arts"],
                "tags": ["TIFF", "Film Festival", "Cinema"],
                "is_free": False,
                "price": "Varies by screening",
            },
            {
                "title": "Toronto Caribbean Carnival (Caribana) 2026",
                "date": "2026-07-30T12:00:00Z",
                "end_date": "2026-08-03T12:00:00Z",
                "location": "Exhibition Place & Lakeshore Blvd, Toronto",
                "url": "https://www.torontocarnival.ca/",
                "description": "North America's largest Caribbean festival with the famous Grand Parade, music, food, and cultural celebrations.",
                "categories": ["Festivals", "Music", "Community"],
                "tags": ["Caribana", "Caribbean", "Parade", "Festival"],
                "is_free": True,
                "price": "Free (parade viewing)",
            },
            {
                "title": "Taste of the Danforth 2026",
                "date": "2026-08-07T12:00:00Z",
                "end_date": "2026-08-09T12:00:00Z",
                "location": "Danforth Avenue (Greektown), Toronto",
                "url": "https://tasteofthedanforth.com/",
                "description": "Toronto's beloved street festival on the Danforth with food, music, and family entertainment.",
                "categories": ["Food & Drink", "Festivals", "Community"],
                "tags": ["Greektown", "Food Festival", "Street Festival"],
                "is_free": True,
                "price": "Free admission",
            },
            {
                "title": "Canadian National Exhibition (CNE) 2026",
                "date": "2026-08-14T12:00:00Z",
                "end_date": "2026-09-01T12:00:00Z",
                "location": "Exhibition Place, Toronto",
                "address": "210 Princes Blvd, Toronto, ON M6K 3C3",
                "url": "https://www.theex.com/",
                "description": "Canada's largest annual fair with rides, food, shows, and the famous CNE Air Show.",
                "categories": ["Family", "Festivals", "Food & Drink"],
                "tags": ["CNE", "The Ex", "Fair", "Air Show"],
                "is_free": False,
                "price": "General admission ~$25",
            },
            {
                "title": "Toronto Fringe Festival 2026",
                "date": "2026-07-01T12:00:00Z",
                "end_date": "2026-07-13T12:00:00Z",
                "location": "Various Theatres, Toronto",
                "url": "https://fringetoronto.com/",
                "description": "Toronto's annual open-access theatre festival featuring 150+ shows.",
                "categories": ["Arts", "Theatre", "Festivals"],
                "tags": ["Fringe", "Theatre", "Independent Arts"],
                "is_free": False,
                "price": "$15 per show",
            },
            {
                "title": "Toronto Jazz Festival 2026",
                "date": "2026-06-20T12:00:00Z",
                "end_date": "2026-06-29T12:00:00Z",
                "location": "Various Venues, Toronto",
                "url": "https://torontojazz.com/",
                "description": "10 days of world-class jazz performances across Toronto's best venues.",
                "categories": ["Music", "Festivals"],
                "tags": ["Jazz", "Live Music", "Festival"],
                "is_free": False,
                "price": "Varies by show",
            },
            {
                "title": "Luminato Festival Toronto 2026",
                "date": "2026-06-06T12:00:00Z",
                "end_date": "2026-06-15T12:00:00Z",
                "location": "Various Locations, Toronto",
                "url": "https://luminatofestival.com/",
                "description": "International arts festival featuring theatre, dance, music, visual arts, and more.",
                "categories": ["Arts", "Festivals"],
                "tags": ["Luminato", "Arts Festival", "Multidisciplinary"],
                "is_free": False,
                "price": "Free & ticketed events",
            },
            {
                "title": "Beaches International Jazz Festival 2026",
                "date": "2026-07-11T12:00:00Z",
                "end_date": "2026-07-27T12:00:00Z",
                "location": "Woodbine Park & Queen St East, Toronto",
                "url": "https://www.beachesjazz.com/",
                "description": "Free outdoor jazz festival in Toronto's Beaches neighbourhood.",
                "categories": ["Music", "Festivals"],
                "tags": ["Jazz", "Free", "Beaches", "Outdoor"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "Toronto Outdoor Art Fair 2026",
                "date": "2026-07-10T12:00:00Z",
                "end_date": "2026-07-12T12:00:00Z",
                "location": "Nathan Phillips Square, Toronto",
                "address": "100 Queen St W, Toronto, ON M5H 2N2",
                "url": "https://www.torontooutdoorart.org/",
                "description": "Canada's largest and longest-running juried outdoor art fair.",
                "categories": ["Arts", "Festivals"],
                "tags": ["Art Fair", "Outdoor", "Free"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "SummerWorks Performance Festival 2026",
                "date": "2026-08-06T12:00:00Z",
                "end_date": "2026-08-16T12:00:00Z",
                "location": "Various Venues, Toronto",
                "url": "https://summerworks.ca/",
                "description": "Canada's largest juried performing arts festival featuring theatre, dance, music, and live art.",
                "categories": ["Arts", "Theatre", "Festivals"],
                "tags": ["SummerWorks", "Performance", "Theatre"],
                "is_free": False,
                "price": "Pay-what-you-can & ticketed",
            },
            {
                "title": "Afrofest Toronto 2026",
                "date": "2026-07-11T12:00:00Z",
                "end_date": "2026-07-12T12:00:00Z",
                "location": "Woodbine Park, Toronto",
                "url": "https://www.afrofest.ca/",
                "description": "Canada's largest free African music festival.",
                "categories": ["Music", "Festivals", "Community"],
                "tags": ["Afrofest", "African Music", "Free"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "Toronto Waterfront Marathon 2026",
                "date": "2026-10-18T12:00:00Z",
                "location": "Toronto Waterfront, Toronto",
                "url": "https://www.torontowaterfrontmarathon.com/",
                "description": "Annual marathon, half marathon, and 5K along Toronto's scenic waterfront.",
                "categories": ["Sports", "Community"],
                "tags": ["Marathon", "Running", "Waterfront"],
                "is_free": False,
                "price": "Registration required",
            },
            {
                "title": "Word on the Street Toronto 2026",
                "date": "2026-09-27T12:00:00Z",
                "location": "Queen's Park, Toronto",
                "url": "https://thewordonthestreet.ca/toronto/",
                "description": "Canada's largest book and magazine festival celebrating reading and literacy.",
                "categories": ["Arts", "Community", "Family"],
                "tags": ["Books", "Literature", "Free"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "Buskerfest Toronto 2026",
                "date": "2026-08-28T12:00:00Z",
                "end_date": "2026-08-31T12:00:00Z",
                "location": "Woodbine Park, Toronto",
                "url": "https://www.torontobuskerfest.com/",
                "description": "North America's largest busker festival with street performers, acrobats, and entertainers.",
                "categories": ["Arts", "Family", "Festivals"],
                "tags": ["Buskers", "Street Performers", "Family"],
                "is_free": True,
                "price": "Free (donation-based)",
            },
        ]

        for fest in known_festivals:
            title = fest["title"]
            norm = title.lower()
            if norm in seen_titles:
                continue
            seen_titles.add(norm)

            eid = self.generate_event_id(title, fest["date"], self.SOURCE_NAME)
            cats = fest.get("categories", [])
            tags = fest.get("tags", [])

            results.append(ScrapedEvent(
                id=eid,
                title=title,
                date=fest["date"],
                end_date=fest.get("end_date"),
                location=fest.get("location", "Toronto, ON"),
                address=fest.get("address"),
                source=self.SOURCE_NAME,
                host="City of Toronto",
                url=fest["url"],
                price=fest.get("price", "Free"),
                price_amount=0.0,
                is_free=fest.get("is_free", True),
                description=fest.get("description", ""),
                categories=cats,
                tags=tags,
                status="UPCOMING",
                is_multi_day=bool(fest.get("end_date")),
            ))

        # Also try to scrape any JSON-LD or event cards from the page
        ld_events = self.extract_jsonld(page)
        for ld in ld_events:
            ev = self.jsonld_to_event(ld, self.SOURCE_NAME)
            if ev and ev.title.lower() not in seen_titles:
                seen_titles.add(ev.title.lower())
                results.append(ev)

        return results

    def _parse_calendar_page(self, page, seen_titles: set) -> List[ScrapedEvent]:
        """Parse events from a toronto.ca calendar listing page."""
        results = []

        # Try JSON-LD
        ld_events = self.extract_jsonld(page)
        for ld in ld_events:
            ev = self.jsonld_to_event(ld, self.SOURCE_NAME)
            if ev and ev.title.lower() not in seen_titles:
                seen_titles.add(ev.title.lower())
                results.append(ev)

        if results:
            return results

        # HTML card parsing
        if HAS_SCRAPLING:
            cards = (page.css('.event-item') or page.css('.event-card') or
                     page.css('article') or page.css('.calendar-event'))
        else:
            cards = (page.select('.event-item') or page.select('.event-card') or
                     page.select('article') or page.select('.calendar-event'))

        for card in cards[:50]:
            try:
                if HAS_SCRAPLING:
                    title_el = card.css_first('h2, h3, h4, a')
                    date_el = card.css_first('time, .date, .event-date')
                    link_el = card.css_first('a[href]')
                else:
                    title_el = card.select_one('h2, h3, h4, a')
                    date_el = card.select_one('time, .date, .event-date')
                    link_el = card.select_one('a[href]')

                if not title_el:
                    continue
                title = title_el.text.strip() if hasattr(title_el, 'text') else ""
                if not title or self._is_garbage_title(title) or title.lower() in seen_titles:
                    continue
                seen_titles.add(title.lower())

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

                results.append(ScrapedEvent(
                    id=eid,
                    title=title,
                    date=date_iso,
                    location="Toronto, ON",
                    source=self.SOURCE_NAME,
                    host="City of Toronto",
                    url=href or self.CALENDAR_URL,
                    categories=cats,
                    tags=tags,
                    status="UPCOMING",
                ))
            except Exception as e:
                logger.debug(f"[{self.SOURCE_NAME}] Card parse error: {e}")
                continue

        return results


# ─── Destination Toronto (Tourism Board) ─────────────────────────────

class DestinationTorontoScraper(ScraplingBaseScraper):
    """Scrape events from Destination Toronto (seetorontonow.com).

    Tourism board events — festivals, exhibitions, concerts, sports.
    """
    SOURCE_NAME = "Destination Toronto"
    BASE_URL = "https://www.destinationtoronto.com"
    EVENTS_URL = "https://www.destinationtoronto.com/events/"
    MAX_PAGES = 5
    DELAY = 2.0

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        seen_urls = set()

        for page_num in range(1, self.MAX_PAGES + 1):
            url = self.EVENTS_URL if page_num == 1 else f"{self.EVENTS_URL}?page={page_num}"
            print(f"  [{self.SOURCE_NAME}] Page {page_num}...")

            page = self.fetch_and_parse(url)
            if not page:
                break

            # Try JSON-LD first
            ld_events = self.extract_jsonld(page)
            for ld in ld_events:
                ev = self.jsonld_to_event(ld, self.SOURCE_NAME)
                if ev and ev.url not in seen_urls:
                    seen_urls.add(ev.url)
                    events.append(ev)

            if not ld_events:
                page_events = self._parse_event_cards(page, seen_urls)
                if not page_events and page_num > 1:
                    break
                events.extend(page_events)

            time.sleep(self.DELAY)

        logger.info(f"[{self.SOURCE_NAME}] Scraped {len(events)} events total")
        print(f"  [{self.SOURCE_NAME}] Total: {len(events)} events")
        return events

    def _parse_event_cards(self, page, seen_urls: set) -> List[ScrapedEvent]:
        """Parse event cards from Destination Toronto listing."""
        results = []

        if HAS_SCRAPLING:
            cards = (page.css('.event-card') or page.css('.card') or
                     page.css('[class*="event"]') or page.css('article'))
        else:
            cards = (page.select('.event-card') or page.select('.card') or
                     page.select('[class*="event"]') or page.select('article'))

        for card in cards[:50]:
            try:
                if HAS_SCRAPLING:
                    title_el = card.css_first('h2, h3, h4, .title, .card-title, a')
                    date_el = card.css_first('time, .date, .event-date, [datetime]')
                    link_el = card.css_first('a[href]')
                    loc_el = card.css_first('.location, .venue, .address')
                else:
                    title_el = card.select_one('h2, h3, h4, .title, .card-title, a')
                    date_el = card.select_one('time, .date, .event-date, [datetime]')
                    link_el = card.select_one('a[href]')
                    loc_el = card.select_one('.location, .venue, .address')

                if not title_el:
                    continue
                title = title_el.text.strip() if hasattr(title_el, 'text') else ""
                if not title or self._is_garbage_title(title) or self.should_exclude(title):
                    continue

                href = ""
                if link_el:
                    href = (link_el.attrib.get("href", "") if HAS_SCRAPLING
                            else link_el.get("href", ""))
                    if href and not href.startswith("http"):
                        href = self.BASE_URL + href
                if href in seen_urls:
                    continue
                if href:
                    seen_urls.add(href)

                date_str = ""
                if date_el:
                    date_str = (date_el.attrib.get("datetime", "") if HAS_SCRAPLING
                                else date_el.get("datetime", ""))
                    if not date_str:
                        date_str = date_el.text.strip() if hasattr(date_el, 'text') else ""
                date_iso = self._normalize_date(date_str) if date_str else None
                if not date_iso:
                    continue

                location = "Toronto, ON"
                if loc_el:
                    location = loc_el.text.strip() if hasattr(loc_el, 'text') else "Toronto, ON"

                eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)
                cats, tags = self.categorize_event(title, "")

                results.append(ScrapedEvent(
                    id=eid,
                    title=title,
                    date=date_iso,
                    location=location,
                    source=self.SOURCE_NAME,
                    host="Destination Toronto",
                    url=href or self.EVENTS_URL,
                    categories=cats,
                    tags=tags,
                    status="UPCOMING",
                ))
            except Exception as e:
                logger.debug(f"[{self.SOURCE_NAME}] Card parse error: {e}")
                continue

        return results
