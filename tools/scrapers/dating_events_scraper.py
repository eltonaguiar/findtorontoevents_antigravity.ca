#!/usr/bin/env python3
"""
Toronto Dating & Singles Events Scraper

Scrapes Eventbrite's dating-specific category pages for Toronto events
with REAL dates (not TBD). Targets:
  - /dating--events/
  - /singles--events/
  - /speed-dating--events/
  - /social-mixer--events/

Also scrapes 25dates.com (major Toronto speed-dating company) if available.

Uses Scrapling for TLS-fingerprinted requests where available,
falls back to requests + BeautifulSoup.
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

# Eventbrite category search URLs for Toronto dating events
EVENTBRITE_DATING_URLS = [
    "https://www.eventbrite.ca/d/canada--toronto/dating--events/",
    "https://www.eventbrite.ca/d/canada--toronto/singles--events/",
    "https://www.eventbrite.ca/d/canada--toronto/speed-dating--events/",
    "https://www.eventbrite.ca/d/canada--toronto/social-mixer--events/",
    "https://www.eventbrite.ca/d/canada--toronto/dating/",
    "https://www.eventbrite.ca/d/canada--toronto/singles/",
]

# 25dates.com — popular Toronto speed-dating company
TWENTYFIVEDATES_URLS = [
    "https://www.25dates.com/events/",
    "https://www.25dates.com/en/speed-dating-toronto/",
]

# Additional dating event sources
FASTLIFE_URL = "https://fastlife.ca/toronto/"

# Toronto dating keywords for filtering / boosting
DATING_KEYWORDS = [
    "dating", "singles", "speed dating", "matchmaking", "social mixer",
    "mingle", "meet singles", "single professionals", "date night",
    "alternative matchmaking", "muslim foodies", "lgbtq dating",
    "gay singles", "lesbian singles", "speed date", "blind date",
    "speeddate", "single night", "singles night", "singles event",
]


class DatingEventsScraper(BaseScraper):
    """Scraper for Toronto dating & singles events with real dates.

    Unlike the generic Eventbrite scraper which hits the main events page,
    this targets the dating/singles/speed-dating category pages specifically
    so dating events actually surface with real calendar dates instead of TBD.
    """

    SOURCE_NAME = "Dating Events"
    BASE_URL = "https://www.eventbrite.ca"
    DELAY = 1.0  # Rate limit between requests

    def __init__(self):
        super().__init__()
        if HAS_SCRAPLING:
            self._fetcher = Fetcher(auto_match=False)

    def _fetch_page(self, url: str):
        """Fetch a page using Scrapling (TLS-fingerprinted) or requests fallback."""
        try:
            if HAS_SCRAPLING:
                return self._fetcher.get(url, timeout=30)
            else:
                resp = self.session.get(url, timeout=30)
                resp.raise_for_status()
                from bs4 import BeautifulSoup
                return BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            logger.warning(f"[{self.SOURCE_NAME}] Error fetching {url}: {e}")
            return None

    def _extract_jsonld(self, page) -> List[dict]:
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

    def _normalize_date(self, date_str: str) -> Optional[str]:
        """Normalize various date strings to ISO-8601."""
        if not date_str:
            return None
        date_str = date_str.strip()
        if re.match(r"\d{4}-\d{2}-\d{2}T", date_str):
            if not date_str.endswith("Z") and "+" not in date_str[10:]:
                date_str += "Z"
            return date_str
        # Date only — use noon UTC (T12:00:00Z) so the event lands on the
        # correct Toronto calendar day. Midnight UTC = 8PM EDT / 7PM EST the
        # PREVIOUS day, which makes events appear on the wrong date.
        if re.match(r"\d{4}-\d{2}-\d{2}$", date_str):
            return f"{date_str}T12:00:00Z"
        for fmt in ["%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y",
                    "%B %d, %Y %I:%M %p", "%b %d, %Y %I:%M %p",
                    "%A, %B %d, %Y", "%A, %b %d, %Y"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                if dt.hour == 0 and dt.minute == 0:
                    # Date-only parse: noon UTC keeps Toronto calendar day correct
                    return dt.replace(hour=12, minute=0, second=0).isoformat() + "Z"
                else:
                    # Has an actual time — treat as EDT and convert to UTC
                    return (dt + timedelta(hours=4)).isoformat() + "Z"
            except ValueError:
                continue
        return None

    # Simple in-process cache so we only hit each detail page once per run.
    _organizer_cache: Dict[str, str] = {}

    def _fetch_organizer_name(self, event_url: str) -> Optional[str]:
        """Fetch the Eventbrite event detail page and extract the organizer name.

        Falls back through:
          1. JSON-LD @type Event -> organizer.name (most reliable)
          2. <meta property="event:organizer"> or similar OG/meta tag
          3. "Organized by <name>" text near the organizer section
        Returns None on any failure; we keep the original empty host in that case.
        """
        if not event_url:
            return None
        if event_url in self._organizer_cache:
            return self._organizer_cache[event_url] or None
        try:
            page = self._fetch_page(event_url)
            if page is None:
                self._organizer_cache[event_url] = ""
                return None
            # Reuse existing JSON-LD extraction helpers.
            events = self._extract_jsonld(page)
            for ev in events:
                org = ev.get("organizer") or {}
                if isinstance(org, list) and org:
                    org = org[0]
                if isinstance(org, dict):
                    name = (org.get("name") or "").strip()
                    if name:
                        self._organizer_cache[event_url] = name
                        return name
                elif isinstance(org, str) and org.strip():
                    self._organizer_cache[event_url] = org.strip()
                    return org.strip()
            # Eventbrite occasionally embeds organizer data in a second
            # Redux/Next state blob rather than at the top level of the page's
            # Event JSON-LD. Fall back to a direct regex over the raw page body.
            raw = ""
            body = getattr(page, "body", None)
            if isinstance(body, (bytes, bytearray)):
                raw = body.decode("utf-8", errors="replace")
            elif isinstance(body, str):
                raw = body
            if not raw:
                # BeautifulSoup fallback
                raw = str(page)
            m = re.search(r'"organizer"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"', raw)
            if m:
                name = m.group(1).strip()
                if name and 2 <= len(name) <= 80:
                    self._organizer_cache[event_url] = name
                    return name
            # Secondary: Eventbrite puts the organizer name in an <a> with
            # `data-testid="organizer-name-link"` or similar; fall back to that.
            if HAS_SCRAPLING:
                el = page.css_first('[data-testid="organizer-name-link"]') or \
                     page.css_first('a[href*="/o/"]')
                if el:
                    text = (getattr(el, "text", "") or "").strip()
                    if text and 2 <= len(text) <= 80:
                        self._organizer_cache[event_url] = text
                        return text
            else:
                el = page.find(attrs={"data-testid": "organizer-name-link"}) or \
                     page.find("a", href=re.compile(r"/o/"))
                if el:
                    text = el.get_text(strip=True) if hasattr(el, "get_text") else ""
                    if text and 2 <= len(text) <= 80:
                        self._organizer_cache[event_url] = text
                        return text
        except Exception as ex:
            logger.debug(f"[{self.SOURCE_NAME}] organizer lookup failed for {event_url}: {ex}")
        self._organizer_cache[event_url] = ""
        return None

    def _is_dating_event(self, title: str, description: str = "") -> bool:
        """Check if an event is dating-related based on title/description."""
        combined = f"{title} {description}".lower()
        for kw in DATING_KEYWORDS:
            if kw in combined:
                return True
        return False

    def _jsonld_to_event(self, ld: dict, source_url: str = "") -> Optional[ScrapedEvent]:
        """Convert a JSON-LD Event dict to ScrapedEvent with dating categories forced."""
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
                street = address_obj.get("streetAddress", "")
                city = address_obj.get("addressLocality", "")
                region = address_obj.get("addressRegion", "")
                postal = address_obj.get("postalCode", "")
                address_parts = [p for p in [street, city, region, postal] if p]
                full_address = ", ".join(address_parts) if address_parts else None
            elif isinstance(address_obj, str):
                full_address = address_obj
            else:
                full_address = None
            geo = loc.get("geo", {})
            lat = float(geo.get("latitude", 0)) if geo else None
            lng = float(geo.get("longitude", 0)) if geo else None
            if lat and abs(lat) < 1:
                lat = None
                lng = None
        elif isinstance(loc, str):
            venue_name = loc
            full_address = None
            lat = lng = None
        else:
            venue_name = "Toronto, ON"
            full_address = None
            lat = lng = None

        # Enhance location from known venues
        loc_info = self.enhance_location(venue_name or "Toronto, ON", title)
        if not full_address and loc_info.get("address"):
            full_address = loc_info["address"]
        if not lat and loc_info.get("lat"):
            lat = loc_info["lat"]
            lng = loc_info["lng"]

        # Price
        offers = ld.get("offers", {})
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        price_val = offers.get("price", 0)
        try:
            price_amount = float(price_val)
        except (ValueError, TypeError):
            price_amount = 0.0
        is_free = price_amount == 0
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
        url = ld.get("url", source_url)

        # Organizer. Browse-listing JSON-LD on Eventbrite often omits `organizer`,
        # which leaves `host` empty and makes the frontend fall back to the scraper
        # SOURCE_NAME ("Dating Events") — so a singles-mixer hosted by "Toronto
        # Social" ends up labelled "Dating Events" on the card. When the listing
        # didn't include it, fetch the event detail page once and pull the name
        # out of that page's JSON-LD or meta tags.
        org = ld.get("organizer", {})
        host = org.get("name", "") if isinstance(org, dict) else str(org) if org else ""
        if not host and url:
            host = self._fetch_organizer_name(url) or ""
        if not host:
            # Final fallback: platform name is more accurate than the empty string
            # (which the UI maps to the scraper SOURCE_NAME).
            host = "Eventbrite" if "eventbrite." in (url or "") else ""

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

        # Force Dating category + auto-categorize for additional tags
        cats, tags = self.categorize_event(title, desc)
        if "Dating" not in cats:
            cats.insert(0, "Dating")
        if "Singles" not in tags:
            tags.append("Singles")

        eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)

        return ScrapedEvent(
            id=eid,
            title=title,
            date=date_iso,
            end_date=end_iso if is_multi else None,
            location=loc_info.get("location", venue_name),
            address=full_address,
            lat=lat,
            lng=lng,
            source=self.SOURCE_NAME,
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
            image=image if image else None,
        )

    def _scrape_eventbrite_category(self, url: str) -> List[ScrapedEvent]:
        """Scrape a single Eventbrite dating category page."""
        events = []
        page = self._fetch_page(url)
        if not page:
            return events

        ld_events = self._extract_jsonld(page)
        for ld in ld_events:
            ev = self._jsonld_to_event(ld, url)
            if ev:
                events.append(ev)

        # Try HTML card fallback if JSON-LD yielded nothing
        if not ld_events:
            events.extend(self._parse_html_cards(page, url))

        return events

    def _parse_html_cards(self, page, base_url: str) -> List[ScrapedEvent]:
        """Fallback: parse HTML event cards when no JSON-LD available."""
        results = []
        if HAS_SCRAPLING:
            cards = (page.css('.event-card') or page.css('.event-listing') or
                     page.css('[class*="event"]') or page.css('article'))
        else:
            cards = (page.select('.event-card') or page.select('.event-listing') or
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
                if not title or self.should_exclude(title):
                    continue

                # Must be dating-related
                if not self._is_dating_event(title):
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
                    continue  # Skip events without real dates

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

                loc_info = self.enhance_location("Toronto, ON", title)
                eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)
                cats, tags = self.categorize_event(title, "")
                if "Dating" not in cats:
                    cats.insert(0, "Dating")
                if "Singles" not in tags:
                    tags.append("Singles")

                results.append(ScrapedEvent(
                    id=eid,
                    title=title,
                    date=date_iso,
                    location=loc_info.get("location", "Toronto, ON"),
                    address=loc_info.get("address"),
                    lat=loc_info.get("lat"),
                    lng=loc_info.get("lng"),
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

    def _scrape_25dates(self) -> List[ScrapedEvent]:
        """Scrape 25dates.com for Toronto speed-dating events."""
        events = []
        for url in TWENTYFIVEDATES_URLS:
            page = self._fetch_page(url)
            if not page:
                continue

            # Try JSON-LD first
            ld_events = self._extract_jsonld(page)
            for ld in ld_events:
                ev = self._jsonld_to_event(ld, url)
                if ev:
                    events.append(ev)

            if not ld_events:
                # HTML fallback — look for event cards with dates
                if HAS_SCRAPLING:
                    cards = page.css('.event-card, .event-item, .event, article, '
                                     '[class*="event"], tr.event')
                else:
                    cards = page.select('.event-card, .event-item, .event, article, '
                                       '[class*="event"], tr.event')

                for card in cards[:30]:
                    try:
                        if HAS_SCRAPLING:
                            title_el = card.css_first('h2, h3, h4, .title, a, .event-name')
                            date_el = card.css_first('.date, time, [datetime], .event-date, .event-time')
                            link_el = card.css_first('a[href]')
                        else:
                            title_el = card.select_one('h2, h3, h4, .title, a, .event-name')
                            date_el = card.select_one('.date, time, [datetime], .event-date, .event-time')
                            link_el = card.select_one('a[href]')

                        if not title_el:
                            continue
                        title = title_el.text.strip() if hasattr(title_el, 'text') else ""
                        if not title:
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
                                href = "https://www.25dates.com" + href

                        loc_info = self.enhance_location("Toronto, ON", title)
                        eid = self.generate_event_id(title, date_iso, "25dates.com")
                        cats, tags = self.categorize_event(title, "")
                        if "Dating" not in cats:
                            cats.insert(0, "Dating")
                        tags = list(set(tags + ["Speed Dating", "Singles"]))

                        events.append(ScrapedEvent(
                            id=eid,
                            title=title,
                            date=date_iso,
                            location=loc_info.get("location", "Toronto, ON"),
                            address=loc_info.get("address"),
                            lat=loc_info.get("lat"),
                            lng=loc_info.get("lng"),
                            source="25dates.com",
                            host="25dates",
                            url=href or url,
                            categories=cats,
                            tags=tags,
                            is_free=False,
                            price="See site",
                        ))
                    except Exception:
                        continue

            time.sleep(self.DELAY)
        return events

    def scrape(self) -> List[ScrapedEvent]:
        """Scrape all dating event sources."""
        all_events = []
        seen_ids = set()

        # 1) Eventbrite dating category pages
        print(f"[{self.SOURCE_NAME}] Scraping Eventbrite dating categories...")
        for url in EVENTBRITE_DATING_URLS:
            category = url.rstrip("/").split("--")[-1].replace("-", " ").title()
            print(f"  Category: {category}")
            events = self._scrape_eventbrite_category(url)
            for ev in events:
                if ev.id not in seen_ids:
                    all_events.append(ev)
                    seen_ids.add(ev.id)
            print(f"    → {len(events)} events from {category}")
            time.sleep(self.DELAY)

        # 2) 25dates.com (Toronto speed-dating company)
        print(f"[{self.SOURCE_NAME}] Scraping 25dates.com...")
        try:
            events_25d = self._scrape_25dates()
            for ev in events_25d:
                if ev.id not in seen_ids:
                    all_events.append(ev)
                    seen_ids.add(ev.id)
            print(f"  25dates.com → {len(events_25d)} events")
        except Exception as e:
            print(f"  25dates.com error: {e}")

        # 3) Paginate Eventbrite results (pages 2-3) for more events
        for url_base in EVENTBRITE_DATING_URLS:
            for page_num in range(2, 4):
                paginated_url = f"{url_base}?page={page_num}"
                try:
                    events = self._scrape_eventbrite_category(paginated_url)
                    added = 0
                    for ev in events:
                        if ev.id not in seen_ids:
                            all_events.append(ev)
                            seen_ids.add(ev.id)
                            added += 1
                    if added == 0:
                        break  # No new events, stop paginating
                    time.sleep(self.DELAY)
                except Exception:
                    break

        print(f"[{self.SOURCE_NAME}] Total: {len(all_events)} dating events with real dates")
        return all_events


def scrape_dating_events() -> List[dict]:
    """Convenience function for standalone use."""
    scraper = DatingEventsScraper()
    return scraper.scrape_to_json()


if __name__ == "__main__":
    import sys
    import io
    # Fix Windows encoding for unicode output
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    logging.basicConfig(level=logging.INFO)

    print(f"Scrapling available: {HAS_SCRAPLING}")
    print("=" * 60)

    events = scrape_dating_events()

    print(f"\n{'=' * 60}")
    print(f"TOTAL: {len(events)} dating events")

    # Print sample events
    for ev in events[:10]:
        print(f"\n  {ev.get('title', '?')}")
        print(f"    Date: {ev.get('date', '?')}")
        print(f"    Location: {ev.get('location', '?')}")
        print(f"    URL: {ev.get('url', '?')[:80]}")
        print(f"    Price: {ev.get('price', '?')}")
        print(f"    Categories: {ev.get('categories', [])}")

    # Save JSON for review
    output_path = "dating_events_sample.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, default=str, ensure_ascii=False)
    print(f"\nSaved {len(events)} events to {output_path}")
