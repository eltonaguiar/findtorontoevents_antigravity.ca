#!/usr/bin/env python3
"""
Enrich events.json with thumbnail images for events that don't have one.

Visits each event's URL and extracts:
  1. og:image meta tag
  2. twitter:image meta tag
  3. JSON-LD image field
  4. First large <img> tag as fallback

Usage:
    python tools/enrich_images.py                       # Enrich events.json (default)
    python tools/enrich_images.py -i events.json -m 200 # Custom input, max 200 fetches
    python tools/enrich_images.py --dry-run              # Show stats without writing
"""
import sys
import os
import json
import time
import argparse
import re
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)


def load_events(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_events(events, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(events, f, indent=2, ensure_ascii=False)


def fetch_image_from_url(session, url, timeout=10):
    """Fetch a page and extract the best image URL."""
    try:
        resp = session.get(url, timeout=timeout, allow_redirects=True)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        image_url = ""

        # 1) og:image meta tag (most reliable)
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            image_url = og["content"]

        # 2) twitter:image meta tag
        if not image_url:
            tw = soup.find("meta", attrs={"name": "twitter:image"})
            if tw and tw.get("content"):
                image_url = tw["content"]

        # 3) JSON-LD image field
        if not image_url:
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    ld = json.loads(script.string or "{}")
                    items = ld if isinstance(ld, list) else [ld]
                    for item in items:
                        if item.get("@type") in ("Event", "SocialEvent", "MusicEvent",
                                                  "ExhibitionEvent", "TheaterEvent"):
                            img = item.get("image", "")
                            if isinstance(img, list) and img:
                                img = img[0]
                            if isinstance(img, dict):
                                img = img.get("url", "")
                            if img:
                                image_url = img
                                break
                except Exception:
                    continue
                if image_url:
                    break

        # 4) First meaningful <img> tag (skip tiny icons/trackers)
        if not image_url:
            for img_tag in soup.find_all("img"):
                src = img_tag.get("src", "") or img_tag.get("data-src", "")
                if not src:
                    continue
                # Skip tracking pixels, icons, and data URIs
                if any(skip in src.lower() for skip in [
                    "pixel", "tracker", "1x1", "spacer", "blank",
                    "data:image", "favicon", ".svg", "logo", "icon",
                    "badge", "sprite", "avatar",
                ]):
                    continue
                # Prefer images with reasonable dimensions
                width = img_tag.get("width", "")
                height = img_tag.get("height", "")
                try:
                    w = int(width) if width else 0
                    h = int(height) if height else 0
                    if w > 0 and w < 100:
                        continue
                    if h > 0 and h < 100:
                        continue
                except (ValueError, TypeError):
                    pass
                image_url = src
                break

        # Ensure absolute URL
        if image_url and not image_url.startswith("http"):
            from urllib.parse import urljoin
            image_url = urljoin(url, image_url)

        return image_url if image_url else None

    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Enrich events with thumbnail images")
    parser.add_argument("-i", "--input", default="events.json",
                        help="Input events JSON file (default: events.json)")
    parser.add_argument("-o", "--output", default=None,
                        help="Output file (default: same as input)")
    parser.add_argument("-m", "--max-fetches", type=int, default=150,
                        help="Max pages to fetch (default: 150)")
    parser.add_argument("-d", "--delay", type=float, default=0.5,
                        help="Delay between requests in seconds (default: 0.5)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show stats without writing")
    parser.add_argument("--future-only", action="store_true", default=True,
                        help="Only enrich events from today onwards (default: true)")
    args = parser.parse_args()

    output_path = args.output or args.input

    print("=" * 60)
    print(f"Image Enrichment - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    events = load_events(args.input)
    print(f"Loaded {len(events)} events from {args.input}")

    # Stats before
    with_image = sum(1 for e in events if e.get("image"))
    without_image = len(events) - with_image
    print(f"  With image: {with_image}")
    print(f"  Without image: {without_image}")

    # Filter to events needing images
    today_str = datetime.now().strftime('%Y-%m-%d')
    candidates = []
    for e in events:
        if e.get("image"):
            continue
        if not e.get("url") or not e["url"].startswith("http"):
            continue
        # Skip domains unlikely to have og:image
        if any(p in e["url"] for p in ["toronto.ca", "notion.so", "google.com"]):
            continue
        # Future events only (if flag set)
        if args.future_only:
            event_date = e.get("date", "")[:10]
            if event_date and event_date < today_str:
                continue
        candidates.append(e)

    print(f"\n  Candidates for enrichment: {len(candidates)}")
    print(f"  Will fetch up to: {min(len(candidates), args.max_fetches)} pages")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
    })

    fetched = 0
    enriched = 0

    for event in candidates:
        if fetched >= args.max_fetches:
            break

        url = event["url"]
        time.sleep(args.delay)
        fetched += 1

        image = fetch_image_from_url(session, url)
        if image:
            event["image"] = image
            enriched += 1
            title = event.get("title", "")[:50]
            print(f"  [{enriched}] {title}")

        if fetched % 25 == 0:
            print(f"  ... {fetched}/{min(len(candidates), args.max_fetches)} fetched, {enriched} enriched")

    # Stats after
    new_with = sum(1 for e in events if e.get("image"))
    print(f"\n{'='*60}")
    print("ENRICHMENT RESULTS")
    print('='*60)
    print(f"  Pages fetched: {fetched}")
    print(f"  Events enriched: {enriched}")
    print(f"  Image coverage: {with_image} -> {new_with} / {len(events)} "
          f"({with_image/len(events)*100:.1f}% -> {new_with/len(events)*100:.1f}%)")

    # Coverage by source
    print(f"\n  Coverage by source:")
    sources = {}
    for e in events:
        s = e.get("source", "Unknown")
        if s not in sources:
            sources[s] = {"w": 0, "n": 0}
        if e.get("image"):
            sources[s]["w"] += 1
        else:
            sources[s]["n"] += 1
    for s, c in sorted(sources.items(), key=lambda x: -(x[1]["w"] + x[1]["n"])):
        total = c["w"] + c["n"]
        pct = c["w"] / total * 100 if total else 0
        print(f"    {s:30s} {c['w']:4d}/{total:4d} ({pct:.0f}%)")

    if not args.dry_run:
        save_events(events, output_path)
        print(f"\nSaved {len(events)} events to {output_path}")
    else:
        print("\n[DRY RUN] No files written.")


if __name__ == "__main__":
    main()
