#!/usr/bin/env python3
"""
The Toronto Calendar by Chris D (Light Morning / Substack).
Landing: https://lightmorning.substack.com/p/an-update-to-the-calendar
Scrapes the page for the "access my curated Toronto events calendar" link;
if found and it's a public calendar/feed URL, we could follow it (future).
For now we extract event-like content from the Substack post itself.
"""
import re
from datetime import datetime
from typing import List, Optional, Tuple
from .base_scraper import BaseScraper, ScrapedEvent, TORONTO_VENUES


class LightMorningCalendarScraper(BaseScraper):
    """Scraper for Chris D's Toronto Calendar (Substack landing + extracted events)."""

    SOURCE_NAME = "The Toronto Calendar (Chris D)"
    BASE_URL = "https://lightmorning.substack.com"
    LANDING_URL = "https://lightmorning.substack.com/p/an-update-to-the-calendar"

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
        soup = self.fetch_page(self.LANDING_URL)
        if not soup:
            return events
        # Extract calendar link for future use (e.g. Google Calendar ical)
        for a in soup.find_all("a", href=True):
            t = a.get_text(strip=True).lower()
            if "calendar" in t and "access" in t or "curated" in t and "calendar" in t:
                href = a["href"]
                if "calendar" in href or "ical" in href or "google.com/calendar" in href:
                    pass  # could follow href in future
        # Event-like content in post: headings or list items with dates
        for el in soup.find_all(["h2", "h3", "h4", "li", "p"]):
            text = el.get_text(strip=True)
            if len(text) < 5 or self.should_exclude(text):
                continue
            start_dt, end_dt, is_multi = self._parse_date(text)
            if not start_dt:
                continue
            # Use first line or first 80 chars as title
            title = text.split("\n")[0].strip()[:120] if "\n" in text else text[:120]
            if len(title) < 3:
                continue
            link = el.find("a", href=True) or el.find_parent("a", href=True)
            event_url = link["href"] if link else self.LANDING_URL
            if event_url and not event_url.startswith("http"):
                event_url = self.BASE_URL + event_url if event_url.startswith("/") else self.BASE_URL + "/" + event_url
            categories, tags = self.categorize_event(title, "")
            event_id = self.generate_event_id(title, start_dt.isoformat(), self.SOURCE_NAME)
            events.append(ScrapedEvent(
                id=event_id,
                title=title,
                date=start_dt.isoformat() + "Z",
                end_date=end_dt.isoformat() + "Z" if end_dt and is_multi else None,
                location="Toronto, ON",
                source=self.SOURCE_NAME,
                host="Chris D / Light Morning",
                url=event_url,
                price="Free",
                price_amount=0.0,
                is_free=True,
                description="",
                categories=categories,
                tags=tags,
                status="UPCOMING",
                is_multi_day=is_multi,
            ))
        seen = set()
        out = []
        for e in events:
            key = (e.title.lower()[:50], e.date[:10])
            if key not in seen:
                seen.add(key)
                out.append(e)
        print(f"[{self.SOURCE_NAME}] Scraped {len(out)} events")
        return out
