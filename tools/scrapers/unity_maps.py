#!/usr/bin/env python3
"""
Scraper for Unity Maps (unitymaps.com) - Discover Events & Activities.
Toronto/GTA events with careful multi-day event handling.

Note: As of 2026-02, unitymaps.com returns 200 on the root URL but event paths
(/events, /toronto, etc.) return 404. The scraper tries JSON-LD and HTML cards;
when the site exposes Toronto events (or a crawlable/API URL is found), events
will be picked up automatically. Multi-day ranges (e.g. "May 23 to 24") are
parsed and stored with end_date and is_multi_day.
"""
import re
import json
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from .base_scraper import BaseScraper, ScrapedEvent, TORONTO_VENUES


class UnityMapsScraper(BaseScraper):
    """Scraper for Unity Maps event listings (Toronto focus)."""

    SOURCE_NAME = "Unity Maps"
    BASE_URL = "https://unitymaps.com"

    # Toronto-focused URLs to try
    SOURCE_URLS = [
        f"{BASE_URL}/",
        f"{BASE_URL}/events",
        f"{BASE_URL}/toronto",
        f"{BASE_URL}/city/toronto",
        f"{BASE_URL}/events/toronto",
        f"{BASE_URL}/explore?location=toronto",
    ]

    def parse_unity_date(self, date_text: str) -> Tuple[Optional[datetime], Optional[datetime], bool]:
        """Parse Unity Maps date formats; return (start, end, is_multi_day)."""
        if not date_text or not date_text.strip():
            return None, None, False
        date_text = date_text.strip()
        year = datetime.now().year
        months = {
            "january": 1, "february": 2, "march": 3, "april": 4,
            "may": 5, "june": 6, "july": 7, "august": 8,
            "september": 9, "october": 10, "november": 11, "december": 12,
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        }

        # Multi-day: "May 23 to 24", "May 23 - June 5", "May 23–24, 2026"
        range_same_month = re.search(
            r"(\w+)\s+(\d+)\s*(?:to|–|-)\s*(\d+)(?:,\s*(\d{4}))?",
            date_text, re.IGNORECASE
        )
        if range_same_month:
            month = months.get(range_same_month.group(1).lower(), 1)
            start_day = int(range_same_month.group(2))
            end_day = int(range_same_month.group(3))
            if range_same_month.group(4):
                year = int(range_same_month.group(4))
            try:
                start_dt = datetime(year, month, start_day)
                end_dt = datetime(year, month, end_day)
                if end_dt < start_dt:
                    end_dt = start_dt
                return start_dt, end_dt, (end_dt - start_dt).days > 0
            except ValueError:
                pass

        range_cross_month = re.search(
            r"(\w+)\s+(\d+)\s*(?:to|–|-)\s*(\w+)\s+(\d+)(?:,\s*(\d{4}))?",
            date_text, re.IGNORECASE
        )
        if range_cross_month:
            sm = months.get(range_cross_month.group(1).lower(), 1)
            sd = int(range_cross_month.group(2))
            em = months.get(range_cross_month.group(3).lower(), 1)
            ed = int(range_cross_month.group(4))
            if range_cross_month.group(5):
                year = int(range_cross_month.group(5))
            try:
                start_dt = datetime(year, sm, sd)
                end_dt = datetime(year, em, ed)
                if end_dt < start_dt:
                    end_dt = start_dt
                return start_dt, end_dt, (end_dt - start_dt).days > 0
            except ValueError:
                pass

        # ISO or "May 23, 2026" or "May 23"
        iso = re.search(r"(\d{4})-(\d{2})-(\d{2})", date_text)
        if iso:
            try:
                dt = datetime(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
                return dt, None, False
            except ValueError:
                pass
        single = re.search(r"(\w+)\s+(\d+)(?:,\s*(\d{4}))?", date_text, re.IGNORECASE)
        if single:
            month = months.get(single.group(1).lower(), None)
            if month is not None:
                day = int(single.group(2))
                y = int(single.group(3)) if single.group(3) else year
                try:
                    dt = datetime(y, month, day)
                    return dt, None, False
                except ValueError:
                    pass
        parsed = self.parse_date(date_text)
        if parsed:
            dt = datetime.fromisoformat(parsed.replace("Z", ""))
            return dt, None, False
        return None, None, False

    def extract_json_ld_events(self, soup) -> List[Dict[str, Any]]:
        """Extract Event schema from JSON-LD script tags."""
        events = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "{}")
                if isinstance(data, dict) and data.get("@type") == "Event":
                    events.append(data)
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "Event":
                            events.append(item)
                elif isinstance(data, dict) and "@graph" in data:
                    for node in data.get("@graph", []):
                        if isinstance(node, dict) and node.get("@type") == "Event":
                            events.append(node)
            except (json.JSONDecodeError, TypeError):
                continue
        return events

    def json_ld_to_scraped(self, ld: Dict[str, Any]) -> Optional[ScrapedEvent]:
        """Convert a JSON-LD Event to ScrapedEvent (Toronto filter, multi-day)."""
        name = (ld.get("name") or "").strip()
        if not name or self.should_exclude(name):
            return None
        start = ld.get("startDate") or ""
        end = ld.get("endDate")
        location = ld.get("location")
        loc_name = "Toronto, ON"
        if isinstance(location, dict):
            loc_name = location.get("name") or loc_name
            addr = location.get("address")
            if isinstance(addr, dict):
                loc_name = addr.get("addressLocality") or addr.get("streetAddress") or loc_name
            elif isinstance(addr, str):
                loc_name = addr or loc_name
        elif isinstance(location, str):
            loc_name = location
        # Prefer Toronto/GTA; allow Ontario if we have no other filter
        loc_lower = loc_name.lower()
        if "toronto" not in loc_lower and "gta" not in loc_lower:
            if "ontario" not in loc_lower and "on," not in loc_lower:
                return None
        start_dt = None
        end_dt = None
        is_multi_day = False
        if start:
            try:
                start_dt = datetime.fromisoformat(start.replace("Z", "+00:00").replace("+00:00", ""))
                if start_dt.tzinfo:
                    start_dt = start_dt.replace(tzinfo=None)
            except ValueError:
                start_dt, end_dt, is_multi_day = self.parse_unity_date(start)
        if end and not end_dt:
            try:
                end_dt = datetime.fromisoformat(end.replace("Z", "+00:00").replace("+00:00", ""))
                if end_dt.tzinfo:
                    end_dt = end_dt.replace(tzinfo=None)
                if start_dt and end_dt and (end_dt - start_dt).days > 0:
                    is_multi_day = True
            except ValueError:
                pass
        if not start_dt:
            return None
        url = ld.get("url") or self.BASE_URL
        if url and not url.startswith("http"):
            url = self.BASE_URL + url
        loc_info = self.enhance_location(loc_name, name)
        categories, tags = self.categorize_event(name, (ld.get("description") or ""))
        event_id = self.generate_event_id(name, start_dt.isoformat(), self.SOURCE_NAME)
        return ScrapedEvent(
            id=event_id,
            title=name,
            date=start_dt.isoformat() + "Z",
            end_date=end_dt.isoformat() + "Z" if end_dt and is_multi_day else None,
            location=loc_info["location"],
            address=loc_info.get("address"),
            lat=loc_info.get("lat"),
            lng=loc_info.get("lng"),
            source=self.SOURCE_NAME,
            host=self.SOURCE_NAME,
            url=url,
            price="Free",
            price_amount=0.0,
            is_free=True,
            description=(ld.get("description") or "")[:500],
            categories=categories,
            tags=tags,
            status="UPCOMING",
            is_multi_day=is_multi_day,
        )

    def scrape_page_html(self, soup, page_url: str) -> List[ScrapedEvent]:
        """Scrape event cards from HTML (flexible selectors)."""
        events = []
        # Common patterns: article, .event, .card, [data-event], li with link
        containers = (
            soup.find_all(class_=re.compile(r"event|card|listing|item", re.I)) or
            soup.find_all("article") or
            soup.select("[data-event-id], [data-event]") or
            soup.find_all("li", class_=re.compile(r"event|item"))
        )
        for container in containers:
            try:
                title_el = (
                    container.find(class_=re.compile(r"title|heading|name", re.I)) or
                    container.find(["h2", "h3", "h4"]) or
                    container.find("a", href=True)
                )
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                if not title or len(title) < 3 or self.should_exclude(title):
                    continue
                link = container.find("a", href=True)
                event_url = (link["href"] if link else page_url)
                if event_url and not event_url.startswith("http"):
                    event_url = self.BASE_URL.rstrip("/") + ("/" if not event_url.startswith("/") else "") + event_url
                date_el = container.find(class_=re.compile(r"date|time|when", re.I)) or container.find("time")
                date_text = date_el.get_text(strip=True) if date_el else ""
                if not date_text:
                    date_text = container.get_text()[:200]
                start_dt, end_dt, is_multi_day = self.parse_unity_date(date_text)
                if not start_dt:
                    continue
                loc_el = container.find(class_=re.compile(r"location|venue|place|address", re.I))
                loc_text = loc_el.get_text(strip=True) if loc_el else "Toronto, ON"
                if "toronto" not in loc_text.lower() and "toronto" not in title.lower():
                    continue
                loc_info = self.enhance_location(loc_text, title)
                categories, tags = self.categorize_event(title, "")
                event_id = self.generate_event_id(title, start_dt.isoformat(), self.SOURCE_NAME)
                events.append(ScrapedEvent(
                    id=event_id,
                    title=title,
                    date=start_dt.isoformat() + "Z",
                    end_date=end_dt.isoformat() + "Z" if end_dt and is_multi_day else None,
                    location=loc_info["location"],
                    address=loc_info.get("address"),
                    lat=loc_info.get("lat"),
                    lng=loc_info.get("lng"),
                    source=self.SOURCE_NAME,
                    host=self.SOURCE_NAME,
                    url=event_url,
                    price="Free",
                    price_amount=0.0,
                    is_free=True,
                    description="",
                    categories=categories,
                    tags=tags,
                    status="UPCOMING",
                    is_multi_day=is_multi_day,
                ))
            except Exception:
                continue
        return events

    def scrape(self) -> List[ScrapedEvent]:
        """Scrape Unity Maps for Toronto events (JSON-LD + HTML)."""
        all_events = []
        seen_ids = set()
        for url in self.SOURCE_URLS:
            soup = self.fetch_page(url)
            if not soup:
                continue
            # 1) JSON-LD events
            for ld in self.extract_json_ld_events(soup):
                ev = self.json_ld_to_scraped(ld)
                if ev and ev.id not in seen_ids:
                    seen_ids.add(ev.id)
                    all_events.append(ev)
            # 2) HTML cards
            for ev in self.scrape_page_html(soup, url):
                if ev.id not in seen_ids:
                    seen_ids.add(ev.id)
                    all_events.append(ev)
            if all_events:
                break
        return all_events
