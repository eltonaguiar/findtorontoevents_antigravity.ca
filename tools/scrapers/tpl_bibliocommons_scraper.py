#!/usr/bin/env python3
"""
Toronto Public Library Events Scraper (BiblioCommons gateway).

The original `tpl_scraper.py` targets the public /programs-and-classes/ HTML,
which is a JS-rendered SPA and yields zero events to plain HTTP clients
(verified 2026-04-25 — events.json contained no "Toronto Public Library"
rows). This scraper hits the JSON gateway that powers tpl.bibliocommons.com,
the same data source the official TPL events UI uses, which exposes ~7,000+
upcoming events with pagination, location/audience/type/image entity maps,
and stable event-detail URLs.

API: https://gateway.bibliocommons.com/v2/libraries/tpl/events?limit=100&page=N
Detail URL: https://tpl.bibliocommons.com/events/{event_id}
"""
from __future__ import annotations

import html
import json
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Set

from .base_scraper import BaseScraper, ScrapedEvent

GATEWAY_URL = "https://gateway.bibliocommons.com/v2/libraries/tpl/events"
DETAIL_URL_FMT = "https://tpl.bibliocommons.com/events/{eid}"
PAGE_LIMIT = 100


class TPLBiblioCommonsScraper(BaseScraper):
    """Scraper for Toronto Public Library events via the BiblioCommons gateway."""

    SOURCE_NAME = "Toronto Public Library"
    BASE_URL = "https://www.torontopubliclibrary.ca"

    def __init__(self, max_pages: Optional[int] = None, rate_limit: float = 0.4):
        super().__init__()
        self.session.headers.update({"Accept": "application/json"})
        self.max_pages = max_pages
        self.rate_limit = rate_limit
        self.seen_ids: Set[str] = set()

    def _fetch_page(self, page: int) -> Optional[Dict]:
        try:
            r = self.session.get(
                GATEWAY_URL,
                params={"limit": PAGE_LIMIT, "page": page},
                timeout=30,
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"[{self.SOURCE_NAME}] Page {page} fetch failed: {e}")
            return None

    @staticmethod
    def _strip_html(s: str) -> str:
        if not s:
            return ""
        s = re.sub(r"<[^>]+>", " ", s)
        s = html.unescape(s)
        return re.sub(r"\s+", " ", s).strip()

    @staticmethod
    def _to_iso(start: str) -> Optional[str]:
        # BiblioCommons returns naive Toronto-local strings, e.g. "2026-05-20T17:00".
        if not start:
            return None
        try:
            dt = datetime.strptime(start[:16], "%Y-%m-%dT%H:%M")
            return dt.isoformat() + "Z"
        except Exception:
            return None

    def _categorize(
        self,
        title: str,
        description: str,
        type_names: List[str],
        audience_names: List[str],
    ):
        cats, tags = self.categorize_event(title, description)
        for t in type_names:
            tl = t.lower()
            if any(k in tl for k in ("kids", "children", "family", "preschool", "baby", "storytime", "teen", "youth")):
                if "Family" not in cats:
                    cats.append("Family")
            if any(k in tl for k in ("computer", "technology", "coding", "digital", "office software", "career", "job", "resume", "business")):
                if "Business" not in cats:
                    cats.append("Business")
            if any(k in tl for k in ("book", "author", "reading", "literature", "writing", "art", "craft", "music", "film")):
                if "Arts" not in cats:
                    cats.append("Arts")
            if any(k in tl for k in ("language", "culture", "newcomer", "esl")):
                if "Community" not in cats:
                    cats.append("Community")
            if t and t not in tags:
                tags.append(t)
        for a in audience_names:
            if a and a not in tags:
                tags.append(a)
        if not cats or cats == ["General"]:
            cats = ["Community"]
        return cats, tags

    def _build_event(self, ev: Dict, entities: Dict) -> Optional[ScrapedEvent]:
        defin = ev.get("definition") or {}
        title = (defin.get("title") or "").strip()
        start_iso = self._to_iso(defin.get("start") or ev.get("key", ""))
        if not title or not start_iso or self.should_exclude(title):
            return None

        eid = ev.get("id")
        if not eid or eid in self.seen_ids:
            return None
        self.seen_ids.add(eid)

        end_iso = self._to_iso(defin.get("end") or "")
        description = self._strip_html(defin.get("description") or "")[:600]

        loc_entities = entities.get("locations", {}) or {}
        branch_id = defin.get("branchLocationId") or defin.get("nonBranchLocationId")
        branch_name = None
        if branch_id and branch_id in loc_entities:
            branch_name = loc_entities[branch_id].get("name")
        location_label = (
            f"{branch_name} (Toronto Public Library)" if branch_name else "Toronto Public Library"
        )
        loc_info = self.enhance_location("toronto public library", title)

        image_url = None
        img_id = defin.get("featuredImageId")
        if img_id:
            img_ent = (entities.get("images", {}) or {}).get(img_id)
            if img_ent:
                image_url = img_ent.get("url")

        type_ents = entities.get("eventTypes", {}) or {}
        aud_ents = entities.get("eventAudiences", {}) or {}
        type_names = [
            type_ents[t].get("name", "") for t in (defin.get("typeIds") or []) if t in type_ents
        ]
        audience_names = [
            aud_ents[a].get("name", "") for a in (defin.get("audienceIds") or []) if a in aud_ents
        ]

        categories, tags = self._categorize(title, description, type_names, audience_names)

        return ScrapedEvent(
            id=self.generate_event_id(title, start_iso, self.SOURCE_NAME),
            title=title,
            date=start_iso,
            end_date=end_iso,
            location=location_label,
            address=loc_info.get("address"),
            lat=loc_info.get("lat"),
            lng=loc_info.get("lng"),
            source=self.SOURCE_NAME,
            host="Toronto Public Library",
            url=DETAIL_URL_FMT.format(eid=eid),
            price="Free",
            price_amount=0.0,
            is_free=True,
            description=description,
            categories=categories,
            tags=tags,
            status="UPCOMING",
            image=image_url,
            is_recurring=bool(ev.get("isRecurring")),
        )

    def scrape(self) -> List[ScrapedEvent]:
        print(f"[{self.SOURCE_NAME}] Starting scrape via BiblioCommons gateway...")
        all_events: List[ScrapedEvent] = []

        first = self._fetch_page(1)
        if not first:
            return all_events

        pagination = (first.get("events") or {}).get("pagination", {}) or {}
        total_pages = pagination.get("pages", 1)
        if self.max_pages:
            total_pages = min(total_pages, self.max_pages)
        total_count = pagination.get("count", 0)
        print(f"[{self.SOURCE_NAME}] {total_count} events across {total_pages} pages")

        def consume(payload: Dict):
            ent_root = payload.get("entities", {}) or {}
            ev_ent = ent_root.get("events", {}) or {}
            for eid in (payload.get("events") or {}).get("items", []) or []:
                ev = ev_ent.get(eid)
                if not ev:
                    continue
                built = self._build_event(ev, ent_root)
                if built:
                    all_events.append(built)

        consume(first)
        for page in range(2, total_pages + 1):
            time.sleep(self.rate_limit)
            payload = self._fetch_page(page)
            if not payload:
                continue
            consume(payload)
            if page % 10 == 0:
                print(f"[{self.SOURCE_NAME}] page {page}/{total_pages} -> {len(all_events)} events so far")

        print(f"[{self.SOURCE_NAME}] Scraped {len(all_events)} events")
        return all_events


def scrape_tpl_bibliocommons(max_pages: Optional[int] = None) -> List[dict]:
    return TPLBiblioCommonsScraper(max_pages=max_pages).scrape_to_json()


if __name__ == "__main__":
    import sys
    cap = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    events = scrape_tpl_bibliocommons(max_pages=cap)
    print(f"\nTotal events: {len(events)}")
    if events:
        print(json.dumps(events[:2], indent=2, default=str))
