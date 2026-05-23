#!/usr/bin/env python3
"""
Experimental event sources for gap scanning only (not part of default UnifiedTorontoScraper).

- Optional RSS feed (default: BlogTO FeedBurner) with keyword filter to reduce non-event posts.
- Optional iCal/webcal URL from env EXPERIMENTAL_ICAL_URL.

Wire these only via: python tools/scan_event_gaps.py --include-experimental
"""
from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING, Dict, List, Optional
from urllib.parse import unquote

import requests

if TYPE_CHECKING:
    from .unified_scraper import UnifiedTorontoScraper

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; FindTorontoEvents-Experimental/1.0)",
    "Accept": "application/rss+xml, application/xml, text/xml, */*;q=0.8",
}

DEFAULT_RSS_URL = "https://feeds.feedburner.com/blogto"

# Title/link must match at least one (case-insensitive) to count as event-ish for RSS filter
RSS_KEYWORD_PATTERNS = re.compile(
    r"(event|festival|concert|theatre|theater|comedy|market|exhibit|"
    r"things to do|free things|this weekend|tickets|music|film|"
    r"screening|performance|show at|exhibition|tour|club|venue|"
    r"gallery|museum|parade|fair|night market|pop-up|popup)",
    re.I,
)


def _iso_from_dtstart(raw: str) -> str:
    raw = raw.strip().replace("Z", "")
    # Strip parameters e.g. DTSTART;TZID=...
    if ":" in raw:
        raw = raw.split(":", 1)[-1]
    raw = unquote(raw)
    # VALUE=DATE:YYYYMMDD
    m = re.match(r"^(\d{4})(\d{2})(\d{2})$", raw)
    if m:
        y, mo, d = m.groups()
        return f"{y}-{mo}-{d}T12:00:00Z"
    # YYYYMMDDTHHMMSS
    m = re.match(
        r"^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})",
        raw,
    )
    if m:
        y, mo, d, hh, mm, ss = m.groups()
        return f"{y}-{mo}-{d}T{hh}:{mm}:{ss}Z"
    return ""


def parse_ical_events(ical_text: str, source_name: str) -> List[dict]:
    """Parse VEVENT blocks from iCalendar text (minimal, no icalendar dependency)."""
    events: List[dict] = []
    for block in re.findall(
        r"BEGIN:VEVENT\s*(.*?)END:VEVENT", ical_text, re.S | re.I
    ):
        lines: List[str] = []
        cur = ""
        for line in block.splitlines():
            if line.startswith(" ") and cur:
                cur += line[1:]
            else:
                if cur:
                    lines.append(cur)
                cur = line
        if cur:
            lines.append(cur)
        data: Dict[str, str] = {}
        for line in lines:
            if ":" not in line:
                continue
            key, val = line.split(":", 1)
            key = key.split(";")[0].upper()
            val = val.strip()
            if key in ("DTSTART", "DTEND", "SUMMARY", "DESCRIPTION", "URL", "UID"):
                if key not in data or key == "SUMMARY":
                    data[key] = val
        dt = data.get("DTSTART", "")
        title = data.get("SUMMARY", "").replace("\\n", " ").strip()
        if not title or not dt:
            continue
        date_iso = _iso_from_dtstart(dt)
        if not date_iso:
            continue
        url = data.get("URL", "")
        desc = data.get("DESCRIPTION", "")[:500]
        events.append(
            {
                "title": title,
                "date": date_iso,
                "location": "Toronto, ON",
                "source": source_name,
                "url": url or "",
                "description": desc,
                "host": source_name,
                "price": "See link",
                "is_free": False,
            }
        )
    return events


def fetch_ical_experimental(scraper: "UnifiedTorontoScraper") -> List[dict]:
    url = (os.environ.get("EXPERIMENTAL_ICAL_URL") or "").strip()
    if not url:
        return []
    try:
        r = requests.get(url, headers=REQUEST_HEADERS, timeout=60)
        if r.status_code != 200 or not r.text:
            return []
    except requests.RequestException:
        return []
    events = parse_ical_events(r.text, "Experimental iCal")
    return [scraper.fix_midnight_utc(e) for e in events]


