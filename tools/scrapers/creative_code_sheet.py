#!/usr/bin/env python3
"""
Creative Code Toronto speaker sign-up sheet (event-specific).
Source: https://docs.google.com/spreadsheets/d/1MsbtdvTGMNT75lqq4lnxydY4TczStAOZE1Ap8mQJKeM
Exports as CSV (gid=0) and parses rows for event-like entries.
"""
import csv
import io
import re
from datetime import datetime
from typing import List, Optional, Tuple
from .base_scraper import BaseScraper, ScrapedEvent, TORONTO_VENUES


class CreativeCodeSheetScraper(BaseScraper):
    """Scraper for Creative Code Toronto Google Sheet (event-specific, not citywide)."""

    SOURCE_NAME = "Creative Code Toronto"
    SHEET_ID = "1MsbtdvTGMNT75lqq4lnxydY4TczStAOZE1Ap8mQJKeM"
    EXPORT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"

    def _parse_date_from_cell(self, text: str) -> Tuple[Optional[datetime], Optional[datetime], bool]:
        if not text or not str(text).strip():
            return None, None, False
        text = str(text).strip()
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
        return None, None, False

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        try:
            response = self.session.get(self.EXPORT_URL, timeout=30)
            response.raise_for_status()
            content = response.text
        except Exception as e:
            print(f"[{self.SOURCE_NAME}] Error fetching sheet: {e}")
            return events
        try:
            reader = csv.reader(io.StringIO(content))
            rows = list(reader)
        except Exception as e:
            print(f"[{self.SOURCE_NAME}] CSV parse error: {e}")
            return events
        if not rows:
            return events
        header = [h.strip().lower() for h in rows[0]]
        # Find column indices by common names
        title_col = None
        date_col = None
        name_col = None
        for i, h in enumerate(header):
            if "title" in h or "event" in h or "topic" in h or "name" in h:
                if title_col is None:
                    title_col = i
            if "date" in h or "when" in h or "time" in h:
                date_col = i
            if "name" in h and "event" not in h:
                name_col = i
        if title_col is None:
            title_col = 0
        if date_col is None:
            date_col = 1 if len(header) > 1 else 0
        for row in rows[1:]:
            if len(row) <= max(title_col, date_col):
                continue
            title = (row[title_col] or "").strip()
            if not title or len(title) < 2 or self.should_exclude(title):
                continue
            date_text = (row[date_col] if date_col < len(row) else "") or ""
            start_dt, end_dt, is_multi = self._parse_date_from_cell(date_text)
            if not start_dt:
                continue
            categories, tags = self.categorize_event(title, "")
            tags = list(set(tags + ["Creative Code", "Tech"]))
            event_id = self.generate_event_id(title, start_dt.isoformat(), self.SOURCE_NAME)
            events.append(ScrapedEvent(
                id=event_id,
                title=title,
                date=start_dt.isoformat() + "Z",
                end_date=end_dt.isoformat() + "Z" if end_dt and is_multi else None,
                location="Toronto, ON",
                source=self.SOURCE_NAME,
                host=self.SOURCE_NAME,
                url=f"https://docs.google.com/spreadsheets/d/{self.SHEET_ID}",
                price="Free",
                price_amount=0.0,
                is_free=True,
                description="Creative Code Toronto event",
                categories=categories,
                tags=tags,
                status="UPCOMING",
                is_multi_day=is_multi,
            ))
        seen = set()
        out = []
        for e in events:
            key = (e.title.lower(), e.date[:10])
            if key not in seen:
                seen.add(key)
                out.append(e)
        print(f"[{self.SOURCE_NAME}] Scraped {len(out)} events")
        return out
