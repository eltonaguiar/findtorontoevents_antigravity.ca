#!/usr/bin/env python3
"""
Additional Toronto event scrapers using Scrapling / requests.

Targets festivals and venues for May-October 2026 coverage.
"""
import json
import re
import sys
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from dataclasses import dataclass, field, asdict

import requests
from bs4 import BeautifulSoup

try:
    from .base_scraper import BaseScraper, ScrapedEvent
except ImportError:
    from base_scraper import BaseScraper, ScrapedEvent

logger = logging.getLogger(__name__)


def normalize_date(date_str: str) -> Optional[str]:
    """Parse date string to ISO-8601 with noon UTC for date-only values."""
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
    year = datetime.now().year
    # Common formats
    for fmt in ["%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y",
                "%A, %B %d, %Y", "%A, %b %d, %Y"]:
        try:
            dt = datetime.strptime(date_str, fmt)
            dt = dt.replace(hour=12, minute=0, second=0)
            return dt.isoformat() + "Z"
        except ValueError:
            continue
    # Yearless formats (assume current year)
    for fmt in ["%B %d", "%b %d", "%A, %B %d", "%A, %b %d"]:
        try:
            dt = datetime.strptime(date_str, fmt)
            dt = dt.replace(year=year, hour=12, minute=0, second=0)
            return dt.isoformat() + "Z"
        except ValueError:
            continue
    # Date with time
    for fmt in ["%B %d, %Y %I:%M %p", "%b %d, %Y %I:%M %p",
                "%A, %B %d, %Y %I:%M %p", "%A, %b %d, %Y %I:%M %p"]:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.isoformat() + "Z"
        except ValueError:
            continue
    # Yearless with time
    for fmt in ["%B %d %I:%M %p", "%b %d %I:%M %p",
                "%A, %B %d %I:%M %p", "%A, %b %d %I:%M %p"]:
        try:
            dt = datetime.strptime(date_str, fmt)
            dt = dt.replace(year=year)
            return dt.isoformat() + "Z"
        except ValueError:
            continue
    return None


class RebelScraper(BaseScraper):
    SOURCE_NAME = "Rebel"
    BASE_URL = "https://rebeltoronto.com"
    VENUE_LAT = 43.6401
    VENUE_LNG = -79.3528
    VENUE_ADDRESS = "11 Polson St, Toronto, ON M5A 1A4"

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        r = requests.get(f"{self.BASE_URL}/events/", headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select("article.events, .type-events")
        for card in cards:
            title_el = card.find(["h2", "h3", "h4", "h1"])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or self.should_exclude(title):
                continue
            link_el = card.find("a")
            href = link_el.get("href", "") if link_el else ""
            if href and not href.startswith("http"):
                href = self.BASE_URL + href
            date_str = card.find(string=re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December)"))
            date_iso = normalize_date(date_str.strip()) if date_str else None
            if not date_iso:
                continue
            eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)
            cats, tags = self.categorize_event(title, "")
            events.append(ScrapedEvent(
                id=eid, title=title, date=date_iso,
                location=self.SOURCE_NAME, address=self.VENUE_ADDRESS,
                lat=self.VENUE_LAT, lng=self.VENUE_LNG,
                source=self.SOURCE_NAME, url=href or self.BASE_URL,
                categories=cats, tags=tags,
            ))
        return events


class PhoenixConcertTheatreScraper(BaseScraper):
    SOURCE_NAME = "Phoenix Concert Theatre"
    BASE_URL = "https://www.thephoenixconcerttheatre.com"
    VENUE_LAT = 43.6647
    VENUE_LNG = -79.3685
    VENUE_ADDRESS = "410 Sherbourne St, Toronto, ON M5X 1K2"

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        r = requests.get(self.BASE_URL + "/", headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select(".event-item")
        for item in items:
            title_el = item.select_one(".event-title a")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or self.should_exclude(title):
                continue
            href = title_el.get("href", "")
            if href and not href.startswith("http"):
                href = self.BASE_URL + href
            date_el = item.select_one(".event-date")
            date_text = date_el.get_text(strip=True) if date_el else ""
            # Strip "Doors: X:XXpm" suffix
            date_text = re.sub(r",?\s*Doors?:\s*\d{1,2}:\d{2}\s*[ap]m", "", date_text, flags=re.IGNORECASE).strip()
            date_iso = normalize_date(date_text) if date_text else None
            if not date_iso:
                continue
            eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)
            cats, tags = self.categorize_event(title, "")
            events.append(ScrapedEvent(
                id=eid, title=title, date=date_iso,
                location=self.SOURCE_NAME, address=self.VENUE_ADDRESS,
                lat=self.VENUE_LAT, lng=self.VENUE_LNG,
                source=self.SOURCE_NAME, url=href or self.BASE_URL,
                categories=cats, tags=tags,
            ))
        return events


