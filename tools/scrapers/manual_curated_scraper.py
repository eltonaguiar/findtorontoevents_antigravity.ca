#!/usr/bin/env python3
"""
Manual curated event sources for findtorontoevents.ca.

Hosts ongoing / on-demand social experiences that don't publish fixed event
dates (so they'd otherwise never appear in scraped output). These surface on
the site as TBD events once the visitor toggles "Show TBD Events".

Add new entries to CURATED_EVENTS below. Keep ``date=""`` for open-ended /
on-demand offerings so the UI classifies them as TBD.
"""
from __future__ import annotations

import hashlib
from typing import Dict, List

try:
    from .base_scraper import BaseScraper, ScrapedEvent
except ImportError:  # standalone run
    from base_scraper import BaseScraper, ScrapedEvent


CURATED_EVENTS: List[Dict] = [
    {
        "slug": "twotwotwo-social-experience-toronto",
        "title": "222 — Surprise Social Experience (Toronto)",
        "url": "https://222.place/",
        "host": "222",
        "location": "Toronto, ON",
        "address": "Toronto, ON",
        "lat": 43.6532,
        "lng": -79.3832,
        "price": "Paid (see site)",
        "price_amount": 0.0,
        "is_free": False,
        "description": (
            "Sign up with your phone number and 222 invites you to a surprise "
            "dinner with 5 hand-matched strangers, followed by an after-party "
            "with ~50 people from other groups. On-demand — no fixed date; "
            "222 schedules each event once the match is confirmed. Great for "
            "meeting new friends in Toronto outside the usual dating-app loop."
        ),
        "categories": ["Dating", "Community"],
        "tags": ["Networking", "Singles", "Social Mixer", "Friends", "TBD"],
    },
    {
        "slug": "timeleft-dinner-with-strangers-toronto",
        "title": "Timeleft — Dinner With Strangers (Toronto)",
        "url": "https://timeleft.com/",
        "host": "Timeleft",
        "location": "Toronto, ON",
        "address": "Toronto, ON",
        "lat": 43.6532,
        "lng": -79.3832,
        "price": "Paid (see site)",
        "price_amount": 0.0,
        "is_free": False,
        "description": (
            "Weekly Wednesday dinner with 5 strangers matched by a personality "
            "quiz, followed by an optional after-party that mixes groups from "
            "across the city. Recurring — no single fixed calendar date since "
            "new tables spin up every week. Filed under dating, but really for "
            "anyone looking to meet new friends or widen their Toronto social "
            "circle."
        ),
        "categories": ["Dating", "Community"],
        "tags": ["Networking", "Singles", "Social Mixer", "Friends", "TBD"],
    },
]


class ManualCuratedScraper(BaseScraper):
    """Emit a small curated set of on-demand / recurring social experiences."""

    SOURCE_NAME = "Manual Curated"
    BASE_URL = ""

    def scrape(self) -> List[ScrapedEvent]:
        out: List[ScrapedEvent] = []
        for entry in CURATED_EVENTS:
            # Stable id — independent of the empty date so re-runs dedupe cleanly.
            ev_id = hashlib.md5(
                f"manual-curated|{entry['slug']}".encode()
            ).hexdigest()
            out.append(
                ScrapedEvent(
                    id=ev_id,
                    title=entry["title"],
                    date="",  # TBD — site renders these only when toggle is active
                    location=entry.get("location", "Toronto, ON"),
                    address=entry.get("address"),
                    lat=entry.get("lat"),
                    lng=entry.get("lng"),
                    source=self.SOURCE_NAME,
                    host=entry.get("host", ""),
                    url=entry.get("url", ""),
                    price=entry.get("price", "Free"),
                    price_amount=float(entry.get("price_amount", 0.0)),
                    is_free=bool(entry.get("is_free", True)),
                    description=entry.get("description", ""),
                    categories=list(entry.get("categories") or ["General"]),
                    tags=list(entry.get("tags") or []),
                )
            )
        return out

    def scrape_to_json(self) -> List[Dict]:
        return [e.to_dict() for e in self.scrape()]


if __name__ == "__main__":
    import json

    print(json.dumps(ManualCuratedScraper().scrape_to_json(), indent=2))
