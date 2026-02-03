#!/usr/bin/env python3
"""
AmericanArenas Toronto Events (concerts, sports, big shows).
Source: https://americanarenas.com/city/toronto-events/
"""
import re
from datetime import datetime
from typing import List, Optional, Tuple
from .base_scraper import BaseScraper, ScrapedEvent, TORONTO_VENUES


class AmericanArenasScraper(BaseScraper):
    """Scraper for AmericanArenas Toronto events calendar."""

    SOURCE_NAME = "AmericanArenas"
    BASE_URL = "https://americanarenas.com"
    EVENTS_URL = "https://americanarenas.com/city/toronto-events/"

    def _parse_date(self, text: str) -> Tuple[Optional[datetime], Optional[datetime], bool]:
        if not text or not text.strip():
            return None, None, False
        text = text.strip()
        year = datetime.now().year
        months = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
        months.update({m: i for i, m in enumerate(["january", "february", "march", "april", "june", "july", "august", "september", "october", "november", "december"], 1)})
        iso = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
        if iso:
            try:
                dt = datetime(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
                return dt, None, False
            except ValueError:
                pass
        single = re.search(r"(\w+)\s+(\d+)(?:,\s*(\d{4}))?", text, re.I)
        if single:
            m = months.get(single.group(1).lower())
            if m is not None:
                d = int(single.group(2))
                y = int(single.group(3)) if single.group(3) else year
                try:
                    return datetime(y, m, d), None, False
                except ValueError:
                    pass
        parsed = self.parse_date(text)
        if parsed:
            dt = datetime.fromisoformat(parsed.replace("Z", ""))
            return dt, None, False
        return None, None, False

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        soup = self.fetch_page(self.EVENTS_URL)
        if not soup:
            return events
        for item in soup.find_all(class_=re.compile(r"event|card|item|listing", re.I)) or soup.find_all("article") or soup.find_all("li"):
            try:
                title_el = item.find(["h1", "h2", "h3", "h4"]) or item.find(class_=re.compile(r"title|name", re.I))
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                if not title or len(title) < 2 or self.should_exclude(title):
                    continue
                link = item.find("a", href=True)
                event_url = link["href"] if link else self.EVENTS_URL
                if event_url and not event_url.startswith("http"):
                    event_url = self.BASE_URL + event_url if event_url.startswith("/") else self.BASE_URL + "/" + event_url
                date_el = item.find(class_=re.compile(r"date|time", re.I)) or item.find("time")
                date_text = date_el.get_text(strip=True) if date_el else item.get_text()[:200]
                start_dt, end_dt, is_multi = self._parse_date(date_text)
                if not start_dt:
                    continue
                loc_el = item.find(class_=re.compile(r"location|venue|arena", re.I))
                loc_text = loc_el.get_text(strip=True) if loc_el else "Toronto, ON"
                loc_info = self.enhance_location(loc_text, title)
                categories, tags = self.categorize_event(title, "")
                if "concert" in title.lower() or "music" in str(categories).lower():
                    tags = list(set(tags + ["Concert"]))
                if "sport" in title.lower() or "game" in title.lower():
                    tags = list(set(tags + ["Sports"]))
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
                    url=event_url,
                    price="See Tickets",
                    price_amount=0.0,
                    is_free=False,
                    description="",
                    categories=categories,
                    tags=tags,
                    status="UPCOMING",
                    is_multi_day=is_multi,
                ))
            except Exception:
                continue
        seen = set()
        out = []
        for e in events:
            key = (e.title.lower(), e.date[:10])
            if key not in seen:
                seen.add(key)
                out.append(e)
        print(f"[{self.SOURCE_NAME}] Scraped {len(out)} events")
        return out
