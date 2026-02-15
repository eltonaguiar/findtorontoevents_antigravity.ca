#!/usr/bin/env python3
"""
Meetup.com Event Scraper for Toronto & GTA
Scrapes Meetup's public event listing pages for upcoming events
in Toronto and surrounding Greater Toronto Area (Mississauga, Brampton,
Markham, Vaughan, Richmond Hill, Oakville, Pickering, etc.).

Meetup's GraphQL API requires Pro access, so this scraper uses their
public-facing find page (Next.js SSR) and individual event pages instead.

Data extraction priority:
  1. __NEXT_DATA__ JSON embedded in the page (most reliable)
  2. JSON-LD structured data on event detail pages
  3. HTML parsing of event cards (fallback)
"""
import re
import json
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Set, Tuple
from .base_scraper import BaseScraper, ScrapedEvent


class MeetupScraper(BaseScraper):
    """Scraper for Meetup.com events in Toronto and GTA"""

    SOURCE_NAME = "Meetup"
    BASE_URL = "https://www.meetup.com"

    # Toronto and GTA search locations
    # Meetup's default ~30 km radius means 3 locations cover the whole GTA.
    SEARCH_LOCATIONS = [
        "ca--on--Toronto",       # Downtown, Midtown, North York, Scarborough, Etobicoke
        "ca--on--Mississauga",   # Western GTA: Mississauga, Brampton, Oakville
        "ca--on--Markham",       # Northern/Eastern GTA: Markham, Richmond Hill, Vaughan, Pickering
    ]

    # Meetup category mapping to our internal categories
    CATEGORY_MAP = {
        "social activities": "Community",
        "hobbies & passions": "General",
        "sports & fitness": "Sports",
        "travel & outdoor": "Sports",
        "career & business": "Business",
        "technology": "Business",
        "community & environment": "Community",
        "identity & language": "Community",
        "games": "General",
        "dancing": "Nightlife",
        "support & coaching": "Community",
        "music": "Music",
        "health & wellbeing": "Community",
        "art & culture": "Arts",
        "science & education": "Business",
        "pets & animals": "General",
        "religion & spirituality": "Community",
        "writing": "Arts",
        "parents & family": "Family",
        "movements & politics": "Community",
        "food & drink": "Food & Drink",
    }

    def __init__(self):
        super().__init__()
        self.seen_event_ids: Set[str] = set()
        self.rate_limit_delay = 1.5  # seconds between requests (be respectful)

    # ── URL helpers ──────────────────────────────────────────────

    def _build_search_url(self, location: str = "ca--on--Toronto") -> str:
        """Build a Meetup find page URL for in-person events"""
        return (
            f"{self.BASE_URL}/find/"
            f"?location={location}"
            "&source=EVENTS"
            "&eventType=inPerson"
        )

    def _clean_event_url(self, url: str) -> str:
        """Strip tracking query params from a Meetup event URL"""
        base = url.split("?")[0] if "?" in url else url
        return base.rstrip("/") + "/"

    def _extract_meetup_event_id(self, url: str) -> Optional[str]:
        """Pull the numeric event ID from a Meetup URL"""
        m = re.search(r"/events/(\d+)", url)
        return m.group(1) if m else None

    # ── Date parsing ─────────────────────────────────────────────

    def _parse_meetup_date(self, date_text: str) -> Optional[str]:
        """
        Parse the date formats Meetup uses into an ISO-8601 string.

        Handles:
          Find page:  "Wed, Feb 18 · 6:00 PM EST"
          Event page: "Sun, Feb 15, 2026, 7:30 PM"
          ISO:        "2026-02-15T19:30:00-05:00"
        """
        if not date_text:
            return None
        date_text = date_text.strip()

        # Format 1  –  find page:  "Wed, Feb 18 · 6:00 PM EST"
        m = re.match(
            r"\w+,\s+(\w+)\s+(\d+)\s*[·•]\s*(\d+:\d+\s*(?:AM|PM))",
            date_text,
        )
        if m:
            month_str, day, time_str = m.groups()
            year = datetime.now().year
            try:
                dt = datetime.strptime(
                    f"{month_str} {day} {year} {time_str}",
                    "%b %d %Y %I:%M %p",
                )
                if dt < datetime.now() - timedelta(days=1):
                    dt = dt.replace(year=year + 1)
                return dt.isoformat() + "Z"
            except ValueError:
                pass

        # Format 2  –  event page: "Sun, Feb 15, 2026, 7:30 PM"
        m2 = re.match(
            r"\w+,\s+(\w+)\s+(\d+),\s*(\d{4}),?\s*(\d+:\d+\s*(?:AM|PM))",
            date_text,
        )
        if m2:
            month_str, day, year, time_str = m2.groups()
            try:
                dt = datetime.strptime(
                    f"{month_str} {day} {year} {time_str}",
                    "%b %d %Y %I:%M %p",
                )
                return dt.isoformat() + "Z"
            except ValueError:
                pass

        # Format 3  –  ISO with timezone offset: "2026-02-15T19:30:00-05:00"
        iso_m = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", date_text)
        if iso_m:
            return iso_m.group(1) + "Z"

        # Format 4  –  ISO date only: "2026-02-15"
        iso_d = re.match(r"(\d{4}-\d{2}-\d{2})$", date_text)
        if iso_d:
            return iso_d.group(1) + "T00:00:00Z"

        # Fallback to base class date parser
        return self.parse_date(date_text)

    # ── __NEXT_DATA__ extraction ─────────────────────────────────

    def _extract_next_data(self, soup) -> Optional[Dict]:
        """Extract the __NEXT_DATA__ JSON blob from a Next.js page"""
        script = soup.find("script", id="__NEXT_DATA__")
        if script and script.string:
            try:
                return json.loads(script.string)
            except (json.JSONDecodeError, TypeError):
                pass
        return None

    def _parse_next_data_events(self, next_data: Dict) -> List[Dict]:
        """Walk __NEXT_DATA__ to pull out event objects"""
        events: List[Dict] = []
        try:
            page_props = next_data.get("props", {}).get("pageProps", {})

            # Meetup's find page stores search results under several paths
            edges = (
                page_props.get("searchResults", {}).get("edges", [])
                or page_props.get("results", {}).get("edges", [])
                or page_props.get("events", [])
            )

            for edge in edges:
                node = edge.get("node", edge) if isinstance(edge, dict) else {}
                if not node or not node.get("title"):
                    continue

                ev: Dict = {
                    "title": node.get("title", ""),
                    "date": node.get("dateTime", ""),
                    "end_date": node.get("endTime", ""),
                    "url": node.get("eventUrl", ""),
                    "description": (node.get("description") or "")[:500],
                    "group": (node.get("group") or {}).get("name", ""),
                    "is_online": node.get("isOnline", False),
                }

                # Venue
                venue = node.get("venue") or {}
                if venue:
                    ev["venue_name"] = venue.get("name", "")
                    ev["address"] = venue.get("address", "")
                    ev["city"] = venue.get("city", "")
                    ev["lat"] = venue.get("lat")
                    ev["lng"] = venue.get("lng")

                # Fee
                fee = node.get("feeSettings") or {}
                if fee:
                    ev["price_amount"] = fee.get("amount", 0)
                    ev["currency"] = fee.get("currency", "CAD")

                # Image
                images = node.get("images") or node.get("featuredPhoto") or {}
                if isinstance(images, list) and images:
                    ev["image"] = images[0].get("baseUrl", "") or images[0].get("source", "")
                elif isinstance(images, dict) and images:
                    ev["image"] = images.get("baseUrl", "") or images.get("source", "")

                events.append(ev)

        except Exception as e:
            print(f"[{self.SOURCE_NAME}] Error parsing __NEXT_DATA__: {e}")

        return events

    # ── HTML-based find-page parser ──────────────────────────────

    def _parse_find_page_html(self, soup) -> List[Dict]:
        """
        Fallback parser: extract events from the rendered HTML.
        Looks for <a> tags whose href matches a Meetup event URL
        and pulls title, date, group from the surrounding card text.
        """
        events: List[Dict] = []

        event_links = soup.find_all(
            "a", href=re.compile(r"meetup\.com/[^/]+/events/\d+")
        )

        for link in event_links:
            try:
                href = link.get("href", "")
                if not href:
                    continue

                clean_url = self._clean_event_url(href)
                meetup_id = self._extract_meetup_event_id(clean_url)
                if not meetup_id or meetup_id in self.seen_event_ids:
                    continue

                # Card text (flat string with pipes for readability)
                card_text = link.get_text(separator=" | ", strip=True)

                # ── Title ──
                title = ""
                # Heading inside or immediately before the link
                heading = link.find(["h2", "h3", "h4"])
                if not heading:
                    parent = link.find_parent(["div", "li", "article"])
                    if parent:
                        heading = parent.find(["h2", "h3", "h4"])
                if heading:
                    title = heading.get_text(strip=True)

                if not title:
                    # First meaningful text segment before date marker
                    parts = re.split(r"\d+ seats? left|Waitlist|\w{3},\s+\w{3}", card_text, maxsplit=1)
                    if parts:
                        title = parts[0].strip(" |")

                if not title or len(title) < 3:
                    continue

                # ── Date ──
                date_match = re.search(
                    r"(\w{3},\s+\w{3}\s+\d+\s*[·•]\s*\d+:\d+\s*(?:AM|PM)\s*\w*)",
                    card_text,
                )
                date_text = date_match.group(1) if date_match else ""

                # ── Group name ──
                group_match = re.search(
                    r"by\s+(.+?)(?:\d+\.?\d*\s*\d+\s+attendee|\s*$)",
                    card_text,
                )
                group_name = group_match.group(1).strip(" |") if group_match else ""

                # ── Attendee count ──
                att_match = re.search(r"(\d+)\s+attendee", card_text)
                attendees = int(att_match.group(1)) if att_match else 0

                ev: Dict = {
                    "title": title,
                    "date_text": date_text,
                    "url": clean_url,
                    "meetup_id": meetup_id,
                    "group": group_name,
                    "attendees": attendees,
                }

                events.append(ev)
                self.seen_event_ids.add(meetup_id)

            except Exception:
                continue

        return events

    # ── Individual event page enrichment ─────────────────────────

    def _enrich_from_event_page(self, event_url: str) -> Dict:
        """Fetch an individual Meetup event page for extra detail"""
        result: Dict = {}
        try:
            time.sleep(self.rate_limit_delay)
            soup = self.fetch_page(event_url)
            if not soup:
                return result

            # ── 1. JSON-LD structured data (best source) ──
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    ld = json.loads(script.string)
                    items = ld if isinstance(ld, list) else [ld]
                    for item in items:
                        if item.get("@type") not in ("Event", "SocialEvent", "MusicEvent"):
                            continue

                        result["title"] = item.get("name", "")
                        result["description"] = (item.get("description") or "")[:500]
                        result["date"] = item.get("startDate", "")
                        result["end_date"] = item.get("endDate", "")

                        img = item.get("image", "")
                        if isinstance(img, list) and img:
                            img = img[0]
                        if isinstance(img, dict):
                            img = img.get("url", "")
                        result["image"] = img

                        loc = item.get("location") or {}
                        if isinstance(loc, dict):
                            result["venue_name"] = loc.get("name", "")
                            addr = loc.get("address") or {}
                            if isinstance(addr, dict):
                                result["address"] = addr.get("streetAddress", "")
                                result["city"] = addr.get("addressLocality", "")
                                result["region"] = addr.get("addressRegion", "")
                                result["postal"] = addr.get("postalCode", "")
                            geo = loc.get("geo") or {}
                            if isinstance(geo, dict):
                                result["lat"] = geo.get("latitude")
                                result["lng"] = geo.get("longitude")

                        org = item.get("organizer") or {}
                        if isinstance(org, dict):
                            result["group"] = org.get("name", "")

                        offers = item.get("offers") or {}
                        if isinstance(offers, list) and offers:
                            offers = offers[0]
                        if isinstance(offers, dict):
                            try:
                                result["price_amount"] = float(offers.get("price", 0))
                            except (ValueError, TypeError):
                                result["price_amount"] = 0
                            result["currency"] = offers.get("priceCurrency", "CAD")
                            if result["price_amount"] == 0:
                                result["is_free"] = True

                        break  # found our event, stop
                except (json.JSONDecodeError, TypeError):
                    continue

            # ── 2. __NEXT_DATA__ as supplement ──
            if not result.get("description"):
                next_data = self._extract_next_data(soup)
                if next_data:
                    try:
                        ev = next_data.get("props", {}).get("pageProps", {}).get("event", {})
                        if ev:
                            if not result.get("description"):
                                result["description"] = (ev.get("description") or "")[:500]
                            if not result.get("image"):
                                imgs = ev.get("images") or []
                                if imgs:
                                    result["image"] = imgs[0].get("baseUrl", "")
                            venue = ev.get("venue") or {}
                            if venue and not result.get("venue_name"):
                                result["venue_name"] = venue.get("name", "")
                                result["lat"] = venue.get("lat")
                                result["lng"] = venue.get("lng")
                    except Exception:
                        pass

            # ── 3. Text fallback for description ──
            if not result.get("description"):
                details_el = (
                    soup.find(id="event-details")
                    or soup.find(class_=re.compile(r"event.*detail", re.I))
                    or soup.find("section", class_=re.compile(r"detail", re.I))
                )
                if details_el:
                    result["description"] = details_el.get_text(strip=True)[:500]

        except Exception as e:
            print(f"[{self.SOURCE_NAME}] Error enriching {event_url}: {e}")

        return result

    # ── Scrape orchestration ─────────────────────────────────────

    def _scrape_find_page(self, url: str) -> List[Dict]:
        """Scrape a single Meetup find page for event data"""
        soup = self.fetch_page(url)
        if not soup:
            return []

        # Try __NEXT_DATA__ first — structured and reliable
        next_data = self._extract_next_data(soup)
        if next_data:
            events = self._parse_next_data_events(next_data)
            if events:
                return events

        # Fallback: parse the rendered HTML
        return self._parse_find_page_html(soup)

    def scrape(self) -> List[ScrapedEvent]:
        """Scrape events from Meetup.com for Toronto and GTA"""
        raw_events: List[Dict] = []

        print(f"[{self.SOURCE_NAME}] Starting scrape for Toronto & GTA...")

        # ── Phase 1: Collect events from find pages ──
        for location in self.SEARCH_LOCATIONS:
            url = self._build_search_url(location=location)
            city_label = location.split("--")[-1]
            print(f"[{self.SOURCE_NAME}] Fetching events near {city_label}...")

            page_events = self._scrape_find_page(url)

            new_count = 0
            for ev in page_events:
                mid = ev.get("meetup_id") or self._extract_meetup_event_id(ev.get("url", ""))
                if mid and mid not in self.seen_event_ids:
                    self.seen_event_ids.add(mid)
                    ev["meetup_id"] = mid
                    raw_events.append(ev)
                    new_count += 1
                elif not mid:
                    raw_events.append(ev)
                    new_count += 1

            print(f"[{self.SOURCE_NAME}]   {new_count} new events from {city_label}")
            time.sleep(self.rate_limit_delay)

        print(f"[{self.SOURCE_NAME}] Total unique events from find pages: {len(raw_events)}")

        # ── Phase 2: Enrich events missing venue / description ──
        enriched_count = 0
        max_enrichments = 50  # cap total HTTP requests for detail pages

        for ev in raw_events:
            if enriched_count >= max_enrichments:
                break

            needs_enrichment = not ev.get("description") and not ev.get("venue_name")
            if not needs_enrichment:
                continue

            event_url = ev.get("url", "")
            if not event_url or "meetup.com" not in event_url:
                continue

            if not event_url.startswith("http"):
                event_url = self.BASE_URL + event_url

            title_preview = (ev.get("title") or "")[:40]
            print(f"[{self.SOURCE_NAME}] Enriching ({enriched_count + 1}/{max_enrichments}): {title_preview}...")

            details = self._enrich_from_event_page(event_url)
            if details:
                for key, val in details.items():
                    if val and not ev.get(key):
                        ev[key] = val
                enriched_count += 1

        if enriched_count:
            print(f"[{self.SOURCE_NAME}] Enriched {enriched_count} events with detail pages")

        # ── Phase 3: Convert raw dicts to ScrapedEvent objects ──
        events: List[ScrapedEvent] = []

        for ev in raw_events:
            try:
                title = ev.get("title", "")
                if not title or self.should_exclude(title):
                    continue

                # Skip online-only events
                if ev.get("is_online"):
                    continue

                # Date
                date_str = ev.get("date", "") or ev.get("date_text", "")
                parsed_date = self._parse_meetup_date(date_str)
                if not parsed_date:
                    parsed_date = self.parse_date(date_str)
                if not parsed_date:
                    continue

                # End date
                end_date = None
                raw_end = ev.get("end_date", "")
                if raw_end:
                    end_date = self._parse_meetup_date(raw_end)

                # Multi-day detection
                is_multi = False
                duration_cat = "single"
                if parsed_date and end_date:
                    try:
                        s = datetime.fromisoformat(parsed_date.replace("Z", ""))
                        e = datetime.fromisoformat(end_date.replace("Z", ""))
                        days = (e - s).days
                        is_multi = days > 0
                        if days == 0:
                            duration_cat = "single"
                        elif days <= 7:
                            duration_cat = "short"
                        elif days <= 30:
                            duration_cat = "medium"
                        else:
                            duration_cat = "long"
                    except (ValueError, TypeError):
                        pass

                # Location / venue
                venue_name = ev.get("venue_name", "")
                city = ev.get("city", "")
                if venue_name:
                    location_str = venue_name
                elif city:
                    location_str = f"{city}, ON"
                else:
                    location_str = "Toronto, ON"

                # Build address string
                address = ev.get("address", "")
                if address and city:
                    region = ev.get("region", "ON")
                    postal = ev.get("postal", "")
                    parts = [address, city, region]
                    if postal:
                        parts.append(postal)
                    address = ", ".join(p for p in parts if p)

                # Enhance with known Toronto venues
                loc_info = self.enhance_location(location_str, title)
                lat = ev.get("lat")
                lng = ev.get("lng")
                if loc_info.get("lat") and not lat:
                    lat = loc_info["lat"]
                    lng = loc_info["lng"]
                if loc_info.get("address") and not address:
                    address = loc_info["address"]
                if loc_info["location"] != location_str:
                    location_str = loc_info["location"]

                # Price
                price_amount = ev.get("price_amount", 0) or 0
                is_free = ev.get("is_free", float(price_amount) == 0)
                if is_free:
                    price_display = "Free"
                elif price_amount > 0:
                    currency = ev.get("currency", "CAD")
                    price_display = f"{currency} ${float(price_amount):.2f}"
                else:
                    price_display = "Free"

                # Categories & tags
                categories, tags = self.categorize_event(
                    title, ev.get("description", "")
                )

                # URL
                event_url = ev.get("url", "")
                if event_url:
                    event_url = self._clean_event_url(event_url)
                    if not event_url.startswith("http"):
                        event_url = self.BASE_URL + event_url

                # Description (strip HTML)
                description = ev.get("description", "")
                if description:
                    description = re.sub(r"<[^>]+>", " ", description)
                    description = re.sub(r"\s+", " ", description).strip()[:500]

                # Host = Meetup group name
                host = ev.get("group", "") or self.SOURCE_NAME

                # Image
                image = ev.get("image", "")

                # Unique ID
                event_id = self.generate_event_id(title, parsed_date, self.SOURCE_NAME)

                event = ScrapedEvent(
                    id=event_id,
                    title=title,
                    date=parsed_date,
                    end_date=end_date if is_multi else None,
                    location=location_str,
                    address=address if address else None,
                    lat=float(lat) if lat else None,
                    lng=float(lng) if lng else None,
                    source=self.SOURCE_NAME,
                    host=host,
                    url=event_url,
                    price=price_display,
                    price_amount=float(price_amount),
                    is_free=is_free,
                    description=description,
                    categories=categories,
                    tags=tags,
                    status="UPCOMING",
                    is_multi_day=is_multi,
                    duration_category=duration_cat,
                )

                events.append(event)

            except Exception as e:
                print(f"[{self.SOURCE_NAME}] Error converting event: {e}")
                continue

        print(f"[{self.SOURCE_NAME}] Scraped {len(events)} events total")
        return events


def scrape_meetup() -> List[dict]:
    """Convenience function for standalone use"""
    scraper = MeetupScraper()
    return scraper.scrape_to_json()


if __name__ == "__main__":
    events = scrape_meetup()
    if events:
        print(json.dumps(events[:3], indent=2))
        print(f"\nTotal events: {len(events)}")
    else:
        print("No events found.")
