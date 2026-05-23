#!/usr/bin/env python3
"""
Additional Toronto event sources — high-volume sources not yet in the pipeline.

Targets:
  1. Songkick API — concert/tour aggregator (API, metro area 27396 = Toronto)
  2. Mirvish Theatres — Princess of Wales, Royal Alexandra, Ed Mirvish, CAA Theatre
  3. Resident Advisor — electronic/DJ events (HTML scraping)
  4. Toronto Zoo — family events, seasonal programs
  5. Luma — tech/community event platform (API with key)

Uses ScraplingBaseScraper for HTML sources; direct API calls for Songkick/Luma.
"""
import json
import os
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
    from .base_scraper import BaseScraper, ScrapedEvent
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from scrapling_enhanced import ScraplingBaseScraper
    from base_scraper import BaseScraper, ScrapedEvent

logger = logging.getLogger(__name__)


# ─── Songkick API ────────────────────────────────────────────────────

class SongkickScraper(BaseScraper):
    """Songkick concert/tour aggregator — API-driven.

    Songkick groups cities as metro areas.  Toronto = metro area 27396.
    API docs: https://www.songkick.com/developer/
    Requires SONGKICK_API_KEY environment variable (free tier: 1000 req/day).
    """
    SOURCE_NAME = "Songkick"
    BASE_URL = "https://api.songkick.com/api/3.0"
    TORONTO_METRO_AREA_ID = 27396
    MAX_PAGES = 20  # ~50 events/page = up to 1000 events

    def __init__(self, api_key: str = None):
        super().__init__()
        self.api_key = api_key or os.getenv("SONGKICK_API_KEY")
        if not self.api_key:
            print(f"[{self.SOURCE_NAME}] Warning: No API key. Set SONGKICK_API_KEY env var.")
            print(f"[{self.SOURCE_NAME}] Register free at: https://www.songkick.com/developer/api-key")

    def _make_request(self, url: str, params: Dict = None) -> Optional[Dict]:
        """Make API request to Songkick."""
        try:
            if not self.api_key:
                return None
            params = params or {}
            params["apikey"] = self.api_key
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(f"[{self.SOURCE_NAME}] API error: {e}")
            return None

    def _parse_event(self, event_data: Dict) -> Optional[ScrapedEvent]:
        """Convert a Songkick event JSON object to ScrapedEvent."""
        try:
            display_name = event_data.get("displayName", "")
            if not display_name or self.should_exclude(display_name):
                return None

            # Songkick dates: start.date (YYYY-MM-DD) or start.datetime (ISO)
            start = event_data.get("start", {})
            start_date_str = start.get("date") or start.get("datetime", "")
            if not start_date_str:
                return None

            # Format: date-only → noon UTC; datetime → keep as-is
            if len(start_date_str) == 10:  # YYYY-MM-DD
                date_iso = f"{start_date_str}T12:00:00Z"
            else:
                date_iso = start_date_str
                if not date_iso.endswith("Z"):
                    date_iso += "Z"
                # Fix bare midnight
                if date_iso.endswith("T00:00:00Z"):
                    date_iso = date_iso.replace("T00:00:00Z", "T12:00:00Z")

            # End date
            end_data = event_data.get("end", {})
            end_date_str = end_data.get("date") or end_data.get("datetime", "") if end_data else ""
            end_iso = None
            if end_date_str:
                if len(end_date_str) == 10:
                    end_iso = f"{end_date_str}T12:00:00Z"
                else:
                    end_iso = end_date_str
                    if not end_iso.endswith("Z"):
                        end_iso += "Z"

            # Venue / location
            venue_data = event_data.get("venue", {})
            venue_name = venue_data.get("displayName", "Toronto, ON")
            venue_lat = venue_data.get("lat")
            venue_lng = venue_data.get("lng")
            # Try to get address from venue metro area
            metro = venue_data.get("metroArea", {})
            city = metro.get("displayName", "Toronto")
            country = metro.get("country", {}).get("displayName", "Canada")

            address = None
            if venue_lat and venue_lng:
                address = f"{venue_name}, {city}"

            # URL
            event_url = event_data.get("uri", "")

            # Type (Concert, Festival)
            event_type = event_data.get("type", "Concert")
            is_festival = event_type == "Festival"

            # Artists / performers
            performance = event_data.get("performance", [])
            artist_names = [p.get("artist", {}).get("displayName", "") for p in performance[:5]]
            headliner = artist_names[0] if artist_names else ""
            description = f"Featuring {', '.join(artist_names)}"
            if is_festival:
                description = f"Festival — {description}"

            # Multi-day
            is_multi = is_festival or bool(end_iso)
            duration_cat = "single"
            if is_multi and end_iso and date_iso:
                try:
                    s = datetime.fromisoformat(date_iso.replace("Z", "+00:00"))
                    e = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
                    days = (e - s).days
                    if days <= 7:
                        duration_cat = "short"
                    elif days <= 30:
                        duration_cat = "medium"
                    else:
                        duration_cat = "long"
                except Exception:
                    pass

            # Price — Songkick doesn't provide prices in API
            price_display = "See Tickets"
            price_amount = 0.0
            is_free = False

            eid = self.generate_event_id(display_name, date_iso, self.SOURCE_NAME)
            cats, tags = self.categorize_event(display_name, description)
            if is_festival and "Festival" not in tags:
                tags.append("Festival")
                if "Community" not in cats:
                    cats.append("Community")

            return ScrapedEvent(
                id=eid,
                title=display_name,
                date=date_iso,
                end_date=end_iso if is_multi else None,
                location=venue_name,
                address=address,
                lat=float(venue_lat) if venue_lat else None,
                lng=float(venue_lng) if venue_lng else None,
                source=self.SOURCE_NAME,
                host=headliner,
                url=event_url,
                price=price_display,
                price_amount=price_amount,
                is_free=is_free,
                description=description[:500],
                categories=cats,
                tags=tags,
                status="UPCOMING",
                is_multi_day=is_multi,
                duration_category=duration_cat,
            )
        except Exception as e:
            logger.debug(f"[{self.SOURCE_NAME}] Parse error: {e}")
            return None

    def scrape(self) -> List[ScrapedEvent]:
        """Scrape Songkick events for Toronto metro area."""
        events = []

        # Try API first if key is available
        if self.api_key:
            events.extend(self._scrape_api())
        else:
            print(f"[{self.SOURCE_NAME}] No API key, trying HTML fallback.")

        # Always try HTML discovery as fallback / supplement
        html_events = self._scrape_html_discovery()
        events.extend(html_events)

        # Dedup by (title, date) — API and HTML may return same events
        seen = set()
        deduped = []
        for ev in events:
            key = (ev.title, ev.date)
            if key not in seen:
                seen.add(key)
                deduped.append(ev)

        print(f"[{self.SOURCE_NAME}] Scraped {len(deduped)} events total (after dedup)")
        return deduped

    def _scrape_api(self) -> List[ScrapedEvent]:
        """Use Songkick API to fetch Toronto events."""
        events = []

        print(f"[{self.SOURCE_NAME}] Starting API scrape (metro area {self.TORONTO_METRO_AREA_ID})...")

        now_str = datetime.utcnow().strftime("%Y-%m-%d")
        future = datetime.utcnow() + timedelta(days=210)  # ~7 months
        future_str = future.strftime("%Y-%m-%d")

        for page in range(1, self.MAX_PAGES + 1):
            url = f"{self.BASE_URL}/metro_areas/{self.TORONTO_METRO_AREA_ID}/calendar.json"
            params = {
                "page": page,
                "min_date": now_str,
                "max_date": future_str,
                "per_page": 50,
            }

            data = self._make_request(url, params)
            if not data:
                break

            results_page = data.get("resultsPage", {})
            status = results_page.get("status", "")
            if status == "error":
                logger.warning(f"[{self.SOURCE_NAME}] API error: {results_page.get('message', 'unknown')}")
                break

            event_entries = results_page.get("results", {}).get("event", [])
            if not event_entries:
                break

            for ev_data in event_entries:
                ev = self._parse_event(ev_data)
                if ev:
                    events.append(ev)

            total = results_page.get("totalEntries", 0)
            per_page = results_page.get("perPage", 50)
            if page * per_page >= total:
                break

            print(f"  [{self.SOURCE_NAME}] Page {page}: {len(event_entries)} events (total: {total})")

        print(f"[{self.SOURCE_NAME}] API: {len(events)} events")
        return events

    def _scrape_html_discovery(self) -> List[ScrapedEvent]:
        """Fallback: HTML scrape Songkick Toronto pages when no API key."""
        events = []
        seen_urls = set()

        urls = [
            "https://www.songkick.com/metro-areas/27396-toronto",
        ]

        for url in urls:
            try:
                if HAS_SCRAPLING:
                    fetcher = Fetcher(auto_match=False)
                    page = fetcher.get(url, timeout=30)
                else:
                    resp = self.session.get(url, timeout=30, headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    })
                    if resp.status_code != 200:
                        logger.debug(f"[{self.SOURCE_NAME}] HTML {resp.status_code} for {url}")
                        continue
                    from bs4 import BeautifulSoup
                    page = BeautifulSoup(resp.text, "html.parser")

                if not page:
                    continue

                if HAS_SCRAPLING:
                    items = page.css('.event-listings .event-item, .event-listings article, '
                                     '[data-type="event"], .concert-event, .festival-event')
                else:
                    items = page.select('.event-listings .event-item, .event-listings article, '
                                       '[data-type="event"], .concert-event, .festival-event')

                for item in items[:60]:
                    try:
                        ev = self._parse_html_event(item, url, seen_urls)
                        if ev:
                            events.append(ev)
                    except Exception:
                        continue

            except Exception as e:
                logger.debug(f"[{self.SOURCE_NAME}] HTML scrape error: {e}")

        if events:
            print(f"[{self.SOURCE_NAME}] HTML fallback: {len(events)} events")
        else:
            print(f"[{self.SOURCE_NAME}] HTML fallback: no events found (site may block scraping)")

        return events

    def _parse_html_event(self, item, base_url: str, seen_urls: set) -> Optional[ScrapedEvent]:
        """Parse a single event from Songkick HTML listing."""
        try:
            if HAS_SCRAPLING:
                title_el = item.css_first('a.title, .event-title a, a[href*="/concerts/"], a[href*="/festivals/"], h2 a, .summary a')
                date_el = item.css_first('time, .date, [datetime], .event-date')
                venue_el = item.css_first('.venue-name, .location, [data-type="venue"] a')
                link_el = item.css_first('a[href*="/concerts/"], a[href*="/festivals/"], .summary a')
            else:
                title_el = item.select_one('a.title, .event-title a, a[href*="/concerts/"], a[href*="/festivals/"], h2 a, .summary a')
                date_el = item.select_one('time, .date, [datetime], .event-date')
                venue_el = item.select_one('.venue-name, .location, [data-type="venue"] a')
                link_el = item.select_one('a[href*="/concerts/"], a[href*="/festivals/"], .summary a')

            title = ""
            if title_el:
                title = title_el.text.strip() if hasattr(title_el, 'text') else str(title_el.string or "").strip()
            if not title or self.should_exclude(title):
                return None

            href = ""
            if link_el:
                href = (link_el.attrib.get("href", "") if HAS_SCRAPLING
                        else link_el.get("href", ""))
                if href and not href.startswith("http"):
                    href = "https://www.songkick.com" + href
            if href in seen_urls:
                return None
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
                item_text = item.text.strip() if hasattr(item, 'text') else ""
                date_iso = self._parse_date_from_text(item_text)
            if not date_iso:
                return None

            venue_name = "Toronto, ON"
            if venue_el:
                venue_name = venue_el.text.strip() if hasattr(venue_el, 'text') else "Toronto, ON"

            eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)
            cats, tags = self.categorize_event(title, "")
            is_festival = "festival" in title.lower()
            if is_festival:
                tags = list(set(tags + ["Festival"]))

            return ScrapedEvent(
                id=eid,
                title=title,
                date=date_iso,
                location=venue_name,
                source=self.SOURCE_NAME,
                host=title.split(" at ")[0].strip() if " at " in title else "",
                url=href or base_url,
                price="See Tickets",
                categories=cats,
                tags=tags,
                status="UPCOMING",
            )
        except Exception:
            return None


