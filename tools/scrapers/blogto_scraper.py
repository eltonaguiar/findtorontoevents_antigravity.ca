#!/usr/bin/env python3
"""
BlogTO Events Scraper for Toronto
Scrapes blogto.com/events/ for upcoming Toronto events.

BlogTO is one of Toronto's most popular media outlets with a comprehensive
events calendar covering concerts, festivals, food events, art shows, and more.
"""
import re
import json
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from .base_scraper import BaseScraper, ScrapedEvent


class BlogTOScraper(BaseScraper):
    """Scraper for BlogTO events in Toronto"""

    SOURCE_NAME = "BlogTO"
    BASE_URL = "https://www.blogto.com"
    EVENTS_URL = f"{BASE_URL}/events/"

    # Category pages to scrape for broader coverage
    CATEGORY_URLS = [
        f"{BASE_URL}/events/",
        f"{BASE_URL}/events/?date=today",
        f"{BASE_URL}/events/?date=tomorrow",
        f"{BASE_URL}/events/?date=this-weekend",
    ]

    def __init__(self):
        super().__init__()
        self.rate_limit_delay = 1.0

    def _extract_jsonld_events(self, soup) -> List[Dict]:
        """Extract events from JSON-LD structured data on BlogTO pages."""
        events = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "{}")
                if isinstance(data, dict):
                    if data.get("@type") == "Event":
                        events.append(data)
                    elif data.get("@type") == "ItemList":
                        for item in data.get("itemListElement", []):
                            ev = item.get("item", {})
                            if ev.get("@type") == "Event":
                                events.append(ev)
                    elif "@graph" in data:
                        for node in data["@graph"]:
                            if isinstance(node, dict) and node.get("@type") == "Event":
                                events.append(node)
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "Event":
                            events.append(item)
            except (json.JSONDecodeError, TypeError):
                continue
        return events

    def _parse_blogto_date(self, date_str: str) -> Optional[str]:
        """Parse BlogTO date formats into ISO format."""
        if not date_str:
            return None

        # ISO format
        iso_m = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", date_str)
        if iso_m:
            return iso_m.group(1) + "Z"

        iso_d = re.match(r"(\d{4}-\d{2}-\d{2})$", date_str)
        if iso_d:
            return iso_d.group(1) + "T00:00:00Z"

        # "February 15, 2026" or "Feb 15, 2026"
        for fmt in ["%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y"]:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.isoformat() + "Z"
            except ValueError:
                continue

        return self.parse_date(date_str)

    def _parse_event_card(self, card, page_url: str) -> Optional[ScrapedEvent]:
        """Parse an event card from BlogTO's event listing HTML."""
        try:
            # Title
            title_el = (
                card.find(class_=re.compile(r"title|heading|name", re.I))
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
            date_el = (
                card.find(class_=re.compile(r"date|time|when", re.I))
                or card.find("time")
            )
            date_text = ""
            if date_el:
                date_text = date_el.get("datetime", "") or date_el.get_text(strip=True)

            parsed_date = self._parse_blogto_date(date_text)
            if not parsed_date:
                # Try extracting from card text
                text = card.get_text()
                date_match = re.search(
                    r"(\w+ \d{1,2},?\s*\d{4})", text
                )
                if date_match:
                    parsed_date = self._parse_blogto_date(date_match.group(1))

            if not parsed_date:
                return None

            # Location
            loc_el = card.find(class_=re.compile(r"location|venue|place|address", re.I))
            location = loc_el.get_text(strip=True) if loc_el else "Toronto, ON"
            loc_info = self.enhance_location(location, title)

            # Description
            desc_el = card.find(class_=re.compile(r"desc|summary|excerpt|body|content", re.I))
            description = desc_el.get_text(strip=True)[:500] if desc_el else ""

            # Price
            price_el = card.find(class_=re.compile(r"price|cost|ticket", re.I))
            price_text = price_el.get_text(strip=True) if price_el else ""
            is_free = "free" in price_text.lower() if price_text else False
            price_display = "Free" if is_free else (price_text or "See Website")

            # Categorize
            categories, tags = self.categorize_event(title, description)

            event_id = self.generate_event_id(title, parsed_date, self.SOURCE_NAME)

            return ScrapedEvent(
                id=event_id,
                title=title,
                date=parsed_date,
                location=loc_info["location"],
                address=loc_info.get("address"),
                lat=loc_info.get("lat"),
                lng=loc_info.get("lng"),
                source=self.SOURCE_NAME,
                host="BlogTO",
                url=event_url,
                price=price_display,
                price_amount=0.0 if is_free else 0.0,
                is_free=is_free,
                description=description,
                categories=categories,
                tags=tags,
                status="UPCOMING",
            )
        except Exception as e:
            print(f"[{self.SOURCE_NAME}] Error parsing event card: {e}")
            return None

    def _scrape_event_detail_page(self, url: str) -> Optional[Dict]:
        """Fetch a BlogTO event detail page for richer data."""
        try:
            soup = self.fetch_page(url)
            if not soup:
                return None

            result = {}

            # JSON-LD (most reliable on detail pages)
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string or "{}")
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get("@type") != "Event":
                            continue
                        result["title"] = item.get("name", "")
                        result["date"] = item.get("startDate", "")
                        result["end_date"] = item.get("endDate", "")
                        result["description"] = (item.get("description") or "")[:500]
                        result["url"] = item.get("url", url)

                        loc = item.get("location") or {}
                        if isinstance(loc, dict):
                            result["venue_name"] = loc.get("name", "")
                            addr = loc.get("address") or {}
                            if isinstance(addr, dict):
                                result["address"] = addr.get("streetAddress", "")
                                result["city"] = addr.get("addressLocality", "")
                            geo = loc.get("geo") or {}
                            if isinstance(geo, dict):
                                result["lat"] = geo.get("latitude")
                                result["lng"] = geo.get("longitude")

                        offers = item.get("offers") or {}
                        if isinstance(offers, list) and offers:
                            offers = offers[0]
                        if isinstance(offers, dict):
                            try:
                                result["price_amount"] = float(offers.get("price", 0))
                            except (ValueError, TypeError):
                                result["price_amount"] = 0
                            if result["price_amount"] == 0:
                                result["is_free"] = True

                        break
                except (json.JSONDecodeError, TypeError):
                    continue

            return result if result else None

        except Exception as e:
            print(f"[{self.SOURCE_NAME}] Error fetching detail: {e}")
            return None

    def scrape(self) -> List[ScrapedEvent]:
        """Scrape events from BlogTO."""
        all_events = []
        seen_ids = set()

        print(f"[{self.SOURCE_NAME}] Starting scrape...")

        for url in self.CATEGORY_URLS:
            print(f"[{self.SOURCE_NAME}] Fetching {url}...")
            soup = self.fetch_page(url)
            if not soup:
                continue

            # 1) JSON-LD events (most reliable)
            jsonld_events = self._extract_jsonld_events(soup)
            for ev_data in jsonld_events:
                title = ev_data.get("name", "")
                start_date = ev_data.get("startDate", "")
                end_date = ev_data.get("endDate", "")

                if not title or not start_date:
                    continue

                parsed_date = self._parse_blogto_date(start_date)
                parsed_end = self._parse_blogto_date(end_date) if end_date else None

                if not parsed_date:
                    continue

                # Location
                loc = ev_data.get("location") or {}
                venue_name = "Toronto, ON"
                address = None
                lat = None
                lng = None
                if isinstance(loc, dict):
                    venue_name = loc.get("name", "Toronto, ON")
                    addr = loc.get("address") or {}
                    if isinstance(addr, dict):
                        street = addr.get("streetAddress", "")
                        city = addr.get("addressLocality", "")
                        parts = [p for p in [street, city, "ON"] if p]
                        address = ", ".join(parts) if street else None
                    geo = loc.get("geo") or {}
                    if isinstance(geo, dict):
                        lat = geo.get("latitude")
                        lng = geo.get("longitude")

                loc_info = self.enhance_location(venue_name, title)
                if loc_info.get("lat") and not lat:
                    lat = loc_info["lat"]
                    lng = loc_info["lng"]
                if loc_info.get("address") and not address:
                    address = loc_info["address"]
                if loc_info["location"] != venue_name:
                    venue_name = loc_info["location"]

                description = (ev_data.get("description") or "")[:500]
                event_url = ev_data.get("url", url)
                if event_url and not event_url.startswith("http"):
                    event_url = self.BASE_URL + event_url

                categories, tags = self.categorize_event(title, description)

                # Price
                offers = ev_data.get("offers") or {}
                if isinstance(offers, list) and offers:
                    offers = offers[0]
                is_free = False
                price_display = "See Website"
                if isinstance(offers, dict):
                    try:
                        price_val = float(offers.get("price", 0))
                        if price_val == 0:
                            is_free = True
                            price_display = "Free"
                        else:
                            price_display = f"CAD ${price_val:.2f}"
                    except (ValueError, TypeError):
                        pass

                event_id = self.generate_event_id(title, parsed_date, self.SOURCE_NAME)
                if event_id in seen_ids:
                    continue
                seen_ids.add(event_id)

                # Multi-day detection
                is_multi = False
                duration_cat = "single"
                if parsed_date and parsed_end:
                    try:
                        s = datetime.fromisoformat(parsed_date.replace("Z", ""))
                        e = datetime.fromisoformat(parsed_end.replace("Z", ""))
                        days = (e - s).days
                        is_multi = days > 0
                        if days <= 7:
                            duration_cat = "short"
                        elif days <= 30:
                            duration_cat = "medium"
                        else:
                            duration_cat = "long"
                    except (ValueError, TypeError):
                        pass

                event = ScrapedEvent(
                    id=event_id,
                    title=title,
                    date=parsed_date,
                    end_date=parsed_end,
                    location=venue_name,
                    address=address,
                    lat=float(lat) if lat else None,
                    lng=float(lng) if lng else None,
                    source=self.SOURCE_NAME,
                    host="BlogTO",
                    url=event_url,
                    price=price_display,
                    price_amount=0.0,
                    is_free=is_free,
                    description=description,
                    categories=categories,
                    tags=tags,
                    status="UPCOMING",
                    is_multi_day=is_multi,
                    duration_category=duration_cat,
                )
                all_events.append(event)

            # 2) HTML event cards
            containers = (
                soup.find_all(class_=re.compile(r"event-card|event-item|event-listing", re.I))
                or soup.find_all("article", class_=re.compile(r"event", re.I))
                or soup.find_all("div", class_=re.compile(r"event-card|listing-card", re.I))
            )
            for card in containers:
                ev = self._parse_event_card(card, url)
                if ev and ev.id not in seen_ids:
                    seen_ids.add(ev.id)
                    all_events.append(ev)

            # 3) Also look for event links to detail pages
            event_links = soup.find_all("a", href=re.compile(r"/events/[^/]+-toronto/"))
            detail_count = 0
            max_details = 30

            for link in event_links:
                if detail_count >= max_details:
                    break

                href = link.get("href", "")
                if not href:
                    continue

                full_url = href if href.startswith("http") else self.BASE_URL + href

                # Quick check: skip if we already have this event
                link_text = link.get_text(strip=True)
                if link_text:
                    test_id = self.generate_event_id(link_text, "", self.SOURCE_NAME)
                    # Not exact but helps avoid obvious duplicates

                time.sleep(self.rate_limit_delay)
                detail = self._scrape_event_detail_page(full_url)

                if not detail or not detail.get("title") or not detail.get("date"):
                    continue

                title = detail["title"]
                parsed_date = self._parse_blogto_date(detail["date"])
                if not parsed_date:
                    continue

                event_id = self.generate_event_id(title, parsed_date, self.SOURCE_NAME)
                if event_id in seen_ids:
                    continue
                seen_ids.add(event_id)

                parsed_end = self._parse_blogto_date(detail.get("end_date", ""))
                venue = detail.get("venue_name", "Toronto, ON")
                loc_info = self.enhance_location(venue, title)
                categories, tags = self.categorize_event(title, detail.get("description", ""))

                is_free = detail.get("is_free", False)
                price_display = "Free" if is_free else "See Website"

                event = ScrapedEvent(
                    id=event_id,
                    title=title,
                    date=parsed_date,
                    end_date=parsed_end,
                    location=loc_info["location"],
                    address=detail.get("address") or loc_info.get("address"),
                    lat=float(detail.get("lat")) if detail.get("lat") else loc_info.get("lat"),
                    lng=float(detail.get("lng")) if detail.get("lng") else loc_info.get("lng"),
                    source=self.SOURCE_NAME,
                    host="BlogTO",
                    url=full_url,
                    price=price_display,
                    price_amount=detail.get("price_amount", 0.0),
                    is_free=is_free,
                    description=detail.get("description", "")[:500],
                    categories=categories,
                    tags=tags,
                    status="UPCOMING",
                )
                all_events.append(event)
                detail_count += 1

            time.sleep(self.rate_limit_delay)

        print(f"[{self.SOURCE_NAME}] Scraped {len(all_events)} events")
        return all_events


def scrape_blogto() -> List[dict]:
    """Convenience function for standalone use."""
    scraper = BlogTOScraper()
    return scraper.scrape_to_json()


if __name__ == "__main__":
    events = scrape_blogto()
    if events:
        print(json.dumps(events[:3], indent=2))
        print(f"\nTotal events: {len(events)}")
    else:
        print("No events found.")