class StacktMarketScraper(BaseScraper):
    SOURCE_NAME = "STACKT Market"
    BASE_URL = "https://stacktmarket.com"
    VENUE_LAT = 43.6424
    VENUE_LNG = -79.4015
    VENUE_ADDRESS = "28 Bathurst St, Toronto, ON M5V 0C6"

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        r = requests.get(f"{self.BASE_URL}/pages/events", headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        # Stackt event cards are <article class="event ...">
        cards = soup.select("article.event")
        for card in cards:
            link_el = card.find("a", href=re.compile(r"/event/"))
            if not link_el:
                continue
            href = link_el.get("href", "")
            if href and not href.startswith("http"):
                href = self.BASE_URL + href
            # Title from link text or image alt
            title = link_el.get_text(strip=True)
            if not title:
                img = link_el.find("img")
                if img:
                    title = img.get("alt", "")
            if not title or len(title) < 5 or self.should_exclude(title):
                continue
            # Date from card text
            date_str = None
            for text in card.stripped_strings:
                if re.match(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}", text.strip()):
                    date_str = text.strip()
                    break
            date_iso = normalize_date(date_str) if date_str else None
            if not date_iso:
                continue
            eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)
            cats, tags = self.categorize_event(title, "")
            events.append(ScrapedEvent(
                id=eid, title=title, date=date_iso,
                location=self.SOURCE_NAME, address=self.VENUE_ADDRESS,
                lat=self.VENUE_LAT, lng=self.VENUE_LNG,
                source=self.SOURCE_NAME, url=href,
                categories=cats, tags=tags,
            ))
        return events


class TorontoJazzFestivalScraper(BaseScraper):
    SOURCE_NAME = "Toronto Jazz Festival"
    BASE_URL = "https://torontojazz.com"
    VENUE_LAT = 43.6532
    VENUE_LNG = -79.3832

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        try:
            r = requests.get(f"{self.BASE_URL}/festival/", headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            # Look for JSON-LD
            for script in soup.find_all("script", {"type": "application/ld+json"}):
                try:
                    data = json.loads(script.string or "")
                    if isinstance(data, dict) and data.get("@type") == "Event":
                        title = data.get("name", "")
                        start = data.get("startDate", "")
                        end = data.get("endDate", "")
                        url = data.get("url", "")
                        if title and start:
                            date_iso = normalize_date(start)
                            end_iso = normalize_date(end) if end else None
                            if date_iso:
                                eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)
                                events.append(ScrapedEvent(
                                    id=eid, title=title, date=date_iso, end_date=end_iso,
                                    location="Toronto, ON",
                                    source=self.SOURCE_NAME, url=url or self.BASE_URL,
                                    categories=["Music", "Arts"], tags=["Jazz", "Festival"],
                                ))
                except (json.JSONDecodeError, TypeError):
                    continue
            # Fallback: look for event listings
            if not events:
                cards = soup.select("[class*=event]")
                for card in cards[:20]:
                    title_el = card.find(["h2", "h3", "h4"])
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)
                    date_str = card.find(string=re.compile(r"(June|July)\s+\d{1,2}"))
                    date_iso = normalize_date(date_str.strip()) if date_str else None
                    if title and date_iso:
                        eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)
                        events.append(ScrapedEvent(
                            id=eid, title=title, date=date_iso,
                            location="Toronto, ON",
                            source=self.SOURCE_NAME, url=self.BASE_URL,
                            categories=["Music", "Arts"], tags=["Jazz", "Festival"],
                        ))
        except Exception as e:
            logger.warning(f"[{self.SOURCE_NAME}] Error: {e}")
        return events


class PrideTorontoScraper(BaseScraper):
    SOURCE_NAME = "Pride Toronto"
    BASE_URL = "https://pridetoronto.com"
    VENUE_LAT = 43.6532
    VENUE_LNG = -79.3832

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        try:
            r = requests.get(self.BASE_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            for script in soup.find_all("script", {"type": "application/ld+json"}):
                try:
                    data = json.loads(script.string or "")
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get("@type") == "Event":
                            title = item.get("name", "")
                            start = item.get("startDate", "")
                            end = item.get("endDate", "")
                            url = item.get("url", "")
                            if title and start:
                                date_iso = normalize_date(start)
                                end_iso = normalize_date(end) if end else None
                                if date_iso:
                                    eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)
                                    events.append(ScrapedEvent(
                                        id=eid, title=title, date=date_iso, end_date=end_iso,
                                        location="Toronto, ON",
                                        source=self.SOURCE_NAME, url=url or self.BASE_URL,
                                        categories=["Community", "Arts"], tags=["Pride", "LGBTQ+"],
                                    ))
                except (json.JSONDecodeError, TypeError):
                    continue
        except Exception as e:
            logger.warning(f"[{self.SOURCE_NAME}] Error: {e}")
        return events