def _strip_ns(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def parse_rss_items(xml_text: str) -> List[dict]:
    """Parse RSS 2.0 / Atom-ish into { title, link, pubDate }."""
    root = ET.fromstring(xml_text)
    items: List[dict] = []
    channel = root
    if _strip_ns(root.tag).lower() == "rss":
        for ch in root:
            if _strip_ns(ch.tag).lower() == "channel":
                channel = ch
                break
    for el in channel.iter():
        tag = _strip_ns(el.tag).lower()
        if tag in ("item", "entry"):
            title = ""
            link = ""
            pub = ""
            for child in el:
                ct = _strip_ns(child.tag).lower()
                if ct == "title" and child.text:
                    title = (child.text or "").strip()
                elif ct in ("link", "id") and (child.text or child.get("href")):
                    link = (child.text or child.get("href") or "").strip()
                elif ct in ("pubdate", "published", "updated") and child.text:
                    pub = (child.text or "").strip()
            if title and link:
                items.append(
                    {
                        "title": title,
                        "link": link,
                        "pubDate": pub,
                    }
                )
    return items


def _rss_item_to_event(item: dict, source_label: str) -> Optional[dict]:
    title = item.get("title", "")
    link = item.get("link", "")
    if not title or not link:
        return None
    if not RSS_KEYWORD_PATTERNS.search(title) and not RSS_KEYWORD_PATTERNS.search(
        link
    ):
        return None
    pub = item.get("pubDate", "")
    date_iso = ""
    if pub:
        try:
            dt = parsedate_to_datetime(pub)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            date_iso = dt.astimezone(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
        except (TypeError, ValueError):
            for fmt in (
                "%a, %d %b %Y %H:%M:%S %z",
                "%a, %d %b %Y %H:%M:%S %Z",
            ):
                try:
                    dt = datetime.strptime(
                        pub.replace(" GMT", " +0000").replace(" UTC", " +0000"),
                        fmt,
                    )
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    date_iso = dt.astimezone(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    )
                    break
                except ValueError:
                    continue
    if not date_iso and pub:
        m = re.search(r"(\d{4}-\d{1,2}-\d{1,2})", pub)
        if m:
            date_iso = m.group(1) + "T12:00:00Z"
    if not date_iso:
        date_iso = datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    return {
        "title": title[:500],
        "date": date_iso,
        "location": "Toronto, ON",
        "source": source_label,
        "url": link,
        "description": "",
        "host": source_label,
        "price": "See link",
        "is_free": False,
    }


def fetch_rss_experimental(
    scraper: "UnifiedTorontoScraper", rss_url: str, max_items: int = 40
) -> List[dict]:
    out: List[dict] = []
    try:
        r = requests.get(rss_url, headers=REQUEST_HEADERS, timeout=60)
        if r.status_code != 200 or not r.text:
            return out
    except requests.RequestException:
        return out
    items = parse_rss_items(r.text)[: max_items * 3]
    label = f"Experimental RSS ({rss_url.split('/')[2] if '/' in rss_url else 'feed'})"
    for it in items:
        ev = _rss_item_to_event(it, label)
        if ev:
            ev = scraper.fix_midnight_utc(ev)
            out.append(ev)
        if len(out) >= max_items:
            break
    return out


def fetch_experimental_events(scraper: "UnifiedTorontoScraper") -> List[dict]:
    """All experimental sources merged (deduped against each other in caller)."""
    rss_url = (os.environ.get("EXPERIMENTAL_RSS_URL") or DEFAULT_RSS_URL).strip()
    merged: List[dict] = []
    merged.extend(fetch_rss_experimental(scraper, rss_url))
    merged.extend(fetch_ical_experimental(scraper))
    return merged
