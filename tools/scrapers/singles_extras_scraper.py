#!/usr/bin/env python3
"""
Singles vertical scrapers — gap-fillers identified by the 2026-04-25 audit.

Sources covered:
  - Single in the City (singleinthecity.ca) — Tribe Events REST API
    (~18 upcoming GTA singles events: speed dating, mixers, social walks)

Sources investigated but not yet implemented (require JS rendering):
  - Flare Events (flareevents.ca) — Toronto page is server-rendered HTML
    but events are loaded via a JS widget; not a Tribe REST endpoint.
  - Toronto Dating Hub (torontodatinghub.com) — Squarespace events
    collection, items not exposed in SQUARESPACE_CONTEXT or sitemap.
  These represent ~15 incremental events combined; revisit with a
  Scrapling/Playwright-based scraper if the singles vertical needs
  fuller coverage.

Filters: only keeps events whose venue/city is in the GTA (Toronto and
adjacent municipalities) so out-of-area Single in the City events
(London, Hamilton, etc.) don't pollute findtorontoevents.ca.
"""
from __future__ import annotations

import html as _html
import json
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Set

from .base_scraper import BaseScraper, ScrapedEvent

SITC_API = "https://singleinthecity.ca/wp-json/tribe/events/v1/events"

# GTA cities — Single in the City posts events GTA-wide; we keep these.
GTA_CITIES = {
    "toronto", "north york", "scarborough", "etobicoke", "york", "east york",
    "mississauga", "brampton", "vaughan", "woodbridge", "markham", "richmond hill",
    "oakville", "burlington", "milton", "ajax", "pickering", "whitby", "oshawa",
    "newmarket", "aurora", "thornhill",
}


def _decode(s: str) -> str:
    return _html.unescape((s or "")).strip()


def _parse_date(s: str) -> Optional[str]:
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s[:19], fmt).isoformat() + "Z"
        except ValueError:
            continue
    return None


class SingleInTheCityScraper(BaseScraper):
    """Tribe Events REST scraper for singleinthecity.ca."""

    SOURCE_NAME = "Single in the City"
    BASE_URL = "https://singleinthecity.ca"

    def __init__(self, page_size: int = 50, rate_limit: float = 0.4):
        super().__init__()
        self.page_size = page_size
        self.rate_limit = rate_limit
        self.seen_ids: Set[str] = set()

    def _fetch(self, page: int) -> Optional[Dict]:
        try:
            r = self.session.get(
                SITC_API,
                params={"per_page": self.page_size, "page": page},
                timeout=30,
            )
            if r.status_code == 400:
                # Tribe returns 400 once you go past the last page.
                return None
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"[{self.SOURCE_NAME}] page {page} failed: {e}")
            return None

    def _is_gta(self, venue: Dict) -> bool:
        if not isinstance(venue, dict):
            return True  # No venue info — accept; SITC is a Toronto-area company.
        city = (venue.get("city") or "").lower().strip()
        if not city:
            return True
        # Strip ", ON" / province
        city = re.sub(r",.*$", "", city).strip()
        return city in GTA_CITIES

    def _build(self, ev: Dict) -> Optional[ScrapedEvent]:
        title = _decode(ev.get("title") or "")
        start = _parse_date(ev.get("start_date") or "")
        if not title or not start or self.should_exclude(title):
            return None

        eid = str(ev.get("id") or "")
        if eid in self.seen_ids:
            return None
        self.seen_ids.add(eid)

        venue = ev.get("venue") or {}
        if not self._is_gta(venue):
            return None

        end = _parse_date(ev.get("end_date") or "")
        url = ev.get("url") or self.BASE_URL

        venue_name = ""
        address = None
        lat = None
        lng = None
        location_label = "Toronto, ON"
        if isinstance(venue, dict):
            venue_name = _decode(venue.get("venue") or "")
            city = _decode(venue.get("city") or "")
            address_raw = _decode(venue.get("address") or "")
            province = _decode(venue.get("province") or venue.get("state_province") or "ON")
            if address_raw or city:
                parts = [p for p in [address_raw, city, province] if p]
                address = ", ".join(parts)
            location_label = venue_name or (city + ", " + province if city else "Toronto, ON")
            try:
                lat = float(venue.get("geo_lat")) if venue.get("geo_lat") else None
                lng = float(venue.get("geo_lng")) if venue.get("geo_lng") else None
            except (TypeError, ValueError):
                lat = lng = None

        # Image
        image_url = None
        img = ev.get("image")
        if isinstance(img, dict):
            image_url = img.get("url") or ((img.get("sizes") or {}).get("medium_large", {}) or {}).get("url")
        elif isinstance(img, str):
            image_url = img

        description = re.sub(r"<[^>]+>", " ", ev.get("description") or "")
        description = re.sub(r"\s+", " ", _decode(description))[:600]

        # Cost
        cost = (ev.get("cost") or "").strip()
        is_free = bool(re.search(r"\bfree\b", cost, re.I)) if cost else False
        price_label = cost if cost else ("Free" if is_free else "Paid (see site)")
        price_amount = 0.0
        m = re.search(r"\$?\s*(\d+(?:\.\d{2})?)", cost or "")
        if m:
            try:
                price_amount = float(m.group(1))
            except ValueError:
                pass

        categories = ["Dating", "Community"]
        tags = ["Singles", "Social Mixer"]
        title_l = title.lower()
        if "speed dat" in title_l:
            tags.append("Speed Dating")
        if "professional" in title_l:
            tags.append("Professionals")
        if "walk" in title_l or "hike" in title_l:
            tags.append("Outdoors")

        return ScrapedEvent(
            id=self.generate_event_id(title, start, self.SOURCE_NAME),
            title=title,
            date=start,
            end_date=end,
            location=location_label,
            address=address,
            lat=lat,
            lng=lng,
            source=self.SOURCE_NAME,
            host="Single in the City",
            url=url,
            price=price_label,
            price_amount=price_amount,
            is_free=is_free,
            description=description,
            categories=categories,
            tags=tags,
            status="UPCOMING",
            image=image_url,
        )

    def scrape(self) -> List[ScrapedEvent]:
        print(f"[{self.SOURCE_NAME}] Starting scrape...")
        out: List[ScrapedEvent] = []
        page = 1
        while True:
            data = self._fetch(page)
            if not data:
                break
            evs = data.get("events") or []
            if not evs:
                break
            for raw in evs:
                built = self._build(raw)
                if built:
                    out.append(built)
            total_pages = data.get("total_pages") or 1
            if page >= total_pages:
                break
            page += 1
            time.sleep(self.rate_limit)
        print(f"[{self.SOURCE_NAME}] Scraped {len(out)} GTA events")
        return out


def scrape_single_in_the_city() -> List[dict]:
    return SingleInTheCityScraper().scrape_to_json()


if __name__ == "__main__":
    evs = scrape_single_in_the_city()
    print(f"\nTotal: {len(evs)}")
    print(json.dumps(evs[:2], indent=2, default=str))