class TorontoFringeScraper(BaseScraper):
    SOURCE_NAME = "Toronto Fringe Festival"
    BASE_URL = "https://fringetoronto.com"
    VENUE_LAT = 43.6532
    VENUE_LNG = -79.3832

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        try:
            r = requests.get(self.BASE_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            for script in soup.find_all("script", {"type": "application/ld+json"}):
                try:
                    data = json.loads(script.string or "")
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get("@type") == "Event":
                            title = item.get("name", "")
                            start = item.get("startDate", "")
                            end = item.get("endDate", "")
                            url = item.get("url", "")
                            if title and start:
                                date_iso = normalize_date(start)
                                end_iso = normalize_date(end) if end else None
                                if date_iso:
                                    eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)
                                    events.append(ScrapedEvent(
                                        id=eid, title=title, date=date_iso, end_date=end_iso,
                                        location="Toronto, ON",
                                        source=self.SOURCE_NAME, url=url or self.BASE_URL,
                                        categories=["Theatre", "Arts"], tags=["Fringe", "Theatre", "Festival"],
                                    ))
                except (json.JSONDecodeError, TypeError):
                    continue
        except Exception as e:
            logger.warning(f"[{self.SOURCE_NAME}] Error: {e}")
        return events


class CaribanaScraper(BaseScraper):
    SOURCE_NAME = "Toronto Caribbean Carnival"
    BASE_URL = "https://torontocarnival.ca"
    VENUE_LAT = 43.6532
    VENUE_LNG = -79.3832

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        try:
            r = requests.get(self.BASE_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            for script in soup.find_all("script", {"type": "application/ld+json"}):
                try:
                    data = json.loads(script.string or "")
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get("@type") == "Event":
                            title = item.get("name", "")
                            start = item.get("startDate", "")
                            end = item.get("endDate", "")
                            url = item.get("url", "")
                            if title and start:
                                date_iso = normalize_date(start)
                                end_iso = normalize_date(end) if end else None
                                if date_iso:
                                    eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)
                                    events.append(ScrapedEvent(
                                        id=eid, title=title, date=date_iso, end_date=end_iso,
                                        location="Toronto, ON",
                                        source=self.SOURCE_NAME, url=url or self.BASE_URL,
                                        categories=["Music", "Community"], tags=["Caribana", "Carnival", "Parade"],
                                    ))
                except (json.JSONDecodeError, TypeError):
                    continue
        except Exception as e:
            logger.warning(f"[{self.SOURCE_NAME}] Error: {e}")
        return events


class NuitBlancheScraper(BaseScraper):
    SOURCE_NAME = "Nuit Blanche Toronto"
    BASE_URL = "https://nbto.com"
    VENUE_LAT = 43.6532
    VENUE_LNG = -79.3832

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        try:
            r = requests.get(self.BASE_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            for script in soup.find_all("script", {"type": "application/ld+json"}):
                try:
                    data = json.loads(script.string or "")
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get("@type") == "Event":
                            title = item.get("name", "")
                            start = item.get("startDate", "")
                            end = item.get("endDate", "")
                            url = item.get("url", "")
                            if title and start:
                                date_iso = normalize_date(start)
                                end_iso = normalize_date(end) if end else None
                                if date_iso:
                                    eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)
                                    events.append(ScrapedEvent(
                                        id=eid, title=title, date=date_iso, end_date=end_iso,
                                        location="Toronto, ON",
                                        source=self.SOURCE_NAME, url=url or self.BASE_URL,
                                        categories=["Arts", "Community"], tags=["Nuit Blanche", "Art Installation", "Night"],
                                    ))
                except (json.JSONDecodeError, TypeError):
                    continue
        except Exception as e:
            logger.warning(f"[{self.SOURCE_NAME}] Error: {e}")
        return events


