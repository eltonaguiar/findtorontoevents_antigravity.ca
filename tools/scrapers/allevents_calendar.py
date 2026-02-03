#!/usr/bin/env python3
"""
AllEvents.in Toronto calendar (month grid, filters).
Source: https://allevents.in/toronto/calendar
"""
import re
from datetime import datetime
from typing import List, Optional, Tuple
from .base_scraper import BaseScraper, ScrapedEvent, TORONTO_VENUES


class AllEventsCalendarScraper(BaseScraper):
    """Scraper for AllEvents.in Toronto calendar view."""

    SOURCE_NAME = "AllEvents.in"
    BASE_URL = "https://allevents.in"
    SOURCE_URLS = [
        "https://allevents.in/toronto/calendar",
        "https://allevents.in/toronto",
    ]

    def _parse_date_text(self, text: str) -> Tuple[Optional[datetime], Optional[datetime], bool]:
        """Parse date(s) from AllEvents-style text; return (start, end, is_multi_day)."""
        if not text or not text.strip():
            return None, None, False
        text = text.strip()
        year = datetime.now().year
        months = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
            "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
            "july": 7, "august": 8, "september": 9, "october": 10,
            "november": 11, "december": 12,
        }
        # ISO or "Mon, Feb 3" or "Feb 3 - Feb 5"
        iso = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
        if iso:
            try:
                dt = datetime(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
                return dt, None, False
            except ValueError:
                pass
        range_m = re.search(r"(\w+)\s+(\d+)\s*[-–to]\s*(\w+)?\s*(\d+)(?:,\s*(\d{4}))?", text, re.I)
        if range_m:
            m1 = months.get(range_m.group(1).lower(), None)
            d1 = int(range_m.group(2))
            m2 = m1
            if range_m.group(3):
                m2 = months.get(range_m.group(3).lower(), m1)
            d2 = int(range_m.group(4))
            if range_m.group(5):
                year = int(range_m.group(5))
            try:
                start_dt = datetime(year, m1, d1)
                end_dt = datetime(year, m2, d2)
                if end_dt < start_dt:
                    end_dt = start_dt
                return start_dt, end_dt, (end_dt - start_dt).days > 0
            except (ValueError, TypeError):
                pass
        single = re.search(r"(\w+)\s+(\d+)(?:,\s*(\d{4}))?(?:\s|$)", text, re.I)
        if single:
            m = months.get(single.group(1).lower(), None)
            if m is not None:
                d = int(single.group(2))
                y = int(single.group(3)) if single.group(3) else year
                try:
                    return datetime(y, m, d), None, False
                except ValueError:
                    pass
        return None, None, False

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        for url in self.SOURCE_URLS:
            soup = self.fetch_page(url)
            if not soup:
                continue
            # Event cards / links: common AllEvents patterns
            for a in soup.find_all("a", href=re.compile(r"allevents\.in/toronto/", re.I)):
                href = a.get("href", "")
                if "/calendar" in href or "?" in href and "event" not in href.lower():
                    continue
                title_el = a.find(class_=re.compile(r"title|event-name|name", re.I)) or a
                title = title_el.get_text(strip=True) if title_el else ""
                if not title or len(title) < 3 or self.should_exclude(title):
                    continue
                card = a.find_parent(class_=re.compile(r"event|card|item", re.I)) or a.find_parent("li") or a
                date_el = (card or a).find(class_=re.compile(r"date|time|when", re.I)) or (card or a).find("time")
                date_text = date_el.get_text(strip=True) if date_el else ""
                if not date_text:
                    date_text = (card or a).get_text()[:150]
                start_dt, end_dt, is_multi = self._parse_date_text(date_text)
                if not start_dt:
                    continue
                loc_el = (card or a).find(class_=re.compile(r"location|venue|place", re.I))
                loc_text = loc_el.get_text(strip=True) if loc_el else "Toronto, ON"
                loc_info = self.enhance_location(loc_text, title)
                if not href.startswith("http"):
                    href = self.BASE_URL + href if href.startswith("/") else self.BASE_URL + "/" + href
                categories, tags = self.categorize_event(title, "")
                event_id = self.generate_event_id(title, start_dt.isoformat(), self.SOURCE_NAME)
                events.append(ScrapedEvent(
                    id=event_id,
                    title=title,
                    date=start_dt.isoformat() + "Z",
                    end_date=end_dt.isoformat() + "Z" if end_dt and is_multi else None,
                    location=loc_info["location"],
                    address=loc_info.get("address"),
                    lat=loc_info.get("lat"),
                    lng=loc_info.get("lng"),
                    source=self.SOURCE_NAME,
                    host=self.SOURCE_NAME,
                    url=href,
                    price="See Tickets",
                    price_amount=0.0,
                    is_free=False,
                    description="",
                    categories=categories,
                    tags=tags,
                    status="UPCOMING",
                    is_multi_day=is_multi,
                ))
            if events:
                break
        # Dedupe by (title, date)
        seen = set()
        out = []
        for e in events:
            key = (e.title.lower(), e.date[:10])
            if key not in seen:
                seen.add(key)
                out.append(e)
        print(f"[{self.SOURCE_NAME}] Scraped {len(out)} events")
        return out
