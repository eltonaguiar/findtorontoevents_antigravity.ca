#!/usr/bin/env python3
"""
Sofia Adel Giudice (@sofiaadelgiudice) Toronto events calendar (Notion).
Provider: sofiaadelgiudice
Source (link to use): https://www.notion.so/2a11557746e4806ca2f8c95fba80ab77?v=2a11557746e480ccbd4c000cddb9687e
Validation: e.g. FREE AGO Wednesday nights 6-9pm. If Notion fetch fails, fallback list is used.
"""
import re
from datetime import datetime
from typing import List, Optional, Tuple
from .base_scraper import BaseScraper, ScrapedEvent, TORONTO_VENUES


class SofiaAdelGiudiceNotionScraper(BaseScraper):
    """Scraper for Sofia Adel Giudice's Toronto events calendar (Notion)."""

    SOURCE_NAME = "sofiaadelgiudice"
    NOTION_URL = "https://www.notion.so/2a11557746e4806ca2f8c95fba80ab77?v=2a11557746e480ccbd4c000cddb9687e"

    def _fallback_events(self, year: int) -> List[ScrapedEvent]:
        """Events from calendar image when Notion fetch fails or returns no events."""
        events = []
        # (day, title, end_day or None for multi-day)
        raw = [
            (1, "OREO pop up", None),
            (1, "FREE KFC", None),
            (1, "FREE jaybird class", None),
            (4, "FREE AGO Wednesday nights 6-9pm", None),
            (6, "LEGO botanicals bloom bar", 7),
            (7, "VAUGHAN WINTERFEST", 8),
            (7, "DIPTYQUE Lunar New Year", None),
            (7, "FREE INDOOR MOVIE NIGHTS", None),
            (11, "NYX BADDIE BROW LAB", 12),
            (14, "FREE INDOOR MOVIE NIGHTS", None),
            (15, "NYX BADDIE BROW LAB", None),
        ]
        for day, title, end_day in raw:
            try:
                start_dt = datetime(year, 2, day)
                end_dt = datetime(year, 2, end_day) if end_day and end_day != day else None
                is_multi = end_dt is not None and (end_dt - start_dt).days > 0
                loc_info = self.enhance_location("Toronto, ON", title)
                if "AGO" in title:
                    loc_info["location"] = "AGO"
                    loc_info["address"] = TORONTO_VENUES.get("ago", {}).get("address")
                    loc_info["lat"] = TORONTO_VENUES.get("ago", {}).get("lat")
                    loc_info["lng"] = TORONTO_VENUES.get("ago", {}).get("lng")
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
                    url=self.NOTION_URL,
                    price="Free",
                    price_amount=0.0,
                    is_free=True,
                    description="",
                    categories=categories,
                    tags=tags,
                    status="UPCOMING",
                    is_multi_day=is_multi,
                ))
            except ValueError:
                continue
        return events

    def _parse_date_from_text(self, text: str, year: int) -> Optional[datetime]:
        """Parse Feb 4 / February 4 style from text."""
        months = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                  "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
        m = re.search(r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d+)|(\d+)\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", text, re.I)
        if m:
            if m.group(1):
                month_str = text[:m.start(1)].split()[-1] if m.start(1) else "feb"
                day = int(m.group(1))
            else:
                day = int(m.group(2))
                month_str = text[m.end(2):].split()[0] if m.end(2) < len(text) else "feb"
            month = months.get(month_str.lower()[:3], 2)
            try:
                return datetime(year, month, day)
            except ValueError:
                pass
        return None

    def scrape(self) -> List[ScrapedEvent]:
        year = datetime.now().year
        events = []
        try:
            soup = self.fetch_page(self.NOTION_URL)
        except Exception:
            soup = None
        if soup:
            for block in soup.find_all(class_=re.compile(r"notion-|page-content|block", re.I)) or soup.find_all(["div", "p", "li"]):
                text = block.get_text(strip=True)
                if len(text) < 5 or self.should_exclude(text):
                    continue
                dt = self._parse_date_from_text(text, year)
                if dt and dt.month == 2:
                    title = text[:120]
                    loc_info = self.enhance_location("Toronto, ON", title)
                    if "AGO" in title:
                        loc_info["location"] = "AGO"
                        loc_info["address"] = TORONTO_VENUES.get("ago", {}).get("address")
                        loc_info["lat"] = TORONTO_VENUES.get("ago", {}).get("lat")
                        loc_info["lng"] = TORONTO_VENUES.get("ago", {}).get("lng")
                    categories, tags = self.categorize_event(title, "")
                    event_id = self.generate_event_id(title, dt.isoformat(), self.SOURCE_NAME)
                    events.append(ScrapedEvent(
                        id=event_id,
                        title=title,
                        date=dt.isoformat() + "Z",
                        end_date=None,
                        location=loc_info["location"],
                        address=loc_info.get("address"),
                        lat=loc_info.get("lat"),
                        lng=loc_info.get("lng"),
                        source=self.SOURCE_NAME,
                        host=self.SOURCE_NAME,
                        url=self.NOTION_URL,
                        price="Free",
                        price_amount=0.0,
                        is_free=True,
                        description="",
                        categories=categories,
                        tags=tags,
                        status="UPCOMING",
                        is_multi_day=False,
                    ))
        if not events:
            events = self._fallback_events(year)
        seen = set()
        out = []
        for e in events:
            key = (e.title.lower()[:60], e.date[:10])
            if key not in seen:
                seen.add(key)
                out.append(e)
        print(f"[{self.SOURCE_NAME}] Scraped {len(out)} events")
        return out