class HorseshoeTavernScraper(BaseScraper):
    SOURCE_NAME = "Horseshoe Tavern"
    BASE_URL = "https://horseshoetavern.com"
    VENUE_LAT = 43.6491
    VENUE_LNG = -79.3911
    VENUE_ADDRESS = "370 Queen St W, Toronto, ON M5V 2A2"

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        try:
            r = requests.get(f"{self.BASE_URL}/events/", headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            # Find all elements that contain a full date string
            for date_el in soup.find_all(string=re.compile(r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}")):
                date_text = date_el.strip()
                date_iso = normalize_date(date_text)
                if not date_iso:
                    continue
                # Look for title in previous siblings or ancestors
                title = None
                container = date_el.parent
                if container:
                    # Try previous siblings of the container
                    for prev in container.find_all_previous(["h2", "h3", "h4", "div", "span"], limit=10):
                        text = prev.get_text(strip=True)
                        # Skip if it's just the date again or meta info
                        if re.match(r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),", text):
                            continue
                        if len(text) > 10 and not re.match(r"(Door Time|19\+|\$)\s*", text):
                            title = text
                            break
                if not title:
                    continue
                # Clean title - remove appended meta info
                title = re.split(r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),", title)[0].strip()
                title = re.sub(r"Door Time:\s*\d{1,2}:\d{2}\s*[ap]m", "", title, flags=re.IGNORECASE).strip()
                title = re.sub(r"19\+", "", title).strip()
                title = re.sub(r"\$\d+(\.\d{2})?", "", title).strip()
                title = re.sub(r"\s+", " ", title).strip()
                if not title or self.should_exclude(title):
                    continue
                eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)
                cats, tags = self.categorize_event(title, "")
                events.append(ScrapedEvent(
                    id=eid, title=title, date=date_iso,
                    location=self.SOURCE_NAME, address=self.VENUE_ADDRESS,
                    lat=self.VENUE_LAT, lng=self.VENUE_LNG,
                    source=self.SOURCE_NAME, url=self.BASE_URL,
                    categories=cats, tags=tags,
                ))
        except Exception as e:
            logger.warning(f"[{self.SOURCE_NAME}] Error: {e}")
        return events


class TIFFScraper(BaseScraper):
    SOURCE_NAME = "Toronto International Film Festival"
    BASE_URL = "https://tiff.net"
    VENUE_LAT = 43.6532
    VENUE_LNG = -79.3832

    def scrape(self) -> List[ScrapedEvent]:
        events = []
        try:
            r = requests.get(self.BASE_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            for script in soup.find_all("script", {"type": "application/ld+json"}):
                try:
                    data = json.loads(script.string or "")
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get("@type") == "Event":
                            title = item.get("name", "")
                            start = item.get("startDate", "")
                            end = item.get("endDate", "")
                            url = item.get("url", "")
                            if title and start:
                                date_iso = normalize_date(start)
                                end_iso = normalize_date(end) if end else None
                                if date_iso:
                                    eid = self.generate_event_id(title, date_iso, self.SOURCE_NAME)
                                    events.append(ScrapedEvent(
                                        id=eid, title=title, date=date_iso, end_date=end_iso,
                                        location="Toronto, ON",
                                        source=self.SOURCE_NAME, url=url or self.BASE_URL,
                                        categories=["Film", "Arts"], tags=["TIFF", "Film Festival", "Cinema"],
                                    ))
                except (json.JSONDecodeError, TypeError):
                    continue
        except Exception as e:
            logger.warning(f"[{self.SOURCE_NAME}] Error: {e}")
        return events


ALL_FESTIVAL_SCRAPERS = [
    RebelScraper,
    PhoenixConcertTheatreScraper,
    StacktMarketScraper,
    HorseshoeTavernScraper,
    TorontoJazzFestivalScraper,
    PrideTorontoScraper,
    TorontoFringeScraper,
    CaribanaScraper,
    NuitBlancheScraper,
    TIFFScraper,
]


def scrape_all_festivals(verbose: bool = True) -> List[ScrapedEvent]:
    all_events = []
    for scraper_cls in ALL_FESTIVAL_SCRAPERS:
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
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO)

    print(f"Festival scrapers: {len(ALL_FESTIVAL_SCRAPERS)}")
    print("=" * 60)

    all_events = scrape_all_festivals(verbose=True)

    print(f"\n{'=' * 60}")
    print(f"TOTAL: {len(all_events)} events from {len(ALL_FESTIVAL_SCRAPERS)} sources")

    by_source = {}
    for ev in all_events:
        by_source.setdefault(ev.source, []).append(ev)

    for source, evts in by_source.items():
        print(f"\n--- {source} ({len(evts)} events) ---")
        for ev in evts[:5]:
            print(f"  {ev.title}")
            print(f"    Date: {ev.date}")
            print(f"    URL: {ev.url}")

    output = [ev.to_dict() for ev in all_events]
    with open("festival_scraper_output.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str, ensure_ascii=False)
    print(f"\nSaved {len(output)} events to festival_scraper_output.json")