# ─── Mirvish Theatres ─────────────────────────────────────────────────

class MirvishTheatresScraper(ScraplingBaseScraper):
    """Mirvish Productions — Princess of Wales, Royal Alexandra,
    Ed Mirvish, CAA Theatre.

    Major Toronto theatre source for Broadway tours, plays, musicals.
    Scrapes mirvish.com for show listings.
    """
    SOURCE_NAME = "Mirvish Theatres"
    BASE_URL = "https://www.mirvish.com"
    DELAY = 1.5

    VENUES = {
        "princess of wales": {
            "name": "Princess of Wales Theatre",
            "lat": 43.6475, "lng": -79.3904,
            "address": "300 King St W, Toronto, ON M5V 1J2",
        },
        "royal alexandra": {
            "name": "Royal Alexandra Theatre",
            "lat": 43.6504, "lng": -79.3847,
            "address": "260 King St W, Toronto, ON M5V 1H8",
        },
        "ed mirvish": {
            "name": "Ed Mirvish Theatre",
            "lat": 43.6572, "lng": -79.3806,
            "address": "244 Victoria St, Toronto, ON M5B 1V6",
        },
        "caa theatre": {
            "name": "CAA Theatre",
            "lat": 43.6524, "lng": -79.3797,
            "address": "651 Yonge St, Toronto, ON M4Y 1Z9",
        },
        "panasonic": {
            "name": "Panasonic Theatre",
            "lat": 43.6529, "lng": -79.3801,
            "address": "651 Yonge St, Toronto, ON M4Y 1Z9",
        },
    }

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        seen_urls = set()

        urls = [
            f"{self.BASE_URL}/shows",
            f"{self.BASE_URL}/shows?category=now-playing",
            f"{self.BASE_URL}/shows?category=coming-soon",
        ]

        for url in urls:
            page = self.fetch_and_parse(url)
            if not page:
                continue

            # Try JSON-LD first
            ld_events = self.extract_jsonld(page)
            for ld in ld_events:
                ev = self.jsonld_to_event(ld, self.SOURCE_NAME, url)
                if ev and ev.url not in seen_urls:
                    seen_urls.add(ev.url)
                    self._assign_venue(ev)
                    events.append(ev)

            # HTML fallback
            if not ld_events:
                page_events = self._parse_show_cards(page, url, seen_urls)
                events.extend(page_events)

            time.sleep(self.DELAY)

        logger.info(f"[{self.SOURCE_NAME}] Scraped {len(events)} events")
        print(f"[{self.SOURCE_NAME}] Scraped {len(events)} events")
        return events

    def _assign_venue(self, ev: ScrapedEvent):
        """Try to match event location to a known Mirvish venue."""
        loc_lower = (ev.location or "").lower()
        desc_lower = (ev.description or "").lower()
        combined = f"{loc_lower} {desc_lower} {ev.title.lower()}"

        for key, venue in self.VENUES.items():
            if key in combined or venue["name"].lower() in combined:
                ev.location = venue["name"]
                ev.lat = venue["lat"]
                ev.lng = venue["lng"]
                ev.address = venue["address"]
                return

    def _parse_show_cards(self, page, base_url: str, seen_urls: set) -> List[ScrapedEvent]:
        """Parse Mirvish show cards from HTML."""
        results = []

        if HAS_SCRAPLING:
            cards = (page.css('.show-card, .production-card, .show-item, '
                              '[class*="show"], [class*="production"], article'))
        else:
            cards = page.select('.show-card, .production-card, .show-item, '
                                '[class*="show"], [class*="production"], article')

        for card in cards[:40]:
            try:
                if HAS_SCRAPLING:
                    title_el = card.css_first('h2, h3, h4, .title, .show-title, a')
                    date_el = card.css_first('.date, time, [datetime], .show-dates, .dates')
                    link_el = card.css_first('a[href]')
                    img_el = card.css_first('img[src], img[data-src]')
                    venue_el = card.css_first('.venue, .location, .theatre')
                    desc_el = card.css_first('p, .description, .synopsis')
                else:
                    title_el = card.select_one('h2, h3, h4, .title, .show-title, a')
                    date_el = card.select_one('.date, time, [datetime], .show-dates, .dates')
                    link_el = card.select_one('a[href]')
                    img_el = card.select_one('img[src], img[data-src]')
                    venue_el = card.select_one('.venue, .location, .theatre')
                    desc_el = card.select_one('p, .description, .synopsis')

                if not title_el:
                    continue

                title = title_el.text.strip() if hasattr(title_el, 'text') else str(title_el.string or "").strip()
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

                # Date parsing — Mirvish often shows "Apr 15 – Jun 28, 2026"
                date_str = ""
                if date_el:
                    date_str = (date_el.attrib.get("datetime", "") if HAS_SCRAPLING
                                else date_el.get("datetime", ""))
                    if not date_str:
                        date_str = date_el.text.strip() if hasattr(date_el, 'text') else ""

                # Mirvish-specific date range parsing
                date_iso, end_iso = self._parse_mirvish_date(date_str)
                if not date_iso:
                    # Try the base class normalizer
                    date_iso = self._normalize_date(date_str) if date_str else None
                if not date_iso:
                    continue

                # Venue
                venue_name = "Mirvish Theatre"
                if venue_el:
                    venue_name = venue_el.text.strip() if hasattr(venue_el, 'text') else venue_name

                # Image
                img = ""
                if img_el:
                    img = (img_el.attrib.get("src", "") or img_el.attrib.get("data-src", "")
                           if HAS_SCRAPLING else img_el.get("src", "") or img_el.get("data-src", ""))

                # Description
                desc = ""
                if desc_el:
                    desc = desc_el.text.strip()[:300] if hasattr(desc_el, 'text') else ""

                # Multi-day
                is_multi = bool(end_iso)
                duration_cat = "single"
                if is_multi and end_iso:
                    try:
                        s = datetime.fromisoformat(date_iso.replace("Z", "+00:00"))
                        e = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
                        days = (e - s).days
                        if days <= 7:
                            duration_cat = "short"
                        elif days <= 30:
                            duration_cat = "medium"
                        else:
                            duration_cat = "long"
                    except Exception:
                        pass

                eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)
                cats, tags = self.categorize_event(title, desc)
                tags = list(set(tags + ["Theatre", "Mirvish"]))

                ev = ScrapedEvent(
                    id=eid,
                    title=title,
                    date=date_iso,
                    end_date=end_iso if is_multi else None,
                    location=venue_name,
                    source=self.SOURCE_NAME,
                    host="Mirvish Productions",
                    url=href or base_url,
                    price="See Tickets",
                    description=desc,
                    categories=cats,
                    tags=tags,
                    status="UPCOMING",
                    is_multi_day=is_multi,
                    duration_category=duration_cat,
                    image=img if img else None,
                )
                self._assign_venue(ev)
                results.append(ev)
            except Exception as e:
                logger.debug(f"[{self.SOURCE_NAME}] Card parse error: {e}")
                continue

        return results

    def _parse_mirvish_date(self, date_str: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse Mirvish date formats like 'Apr 15 – Jun 28, 2026' or 'May 2026'."""
        if not date_str:
            return None, None

        date_str = date_str.strip()

        # Pattern: "Month DD – Month DD, YYYY" or "Month DD - Month DD, YYYY"
        range_pat = re.compile(
            r'(\w{3,9}\.?\s+\d{1,2})\s*[–\-—]\s*(\w{3,9}\.?\s+\d{1,2}),?\s*(\d{4})',
            re.IGNORECASE
        )
        m = range_pat.search(date_str)
        if m:
            year = int(m.group(3))
            start = self._parse_month_day(m.group(1), year)
            end = self._parse_month_day(m.group(2), year)
            return start, end

        # Pattern: "Month DD, YYYY"
        single_pat = re.compile(r'(\w{3,9}\.?\s+\d{1,2},?\s*\d{4})', re.IGNORECASE)
        m = single_pat.search(date_str)
        if m:
            parsed = self._normalize_date(m.group(1))
            return parsed, None

        # Pattern: just "Month YYYY" — use 1st of the month
        month_year = re.compile(r'(\w{3,9})\s+(\d{4})', re.IGNORECASE)
        m = month_year.search(date_str)
        if m:
            month_str = m.group(1)
            year = int(m.group(2))
            for fmt in ["%B", "%b"]:
                try:
                    dt = datetime.strptime(month_str, fmt)
                    dt = dt.replace(year=year, day=1, hour=12, minute=0, second=0)
                    return dt.isoformat() + "Z", None
                except ValueError:
                    continue

        return None, None

    def _parse_month_day(self, text: str, year: int) -> Optional[str]:
        """Parse 'Apr 15' or 'April 15' into ISO with noon UTC."""
        text = text.strip().rstrip('.')
        for fmt in ["%B %d", "%b %d"]:
            try:
                dt = datetime.strptime(text, fmt)
                dt = dt.replace(year=year, hour=12, minute=0, second=0)
                return dt.isoformat() + "Z"
            except ValueError:
                continue
        return None


# ─── Resident Advisor ─────────────────────────────────────────────────

class ResidentAdvisorScraper(ScraplingBaseScraper):
    """Resident Advisor — electronic music / DJ events in Toronto.

    RA has a well-structured event listing for Toronto with date,
    venue, artist, and ticket info. HTML scraping.
    """
    SOURCE_NAME = "Resident Advisor"
    BASE_URL = "https://www.residentadvisor.net"
    EVENTS_URL = "https://www.residentadvisor.net/events/toronto"
    MAX_PAGES = 8
    DELAY = 1.5

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        seen_urls = set()

        # RA shows week-by-week; scrape current + upcoming weeks
        for page_num in range(self.MAX_PAGES):
            url = f"{self.EVENTS_URL}/week/{page_num}" if page_num > 0 else self.EVENTS_URL
            print(f"  [{self.SOURCE_NAME}] Page {page_num + 1}...")

            page = self.fetch_and_parse(url)
            if not page:
                break

            # Try JSON-LD
            ld_events = self.extract_jsonld(page)
            for ld in ld_events:
                ev = self.jsonld_to_event(ld, self.SOURCE_NAME, url)
                if ev and ev.url not in seen_urls:
                    seen_urls.add(ev.url)
                    events.append(ev)

            # HTML fallback — RA uses structured event list items
            if not ld_events:
                page_events = self._parse_event_list(page, url, seen_urls)
                if not page_events and page_num > 2:
                    break
                events.extend(page_events)

            time.sleep(self.DELAY)

        logger.info(f"[{self.SOURCE_NAME}] Scraped {len(events)} events")
        print(f"[{self.SOURCE_NAME}] Scraped {len(events)} events")
        return events

    def _parse_event_list(self, page, base_url: str, seen_urls: set) -> List[ScrapedEvent]:
        """Parse RA event list items."""
        results = []

        # RA event list structure: ul#items or .event-list items
        if HAS_SCRAPLING:
            items = (page.css('.event-item, .event-list-item, [data-type="event"], '
                             '.evt-detail, li.event') or page.css('ul.items li'))
        else:
            items = (page.select('.event-item, .event-list-item, [data-type="event"], '
                                 '.evt-detail, li.event') or page.select('ul.items li'))

        for item in items[:50]:
            try:
                if HAS_SCRAPLING:
                    title_el = item.css_first('h1, .title, .event-title, a[href*="/events/"]')
                    date_el = item.css_first('time, .date, [datetime], .event-date')
                    link_el = item.css_first('a[href*="/events/"]')
                    venue_el = item.css_first('.venue, .location, [data-type="venue"] a, .venue-name')
                    artist_el = item.css_first('.artists, .lineup, .dj-name')
                else:
                    title_el = item.select_one('h1, .title, .event-title, a[href*="/events/"]')
                    date_el = item.select_one('time, .date, [datetime], .event-date')
                    link_el = item.select_one('a[href*="/events/"]')
                    venue_el = item.select_one('.venue, .location, [data-type="venue"] a, .venue-name')
                    artist_el = item.select_one('.artists, .lineup, .dj-name')

                # Title — RA titles often include the headliner
                title = ""
                if title_el:
                    title = title_el.text.strip() if hasattr(title_el, 'text') else str(title_el.string or "").strip()
                if not title or self._is_garbage_title(title) or self.should_exclude(title):
                    continue

                # URL
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

                # Date
                date_str = ""
                if date_el:
                    date_str = (date_el.attrib.get("datetime", "") if HAS_SCRAPLING
                                else date_el.get("datetime", ""))
                    if not date_str:
                        date_str = date_el.text.strip() if hasattr(date_el, 'text') else ""
                date_iso = self._normalize_date(date_str) if date_str else None

                # RA also embeds date in the page context (e.g., "Friday 18 April 2025")
                if not date_iso:
                    # Try to extract from surrounding text
                    item_text = item.text.strip() if hasattr(item, 'text') else ""
                    date_iso = self._parse_date_from_text(item_text)

                if not date_iso:
                    continue

                # Venue
                venue_name = "Toronto, ON"
                if venue_el:
                    venue_name = venue_el.text.strip() if hasattr(venue_el, 'text') else "Toronto, ON"

                # Artists for description
                desc = ""
                if artist_el:
                    desc = artist_el.text.strip()[:300] if hasattr(artist_el, 'text') else ""

                eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)
                cats, tags = self.categorize_event(title, desc)
                tags = list(set(tags + ["Electronic", "DJ"]))

                results.append(ScrapedEvent(
                    id=eid,
                    title=title,
                    date=date_iso,
                    location=venue_name,
                    source=self.SOURCE_NAME,
                    host=title,
                    url=href or base_url,
                    price="See Tickets",
                    description=desc,
                    categories=cats,
                    tags=tags,
                    status="UPCOMING",
                ))
            except Exception as e:
                logger.debug(f"[{self.SOURCE_NAME}] Item parse error: {e}")
                continue

        return results


# ─── Toronto Zoo ──────────────────────────────────────────────────────

class TorontoZooScraper(ScraplingBaseScraper):
    """Toronto Zoo events — family events, seasonal programs, exhibits.

    The zoo has a well-structured events page.
    """
    SOURCE_NAME = "Toronto Zoo"
    BASE_URL = "https://www.torontozoo.com"
    DELAY = 1.5

    VENUE_LAT = 43.8176
    VENUE_LNG = -79.1847
    VENUE_ADDRESS = "2000 Meadowvale Rd, Toronto, ON M1B 5K7"

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        seen_titles = set()

        urls = [
            f"{self.BASE_URL}/events",
            f"{self.BASE_URL}/calendar",
            f"{self.BASE_URL}/whats-on",
        ]

        for url in urls:
            page = self.fetch_and_parse(url)
            if not page:
                continue

            # Try JSON-LD
            ld_events = self.extract_jsonld(page)
            for ld in ld_events:
                ev = self.jsonld_to_event(ld, self.SOURCE_NAME, url)
                if ev and ev.title.lower() not in seen_titles:
                    seen_titles.add(ev.title.lower())
                    ev.lat = self.VENUE_LAT
                    ev.lng = self.VENUE_LNG
                    ev.address = self.VENUE_ADDRESS
                    events.append(ev)

            # HTML fallback
            if not ld_events:
                page_events = self._parse_event_cards(page, url, seen_titles)
                events.extend(page_events)

            time.sleep(self.DELAY)

        # Add known seasonal zoo events if not already found
        events.extend(self._known_zoo_events(seen_titles))

        logger.info(f"[{self.SOURCE_NAME}] Scraped {len(events)} events")
        print(f"[{self.SOURCE_NAME}] Scraped {len(events)} events")
        return events

    def _parse_event_cards(self, page, base_url: str, seen_titles: set) -> List[ScrapedEvent]:
        """Parse event cards from Toronto Zoo pages."""
        results = []

        if HAS_SCRAPLING:
            cards = (page.css('.event-card, .event-item, .calendar-event, '
                              '[class*="event"], article, .card'))
        else:
            cards = page.select('.event-card, .event-item, .calendar-event, '
                                '[class*="event"], article, .card')

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
                if title.lower() in seen_titles:
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

                img = ""
                if img_el:
                    img = (img_el.attrib.get("src", "") if HAS_SCRAPLING
                           else img_el.get("src", ""))

                desc = ""
                if desc_el:
                    desc = desc_el.text.strip()[:300] if hasattr(desc_el, 'text') else ""

                eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)
                cats, tags = self.categorize_event(title, desc)
                tags = list(set(tags + ["Zoo", "Family", "Wildlife"]))

                results.append(ScrapedEvent(
                    id=eid,
                    title=title,
                    date=date_iso,
                    location=self.SOURCE_NAME,
                    address=self.VENUE_ADDRESS,
                    lat=self.VENUE_LAT,
                    lng=self.VENUE_LNG,
                    source=self.SOURCE_NAME,
                    host="Toronto Zoo",
                    url=href or base_url,
                    description=desc,
                    categories=cats,
                    tags=tags,
                    image=img if img else None,
                    status="UPCOMING",
                ))
            except Exception as e:
                logger.debug(f"[{self.SOURCE_NAME}] Card parse error: {e}")
                continue

        return results

    def _known_zoo_events(self, seen_titles: set) -> List[ScrapedEvent]:
        """Known seasonal Toronto Zoo events for 2026 (approximate dates)."""
        known = [
            {
                "title": "Toronto Zoo Earth Day Celebration 2026",
                "date": "2026-04-22T12:00:00Z",
                "description": "Special Earth Day programming with conservation talks and animal enrichment.",
            },
            {
                "title": "Toronto Zoo Seasonal Opening — Splash Pad 2026",
                "date": "2026-05-17T12:00:00Z",
                "end_date": "2026-09-07T12:00:00Z",
                "description": "Water play area open daily through Labour Day weekend.",
            },
            {
                "title": "Toronto Zoo Summer Camp 2026",
                "date": "2026-07-01T12:00:00Z",
                "end_date": "2026-08-31T12:00:00Z",
                "description": "Week-long summer day camps for kids ages 4-14 with animal encounters and nature activities.",
            },
            {
                "title": "Toronto Zoo Halloween — Howloween 2026",
                "date": "2026-10-01T12:00:00Z",
                "end_date": "2026-10-31T12:00:00Z",
                "description": "Family-friendly Halloween event with trick-or-treating and animal enrichment.",
            },
        ]

        results = []
        for ev_data in known:
            title = ev_data["title"]
            if title.lower() in seen_titles:
                continue
            seen_titles.add(title.lower())

            eid = self.generate_event_id(title, ev_data["date"], self.SOURCE_NAME)
            cats, tags = self.categorize_event(title, ev_data.get("description", ""))
            tags = list(set(tags + ["Zoo", "Family", "Wildlife"]))
            is_multi = bool(ev_data.get("end_date"))
            duration_cat = "single"
            if is_multi:
                try:
                    s = datetime.fromisoformat(ev_data["date"].replace("Z", "+00:00"))
                    e = datetime.fromisoformat(ev_data["end_date"].replace("Z", "+00:00"))
                    days = (e - s).days
                    if days <= 7:
                        duration_cat = "short"
                    elif days <= 30:
                        duration_cat = "medium"
                    else:
                        duration_cat = "long"
                except Exception:
                    pass

            results.append(ScrapedEvent(
                id=eid,
                title=title,
                date=ev_data["date"],
                end_date=ev_data.get("end_date"),
                location=self.SOURCE_NAME,
                address=self.VENUE_ADDRESS,
                lat=self.VENUE_LAT,
                lng=self.VENUE_LNG,
                source=self.SOURCE_NAME,
                host="Toronto Zoo",
                url=f"{self.BASE_URL}/events",
                description=ev_data.get("description", ""),
                categories=cats,
                tags=tags,
                is_free=False,
                price="Zoo admission required",
                status="UPCOMING",
                is_multi_day=is_multi,
                duration_category=duration_cat,
            ))

        return results


# ─── Luma Event Platform ─────────────────────────────────────────────

class LumaScraper(BaseScraper):
    """Luma (luma.com) — tech/community event platform.

    Luma is widely used for Toronto tech meetups, workshops, and
    community events.  Uses the public API with LUMA_API_KEY.
    """
    SOURCE_NAME = "Luma"
    BASE_URL = "https://api.lu.ma"
    MAX_PAGES = 5
    DELAY = 1.0

    def __init__(self, api_key: str = None):
        super().__init__()
        self.api_key = api_key or os.getenv("LUMA_API_KEY")
        if not self.api_key:
            print(f"[{self.SOURCE_NAME}] Info: No API key. Set LUMA_API_KEY for more events.")
            print(f"[{self.SOURCE_NAME}] Will try HTML scraping as fallback.")

    def scrape(self) -> List[ScrapedEvent]:
        """Scrape Luma events for Toronto."""
        events = []

        # If we have an API key, use it
        if self.api_key:
            events.extend(self._scrape_api())

        # Also try HTML discovery for Toronto events
        events.extend(self._scrape_html_discovery())

        print(f"[{self.SOURCE_NAME}] Scraped {len(events)} events")
        return events

    def _scrape_api(self) -> List[ScrapedEvent]:
        """Use Luma API to search Toronto events."""
        events = []

        try:
            headers = {
                "x-luma-api-key": self.api_key,
                "Content-Type": "application/json",
            }

            # Luma search endpoint for Toronto events
            now_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            for page in range(self.MAX_PAGES):
                url = f"{self.BASE_URL}/event/get-events"
                payload = {
                    "city": "Toronto",
                    "country": "CA",
                    "period": "upcoming",
                    "limit": 50,
                    "offset": page * 50,
                }

                resp = self.session.post(url, json=payload, headers=headers, timeout=30)
                if resp.status_code != 200:
                    break

                data = resp.json()
                entries = data.get("entries", data.get("events", []))
                if not entries:
                    break

                for entry in entries:
                    ev = self._parse_api_event(entry)
                    if ev:
                        events.append(ev)

                if len(entries) < 50:
                    break

                time.sleep(self.DELAY)

        except Exception as e:
            logger.warning(f"[{self.SOURCE_NAME}] API error: {e}")

        return events

    def _parse_api_event(self, data: Dict) -> Optional[ScrapedEvent]:
        """Parse a Luma API event entry."""
        try:
            title = data.get("name", data.get("title", ""))
            if not title or self.should_exclude(title):
                return None

            # Date
            start_str = data.get("start_at", data.get("date", ""))
            if not start_str:
                return None

            date_iso = self._normalize_luma_date(start_str)
            if not date_iso:
                return None

            end_str = data.get("end_at", data.get("end_date", ""))
            end_iso = self._normalize_luma_date(end_str) if end_str else None

            # Location
            venue = data.get("venue", {})
            if isinstance(venue, dict):
                location = venue.get("name", "Toronto, ON")
                address = venue.get("address", "")
                lat = venue.get("lat")
                lng = venue.get("lng")
            else:
                location = str(venue) if venue else "Toronto, ON"
                address = ""
                lat = lng = None

            # URL
            url = data.get("url", data.get("web_url", ""))

            # Description
            desc = data.get("description", data.get("about", ""))[:500]

            # Price
            ticket_info = data.get("ticket_info", {})
            is_free = False
            price_display = "See Tickets"
            price_amount = 0.0
            if ticket_info:
                is_free = ticket_info.get("is_free", False)
                if is_free:
                    price_display = "Free"
                else:
                    min_price = ticket_info.get("price", [])
                    if isinstance(min_price, list) and min_price:
                        try:
                            price_amount = float(min_price[0])
                            price_display = f"${price_amount:.2f}"
                        except (ValueError, IndexError):
                            pass

            # Image
            image = data.get("cover_url", data.get("image", ""))

            # Multi-day
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

            eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)
            cats, tags = self.categorize_event(title, desc)
            tags = list(set(tags + ["Tech", "Community"]))

            return ScrapedEvent(
                id=eid,
                title=title,
                date=date_iso,
                end_date=end_iso if is_multi else None,
                location=location,
                address=address if address else None,
                lat=float(lat) if lat else None,
                lng=float(lng) if lng else None,
                source=self.SOURCE_NAME,
                host=self._parse_organizer(data.get("organizer")),
                url=url,
                price=price_display,
                price_amount=price_amount,
                is_free=is_free,
                description=desc,
                categories=cats,
                tags=tags,
                status="UPCOMING",
                is_multi_day=is_multi,
                duration_category=duration_cat,
                image=image if image else None,
            )
        except Exception as e:
            logger.debug(f"[{self.SOURCE_NAME}] API parse error: {e}")
            return None

    def _scrape_html_discovery(self) -> List[ScrapedEvent]:
        """Fallback: HTML scrape Luma Toronto discovery pages."""
        events = []
        seen_urls = set()

        # Luma discovery URLs — city page + topic-specific pages
        urls = [
            "https://lu.ma/toronto",
            "https://lu.ma/city/toronto",
            "https://lu.ma/discover?city=Toronto",
            "https://lu.ma/discover?city=Toronto&topic=tech",
            "https://lu.ma/discover?city=Toronto&topic=startup",
            "https://lu.ma/discover?city=Toronto&topic=ai",
            "https://lu.ma/discover?city=Toronto&topic=community",
            "https://lu.ma/discover?city=Toronto&topic=business",
        ]

        for url in urls:
            try:
                if HAS_SCRAPLING:
                    fetcher = Fetcher(auto_match=False)
                    page = fetcher.get(url, timeout=30)
                else:
                    resp = self.session.get(url, timeout=30, headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    })
                    if resp.status_code != 200:
                        continue
                    from bs4 import BeautifulSoup
                    page = BeautifulSoup(resp.text, "html.parser")

                if not page:
                    continue

                # Extract event links and data from Luma discovery pages
                if HAS_SCRAPLING:
                    cards = page.css('[class*="event"], .event-card, .event-item, '
                                     'a[href*="/event/"], [data-event-id], '
                                     '.card, article, [class*="card"]')
                else:
                    cards = page.select('[class*="event"], .event-card, .event-item, '
                                       'a[href*="/event/"], [data-event-id], '
                                       '.card, article, [class*="card"]')

                for card in cards[:50]:
                    try:
                        # Get title
                        if HAS_SCRAPLING:
                            title_el = card.css_first('h2, h3, h4, .title, .event-name, '
                                                     '.event-title, span[class*="title"]')
                        else:
                            title_el = card.select_one('h2, h3, h4, .title, .event-name, '
                                                      '.event-title, span[class*="title"]')

                        title = ""
                        if title_el:
                            title = title_el.text.strip() if hasattr(title_el, 'text') else ""

                        if not title:
                            # For <a> elements, the link text itself might be the title
                            title = card.text.strip()[:100] if hasattr(card, 'text') else ""

                        if not title or self.should_exclude(title):
                            continue

                        # URL
                        href = ""
                        if HAS_SCRAPLING:
                            if card.tag == "a":
                                href = card.attrib.get("href", "")
                            else:
                                link = card.css_first('a[href*="/event/"]')
                                if link:
                                    href = link.attrib.get("href", "")
                        else:
                            if card.name == "a" and "/event/" in card.get("href", ""):
                                href = card.get("href", "")
                            else:
                                link = card.select_one('a[href*="/event/"]')
                                if link:
                                    href = link.get("href", "")

                        if href and not href.startswith("http"):
                            href = "https://lu.ma" + href
                        if not href or href in seen_urls:
                            continue
                        seen_urls.add(href)

                        # Date — try to extract from text
                        card_text = card.text.strip() if hasattr(card, 'text') else ""
                        date_iso = self._extract_date_from_luma_text(card_text)
                        if not date_iso:
                            continue

                        # Try to get venue from card
                        if HAS_SCRAPLING:
                            venue_el = card.css_first('.venue, .location, [class*="venue"], '
                                                     '[class*="location"]')
                        else:
                            venue_el = card.select_one('.venue, .location, [class*="venue"], '
                                                      '[class*="location"]')
                        venue_name = "Toronto, ON"
                        if venue_el:
                            venue_name = venue_el.text.strip() if hasattr(venue_el, 'text') else "Toronto, ON"

                        # Price — use word-boundary match to avoid "freedom" false positives
                        is_free = bool(re.search(r'\bfree\b', card_text, re.IGNORECASE))
                        price_display = "Free" if is_free else "See Tickets"

                        eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)
                        cats, tags = self.categorize_event(title, "")
                        tags = list(set(tags + ["Tech", "Community"]))

                        events.append(ScrapedEvent(
                            id=eid,
                            title=title,
                            date=date_iso,
                            location=venue_name,
                            source=self.SOURCE_NAME,
                            url=href,
                            categories=cats,
                            tags=tags,
                            is_free=is_free,
                            price=price_display,
                            status="UPCOMING",
                        ))
                    except Exception:
                        continue

            except Exception as e:
                logger.debug(f"[{self.SOURCE_NAME}] HTML scrape error for {url}: {e}")
                continue

        if events:
            print(f"[{self.SOURCE_NAME}] HTML fallback: {len(events)} events")
        else:
            print(f"[{self.SOURCE_NAME}] HTML fallback: no events found (site may require JS)")

        return events

    def _parse_organizer(self, org_data) -> str:
        """Extract organizer name from Luma API organizer field."""
        if isinstance(org_data, dict):
            return org_data.get("name", "Luma")
        if org_data:
            return str(org_data)
        return "Luma"

    def _normalize_luma_date(self, date_str: str) -> Optional[str]:
        """Normalize Luma date strings to ISO-8601."""
        if not date_str:
            return None
        date_str = date_str.strip()

        # Already ISO
        if re.match(r"\d{4}-\d{2}-\d{2}T", date_str):
            if not date_str.endswith("Z") and "+" not in date_str[10:]:
                date_str += "Z"
            if date_str.endswith("T00:00:00Z"):
                date_str = date_str.replace("T00:00:00Z", "T12:00:00Z")
            return date_str

        # Try standard formats
        for fmt in ["%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                dt = dt.replace(hour=12, minute=0, second=0)
                return dt.isoformat() + "Z"
            except ValueError:
                continue

        return None

    def _extract_date_from_luma_text(self, text: str) -> Optional[str]:
        """Extract date from Luma event card text."""
        # Pattern: "Thu, Apr 17, 2025" or "Apr 17, 2025"
        pat = re.compile(r'(\w{3})\s+(\d{1,2}),?\s+(\d{4})', re.IGNORECASE)
        m = pat.search(text)
        if m:
            try:
                dt = datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%b %d %Y")
                dt = dt.replace(hour=12, minute=0, second=0)
                return dt.isoformat() + "Z"
            except ValueError:
                pass

        # Pattern: "April 17, 2025"
        pat2 = re.compile(r'(\w+)\s+(\d{1,2}),?\s+(\d{4})', re.IGNORECASE)
        m = pat2.search(text)
        if m:
            for fmt in ["%B %d %Y", "%b %d %Y"]:
                try:
                    dt = datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", fmt)
                    dt = dt.replace(hour=12, minute=0, second=0)
                    return dt.isoformat() + "Z"
                except ValueError:
                    continue

        return None


# ─── Major Toronto Festivals (Known Annual Events) ────────────────────

class MajorFestivalsScraper(BaseScraper):
    """Known major Toronto festivals and events for 2026.

    These are annual signature events that every Toronto event site
    should have. Dates are approximate based on historical patterns
    and will be refined as official dates are announced.
    """
    SOURCE_NAME = "Major Toronto Festivals"

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        seen = set()

        known_festivals = [
            {
                "title": "Luminato Festival Toronto 2026",
                "date": "2026-06-03T12:00:00Z",
                "end_date": "2026-06-28T12:00:00Z",
                "location": "Various Locations, Toronto",
                "url": "https://luminatofestival.com",
                "description": "Toronto's international arts festival — theatre, dance, music, visual art across 26 days.",
                "categories": ["Arts", "Community"],
                "tags": ["Luminato", "Arts Festival", "Theatre"],
                "is_free": True,
                "price": "Free + Ticketed events",
            },
            {
                "title": "Toronto Fringe Festival 2026",
                "date": "2026-07-02T12:00:00Z",
                "end_date": "2026-07-13T12:00:00Z",
                "location": "Various Venues, Toronto",
                "url": "https://fringetoronto.com",
                "description": "Toronto's largest theatre festival with 150+ shows across the city.",
                "categories": ["Arts", "Theatre"],
                "tags": ["Fringe", "Theatre", "Indie"],
                "is_free": False,
                "price": "$12-15 per show",
                "price_amount": 12.0,
            },
            {
                "title": "Hot Docs Canadian International Documentary Festival 2026",
                "date": "2026-04-24T12:00:00Z",
                "end_date": "2026-05-04T12:00:00Z",
                "location": "Hot Docs Ted Rogers Cinema, Toronto",
                "address": "506 Bloor St W, Toronto, ON M5S 1Y3",
                "url": "https://hotdocs.ca",
                "description": "North America's largest documentary film festival with 200+ films.",
                "categories": ["Arts", "Film"],
                "tags": ["Documentary", "Film Festival", "Hot Docs"],
                "is_free": False,
                "price": "$8-18 per screening",
                "price_amount": 8.0,
            },
            {
                "title": "NXNE Music Festival 2026",
                "date": "2026-06-11T12:00:00Z",
                "end_date": "2026-06-15T12:00:00Z",
                "location": "Various Venues, Toronto",
                "url": "https://nxne.com",
                "description": "North by Northeast — Toronto's emerging music festival with 300+ acts.",
                "categories": ["Music", "Festival"],
                "tags": ["NXNE", "Music Festival", "Emerging Artists"],
                "is_free": False,
                "price": "Free + Ticketed showcases",
            },
            {
                "title": "Taste of the Danforth 2026",
                "date": "2026-08-07T12:00:00Z",
                "end_date": "2026-08-09T12:00:00Z",
                "location": "Danforth Ave, Toronto",
                "address": "Danforth Ave between Broadview & Donlands, Toronto, ON",
                "url": "https://tasteofthedanforth.com",
                "description": "Toronto's iconic Greek food festival — the largest food festival in Canada.",
                "categories": ["Food & Drink", "Community"],
                "tags": ["Greek", "Food Festival", "Danforth"],
                "is_free": True,
                "price": "Free admission",
            },
            {
                "title": "Toronto Caribbean Carnival (Caribana) 2026",
                "date": "2026-07-30T12:00:00Z",
                "end_date": "2026-08-03T12:00:00Z",
                "location": "Exhibition Place & Lakeshore Blvd, Toronto",
                "address": "100 Princes' Blvd, Toronto, ON M6K 3C3",
                "url": "https://torontocaribbeancarnival.com",
                "description": "North America's largest Caribbean cultural festival — Grand Parade along Lakeshore Blvd.",
                "categories": ["Community", "Music", "Festival"],
                "tags": ["Caribana", "Caribbean", "Parade", "Carnival"],
                "is_free": True,
                "price": "Free (parade); Ticketed events",
            },
            {
                "title": "Canadian National Exhibition (CNE) 2026",
                "date": "2026-08-21T12:00:00Z",
                "end_date": "2026-09-07T12:00:00Z",
                "location": "Exhibition Place, Toronto",
                "address": "100 Princes' Blvd, Toronto, ON M6K 3C3",
                "url": "https://theex.com",
                "description": "Canada's largest annual fair — midway, food, concerts, air show, shopping.",
                "categories": ["Community", "Family", "Festival"],
                "tags": ["CNE", "Fair", "Exhibition", "Air Show"],
                "is_free": False,
                "price": "$20-25 admission",
                "price_amount": 20.0,
            },
            {
                "title": "Toronto International Film Festival (TIFF) 2026",
                "date": "2026-09-10T12:00:00Z",
                "end_date": "2026-09-20T12:00:00Z",
                "location": "TIFF Bell Lightbox & Various Venues, Toronto",
                "address": "350 King St W, Toronto, ON M5V 3X5",
                "url": "https://tiff.net",
                "description": "The world's largest public film festival — 300+ films, celebrity sightings, premieres.",
                "categories": ["Arts", "Film", "Festival"],
                "tags": ["TIFF", "Film Festival", "Premiere"],
                "is_free": False,
                "price": "$15-50 per screening",
                "price_amount": 15.0,
            },
            {
                "title": "Word on the Street Toronto 2026",
                "date": "2026-09-01T12:00:00Z",
                "location": "Queen's Park Circle, Toronto",
                "url": "https://www.thewordonthestreet.ca/toronto/",
                "description": "Canada's largest book and magazine festival — author readings, book vendors.",
                "categories": ["Community", "Arts"],
                "tags": ["Books", "Literary Festival"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "Toronto Jazz Festival 2026",
                "date": "2026-06-20T12:00:00Z",
                "end_date": "2026-06-29T12:00:00Z",
                "location": "Various Venues, Toronto",
                "url": "https://www.torontojazz.com",
                "description": "Toronto's premier jazz festival with 100+ concerts across the city.",
                "categories": ["Music", "Festival"],
                "tags": ["Jazz", "Music Festival"],
                "is_free": False,
                "price": "Free + Ticketed events",
            },
            {
                "title": "Salsa on St. Clair 2026",
                "date": "2026-07-12T12:00:00Z",
                "end_date": "2026-07-13T12:00:00Z",
                "location": "St. Clair Ave W, Toronto",
                "url": "https://www.salsaonstclair.com",
                "description": "Two-day Latin street festival with live music, dance, and food on St. Clair.",
                "categories": ["Community", "Music", "Food & Drink"],
                "tags": ["Salsa", "Latin", "Street Festival"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "Festival of Authors (IFOA) 2026",
                "date": "2026-10-23T12:00:00Z",
                "end_date": "2026-11-02T12:00:00Z",
                "location": "Harbourfront Centre, Toronto",
                "address": "235 Queens Quay W, Toronto, ON M5J 2G8",
                "url": "https://festivalofauthors.ca",
                "description": "International Festival of Authors — readings, interviews, book signings.",
                "categories": ["Arts", "Community"],
                "tags": ["Literary", "Authors", "Books"],
                "is_free": False,
                "price": "Free + Ticketed events",
            },
            {
                "title": "Toronto Oktoberfest 2026",
                "date": "2026-09-25T12:00:00Z",
                "end_date": "2026-10-12T12:00:00Z",
                "location": "Ontario Place, Toronto",
                "address": "955 Lake Shore Blvd W, Toronto, ON M6K 3B9",
                "url": "https://www.torontooktoberfest.ca",
                "description": "German heritage celebration with beer gardens, live music, and traditional food.",
                "categories": ["Food & Drink", "Community", "Festival"],
                "tags": ["Oktoberfest", "German", "Beer"],
                "is_free": False,
                "price": "$15-30 admission",
                "price_amount": 15.0,
            },
            {
                "title": "FIFA World Cup 2026 Toronto Matches",
                "date": "2026-06-12T12:00:00Z",
                "end_date": "2026-07-12T12:00:00Z",
                "location": "BMO Field, Toronto",
                "address": "170 Princes' Blvd, Toronto, ON M6K 3C3",
                "url": "https://www.fifa.com/fifaplus/en/tournaments/mens/worldcup/2026",
                "description": "6 FIFA World Cup 2026 matches at BMO Field plus fan zone at Exhibition Place.",
                "categories": ["Sports", "Community"],
                "tags": ["FIFA", "World Cup", "Soccer", "Football"],
                "is_free": False,
                "price": "Ticketed",
            },

            # ─── Newly added 2026 festivals ─────────────────────────

            {
                "title": "Pride Toronto Festival 2026",
                "date": "2026-06-26T12:00:00Z",
                "end_date": "2026-06-28T12:00:00Z",
                "location": "Yonge & Dundas to Church & Wellesley, Toronto",
                "address": "Church & Wellesley Village, Toronto, ON",
                "url": "https://pridetoronto.com",
                "description": "Canada's largest Pride celebration — parade, Dyke March, Trans March, street fair, and 3 days of live entertainment.",
                "categories": ["Community", "Festival"],
                "tags": ["Pride", "LGBTQ+", "Parade", "Celebration"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "Doors Open Toronto 2026",
                "date": "2026-05-23T12:00:00Z",
                "end_date": "2026-05-24T12:00:00Z",
                "location": "Various Buildings, Toronto",
                "url": "https://www.toronto.ca/explore-enjoy/art-culture/museums-galleries/doors-open-toronto/",
                "description": "Free access to 150+ architecturally, historically, and culturally significant buildings across Toronto.",
                "categories": ["Arts", "Community", "Architecture"],
                "tags": ["Doors Open", "Architecture", "Heritage", "Free"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "TIFF Street Festival 2026",
                "date": "2026-09-10T12:00:00Z",
                "end_date": "2026-09-11T12:00:00Z",
                "location": "King St W between John & Peter, Toronto",
                "address": "King St W, Toronto, ON M5V",
                "url": "https://tiff.net",
                "description": "Free outdoor street festival during TIFF opening weekend — live music, food vendors, film screenings, and celebrity sightings.",
                "categories": ["Arts", "Film", "Festival"],
                "tags": ["TIFF", "Street Festival", "Film", "Free"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "Winterlicious 2026",
                "date": "2026-01-30T12:00:00Z",
                "end_date": "2026-02-13T12:00:00Z",
                "location": "Various Restaurants, Toronto",
                "url": "https://www.toronto.ca/explore-enjoy/dine-out/winterlicious/",
                "description": "Toronto's prix-fixe dining event — 200+ restaurants offering 3-course menus at set prices ($20-$55).",
                "categories": ["Food & Drink"],
                "tags": ["Winterlicious", "Restaurant", "Dining", "Prix Fixe"],
                "is_free": False,
                "price": "$20-55 per meal",
                "price_amount": 20.0,
            },
            {
                "title": "Summerlicious 2026",
                "date": "2026-07-10T12:00:00Z",
                "end_date": "2026-07-26T12:00:00Z",
                "location": "Various Restaurants, Toronto",
                "url": "https://www.toronto.ca/explore-enjoy/dine-out/summerlicious/",
                "description": "Summer edition of Toronto's prix-fixe dining event — 200+ restaurants with 3-course set menus.",
                "categories": ["Food & Drink"],
                "tags": ["Summerlicious", "Restaurant", "Dining", "Prix Fixe"],
                "is_free": False,
                "price": "$20-55 per meal",
                "price_amount": 20.0,
            },
            {
                "title": "Nuit Blanche Toronto 2026",
                "date": "2026-10-03T12:00:00Z",
                "location": "Various Locations, Toronto",
                "url": "https://www.nbto.com",
                "description": "All-night contemporary art event — installations, performance art, and interactive projects across the city from sunset to sunrise.",
                "categories": ["Arts", "Festival"],
                "tags": ["Nuit Blanche", "Art", "Contemporary", "Overnight"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "Toronto Outdoor Art Fair 2026",
                "date": "2026-07-11T12:00:00Z",
                "end_date": "2026-07-13T12:00:00Z",
                "location": "Nathan Phillips Square, Toronto",
                "address": "100 Queen St W, Toronto, ON M5H 2N2",
                "url": "https://www.torontooutdoorart.com",
                "description": "Canada's largest outdoor art exhibition — 500+ artists showcasing painting, sculpture, photography, and mixed media.",
                "categories": ["Arts", "Festival"],
                "tags": ["Art Fair", "Outdoor", "Visual Art"],
                "is_free": True,
                "price": "Free admission",
            },
            {
                "title": "Toronto BuskerFest 2026",
                "date": "2026-08-28T12:00:00Z",
                "end_date": "2026-08-31T12:00:00Z",
                "location": "Woodbine Park, Toronto",
                "address": "1695 Queen St E, Toronto, ON M4L 1G7",
                "url": "https://www.torontobuskerfest.com",
                "description": "Street performer festival — acrobats, fire-breathers, musicians, and magicians in a waterfront park.",
                "categories": ["Arts", "Community", "Festival"],
                "tags": ["Busker", "Street Performance", "Circus"],
                "is_free": True,
                "price": "Donation suggested (Epilepsy Toronto)",
            },
            {
                "title": "Royal Agricultural Winter Fair 2026",
                "date": "2026-11-06T12:00:00Z",
                "end_date": "2026-11-15T12:00:00Z",
                "location": "Exhibition Place, Toronto",
                "address": "100 Princes' Blvd, Toronto, ON M6K 3C3",
                "url": "https://royalfair.org",
                "description": "The world's largest indoor agricultural fair — horse shows, farm animals, butter sculptures, and local food.",
                "categories": ["Community", "Family", "Festival"],
                "tags": ["Royal Fair", "Agriculture", "Horse Show", "Farm"],
                "is_free": False,
                "price": "$20-30 admission",
                "price_amount": 20.0,
            },
            {
                "title": "Toronto Santa Claus Parade 2026",
                "date": "2026-11-15T12:00:00Z",
                "location": "Bloor St to Front St via University Ave, Toronto",
                "url": "https://www.thesantaclausparade.com",
                "description": "One of the oldest and largest Santa Claus parades in the world — floats, marching bands, and Santa.",
                "categories": ["Community", "Family", "Festival"],
                "tags": ["Santa Claus", "Parade", "Christmas", "Family"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "Cavalcade of Lights 2026",
                "date": "2026-11-22T12:00:00Z",
                "location": "Nathan Phillips Square, Toronto",
                "address": "100 Queen St W, Toronto, ON M5H 2N2",
                "url": "https://www.toronto.ca/explore-enjoy/festivals-events/cavalcade-of-lights/",
                "description": "Annual holiday kickoff — Christmas tree lighting, fireworks, ice skating, and live performances.",
                "categories": ["Community", "Festival", "Arts"],
                "tags": ["Cavalcade", "Christmas", "Lights", "Fireworks"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "CONTACT Photography Festival 2026",
                "date": "2026-05-01T12:00:00Z",
                "end_date": "2026-05-31T12:00:00Z",
                "location": "Various Galleries, Toronto",
                "url": "https://scotiabankcontactphoto.com",
                "description": "Canada's largest photography festival — 200+ exhibitions across galleries, public spaces, and online.",
                "categories": ["Arts", "Photography"],
                "tags": ["Contact", "Photography", "Gallery", "Exhibition"],
                "is_free": True,
                "price": "Free + Ticketed exhibitions",
            },
            {
                "title": "Beaches International Jazz Festival 2026",
                "date": "2026-07-18T12:00:00Z",
                "end_date": "2026-07-27T12:00:00Z",
                "location": "The Beaches, Toronto",
                "address": "Queen St E at Woodbine Ave, Toronto, ON M4L 1C5",
                "url": "https://www.beachesjazz.com",
                "description": "Free outdoor jazz festival in The Beaches neighbourhood — 50+ bands across multiple stages.",
                "categories": ["Music", "Festival"],
                "tags": ["Jazz", "Beaches", "Music Festival", "Free"],
                "is_free": True,
                "price": "Free (outdoor stages)",
            },
            {
                "title": "Toronto Dragon Boat Festival 2026",
                "date": "2026-06-21T12:00:00Z",
                "end_date": "2026-06-22T12:00:00Z",
                "location": "Toronto Islands, Toronto",
                "address": "Toronto Islands, Toronto, ON",
                "url": "https://dragonboats.com",
                "description": "Annual dragon boat races on the Toronto Islands — 200+ teams, cultural performances, and food.",
                "categories": ["Sports", "Community", "Festival"],
                "tags": ["Dragon Boat", "Racing", "Cultural"],
                "is_free": True,
                "price": "Free admission",
            },
            {
                "title": "Redpath Waterfront Festival 2026",
                "date": "2026-06-28T12:00:00Z",
                "end_date": "2026-06-30T12:00:00Z",
                "location": "Harbourfront Centre & Queens Quay, Toronto",
                "address": "235 Queens Quay W, Toronto, ON M5J 2G8",
                "url": "https://www.redpathwaterfrontfestival.com",
                "description": "Waterfront celebration with live music, food vendors, boat tours, and family activities.",
                "categories": ["Community", "Music", "Food & Drink"],
                "tags": ["Waterfront", "Redpath", "Harbourfront"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "Corso Italia Festival 2026",
                "date": "2026-07-05T12:00:00Z",
                "end_date": "2026-07-06T12:00:00Z",
                "location": "St. Clair Ave W (Dufferin to Lansdowne), Toronto",
                "address": "St. Clair Ave W, Toronto, ON",
                "url": "https://www.corsoitaliafestival.com",
                "description": "Italian street festival — live music, food vendors, patios, and cultural performances on St. Clair.",
                "categories": ["Community", "Food & Drink", "Festival"],
                "tags": ["Italian", "Corso Italia", "Street Festival"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "Toronto Greek Community Festival (Panigiri) 2026",
                "date": "2026-06-20T12:00:00Z",
                "end_date": "2026-06-22T12:00:00Z",
                "location": "Alexander the Great Parkette, Toronto",
                "address": "7 Wong Ave, Toronto, ON M4K 1A7",
                "url": "https://torontogreekfestival.com",
                "description": "Traditional Greek community Panigiri — souvlaki, live music, folk dancing, and church grounds celebration. (Separate from Taste of the Danforth in August.)",
                "categories": ["Community", "Food & Drink", "Festival"],
                "tags": ["Greek", "Panigiri", "Cultural", "Church Festival"],
                "is_free": True,
                "price": "Free admission",
            },
            {
                "title": "Festival of South Asia 2026",
                "date": "2026-08-16T12:00:00Z",
                "end_date": "2026-08-17T12:00:00Z",
                "location": "Gerrard St (Coxwell to Greenwood), Toronto",
                "address": "Gerrard India Bazaar, Toronto, ON M4L",
                "url": "https://www.festivalofsouthasia.com",
                "description": "South Asian street festival — Bollywood performances, street food, fashion, and art on Gerrard India Bazaar.",
                "categories": ["Community", "Food & Drink", "Festival"],
                "tags": ["South Asia", "Indian", "Bollywood", "Street Festival"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "Polish Festival on Roncesvalles 2026",
                "date": "2026-09-13T12:00:00Z",
                "end_date": "2026-09-14T12:00:00Z",
                "location": "Roncesvalles Ave, Toronto",
                "address": "Roncesvalles Ave, Toronto, ON M6R",
                "url": "https://www.polishfestival.ca",
                "description": "Canada's largest Polish festival — pierogi, folk dancing, live music, and cultural exhibits.",
                "categories": ["Community", "Food & Drink", "Festival"],
                "tags": ["Polish", "Roncesvalles", "Cultural Festival"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "Canada Day Celebrations at Nathan Phillips Square 2026",
                "date": "2026-07-01T12:00:00Z",
                "location": "Nathan Phillips Square, Toronto",
                "address": "100 Queen St W, Toronto, ON M5H 2N2",
                "url": "https://www.toronto.ca/explore-enjoy/festivals-events/canada-day/",
                "description": "Official Canada Day celebration — live music, citizenship ceremony, food, and fireworks.",
                "categories": ["Community", "Festival"],
                "tags": ["Canada Day", "Fireworks", "Celebration"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "Junction Arts Festival 2026",
                "date": "2026-09-18T12:00:00Z",
                "end_date": "2026-09-21T12:00:00Z",
                "location": "The Junction, Toronto",
                "address": "Dundas St W at Keele St, Toronto, ON M6P",
                "url": "https://www.junctionartsfest.com",
                "description": "Multi-day arts festival in The Junction — live music, art installations, food, and family activities.",
                "categories": ["Arts", "Community", "Festival"],
                "tags": ["Junction", "Arts Festival", "Live Music"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "Toronto Reel Asian International Film Festival 2026",
                "date": "2026-11-12T12:00:00Z",
                "end_date": "2026-11-16T12:00:00Z",
                "location": "Various Cinemas, Toronto",
                "url": "https://www.reelasian.com",
                "description": "Canada's premier pan-Asian film festival — East and South Asian cinema, documentaries, and shorts.",
                "categories": ["Arts", "Film", "Festival"],
                "tags": ["Reel Asian", "Film Festival", "Asian Cinema"],
                "is_free": False,
                "price": "$10-15 per screening",
                "price_amount": 10.0,
            },
            {
                "title": "Kensington Market Jazz Festival 2026",
                "date": "2026-09-05T12:00:00Z",
                "end_date": "2026-09-07T12:00:00Z",
                "location": "Kensington Market, Toronto",
                "address": "Kensington Market, Toronto, ON M5T",
                "url": "https://kensingtonmarketjazz.com",
                "description": "Free jazz performances in the heart of Kensington Market — intimate sets in shops, patios, and streets.",
                "categories": ["Music", "Festival"],
                "tags": ["Jazz", "Kensington Market", "Live Music", "Free"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "Ashkenaz Festival 2026",
                "date": "2026-08-31T12:00:00Z",
                "end_date": "2026-09-01T12:00:00Z",
                "location": "Harbourfront Centre, Toronto",
                "address": "235 Queens Quay W, Toronto, ON M5J 2G8",
                "url": "https://ashkenazfestival.com",
                "description": "Jewish arts and culture festival — klezmer music, Yiddish theatre, food, and film.",
                "categories": ["Arts", "Community", "Festival"],
                "tags": ["Jewish", "Klezmer", "Ashkenaz", "Cultural"],
                "is_free": True,
                "price": "Free",
            },
            {
                "title": "Toronto Ukrainian Festival 2026",
                "date": "2026-09-19T12:00:00Z",
                "end_date": "2026-09-21T12:00:00Z",
                "location": "Bloor St W (Jane to Runnymede), Toronto",
                "address": "Bloor St W, Toronto, ON M6S",
                "url": "https://www.ukrainianfestival.com",
                "description": "Annual Ukrainian festival — dancing, music, food (pierogies, holubtsi), and cultural exhibits.",
                "categories": ["Community", "Food & Drink", "Festival"],
                "tags": ["Ukrainian", "Cultural Festival", "Bloor West Village"],
                "is_free": True,
                "price": "Free",
            },
        ]

        for fest in known_festivals:
            title = fest["title"]
            norm = title.lower()
            if norm in seen:
                continue
            seen.add(norm)

            date_iso = fest["date"]
            end_iso = fest.get("end_date")
            is_multi = bool(end_iso)
            duration_cat = "single"
            if is_multi and end_iso:
                try:
                    s = datetime.fromisoformat(date_iso.replace("Z", "+00:00"))
                    e = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
                    days = (e - s).days
                    if days <= 7:
                        duration_cat = "short"
                    elif days <= 30:
                        duration_cat = "medium"
                    else:
                        duration_cat = "long"
                except Exception:
                    pass

            eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)

            events.append(ScrapedEvent(
                id=eid,
                title=title,
                date=date_iso,
                end_date=end_iso if is_multi else None,
                location=fest.get("location", "Toronto, ON"),
                address=fest.get("address"),
                source=self.SOURCE_NAME,
                host=title.split("2026")[0].strip(),
                url=fest.get("url", ""),
                price=fest.get("price", "See event page"),
                price_amount=fest.get("price_amount", 0.0),
                is_free=fest.get("is_free", False),
                description=fest.get("description", "")[:500],
                categories=fest.get("categories", ["General"]),
                tags=fest.get("tags", ["General"]),
                status="UPCOMING",
                is_multi_day=is_multi,
                duration_category=duration_cat,
            ))

        return events


# ─── Export list ──────────────────────────────────────────────────────

ALL_ADDITIONAL_SCRAPERS = [
    SongkickScraper,
    MirvishTheatresScraper,
    ResidentAdvisorScraper,
    TorontoZooScraper,
    LumaScraper,
    MajorFestivalsScraper,
]


def scrape_all_additional(verbose: bool = True) -> List[ScrapedEvent]:
    """Run all additional scrapers and return combined events."""
    all_events = []
    for scraper_cls in ALL_ADDITIONAL_SCRAPERS:
        name = scraper_cls.SOURCE_NAME
        try:
            scraper = scraper_cls()
            events = scraper.scrape()
            if verbose:
                print(f"  [{name}] -> {len(events)} events")
            all_events.extend(events)
        except Exception as e:
            if verbose:
                print(f"  [{name}] ERROR: {e}")
    return all_events


if __name__ == "__main__":
    import sys
    import io
    # Fix Windows encoding
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    logging.basicConfig(level=logging.INFO)

    print(f"Scrapling available: {HAS_SCRAPLING}")
    print(f"Additional scrapers: {len(ALL_ADDITIONAL_SCRAPERS)}")
    print("=" * 60)

    all_events = scrape_all_additional(verbose=True)

    print(f"\n{'=' * 60}")
    print(f"TOTAL: {len(all_events)} events from {len(ALL_ADDITIONAL_SCRAPERS)} sources")

    # Save sample output
    output = [ev.to_dict() for ev in all_events]
    with open("additional_sources_sample.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str, ensure_ascii=False)
    print(f"Saved {len(output)} events to additional_sources_sample.json")
